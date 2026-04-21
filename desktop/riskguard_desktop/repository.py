from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import os

import requests

from .models import Assessment, ExpertUser, Risk


class ExpertRepository:
    """HTTP data layer for desktop client."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or os.getenv("RISKGUARD_API_URL") or "http://127.0.0.1:5000").rstrip("/")
        self._token = ""
        self._expert: ExpertUser | None = None
        self._risks_cache: dict[str, Risk] = {}
        self._assessment_cache: list[tuple[Risk, Assessment]] = []
        self._drafts: dict[str, Assessment] = {}
        self.last_error = ""

    @property
    def access_token(self) -> str:
        return self._token

    def authenticate(self, email: str, password: str) -> bool:
        self.last_error = ""
        try:
            response = requests.post(
                f"{self._base_url}/auth/login",
                json={"email": email.strip().lower(), "password": password},
                timeout=12,
            )
        except requests.RequestException:
            self.last_error = "Нет подключения к веб-серверу. Убедитесь, что web запущен."
            return False

        if response.status_code != 200:
            self.last_error = self._api_error(response, default="Ошибка входа")
            return False

        token = str((response.json() or {}).get("access_token", "")).strip()
        if not token:
            self.last_error = "Сервер не вернул токен доступа."
            return False
        return self.restore_session(token)

    def restore_session(self, token: str) -> bool:
        self.last_error = ""
        self._token = token
        user = self._fetch_me()
        if not user:
            self._token = ""
            return False
        self._expert = user
        self._refresh_risks()
        self._refresh_assessments()
        return True

    def register_expert(self, full_name: str, email: str, password: str) -> tuple[bool, str]:
        try:
            response = requests.post(
                f"{self._base_url}/auth/register",
                json={
                    "full_name": full_name.strip(),
                    "email": email.strip().lower(),
                    "password": password,
                    "role": "expert",
                },
                timeout=12,
            )
        except requests.RequestException:
            return False, "Нет подключения к веб-серверу. Убедитесь, что web запущен."

        if response.status_code != 201:
            return False, self._api_error(response, default="Не удалось отправить заявку")

        message = str((response.json() or {}).get("message", "")).strip()
        return True, message or "Заявка отправлена на одобрение администратором."

    def is_known_user(self, email: str) -> bool:
        if not self._expert:
            return False
        return self._expert.email == email.strip().lower()

    def get_expert(self) -> ExpertUser:
        if self._expert:
            return deepcopy(self._expert)
        fallback = ExpertUser(
            full_name="Эксперт",
            email="",
            role="Эксперт",
            joined_at="",
        )
        return fallback

    def list_risks(self, search: str = "", status_filter: str = "all") -> list[Risk]:
        if not self._risks_cache:
            self._refresh_risks()

        query = search.strip().lower()
        risks = list(self._risks_cache.values())
        result: list[Risk] = []
        for risk in risks:
            local = self._apply_draft_overlay(deepcopy(risk))
            if status_filter != "all" and local.status != status_filter:
                continue
            if query and query not in local.id.lower() and query not in local.title.lower():
                continue
            result.append(local)
        return sorted(result, key=lambda item: item.id)

    def get_risk(self, risk_id: str) -> Risk | None:
        response = self._request("GET", f"/api/expert/risks/{risk_id}")
        if not response:
            return self._apply_draft_overlay(deepcopy(self._risks_cache.get(risk_id))) if risk_id in self._risks_cache else None
        risk = self._risk_from_api(response)
        self._risks_cache[risk.id] = deepcopy(risk)
        return self._apply_draft_overlay(risk)

    def save_draft(self, risk_id: str, probability: int, impact: int, recommendation: str) -> None:
        draft = Assessment(
            risk_id=risk_id,
            probability=probability,
            impact=impact,
            recommendation=recommendation.strip(),
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            submitted=False,
        )
        self._drafts[risk_id] = draft

    def submit_assessment(self, risk_id: str, probability: int, impact: int, recommendation: str) -> None:
        payload = {
            "probability": probability,
            "impact_score": impact,
            "recommendation": recommendation.strip(),
        }
        response = self._request("POST", f"/api/risks/{risk_id}/assessments", json=payload)
        if response is None:
            raise RuntimeError(self.last_error or "Не удалось отправить оценку")
        self._drafts.pop(risk_id, None)
        self._refresh_risks()
        self._refresh_assessments()

    def list_submitted_assessments(self) -> list[tuple[Risk, Assessment]]:
        if not self._assessment_cache:
            self._refresh_assessments()
        return [(deepcopy(risk), deepcopy(assessment)) for risk, assessment in self._assessment_cache]

    def get_stats(self) -> dict[str, int]:
        risks = self.list_risks()
        total = len(risks)
        pending = len([item for item in risks if item.status == "pending"])
        drafts = len([item for item in risks if item.status == "draft"])
        assessed = len([item for item in risks if item.status == "assessed"])
        return {"total": total, "pending": pending, "draft": drafts, "assessed": assessed}

    def _fetch_me(self) -> ExpertUser | None:
        data = self._request("GET", "/api/me")
        if not data:
            return None
        role = str(data.get("role", ""))
        if role not in {"expert", "admin"}:
            self.last_error = "Desktop доступен только эксперту и администратору."
            return None
        return ExpertUser(
            full_name=str(data.get("full_name", "Эксперт")),
            email=str(data.get("email", "")),
            role=self._role_label(role or "expert"),
            joined_at=str(data.get("joined_at", "")),
        )

    def _refresh_risks(self) -> None:
        data = self._request("GET", "/api/expert/risks")
        if data is None:
            return
        risks = [self._risk_from_api(item) for item in data]
        self._risks_cache = {risk.id: risk for risk in risks}

    def _refresh_assessments(self) -> None:
        data = self._request("GET", "/api/expert/assessments")
        if data is None:
            return
        result: list[tuple[Risk, Assessment]] = []
        for item in data:
            risk = Risk(
                id=str(item.get("risk_id", "")),
                title=str(item.get("risk_title", "")),
                description="",
                category="",
                owner="",
                priority=0,
                assigned_date=str(item.get("date", "")),
                status="assessed",
            )
            assessment = Assessment(
                risk_id=risk.id,
                probability=int(item.get("probability", 1)),
                impact=int(item.get("impact_score", 1)),
                recommendation=str(item.get("recommendation", "")),
                created_at=str(item.get("date", "")),
                submitted=True,
            )
            result.append((risk, assessment))
        self._assessment_cache = result

    def _risk_from_api(self, item: dict) -> Risk:
        risk_id = str(item.get("id", ""))
        assessment = self._assessment_from_api(item.get("my_assessment"))
        incidents = [str(text) for text in (item.get("incidents") or [])]
        mitigations = [str(text) for text in (item.get("mitigations") or [])]
        return Risk(
            id=risk_id,
            title=str(item.get("title", "")),
            description=str(item.get("description", "")),
            category=str(item.get("category", "")),
            owner=str(item.get("owner", "")),
            priority=int(item.get("priority", self._priority_by_level(str(item.get("impact_level", ""))))),
            assigned_date=str(item.get("assigned_date", "")),
            status="assessed" if assessment else "pending",
            incidents=incidents,
            mitigations=mitigations,
            assessment=assessment,
        )

    @staticmethod
    def _assessment_from_api(item: dict | None) -> Assessment | None:
        if not item:
            return None
        return Assessment(
            risk_id=str(item.get("risk_id", "")),
            probability=int(item.get("probability", 1)),
            impact=int(item.get("impact_score", 1)),
            recommendation=str(item.get("recommendation", "")),
            created_at=str(item.get("date", "")),
            submitted=True,
        )

    def _apply_draft_overlay(self, risk: Risk | None) -> Risk | None:
        if risk is None:
            return None
        draft = self._drafts.get(risk.id)
        if draft and risk.status != "assessed":
            risk.status = "draft"
            risk.assessment = deepcopy(draft)
        return risk

    def _request(self, method: str, path: str, json: dict | None = None) -> dict | list | None:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            response = requests.request(
                method=method,
                url=f"{self._base_url}{path}",
                headers=headers,
                json=json,
                timeout=12,
            )
        except requests.RequestException:
            self.last_error = "Нет подключения к веб-серверу. Убедитесь, что web запущен."
            return None

        if response.status_code >= 400:
            self.last_error = self._api_error(response, default="Ошибка API")
            if response.status_code == 401:
                self._token = ""
            return None

        if not response.content:
            return {}
        return response.json()

    def _api_error(self, response: requests.Response, default: str) -> str:
        try:
            payload = response.json() or {}
        except ValueError:
            return default
        raw = str(payload.get("error") or payload.get("message") or default)
        mapping = {
            "Invalid credentials": "Неверный email или пароль.",
            "Account awaits administrator approval": "Аккаунт ожидает одобрения администратором.",
            "User already exists": "Пользователь с таким email уже существует.",
            "Missing token": "Сессия истекла. Выполните вход снова.",
            "Invalid token": "Сессия истекла. Выполните вход снова.",
            "Forbidden": "Недостаточно прав для этого действия.",
            "Not found": "Запись не найдена.",
        }
        return mapping.get(raw, raw)

    @staticmethod
    def _priority_by_level(level: str) -> int:
        return {
            "Critical": 5,
            "High": 4,
            "Medium": 3,
            "Low": 2,
        }.get(level, 3)

    @staticmethod
    def _role_label(role: str) -> str:
        return {
            "admin": "Администратор",
            "risk_manager": "Риск-менеджер",
            "expert": "Эксперт",
            "worker": "Работник",
        }.get(role, role)
