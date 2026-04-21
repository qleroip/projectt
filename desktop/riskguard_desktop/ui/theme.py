APP_STYLESHEET = """
QWidget {
    background: #edf2f9;
    color: #142447;
    font-family: "Segoe UI";
    font-size: 14px;
}

QLabel {
    background: transparent;
}

QMainWindow, QDialog {
    background: #edf2f9;
}

QWidget#LoginWindow {
    background: #e7edf7;
}

QFrame#LoginCard {
    background: #ffffff;
    border: 1px solid #d7e0ef;
    border-radius: 18px;
}

QLabel#LoginLogo {
    background: transparent;
}

QLabel#LoginBrand {
    color: #0d1f45;
    font-size: 34px;
    font-weight: 800;
}

QLabel#LoginTitle {
    color: #10254d;
    font-size: 29px;
    font-weight: 800;
}

QLabel#LoginSubtitle {
    color: #6179a6;
    font-size: 14px;
}

QPushButton#LinkButton {
    border: none;
    background: transparent;
    color: #2a66f5;
    font-weight: 600;
    padding: 2px;
}

QPushButton#LinkButton:hover {
    color: #1f54d8;
    text-decoration: underline;
}

QPushButton:focus {
    outline: none;
}

QLabel#ErrorText {
    color: #db3d3d;
    font-weight: 700;
}

QFrame#Sidebar {
    background: #162544;
    border: none;
    border-right: 1px solid #2a3c63;
}

QFrame#SidebarTop {
    background: #162544;
    border: none;
    border-bottom: 1px solid #2a3c63;
}

QFrame#SidebarBody,
QFrame#SidebarBottom {
    background: #162544;
}

QFrame#Sidebar QLabel {
    background: transparent;
}

QLabel#SidebarLogo {
    background: transparent;
    border: none;
    padding: 0px;
}

QLabel#BrandTitle {
    color: #ffffff;
    font-size: 24px;
    font-weight: 800;
}

QLabel#BrandSubtitle {
    color: #a9bcdf;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#NavButton {
    text-align: left;
    border: none;
    border-radius: 12px;
    padding: 11px 14px;
    color: #dbe6ff;
    background: transparent;
    font-weight: 700;
    font-size: 16px;
}

QPushButton#NavButton:hover {
    background: #263a61;
    color: #ffffff;
}

QPushButton#NavButton:checked {
    background: #37527f;
    color: #ffffff;
}

QPushButton#NavButton:focus {
    border: none;
    outline: none;
}

QFrame#UserCard {
    background: rgba(255, 255, 255, 0.10);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 12px;
}

QLabel#SidebarInitials {
    border-radius: 17px;
    background: #2a66f5;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
}

QLabel#SidebarUserName {
    color: #ffffff;
    font-weight: 700;
    font-size: 14px;
}

QLabel#SidebarUserRole {
    color: #bed0f3;
    font-size: 12px;
}

QPushButton#LogoutButton {
    text-align: left;
    border: none;
    border-radius: 10px;
    padding: 10px 12px;
    color: #dbe6ff;
    background: transparent;
    font-size: 14px;
    font-weight: 600;
}

QPushButton#LogoutButton:hover {
    background: #263a61;
    color: #ffffff;
}

QPushButton#LogoutButton:focus {
    border: none;
    outline: none;
}

QFrame#ContentArea {
    background: #edf2f9;
}

QLabel#PageTitle {
    color: #0f2247;
    font-size: 26px;
    font-weight: 800;
}

QLabel#PageSubtitle {
    color: #5f779f;
    font-size: 14px;
}

QLabel#SectionTitle {
    color: #10244a;
    font-size: 20px;
    font-weight: 800;
}

QLabel#MutedText {
    color: #637da9;
    font-size: 13px;
}

QLabel#MutedLabel {
    color: #6b84b1;
    font-size: 12px;
    font-weight: 500;
}

QLabel#MetricValue,
QLabel#ProfileValue {
    color: #122449;
    font-size: 17px;
    font-weight: 700;
}

QFrame#PageCard,
QFrame#StatCard,
QFrame#RiskListCard,
QFrame#EmptyCard,
QFrame#SummaryCard {
    background: #ffffff;
    border: 1px solid #d4dfef;
    border-radius: 13px;
}

QFrame#SoftCard {
    background: #f4f8ff;
    border: 1px solid #d7e2f3;
    border-radius: 10px;
}

QFrame#ProfileRow,
QFrame#StatRow {
    background: transparent;
    border: none;
}

QFrame#PriorityCard {
    background: #fff8eb;
    border: 1px solid #f2ca92;
    border-radius: 12px;
}

QLabel#PriorityTitle {
    color: #c45a0c;
    font-size: 16px;
    font-weight: 800;
}

QLabel#PriorityText {
    color: #c55a0f;
    font-size: 13px;
}

QLabel#StatLabel,
QLabel#StatSubLabel {
    color: #5f789f;
    font-size: 13px;
}

QLabel#StatValue {
    color: #0f2349;
    font-size: 31px;
    font-weight: 800;
}

QLabel#StatValueSmall {
    color: #0f2349;
    font-size: 30px;
    font-weight: 800;
}

QLabel#StatIcon {
    border-radius: 8px;
    background: transparent;
    border: none;
}

QLabel#StatIcon[tone="blue"] {
    background: #e8efff;
}

QLabel#StatIcon[tone="orange"] {
    background: #fff4e7;
}

QLabel#StatIcon[tone="green"] {
    background: #e8faef;
}

QFrame#SearchWrap {
    border-radius: 10px;
    border: 1px solid #d8e3f3;
    background: #f7f9fd;
}

QLineEdit#SearchInput {
    border: none;
    background: transparent;
    padding: 7px 3px;
    color: #122448;
}

QPushButton#FilterButton {
    border-radius: 10px;
    border: 1px solid #d8e2f1;
    background: #ffffff;
    color: #24385f;
    font-size: 14px;
    font-weight: 700;
    padding: 8px 14px;
}

QPushButton#FilterButton:hover {
    background: #f5f8fd;
}

QPushButton#FilterButton:checked {
    border-color: #0f1b3d;
    background: #0f1b3d;
    color: #ffffff;
}

QLabel#RiskId {
    color: #6a83ad;
    font-size: 13px;
    font-weight: 600;
}

QLabel#RiskTitleText {
    color: #10244a;
    font-size: 18px;
    font-weight: 800;
}

QLabel#RiskDescText,
QLabel#RiskMetaText {
    color: #375280;
    font-size: 13px;
}

QLabel#Badge {
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 700;
}

QLabel#Badge[badgeType="status_pending"],
QLabel#Badge[badgeType="status_draft"] {
    background: #e8efff;
    border: 1px solid #2f63e6;
    color: #2f63e6;
}

QLabel#Badge[badgeType="status_assessed"] {
    background: #e9f9ee;
    border: 1px solid #10a055;
    color: #10a055;
}

QLabel#Badge[badgeType="priority_critical"] {
    background: #ffecec;
    border: 1px solid #e04646;
    color: #e04646;
}

QLabel#Badge[badgeType="priority_high"] {
    background: #fff0e7;
    border: 1px solid #ea6e2f;
    color: #ea6e2f;
}

QLabel#Badge[badgeType="priority_medium"] {
    background: #fff7e5;
    border: 1px solid #e6a22d;
    color: #cc7e00;
}

QLabel#Badge[badgeType="priority_low"] {
    background: #ecfbf2;
    border: 1px solid #2fa45e;
    color: #2fa45e;
}

QLabel#Badge[badgeType="level_low"] {
    background: #ecfbf2;
    border: 1px solid #2fa45e;
    color: #2fa45e;
}

QLabel#Badge[badgeType="level_medium"] {
    background: #fff7e5;
    border: 1px solid #e6a22d;
    color: #cc7e00;
}

QLabel#Badge[badgeType="level_high"] {
    background: #fff0e7;
    border: 1px solid #ea6e2f;
    color: #ea6e2f;
}

QLabel#Badge[badgeType="level_critical"] {
    background: #ffecec;
    border: 1px solid #e04646;
    color: #e04646;
}

QPushButton#PrimaryButton,
QPushButton#PrimarySmallButton {
    background: #2a66f5;
    color: #ffffff;
    border: none;
    border-radius: 9px;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 14px;
}

QPushButton#PrimarySmallButton {
    min-width: 94px;
    padding: 7px 12px;
}

QPushButton#PrimaryButton:hover,
QPushButton#PrimarySmallButton:hover {
    background: #1f54d8;
}

QPushButton#PrimaryButton:pressed,
QPushButton#PrimarySmallButton:pressed {
    background: #1a46be;
}

QPushButton#PrimaryButton:disabled,
QPushButton#PrimarySmallButton:disabled {
    background: #9fb7eb;
    color: #edf3ff;
}

QPushButton#OutlineButton {
    background: #ffffff;
    color: #1e355f;
    border: 1px solid #d5e0ef;
    border-radius: 9px;
    padding: 9px 12px;
    font-size: 14px;
    font-weight: 600;
}

QPushButton#OutlineButton:hover {
    background: #f5f8fd;
    border-color: #bfcfe9;
}

QPushButton#OutlineButton:pressed {
    background: #eef3fb;
}

QLabel#SummaryTitle {
    color: #134182;
    font-size: 22px;
    font-weight: 800;
}

QLabel#SummaryText {
    color: #3c6fb8;
    font-size: 13px;
}

QLabel#ProgressValue {
    color: #114191;
    font-size: 30px;
    font-weight: 800;
}

QFrame#ProgressTrack {
    background: #c8dbfb;
    border-radius: 4px;
}

QFrame#ProgressFill {
    background: #2a66f5;
    border-radius: 4px;
}

QLineEdit,
QTextEdit,
QSpinBox {
    background: #f5f8fd;
    border: 1px solid #d5e0ef;
    border-radius: 9px;
    padding: 8px 10px;
    color: #122448;
}

QLineEdit:focus,
QTextEdit:focus,
QSpinBox:focus {
    background: #ffffff;
    border: 1px solid #4d79f1;
}

QLineEdit:disabled,
QTextEdit:disabled,
QSpinBox:disabled {
    background: #eff4fc;
    color: #8397bf;
    border-color: #d7e0ef;
}

QCheckBox {
    color: #1a2e55;
    font-size: 14px;
}

QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    background: #e7eef8;
    width: 10px;
    margin: 2px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #aebfdd;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar:horizontal {
    background: #e7eef8;
    height: 10px;
    margin: 2px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #aebfdd;
    border-radius: 5px;
    min-width: 24px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
    height: 0px;
}
"""
