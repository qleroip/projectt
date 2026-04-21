import AsyncStorage from "@react-native-async-storage/async-storage";
import type { CurrentUser, IncidentHistoryItem } from "./types";

const TOKEN_KEY = "riskguard.apk.token";
const USER_KEY = "riskguard.apk.user";
const INCIDENTS_KEY = "riskguard.apk.history";
const API_BASE_KEY = "riskguard.apk.api_base";

export async function saveSession(token: string, user: CurrentUser) {
  await AsyncStorage.multiSet([
    [TOKEN_KEY, token],
    [USER_KEY, JSON.stringify(user)],
  ]);
}

export async function loadSession() {
  const [token, userRaw] = await AsyncStorage.multiGet([TOKEN_KEY, USER_KEY]);
  const tokenValue = token[1] || "";
  const userValue = userRaw[1] || "";
  if (!tokenValue || !userValue) return null;

  try {
    return { token: tokenValue, user: JSON.parse(userValue) as CurrentUser };
  } catch {
    return null;
  }
}

export async function clearSession() {
  await AsyncStorage.multiRemove([TOKEN_KEY, USER_KEY]);
}

export async function loadIncidentHistory() {
  const raw = await AsyncStorage.getItem(INCIDENTS_KEY);
  if (!raw) return [] as IncidentHistoryItem[];
  try {
    return JSON.parse(raw) as IncidentHistoryItem[];
  } catch {
    return [] as IncidentHistoryItem[];
  }
}

export async function saveIncidentHistory(items: IncidentHistoryItem[]) {
  await AsyncStorage.setItem(INCIDENTS_KEY, JSON.stringify(items.slice(0, 20)));
}

export async function loadApiBase() {
  return (await AsyncStorage.getItem(API_BASE_KEY)) || "";
}

export async function saveApiBase(url: string) {
  await AsyncStorage.setItem(API_BASE_KEY, url.trim());
}
