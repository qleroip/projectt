import type { SubmittedAssessment } from "../lib/types";
import { formatDate, severityVariant } from "../lib/labels";
import { Badge, Card } from "./ui";
import { Metric, PageHeader } from "./shared";

export function AssessmentsPage({ assessments }: { assessments: SubmittedAssessment[] }) {
  return (
    <section className="space-y-6">
      <PageHeader title="Мои оценки" subtitle="Отправленные экспертные оценки рисков" />
      <div className="space-y-4">
        {assessments.map((item) => (
          <Card className="card-lift p-5" key={item.id}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-muted-foreground">{item.risk_id}</span>
              <Badge variant="green">Оценен</Badge>
              <Badge variant={severityVariant(item.severity_level)}>{item.severity_level}</Badge>
            </div>
            <h3 className="mt-4 text-xl font-extrabold">{item.risk_title}</h3>
            <div className="mt-4 grid grid-cols-4 gap-4 text-sm">
              <Metric label="Дата оценки" value={formatDate(item.date)} />
              <Metric label="Вероятность" value={`${item.probability}/5`} />
              <Metric label="Влияние" value={`${item.impact_score}/5`} />
              <Metric label="Итоговый балл" value={String(item.probability * item.impact_score)} />
            </div>
            <div className="mt-4 rounded-md border border-border bg-muted/50 p-4">
              <div className="text-xs font-semibold text-muted-foreground">Рекомендация эксперта</div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.recommendation}</p>
            </div>
          </Card>
        ))}
      </div>
      <Card className="p-5">
        <div className="text-xl font-extrabold text-[#134182]">Всего отправлено оценок: {assessments.length}</div>
        <p className="mt-1 text-sm text-[#3c6fb8]">Продолжайте отличную работу!</p>
      </Card>
    </section>
  );
}
