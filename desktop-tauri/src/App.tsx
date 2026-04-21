import { useEffect, useRef, useState } from "react";
import { getMe, getRisk, isServerOfflineErrorMessage, listAssessments, listRisks, login, registerExpert } from "./lib/api";
import type { DraftAssessment, ExpertUser, Risk, SubmittedAssessment, ThemeMode } from "./lib/types";
import { LoginScreen } from "./components/LoginScreen";
import { Sidebar, type Page } from "./components/Sidebar";
import { AssignedRisksPage } from "./components/AssignedRisksPage";
import { AssessmentsPage } from "./components/AssessmentsPage";
import { ProfilePage } from "./components/ProfilePage";
import { RiskDetail } from "./components/RiskDetail";
import { Alert, ServerOfflineNotice } from "./components/shared";

const TOKEN_KEY = "riskguard.tauri.token";
const EMAIL_KEY = "riskguard.tauri.email";
const DRAFTS_KEY = "riskguard.tauri.drafts";
const THEME_KEY = "riskguard.tauri.theme";

function loadDrafts(): Record<string, DraftAssessment> {
  try {
    return JSON.parse(localStorage.getItem(DRAFTS_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveDrafts(drafts: Record<string, DraftAssessment>) {
  localStorage.setItem(DRAFTS_KEY, JSON.stringify(drafts));
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [rememberedEmail, setRememberedEmail] = useState(() => localStorage.getItem(EMAIL_KEY) || "");
  const [user, setUser] = useState<ExpertUser | null>(null);
  const [page, setPage] = useState<Page>("risks");
  const [risks, setRisks] = useState<Risk[]>([]);
  const [assessments, setAssessments] = useState<SubmittedAssessment[]>([]);
  const [drafts, setDrafts] = useState<Record<string, DraftAssessment>>(() => loadDrafts());
  const [selectedRisk, setSelectedRisk] = useState<Risk | null>(null);
  const [loading, setLoading] = useState(Boolean(token));
  const [reconnecting, setReconnecting] = useState(false);
  const syncInFlightRef = useRef(false);
  const [error, setError] = useState("");
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem(THEME_KEY);
    return saved === "night" ? "night" : "day";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = themeMode;
    localStorage.setItem(THEME_KEY, themeMode);
  }, [themeMode]);

  useEffect(() => {
    if (!token) return;
    void bootstrap(token);
  }, []);

  async function bootstrap(nextToken: string) {
    setLoading(true);
    setError("");
    try {
      const [nextUser, nextRisks, nextAssessments] = await Promise.all([
        getMe(nextToken),
        listRisks(nextToken),
        listAssessments(nextToken),
      ]);
      setUser(nextUser);
      setRisks(nextRisks);
      setAssessments(nextAssessments);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить данные.");
      localStorage.removeItem(TOKEN_KEY);
      setToken("");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  async function refreshData(nextToken = token) {
    if (!nextToken) return;
    const [nextRisks, nextAssessments] = await Promise.all([listRisks(nextToken), listAssessments(nextToken)]);
    setRisks(nextRisks);
    setAssessments(nextAssessments);
  }

  async function syncDataSilently(nextToken = token) {
    if (!nextToken || syncInFlightRef.current) return;
    syncInFlightRef.current = true;
    try {
      await refreshData(nextToken);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обновить данные.");
    } finally {
      syncInFlightRef.current = false;
    }
  }

  async function handleLogin(email: string, password: string, remember: boolean) {
    setError("");
    const nextToken = await login(email, password);
    setToken(nextToken);
    setRememberedEmail(email);
    if (remember) {
      localStorage.setItem(TOKEN_KEY, nextToken);
      localStorage.setItem(EMAIL_KEY, email);
    } else {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.setItem(EMAIL_KEY, email);
    }
    await bootstrap(nextToken);
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    setToken("");
    setUser(null);
    setSelectedRisk(null);
  }

  function handlePageChange(nextPage: Page) {
    setSelectedRisk(null);
    setPage(nextPage);
    if (nextPage === "risks") {
      void syncDataSilently();
    }
  }

  function updateDraft(riskId: string, draft: DraftAssessment | null) {
    const next = { ...drafts };
    if (draft) {
      next[riskId] = draft;
    } else {
      delete next[riskId];
    }
    setDrafts(next);
    saveDrafts(next);
  }

  async function reconnectServer() {
    setReconnecting(true);
    try {
      await refreshData();
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось подключиться к серверу.");
    } finally {
      setReconnecting(false);
    }
  }

  useEffect(() => {
    if (!token || !user) return;
    const intervalId = window.setInterval(() => {
      void syncDataSilently(token);
    }, 8000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [token, user]);

  if (!token || !user) {
    return (
      <LoginScreen
        loading={loading}
        initialEmail={rememberedEmail}
        error={error}
        onLogin={handleLogin}
        onRegister={registerExpert}
      />
    );
  }

  return (
    <div className="app-shell">
      <Sidebar user={user} page={page} onPage={handlePageChange} onLogout={logout} />
      <main className="content">
        {error ? (
          isServerOfflineErrorMessage(error) ? (
            <ServerOfflineNotice
              className="mb-5"
              onRetry={reconnectServer}
              retrying={reconnecting}
            />
          ) : (
            <Alert text={error} onClose={() => setError("")} />
          )
        ) : null}
        <div className="page-enter" key={selectedRisk ? selectedRisk.id : page}>
          {selectedRisk ? (
            <RiskDetail
              risk={selectedRisk}
              draft={drafts[selectedRisk.id]}
              token={token}
              onBack={() => setSelectedRisk(null)}
              onDraft={updateDraft}
              onSubmit={async () => {
                await refreshData();
                setSelectedRisk(null);
              }}
            />
          ) : page === "risks" ? (
            <AssignedRisksPage
              risks={risks}
              drafts={drafts}
              onOpen={async (riskId) => {
                setError("");
                try {
                  setSelectedRisk(await getRisk(token, riskId));
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Не удалось открыть риск.");
                }
              }}
            />
          ) : page === "assessments" ? (
            <AssessmentsPage assessments={assessments} />
          ) : (
            <ProfilePage
              user={user}
              risks={risks}
              assessments={assessments}
              themeMode={themeMode}
              onThemeChange={setThemeMode}
            />
          )}
        </div>
      </main>
    </div>
  );
}
