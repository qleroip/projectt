from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from riskguard_desktop.repository import ExpertRepository
from riskguard_desktop.session import SessionStore
from riskguard_desktop.ui.login_window import LoginWindow
from riskguard_desktop.ui.main_window import MainWindow
from riskguard_desktop.ui.theme import APP_STYLESHEET


class DesktopController:
    def __init__(self, app: QApplication) -> None:
        self._app = app
        self._repository = ExpertRepository()
        self._session = SessionStore()
        self._login_window: LoginWindow | None = None
        self._main_window: MainWindow | None = None

    def start(self) -> None:
        remembered_email = self._session.get_remembered_user() or ""
        saved_token = self._session.get_saved_token()
        if remembered_email and saved_token and self._repository.restore_session(saved_token):
            self._open_main(remembered_email)
            return
        self._open_login(remembered_email)

    def _open_login(self, remembered_email: str) -> None:
        self._login_window = LoginWindow(
            repository=self._repository,
            session_store=self._session,
            remembered_email=remembered_email,
        )
        self._login_window.login_success.connect(self._open_main)
        self._login_window.show()

    def _open_main(self, email: str) -> None:
        if self._login_window:
            self._login_window.close()
            self._login_window = None
        self._main_window = MainWindow(
            repository=self._repository,
            session_store=self._session,
            email=email,
            on_logout=self._handle_logout,
        )
        self._main_window.show()

    def _handle_logout(self) -> None:
        self._session.clear_token()
        self._open_login(self._session.get_remembered_user() or "")


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    controller = DesktopController(app)
    controller.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
