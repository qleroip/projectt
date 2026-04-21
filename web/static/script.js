/**
 * @typedef {"day" | "night"} Mode
 */

/**
 * Creates a reusable segmented mode toggle.
 * @param {HTMLElement} mount
 * @param {{initialMode?: Mode, onChange?: (mode: Mode) => void, className?: string}} [options]
 */
function createSegmentedModeToggle(mount, options = {}) {
  const modes = /** @type {Mode[]} */ (["day", "night"]);
  const initialCandidate = /** @type {Mode} */ (options.initialMode || "day");
  let currentMode = modes.includes(initialCandidate) ? initialCandidate : "day";

  const root = document.createElement("div");
  root.className = `mode-toggle ${options.className || ""}`.trim();
  root.setAttribute("role", "radiogroup");
  root.setAttribute("aria-label", "Режим интерфейса");
  root.innerHTML = `
    <div class="mode-toggle__thumb" aria-hidden="true"></div>
    <button type="button" class="mode-toggle__option" data-mode="day" role="radio" aria-label="Дневной режим" title="Дневной режим">
      <span class="mode-toggle__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="4.3"></circle><path d="M12 2.6v2.4M12 19v2.4M4.6 4.6l1.7 1.7M17.7 17.7l1.7 1.7M2.6 12H5M19 12h2.4M4.6 19.4l1.7-1.7M17.7 6.3l1.7-1.7"></path></svg>
      </span>
    </button>
    <button type="button" class="mode-toggle__option" data-mode="night" role="radio" aria-label="Ночной режим" title="Ночной режим">
      <span class="mode-toggle__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none"><path d="M16.7 14.7a7.2 7.2 0 1 1-7.4-12 8.4 8.4 0 1 0 7.4 12Z"></path></svg>
      </span>
    </button>
  `;

  mount.innerHTML = "";
  mount.appendChild(root);

  const buttons = /** @type {HTMLButtonElement[]} */ ([...root.querySelectorAll(".mode-toggle__option")]);
  const onChange = typeof options.onChange === "function" ? options.onChange : () => {};

  function modeIndex(mode) {
    return Math.max(0, modes.indexOf(mode));
  }

  /**
   * @param {Mode} nextMode
   */
  function setMode(nextMode) {
    if (!modes.includes(nextMode)) {
      return;
    }
    currentMode = nextMode;
    root.style.setProperty("--mode-index", String(modeIndex(nextMode)));
    root.dataset.mode = nextMode;
    buttons.forEach((button) => {
      const selected = button.dataset.mode === nextMode;
      button.setAttribute("aria-checked", selected ? "true" : "false");
      button.tabIndex = selected ? 0 : -1;
      button.classList.toggle("is-selected", selected);
    });
    onChange(nextMode);
  }

  buttons.forEach((button, buttonIndex) => {
    button.addEventListener("click", () => {
      setMode(/** @type {Mode} */ (button.dataset.mode || "day"));
    });

    button.addEventListener("keydown", (event) => {
      const key = event.key;
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(key)) {
        return;
      }
      event.preventDefault();
      let targetIndex = buttonIndex;
      if (key === "ArrowRight") {
        targetIndex = (buttonIndex + 1) % modes.length;
      } else if (key === "ArrowLeft") {
        targetIndex = (buttonIndex - 1 + modes.length) % modes.length;
      } else if (key === "Home") {
        targetIndex = 0;
      } else if (key === "End") {
        targetIndex = modes.length - 1;
      }
      buttons[targetIndex].focus();
      setMode(/** @type {Mode} */ (modes[targetIndex]));
    });
  });

  setMode(currentMode);
  return {
    getMode: () => currentMode,
    setMode,
    element: root,
  };
}

function initSidebarModeToggle() {
  const mount = document.getElementById("mode-toggle-root");
  if (!mount) {
    return;
  }

  const savedMode = /** @type {Mode | null} */ (localStorage.getItem("riskguard.mode"));
  const datasetMode = /** @type {Mode} */ (mount.dataset.initialMode || "day");
  const initialMode = savedMode || datasetMode || "day";
  const root = document.documentElement;
  const body = document.body;

  createSegmentedModeToggle(mount, {
    initialMode,
    className: mount.dataset.className || "",
    onChange: (mode) => {
      root.dataset.uiMode = mode;
      body.dataset.uiMode = mode;
      localStorage.setItem("riskguard.mode", mode);
    },
  });

  root.dataset.uiMode = initialMode;
  body.dataset.uiMode = initialMode;
}

function initAutoSubmitSelects() {
  document.querySelectorAll(".auto-submit-select").forEach((select) => {
    select.addEventListener("change", () => {
      if (select.value && select.form) {
        select.form.requestSubmit();
      }
    });
  });
}

function initMeasureBuilder() {
  const container = document.getElementById("measures-container");
  const addButton = document.getElementById("add-measure-btn");

  if (!container || !addButton) {
    return;
  }

  function syncMeasureCards() {
    const cards = [...container.querySelectorAll(".measure-card")];
    cards.forEach((card, index) => {
      const number = card.querySelector(".measure-number");
      const removeButton = card.querySelector(".measure-remove");
      const radios = card.querySelectorAll('input[type="radio"]');
      const hidden = card.querySelector(".priority-hidden");

      if (number) {
        number.textContent = String(index + 1);
      }

      if (removeButton) {
        removeButton.disabled = cards.length === 1;
      }

      radios.forEach((radio) => {
        radio.name = `measure_priority_${index}`;
        radio.addEventListener("change", () => {
          if (radio.checked && hidden) {
            hidden.value = radio.value;
          }
        });
      });
    });
  }

  function bindRemove(card) {
    const removeButton = card.querySelector(".measure-remove");
    if (!removeButton) {
      return;
    }
    removeButton.addEventListener("click", () => {
      if (container.querySelectorAll(".measure-card").length <= 1) {
        return;
      }
      card.remove();
      syncMeasureCards();
    });
  }

  [...container.querySelectorAll(".measure-card")].forEach(bindRemove);
  syncMeasureCards();

  addButton.addEventListener("click", () => {
    const card = document.createElement("article");
    card.className = "measure-card";
    card.innerHTML = `
      <div class="measure-card-head">
        <div class="measure-number"></div>
        <button class="measure-remove" type="button" aria-label="Удалить меру">Удалить</button>
      </div>
      <div class="field-stack">
        <label>Действие *</label>
        <input name="measure_action" placeholder="Опишите меру предотвращения" required>
        <div class="form-grid">
          <div>
            <label>Ответственный *</label>
            <input name="measure_person" placeholder="ФИО ответственного" required>
          </div>
          <div>
            <label>Срок *</label>
            <input type="date" name="measure_deadline" required>
          </div>
        </div>
        <label>Приоритет *</label>
        <div class="priority-group">
          <label><input type="radio" value="High" checked><span>Высокий</span></label>
          <label><input type="radio" value="Medium"><span>Средний</span></label>
          <label><input type="radio" value="Low"><span>Низкий</span></label>
        </div>
        <input type="hidden" name="measure_priority" value="High" class="priority-hidden">
      </div>
    `;
    container.appendChild(card);
    bindRemove(card);
    syncMeasureCards();
  });
}

window.createSegmentedModeToggle = createSegmentedModeToggle;

document.addEventListener("DOMContentLoaded", () => {
  initSidebarModeToggle();
  initAutoSubmitSelects();
  initMeasureBuilder();
});
