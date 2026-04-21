# Checklist: Задание 4.x / 5.x

## 4.1 CQRS

### 4.1.1 Разделение command/query

- Command endpoints:
  - `POST /api/commands/risks`
  - `PATCH /api/commands/risks/<id>/status`
  - `POST /api/commands/risks/<id>/assign-expert`
  - `POST /api/commands/events/process`
- Query endpoints:
  - `GET /api/queries/risks`
  - `GET /api/queries/risks/<id>`
  - `GET /api/queries/lag`

### 4.1.2 Разные модели данных

- Write-model: нормализованные ORM-таблицы (`risk`, `assessment`, `incident`, ...).
- Read-model: денормализованная `risk_read_model`.

### 4.1.3 Query без ORM, command через ORM

- Query: raw SQL (`sqlalchemy.text`) в `read_model_risks_query`, `read_model_risk_by_public_id`, `api_heatmap`.
- Command: ORM-сервисы (`create_risk_with_measures`, `transition_risk_status`, `assign_expert_to_risk`, `create_assessment`).

## 4.2 Backend for Frontend

### 4.2.1 Отдельные endpoint'ы под клиентов

- `GET /api/bff/web/dashboard`
- `GET /api/bff/mobile/home`
- `GET /api/bff/desktop/expert`

### 4.2.2 Разные DTO

- Web DTO: summary + risk_cards + audit_feed.
- Mobile DTO: profile + incident_queue.
- Desktop DTO: expert + assigned_risks + latest_assessments.

### 4.2.3 Агрегация данных

- BFF-endpoint'ы объединяют несколько источников (read-model + audit/assessment/intake) под конкретный UI.

## 4.3 Events + Queue

### 4.3.1 Минимум два domain event

- `RiskCreated`
- `RiskStatusChanged`
- Дополнительно: `RiskExpertAssigned`, `RiskAssessed`, `IncidentIntakeRegistered`.

### 4.3.2 Очередь событий

- Таблица `domain_event` + обработчик `process_domain_events`.

## 4.4 Eventual consistency

- Команда пишет в write-model сразу.
- Read-model обновляется асинхронно (через `process_domain_events`).
- Лаг: `GET /api/queries/lag`.

## 5.1 Git process

### 5.1.1 Стратегия веток

- `main`, `developer`, `feature/*`.

### 5.1.2 Workflow examples

- `feature/cqrs-commands`
- `feature/bff-mobile`

### 5.1.3 PR описание

- Шаблон PR: `../.github/pull_request_template.md`.

### 5.1.4 Коммиты

- Рекомендуемые префиксы:
  - `feat:`
  - `fix:`
  - `refactor:`
  - `docs:`

## 5.2 Heatmap / Metrics

### 5.2.1 Горячие точки

- `GET /api/heatmap`: частые query, тяжелые command, состояние очереди.

### 5.2.2 Метрики

- Таблица `api_request_metric`, запись на каждом `/api/*` запросе.

### 5.2.3 Инвалидация кэша после команд

- Query-cache (`QUERY_CACHE`) очищается в command-сервисах.
