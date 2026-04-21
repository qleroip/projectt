import { useMemo, useState } from "react";
import type { DraftAssessment, Risk, RiskStatus } from "../lib/types";
import { priorityLabel, priorityVariant, statusLabels, statusVariant, formatDate } from "../lib/labels";
import { Badge, Button, Card, Input } from "./ui";
import { PageHeader, StatCard } from "./shared";

export function AssignedRisksPage({
  risks,
  drafts,
  onOpen,
}: {
  risks: Risk[];
  drafts: Record<string, DraftAssessment>;
  onOpen: (riskId: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | RiskStatus>("all");

  const decoratedRisks = useMemo(
    () =>
      risks.map((risk) => ({
        ...risk,
        status: risk.status === "assessed" ? "assessed" : drafts[risk.id] ? "draft" : "pending",
      })) as Risk[],
    [risks, drafts],
  );
  const pending = decoratedRisks.filter((risk) => risk.status !== "assessed").length;
  const assessed = decoratedRisks.filter((risk) => risk.status === "assessed").length;
  const high = decoratedRisks.filter((risk) => risk.status !== "assessed" && risk.priority >= 4).length;
  const visible = decoratedRisks.filter((risk) => {
    const matchesQuery = `${risk.id} ${risk.title}`.toLowerCase().includes(query.trim().toLowerCase());
    const matchesStatus = filter === "all" || risk.status === filter;
    return matchesQuery && matchesStatus;
  });

  return (
    <section className="space-y-6">
      <PageHeader title="Назначенные риски" subtitle="Риски, ожидающие вашей экспертной оценки" />
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Всего назначено" value={decoratedRisks.length} sublabel="Всего" />
        <StatCard label="Ожидают оценки" value={pending} sublabel="В работе" tone="orange" />
        <StatCard label="Оценено" value={assessed} sublabel="Готово" tone="green" />
      </div>

      {high ? (
        <Card className="border-orange-200 bg-orange-50 p-5">
          <div className="font-extrabold text-orange-800">Внимание: {high} рисков требуют приоритетной оценки</div>
          <p className="mt-1 text-sm text-orange-700">Начните с рисков с высоким приоритетом.</p>
        </Card>
      ) : null}

      <Card className="flex items-center gap-3 p-4">
        <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Поиск по ID или названию риска..." />
        <div className="flex shrink-0 gap-2">
          <Button onClick={() => setFilter("all")} variant={filter === "all" ? "default" : "secondary"}>
            Все
          </Button>
          <Button onClick={() => setFilter("pending")} variant={filter === "pending" ? "default" : "secondary"}>
            Ожидают оценки
          </Button>
          <Button onClick={() => setFilter("assessed")} variant={filter === "assessed" ? "default" : "secondary"}>
            Оценены
          </Button>
        </div>
      </Card>

      <div className="space-y-4">
        {visible.map((risk) => (
          <RiskCard key={risk.id} risk={risk} onOpen={onOpen} />
        ))}
        {!visible.length ? (
          <Card className="p-6">
            <h3 className="text-lg font-extrabold">Риски не найдены</h3>
            <p className="mt-1 text-sm text-muted-foreground">Измените поиск или фильтр.</p>
          </Card>
        ) : null}
      </div>
    </section>
  );
}

function RiskCard({ risk, onOpen }: { risk: Risk; onOpen: (riskId: string) => void }) {
  return (
    <Card className="card-lift p-5">
      <div className="flex items-start gap-3">
        <div className="flex flex-1 flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-muted-foreground">{risk.id}</span>
          <Badge variant={statusVariant(risk.status)}>{statusLabels[risk.status]}</Badge>
          <Badge variant={priorityVariant(risk.priority)}>{priorityLabel(risk.priority)}</Badge>
        </div>
        <Button onClick={() => onOpen(risk.id)} size="sm">
          Открыть
        </Button>
      </div>
      <h3 className="mt-4 text-xl font-extrabold text-foreground">{risk.title}</h3>
      <p className="mt-2 max-w-5xl text-sm leading-6 text-muted-foreground">{risk.description || "Описание пока не заполнено."}</p>
      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
        <span>
          Категория: <b>{risk.category || "-"}</b>
        </span>
        <span>
          Владелец: <b>{risk.owner || "-"}</b>
        </span>
        <span>
          Назначен: <b>{formatDate(risk.assigned_date)}</b>
        </span>
      </div>
    </Card>
  );
}
