import { StatusBar } from "expo-status-bar";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  apiBaseUrl,
  createIncident,
  defaultApiBaseUrl,
  getMe,
  login,
  pingServer,
  registerWorker,
  setApiBaseUrl,
} from "./src/lib/api";
import { humanDateTime, nowAsApiDate } from "./src/lib/format";
import {
  clearSession,
  loadApiBase,
  loadIncidentHistory,
  loadSession,
  saveApiBase,
  saveIncidentHistory,
  saveSession,
} from "./src/lib/storage";
import type {
  CurrentUser,
  IncidentHistoryItem,
  IncidentPayload,
} from "./src/lib/types";

type Option = { label: string; value: string };

const CATEGORY_OPTIONS: Option[] = [
  { label: "Операционный", value: "Operational" },
  { label: "Инфобез", value: "Information Security" },
  { label: "Комплаенс", value: "Compliance" },
  { label: "Технологический", value: "Technology" },
  { label: "Инфраструктура", value: "Infrastructure" },
];

const IMPACT_OPTIONS: Option[] = [
  { label: "Низкий", value: "Low" },
  { label: "Средний", value: "Medium" },
  { label: "Высокий", value: "High" },
  { label: "Критический", value: "Critical" },
];

export default function App() {
  const [booting, setBooting] = useState(true);
  const [token, setToken] = useState("");
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [history, setHistory] = useState<IncidentHistoryItem[]>([]);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authLoading, setAuthLoading] = useState(false);
  const [error, setError] = useState("");
  const [registerMessage, setRegisterMessage] = useState("");
  const [registerFullName, setRegisterFullName] = useState("");
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);
  const [serverSettingsOpen, setServerSettingsOpen] = useState(false);
  const [serverInput, setServerInput] = useState(apiBaseUrl());
  const [serverMessage, setServerMessage] = useState("");
  const [serverChecking, setServerChecking] = useState(false);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState(CATEGORY_OPTIONS[0].value);
  const [impactLevel, setImpactLevel] = useState(IMPACT_OPTIONS[1].value);
  const [occurrenceDate, setOccurrenceDate] = useState(nowAsApiDate());
  const [actualLoss, setActualLoss] = useState("0");
  const [incidentLoading, setIncidentLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    void bootstrap();
  }, []);

  async function bootstrap() {
    setBooting(true);
    try {
      const [session, storedHistory, storedApiBase] = await Promise.all([
        loadSession(),
        loadIncidentHistory(),
        loadApiBase(),
      ]);
      setApiBaseUrl(storedApiBase || defaultApiBaseUrl());
      setServerInput(apiBaseUrl());
      setHistory(storedHistory);
      if (!session) return;
      setToken(session.token);
      setUser(session.user);
      setEmail(session.user.email);
    } finally {
      setBooting(false);
    }
  }

  async function onLogin() {
    setError("");
    setRegisterMessage("");
    setSuccessMessage("");
    setServerMessage("");
    if (!email.trim() || !password) {
      setError("Введите email и пароль.");
      return;
    }

    setAuthLoading(true);
    try {
      const nextToken = await login(email, password);
      const nextUser = await getMe(nextToken);
      if (nextUser.role !== "worker" && nextUser.role !== "admin") {
        throw new Error("В APK доступ разрешен только роли работника.");
      }
      await saveSession(nextToken, nextUser);
      setToken(nextToken);
      setUser(nextUser);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа.");
    } finally {
      setAuthLoading(false);
    }
  }

  async function onRegister() {
    setError("");
    setRegisterMessage("");
    setSuccessMessage("");
    setServerMessage("");

    if (!registerFullName.trim() || !registerEmail.trim() || !registerPassword) {
      setError("Заполните ФИО, email и пароль.");
      return;
    }

    setAuthLoading(true);
    try {
      const response = await registerWorker(registerFullName, registerEmail, registerPassword);
      const message =
        response.message || "Заявка отправлена на одобрение администратором.";
      setRegisterMessage(message);
      setEmail(registerEmail.trim().toLowerCase());
      setPassword("");
      setRegisterPassword("");
      setAuthMode("login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка регистрации.");
    } finally {
      setAuthLoading(false);
    }
  }

  async function onSaveServerSettings() {
    const value = serverInput.trim();
    if (!value) {
      setServerMessage("Укажите IP или URL сервера.");
      return;
    }
    setApiBaseUrl(value);
    const next = apiBaseUrl();
    await saveApiBase(next);
    setServerInput(next);
    setServerChecking(true);
    try {
      await pingServer();
      setServerMessage(`Сервер сохранен и доступен: ${next}`);
    } catch (err) {
      setServerMessage(
        `Адрес сохранен (${next}), но сервер не отвечает. Проверьте web/app.py и firewall.`,
      );
      setError(err instanceof Error ? err.message : "Сервер недоступен.");
    } finally {
      setServerChecking(false);
    }
  }

  async function onResetServerSettings() {
    setApiBaseUrl(defaultApiBaseUrl());
    const next = apiBaseUrl();
    await saveApiBase(next);
    setServerInput(next);
    setServerMessage("Адрес сброшен на значение по умолчанию.");
  }

  async function onCheckServerConnection() {
    setServerChecking(true);
    setServerMessage("Проверка подключения...");
    setError("");
    try {
      await pingServer();
      setServerMessage(`Сервер доступен: ${apiBaseUrl()}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Сервер недоступен.";
      setServerMessage("Сервер недоступен. Проверьте IP, порт 5000 и запуск web/app.py.");
      setError(message);
    } finally {
      setServerChecking(false);
    }
  }

  async function onLogout() {
    await clearSession();
    setToken("");
    setUser(null);
    setPassword("");
    setSuccessMessage("");
    setError("");
  }

  async function onSubmitIncident() {
    setError("");
    setSuccessMessage("");

    const payload = normalizeIncident({
      title,
      description,
      category,
      impact_level: impactLevel,
      occurrence_date: occurrenceDate,
      actual_loss: Number(actualLoss || 0),
    });
    const validationError = validateIncident(payload);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIncidentLoading(true);
    try {
      const created = await createIncident(token, payload);
      const item: IncidentHistoryItem = {
        id: created.id,
        status: created.status,
        title: payload.title,
        sentAt: new Date().toISOString(),
      };
      const updated = [item, ...history].slice(0, 20);
      setHistory(updated);
      await saveIncidentHistory(updated);

      setTitle("");
      setDescription("");
      setCategory(CATEGORY_OPTIONS[0].value);
      setImpactLevel(IMPACT_OPTIONS[1].value);
      setOccurrenceDate(nowAsApiDate());
      setActualLoss("0");
      setSuccessMessage(`Инцидент ${created.id} отправлен. Статус: ${created.status}`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Не удалось отправить инцидент.",
      );
    } finally {
      setIncidentLoading(false);
    }
  }

  const offlineHint = useMemo(
    () => error.includes("Нет подключения к серверу"),
    [error],
  );

  if (booting) {
    return (
      <SafeAreaView style={[styles.root, styles.center]}>
        <StatusBar style="dark" />
        <ActivityIndicator size="large" color="#2c66f5" />
        <Text style={styles.bootText}>Запуск RiskGuard Worker...</Text>
      </SafeAreaView>
    );
  }

  if (!token || !user) {
    return (
      <SafeAreaView style={styles.authRoot}>
        <StatusBar style="light" />
        <View style={styles.authCard}>
          <Text style={styles.brandTitle}>RiskGuard</Text>
          <Text style={styles.brandSubtitle}>APK работника</Text>

          <View style={styles.authTabs}>
            <Pressable
              onPress={() => {
                setError("");
                setRegisterMessage("");
                setAuthMode("login");
              }}
              style={[styles.authTab, authMode === "login" && styles.authTabActive]}
            >
              <Text
                style={[
                  styles.authTabText,
                  authMode === "login" && styles.authTabTextActive,
                ]}
              >
                Вход
              </Text>
            </Pressable>
            <Pressable
              onPress={() => {
                setError("");
                setRegisterMessage("");
                setAuthMode("register");
              }}
              style={[styles.authTab, authMode === "register" && styles.authTabActive]}
            >
              <Text
                style={[
                  styles.authTabText,
                  authMode === "register" && styles.authTabTextActive,
                ]}
              >
                Регистрация
              </Text>
            </Pressable>
          </View>

          {authMode === "register" ? (
            <>
              <Text style={styles.label}>ФИО</Text>
              <TextInput
                onChangeText={setRegisterFullName}
                placeholder="Иванов Иван Иванович"
                placeholderTextColor="#90a1bd"
                style={styles.input}
                value={registerFullName}
              />

              <Text style={styles.label}>Email</Text>
              <TextInput
                autoCapitalize="none"
                keyboardType="email-address"
                onChangeText={setRegisterEmail}
                placeholder="worker@company.com"
                placeholderTextColor="#90a1bd"
                style={styles.input}
                value={registerEmail}
              />

              <Text style={styles.label}>Пароль</Text>
              <View style={styles.passwordRow}>
                <TextInput
                  onChangeText={setRegisterPassword}
                  placeholder="Придумайте пароль"
                  placeholderTextColor="#90a1bd"
                  secureTextEntry={!showRegisterPassword}
                  style={[styles.input, styles.passwordInput]}
                  value={registerPassword}
                />
                <Pressable
                  onPress={() => setShowRegisterPassword((prev) => !prev)}
                  style={styles.passToggle}
                >
                  <Text style={styles.passToggleText}>
                    {showRegisterPassword ? "Скрыть" : "Показать"}
                  </Text>
                </Pressable>
              </View>

              <Text style={styles.authHint}>
                Роль работника назначается автоматически. После отправки заявку одобряет администратор.
              </Text>
            </>
          ) : (
            <>
              <Text style={styles.label}>Email</Text>
              <TextInput
                autoCapitalize="none"
                keyboardType="email-address"
                onChangeText={setEmail}
                placeholder="john.smith@company.com"
                placeholderTextColor="#90a1bd"
                style={styles.input}
                value={email}
              />

              <Text style={styles.label}>Пароль</Text>
              <View style={styles.passwordRow}>
                <TextInput
                  onChangeText={setPassword}
                  placeholder="Введите пароль"
                  placeholderTextColor="#90a1bd"
                  secureTextEntry={!showPassword}
                  style={[styles.input, styles.passwordInput]}
                  value={password}
                />
                <Pressable
                  onPress={() => setShowPassword((prev) => !prev)}
                  style={styles.passToggle}
                >
                  <Text style={styles.passToggleText}>
                    {showPassword ? "Скрыть" : "Показать"}
                  </Text>
                </Pressable>
              </View>
            </>
          )}

          {error ? (
            <View style={offlineHint ? styles.offlineBox : styles.errorBox}>
              <Text style={offlineHint ? styles.offlineTitle : styles.errorText}>
                {error}
              </Text>
              {offlineHint ? (
                <Text style={styles.offlineHelp}>
                  Запустите сервер: `web\app.py`, затем повторите вход. Текущий API: {apiBaseUrl()}
                </Text>
              ) : null}
            </View>
          ) : null}
          {registerMessage ? (
            <View style={styles.successBox}>
              <Text style={styles.successText}>{registerMessage}</Text>
            </View>
          ) : null}

          <Pressable
            disabled={authLoading}
            onPress={() =>
              void (authMode === "register" ? onRegister() : onLogin())
            }
            style={[styles.primaryButton, authLoading && styles.disabledButton]}
          >
            {authLoading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.primaryButtonText}>
                {authMode === "register" ? "Отправить заявку" : "Войти"}
              </Text>
            )}
          </Pressable>

          <View style={styles.serverToolsRow}>
            <Text style={styles.apiHint}>API: {apiBaseUrl()}</Text>
            <Pressable
              onPress={() => {
                setServerMessage("");
                setServerSettingsOpen((prev) => !prev);
              }}
              style={styles.serverSettingsButton}
            >
              <Text style={styles.serverSettingsButtonText}>Настройки сервера</Text>
            </Pressable>
          </View>

          {serverSettingsOpen ? (
            <View style={styles.serverCard}>
              <Text style={styles.label}>API адрес</Text>
              <TextInput
                autoCapitalize="none"
                autoCorrect={false}
                onChangeText={setServerInput}
                placeholder="Например: 192.168.1.20:5000"
                placeholderTextColor="#90a1bd"
                style={styles.input}
                value={serverInput}
              />
              <Text style={styles.serverHint}>
                Android Studio Emulator: `http://10.0.2.2:5000`, LDPlayer: `http://IP_ПК:5000`
              </Text>
              <View style={styles.serverActions}>
                <Pressable
                  disabled={serverChecking}
                  onPress={() => void onSaveServerSettings()}
                  style={[styles.smallPrimary, serverChecking && styles.disabledButton]}
                >
                  <Text style={styles.smallPrimaryText}>Сохранить</Text>
                </Pressable>
                <Pressable
                  disabled={serverChecking}
                  onPress={() => void onCheckServerConnection()}
                  style={[styles.smallGhost, serverChecking && styles.disabledButton]}
                >
                  <Text style={styles.smallGhostText}>Проверить</Text>
                </Pressable>
                <Pressable
                  disabled={serverChecking}
                  onPress={() => void onResetServerSettings()}
                  style={[styles.smallGhost, serverChecking && styles.disabledButton]}
                >
                  <Text style={styles.smallGhostText}>Сброс</Text>
                </Pressable>
              </View>
              {serverMessage ? <Text style={styles.serverMessage}>{serverMessage}</Text> : null}
            </View>
          ) : null}
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.root}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>Портал инцидентов</Text>
            <Text style={styles.headerSubtitle}>
              Работник регистрирует событие для проверки риск-менеджером
            </Text>
          </View>
          <Pressable onPress={() => void onLogout()} style={styles.secondaryButton}>
            <Text style={styles.secondaryButtonText}>Выйти</Text>
          </Pressable>
        </View>

        <View style={styles.infoCard}>
          <Text style={styles.infoName}>{user.full_name}</Text>
          <Text style={styles.infoText}>{user.email}</Text>
          <Text style={styles.infoRole}>Роль: {user.role}</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Создать инцидент</Text>

          <Text style={styles.label}>Заголовок</Text>
          <TextInput
            onChangeText={setTitle}
            placeholder="Кратко: что произошло"
            placeholderTextColor="#90a1bd"
            style={styles.input}
            value={title}
          />

          <Text style={styles.label}>Описание</Text>
          <TextInput
            multiline
            onChangeText={setDescription}
            placeholder="Подробности инцидента"
            placeholderTextColor="#90a1bd"
            style={[styles.input, styles.textArea]}
            value={description}
          />

          <Text style={styles.label}>Категория</Text>
          <View style={styles.optionWrap}>
            {CATEGORY_OPTIONS.map((item) => (
              <OptionChip
                active={category === item.value}
                key={item.value}
                label={item.label}
                onPress={() => setCategory(item.value)}
              />
            ))}
          </View>

          <Text style={styles.label}>Уровень влияния</Text>
          <View style={styles.optionWrap}>
            {IMPACT_OPTIONS.map((item) => (
              <OptionChip
                active={impactLevel === item.value}
                key={item.value}
                label={item.label}
                onPress={() => setImpactLevel(item.value)}
              />
            ))}
          </View>

          <Text style={styles.label}>Дата и время (YYYY-MM-DD HH:mm)</Text>
          <TextInput
            onChangeText={setOccurrenceDate}
            placeholder="2026-04-19 14:20"
            placeholderTextColor="#90a1bd"
            style={styles.input}
            value={occurrenceDate}
          />

          <Text style={styles.label}>Факт. ущерб</Text>
          <TextInput
            keyboardType="numeric"
            onChangeText={(value) => setActualLoss(value.replace(/[^\d]/g, ""))}
            placeholder="0"
            placeholderTextColor="#90a1bd"
            style={styles.input}
            value={actualLoss}
          />

          {error ? (
            <View style={offlineHint ? styles.offlineBox : styles.errorBox}>
              <Text style={offlineHint ? styles.offlineTitle : styles.errorText}>
                {error}
              </Text>
            </View>
          ) : null}

          {successMessage ? (
            <View style={styles.successBox}>
              <Text style={styles.successText}>{successMessage}</Text>
            </View>
          ) : null}

          <Pressable
            disabled={incidentLoading}
            onPress={() => void onSubmitIncident()}
            style={[styles.primaryButton, incidentLoading && styles.disabledButton]}
          >
            {incidentLoading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.primaryButtonText}>Отправить инцидент</Text>
            )}
          </Pressable>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Последние отправки</Text>
          {!history.length ? (
            <Text style={styles.emptyText}>Пока нет отправленных инцидентов.</Text>
          ) : (
            history.map((item) => (
              <View key={`${item.id}-${item.sentAt}`} style={styles.historyRow}>
                <View style={styles.historyMain}>
                  <Text style={styles.historyTitle}>{item.id}</Text>
                  <Text style={styles.historySub}>{item.title}</Text>
                  <Text style={styles.historyDate}>{humanDateTime(item.sentAt)}</Text>
                </View>
                <View style={styles.statusPill}>
                  <Text style={styles.statusText}>{item.status}</Text>
                </View>
              </View>
            ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function OptionChip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.optionChip, active && styles.optionChipActive]}
    >
      <Text style={[styles.optionChipText, active && styles.optionChipTextActive]}>
        {label}
      </Text>
    </Pressable>
  );
}

function normalizeIncident(input: IncidentPayload): IncidentPayload {
  return {
    ...input,
    title: input.title.trim(),
    description: input.description.trim(),
    occurrence_date: input.occurrence_date.trim(),
    actual_loss: Number.isFinite(input.actual_loss) ? input.actual_loss : 0,
  };
}

function validateIncident(payload: IncidentPayload) {
  if (!payload.title) return "Укажите заголовок инцидента.";
  if (payload.title.length < 4) return "Заголовок должен быть не короче 4 символов.";
  if (!payload.description || payload.description.length < 10) {
    return "Описание должно быть не короче 10 символов.";
  }
  if (!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(payload.occurrence_date)) {
    return "Дата должна быть в формате YYYY-MM-DD HH:mm.";
  }
  if (payload.actual_loss < 0) return "Ущерб не может быть отрицательным.";
  return "";
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#eef3fb",
  },
  center: {
    justifyContent: "center",
    alignItems: "center",
    gap: 10,
  },
  bootText: {
    fontSize: 14,
    color: "#50668d",
    fontWeight: "700",
  },
  authRoot: {
    flex: 1,
    backgroundColor: "#172642",
    justifyContent: "center",
    padding: 20,
  },
  authCard: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#3a537f",
    backgroundColor: "#f8fbff",
    padding: 18,
    gap: 10,
    shadowColor: "#000000",
    shadowOpacity: 0.16,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
  },
  brandTitle: {
    fontSize: 26,
    fontWeight: "800",
    color: "#11264c",
  },
  brandSubtitle: {
    marginTop: 2,
    marginBottom: 4,
    fontSize: 14,
    color: "#58729e",
    fontWeight: "600",
  },
  authTabs: {
    marginTop: 4,
    marginBottom: 2,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#c8d6eb",
    backgroundColor: "#eef4ff",
    padding: 4,
    flexDirection: "row",
    gap: 4,
  },
  authTab: {
    flex: 1,
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: "center",
    justifyContent: "center",
  },
  authTabActive: {
    backgroundColor: "#2c66f5",
  },
  authTabText: {
    color: "#2b4f8f",
    fontWeight: "700",
    fontSize: 13,
  },
  authTabTextActive: {
    color: "#ffffff",
  },
  content: {
    padding: 16,
    gap: 14,
  },
  header: {
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#c8d6eb",
    borderRadius: 14,
    padding: 14,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
  },
  headerTitle: {
    fontSize: 23,
    fontWeight: "800",
    color: "#12284e",
  },
  headerSubtitle: {
    marginTop: 4,
    color: "#5b74a0",
    fontSize: 13,
    maxWidth: 250,
  },
  infoCard: {
    backgroundColor: "#e8f0ff",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#bdd0f0",
    padding: 14,
    gap: 3,
  },
  infoName: {
    fontSize: 18,
    fontWeight: "800",
    color: "#11264c",
  },
  infoText: {
    fontSize: 13,
    color: "#4e6792",
  },
  infoRole: {
    marginTop: 3,
    fontSize: 13,
    color: "#2b4f8f",
    fontWeight: "700",
  },
  card: {
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#c8d6eb",
    borderRadius: 14,
    padding: 14,
    gap: 8,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "800",
    marginBottom: 4,
    color: "#11264c",
  },
  label: {
    fontSize: 13,
    color: "#5c739e",
    fontWeight: "700",
    marginTop: 4,
  },
  input: {
    borderWidth: 1,
    borderColor: "#c8d6eb",
    borderRadius: 10,
    backgroundColor: "#f7faff",
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: "#12284e",
  },
  textArea: {
    minHeight: 92,
    textAlignVertical: "top",
  },
  passwordRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  passwordInput: {
    flex: 1,
  },
  passToggle: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#c8d6eb",
    backgroundColor: "#ffffff",
    paddingHorizontal: 12,
    paddingVertical: 11,
  },
  passToggleText: {
    color: "#2a4b85",
    fontWeight: "700",
    fontSize: 12,
  },
  authHint: {
    marginTop: 2,
    color: "#637ca5",
    fontSize: 12,
    fontWeight: "600",
  },
  optionWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginBottom: 2,
  },
  optionChip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#c8d6eb",
    backgroundColor: "#f7faff",
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  optionChipActive: {
    borderColor: "#2c66f5",
    backgroundColor: "#e8efff",
  },
  optionChipText: {
    color: "#4f6d9c",
    fontSize: 12,
    fontWeight: "700",
  },
  optionChipTextActive: {
    color: "#19439e",
  },
  primaryButton: {
    marginTop: 8,
    borderRadius: 10,
    backgroundColor: "#2c66f5",
    height: 46,
    justifyContent: "center",
    alignItems: "center",
  },
  disabledButton: {
    opacity: 0.7,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontWeight: "800",
    fontSize: 16,
  },
  secondaryButton: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#c4d4ec",
    backgroundColor: "#ffffff",
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  secondaryButtonText: {
    color: "#2b4f8f",
    fontWeight: "700",
    fontSize: 13,
  },
  errorBox: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#f0b8b8",
    backgroundColor: "#fff3f3",
    padding: 10,
  },
  errorText: {
    color: "#b63939",
    fontWeight: "700",
    fontSize: 13,
  },
  offlineBox: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#f4cf9a",
    backgroundColor: "#fff5e8",
    padding: 10,
    gap: 4,
  },
  offlineTitle: {
    color: "#8f5b10",
    fontWeight: "700",
    fontSize: 13,
  },
  offlineHelp: {
    color: "#8f5b10",
    fontSize: 12,
  },
  successBox: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#9dd6b0",
    backgroundColor: "#ecfff2",
    padding: 10,
  },
  successText: {
    color: "#157a3d",
    fontWeight: "700",
    fontSize: 13,
  },
  apiHint: {
    marginTop: 2,
    color: "#667fa7",
    fontSize: 12,
    fontWeight: "600",
  },
  serverToolsRow: {
    marginTop: 4,
    gap: 8,
  },
  serverSettingsButton: {
    alignSelf: "flex-start",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#c8d6eb",
    backgroundColor: "#ffffff",
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  serverSettingsButtonText: {
    color: "#2a4b85",
    fontWeight: "700",
    fontSize: 12,
  },
  serverCard: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#c8d6eb",
    backgroundColor: "#f5f9ff",
    padding: 10,
    gap: 8,
  },
  serverActions: {
    flexDirection: "row",
    gap: 8,
  },
  smallPrimary: {
    borderRadius: 10,
    backgroundColor: "#2c66f5",
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  smallPrimaryText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 12,
  },
  smallGhost: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#c8d6eb",
    backgroundColor: "#ffffff",
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  smallGhostText: {
    color: "#2a4b85",
    fontWeight: "700",
    fontSize: 12,
  },
  serverMessage: {
    color: "#4e6792",
    fontSize: 12,
    fontWeight: "600",
  },
  serverHint: {
    color: "#5f7399",
    fontSize: 12,
    fontWeight: "600",
  },
  emptyText: {
    fontSize: 13,
    color: "#6882ad",
  },
  historyRow: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#d2def0",
    backgroundColor: "#f8fbff",
    padding: 10,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  historyMain: {
    flex: 1,
    gap: 2,
  },
  historyTitle: {
    fontSize: 14,
    fontWeight: "800",
    color: "#10284c",
  },
  historySub: {
    fontSize: 13,
    color: "#4e6792",
  },
  historyDate: {
    fontSize: 12,
    color: "#6f85ab",
  },
  statusPill: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#2fca73",
    backgroundColor: "#e7fff0",
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  statusText: {
    color: "#189550",
    fontWeight: "800",
    fontSize: 12,
  },
});
