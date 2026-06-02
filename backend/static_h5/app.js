const API_BASE = (() => {
  const privateLanPattern = /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[0-1])\.)/;
  if (!window.location.protocol.startsWith("http")) {
    return "http://127.0.0.1:8765";
  }
  if (
    ["127.0.0.1", "localhost", "::1"].includes(window.location.hostname) &&
    window.location.port === "8765"
  ) {
    return window.location.origin;
  }
  if (["127.0.0.1", "localhost", "::1"].includes(window.location.hostname)) {
    return `${window.location.protocol}//${window.location.hostname}:8765`;
  }
  if (privateLanPattern.test(window.location.hostname)) {
    return `${window.location.protocol}//${window.location.hostname}:8765`;
  }
  return window.location.origin;
})();

const state = {
  tab: "train",
  screen: "auth",
  mode: "backend",
  account: null,
  authMode: "register",
  summary: null,
  training: null,
  feedback: null,
  history: [],
  profile: null,
  orders: [],
  selectedHistoryId: "",
  selectedHistoryRound: 1,
  trackedEvents: new Set(),
  timers: {
    thinking: null,
    speaking: null,
    analyzing: null,
  },
};

const app = document.querySelector("#app");
const modePill = document.querySelector("#mode-pill");
const bottomLinks = Array.from(document.querySelectorAll(".bottom-link"));
const toast = document.querySelector("#toast");
const recentCardToggles = new Map();
const PAYMENT_PENDING_KEY = "biaoda_pending_payment";
const TRAINING_RECOVERY_KEY = "biaoda_training_recovery";
let paymentResumePromptOpen = false;
let draftSaveTimer = null;
let latestDraftSave = Promise.resolve();

function runInBackground(task, label = "后台刷新") {
  Promise.resolve()
    .then(task)
    .catch((error) => {
      console.warn(`${label} failed`, error);
    });
}

function refreshAndRenderIf(predicate, task, label) {
  runInBackground(async () => {
    await task();
    if (!predicate || predicate()) {
      render();
    }
  }, label);
}

function getClientId() {
  const storageKey = "biaoda_client_id";
  const fallback = `h5-${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
  try {
    const existing = window.localStorage.getItem(storageKey);
    if (existing) {
      return existing;
    }
    window.localStorage.setItem(storageKey, fallback);
    return fallback;
  } catch (error) {
    return fallback;
  }
}

function getAuthToken() {
  try {
    return window.localStorage.getItem("biaoda_auth_token") || "";
  } catch (error) {
    return "";
  }
}

function setAuthToken(token) {
  try {
    if (!token) {
      window.localStorage.removeItem("biaoda_auth_token");
      return;
    }
    window.localStorage.setItem("biaoda_auth_token", token);
  } catch (error) {
    // ignore storage errors in local browser fallback
  }
}

async function request(path, options = {}) {
  const method = options.method || "GET";
  const clientId = getClientId();
  const authToken = getAuthToken();
  const url = new URL(`${API_BASE}${path}`);
  url.searchParams.set("clientId", clientId);
  if (authToken) {
    url.searchParams.set("authToken", authToken);
  }

  const fetchOptions = { ...options, method };
  const originalBody = options.body;

  if (method === "GET") {
    fetchOptions.headers = authToken ? { "X-Auth-Token": authToken } : {};
    delete fetchOptions.body;
  } else {
    fetchOptions.headers = {
      "Content-Type": "text/plain;charset=UTF-8",
      ...(authToken ? { "X-Auth-Token": authToken } : {}),
      ...(options.headers || {}),
    };
    if (typeof originalBody === "string") {
      try {
        const parsed = JSON.parse(originalBody);
        parsed.clientId = clientId;
        if (authToken) parsed.authToken = authToken;
        fetchOptions.body = JSON.stringify(parsed);
      } catch {
        fetchOptions.body = originalBody;
      }
    } else if (originalBody && typeof originalBody === "object") {
      fetchOptions.body = JSON.stringify({ ...originalBody, clientId, ...(authToken ? { authToken } : {}) });
    }
  }

  let response;
  try {
    response = await fetch(url.toString(), fetchOptions);
  } catch (error) {
    console.warn(`${method} ${url.pathname} request failed`, error);
    throw new Error("网络有点不稳定，请稍后再试。");
  }
  const payload = await response.json();
  if (!response.ok || payload.code !== 0) {
    console.warn(`${method} ${url.pathname} response failed`, payload);
    throw new Error(payload.message || "操作失败，请稍后再试。");
  }
  return payload.data;
}

function trackTrainingEvent(eventName, selectedWords = []) {
  const sessionId = state.training?.id || "";
  const eventKey = `${eventName}:${sessionId}:${selectedWords.join("|")}`;
  if (!sessionId || state.trackedEvents.has(eventKey)) return;
  state.trackedEvents.add(eventKey);
  request("/api/analytics/training-event", {
    method: "POST",
    body: JSON.stringify({
      eventName,
      selectedWords,
    }),
  }).catch((error) => {
    console.warn("training event failed", error);
  });
}

function setMode(text, kind = "backend") {
  state.mode = kind;
  modePill.textContent = text;
}

function setActiveTab(tab) {
  state.tab = tab;
  bottomLinks.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.tab === tab);
  });
}

function selectedChip(word) {
  return `<span class="selected-chip">${word}</span>`;
}

function cleanUserMessage(message, fallback = "操作失败，请稍后再试。") {
  const text = String(message || "").trim();
  if (!text) return fallback;
  if (/did not match the expected pattern|expected pattern|string did not match/i.test(text)) {
    return "输入格式不正确，请检查后再试。";
  }
  if (/invalid|constraint|validation|pattern/i.test(text) && /password|phone|string|input/i.test(text)) {
    return "输入格式不正确，请检查后再试。";
  }
  if (/^(GET|POST|PUT|DELETE|PATCH)\s+\/api\//i.test(text)) {
    return text.replace(/^(GET|POST|PUT|DELETE|PATCH)\s+\/api\/[^：:]+[：:]\s*/i, "") || fallback;
  }
  if (/服务端异常|request failed|failed to fetch/i.test(text)) {
    return fallback;
  }
  return text;
}

function showToast(message) {
  if (!toast) {
    return;
  }
  toast.classList.remove("is-loading");
  toast.textContent = cleanUserMessage(message);
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 1800);
}

function showLoadingToast(message = "加载中...") {
  if (!toast) {
    return;
  }
  toast.innerHTML = `<span class="toast-spinner" aria-hidden="true"></span><span>${cleanUserMessage(message)}</span>`;
  toast.classList.add("is-visible", "is-loading");
  window.clearTimeout(showToast.timer);
}

function hideLoadingToast() {
  if (!toast) {
    return;
  }
  toast.classList.remove("is-visible", "is-loading");
  toast.textContent = "";
}

function toastError(error, fallback) {
  showToast(cleanUserMessage(error?.message, fallback || "操作失败，请稍后再试。"));
}

function confirmDialog(message, options = {}) {
  const cancelText = options.cancelText || "取消";
  const okText = options.okText || "确定";
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "confirm-overlay";
    overlay.innerHTML = `
      <div class="confirm-box" role="dialog" aria-modal="true">
        <p>${message}</p>
        <div class="confirm-actions">
          <button class="confirm-cancel" type="button">${cancelText}</button>
          <button class="confirm-ok" type="button">${okText}</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    const close = (value) => {
      overlay.remove();
      resolve(value);
    };
    overlay.querySelector(".confirm-cancel").addEventListener("click", () => close(false));
    overlay.querySelector(".confirm-ok").addEventListener("click", () => close(true));
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) close(false);
    });
  });
}

const PASSWORD_EYE_CLOSED = `
  <svg viewBox="0 0 24 24" fill="none">
    <path d="M3 12s3.4-5.2 9-5.2S21 12 21 12s-3.4 5.2-9 5.2S3 12 3 12Z" stroke-width="2.2"/>
    <path d="M4.5 4.5l15 15" stroke-width="2.2" stroke-linecap="round"/>
  </svg>
`;

const PASSWORD_EYE_OPEN = `
  <svg viewBox="0 0 24 24" fill="none">
    <path d="M3 12s3.4-5.2 9-5.2S21 12 21 12s-3.4 5.2-9 5.2S3 12 3 12Z" stroke-width="2.2"/>
    <circle cx="12" cy="12" r="2.7" stroke-width="2.2"/>
  </svg>
`;

function formatDateTime(value, fallback = "-") {
  if (!value) return fallback;
  return String(value).slice(0, 16).replace("T", " ");
}

function formatDate(value, fallback = "-") {
  if (!value) return fallback;
  return String(value).slice(0, 10);
}

function paymentCallbackParams() {
  const params = new URLSearchParams(window.location.search || "");
  const outTradeNo = params.get("out_trade_no");
  if (!outTradeNo) {
    return null;
  }
  const callbackParams = {};
  params.forEach((value, key) => {
    callbackParams[key] = value;
  });
  return callbackParams;
}

function setPendingPayment(order) {
  try {
    window.sessionStorage.setItem(PAYMENT_PENDING_KEY, JSON.stringify({
      outTradeNo: order?.outTradeNo || order?.orderNo || "",
      createdAt: Date.now(),
    }));
  } catch (error) {
    // ignore storage errors
  }
}

function clearPendingPayment() {
  try {
    window.sessionStorage.removeItem(PAYMENT_PENDING_KEY);
  } catch (error) {
    // ignore storage errors
  }
}

function setTrainingRecovery(reason = "payment_required") {
  try {
    window.sessionStorage.setItem(TRAINING_RECOVERY_KEY, JSON.stringify({
      reason,
      sessionId: state.training?.sessionId || state.training?.id || "",
      draftText: state.training?.draftText || "",
      createdAt: Date.now(),
    }));
  } catch (error) {
    // ignore storage errors
  }
}

function clearTrainingRecovery() {
  try {
    window.sessionStorage.removeItem(TRAINING_RECOVERY_KEY);
  } catch (error) {
    // ignore storage errors
  }
}

function hasTrainingRecovery() {
  try {
    const recovery = JSON.parse(window.sessionStorage.getItem(TRAINING_RECOVERY_KEY) || "null");
    return Boolean(recovery && Date.now() - Number(recovery.createdAt || 0) < 2 * 60 * 60 * 1000);
  } catch (error) {
    return false;
  }
}

function getPendingPayment() {
  try {
    const pending = JSON.parse(window.sessionStorage.getItem(PAYMENT_PENDING_KEY) || "null");
    if (!pending) return null;
    if (Date.now() - Number(pending.createdAt || 0) > 30 * 60 * 1000) {
      clearPendingPayment();
      return null;
    }
    return pending;
  } catch (error) {
    return null;
  }
}

function updatePendingPayment(pending) {
  try {
    window.sessionStorage.setItem(PAYMENT_PENDING_KEY, JSON.stringify(pending));
  } catch (error) {
    // ignore storage errors
  }
}

async function refreshPaymentStatus(showWaitingToast = true) {
  const pending = getPendingPayment();
  if (!pending) {
    showToast("暂时没有需要刷新的支付订单");
    return false;
  }
  if (showWaitingToast) {
    showLoadingToast("正在刷新支付状态...");
  }
  try {
    const result = await request("/api/account/payment-status", {
      method: "POST",
      body: JSON.stringify({ orderNo: pending.outTradeNo || "" }),
    });
    state.account = result.state || state.account;
    if (state.account?.auth?.authToken) {
      setAuthToken(state.account.auth.authToken);
    }
    hideLoadingToast();
    if (result.paid) {
      clearPendingPayment();
      showToast("支付成功，权益已到账");
      if (hasTrainingRecovery()) {
        state.tab = "train";
        await syncTrainStateFromBackend({ preferDraft: true });
        clearTrainingRecovery();
      }
      render();
      return true;
    }
    if (showWaitingToast) {
      showToast(result.message || "支付暂未完成，可稍后刷新状态。");
    }
  } catch (error) {
    hideLoadingToast();
    toastError(error, "刷新支付状态失败，请稍后再试。");
  }
  return false;
}

async function handlePaymentResume() {
  if (paymentCallbackParams() || document.visibilityState === "hidden") {
    return;
  }
  const pending = getPendingPayment();
  if (!pending) {
    return;
  }
  if (paymentResumePromptOpen || Number(pending.resumePromptCount || 0) >= 2) {
    hideLoadingToast();
    return;
  }
  hideLoadingToast();
  pending.resumePromptCount = Number(pending.resumePromptCount || 0) + 1;
  pending.lastPromptedAt = Date.now();
  updatePendingPayment(pending);
  paymentResumePromptOpen = true;
  try {
    const paidByUser = await confirmDialog("未查询到支付成功状态。你刚才是否已经完成支付？", {
      cancelText: "未支付",
      okText: "已支付",
    });
    if (paidByUser) {
      await refreshPaymentStatus(true);
      return;
    }
    showToast("若后续支付成功，可刷新订单状态。");
  } finally {
    paymentResumePromptOpen = false;
  }
}

function clearTimers() {
  Object.values(state.timers).forEach((timer) => {
    if (timer) {
      clearInterval(timer);
    }
  });
  state.timers.thinking = null;
  state.timers.speaking = null;
  state.timers.analyzing = null;
}

async function maybeVerifyReturn() {
  const callbackParams = paymentCallbackParams();
  if (!callbackParams) {
    return null;
  }
  const result = await request("/api/account/verify-return", {
    method: "POST",
    body: JSON.stringify({ callbackParams }),
  });
  clearPendingPayment();
  hideLoadingToast();
  const cleanUrl = `${window.location.origin}${window.location.pathname}`;
  window.history.replaceState({}, document.title, cleanUrl);
  state.account = result;
  if (result?.auth?.authToken) {
    setAuthToken(result.auth.authToken);
  }
  return result;
}

function normalizeDetails(details = []) {
  const expectedLabels = [
    "主张清楚",
    "解释成立",
    "结构聚焦",
    "观点深度",
    "案例具体",
    "表达自然",
  ];
  const normalized = expectedLabels.map((label, index) => {
    const existing = details[index] || details.find((item) => item.label === label) || {};
    return {
      label,
      score: Math.max(0, Math.min(100, Number(existing.score ?? 75))),
      note: existing.note || "这一维还可以继续展开。",
    };
  });
  return normalized;
}

function renderHeardPoints(points = []) {
  return `
    <div class="guide-list guide-list--feedback">
      ${points
        .map(
          (item, index) => `
            <div class="guide-item">
              <span>${String(index + 1).padStart(2, "0")}</span>
              <p>${item}</p>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function findPreviousAttempt(feedback) {
  const attempts = feedback.attemptHistory || [];
  const currentNo = feedback.attemptNo || 1;
  const previous = attempts.find((item) => item.attemptNo === currentNo - 1);
  return previous ? normalizeDetails(previous.feedback?.visibleDetails || previous.feedback?.details || []) : null;
}

function renderRadar(details, totalScore) {
  const points = normalizeDetails(details);
  const width = 260;
  const height = 230;
  const centerX = width / 2;
  const centerY = 112;
  const radius = 70;
  const levels = [25, 50, 75, 100];
  const polygons = levels
    .map((level) => {
      const ratio = level / 100;
      const coords = points
        .map((_, index) => {
          const angle = (-Math.PI / 2) + (Math.PI * 2 * index) / points.length;
          const x = centerX + Math.cos(angle) * radius * ratio;
          const y = centerY + Math.sin(angle) * radius * ratio;
          return `${x},${y}`;
        })
        .join(" ");
      return `<polygon points="${coords}" fill="none" stroke="rgba(72,89,192,0.12)" stroke-width="1" />`;
    })
    .join("");

  const axes = points
    .map((item, index) => {
      const angle = (-Math.PI / 2) + (Math.PI * 2 * index) / points.length;
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;
      return `<line x1="${centerX}" y1="${centerY}" x2="${x}" y2="${y}" stroke="rgba(72,89,192,0.14)" stroke-width="1" />`;
    })
    .join("");

  const scorePolygon = points
    .map((item, index) => {
      const angle = (-Math.PI / 2) + (Math.PI * 2 * index) / points.length;
      const x = centerX + Math.cos(angle) * radius * (item.score / 100);
      const y = centerY + Math.sin(angle) * radius * (item.score / 100);
      return `${x},${y}`;
    })
    .join(" ");

  const positions = [
    "top",
    "right-top",
    "right-bottom",
    "bottom",
    "left-bottom",
    "left-top",
  ];

  return `
    <div class="ref-eval-layout">
      <aside class="ref-total-card">
        <strong>${totalScore ?? "-"}</strong>
        <small>满分 100</small>
      </aside>
      <div class="ref-radar-stage">
        <svg class="ref-radar-svg" viewBox="0 0 ${width} ${height}" aria-hidden="true">
          ${polygons}
          ${axes}
          <polygon points="${scorePolygon}" fill="rgba(255,108,144,0.20)" stroke="#ff6c90" stroke-width="2.4" />
        </svg>
        ${points
          .map(
            (item, index) => `
              <div class="ref-radar-label ${positions[index]}">
                <span>${item.label}</span>
                <strong>${item.score}</strong>
              </div>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderEvaluationDetails(details, previousDetails) {
  return normalizeDetails(details)
    .map((item, index) => {
      const previousScore = previousDetails?.[index]?.score;
      const delta = typeof previousScore === "number" ? item.score - previousScore : null;
      const deltaText = delta === null
        ? ""
        : delta === 0
          ? "持平"
          : delta > 0
            ? `+${delta}`
            : `${delta}`;
      return `
        <article class="feedback-detail ref-dim-detail">
          <div class="feedback-detail-summary">
            <div class="ref-dim-summary">
              <span class="ref-eval-icon dim-${index + 1}"></span>
              <strong>${item.label}</strong>
              <span>${item.score}${deltaText ? `<em class="detail-delta">${deltaText}</em>` : ""}</span>
            </div>
          </div>
          <div class="feedback-detail-body">
            <p>${item.note || "这一维还可以继续展开。"}</p>
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadDashboardData() {
  try {
    const [summary, history, profile] = await Promise.all([
      request("/api/user/home-summary"),
      request("/api/training/history"),
      request("/api/user/profile"),
    ]);
    state.summary = summary;
    state.history = history;
    state.profile = profile;
    setMode("", "backend");
  } catch (error) {
    setMode("", "error");
    throw error;
  }
}

async function refreshAccountState() {
  state.account = await request("/api/account/state");
  const authToken = state.account?.auth?.authToken || "";
  if (authToken) {
    setAuthToken(authToken);
  }
  return state.account;
}

function isAccountActive() {
  return state.account?.auth?.loggedIn && state.account?.status === "active";
}

function hasLoggedInAccount() {
  return Boolean(state.account?.auth?.loggedIn);
}

function renderLanding() {
  const template = document.querySelector("#landing-template").content.cloneNode(true);
  app.replaceChildren(template);

  const summary = state.summary;
  const latest = state.history[0];
  const dailyQuote = summary?.dailyQuote;
  if (dailyQuote?.text) {
    document.querySelector("#daily-quote-text").textContent = dailyQuote.text;
    document.querySelector("#daily-quote-author").textContent = `来自 ${dailyQuote.author || "佚名"}`;
  }
  document.querySelector("#refresh-daily-quote")?.addEventListener("click", async () => {
    const button = document.querySelector("#refresh-daily-quote");
    button.disabled = true;
    try {
      const nextSummary = await request("/api/user/home-summary");
      state.summary = nextSummary;
      const nextQuote = nextSummary?.dailyQuote;
      if (nextQuote?.text) {
        document.querySelector("#daily-quote-text").textContent = nextQuote.text;
        document.querySelector("#daily-quote-author").textContent = `来自 ${nextQuote.author || "佚名"}`;
      }
    } catch (error) {
      toastError(error, "换一句失败，请稍后再试。");
    } finally {
      button.disabled = false;
    }
  });

  document.querySelector("#hero-stats").innerHTML = [
    { value: "16", label: "每轮议题词卡" },
    { value: "2min", label: "构思热身" },
    { value: "2min", label: "表达时长" },
    { value: "3轮", label: "递进教练反馈" },
  ]
    .map(
      (item) => `
        <div class="stat-card">
          <strong>${item.value}</strong>
          <span>${item.label}</span>
        </div>
      `
    )
    .join("");

  document.querySelector("#latest-card").innerHTML = latest
    ? `
      <div class="panel-title-row">
        <div>
          <span class="eyebrow">最近一次训练</span>
          <h3>${latest.title}</h3>
        </div>
        <div class="clock-pill">${latest.score}</div>
      </div>
      <p>${latest.summary}</p>
    `
    : `
      <div class="panel-title-row">
        <div>
          <span class="eyebrow">第一次训练</span>
          <h3>还没有历史记录</h3>
        </div>
      </div>
      <p>先开始第一轮，把两张词卡之间的关系讲清楚。</p>
    `;

  document.querySelector("#start-training").addEventListener("click", async () => {
    try {
      if (!state.account) {
        await refreshAccountState();
      }
      if (!hasLoggedInAccount()) {
        state.tab = "train";
        state.screen = "auth";
        render();
        return;
      }
      await startTraining();
    } catch (error) {
      showToast(error.message || "启动训练失败，请稍后再试");
    }
  });
}

async function startTraining() {
  const result = await request("/api/training/session/create", { method: "POST" });
  if (result.blocked) {
    state.tab = "profile";
    state.screen = hasLoggedInAccount() ? "plans" : "auth";
    render();
    return;
  }

  state.feedback = null;
  state.training = result.state;
  state.screen = "training";
  render();
}

function renderTraining() {
  state.feedback = null;
  const template = document.querySelector("#training-template").content.cloneNode(true);
  app.replaceChildren(template);

  document.querySelector("#round-label").textContent = `第 ${state.training.roundNo} 轮`;

  const selectedRow = document.querySelector("#selected-row");
  selectedRow.innerHTML = state.training.selectedCards.length
    ? state.training.selectedCards.map((item) => selectedChip(item.word)).join("")
    : `<span class="muted">翻开词卡，选中 2 张。</span>`;

  const grid = document.querySelector("#matrix-grid");
  grid.innerHTML = state.training.cards
    .map((card) => {
      const text = card.state === "hidden" ? "⚡" : card.word;
      const classes = [
        "matrix-card",
        card.state === "hidden" ? "hidden" : "",
        card.state === "used" ? "used" : "",
        card.isSelected ? "selected" : "",
      ]
        .filter(Boolean)
        .join(" ");
      return `<button class="${classes}" data-card="${card.id}">${text}</button>`;
    })
    .join("");

  let pendingCardId = "";
  grid.querySelectorAll(".matrix-card").forEach((button) => {
    const toggleCard = async () => {
      const cardId = button.dataset.card;
      const now = Date.now();
      if (now - (recentCardToggles.get(cardId) || 0) < 450) return;
      if (pendingCardId) return;
      recentCardToggles.set(cardId, now);
      pendingCardId = cardId;
      button.disabled = true;
      try {
        state.training = (await request("/api/training/session/current/cards/toggle", {
          method: "POST",
          body: JSON.stringify({ cardId }),
        })).state;
        renderTraining();
      } catch (error) {
        if ((error.message || "").includes("一次只能选 2 张卡")) {
          showToast("你已经选择 2 个啦～");
          return;
        }
        showToast(error.message || "选词失败");
      } finally {
        pendingCardId = "";
        button.disabled = false;
      }
    };
    button.addEventListener("click", toggleCard);
  });

  const refreshBatchButton = document.querySelector("#refresh-batch");
  const allCardsRevealed = state.training.flippedCount >= state.training.totalCount;
  refreshBatchButton.classList.toggle("is-visible", allCardsRevealed);
  refreshBatchButton.addEventListener("click", async () => {
    if (!allCardsRevealed) {
      return;
    }
    refreshBatchButton.disabled = true;
    refreshBatchButton.textContent = "刷新中...";
    try {
      const result = await request("/api/training/session/refresh", { method: "POST" });
      if (result.blocked) {
        state.tab = "profile";
        state.screen = hasLoggedInAccount() ? "plans" : "auth";
        render();
        return;
      }
      state.feedback = null;
      state.training = result.state;
      state.screen = "training";
      render();
    } catch (error) {
      refreshBatchButton.disabled = false;
      refreshBatchButton.textContent = "换一批";
      showToast(error.message || "换词失败");
    }
  });

  document.querySelector("#proceed-training").addEventListener("click", async () => {
    if (state.training?.isComplete) {
      await startTraining();
      return;
    }
    if ((state.training?.selectedCount || 0) !== 2) {
      showToast("先选 2 张词卡");
      return;
    }
    state.screen = "thinking";
    render();
  });

  document.querySelector("#training-back").addEventListener("click", () => {
    state.screen = "landing";
    render();
  });
}

function renderThinking() {
  const template = document.querySelector("#thinking-template").content.cloneNode(true);
  app.replaceChildren(template);

  document.querySelector("#thinking-words").innerHTML = state.training.selectedCards
    .map((item) => selectedChip(item.word))
    .join("");

  let seconds = 120;
  const clock = document.querySelector("#thinking-clock");
  clock.textContent = "02:00";
  state.timers.thinking = setInterval(() => {
    seconds -= 1;
    const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
    const ss = String(seconds % 60).padStart(2, "0");
    clock.textContent = `${mm}:${ss}`;
    if (seconds <= 0) {
      clearTimers();
      state.training.draftText = "";
      state.screen = "speaking";
      render();
    }
  }, 1000);

  document.querySelector("#skip-thinking").addEventListener("click", () => {
    clearTimers();
    state.training.draftText = "";
    state.screen = "speaking";
    render();
  });

  document.querySelector("#thinking-back").addEventListener("click", () => {
    clearTimers();
    state.screen = "training";
    render();
  });
}

function analyzingStepsForAttempt(attemptNo) {
  if (attemptNo === 1) {
    return [
      "正在听你这次主要想证明什么。",
      "正在判断两个词之间的关系有没有讲清楚。",
      "正在看你的例子有没有支撑观点。",
      "正在评估六个维度的得分。",
      "正在整理这轮最值得保留的地方。",
      "正在生成下一步练习建议。",
    ];
  }
  if (attemptNo === 2) {
    return [
      "正在对比你和上一轮的变化。",
      "正在看这次有没有把建议讲得更具体。",
      "正在评估哪些维度变好了。",
      "正在检查这轮表达有没有更聚焦。",
      "正在整理阶段性教练版本。",
      "正在判断是否还需要再练一轮。",
    ];
  }
  return [
    "正在综合前三轮表达。",
    "正在挑出最稳定、最有力量的材料。",
    "正在整理最终教练版本。",
    "正在检查最终表达是否讲通。",
    "正在汇总本组词的最终建议。",
    "正在生成这次训练的完整记录。",
  ];
}

function buildMockTranscript(words) {
  const first = words[0] || "自由";
  const second = words[1] || "束缚";
  return [
    `我的观点是，${first}是一种${second}。`,
    `这句话听起来有点反直觉，但我想表达的是，${first}和${second}并不是互相排斥的，它们在很多真实处境里其实会同时出现。`,
    `比如一个人在工作选择、亲密关系或者自我要求里，表面上在处理${first}，本质上也在暴露他对${second}的理解，因为你怎么取舍、承担什么代价、愿不愿意面对后果，都会把这两个词绑在一起。`,
    `所以我不把${first}看成一个孤立的概念，而更愿意把它理解成通向${second}的一种过程，或者说，${first}本身就带着${second}的影子，这样这句话就成立了。`,
  ].join("\n");
}

function renderSpeaking() {
  const template = document.querySelector("#speaking-template").content.cloneNode(true);
  app.replaceChildren(template);
  const words =
    state.training.selectedCards?.length
      ? state.training.selectedCards.map((item) => item.word)
      : (state.feedback?.selectedWords || []);
  trackTrainingEvent("speaking_page_entered", words);
  document.querySelector("#speaking-words").innerHTML = words.map(selectedChip).join("");
  const speakingEyebrow = document.querySelector(".speaking-stage .eyebrow");
  const speakingAdviceTitle = document.querySelector(".speaking-advice-title");
  const speakingTip = document.querySelector(".speaking-advice-text");
  const attemptNo = (state.training?.attemptCount || 0) + 1;
  const lastFeedback = state.training?.feedback || state.feedback || null;
  if (attemptNo > 1) {
    speakingEyebrow.textContent = `第 ${attemptNo} 轮表达`;
    speakingAdviceTitle.textContent = "这一轮只改一个地方。";
    speakingTip.textContent = lastFeedback?.improvement || "这一轮只做一件事：先把你真正想证明的那个点说准，再补一个具体的人和一个具体时刻。";
  }

  const textarea = document.querySelector("#transcript-input");
  const shouldStartBlank =
    (state.training?.attemptCount || 0) === 0 ||
    !state.training?.draftText ||
    state.training?.draftText === "__CLEAR__";
  textarea.value = shouldStartBlank ? "" : state.training.draftText || "";

  let seconds = 120;
  const clock = document.querySelector("#speaking-clock");
  const updateSpeakingClock = () => {
    const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
    const ss = String(seconds % 60).padStart(2, "0");
    clock.textContent = `${mm}:${ss}`;
    clock.classList.toggle("is-urgent", seconds <= 30);
  };
  updateSpeakingClock();
  state.timers.speaking = setInterval(() => {
    seconds -= 1;
    updateSpeakingClock();
    if (seconds <= 0) {
      clearTimers();
    }
  }, 1000);

  textarea.addEventListener("input", () => {
    state.training.draftText = textarea.value;
    window.clearTimeout(draftSaveTimer);
    draftSaveTimer = window.setTimeout(() => {
      const draftText = textarea.value;
      latestDraftSave = request("/api/training/session/current/draft", {
        method: "POST",
        body: JSON.stringify({ draftText }),
      })
        .then((session) => {
          if (state.training?.sessionId === session?.sessionId) {
            state.training = { ...session, draftText };
          }
        })
        .catch((error) => {
          console.warn("draft save failed", error);
        });
    }, 700);
  });

  document.querySelector("#speaking-back").addEventListener("click", () => {
    state.screen = "thinking";
    render();
  });
  document.querySelector("#reset-record").addEventListener("click", async () => {
    textarea.value = "";
    state.training = await request("/api/training/session/current/draft", {
      method: "POST",
      body: JSON.stringify({ draftText: "" }),
    });
    textarea.focus();
  });

  document.querySelector("#submit-speaking").addEventListener("click", async () => {
    if (!textarea.value.trim()) {
      showToast("先讲一点出来，再交给教练点评");
      return;
    }
    window.clearTimeout(draftSaveTimer);
    trackTrainingEvent("coach_feedback_submit_clicked", words);
    state.training.draftText = textarea.value;
    state.screen = "analyzing";
    render();

    try {
      state.feedback = await request("/api/training/session/current/submit", {
        method: "POST",
        body: JSON.stringify({
          transcriptText: textarea.value,
          selectedWords: words,
          pairTitle: words.length === 2 ? `${words[0]} + ${words[1]}` : "",
        }),
      });
      state.screen = "feedback";
      render();
      refreshAndRenderIf(
        () => state.screen === "feedback",
        () => state.feedback.isFinal ? refreshSummaryHistoryAndProfile() : refreshHistoryAndProfile(),
        "反馈后资料刷新"
      );
    } catch (error) {
      if ((error?.message || "").includes("权益") || (error?.message || "").includes("开通") || (error?.message || "").includes("续费")) {
        trackTrainingEvent("coach_feedback_blocked_payment", words);
        try {
          state.training = await request("/api/training/session/current/draft", {
            method: "POST",
            body: JSON.stringify({ draftText: textarea.value }),
          });
        } catch (draftError) {
          // Keep the local draft even if the network hiccups before the plan page.
        }
        state.training.draftText = textarea.value;
        setTrainingRecovery("submit_payment_required");
        showToast("当前点评次数不足，正在跳转计划页...");
        state.tab = "profile";
        await refreshAccountState();
        state.screen = "plans";
        render();
        return;
      }
      toastError(error, "这次教练点评生成失败，请稍后重试。");
      state.screen = "speaking";
      render();
    }
  });
}

function renderAnalyzing() {
  const template = document.querySelector("#analyzing-template").content.cloneNode(true);
  app.replaceChildren(template);
  const subtitle = document.querySelector("#analyzing-subtitle");
  const statusList = document.querySelector("#analyzing-status-list");
  const nextAttempt = (state.training?.attemptCount || 0) + 1;
  subtitle.textContent = nextAttempt === 1
    ? "教练会从多个维度，为你整理出这一轮最值得保留的观点和建议。"
    : nextAttempt === 2
      ? "这次会重点看：你有没有把上轮建议讲得更具体、更聚焦。"
      : "这次会把前三轮材料一起看完，然后给你最终总评和整理版。";
  const progressLabels = nextAttempt === 1
    ? ["理解核心观点", "分析逻辑结构", "提炼表达亮点", "定位提升空间", "生成反馈建议"]
    : nextAttempt === 2
      ? ["对比上一轮变化", "检查建议完成度", "提炼新的亮点", "定位仍卡住的地方", "整理阶段性反馈"]
      : ["综合前三轮表达", "挑出稳定材料", "整理最终版本", "检查表达是否讲通", "生成完整记录"];
  statusList.innerHTML = `
    <div class="coach-progress-line"></div>
    ${progressLabels
      .map(
        (item, index) => `
          <div class="coach-wait-step" style="--i:${index}">
            <div class="coach-progress-node">
              <svg class="coach-check" viewBox="0 0 16 12"><path d="M2 6.5 6.4 10 14 2"></path></svg>
            </div>
            <div class="coach-step-text">${item}</div>
          </div>
        `
      )
      .join("")}
  `;
}

function currentFeedbackViewModel() {
  const feedback = state.feedback || {};
  const isFinal = Boolean(feedback.isFinal);
  const normalizedDetails = normalizeDetails(feedback.visibleDetails || feedback.details || []);
  const previousDetails = findPreviousAttempt(feedback);
  const previousAttempt = feedback.attemptHistory?.find(
    (item) => item.attemptNo === (feedback.attemptNo || 1) - 1
  );
  const previousTotal = typeof previousAttempt?.feedback?.totalScore === "number"
    ? previousAttempt.feedback.totalScore
    : null;
  const totalDelta = previousTotal === null ? null : (feedback.totalScore || 0) - previousTotal;
  const transcriptText = feedback.transcriptText || state.training?.draftText || feedback.excerpt || "";
  const rewriteParagraphs = String(feedback.rewrite || "")
    .split(/\n{2,}/)
    .filter(Boolean);

  return {
    feedback,
    isFinal,
    isProgressRound: !isFinal,
    normalizedDetails,
    previousDetails,
    totalDelta,
    transcriptText,
    rewriteParagraphs,
  };
}

function latestAttemptForHistoryItem(item) {
  const attempts = item?.attempts || [];
  if (attempts.length) {
    return attempts[attempts.length - 1];
  }
  return null;
}

function historyPairTitle(item, feedback = {}) {
  const pair = [item?.pair, feedback?.selectedWords, item?.finalFeedback?.selectedWords]
    .find((candidate) => Array.isArray(candidate) && candidate.filter(Boolean).length === 2);
  if (pair) {
    return pair.map((word) => String(word).trim()).filter(Boolean).join(" + ");
  }
  const title = String(item?.title || "").replace(/^第\d+轮[｜|]\s*/, "").trim();
  return title && title !== "+" ? title : "本轮词组";
}

function findHistoryRecord() {
  return state.history.find((item) => String(item.id) === String(state.selectedHistoryId)) || null;
}

function selectedHistoryAttempt(record) {
  if (!record) return null;
  const attempts = record.attempts || [];
  if (!attempts.length) return null;
  return attempts.find((item) => Number(item.attemptNo) === Number(state.selectedHistoryRound)) || attempts[attempts.length - 1];
}

function safeTranscriptForHistory(attempt, record, feedback) {
  const blocked = new Set(
    [
      feedback?.improvement,
      feedback?.summary,
      feedback?.rewrite,
    ]
      .filter(Boolean)
      .map((item) => String(item).trim())
  );
  const looksLikeCoachAdvice = (text) => {
    const value = String(text || "");
    const markers = ["下一轮", "这一轮", "你可以", "建议", "听众", "表达更", "逻辑", "观点", "场景讲清楚"];
    return markers.filter((marker) => value.includes(marker)).length >= 3;
  };
  const candidates = [
    attempt?.transcriptText,
    record?.transcriptText,
    record?.excerpt,
    ...(record?.attempts || []).slice().reverse().map((item) => item.transcriptText),
  ];
  const transcript = candidates
    .map((item) => String(item || "").trim())
    .find((item) => item && !blocked.has(item) && !looksLikeCoachAdvice(item));
  return transcript || "这轮表达原文没有正确保存。";
}

function renderTranscriptCard(transcriptText) {
  return `
    <button class="ref-toggle" type="button">
      <div class="ref-row-title">
        <span class="ref-mini-icon doc"></span>
        <div>
          <div>你的表达</div>
          <div class="ref-caption">展开文字稿</div>
        </div>
      </div>
    </button>
    <div class="ref-accordion-body">
      <div class="ref-transcript">${transcriptText || "这次表达原文会保存在这里。"}</div>
    </div>
  `;
}

function renderSuggestionsCard(feedback) {
  return `
    <div class="ref-row-title"><span class="ref-mini-icon chat"></span><div>本轮表达建议</div></div>
      <div class="ref-advice-list">
        <div class="ref-subcard good">
        <div class="ref-subhead"><span class="ref-mini-icon soft-green"></span>这一轮好的地方</div>
        <ul>
          ${(feedback.strengths || ["观点已经开始成形，听的人能知道你想证明什么。"])
            .map((item) => `<li><span class="ref-point-check">✓</span><span>${item}</span></li>`)
            .join("")}
        </ul>
      </div>
      <div class="ref-subcard improve">
        <div class="ref-subhead"><span class="ref-mini-icon soft-orange"></span>下一轮只改这里</div>
        <p class="ref-improve-text">${feedback.improvement || "继续补充更具体的场景和细节，让表达不只是讲明白，而是更有画面感。"}</p>
      </div>
    </div>
    <div class="ref-card-action-slot" id="coach-demo-action-slot"></div>
  `;
}

function renderCoachRewriteCard(feedback, rewriteParagraphs) {
  return `
    <span class="coach-demo-quote-mark" aria-hidden="true">“</span>
    <div class="ref-scroll-area">
      ${rewriteParagraphs.map((item) => `<p>${item}</p>`).join("")}
    </div>
    <img class="ref-fox-comment" src="/assets/visual/coach/fox-coach-comment-01.webp" alt="狐狸表达教练" />
    <div class="ref-bottom-wave"></div>
  `;
}

function bindFeedbackActionButtons(isProgressRound, hasRewrite) {
  const continueButton = document.querySelector("#continue-training");
  const retryButton = document.querySelector("#retry-speaking");

  if (!continueButton || !retryButton) {
    return;
  }

  const attemptNo = Number(state.feedback?.attemptNo || 1);
  if (isProgressRound) {
    continueButton.textContent = "继续本组";
    retryButton.style.display = "";
    retryButton.textContent = "更换新词";
  } else {
    continueButton.textContent = "更换新词";
    retryButton.style.display = "none";
    retryButton.textContent = "更换新词";
  }
  document.querySelector(".ref-btns")?.classList.toggle("has-two-actions", retryButton.style.display !== "none");

  continueButton.addEventListener("click", async () => {
    if (isProgressRound) {
      const result = await request("/api/training/session/current/continue", { method: "POST" });
      if (result.route.includes("speaking")) {
        state.training = result.state || state.training;
        state.training.draftText = "__CLEAR__";
        state.screen = "speaking";
      }
      render();
      return;
    }
    const result = await request("/api/training/session/current/continue", { method: "POST" });
    if (result.route.includes("training")) {
      state.feedback = null;
      state.training = result.state || state.training;
      state.screen = "training";
    } else if (result.route.includes("account/plan")) {
      state.tab = "profile";
      await refreshAccountState();
      state.screen = "plans";
    } else {
      state.screen = "landing";
    }
    render();
  });

  retryButton.addEventListener("click", async () => {
    if (isProgressRound) {
      state.feedback = await request("/api/training/session/current/finish", { method: "POST" });
      await refreshSummaryHistoryAndProfile();
      const result = await request("/api/training/session/current/continue", { method: "POST" });
      state.feedback = null;
      if (result.route.includes("training")) {
        state.training = result.state || state.training;
        state.screen = "training";
      } else if (result.route.includes("account/plan")) {
        state.tab = "profile";
        await refreshAccountState();
        state.screen = "plans";
      } else {
        state.screen = "landing";
      }
      render();
      return;
    }
    state.training = await request("/api/training/session/current");
    if (!state.training.selectedCards?.length && state.feedback?.selectedWords?.length) {
      state.training.selectedCards = state.feedback.selectedWords.map((word, index) => ({
        id: `retry-word-${index}`,
        word,
      }));
    }
    state.training.draftText = "__CLEAR__";
    state.screen = "speaking";
    render();
  });
}

function renderFeedback() {
  const template = document.querySelector("#feedback-template").content.cloneNode(true);
  app.replaceChildren(template);

  const {
    feedback,
    isFinal,
    isProgressRound,
    transcriptText,
    rewriteParagraphs,
  } = currentFeedbackViewModel();

  document.querySelector("#feedback-title").textContent = isFinal
    ? (feedback.pairTitle || "本次点评")
    : `第 ${feedback.attemptNo || 1} 轮｜教练反馈`;
  document.querySelector("#feedback-summary").textContent = feedback.summary || "你的教练已经完成这次分析。";
  document.querySelector("#feedback-score").textContent = feedback.totalScore ?? "-";
  document.querySelector("#feedback-model").textContent = feedback.aiModel
    ? `模型：${feedback.aiModel}`
    : "";

  document.querySelector("#feedback-transcript").innerHTML = renderTranscriptCard(transcriptText);
  document.querySelector("#feedback-transcript .ref-toggle").addEventListener("click", () => {
    const isOpen = document.querySelector("#feedback-transcript").classList.toggle("open");
    document.querySelector("#feedback-transcript .ref-caption").textContent = isOpen ? "收起文字稿" : "展开文字稿";
  });

  document.querySelector("#feedback-suggestions").innerHTML = renderSuggestionsCard(feedback);
  const openEvaluation = () => {
    state.screen = "feedbackEvaluation";
    render();
  };
  document.querySelector("#open-feedback-evaluation").addEventListener("click", openEvaluation);

  const coachDemoButton = document.querySelector("#open-coach-demo");
  const coachDemoSlot = document.querySelector("#coach-demo-action-slot");
  if (coachDemoButton && coachDemoSlot) {
    coachDemoSlot.appendChild(coachDemoButton);
  }
  if (rewriteParagraphs.length) {
    coachDemoButton.textContent = feedback.rewriteMode === "demo" ? "查看教练示范 ›" : "查看教练整理 ›";
    coachDemoButton.addEventListener("click", () => {
      state.screen = "coachDemo";
      render();
    });
  } else {
    coachDemoButton.classList.add("is-disabled");
    coachDemoButton.textContent = "暂无教练整理版";
  }

  document.querySelector(".feedback-ref-back").addEventListener("click", () => {
    state.screen = "speaking";
    render();
  });

  bindFeedbackActionButtons(isProgressRound, rewriteParagraphs.length > 0);
}

function renderFeedbackEvaluation() {
  const template = document.querySelector("#feedback-evaluation-template").content.cloneNode(true);
  app.replaceChildren(template);
  const { feedback, normalizedDetails, previousDetails, totalDelta } = currentFeedbackViewModel();
  const deltaText = totalDelta === null
    ? ""
    : totalDelta === 0
      ? "相比同组词汇上一轮持平"
      : `相比同组词汇上一轮 ${totalDelta > 0 ? `+${totalDelta}` : totalDelta}`;

  document.querySelector("#evaluation-title").textContent = `第 ${feedback.attemptNo || 1} 轮评分`;
  document.querySelector("#evaluation-radar").innerHTML = `
    <div class="panel-title-row ref-section-title">
      <h3>六维评分</h3>
      ${deltaText ? `<span class="muted">${deltaText}</span>` : ""}
    </div>
    ${renderRadar(normalizedDetails, feedback.totalScore)}
  `;
  document.querySelector("#evaluation-details").innerHTML = `
      <div class="panel-title-row ref-section-title">
        <h3>评分拆解</h3>
      </div>
    ${renderEvaluationDetails(normalizedDetails, previousDetails)}
  `;

  document.querySelector("#evaluation-back").addEventListener("click", () => {
    state.screen = "feedback";
    render();
  });
}

function renderCoachDemo() {
  const template = document.querySelector("#coach-demo-template").content.cloneNode(true);
  app.replaceChildren(template);
  const { feedback, rewriteParagraphs } = currentFeedbackViewModel();
  document.querySelector("#coach-demo-title").textContent =
    feedback.rewriteMode === "demo" ? "教练示范版" : "教练整理版";
  document.querySelector("#coach-demo-content").innerHTML = rewriteParagraphs.length
    ? renderCoachRewriteCard(feedback, rewriteParagraphs)
    : `
      <span class="coach-demo-quote-mark" aria-hidden="true">“</span>
      <div class="ref-scroll-area">
        <p>这一轮先不出整理版。先按本轮建议再讲一次，教练会在下一轮帮你整理出更完整的表达。</p>
      </div>
      <img class="ref-fox-comment" src="/assets/visual/coach/fox-coach-comment-01.webp" alt="狐狸表达教练" />
    `;
  const goBack = () => {
    state.screen = "feedback";
    render();
  };
  document.querySelector("#coach-demo-back").addEventListener("click", goBack);
  document.querySelector("#coach-demo-close").addEventListener("click", goBack);
}

function renderHistory() {
  const template = document.querySelector("#history-template").content.cloneNode(true);
  app.replaceChildren(template);
  document.querySelector("#history-back")?.addEventListener("click", () => {
    state.tab = "train";
    state.screen = hasLoggedInAccount() && isAccountActive() ? "landing" : "auth";
    render();
  });
  const list = document.querySelector("#history-list");
  if (!state.history.length) {
    list.innerHTML = `
      <article class="record-card-v2">
        <div class="feedback-card">
          <div class="feedback-title"><span>还没有训练记录</span></div>
          <div class="feedback-text">完成第一组表达后，这里会自动保存每轮原文、评分和教练整理版。</div>
        </div>
      </article>
    `;
    return;
  }

  list.innerHTML = state.history
    .map((item) => {
      const latestAttempt = latestAttemptForHistoryItem(item);
      const latestFeedback = latestAttempt?.feedback || item.finalFeedback || {};
      const latestScore = latestFeedback.totalScore ?? item.score ?? "-";
      const latestSummary = latestFeedback.summary || item.summary || "这组训练已经保存，可以点开继续复盘。";
      const latestRound = latestAttempt?.attemptNo || item.attemptCount || 1;
      const pairTitle = historyPairTitle(item, latestFeedback);
      return `
        <article class="record-card-v2" data-history-open="${item.id}">
          <div class="record-main">
            <div>
              <div class="record-word"><span class="round-badge">第${latestRound}轮</span>${pairTitle}</div>
              <div class="record-date">${item.timeLabel} · 共 ${item.attemptCount || 1} 轮教练反馈</div>
            </div>
            <div class="record-score"><div class="n">${latestScore}</div><div class="l">总分</div></div>
          </div>
          <div class="feedback-card">
            <div class="feedback-title"><span>教练反馈</span><span>›</span></div>
            <div class="feedback-text">${latestSummary}</div>
          </div>
        </article>
      `;
    })
    .join("");

  list.querySelectorAll("[data-history-open]").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedHistoryId = node.dataset.historyOpen;
      const record = state.history.find((item) => String(item.id) === String(state.selectedHistoryId));
      state.selectedHistoryRound = latestAttemptForHistoryItem(record)?.attemptNo || record?.attemptCount || 1;
      state.screen = "historyDetail";
      render();
    });
  });
}

function renderHistoryDetail() {
  const record = findHistoryRecord();
  if (!record) {
    state.screen = "history";
    render();
    return;
  }

  const attempt = selectedHistoryAttempt(record);
  const feedback = attempt?.feedback || record.finalFeedback || {};
  const details = normalizeDetails(feedback.visibleDetails || feedback.details || record.details || []);
  const rewriteParagraphs = String(feedback.rewrite || "")
    .split(/\n{2,}/)
    .filter(Boolean);

  const template = document.querySelector("#history-detail-template").content.cloneNode(true);
  app.replaceChildren(template);
  document.querySelector("#history-detail-title").textContent = historyPairTitle(record, feedback);
  document.querySelector("#history-detail-time").textContent = record.timeLabel;
  document.querySelector("#history-detail-score").innerHTML = `${feedback.totalScore ?? record.score ?? "-"}<small>/100</small>`;
  document.querySelector("#history-detail-transcript").textContent =
    safeTranscriptForHistory(attempt, record, feedback);
  const transcriptToggle = document.querySelector("#history-detail-transcript-toggle");
  const transcriptNode = document.querySelector("#history-detail-transcript");
  transcriptToggle.addEventListener("click", () => {
    const collapsed = transcriptNode.classList.toggle("is-collapsed");
    transcriptToggle.querySelector("span").textContent = collapsed ? "展开" : "收起";
    transcriptToggle.classList.toggle("open", !collapsed);
  });

  const roundTabs = document.querySelector("#history-round-tabs");
  roundTabs.innerHTML = (record.attempts || []).map((item) => `
    <button class="round-tab ${Number(item.attemptNo) === Number(state.selectedHistoryRound) ? "active" : ""}" type="button" data-round="${item.attemptNo}">
      第${item.attemptNo}轮
    </button>
  `).join("");
  roundTabs.querySelectorAll("[data-round]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedHistoryRound = Number(button.dataset.round);
      render();
    });
  });

  document.querySelector("#history-detail-scores").innerHTML = `
    <h3 class="section-title section-title--with-icon"><span class="ref-mini-icon chart"></span>六维评分</h3>
    <div class="dim-grid">
      ${details.map((item, index) => `
        <div class="dim">
          <span class="ref-eval-icon dim-${index + 1}"></span>
          <div class="dim-name">${item.label}</div>
          <div class="dim-val">${item.score}</div>
        </div>
      `).join("")}
    </div>
  `;
  document.querySelector("#history-detail-summary").textContent =
    feedback.summary || record.summary || "这一轮点评已经保存。";

  const strengths = feedback.strengths || [];
  const improvement = feedback.improvement
    ? [feedback.improvement]
    : [];
  document.querySelector("#history-detail-strengths").innerHTML = strengths.length
    ? strengths.map((item) => `<div class="history-good"><span class="ref-point-check">✓</span><span>${item}</span></div>`).join("")
    : `<div class="history-good"><span class="ref-point-check">✓</span><span>这一轮的亮点已经在上面的教练总结里整理出来了。</span></div>`;
  document.querySelector("#history-detail-improvement").innerHTML = improvement.length
    ? improvement.map((item) => `<div class="history-warn">${item}</div>`).join("")
    : `<div class="history-warn">这一轮没有额外的待提升说明。</div>`;

  const rewriteWrap = document.querySelector("#history-detail-rewrite-wrap");
  if (rewriteParagraphs.length) {
    document.querySelector("#history-detail-rewrite").innerHTML = rewriteParagraphs.map((item) => `<p>${item}</p>`).join("");
  } else {
    rewriteWrap.style.display = "none";
  }

  document.querySelector("#history-detail-back").addEventListener("click", () => {
    state.screen = "history";
    render();
  });
}

async function refreshOrders() {
  state.orders = await request("/api/account/orders");
}

function renderOrders() {
  const template = document.querySelector("#orders-template").content.cloneNode(true);
  app.replaceChildren(template);
  const list = document.querySelector("#orders-list");
  if (!state.orders.length) {
    list.innerHTML = `
      <article class="order-card card">
        <div class="order-title">还没有支付订单</div>
        <div class="order-lines">
          <div class="order-line"><span class="order-label">说明：</span><span>你后续购买的训练计划会显示在这里，方便回看金额、次数和有效天数。</span></div>
        </div>
      </article>
    `;
  } else {
    list.innerHTML = state.orders
      .map(
        (item) => {
          const isPaid = item.statusRaw === "paid" || item.status === "已支付";
          return `
          <article class="order-card card ${isPaid ? "is-paid" : "is-pending"}">
            <div class="order-title-row">
              <div class="order-title">${item.planName}</div>
              <span class="order-status ${isPaid ? "paid" : "pending"}">${isPaid ? "已支付" : "未完成支付"}</span>
            </div>
            <div class="order-lines">
              <div class="order-line"><span class="order-label">订单编号：</span><span>${item.orderNo}</span></div>
              <div class="order-line"><span class="order-label">${isPaid ? "支付时间：" : "下单时间："}</span><span>${formatDateTime(item.paidAt || item.createdAt)}</span></div>
              <div class="order-line"><span class="order-label">${isPaid ? "实付金额：" : "订单金额："}</span><span>${item.displayAmount}</span></div>
              <div class="order-line"><span class="order-label">点评次数：</span><span>${item.credits}次</span></div>
              <div class="order-line"><span class="order-label">有效天数：</span><span>${item.days}天</span></div>
              ${isPaid ? "" : `<div class="order-pending-note">未支付订单不会占用权益，可重新下单。</div>`}
            </div>
          </article>
        `;
        }
      )
      .join("");
  }
  document.querySelector("#orders-back").addEventListener("click", () => {
    state.screen = "profile";
    render();
  });
}

function renderAuth() {
  const template = document.querySelector("#auth-template").content.cloneNode(true);
  app.replaceChildren(template);

  const modeButtons = Array.from(document.querySelectorAll(".auth-tab"));
  const phoneInput = document.querySelector("#auth-phone");
  const passwordInput = document.querySelector("#auth-password");
  const confirmWrap = document.querySelector("#auth-confirm-wrap");
  const confirmInput = document.querySelector("#auth-confirm-password");
  const message = document.querySelector("#auth-message");
  const submitButton = document.querySelector("#auth-submit");
  const agreementLink = document.querySelector("#agreement-link");
  const inputs = [phoneInput, passwordInput, confirmInput];

  const isAuthReady = () => {
    const phoneReady = phoneInput.value.trim().length > 0;
    const passwordReady = passwordInput.value.length > 0;
    const confirmReady = state.authMode !== "register" || confirmInput.value.length > 0;
    return phoneReady && passwordReady && confirmReady;
  };

  const syncSubmitState = () => {
    submitButton.disabled = !isAuthReady();
  };

  const syncMode = () => {
    modeButtons.forEach((button) => {
      const isCurrentMode = button.dataset.authMode === state.authMode;
      button.classList.toggle("active", isCurrentMode);
      button.classList.toggle("is-active", isCurrentMode);
    });
    confirmWrap.style.display = state.authMode === "register" ? "" : "none";
    const freeCredits = state.account?.freeTrialCredits ?? 1;
    message.textContent = state.authMode === "register" ? `注册成功后，你会自动获得 ${freeCredits} 次免费教练点评。` : "";
    message.style.display = state.authMode === "register" ? "" : "none";
    submitButton.textContent = state.authMode === "register" ? "注册并开始训练" : "登录并继续训练";
    syncSubmitState();
  };

  const bindEye = (buttonId, input) => {
    const button = document.querySelector(buttonId);
    const syncEye = () => {
      const hidden = input.type === "password";
      button.innerHTML = hidden ? PASSWORD_EYE_CLOSED : PASSWORD_EYE_OPEN;
      button.setAttribute("aria-label", hidden ? "显示密码" : "隐藏密码");
      button.classList.toggle("is-open", !hidden);
    };
    syncEye();
    button.addEventListener("click", () => {
      input.type = input.type === "password" ? "text" : "password";
      syncEye();
    });
  };
  bindEye("#auth-password-eye", passwordInput);
  bindEye("#auth-confirm-eye", confirmInput);

  modeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.authMode = button.dataset.authMode;
      syncMode();
    });
  });

  inputs.forEach((input) => {
    input.addEventListener("input", syncSubmitState);
  });

  agreementLink?.addEventListener("click", (event) => {
    event.preventDefault();
    hideLoadingToast();
    window.location.assign(agreementLink.href);
  });

  syncMode();

  submitButton.addEventListener("click", async () => {
    if (!isAuthReady()) {
      showToast(state.authMode === "register" ? "请先填完手机号、密码和确认密码。" : "请先输入手机号和密码。");
      return;
    }
    const phone = phoneInput.value.trim();
    if (!/^1\d{10}$/.test(phone)) {
      showToast("请输入正确的 11 位手机号");
      return;
    }
    if (passwordInput.value.length < 6) {
      showToast("密码至少需要 6 位");
      return;
    }
    if (state.authMode === "register" && passwordInput.value !== confirmInput.value) {
      showToast("两次输入的密码不一致");
      return;
    }
    try {
      submitButton.disabled = true;
      showLoadingToast(state.authMode === "register" ? "正在注册..." : "正在登录...");
      const payload = state.authMode === "register"
        ? {
            phone,
            password: passwordInput.value,
            confirmPassword: confirmInput.value,
          }
        : {
            phone,
            password: passwordInput.value,
          };
      const account = await request(`/api/account/${state.authMode}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      state.account = account;
      setAuthToken(account?.auth?.authToken || "");
      await loadDashboardData();
      state.tab = "train";
      state.screen = "landing";
      hideLoadingToast();
      render();
    } catch (error) {
      hideLoadingToast();
      toastError(error, "账户操作失败，请稍后再试。");
      syncSubmitState();
    }
  });
}

function renderPlans() {
  trackTrainingEvent("plan_page_viewed", state.training?.selectedCards?.map((item) => item.word) || []);
  const template = document.querySelector("#plans-template").content.cloneNode(true);
  app.replaceChildren(template);
  const recoveryStrip = document.querySelector("#payment-recovery-strip");
  const refreshPaymentButton = document.querySelector("#refresh-payment-status");
  const pendingPayment = getPendingPayment();
  if (recoveryStrip) {
    recoveryStrip.hidden = !pendingPayment;
  }
  refreshPaymentButton?.addEventListener("click", () => {
    refreshPaymentStatus(true);
  });
  const stack = document.querySelector("#plans-stack");
  stack.innerHTML = (state.account?.plans || [])
    .map(
      (plan) => `
        <article class="plan-card-v2 ${plan.planId === "month30" ? "pro" : "hot"}">
          <img class="plan-visual" src="${plan.planId === "month30" ? "/assets/visual/other-elements/buy-option89-01.webp" : "/assets/visual/other-elements/buy-option29-01.webp"}" alt="" />
          <div class="plan-top">
            <div class="plan-name-v2">${plan.planName}</div>
            ${plan.planId === "month30" ? '<span class="plan-tag purple">强烈推荐</span>' : ""}
          </div>
          <div class="plan-desc-v2">${plan.tagline}</div>
          <div class="price-block">
            <div class="price-v2"><small>¥</small>${plan.displayPrice}</div>
          </div>
          <div class="benefit-list">
            <div class="benefit-item">${plan.totalCredits}次教练点评</div>
            <div class="benefit-item">开通后${plan.days}个自然日内有效</div>
            <div class="benefit-item">${plan.fitFor}</div>
          </div>
          <button class="buy-btn" data-plan-buy="${plan.planId}">立即购买</button>
        </article>
      `
    )
    .join("");

  stack.querySelectorAll("[data-plan-buy]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        showLoadingToast("正在跳转支付页面...");
        button.disabled = true;
        button.textContent = "正在跳转";
        const order = await request("/api/account/order", {
          method: "POST",
          body: JSON.stringify({ planId: button.dataset.planBuy }),
        });
        setPendingPayment(order);
        const form = document.createElement("form");
        form.method = order.paymentForm.method || "POST";
        form.action = order.paymentForm.action;
        Object.entries(order.paymentForm.fields || {}).forEach(([name, value]) => {
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = name;
          input.value = value;
          form.appendChild(input);
        });
        document.body.appendChild(form);
        form.submit();
      } catch (error) {
        hideLoadingToast();
        button.disabled = false;
        button.textContent = "立即购买";
        showToast(error.message || "发起支付失败");
      }
    });
  });

  document.querySelector("#plans-back")?.addEventListener("click", () => {
    if (hasLoggedInAccount()) {
      state.tab = "profile";
      state.screen = "profile";
    } else {
      state.tab = "train";
      state.screen = "auth";
    }
    render();
  });
}

function renderProfile() {
  const template = document.querySelector("#profile-template").content.cloneNode(true);
  app.replaceChildren(template);
  document.querySelector("#profile-back")?.addEventListener("click", () => {
    state.tab = "train";
    state.screen = hasLoggedInAccount() && isAccountActive() ? "landing" : "auth";
    render();
  });
  const account = state.account;
  const accountStatus = account?.status || "inactive";
  document.querySelector("#profile-phone").textContent = account?.auth?.phoneMasked
    ? `当前账户：${account.auth.phoneMasked}`
    : "当前账户还没有绑定手机号。";
  document.querySelector("#profile-trained").textContent = String(state.profile?.trainedGroups ?? 0);
  document.querySelector("#profile-remaining").textContent = String(account?.account?.remainingCredits ?? 0);
  document.querySelector("#profile-expire").textContent =
    account?.account?.expireAt ? String(account.account.expireAt).slice(0, 10) : "-";
  const statusNode = document.querySelector("#profile-status-text");
  const isActiveBenefit = accountStatus === "active";
  statusNode.textContent = isActiveBenefit ? "权益生效中" : "权益已失效";
  statusNode.classList.toggle("is-inactive", !isActiveBenefit);

  const openButton = document.querySelector("#open-membership");
  openButton.textContent = accountStatus === "active" ? "继续开启新的训练计划" : "选择训练计划并支付";
  openButton.addEventListener("click", () => {
    state.screen = "plans";
    render();
  });
  document.querySelector("#logout-account").addEventListener("click", async () => {
    if (!(await confirmDialog("确定要退出当前账号吗？"))) {
      return;
    }
    await request("/api/account/logout", { method: "POST", body: JSON.stringify({}) });
    setAuthToken("");
    state.account = await refreshAccountState();
    state.summary = null;
    state.training = null;
    state.feedback = null;
    state.history = [];
    state.profile = null;
    state.tab = "train";
    state.screen = "auth";
    render();
  });
  document.querySelector("#open-orders").addEventListener("click", async () => {
    await refreshOrders();
    state.screen = "orders";
    render();
  });
}

function render() {
  clearTimers();
  setActiveTab(state.tab);
  document.body.classList.toggle("is-landing", state.tab === "train" && state.screen === "landing");
  document.body.classList.toggle("is-mobile-flow", state.tab === "train" && state.screen !== "landing");
  document.body.classList.toggle("is-speaking", state.tab === "train" && state.screen === "speaking");
  document.body.classList.toggle("is-analyzing", state.tab === "train" && state.screen === "analyzing");
  document.body.classList.toggle("is-auth-screen", state.screen === "auth");
  document.body.classList.toggle(
    "is-account-flow",
    state.tab === "history" || state.tab === "profile" || ["auth", "plans"].includes(state.screen)
  );
  document.body.classList.toggle(
    "is-feedback-view",
    state.tab === "train" && ["feedback", "feedbackEvaluation", "coachDemo"].includes(state.screen)
  );
  if (state.tab === "history") {
    if (!hasLoggedInAccount()) {
      state.tab = "train";
      state.screen = "auth";
      render();
      return;
    }
    if (state.screen === "historyDetail") {
      renderHistoryDetail();
    } else {
      renderHistory();
    }
    return;
  }
  if (state.tab === "profile") {
    if (!hasLoggedInAccount()) {
      state.tab = "train";
      state.screen = "auth";
      render();
      return;
    }
    if (state.screen === "plans") {
      renderPlans();
    } else if (state.screen === "orders") {
      renderOrders();
    } else {
      renderProfile();
    }
    return;
  }

  switch (state.screen) {
    case "training":
      renderTraining();
      break;
    case "thinking":
      renderThinking();
      break;
    case "speaking":
      renderSpeaking();
      break;
    case "analyzing":
      renderAnalyzing();
      break;
    case "feedback":
      renderFeedback();
      break;
    case "feedbackEvaluation":
      renderFeedbackEvaluation();
      break;
    case "coachDemo":
      renderCoachDemo();
      break;
    case "auth":
      renderAuth();
      break;
    case "plans":
      renderPlans();
      break;
    default:
      renderLanding();
      break;
  }
}

async function refreshHistoryAndProfile() {
  const [history, profile] = await Promise.all([
    request("/api/training/history"),
    request("/api/user/profile"),
  ]);
  state.history = history;
  state.profile = profile;
}

async function refreshSummaryHistoryAndProfile() {
  const [summary, history, profile] = await Promise.all([
    request("/api/user/home-summary"),
    request("/api/training/history"),
    request("/api/user/profile"),
  ]);
  state.summary = summary;
  state.history = history;
  state.profile = profile;
}

async function syncTrainStateFromBackend(options = {}) {
  const session = await request("/api/training/session/current");
  state.training = session;
  if (options.preferDraft && session && (session?.selectedCount === 2 || (session?.draftText || "").trim())) {
    state.feedback = null;
    state.screen = "speaking";
    return;
  }
  if (session?.feedback && Object.keys(session.feedback || {}).length) {
    state.feedback = session.feedback;
    state.screen = "feedback";
    return;
  }
  state.feedback = null;
  if (session?.selectedCount === 2 || (session?.draftText || "").trim()) {
    state.screen = "speaking";
  } else if (session) {
    state.screen = "training";
  } else {
    state.screen = "landing";
  }
}

bottomLinks.forEach((button) => {
  button.addEventListener("click", async () => {
    state.tab = button.dataset.tab;
    if (state.tab === "history") {
      if (!hasLoggedInAccount()) {
        state.tab = "train";
        state.screen = "auth";
        render();
        refreshAndRenderIf(() => state.screen === "auth", refreshAccountState, "账号状态刷新");
        return;
      }
      state.screen = "history";
      render();
      refreshAndRenderIf(
        () => state.tab === "history" && state.screen === "history",
        async () => {
          state.history = await request("/api/training/history");
        },
        "历史记录刷新"
      );
      return;
    }
    if (state.tab === "profile") {
      state.screen = "profile";
      if (!hasLoggedInAccount()) {
        state.tab = "train";
        state.screen = "auth";
        render();
        refreshAndRenderIf(() => state.screen === "auth", refreshAccountState, "账号状态刷新");
        return;
      }
      render();
      refreshAndRenderIf(
        () => state.tab === "profile" && state.screen === "profile",
        async () => {
          state.profile = await request("/api/user/profile");
        },
        "个人页刷新"
      );
      return;
    }
    if (state.tab === "train") {
      if (!hasLoggedInAccount()) {
        state.screen = "auth";
      } else if (!isAccountActive()) {
        state.screen = "landing";
      } else {
        const trainScreens = new Set([
          "landing",
          "training",
          "thinking",
          "speaking",
          "analyzing",
          "feedback",
          "feedbackEvaluation",
          "coachDemo",
        ]);
        state.screen = state.training && trainScreens.has(state.screen) ? state.screen : "landing";
      }
      render();
      refreshAndRenderIf(
        () => state.tab === "train",
        async () => {
          await refreshAccountState();
          if (hasLoggedInAccount() && isAccountActive()) {
            await syncTrainStateFromBackend();
            if (hasTrainingRecovery() && state.screen === "speaking") {
              clearTrainingRecovery();
            }
          }
        },
        "训练状态刷新"
      );
      return;
    }
    render();
  });
});

async function bootstrap() {
  try {
    await maybeVerifyReturn();
    await refreshAccountState();
    if (!hasLoggedInAccount()) {
      state.tab = "train";
      state.screen = "auth";
      render();
      return;
    }
    if (!isAccountActive()) {
      state.tab = "train";
      state.screen = "landing";
      render();
      return;
    }
    if (hasTrainingRecovery()) {
      state.tab = "train";
      await syncTrainStateFromBackend();
      if (state.screen === "speaking") {
        clearTrainingRecovery();
        render();
        return;
      }
    }
    state.tab = "train";
    state.screen = "landing";
    render();
    refreshAndRenderIf(
      () => state.tab === "train" && state.screen === "landing",
      loadDashboardData,
      "首页数据加载"
    );
  } catch (error) {
    const detail = error && error.message ? error.message : String(error || "unknown error");
    app.innerHTML = `
      <section class="screen">
        <article class="hero-panel">
          <span class="eyebrow">暂时离线</span>
          <h2>暂时没连上服务。</h2>
          <p>稍后再刷新一次，或确认本地服务是否已经启动。</p>
          <p style="margin-top: 16px; font-size: 13px; color: #8a93bd; word-break: break-word;">错误详情：${detail}</p>
        </article>
      </section>
    `;
  }
}

window.addEventListener("pageshow", handlePaymentResume);
window.addEventListener("focus", handlePaymentResume);
document.addEventListener("visibilitychange", handlePaymentResume);

bootstrap();
