import { useState } from "react";
import { submitAssessment } from "../lib/api";
import type { DraftAssessment, Risk } from "../lib/types";
import { formatDate, levelLabels, riskLevel, severityVariant, statusLabels, statusVariant } from "../lib/labels";
import { Badge, Button, Card, Input, Spinner, Textarea } from "./ui";
import { PageHeader } from "./shared";

export function RiskDetail({
  risk,
  draft,
  token,
  onBack,
  onDraft,
  onSubmit,
}: {
  risk: Risk;
  draft?: DraftAssessment;
  token: string;
  onBack: () => void;
  onDraft: (riskId: string, draft: DraftAssessment | null) => void;
  onSubmit: () => Promise<void>;
}) {
  const assessment = risk.my_assessment;
  const locked = Boolean(assessment);
  const [probability, setProbability] = useState(draft?.probability || assessment?.probability || 1);
  const [impact, setImpact] = useState(draft?.impact_score || assessment?.impact_score || 1);
  const [recommendation, setRecommendation] = useState(draft?.recommendation || assessment?.recommendation || "");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const level = riskLevel(probability, impact);
  const localStatus = locked ? "assessed" : draft ? "draft" : "pending";

  function saveDraft() {
    if (locked) return;
    onDraft(risk.id, {
      probability,
      impact_score: impact,
      recommendation,
      date: new Date().toISOString(),
    });
  }

  async function submit() {
    setError("");
    if (recommendation.trim().length < 8) {
      setError("Добавьте рекомендацию не короче 8 символов.");
      return;
    }
    setSubmitting(true);
    try {
      await submitAssessment(token, risk.id, probability, impact, recommendation);
      onDraft(risk.id, null);
      await onSubmit();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить оценку.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="space-y-5">
      <Button onClick={onBack} variant="secondary">
        Назад к списку
      </Button>
      <PageHeader title={`${risk.id} - ${risk.title}`} subtitle={`Категория: ${risk.category || "-"} | Владелец: ${risk.owner || "-"} | Назначен: ${formatDate(risk.assigned_date)}`} />

      <div className="grid grid-cols-[minmax(0,1.4fr)_minmax(360px,0.6fr)] gap-5">
        <div className="space-y-5">
          <Card className="p-5 shadow-[0_18px_42px_rgba(22,36,66,0.075)]">
            <Badge variant={statusVariant(localStatus)}>{statusLabels[localStatus]}</Badge>
            <p className="mt-4 leading-7 text-muted-foreground">{risk.description}</p>
          </Card>

          <InfoList title="Инциденты" items={risk.incidents || []} empty="Нет зарегистрированных инцидентов." />
          <InfoList title="Меры минимизации" items={risk.mitigations || []} empty="Меры минимизации еще не добавлены." />
        </div>

        <Card className="sticky top-6 h-fit border-primary/10 bg-white/95 p-5 shadow-[0_22px_55px_rgba(22,36,66,0.12)] backdrop-blur">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-lg font-extrabold">Экспертная оценка</h3>
            <Badge variant={severityVariant(level)}>{levelLabels[level]}</Badge>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3">
            <ScoreField disabled={locked} label="Вероятность" value={probability} onChange={setProbability} />
            <ScoreField disabled={locked} label="Влияние" value={impact} onChange={setImpact} />
          </div>
          <label className="mt-4 block space-y-2 text-sm font-semibold">
            <span>Рекомендация</span>
            <Textarea
              disabled={locked}
              value={recommendation}
              onChange={(event) => setRecommendation(event.target.value)}
              placeholder="Опишите экспертную рекомендацию"
            />
          </label>
          {error ? <p className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
          <div className="mt-5 flex gap-3">
            <Button disabled={locked || submitting} onClick={saveDraft} variant="secondary">
              Сохранить черновик
            </Button>
            <Button disabled={locked || submitting} onClick={submit}>
              {submitting ? (
                <span className="inline-flex items-center gap-2">
                  <Spinner className="border-primary-foreground/40" />
                  Отправка...
                </span>
              ) : (
                "Отправить оценку"
              )}
            </Button>
          </div>
          {submitting ? <p className="mt-2 text-xs font-semibold text-muted-foreground">Сохраняем оценку на сервере...</p> : null}
        </Card>
      </div>
    </section>
  );
}

function ScoreField({
  label,
  value,
  disabled,
  onChange,
}: {
  label: string;
  value: number;
  disabled: boolean;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block space-y-2 text-sm font-semibold">
      <span>{label}</span>
      <Input disabled={disabled} max={5} min={1} onChange={(event) => onChange(Number(event.target.value))} type="number" value={value} />
    </label>
  );
}

function InfoList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <Card className="p-5 shadow-[0_14px_34px_rgba(22,36,66,0.06)]">
      <h3 className="text-lg font-extrabold">{title}</h3>
      {!items.length ? <p className="mt-3 text-sm text-muted-foreground">{empty}</p> : null}
      <div className="mt-3 space-y-2">
        {items.map((item, index) => (
          <div className="rounded-md border border-border bg-muted/50 px-3 py-2 text-sm text-muted-foreground" key={`${item}-${index}`}>
            {item}
          </div>
        ))}
      </div>
    </Card>
  );
}
