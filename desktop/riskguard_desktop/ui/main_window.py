from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..models import Risk, calculate_risk_level, risk_level_label, risk_status_label
from ..repository import ExpertRepository
from ..session import SessionStore
from .assets import load_app_icon


def _clear_layout(layout: QVBoxLayout | QHBoxLayout | QGridLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child_layout = item.layout()
        if widget is not None:
            widget.deleteLater()
        elif child_layout is not None:
            _clear_layout(child_layout)  # type: ignore[arg-type]


def _badge(text: str, badge_type: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Badge")
    label.setProperty("badgeType", badge_type)
    label.setAlignment(Qt.AlignCenter)
    return label


def _safe_date(date_text: str) -> str:
    date_text = (date_text or "").strip()
    if not date_text:
        return "—"
    formats = ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S")
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_text, fmt)
            return parsed.strftime("%d.%m.%Y")
        except ValueError:
            continue
    return date_text


def _priority_badge(risk: Risk) -> QLabel:
    if risk.priority >= 5:
        return _badge("Критический приоритет", "priority_critical")
    if risk.priority >= 4:
        return _badge("Высокий приоритет", "priority_high")
    if risk.priority >= 3:
        return _badge("Средний приоритет", "priority_medium")
    return _badge("Низкий приоритет", "priority_low")


class AssignedRisksPage(QWidget):
    open_risk = Signal(str)

    def __init__(self, repository: ExpertRepository) -> None:
        super().__init__()
        self._repository = repository
        self._status_filter = "all"
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("PageScroll")
        shell.addWidget(scroll)

        content = QWidget()
        content.setObjectName("PageContainer")
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(28, 24, 28, 24)
        self._content_layout.setSpacing(16)
        scroll.setWidget(content)

        title = QLabel("Назначенные риски")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Риски, ожидающие вашей экспертной оценки")
        subtitle.setObjectName("PageSubtitle")
        self._content_layout.addWidget(title)
        self._content_layout.addWidget(subtitle)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        total_card, self.total_stat = self._stat_card("Всего назначено", "Всего", "blue")
        pending_card, self.pending_stat = self._stat_card("Ожидают оценки", "В работе", "orange")
        assessed_card, self.assessed_stat = self._stat_card("Оценено", "Готово", "green")
        stats_row.addWidget(total_card)
        stats_row.addWidget(pending_card)
        stats_row.addWidget(assessed_card)
        self._content_layout.addLayout(stats_row)

        self.priority_card = QFrame()
        self.priority_card.setObjectName("PriorityCard")
        priority_layout = QVBoxLayout(self.priority_card)
        priority_layout.setContentsMargins(16, 14, 16, 14)
        priority_layout.setSpacing(4)
        self.priority_title = QLabel("Внимание: приоритетные риски")
        self.priority_title.setObjectName("PriorityTitle")
        self.priority_text = QLabel("")
        self.priority_text.setObjectName("PriorityText")
        self.priority_text.setWordWrap(True)
        priority_layout.addWidget(self.priority_title)
        priority_layout.addWidget(self.priority_text)
        self._content_layout.addWidget(self.priority_card)

        filter_card = QFrame()
        filter_card.setObjectName("PageCard")
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setContentsMargins(18, 16, 18, 16)
        filter_layout.setSpacing(12)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)

        search_wrap = QFrame()
        search_wrap.setObjectName("SearchWrap")
        search_layout = QHBoxLayout(search_wrap)
        search_layout.setContentsMargins(12, 4, 12, 4)
        search_layout.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("Поиск по ID или названию риска...")
        self.search_input.textChanged.connect(self.refresh_data)
        search_layout.addWidget(self.search_input)
        controls_row.addWidget(search_wrap, 1)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)
        self.filter_all = self._filter_button("Все", "all")
        self.filter_pending = self._filter_button("Ожидают оценки", "pending")
        self.filter_assessed = self._filter_button("Оценены", "assessed")
        self.filter_all.setChecked(True)
        filters.addWidget(self.filter_all)
        filters.addWidget(self.filter_pending)
        filters.addWidget(self.filter_assessed)
        controls_row.addLayout(filters)

        filter_layout.addLayout(controls_row)
        self._content_layout.addWidget(filter_card)

        self.risk_list_host = QVBoxLayout()
        self.risk_list_host.setSpacing(12)
        self._content_layout.addLayout(self.risk_list_host)
        self._content_layout.addStretch()

    @staticmethod
    def _stat_card(title: str, subtitle: str, tone: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("StatCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        icon = QLabel("")
        icon.setObjectName("StatIcon")
        icon.setProperty("tone", tone)
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(40, 40)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        title_label = QLabel(title)
        title_label.setObjectName("StatLabel")
        value_label = QLabel("0")
        value_label.setObjectName("StatValue")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("StatSubLabel")
        text_col.addWidget(title_label)
        text_col.addWidget(value_label)
        text_col.addWidget(subtitle_label)

        layout.addWidget(icon)
        layout.addLayout(text_col, 1)
        return card, value_label

    def _filter_button(self, text: str, value: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("FilterButton")
        button.setCheckable(True)
        button.setProperty("filterValue", value)
        button.clicked.connect(lambda: self._set_filter(value))
        self.filter_group.addButton(button)
        return button

    def _set_filter(self, value: str) -> None:
        self._status_filter = value
        self.refresh_data()

    def _matches_status(self, risk: Risk) -> bool:
        if self._status_filter == "all":
            return True
        if self._status_filter == "assessed":
            return risk.status == "assessed"
        return risk.status in {"pending", "draft"}

    def refresh_data(self) -> None:
        risks_all = self._repository.list_risks(search=self.search_input.text(), status_filter="all")
        risks = [risk for risk in risks_all if self._matches_status(risk)]

        total = len(risks_all)
        pending = len([risk for risk in risks_all if risk.status in {"pending", "draft"}])
        assessed = len([risk for risk in risks_all if risk.status == "assessed"])
        high_priority = len([risk for risk in risks_all if risk.status in {"pending", "draft"} and risk.priority >= 4])

        self.total_stat.setText(str(total))
        self.pending_stat.setText(str(pending))
        self.assessed_stat.setText(str(assessed))

        self.priority_card.setVisible(high_priority > 0)
        if high_priority > 0:
            self.priority_title.setText(f"Внимание: {high_priority} рисков требуют приоритетной оценки")
            self.priority_text.setText("Эти риски отмечены высоким приоритетом и требуют экспертной оценки в первую очередь.")

        _clear_layout(self.risk_list_host)
        if not risks:
            empty = QFrame()
            empty.setObjectName("EmptyCard")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(18, 18, 18, 18)
            empty_title = QLabel("Риски не найдены")
            empty_title.setObjectName("SectionTitle")
            empty_text = QLabel(
                self._repository.last_error
                or "Попробуйте изменить фильтр или позже обновите список назначенных рисков."
            )
            empty_text.setObjectName("MutedText")
            empty_text.setWordWrap(True)
            empty_layout.addWidget(empty_title)
            empty_layout.addWidget(empty_text)
            self.risk_list_host.addWidget(empty)
            return

        for risk in risks:
            self.risk_list_host.addWidget(self._risk_card(risk))
        self.risk_list_host.addStretch()

    def _risk_card(self, risk: Risk) -> QFrame:
        card = QFrame()
        card.setObjectName("RiskListCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(8)
        risk_id = QLabel(risk.id)
        risk_id.setObjectName("RiskId")
        top.addWidget(risk_id)
        top.addWidget(_badge(risk_status_label(risk.status), f"status_{risk.status}"))
        top.addWidget(_priority_badge(risk))
        top.addStretch()
        open_btn = QPushButton("Открыть")
        open_btn.setObjectName("PrimarySmallButton")
        open_btn.clicked.connect(lambda _, risk_id=risk.id: self.open_risk.emit(risk_id))
        top.addWidget(open_btn)
        layout.addLayout(top)

        title = QLabel(risk.title)
        title.setObjectName("RiskTitleText")
        title.setWordWrap(True)
        layout.addWidget(title)

        description = QLabel(risk.description or "Описание пока не заполнено.")
        description.setObjectName("RiskDescText")
        description.setWordWrap(True)
        layout.addWidget(description)

        meta = QHBoxLayout()
        meta.setSpacing(18)
        category = QLabel(f"Категория: {risk.category or '—'}")
        category.setObjectName("RiskMetaText")
        owner = QLabel(f"Владелец: {risk.owner or '—'}")
        owner.setObjectName("RiskMetaText")
        assigned = QLabel(f"Назначен: {_safe_date(risk.assigned_date)}")
        assigned.setObjectName("RiskMetaText")
        meta.addWidget(category)
        meta.addWidget(owner)
        meta.addWidget(assigned)
        meta.addStretch()
        layout.addLayout(meta)
        return card


class RiskDetailPage(QWidget):
    back_requested = Signal()
    saved = Signal()

    def __init__(self, repository: ExpertRepository) -> None:
        super().__init__()
        self._repository = repository
        self._risk_id: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        shell.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        top = QHBoxLayout()
        back_btn = QPushButton("Назад к списку")
        back_btn.setObjectName("OutlineButton")
        back_btn.clicked.connect(self.back_requested.emit)
        top.addWidget(back_btn)
        top.addStretch()
        root.addLayout(top)

        self.title_label = QLabel("Карточка риска")
        self.title_label.setObjectName("PageTitle")
        self.meta_label = QLabel("")
        self.meta_label.setObjectName("PageSubtitle")
        root.addWidget(self.title_label)
        root.addWidget(self.meta_label)

        self.status_badge = _badge("", "status_pending")
        root.addWidget(self.status_badge, alignment=Qt.AlignLeft)

        info_card = QFrame()
        info_card.setObjectName("PageCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(16, 14, 16, 14)
        info_layout.setSpacing(10)

        self.description = QLabel("")
        self.description.setObjectName("RiskDescText")
        self.description.setWordWrap(True)
        info_layout.addWidget(self.description)

        self.incidents_label = QLabel("")
        self.incidents_label.setObjectName("MutedText")
        self.incidents_label.setWordWrap(True)
        self.mitigations_label = QLabel("")
        self.mitigations_label.setObjectName("MutedText")
        self.mitigations_label.setWordWrap(True)
        info_layout.addWidget(self.incidents_label)
        info_layout.addWidget(self.mitigations_label)
        root.addWidget(info_card)

        form_container = QFrame()
        form_container.setObjectName("PageCard")
        form_layout = QFormLayout(form_container)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(10)

        self.probability_input = QSpinBox()
        self.probability_input.setRange(1, 5)
        self.probability_input.valueChanged.connect(self._update_level_badge)

        self.impact_input = QSpinBox()
        self.impact_input.setRange(1, 5)
        self.impact_input.valueChanged.connect(self._update_level_badge)

        self.level_label = _badge("Низкий", "level_low")

        self.recommendation_input = QTextEdit()
        self.recommendation_input.setPlaceholderText("Рекомендация эксперта")
        self.recommendation_input.setMinimumHeight(130)

        form_layout.addRow("Вероятность (1-5)", self.probability_input)
        form_layout.addRow("Влияние (1-5)", self.impact_input)
        form_layout.addRow("Уровень риска", self.level_label)
        form_layout.addRow("Рекомендация", self.recommendation_input)
        root.addWidget(form_container)

        actions = QHBoxLayout()
        actions.addStretch()
        self.save_draft_btn = QPushButton("Сохранить черновик")
        self.save_draft_btn.setObjectName("OutlineButton")
        self.save_draft_btn.clicked.connect(self._save_draft)
        self.submit_btn = QPushButton("Отправить оценку")
        self.submit_btn.setObjectName("PrimaryButton")
        self.submit_btn.clicked.connect(self._submit)
        actions.addWidget(self.save_draft_btn)
        actions.addWidget(self.submit_btn)
        root.addLayout(actions)

    def load_risk(self, risk_id: str) -> None:
        risk = self._repository.get_risk(risk_id)
        if risk is None:
            QMessageBox.warning(self, "Ошибка", "Риск не найден.")
            return

        self._risk_id = risk.id
        self.title_label.setText(f"{risk.id} — {risk.title}")
        self.meta_label.setText(f"Категория: {risk.category} | Владелец: {risk.owner} | Приоритет: {risk.priority}")
        self.status_badge.setText(risk_status_label(risk.status))
        self.status_badge.setProperty("badgeType", f"status_{risk.status}")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.description.setText(risk.description)

        incidents = "\n".join(f"• {text}" for text in risk.incidents) if risk.incidents else "Нет зарегистрированных инцидентов."
        mitigations = (
            "\n".join(f"• {text}" for text in risk.mitigations)
            if risk.mitigations
            else "Меры минимизации еще не добавлены."
        )
        self.incidents_label.setText(f"Инциденты:\n{incidents}")
        self.mitigations_label.setText(f"Меры минимизации:\n{mitigations}")

        if risk.assessment:
            self.probability_input.setValue(risk.assessment.probability)
            self.impact_input.setValue(risk.assessment.impact)
            self.recommendation_input.setPlainText(risk.assessment.recommendation)
        else:
            self.probability_input.setValue(1)
            self.impact_input.setValue(1)
            self.recommendation_input.clear()

        locked = risk.status == "assessed"
        self.probability_input.setEnabled(not locked)
        self.impact_input.setEnabled(not locked)
        self.recommendation_input.setReadOnly(locked)
        self.save_draft_btn.setEnabled(not locked)
        self.submit_btn.setEnabled(not locked)
        self._update_level_badge()

    def _update_level_badge(self) -> None:
        level = calculate_risk_level(self.probability_input.value(), self.impact_input.value())
        self.level_label.setText(risk_level_label(level))
        self.level_label.setProperty("badgeType", f"level_{level}")
        self.level_label.style().unpolish(self.level_label)
        self.level_label.style().polish(self.level_label)

    def _validate(self) -> bool:
        if not self._risk_id:
            QMessageBox.warning(self, "Ошибка", "Риск не выбран.")
            return False
        if len(self.recommendation_input.toPlainText().strip()) < 8:
            QMessageBox.warning(self, "Проверка", "Добавьте более подробную рекомендацию (не менее 8 символов).")
            return False
        return True

    def _save_draft(self) -> None:
        if not self._validate():
            return
        self._repository.save_draft(
            risk_id=self._risk_id or "",
            probability=self.probability_input.value(),
            impact=self.impact_input.value(),
            recommendation=self.recommendation_input.toPlainText(),
        )
        QMessageBox.information(self, "Черновик", "Черновик оценки сохранен.")
        self.saved.emit()

    def _submit(self) -> None:
        if not self._validate():
            return
        try:
            self._repository.submit_assessment(
                risk_id=self._risk_id or "",
                probability=self.probability_input.value(),
                impact=self.impact_input.value(),
                recommendation=self.recommendation_input.toPlainText(),
            )
        except RuntimeError as error:
            QMessageBox.warning(self, "Ошибка", str(error))
            return
        QMessageBox.information(self, "Успешно", "Экспертная оценка отправлена.")
        if self._risk_id:
            self.load_risk(self._risk_id)
        self.saved.emit()


class MyAssessmentsPage(QWidget):
    open_risk = Signal(str)

    def __init__(self, repository: ExpertRepository) -> None:
        super().__init__()
        self._repository = repository
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        shell.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(28, 24, 28, 24)
        self._content_layout.setSpacing(16)

        title = QLabel("Мои оценки")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Отправленные экспертные оценки рисков")
        subtitle.setObjectName("PageSubtitle")
        self._content_layout.addWidget(title)
        self._content_layout.addWidget(subtitle)

        self.assessment_list = QVBoxLayout()
        self.assessment_list.setSpacing(12)
        self._content_layout.addLayout(self.assessment_list)

        self.summary_card = QFrame()
        self.summary_card.setObjectName("SummaryCard")
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setSpacing(2)
        self.summary_title = QLabel("Всего отправлено оценок: 0")
        self.summary_title.setObjectName("SummaryTitle")
        self.summary_text = QLabel("Продолжайте отличную работу!")
        self.summary_text.setObjectName("SummaryText")
        summary_layout.addWidget(self.summary_title)
        summary_layout.addWidget(self.summary_text)
        self._content_layout.addWidget(self.summary_card)
        self._content_layout.addStretch()

    def refresh_data(self) -> None:
        items = self._repository.list_submitted_assessments()
        _clear_layout(self.assessment_list)

        if not items:
            empty = QFrame()
            empty.setObjectName("EmptyCard")
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(18, 18, 18, 18)
            title = QLabel("Отправленных оценок пока нет")
            title.setObjectName("SectionTitle")
            text = QLabel(self._repository.last_error or "Ваши отправленные экспертные оценки появятся здесь.")
            text.setObjectName("MutedText")
            text.setWordWrap(True)
            empty_layout.addWidget(title)
            empty_layout.addWidget(text)
            self.assessment_list.addWidget(empty)
            self.summary_card.hide()
            return

        self.summary_card.show()
        self.summary_title.setText(f"Всего отправлено оценок: {len(items)}")
        for risk, assessment in items:
            card = QFrame()
            card.setObjectName("RiskListCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(20, 16, 20, 16)
            layout.setSpacing(10)

            top = QHBoxLayout()
            top.setSpacing(8)
            risk_id = QLabel(risk.id)
            risk_id.setObjectName("RiskId")
            top.addWidget(risk_id)
            top.addWidget(_badge("Оценен", "status_assessed"))
            top.addWidget(_badge(risk_level_label(assessment.level), f"level_{assessment.level}"))
            top.addStretch()
            open_btn = QPushButton("Открыть")
            open_btn.setObjectName("OutlineButton")
            open_btn.clicked.connect(lambda _, risk_id=risk.id: self.open_risk.emit(risk_id))
            top.addWidget(open_btn)
            layout.addLayout(top)

            title = QLabel(risk.title)
            title.setObjectName("RiskTitleText")
            title.setWordWrap(True)
            layout.addWidget(title)

            metrics = QGridLayout()
            metrics.setHorizontalSpacing(22)
            metrics.setVerticalSpacing(2)
            self._add_metric(metrics, 0, "Дата оценки", _safe_date(assessment.created_at))
            self._add_metric(metrics, 1, "Вероятность", f"{assessment.probability}/5")
            self._add_metric(metrics, 2, "Влияние", f"{assessment.impact}/5")
            self._add_metric(metrics, 3, "Итоговый балл", str(assessment.probability * assessment.impact))
            layout.addLayout(metrics)

            recommendation_card = QFrame()
            recommendation_card.setObjectName("SoftCard")
            recommendation_layout = QVBoxLayout(recommendation_card)
            recommendation_layout.setContentsMargins(12, 10, 12, 10)
            recommendation_title = QLabel("Рекомендация эксперта")
            recommendation_title.setObjectName("MutedLabel")
            recommendation_text = QLabel(assessment.recommendation)
            recommendation_text.setObjectName("RiskDescText")
            recommendation_text.setWordWrap(True)
            recommendation_layout.addWidget(recommendation_title)
            recommendation_layout.addWidget(recommendation_text)
            layout.addWidget(recommendation_card)

            self.assessment_list.addWidget(card)
        # Keep summary right below the list, without large empty gap above it.

    @staticmethod
    def _add_metric(layout: QGridLayout, column: int, label_text: str, value_text: str) -> None:
        title = QLabel(label_text)
        title.setObjectName("MutedLabel")
        value = QLabel(value_text)
        value.setObjectName("MetricValue")
        layout.addWidget(title, 0, column)
        layout.addWidget(value, 1, column)


class ProfilePage(QWidget):
    def __init__(self, repository: ExpertRepository) -> None:
        super().__init__()
        self._repository = repository
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        shell.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel("Профиль")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Информация о вашем аккаунте эксперта")
        subtitle.setObjectName("PageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.setSpacing(14)
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        info_card = QFrame()
        info_card.setObjectName("PageCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 18, 20, 18)
        info_layout.setSpacing(14)
        info_title = QLabel("Личные данные")
        info_title.setObjectName("SectionTitle")
        info_layout.addWidget(info_title)

        self.name_value = self._profile_row(info_layout, "Имя")
        self.email_value = self._profile_row(info_layout, "Email")
        self.role_value = self._profile_row(info_layout, "Роль")
        self.joined_value = self._profile_row(info_layout, "Дата подключения")
        left_col.addWidget(info_card)
        left_col.addStretch()

        stats_card = QFrame()
        stats_card.setObjectName("PageCard")
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.setContentsMargins(20, 18, 20, 18)
        stats_layout.setSpacing(14)
        stats_title = QLabel("Статистика")
        stats_title.setObjectName("SectionTitle")
        stats_layout.addWidget(stats_title)

        self.assigned_stat = self._small_stat(stats_layout, "Назначенных рисков", "blue")
        self.submitted_stat = self._small_stat(stats_layout, "Отправленных оценок", "green")

        completion_card = QFrame()
        completion_card.setObjectName("SoftCard")
        completion_layout = QVBoxLayout(completion_card)
        completion_layout.setContentsMargins(12, 10, 12, 10)
        completion_layout.setSpacing(4)
        completion_title = QLabel("Процент завершения")
        completion_title.setObjectName("MutedLabel")
        self.completion_value = QLabel("0%")
        self.completion_value.setObjectName("ProgressValue")
        self.completion_bar = QFrame()
        self.completion_bar.setObjectName("ProgressTrack")
        self.completion_fill = QFrame(self.completion_bar)
        self.completion_fill.setObjectName("ProgressFill")
        self.completion_fill.setFixedHeight(8)
        self.completion_fill.move(0, 0)
        self.completion_bar.setFixedHeight(8)
        completion_layout.addWidget(completion_title)
        completion_layout.addWidget(self.completion_value)
        completion_layout.addWidget(self.completion_bar)
        stats_layout.addWidget(completion_card)
        right_col.addWidget(stats_card)

        app_card = QFrame()
        app_card.setObjectName("SoftCard")
        app_layout = QVBoxLayout(app_card)
        app_layout.setContentsMargins(14, 12, 14, 12)
        app_layout.setSpacing(2)
        app_text_col = QVBoxLayout()
        app_text_col.setSpacing(0)
        app_title = QLabel("RiskGuard")
        app_title.setObjectName("SectionTitle")
        app_subtitle = QLabel("Desktop-версия для экспертов")
        app_subtitle.setObjectName("MutedText")
        app_text_col.addWidget(app_title)
        app_text_col.addWidget(app_subtitle)
        app_layout.addLayout(app_text_col)
        right_col.addWidget(app_card)
        right_col.addStretch()

        body.addLayout(left_col, 2)
        body.addLayout(right_col, 1)
        root.addLayout(body)
        root.addStretch()

    @staticmethod
    def _profile_row(parent_layout: QVBoxLayout, title: str) -> QLabel:
        row = QFrame()
        row.setObjectName("ProfileRow")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        row_title = QLabel(title)
        row_title.setObjectName("MutedLabel")
        value = QLabel("—")
        value.setObjectName("ProfileValue")
        layout.addWidget(row_title)
        layout.addWidget(value)
        parent_layout.addWidget(row)
        return value

    @staticmethod
    def _small_stat(parent_layout: QVBoxLayout, title: str, tone: str) -> QLabel:
        row = QFrame()
        row.setObjectName("StatRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        icon = QLabel("")
        icon.setObjectName("StatIcon")
        icon.setProperty("tone", tone)
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(32, 32)
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        value = QLabel("0")
        value.setObjectName("StatValueSmall")
        label = QLabel(title)
        label.setObjectName("MutedLabel")
        text_col.addWidget(value)
        text_col.addWidget(label)
        layout.addWidget(icon)
        layout.addLayout(text_col)
        parent_layout.addWidget(row)
        return value

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        completion_width = self.completion_bar.width()
        if completion_width <= 0:
            return
        pct = self.completion_fill.property("percent") or 0
        fill_width = max(8, int(completion_width * (float(pct) / 100.0))) if float(pct) > 0 else 0
        self.completion_fill.setFixedWidth(fill_width)

    def refresh_data(self) -> None:
        expert = self._repository.get_expert()
        stats = self._repository.get_stats()

        self.name_value.setText(expert.full_name or "—")
        self.email_value.setText(expert.email or "—")
        self.role_value.setText(expert.role or "—")
        self.joined_value.setText(_safe_date(expert.joined_at))

        self.assigned_stat.setText(str(stats["total"]))
        self.submitted_stat.setText(str(stats["assessed"]))
        completion = int(round((stats["assessed"] / stats["total"]) * 100)) if stats["total"] > 0 else 0
        self.completion_value.setText(f"{completion}%")
        self.completion_fill.setProperty("percent", completion)
        fill_width = int(self.completion_bar.width() * (completion / 100.0)) if completion > 0 else 0
        self.completion_fill.setFixedWidth(max(8, fill_width) if completion > 0 else 0)


class MainWindow(QMainWindow):
    def __init__(
        self,
        repository: ExpertRepository,
        session_store: SessionStore,
        email: str,
        on_logout: Callable[[], None],
    ) -> None:
        super().__init__()
        self._repository = repository
        self._session_store = session_store
        self._email = email
        self._on_logout = on_logout
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("RiskGuard Desktop - Эксперт")
        self.resize(1480, 900)
        self.setMinimumSize(1160, 740)

        container = QWidget()
        root = QHBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        content = QFrame()
        content.setObjectName("ContentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)
        root.addWidget(content, 1)

        self.page_risks = AssignedRisksPage(self._repository)
        self.page_risk_detail = RiskDetailPage(self._repository)
        self.page_assessments = MyAssessmentsPage(self._repository)
        self.page_profile = ProfilePage(self._repository)

        self.stack.addWidget(self.page_risks)
        self.stack.addWidget(self.page_risk_detail)
        self.stack.addWidget(self.page_assessments)
        self.stack.addWidget(self.page_profile)
        self.stack.setCurrentWidget(self.page_risks)

        self.page_risks.open_risk.connect(self._open_risk_detail)
        self.page_risk_detail.back_requested.connect(lambda: self._switch_page(self.nav_risks, self.page_risks))
        self.page_risk_detail.saved.connect(self._refresh_after_assessment_change)
        self.page_assessments.open_risk.connect(self._open_risk_detail)

        self.setCentralWidget(container)
        self._switch_page(self.nav_risks, self.page_risks)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(300)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top = QFrame()
        top.setObjectName("SidebarTop")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(14, 14, 14, 14)
        top_layout.setSpacing(12)
        logo = QLabel()
        logo.setObjectName("SidebarLogo")
        logo.setFixedSize(96, 96)
        icon = load_app_icon(92)
        if not icon.isNull():
            logo.setPixmap(icon)
            logo.setAlignment(Qt.AlignCenter)
        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        brand_title = QLabel("RiskGuard")
        brand_title.setObjectName("BrandTitle")
        brand_subtitle = QLabel("Экспертная панель")
        brand_subtitle.setObjectName("BrandSubtitle")
        brand_col.addWidget(brand_title)
        brand_col.addWidget(brand_subtitle)
        top_layout.addWidget(logo)
        top_layout.addLayout(brand_col)
        layout.addWidget(top)

        nav_host = QFrame()
        nav_host.setObjectName("SidebarBody")
        nav_layout = QVBoxLayout(nav_host)
        nav_layout.setContentsMargins(14, 16, 14, 14)
        nav_layout.setSpacing(8)

        self.nav_risks = self._make_nav_button("Назначенные риски", lambda: self._switch_page(self.nav_risks, self.page_risks))
        self.nav_assessments = self._make_nav_button(
            "Оценки", lambda: self._switch_page(self.nav_assessments, self.page_assessments)
        )
        self.nav_profile = self._make_nav_button("Профиль", lambda: self._switch_page(self.nav_profile, self.page_profile))

        nav_layout.addWidget(self.nav_risks)
        nav_layout.addWidget(self.nav_assessments)
        nav_layout.addWidget(self.nav_profile)
        nav_layout.addStretch()
        layout.addWidget(nav_host, 1)

        expert = self._repository.get_expert()
        initials = self._initials(expert.full_name)

        bottom = QFrame()
        bottom.setObjectName("SidebarBottom")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(14, 12, 14, 14)
        bottom_layout.setSpacing(12)

        user_card = QFrame()
        user_card.setObjectName("UserCard")
        user_layout = QHBoxLayout(user_card)
        user_layout.setContentsMargins(10, 10, 10, 10)
        user_layout.setSpacing(10)
        initials_label = QLabel(initials)
        initials_label.setObjectName("SidebarInitials")
        initials_label.setAlignment(Qt.AlignCenter)
        initials_label.setFixedSize(34, 34)
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        name = QLabel(expert.full_name)
        name.setObjectName("SidebarUserName")
        role = QLabel(expert.role)
        role.setObjectName("SidebarUserRole")
        text_col.addWidget(name)
        text_col.addWidget(role)
        user_layout.addWidget(initials_label)
        user_layout.addLayout(text_col)
        bottom_layout.addWidget(user_card)

        logout_btn = QPushButton("Выйти")
        logout_btn.setObjectName("LogoutButton")
        logout_btn.clicked.connect(self._logout)
        bottom_layout.addWidget(logout_btn)
        layout.addWidget(bottom)
        return sidebar

    @staticmethod
    def _initials(full_name: str) -> str:
        parts = [part for part in full_name.strip().split() if part]
        if not parts:
            return "RG"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[1][0]).upper()

    @staticmethod
    def _make_nav_button(title: str, callback: Callable[[], None]) -> QPushButton:
        button = QPushButton(title)
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.clicked.connect(callback)
        return button

    def _set_active_nav(self, active: QPushButton | None) -> None:
        for nav in [self.nav_risks, self.nav_assessments, self.nav_profile]:
            nav.setChecked(nav is active)

    def _switch_page(self, button: QPushButton, page: QWidget) -> None:
        self._set_active_nav(button)
        self.stack.setCurrentWidget(page)
        if page is self.page_risks:
            self.page_risks.refresh_data()
        elif page is self.page_assessments:
            self.page_assessments.refresh_data()
        elif page is self.page_profile:
            self.page_profile.refresh_data()

    def _open_risk_detail(self, risk_id: str) -> None:
        self.page_risk_detail.load_risk(risk_id)
        self.stack.setCurrentWidget(self.page_risk_detail)
        self._set_active_nav(None)

    def _refresh_after_assessment_change(self) -> None:
        self.page_risks.refresh_data()
        self.page_assessments.refresh_data()
        self.page_profile.refresh_data()

    def _logout(self) -> None:
        self._session_store.clear_token()
        self.close()
        self._on_logout()
