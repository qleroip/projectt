import { cn } from "../lib/utils";
import { Button, Card, Spinner } from "./ui";

export function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header>
      <h1 className="text-4xl font-extrabold tracking-normal text-foreground">{title}</h1>
      <p className="mt-2 text-base text-muted-foreground">{subtitle}</p>
    </header>
  );
}

export function StatCard({
  label,
  value,
  sublabel,
  tone = "blue",
}: {
  label: string;
  value: number;
  sublabel: string;
  tone?: "blue" | "orange" | "green";
}) {
  const toneClass = {
    blue: "bg-blue-50 text-blue-700",
    orange: "bg-orange-50 text-orange-700",
    green: "bg-emerald-50 text-emerald-700",
  }[tone];
  return (
    <Card className="card-lift flex items-center gap-4 p-5">
      <div className={cn("h-11 w-11 rounded-md", toneClass)} />
      <div>
        <div className="text-sm text-muted-foreground">{label}</div>
        <div className="text-3xl font-extrabold text-[#0f2349]">{value}</div>
        <div className="text-sm text-muted-foreground">{sublabel}</div>
      </div>
    </Card>
  );
}

export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs font-semibold text-muted-foreground">{label}</div>
      <div className="mt-1 text-base font-extrabold">{value}</div>
    </div>
  );
}

export function Alert({ text, onClose }: { text: string; onClose: () => void }) {
  return (
    <div className="mb-5 flex items-center justify-between rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
      {text}
      <button className="font-extrabold" onClick={onClose} type="button">
        Закрыть
      </button>
    </div>
  );
}

export function ServerOfflineNotice({
  onRetry,
  retrying,
  className,
}: {
  onRetry?: () => void | Promise<void>;
  retrying?: boolean;
  className?: string;
}) {
  return (
    <Card className={cn("border-orange-200 bg-orange-50/85 p-5 shadow-[0_12px_30px_rgba(99,64,11,0.12)]", className)}>
      <h3 className="text-lg font-extrabold text-orange-900">Нет подключения к серверу RiskGuard</h3>
      <p className="mt-2 text-sm leading-6 text-orange-800">
        Запустите web-сервер, затем повторите действие. Desktop получает данные только через API.
      </p>
      <div className="mt-3 rounded-md border border-orange-200 bg-white/75 px-3 py-2 text-xs text-orange-900">
        <div className="font-semibold">Команда запуска web:</div>
        <code className="mt-1 block">cd web && ..\.venv\Scripts\python app.py</code>
      </div>
      {onRetry ? (
        <Button className="mt-4" disabled={retrying} onClick={() => void onRetry()} size="sm" variant="secondary">
          {retrying ? (
            <span className="inline-flex items-center gap-2">
              <Spinner />
              Проверяем...
            </span>
          ) : (
            "Проверить подключение"
          )}
        </Button>
      ) : null}
    </Card>
  );
}
