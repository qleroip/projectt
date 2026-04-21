# RiskGuard Monorepo

Проект разделен на независимые части:

- `web/` - веб-панель (Flask)
- `desktop/` - desktop-клиент эксперта (PySide6)
- `desktop-tauri/` - новая desktop-версия эксперта (Tauri + React + Tailwind)
- `apk/` - мобильный клиент работника (Expo React Native)

## Демо: что запускать

1. Web/API:

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\web"
$env:RISKGUARD_HOST="0.0.0.0"
$env:RISKGUARD_PORT="5000"
.\.venv\Scripts\python.exe app.py
```

2. Desktop Tauri (режим разработки):

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\desktop-tauri"
npm install
npm run tauri:dev
```

Desktop для демо подключается к `http://127.0.0.1:5000`, поэтому web и desktop запускаем на одном ПК.
APK подключается к адресу, который задается на экране входа в `Настройки сервера`.

## Минимум для запуска на новом ПК

Для демонстрации на новом ПК минимально нужны:

- папка `web/`
- собранный desktop-установщик или готовый `.exe`
- собранный APK-файл
- установленный Python 3.11+ на новом ПК

Не нужно переносить, если APK и desktop уже собраны:

- `apk/`
- `desktop/`
- `desktop-tauri/`
- `node_modules/`
- корневую `.venv/`

Если нужна текущая база с уже созданными пользователями/рисками, переносите `web/instance/` вместе с `web/`.
Если нужна чистая демо-база, `web/instance/` можно не переносить или выполнить сброс после запуска.

Первый запуск `web` на новом ПК выполняется один раз:

```powershell
cd "C:\Path\To\web"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Обычный запуск `web/API` для демонстрации:

```powershell
cd "C:\Path\To\web"
$env:RISKGUARD_HOST="0.0.0.0"
$env:RISKGUARD_PORT="5000"
.\.venv\Scripts\python.exe app.py
```

После запуска откройте web на этом ПК:

```text
http://127.0.0.1:5000
```

IP для APK на новом ПК:

```powershell
(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null }).IPv4Address.IPAddress
```

В APK укажите адрес в `Настройки сервера`:

```text
http://<IP_НОВОГО_ПК>:5000
```

Если APK запускается в LDPlayer на новом ПК:

- web должен быть запущен с `RISKGUARD_HOST="0.0.0.0"`;
- в APK указывайте обычный LAN IPv4 ПК, чаще всего вида `192.168.x.x` или `10.x.x.x`;
- адреса `100.x.x.x` часто относятся к VPN/Tailscale и могут не работать в LDPlayer;
- `ADB` нужен для установки/отладки, но для подключения APK к web через IP он не обязателен;
- перед входом проверьте в браузере LDPlayer: `http://<IP_ПК>:5000/api/ping`;
- если браузер LDPlayer не открывает адрес, откройте порт:

```powershell
netsh advfirewall firewall add rule name="RiskGuard 5000" dir=in action=allow protocol=TCP localport=5000
```

Desktop для демо подключается к `http://127.0.0.1:5000`, поэтому его проще запускать на том же ПК, где запущен `web`.

Новые таблицы для CQRS/events/metrics (`risk_read_model`, `domain_event`, `api_request_metric`) создаются автоматически при запуске `web`.

## Сборка desktop-установщика

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\desktop-tauri"
npm run tauri:build
```

Готовые установщики появятся в `desktop-tauri/src-tauri/target/release/bundle`.

## Сброс демо-БД

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\web"
.\.venv\Scripts\python.exe reset_demo_db.py
```

Подробно про web и БД: `web/README.md`.
Чеклист задания 4.x/5.x: `web/COURSE_4_5_CHECKLIST.md`.

## Архитектурные требования курса (4.x/5.x)

Ниже кратко, что уже добавлено в проект.

### 4.1 CQRS

- Команды (`write`): отдельные endpoint'ы:
  - `POST /api/commands/risks`
  - `PATCH /api/commands/risks/<id>/status`
  - `POST /api/commands/risks/<id>/assign-expert`
- Запросы (`read`): отдельные endpoint'ы:
  - `GET /api/queries/risks`
  - `GET /api/queries/risks/<id>`
  - `GET /api/queries/lag`
- `write`-модель нормализована (таблицы `risk`, `assessment`, `incident`, ...).
- `read`-модель денормализована (`risk_read_model`).
- Query-слой использует raw SQL (`sqlalchemy.text`), command-слой — ORM.

### 4.2 Backend for Frontend (BFF)

Добавлены отдельные BFF-endpoint'ы под клиентов:

- `GET /api/bff/web/dashboard`
- `GET /api/bff/mobile/home`
- `GET /api/bff/desktop/expert`

Они возвращают разные DTO и агрегируют данные под конкретный UI.

### 4.3 Domain Events + Queue

- Доменные события: минимум два, в проекте больше:
  - `RiskCreated`
  - `RiskStatusChanged`
  - `RiskExpertAssigned`
  - `RiskAssessed`
  - `IncidentIntakeRegistered`
- Очередь событий: таблица `domain_event`.
- Обработчик очереди:
  - `POST /api/commands/events/process`
  - также обрабатывается шагами через экран фоновых задач.

### 4.4 Eventual Consistency

- Команда фиксируется сразу в write-модели.
- Read-модель обновляется с задержкой через очередь событий.
- Текущую задержку можно смотреть через `GET /api/queries/lag`.

### 5.1 Git workflow

Рекомендуемая стратегия веток:

- `main` — стабильная ветка демонстрации.
- `developer` — интеграционная.
- `feature/*` — фичи.

Примеры feature-веток:

- `feature/cqrs-commands`
- `feature/bff-mobile`

Соглашения по коммитам:

- `feat: ...`
- `fix: ...`
- `refactor: ...`
- `docs: ...`

Шаблон PR добавлен в `.github/pull_request_template.md`.

### 5.2 Тепловая карта и метрики

- Endpoint `GET /api/heatmap` показывает:
  - самые частые query endpoint'ы,
  - самые "тяжелые" command endpoint'ы (по среднему времени),
  - состояние очереди событий.
- Метрики собираются в таблицу `api_request_metric`.
- После команд кэш query-слоя инвалидируется.
