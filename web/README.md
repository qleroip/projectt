# RiskGuard Web

Веб-сервер и API для проекта RiskGuard.

## 1) Первый запуск на новом ПК (если переносите только папку `web`)

Минимально для запуска web/API на новом ПК нужно:

- папка `web/`
- Python 3.11+
- интернет при первом `pip install`

Если хотите перенести текущую базу, оставьте внутри `web/instance/`.
Если нужна чистая демо-база, `web/instance/` можно не переносить или выполнить reset.

```powershell
cd "C:\Path\To\web"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Новые таблицы для CQRS/events/metrics создаются автоматически при запуске:

- `risk_read_model`
- `domain_event`
- `api_request_metric`

## 2) Запуск web/API

### Локально (только на этом ПК)

```powershell
cd "C:\Path\To\web"
.\.venv\Scripts\python.exe app.py
```

Откройте: `http://127.0.0.1:5000`

### Для подключения APK/других устройств по сети

```powershell
cd "C:\Path\To\web"
$env:RISKGUARD_HOST="0.0.0.0"
$env:RISKGUARD_PORT="5000"
$env:RISKGUARD_DEBUG="1"
.\.venv\Scripts\python.exe app.py
```

Именно этот вариант запуска нужен для APK и других устройств в сети.

## 3) Как узнать IP ПК для APK

На ПК с запущенным web выполните:

```powershell
(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null }).IPv4Address.IPAddress
```

Альтернативно можно посмотреть IPv4 через:

```powershell
ipconfig
```

Используйте адрес в APK в формате:

`http://<ВАШ_IP>:5000`

Пример: `http://192.168.1.45:5000`

Для LDPlayer лучше брать обычный LAN IPv4 (`192.168.x.x` или `10.x.x.x`).
Адреса вида `100.x.x.x` часто относятся к VPN/Tailscale и в LDPlayer могут не открываться.

## 4) Полезные команды диагностики

Проверить, что сервер поднялся на 5000:

```powershell
netstat -ano | findstr :5000
```

Проверить доступ с этого же ПК:

```powershell
Invoke-WebRequest "http://127.0.0.1:5000" -UseBasicParsing
```

При необходимости открыть порт 5000 в Firewall (один раз):

```powershell
netsh advfirewall firewall add rule name="RiskGuard 5000" dir=in action=allow protocol=TCP localport=5000
```

Проверить API ping:

```powershell
Invoke-WebRequest "http://127.0.0.1:5000/api/ping" -UseBasicParsing
```

Если используете LDPlayer, дополнительно откройте в браузере LDPlayer:

```text
http://<IP_ПК>:5000/api/ping
```

Если на ПК ping работает, а в LDPlayer нет, почти всегда причина в firewall, неверном IP или сетевом режиме эмулятора.

## 5) Сброс демо-БД

База: `web/instance/riskguard_v3.db`

```powershell
cd "C:\Path\To\web"
.\.venv\Scripts\python.exe .\reset_demo_db.py
```

## 6) Демо-аккаунты

- `michael.brown@company.com / password123` — администратор
- `maria.rodriguez@company.com / password123` — риск-менеджер
- `sarah.chen@company.com / password123` — эксперт
- `john.smith@company.com / password123` — работник

## 7) CQRS (для задания 4.1)

Write (commands):

- `POST /api/commands/risks`
- `PATCH /api/commands/risks/<id>/status`
- `POST /api/commands/risks/<id>/assign-expert`

Read (queries):

- `GET /api/queries/risks`
- `GET /api/queries/risks/<id>`
- `GET /api/queries/lag`

Важно:

- write-модель: нормализованные таблицы (`risk`, `assessment`, `incident`, ...).
- read-модель: денормализованная таблица `risk_read_model`.
- query-слой выполнен raw SQL (`sqlalchemy.text`), command-слой через ORM.

## 8) Domain Events + очередь (для задания 4.3/4.4)

Таблица очереди: `domain_event`.

Примеры событий:

- `RiskCreated`
- `RiskStatusChanged`
- `RiskExpertAssigned`
- `RiskAssessed`

Обработка очереди:

- вручную: `POST /api/commands/events/process`
- через UI: кнопки в разделе "Фоновые задачи"

Eventual consistency:

- команда фиксируется сразу;
- read-модель догоняет через очередь;
- лаг смотреть через `GET /api/queries/lag`.

## 9) BFF endpoint'ы (для задания 4.2)

- `GET /api/bff/web/dashboard` — агрегат под web-панель менеджера
- `GET /api/bff/mobile/home` — агрегат под APK работника
- `GET /api/bff/desktop/expert` — агрегат под desktop эксперта

## 10) Heatmap/метрики (для задания 5.2)

Endpoint:

- `GET /api/heatmap`

Что показывает:

- горячие query endpoint'ы (частота),
- тяжелые command endpoint'ы (средняя длительность),
- состояние очереди событий.

Полный чеклист по пунктам 4.x/5.x: `COURSE_4_5_CHECKLIST.md`.
