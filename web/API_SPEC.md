# RiskGuard API

Base URL for local development: `http://127.0.0.1:5000`

All protected endpoints require:

```http
Authorization: Bearer <access_token>
```

## Auth

### POST `/auth/login`

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

### POST `/auth/register`

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

### GET `/api/me`

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

### GET `/api/expert/risks`

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

### GET `/api/expert/risks/<risk_id>`

Allowed roles: `expert`, `admin`.

Response includes detailed fields:

- `incidents` (array of descriptions)
- `mitigations` (array of actions)
- `my_assessment`

### GET `/api/expert/assessments`

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

### POST `/api/risks/<risk_id>/assessments`

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

### POST `/api/incidents`

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

### GET `/api/legacy/risks` (legacy)

Allowed roles: `risk_manager`, `expert`, `admin`.

For `expert`, returns only assigned risks. For `worker`, returns `403`.

### POST `/api/legacy/risks` (legacy)

Creates a risk with mitigation measures in one transaction.

Allowed roles: `risk_manager`, `admin`.

### PATCH `/api/legacy/risks/<risk_id>/status` (legacy)

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

### POST `/api/commands/risks`

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

### PATCH `/api/commands/risks/<risk_id>/status`

Change status in write model, enqueue domain event.

### POST `/api/commands/risks/<risk_id>/assign-expert`

Assign expert to risk in write model.

### POST `/api/commands/events/process`

Process queued domain events and synchronize read model.

Request:

```json
{
  "limit": 10
}
```

### Queries (read model, raw SQL)

### GET `/api/queries/risks?status=ACTIVE&search=risk-001`

Returns denormalized records from `risk_read_model`.

### GET `/api/queries/risks/<risk_id>`

Returns one denormalized risk card.

### GET `/api/queries/lag`

Shows queue lag for eventual consistency.

---

## BFF Endpoints (course 4.2)

### GET `/api/bff/web/dashboard`

Aggregated DTO for manager web UI:

- summary counters
- risk cards
- recent audit feed

### GET `/api/bff/mobile/home`

Aggregated DTO for worker mobile UI:

- user profile block
- recent incident queue items

### GET `/api/bff/desktop/expert`

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

### GET `/api/heatmap`

Returns:

- most frequent query endpoints,
- heaviest command endpoints by avg duration,
- event queue state (`pending/processed/failed`).

Metrics are persisted in `api_request_metric`.

---

## Legacy endpoints

Legacy mixed read/write endpoint paths are kept under `/api/legacy/*` for compatibility and should not be used for new clients.
