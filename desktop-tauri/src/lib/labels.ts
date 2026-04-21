import type { RiskLevel, RiskStatus } from "./types";

export const roleLabels = {
  admin: "Администратор",
  expert: "Эксперт",
  risk_manager: "Риск-менеджер",
  worker: "Работник",
};

export const statusLabels: Record<RiskStatus, string> = {
  pending: "Ожидает оценки",
  draft: "Черновик",
  assessed: "Оценен",
};

export const levelLabels: Record<RiskLevel, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  critical: "Критический",
};

export function riskLevel(probability: number, impact: number): RiskLevel {
  const score = probability * impact;
  if (score >= 20) return "critical";
  if (score >= 12) return "high";
  if (score >= 6) return "medium";
  return "low";
}

type BadgeTone = "blue" | "green" | "orange" | "red" | "gray";

export function statusVariant(status: RiskStatus): BadgeTone {
  if (status === "assessed") return "green";
  if (status === "draft") return "gray";
  return "blue";
}

export function priorityVariant(priority: number): BadgeTone {
  if (priority >= 5) return "red";
  if (priority >= 4) return "orange";
  if (priority >= 3) return "orange";
  return "green";
}

export function priorityLabel(priority: number) {
  if (priority >= 5) return "Критический";
  if (priority >= 4) return "Высокий";
  if (priority >= 3) return "Средний";
  return "Низкий";
}

export function severityVariant(level: string | RiskLevel): BadgeTone {
  const normalized = level.toLowerCase();
  if (normalized === "critical") return "red";
  if (normalized === "high") return "orange";
  if (normalized === "medium") return "orange";
  return "green";
}

export function formatDate(date: string) {
  if (!date) return "-";
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return date;
  return parsed.toLocaleDateString("ru-RU");
}
