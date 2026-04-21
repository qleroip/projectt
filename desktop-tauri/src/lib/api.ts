import type { ExpertUser, Risk, SubmittedAssessment } from "./types";

const DEFAULT_API_BASE = "http://127.0.0.1:5000";
export const SERVER_OFFLINE_MESSAGE = "Нет подключения к веб-серверу. Убедитесь, что web запущен.";

export class ApiError extends Error {
  constructor(message: string, public status = 0) {
    super(message);
  }
}

export function apiBaseUrl() {
  return (import.meta.env.VITE_RISKGUARD_API_URL || DEFAULT_API_BASE).replace(/\/$/, "");
}

export function isServerOfflineErrorMessage(message: string) {
  return message.includes("Нет подключения к веб-серверу");
}

function translateApiError(raw: string) {
  const messages: Record<string, string> = {
    "Invalid credentials": "Неверный email или пароль.",
    "Account awaits administrator approval": "Аккаунт ожидает одобрения администратором.",
    "User already exists": "Пользователь с таким email уже существует.",
    "Missing token": "Сессия истекла. Выполните вход снова.",
    "Invalid token": "Сессия истекла. Выполните вход снова.",
    Forbidden: "Недостаточно прав для этого действия.",
    "Not found": "Запись не найдена.",
  };
  return messages[raw] || raw || "Ошибка API";
}

async function request<T>(path: string, options: RequestInit = {}, token = ""): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(SERVER_OFFLINE_MESSAGE);
  }

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new ApiError(translateApiError(data?.error || data?.message), response.status);
  }
  return data as T;
}

export async function login(email: string, password: string) {
  const data = await request<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });
  if (!data.access_token) {
    throw new ApiError("Сервер не вернул токен доступа.");
  }
  return data.access_token;
}

export async function registerExpert(fullName: string, email: string, password: string) {
  return request<{ message: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      full_name: fullName.trim(),
      email: email.trim().toLowerCase(),
      password,
      role: "expert",
    }),
  });
}

export async function getMe(token: string) {
  const user = await request<ExpertUser>("/api/me", {}, token);
  if (user.role !== "expert" && user.role !== "admin") {
    throw new ApiError("Desktop доступен только эксперту и администратору.");
  }
  return user;
}

export async function listRisks(token: string) {
  return request<Risk[]>("/api/expert/risks", {}, token).then((items) => items.map(normalizeRisk));
}

export async function getRisk(token: string, riskId: string) {
  return request<Risk>(`/api/expert/risks/${riskId}`, {}, token).then(normalizeRisk);
}

export async function listAssessments(token: string) {
  return request<SubmittedAssessment[]>("/api/expert/assessments", {}, token);
}

export async function submitAssessment(
  token: string,
  riskId: string,
  probability: number,
  impactScore: number,
  recommendation: string,
) {
  return request<{ id: number; severity_level: string }>(
    `/api/risks/${riskId}/assessments`,
    {
      method: "POST",
      body: JSON.stringify({
        probability,
        impact_score: impactScore,
        recommendation: recommendation.trim(),
      }),
    },
    token,
  );
}

function normalizeRisk(item: Risk): Risk {
  return {
    ...item,
    status: item.my_assessment ? "assessed" : "pending",
    priority: Number(item.priority || priorityByImpact(item.impact_level || "")),
  };
}

function priorityByImpact(level: string) {
  const scores: Record<string, number> = {
    Critical: 5,
    High: 4,
    Medium: 3,
    Low: 2,
  };
  return scores[level] || 3;
}
