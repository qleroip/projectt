import type { ExpertUser, Risk, SubmittedAssessment, ThemeMode } from "../lib/types";
import { formatDate, roleLabels } from "../lib/labels";
import { Card } from "./ui";
import { Metric, PageHeader } from "./shared";
import { cn } from "../lib/utils";

export function ProfilePage({
  user,
  risks,
  assessments,
  themeMode,
  onThemeChange,
}: {
  user: ExpertUser;
  risks: Risk[];
  assessments: SubmittedAssessment[];
  themeMode: ThemeMode;
  onThemeChange: (mode: ThemeMode) => void;
}) {
  const percent = risks.length ? Math.round((assessments.length / risks.length) * 100) : 0;
  const initials = user.full_name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
  return (
    <section className="space-y-6">
      <PageHeader title="Профиль" subtitle="Информация о вашем аккаунте эксперта" />
      <div className="grid grid-cols-[minmax(0,2fr)_minmax(340px,1fr)] gap-5">
        <Card className="card-lift p-6">
          <h3 className="text-xl font-extrabold">Личные данные</h3>
          <div className="mt-4 flex items-center gap-4 rounded-lg border border-primary/15 bg-primary/5 p-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary text-lg font-extrabold text-primary-foreground">
              {initials || "RG"}
            </div>
            <div>
              <div className="text-lg font-extrabold">{user.full_name}</div>
              <div className="text-sm text-muted-foreground">{roleLabels[user.role]}</div>
            </div>
          </div>
          <div className="mt-5 grid gap-5">
            <ProfileRow label="Имя" value={user.full_name} />
            <ProfileRow label="Email" value={user.email} />
            <ProfileRow label="Роль" value={roleLabels[user.role]} />
            <ProfileRow label="Дата подключения" value={formatDate(user.joined_at)} />
          </div>
        </Card>
        <div className="space-y-5">
          <Card className="card-lift p-6">
            <h3 className="text-xl font-extrabold">Статистика</h3>
            <div className="mt-5 space-y-5">
              <Metric label="Назначенных рисков" value={String(risks.length)} />
              <Metric label="Отправленных оценок" value={String(assessments.length)} />
              <div className="theme-panel rounded-md border p-4">
                <div className="text-sm font-semibold text-muted-foreground">Процент завершения</div>
                <div className="mt-2 text-3xl font-extrabold text-primary">{percent}%</div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-primary/20">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
                </div>
              </div>
            </div>
          </Card>
          <Card className="card-lift p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xl font-extrabold">Оформление</div>
                <p className="mt-1 text-sm text-muted-foreground">Переключение рабочей темы интерфейса</p>
              </div>
              <div className="theme-switch" role="group" aria-label="Тема интерфейса">
                <button
                  className={cn("theme-switch-button", themeMode === "day" && "active")}
                  onClick={() => onThemeChange("day")}
                  type="button"
                >
                  День
                </button>
                <button
                  className={cn("theme-switch-button", themeMode === "night" && "active")}
                  onClick={() => onThemeChange("night")}
                  type="button"
                >
                  Ночь
                </button>
              </div>
            </div>
          </Card>
          <Card className="card-lift p-5">
            <div className="text-xl font-extrabold">RiskGuard</div>
            <p className="mt-1 text-sm text-muted-foreground">Desktop-версия для экспертов</p>
          </Card>
        </div>
      </div>
    </section>
  );
}

function ProfileRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border/70 bg-muted/45 px-4 py-3">
      <div className="text-sm font-semibold text-muted-foreground">{label}</div>
      <div className="mt-1 text-base font-extrabold">{value || "-"}</div>
    </div>
  );
}
