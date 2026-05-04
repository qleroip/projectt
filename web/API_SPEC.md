# RiskGuard API

Base URL for local development: `http://127.0.0.1:5000`

All protected endpoints require:

```http
Authorization: Bearer <access_token>
```

## API versioning

Current stable version prefix: `/api/v1`.

For demo compatibility, the previous unversioned routes are still available and return the same payloads:

- `/auth/login` and `/api/v1/auth/login`
- `/auth/register` and `/api/v1/auth/register`
- `/api/...` and `/api/v1/...`

New APK, desktop and integration clients should prefer `/api/v1/*`. Existing clients do not need rebuilds while legacy aliases are kept.

## Error format

API errors use one common JSON format. The `error` field is intentionally kept for old clients.

```json
{
  "error": "Forbidden",
  "code": "ACCESS_FORBIDDEN",
  "message": "Forbidden",
  "details": {
    "field": "optional extra context"
  }
}
```

Common status codes:

- `400` / `VALIDATION_ERROR` - invalid request fields.
- `401` / `AUTH_TOKEN_MISSING`, `AUTH_TOKEN_INVALID`, `INVALID_CREDENTIALS` - authentication problem.
- `403` / `ACCESS_FORBIDDEN`, `ACCOUNT_PENDING_APPROVAL` - authenticated but not allowed.
- `404` / `RISK_NOT_FOUND`, `EXPERT_NOT_FOUND` - entity not found.
- `409` / `INVALID_STATUS_TRANSITION`, `USER_ALREADY_EXISTS` - business conflict.

## Pagination

List endpoints keep the old response format unless pagination parameters are provided.

Without pagination:

```json
[
  { "id": "RISK-001" }
]
```

With `page`, `limit` or `offset`:

```http
GET /api/v1/queries/risks?page=1&limit=20
```

```json
{
  "items": [
    { "id": "RISK-001" }
  ],
  "pagination": {
    "total": 42,
    "limit": 20,
    "offset": 0,
    "page": 1,
    "has_next": true
  }
}
```

Supported by:

- `GET /api/v1/queries/risks`
- `GET /api/v1/legacy/risks`
- `GET /api/v1/expert/risks`
- `GET /api/v1/expert/assessments`

## Auth

### POST `/api/v1/auth/login`

Legacy alias: `POST /auth/login`

Request:

```json
{
  "email": "sarah.chen@company.com",
  "password": "password123"
}
```

Response:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

### POST `/api/v1/auth/register`

Legacy alias: `POST /auth/register`

Creates an access request. The account must be approved by an administrator.

Allowed role values for public registration: `worker`, `expert`, `risk_manager`.
`admin` is not accepted in this endpoint.

Request:

```json
{
  "full_name": "Ivan Petrov",
  "email": "ivan.petrov@company.com",
  "password": "password123",
  "role": "expert"
}
```

Response `201`:

```json
{
  "message": "Заявка отправлена на одобрение администратором"
}
```

## Common profile endpoint

### GET `/api/v1/me`

Legacy alias: `GET /api/me`

Returns current authorized user.

Response:

```json
{
  "id": 4,
  "full_name": "Sarah Chen",
  "email": "sarah.chen@company.com",
  "role": "expert",
  "joined_at": "2026-01-15",
  "is_approved": true
}
```

## Desktop Client: Expert

### GET `/api/v1/expert/risks`

Legacy alias: `GET /api/expert/risks`

Allowed roles: `expert`, `admin`.

For expert returns only assigned risks.

Response item:

```json
{
  "id": "RISK-001",
  "title": "Data Center Power Failure",
  "description": "Risk of power outage at primary data center",
  "category": "Infrastructure",
  "status": "ACTIVE",
  "impact_level": "High",
  "owner": "Maria Rodriguez",
  "expert": "Sarah Chen",
  "priority": 4,
  "assigned_date": "2026-04-10",
  "incident_count": 1,
  "measure_count": 2,
  "assessment_count": 1,
  "my_assessment": {
    "id": 9,
    "risk_id": 1,
    "probability": 4,
    "impact_score": 5,
    "recommendation": "Run failover drill.",
    "severity_level": "Critical",
    "date": "2026-04-13",
    "expert_id": 3
  }
}
```

### GET `/api/v1/expert/risks/<risk_id>`

Legacy alias: `GET /api/expert/risks/<risk_id>`

Allowed roles: `expert`, `admin`.

Response includes detailed fields:

- `incidents` (array of descriptions)
- `mitigations` (array of actions)
- `my_assessment`

### GET `/api/v1/expert/assessments`

Legacy alias: `GET /api/expert/assessments`

Allowed roles: `expert`, `admin`.

For expert returns only own assessments.

Response item:

```json
{
  "id": 9,
  "risk_id": "RISK-001",
  "risk_title": "Data Center Power Failure",
  "probability": 4,
  "impact_score": 5,
  "recommendation": "Run failover drill.",
  "severity_level": "Critical",
  "date": "2026-04-13"
}
```

### POST `/api/v1/risks/<risk_id>/assessments`

Legacy alias: `POST /api/risks/<risk_id>/assessments`

Creates an expert assessment for an assigned risk.

Allowed roles: `expert`, `admin`.

Request:

```json
{
  "probability": 4,
  "impact_score": 5,
  "recommendation": "Run failover drill and increase reserve power capacity."
}
```

Response:

```json
{
  "id": 1,
  "severity_level": "Critical"
}
```

## APK Client: Worker

### POST `/api/v1/incidents`

Legacy alias: `POST /api/incidents`

Creates an incident intake item for risk-manager review. It does not create a risk automatically.

Allowed roles: `worker`, `admin`.

Request:

```json
{
  "title": "Power interruption",
  "description": "Short power interruption in the primary data center.",
  "category": "Operational",
  "impact_level": "Medium",
  "occurrence_date": "2026-04-16 20:10",
  "actual_loss": 1000
}
```

Response:

```json
{
  "id": "INQ-003",
  "status": "PENDING"
}
```

## Web/API Client: Risk Manager

### GET `/api/v1/legacy/risks` (legacy)

Legacy alias: `GET /api/legacy/risks`

Allowed roles: `risk_manager`, `expert`, `admin`.

For `expert`, returns only assigned risks. For `worker`, returns `403`.

### POST `/api/v1/legacy/risks` (legacy)

Legacy alias: `POST /api/legacy/risks`

Creates a risk with mitigation measures in one transaction.

Allowed roles: `risk_manager`, `admin`.

### PATCH `/api/v1/legacy/risks/<risk_id>/status` (legacy)

Legacy alias: `PATCH /api/legacy/risks/<risk_id>/status`

Changes risk status.

Allowed roles: `risk_manager`, `admin`.

Valid transitions:

- `CREATED -> ACTIVE`
- `ACTIVE -> COMPLETED`
- `ACTIVE -> CANCELLED`

Notes:

- `ACTIVE` requires an assigned expert.
- Invalid transitions return `409`.
- Validation errors return `400`.

Для новых интеграций использовать только CQRS endpoint'ы из следующего раздела.

---

## CQRS Endpoints (course 4.1)

### Commands (write model, ORM)

### POST `/api/v1/commands/risks`

Legacy alias: `POST /api/commands/risks`

Create risk + measures in one transaction.

Response:

```json
{
  "id": "RISK-010",
  "status": "CREATED",
  "pending_events": 2,
  "eventual_consistency": true
}
```

### PATCH `/api/v1/commands/risks/<risk_id>/status`

Legacy alias: `PATCH /api/commands/risks/<risk_id>/status`

Change status in write model, enqueue domain event.

### POST `/api/v1/commands/risks/<risk_id>/assign-expert`

Legacy alias: `POST /api/commands/risks/<risk_id>/assign-expert`

Assign expert to risk in write model.

### POST `/api/v1/commands/events/process`

Legacy alias: `POST /api/commands/events/process`

Process queued domain events and synchronize read model.

Request:

```json
{
  "limit": 10
}
```

### Queries (read model, raw SQL)

### GET `/api/v1/queries/risks?status=ACTIVE&search=risk-001`

Legacy alias: `GET /api/queries/risks`

Returns denormalized records from `risk_read_model`.

### GET `/api/v1/queries/risks/<risk_id>`

Legacy alias: `GET /api/queries/risks/<risk_id>`

Returns one denormalized risk card.

### GET `/api/v1/queries/lag`

Legacy alias: `GET /api/queries/lag`

Shows queue lag for eventual consistency.

---

## BFF Endpoints (course 4.2)

### GET `/api/v1/bff/web/dashboard`

Legacy alias: `GET /api/bff/web/dashboard`

Aggregated DTO for manager web UI:

- summary counters
- risk cards
- recent audit feed

### GET `/api/v1/bff/mobile/home`

Legacy alias: `GET /api/bff/mobile/home`

Aggregated DTO for worker mobile UI:

- user profile block
- recent incident queue items

### GET `/api/v1/bff/desktop/expert`

Legacy alias: `GET /api/bff/desktop/expert`

Aggregated DTO for expert desktop UI:

- expert profile block
- assigned risks
- latest assessments

---

## Events + Queue (course 4.3/4.4)

Domain events are persisted in table `domain_event`.

Implemented event types include:

- `RiskCreated`
- `RiskStatusChanged`
- `RiskExpertAssigned`
- `RiskAssessed`
- `IncidentIntakeRegistered`

Read model is eventually consistent by design:

1. Command updates write model immediately.
2. Event is queued.
3. Queue processor updates read model with delay.

---

## Heatmap / Metrics (course 5.2)

### GET `/api/v1/heatmap`

Legacy alias: `GET /api/heatmap`

Returns:

- most frequent query endpoints,
- heaviest command endpoints by avg duration,
- event queue state (`pending/processed/failed`).

Metrics are persisted in `api_request_metric`.

---

## Legacy endpoints

Legacy mixed read/write endpoint paths are kept under `/api/legacy/*` for compatibility and should not be used for new clients.
