# RiskGuard APK (Worker)

Мобильный клиент для роли `worker` (работник).
Текущая версия проекта: `Expo SDK 54`.

## Реализовано

- Вход по `email/password` через `/auth/login`
- Регистрация работника через `/auth/register` (заявка уходит на одобрение администратору)
- Проверка роли через `/api/me` (доступ только для `worker` и `admin`)
- Форма регистрации инцидента через `/api/incidents`
- Настройки сервера на экране входа (можно менять API-адрес без правки кода)
- Валидация формы:
  - обязательные поля
  - дата в формате `YYYY-MM-DD HH:mm`
  - `Факт. ущерб` только число
- Локальное хранение сессии и истории последних отправок
- Экран ошибки сети с подсказкой, что нужно запустить web

## Запуск (демо)

1. Запустить web на ПК-сервере:

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\web"
$env:RISKGUARD_HOST="0.0.0.0"
$env:RISKGUARD_PORT="5000"
.\.venv\Scripts\python.exe app.py
```

2. Узнать IP этого ПК:

```powershell
(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null }).IPv4Address.IPAddress
```

3. Запустить APK-клиент:

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\apk"
npm install
npm run android
```

Для Android Studio AVD используйте:

```powershell
npm run android:studio
```

4. В APK (экран входа):

- нажмите `Настройки сервера`
- укажите `http://<IP_ПК_С_WEB>:5000`
- сохраните
- для Android Studio Emulator обычно используйте `http://10.0.2.2:5000`

## Настройка Android SDK и эмулятора (Windows)

Рекомендуемый эмулятор для разработки: **Android Studio Emulator (AVD)**.

1. Установите Android Studio.
2. В Android Studio откройте `SDK Manager` и установите:
   - `Android SDK Platform` (например, API 34/35)
   - `Android SDK Platform-Tools`
   - `Android SDK Build-Tools`
3. Откройте `Device Manager` и создайте виртуальное устройство (например, Pixel 6).
4. Добавьте переменные окружения (PowerShell от имени пользователя):

```powershell
setx ANDROID_HOME "C:\Users\User\AppData\Local\Android\Sdk"
setx ANDROID_SDK_ROOT "C:\Users\User\AppData\Local\Android\Sdk"
setx PATH "$($env:PATH);C:\Users\User\AppData\Local\Android\Sdk\platform-tools;C:\Users\User\AppData\Local\Android\Sdk\emulator"
```

5. Полностью закройте и заново откройте терминал.
6. Проверьте:

```powershell
adb version
```

7. Запустите эмулятор из Android Studio (`Device Manager -> Play`) и только потом:

```powershell
npm run android
```

## Быстрый запуск через LDPlayer (легкий вариант)

Этот раздел нужен для разработки через Expo Go. Если у вас уже есть собранный APK, `ADB` для подключения к web через IP не обязателен.

1. Запустите LDPlayer вручную.
2. В LDPlayer включите ADB, если нужно ставить/запускать приложение из терминала:
   - `Настройки -> Другие настройки -> Отладка по ADB -> Вкл`
   - Перезапустите LDPlayer.
3. В новом терминале проверьте устройство:

```powershell
adb devices
```

4. Если список пустой, подключите вручную:

```powershell
adb connect 127.0.0.1:5555
adb connect 127.0.0.1:5557
adb devices
```

5. Если видите `127.0.0.1:5555 device`, запускайте:

```powershell
npm run android
```

`npm run android` в этом проекте уже запускает LDPlayer-совместимый режим (`expo start --lan`).
Затем откройте в LDPlayer приложение `Expo Go` и вставьте URL `exp://...` из терминала.

## Подключение LDPlayer к web/API на новом ПК

1. Запустите web именно на всех интерфейсах:

```powershell
cd "C:\Path\To\web"
$env:RISKGUARD_HOST="0.0.0.0"
$env:RISKGUARD_PORT="5000"
.\.venv\Scripts\python.exe app.py
```

2. Проверьте web на самом ПК:

```text
http://127.0.0.1:5000/api/ping
```

3. Узнайте LAN IPv4 ПК:

```powershell
ipconfig
```

Берите адрес вида `192.168.x.x` или `10.x.x.x`.
Адреса `100.x.x.x` часто являются VPN/Tailscale и могут не работать в LDPlayer.

4. Проверьте доступ из браузера LDPlayer:

```text
http://<IP_ПК>:5000/api/ping
```

5. В APK на экране входа откройте `Настройки сервера` и укажите:

```text
http://<IP_ПК>:5000
```

6. Если браузер LDPlayer не открывает `/api/ping`, откройте порт `5000` в Windows Firewall:

```powershell
netsh advfirewall firewall add rule name="RiskGuard 5000" dir=in action=allow protocol=TCP localport=5000
```

Если приложение хранит старый адрес, откройте `Настройки сервера`, введите новый адрес и нажмите `Сохранить`/`Проверить`.

## Важное про API-адрес

По умолчанию в приложении есть базовый адрес, но на другом ПК IP обычно будет другим.

Сейчас **код менять не нужно**: просто откройте `Настройки сервера` на экране входа APK и сохраните новый адрес вида:

`http://<НОВЫЙ_IP>:5000`

В конфиге `app.json` подключен плагин `expo-build-properties` с `android.usesCleartextTraffic=true`, поэтому HTTP-адреса локального сервера (без HTTPS) работают в собранном APK.

## Сборка APK

Для демонстрации удобнее собирать через EAS Cloud. На выходе будет обычный `.apk` файл.

```powershell
cd "C:\Users\User\OneDrive\Документы\New project\apk"
npx eas-cli login
npm run build:apk
```

После завершения EAS даст ссылку на скачивание APK.

Если на ПК не установлен Git, команда `npm run build:apk` уже запускает EAS с `EAS_NO_VCS=1`, поэтому Git для демо-сборки не обязателен.
Также включен `EXPO_NO_DOCTOR=1`, чтобы локальная проверка `expo doctor` не блокировала сборку в среде без Git.
Команда также использует `npx.cmd`, чтобы PowerShell не блокировал `npx.ps1`.

Локальная сборка без EAS тоже возможна, но на ПК должны быть установлены Android SDK и JDK:

```powershell
npx expo prebuild --platform android
cd android
.\gradlew.bat assembleDebug
```

Готовый debug APK в таком случае будет здесь:

`apk/android/app/build/outputs/apk/debug/app-debug.apk`

## Полезные команды

```powershell
npm run start
npm run android
npm run android:studio
npm run ldplayer
npm run web
npm run typecheck
npm run build:apk
```
