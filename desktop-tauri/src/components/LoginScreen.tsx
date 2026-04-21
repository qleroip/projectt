import { type FormEvent, useState } from "react";
import { Button, Card, Input, Spinner } from "./ui";
import { cn } from "../lib/utils";
import { ServerOfflineNotice } from "./shared";
import { isServerOfflineErrorMessage } from "../lib/api";

export function LoginScreen({
  loading,
  initialEmail,
  error,
  onLogin,
  onRegister,
}: {
  loading: boolean;
  initialEmail: string;
  error: string;
  onLogin: (email: string, password: string, remember: boolean) => Promise<void>;
  onRegister: (fullName: string, email: string, password: string) => Promise<{ message: string }>;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [remember, setRemember] = useState(Boolean(initialEmail));
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState("");
  const [localError, setLocalError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const activeError = localError || error;
  const serverOffline = isServerOfflineErrorMessage(activeError);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLocalError("");
    setMessage("");
    setSubmitting(true);
    try {
      if (mode === "register") {
        if (!fullName.trim() || !email.trim() || password.length < 6) {
          throw new Error("Заполните ФИО, email и пароль не короче 6 символов.");
        }
        const result = await onRegister(fullName, email, password);
        setMessage(result.message || "Заявка отправлена администратору.");
        setMode("login");
      } else {
        await onLogin(email, password, remember);
      }
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Ошибка входа.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell flex min-h-screen items-center justify-center px-6">
      <Card className="auth-card w-full max-w-[520px] p-8">
        <form className="space-y-5" onSubmit={submit}>
          <div className="auth-brand flex items-center justify-center gap-3">
            <div className="auth-brand-logo flex h-20 w-20 items-center justify-center rounded-[22px] border border-primary/15 bg-white/80 shadow-[0_16px_44px_rgba(18,44,88,0.18)]">
              <img className="h-14 w-14 object-contain" src="/guard.png" alt="RiskGuard" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-normal text-foreground">RiskGuard</h1>
              <p className="text-sm text-muted-foreground">Экспертная панель</p>
            </div>
          </div>

          <div className="auth-tabs grid grid-cols-2 rounded-md bg-muted p-1">
            <button
              className={cn("rounded-md px-4 py-2 text-sm font-bold", mode === "login" && "bg-card shadow-sm")}
              type="button"
              onClick={() => setMode("login")}
            >
              Вход
            </button>
            <button
              className={cn("rounded-md px-4 py-2 text-sm font-bold", mode === "register" && "bg-card shadow-sm")}
              type="button"
              onClick={() => setMode("register")}
            >
              Запрос доступа
            </button>
          </div>

          <div className="auth-mode" key={mode}>
            <div className="text-center">
              <h2 className="text-2xl font-extrabold text-foreground">
                {mode === "login" ? "Вход эксперта" : "Заявка эксперта"}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {mode === "login" ? "Доступ только для назначенных экспертов" : "Администратор одобрит доступ в веб-панели"}
              </p>
            </div>

            {mode === "register" ? (
              <label className="block space-y-2 text-sm font-semibold">
                <span>ФИО</span>
                <Input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Иван Петров" />
              </label>
            ) : null}

            <label className="block space-y-2 text-sm font-semibold">
              <span>Email</span>
              <Input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@company.com" />
            </label>

            <label className="block space-y-2 text-sm font-semibold">
              <span>Пароль</span>
              <Input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Введите пароль"
                type={showPassword ? "text" : "password"}
              />
            </label>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <label className="flex items-center gap-2">
              <input checked={remember} onChange={(event) => setRemember(event.target.checked)} type="checkbox" />
              Запомнить меня
            </label>
            <label className="flex items-center gap-2">
              <input checked={showPassword} onChange={(event) => setShowPassword(event.target.checked)} type="checkbox" />
              Показать пароль
            </label>
          </div>

          {message ? <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</p> : null}
          {serverOffline ? (
            <ServerOfflineNotice className="border-orange-200 bg-orange-50/70 p-4 shadow-none" />
          ) : null}
          {!serverOffline && activeError ? (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">
              {activeError}
            </p>
          ) : null}

          <Button className="w-full" disabled={loading || submitting} size="lg" type="submit">
            {loading || submitting ? (
              <span className="inline-flex items-center gap-2">
                <Spinner className="border-primary-foreground/40" />
                {mode === "login" ? "Входим..." : "Отправляем..."}
              </span>
            ) : mode === "login" ? (
              "Войти"
            ) : (
              "Отправить заявку"
            )}
          </Button>
        </form>
      </Card>
    </main>
  );
}
