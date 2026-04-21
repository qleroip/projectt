import type { CurrentUser, IncidentPayload, IncidentResponse } from "./types";

const DEFAULT_API_BASE = "http://100.127.19.75:5000";
let currentApiBase = DEFAULT_API_BASE;

export class ApiError extends Error {
  constructor(message: string, public status = 0) {
    super(message);
  }
}

function normalizeApiBase(value: string) {
  let next = value.trim().replace(/\s+/g, "");
  if (!next) return DEFAULT_API_BASE;
  if (!/^https?:\/\//i.test(next)) {
    next = `http://${next}`;
  }
  return next.replace(/\/+$/, "");
}

export function defaultApiBaseUrl() {
  return normalizeApiBase(DEFAULT_API_BASE);
}

export function setApiBaseUrl(value: string) {
  currentApiBase = normalizeApiBase(value);
}

export function apiBaseUrl() {
  return normalizeApiBase(currentApiBase);
}

function mapError(raw: string) {
  const messages: Record<string, string> = {
    "Invalid credentials": "Неверный email или пароль.",
    "Account awaits administrator approval":
      "Заявка еще не одобрена администратором.",
    Forbidden: "Недостаточно прав для этого действия.",
    "Not found": "Данные не найдены.",
    "Missing token": "Сессия истекла. Выполните вход снова.",
    "Invalid token": "Сессия истекла. Выполните вход снова.",
    "User already exists": "Пользователь с таким email уже существует.",
    "full_name, email and password are required":
      "Заполните ФИО, email и пароль.",
  };
  return messages[raw] || raw || "Ошибка API";
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token = "",
): Promise<T> {
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
  } catch (error) {
    const reason = error instanceof Error ? ` (${error.message})` : "";
    throw new ApiError(
      `Нет подключения к серверу (${apiBaseUrl()}). Запустите web/app.py и проверьте API-адрес.${reason}`,
    );
  }

  const raw = await response.text();
  let data: any = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = { message: raw };
    }
  }
  if (!response.ok) {
    throw new ApiError(mapError(data?.error || data?.message), response.status);
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

export async function registerWorker(
  fullName: string,
  email: string,
  password: string,
) {
  return request<{ message?: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      full_name: fullName.trim(),
      email: email.trim().toLowerCase(),
      password,
      role: "worker",
    }),
  });
}

export async function getMe(token: string) {
  return request<CurrentUser>("/api/me", {}, token);
}

export async function createIncident(token: string, payload: IncidentPayload) {
  return request<IncidentResponse>(
    "/api/incidents",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function pingServer() {
  return request<{ ok: boolean; message: string }>("/api/ping");
}
