# RiskGuard Desktop Tauri

Новая desktop-версия эксперта на Tauri + React + Tailwind + shadcn-style компонентах.

## Требования

На ПК должны быть установлены:

- Node.js LTS
- Rust с Cargo
- Microsoft Visual Studio Build Tools с компонентом Desktop development with C++
- WebView2 Runtime

## Запуск (демо)

1. Запустить web API:

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\web"
..\.venv\Scripts\python app.py
```

2. Запустить desktop:

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\desktop-tauri"
npm install
npm run tauri:dev
```

Desktop для демо подключается к `http://127.0.0.1:5000`.

## Сборка установщика

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\desktop-tauri"
npm run tauri:build
```

Готовые файлы появятся в `src-tauri/target/release/bundle`.

Файл из `src-tauri/target/debug` создается режимом разработки. Он зависит от dev-сервера Vite и может показывать окно WebView/Edge с ошибкой подключения, если запускать его отдельно.

## Сброс демо-БД

Сброс базы выполняется на стороне web:

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\web"
.\.venv\Scripts\python reset_demo_db.py
```
