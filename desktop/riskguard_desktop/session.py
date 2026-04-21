from __future__ import annotations

from PySide6.QtCore import QSettings


class SessionStore:
    def __init__(self) -> None:
        self._settings = QSettings("RiskGuard", "ExpertDesktop")

    def get_remembered_user(self) -> str | None:
        remember = self._settings.value("auth/remember", False, bool)
        email = self._settings.value("auth/email", "", str).strip()
        if remember and email:
            return email
        return None

    def get_saved_token(self) -> str | None:
        remember = self._settings.value("auth/remember", False, bool)
        token = self._settings.value("auth/token", "", str).strip()
        if remember and token:
            return token
        return None

    def save_login(self, email: str, remember: bool, token: str = "") -> None:
        self._settings.setValue("auth/remember", remember)
        if remember:
            self._settings.setValue("auth/email", email.strip().lower())
            if token.strip():
                self._settings.setValue("auth/token", token.strip())
            else:
                self._settings.remove("auth/token")
        else:
            self._settings.remove("auth/email")
            self._settings.remove("auth/token")

    def clear_token(self) -> None:
        self._settings.remove("auth/token")

    def clear(self) -> None:
        self._settings.setValue("auth/remember", False)
        self._settings.remove("auth/email")
        self._settings.remove("auth/token")
