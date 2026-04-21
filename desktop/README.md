# RiskGuard Desktop (PySide6)

Desktop-клиент для роли `Эксперт`.

## Что уже реализовано

- Авторизация через API веб-сервера (`/auth/login`)
- `Запомнить меня` с сохранением email и токена
- Автовосстановление сессии при валидном токене
- Отправка заявки на доступ эксперта (`Запросить доступ` -> `/auth/register`)
- Разделы эксперта:
  - `Назначенные риски`
  - `Мои оценки`
  - `Профиль`
- Карточка риска:
  - вероятность 1-5
  - влияние 1-5
  - расчет уровня риска
  - черновик (локально до отправки)
  - отправка оценки в API (`/api/risks/<id>/assessments`)

## Запуск

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\web"
..\.venv\Scripts\python app.py
```

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\desktop"
..\.venv\Scripts\python -m pip install -r requirements.txt
..\.venv\Scripts\python main.py
```

## API, которые использует desktop

- `POST /auth/login`
- `POST /auth/register`
- `GET /api/me`
- `GET /api/expert/risks`
- `GET /api/expert/risks/<id>`
- `GET /api/expert/assessments`
- `POST /api/risks/<id>/assessments`

## Структура

- `main.py` - точка входа
- `riskguard_desktop/models.py` - типы данных
- `riskguard_desktop/repository.py` - API-клиент desktop
- `riskguard_desktop/session.py` - хранение сессии
- `riskguard_desktop/ui/login_window.py` - вход и отправка заявки
- `riskguard_desktop/ui/main_window.py` - dashboard эксперта
- `riskguard_desktop/ui/theme.py` - тема интерфейса
