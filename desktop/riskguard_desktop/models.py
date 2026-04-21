from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

RiskStatus = Literal["pending", "draft", "assessed"]
RiskLevel = Literal["low", "medium", "high", "critical"]


def calculate_risk_level(probability: int, impact: int) -> RiskLevel:
    score = probability * impact
    if score >= 20:
        return "critical"
    if score >= 12:
        return "high"
    if score >= 6:
        return "medium"
    return "low"


def risk_level_label(level: RiskLevel) -> str:
    return {
        "low": "Низкий",
        "medium": "Средний",
        "high": "Высокий",
        "critical": "Критический",
    }[level]


def risk_status_label(status: RiskStatus) -> str:
    return {
        "pending": "Ожидает оценки",
        "draft": "Черновик",
        "assessed": "Оценен",
    }[status]


@dataclass(slots=True)
class Assessment:
    risk_id: str
    probability: int
    impact: int
    recommendation: str
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    submitted: bool = False

    @property
    def level(self) -> RiskLevel:
        return calculate_risk_level(self.probability, self.impact)


@dataclass(slots=True)
class Risk:
    id: str
    title: str
    description: str
    category: str
    owner: str
    priority: int
    assigned_date: str
    status: RiskStatus = "pending"
    incidents: list[str] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)
    assessment: Assessment | None = None


@dataclass(slots=True)
class ExpertUser:
    full_name: str
    email: str
    role: str
    joined_at: str
