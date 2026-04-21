from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..repository import ExpertRepository
from ..session import SessionStore
from .assets import load_app_icon


class RegisterDialog(QDialog):
    def __init__(self, repository: ExpertRepository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._repository = repository
        self.setWindowTitle("Запрос доступа")
        self.setObjectName("RegisterDialog")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        title = QLabel("Запросить доступ эксперта")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("После отправки заявки администратор одобрит доступ в веб-панели.")
        subtitle.setObjectName("MutedText")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("ФИО")
        self.email = QLineEdit()
        self.email.setPlaceholderText("name@company.com")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Минимум 6 символов")
        form.addRow("ФИО", self.full_name)
        form.addRow("Email", self.email)
        form.addRow("Пароль", self.password)
        root.addLayout(form)

        self.show_password = QCheckBox("Показать пароль")
        self.show_password.toggled.connect(self._toggle_password_visibility)
        root.addWidget(self.show_password)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("OutlineButton")
        cancel_btn.clicked.connect(self.reject)
        submit_btn = QPushButton("Отправить заявку")
        submit_btn.setObjectName("PrimaryButton")
        submit_btn.clicked.connect(self._submit)
        actions.addWidget(cancel_btn)
        actions.addWidget(submit_btn)
        root.addLayout(actions)

    def _toggle_password_visibility(self, checked: bool) -> None:
        self.password.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def _submit(self) -> None:
        full_name = self.full_name.text().strip()
        email = self.email.text().strip().lower()
        password = self.password.text()
        if not full_name or not email or len(password) < 6:
            QMessageBox.warning(self, "Проверка", "Заполните поля и укажите пароль не короче 6 символов.")
            return
        ok, message = self._repository.register_expert(full_name, email, password)
        if not ok:
            QMessageBox.warning(self, "Ошибка", message)
            return
        QMessageBox.information(self, "Заявка отправлена", message)
        self.accept()


class LoginWindow(QWidget):
    login_success = Signal(str)

    def __init__(self, repository: ExpertRepository, session_store: SessionStore, remembered_email: str = "") -> None:
        super().__init__()
        self._repository = repository
        self._session_store = session_store
        self._remembered_email = remembered_email
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("LoginWindow")
        self.setWindowTitle("RiskGuard Desktop - Вход эксперта")
        self.resize(1280, 760)
        self.setMinimumSize(1000, 640)

        shell = QVBoxLayout(self)
        shell.setContentsMargins(40, 30, 40, 30)
        shell.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("LoginCard")
        card.setFixedWidth(520)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 28, 30, 26)
        card_layout.setSpacing(15)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        logo_row.setAlignment(Qt.AlignCenter)
        logo_holder = QLabel()
        logo_holder.setObjectName("LoginLogo")
        logo_holder.setFixedSize(84, 84)
        icon = load_app_icon(78)
        if not icon.isNull():
            logo_holder.setPixmap(icon)
            logo_holder.setAlignment(Qt.AlignCenter)
        logo_text = QLabel("RiskGuard")
        logo_text.setObjectName("LoginBrand")
        logo_row.addWidget(logo_holder)
        logo_row.addWidget(logo_text)
        card_layout.addLayout(logo_row)

        title = QLabel("Вход эксперта")
        title.setObjectName("LoginTitle")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Доступ только для назначенных экспертов")
        subtitle.setObjectName("LoginSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)

        form = QFormLayout()
        form.setContentsMargins(2, 4, 2, 0)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your.email@company.com")
        self.email_input.setText(self._remembered_email)
        self.email_input.returnPressed.connect(self._submit)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Введите пароль")
        self.password_input.returnPressed.connect(self._submit)

        form.addRow("Email", self.email_input)
        form.addRow("Пароль", self.password_input)
        card_layout.addLayout(form)

        remember_row = QHBoxLayout()
        remember_row.setSpacing(8)
        self.remember_checkbox = QCheckBox("Запомнить меня")
        self.remember_checkbox.setChecked(bool(self._remembered_email))
        self.show_password_checkbox = QCheckBox("Показать пароль")
        self.show_password_checkbox.toggled.connect(self._toggle_login_password_visibility)
        forgot_btn = QPushButton("Забыли пароль?")
        forgot_btn.setObjectName("LinkButton")
        forgot_btn.clicked.connect(lambda: QMessageBox.information(self, "Подсказка", "Обратитесь к администратору."))
        remember_row.addWidget(self.remember_checkbox)
        remember_row.addWidget(self.show_password_checkbox)
        remember_row.addStretch()
        remember_row.addWidget(forgot_btn)
        card_layout.addLayout(remember_row)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorText")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        card_layout.addWidget(self.error_label)

        self.login_button = QPushButton("Войти")
        self.login_button.setObjectName("PrimaryButton")
        self.login_button.setMinimumHeight(42)
        self.login_button.clicked.connect(self._submit)
        card_layout.addWidget(self.login_button)

        hint = QFrame()
        hint.setObjectName("SoftCard")
        hint_layout = QVBoxLayout(hint)
        hint_layout.setContentsMargins(10, 8, 10, 8)
        hint_text = QLabel("Для демо: email уже заполнен, используйте пароль: password")
        hint_text.setObjectName("MutedText")
        hint_text.setWordWrap(True)
        hint_layout.addWidget(hint_text)
        card_layout.addWidget(hint)

        register_btn = QPushButton("Запросить доступ")
        register_btn.setObjectName("OutlineButton")
        register_btn.setMinimumHeight(40)
        register_btn.clicked.connect(self._open_register_dialog)
        card_layout.addWidget(register_btn)

        shell.addWidget(card, alignment=Qt.AlignCenter)

    def _submit(self) -> None:
        email = self.email_input.text().strip().lower()
        password = self.password_input.text()
        remember = self.remember_checkbox.isChecked()

        if not email or not password:
            self._show_error("Заполните email и пароль.")
            return

        if not self._repository.authenticate(email, password):
            self._show_error(self._repository.last_error or "Неверный email или пароль.")
            return

        token = self._repository.access_token if remember else ""
        self._session_store.save_login(email=email, remember=remember, token=token)
        self.error_label.hide()
        self.login_success.emit(email)

    def _open_register_dialog(self) -> None:
        dialog = RegisterDialog(self._repository, parent=self)
        dialog.exec()

    def _show_error(self, text: str) -> None:
        self.error_label.setText(text)
        self.error_label.show()

    def _toggle_login_password_visibility(self, checked: bool) -> None:
        self.password_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
