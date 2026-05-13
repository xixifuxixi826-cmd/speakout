const API_BASE = (() => {
  if (!window.location.protocol.startsWith("http")) {
    return "http://127.0.0.1:8765";
  }
  if (window.location.port === "8088") {
    return `${window.location.protocol}//${window.location.hostname}:8765`;
  }
  if (window.location.hostname === "getspeakout.com" || window.location.hostname.endsWith(".getspeakout.com")) {
    return "https://api.getspeakout.com";
  }
  return `${window.location.protocol}//api.${window.location.hostname}`;
})();

const state = {
  tab: "train",
  screen: "landing",
  mode: "backend",
  summary: null,
  training: null,
  feedback: null,
  history: [],
  profile: null,
  membershipMessage: "开通成功后，你的剩余轮次会立即切换为无限。",
  registerMessage: "注册后可以保存点评记录、领取兑换码，并在下次继续训练。",
  registerContext: "default",
  timers: {
    thinking: null,
    speaking: null,
  },
};

const app = document.querySelector("#app");
const modePill = document.querySelector("#mode-pill");
const bottomLinks = Array.from(document.querySelectorAll(".bottom-link"));
const toast = document.querySelector("#toast");

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

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      "X-Client-Id": getClientId(),
    },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.code !== 0) {
    throw new Error(payload.message || "request failed");
  }
  return payload.data;
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

function showToast(message) {
  if (!toast) {
    return;
  }
  toast.textContent = message;
  toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 1800);
}

function clearTimers() {
  Object.values(state.timers).forEach((timer) => {
    if (timer) {
      clearInterval(timer);
    }
  });
  state.timers.thinking = null;
  state.timers.speaking = null;
}

function normalizeDetails(details = []) {
  const expectedLabels = [
    "判断句成立度",
    "观点张力",
    "解释充分度",
    "具体性与画面感",
    "结构流畅度",
    "语言自然度",
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

function renderRadar(details) {
  const points = normalizeDetails(details);
  const size = 220;
  const center = size / 2;
  const radius = 76;
  const levels = [25, 50, 75, 100];
  const polygons = levels
    .map((level) => {
      const ratio = level / 100;
      const coords = points
        .map((_, index) => {
          const angle = (-Math.PI / 2) + (Math.PI * 2 * index) / points.length;
          const x = center + Math.cos(angle) * radius * ratio;
          const y = center + Math.sin(angle) * radius * ratio;
          return `${x},${y}`;
        })
        .join(" ");
      return `<polygon points="${coords}" fill="none" stroke="rgba(72,89,192,0.12)" stroke-width="1" />`;
    })
    .join("");

  const axes = points
    .map((item, index) => {
      const angle = (-Math.PI / 2) + (Math.PI * 2 * index) / points.length;
      const x = center + Math.cos(angle) * radius;
      const y = center + Math.sin(angle) * radius;
      return `<line x1="${center}" y1="${center}" x2="${x}" y2="${y}" stroke="rgba(72,89,192,0.14)" stroke-width="1" />`;
    })
    .join("");

  const scorePolygon = points
    .map((item, index) => {
      const angle = (-Math.PI / 2) + (Math.PI * 2 * index) / points.length;
      const x = center + Math.cos(angle) * radius * (item.score / 100);
      const y = center + Math.sin(angle) * radius * (item.score / 100);
      return `${x},${y}`;
    })
    .join(" ");

  const labels = points
    .map((item, index) => {
      const angle = (-Math.PI / 2) + (Math.PI * 2 * index) / points.length;
      const x = center + Math.cos(angle) * (radius + 26);
      const y = center + Math.sin(angle) * (radius + 26);
      return `<text x="${x}" y="${y}" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="#66709b">${item.label}</text>`;
    })
    .join("");

  return `
    <div class="panel-title-row">
      <h3>六维拆解</h3>
    </div>
    <div class="radar-wrap">
      <svg class="radar-svg" viewBox="0 0 ${size} ${size}">
        ${polygons}
        ${axes}
        <polygon points="${scorePolygon}" fill="rgba(255,108,144,0.22)" stroke="#ff6c90" stroke-width="2" />
        ${labels}
      </svg>
      <div class="radar-legend">
        ${points
          .map(
            (item) => `
              <div class="radar-legend-item">
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

function renderLanding() {
  const template = document.querySelector("#landing-template").content.cloneNode(true);
  app.replaceChildren(template);

  const summary = state.summary;
  const latest = state.history[0];

  document.querySelector("#hero-stats").innerHTML = [
    { value: "16", label: "每轮议题词卡" },
    { value: "30s", label: "构思热身" },
    { value: "2min", label: "表达时长" },
    { value: summary?.remainingQuotaText || "-", label: "剩余额度" },
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

  document.querySelector("#start-training").addEventListener("click", startTraining);
}

async function startTraining() {
  const result = await request("/api/training/session/create", { method: "POST" });
  if (result.blocked) {
    state.screen = "membership";
    render();
    return;
  }

  state.training = result.state;
  state.screen = "training";
  render();
}

function renderTraining() {
  const template = document.querySelector("#training-template").content.cloneNode(true);
  app.replaceChildren(template);

  document.querySelector("#round-label").textContent = `第 ${state.training.roundNo} 轮`;
  document.querySelector("#quota-chip").textContent =
    state.training.remainingQuota < 0 ? "不限次数" : `剩余 ${state.training.remainingQuota} 次`;

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

  grid.querySelectorAll(".matrix-card").forEach((button) => {
    button.addEventListener("click", async () => {
      const cardId = button.dataset.card;
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
      }
    });
  });

  document.querySelector("#proceed-training").addEventListener("click", async () => {
    const current = await request("/api/training/session/current");
    state.training = current;
    if (current.isComplete) {
      await startTraining();
      return;
    }
    if (current.selectedCount !== 2) {
      alert("先选 2 张词卡");
      return;
    }
    state.screen = "thinking";
    render();
  });
}

function renderThinking() {
  const template = document.querySelector("#thinking-template").content.cloneNode(true);
  app.replaceChildren(template);

  document.querySelector("#thinking-words").innerHTML = state.training.selectedCards
    .map((item) => selectedChip(item.word))
    .join("");

  let seconds = 30;
  const clock = document.querySelector("#thinking-clock");
  clock.textContent = "00:30";
  state.timers.thinking = setInterval(() => {
    seconds -= 1;
    const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
    const ss = String(seconds % 60).padStart(2, "0");
    clock.textContent = `${mm}:${ss}`;
    if (seconds <= 0) {
      clearTimers();
      state.screen = "speaking";
      render();
    }
  }, 1000);

  document.querySelector("#skip-thinking").addEventListener("click", () => {
    clearTimers();
    state.screen = "speaking";
    render();
  });
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
  document.querySelector("#speaking-words").innerHTML = words.map(selectedChip).join("");

  const textarea = document.querySelector("#transcript-input");
  const transcriptStatus = document.querySelector("#transcript-status");
  textarea.value = state.training.draftText || "";
  if (textarea.value.trim()) {
    transcriptStatus.textContent = "已写入";
  }

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

  textarea.addEventListener("input", async () => {
    transcriptStatus.textContent = textarea.value.trim() ? "已写入" : "准备开始";
    state.training = await request("/api/training/session/current/draft", {
      method: "POST",
      body: JSON.stringify({ draftText: textarea.value }),
    });
  });

  document.querySelector("#focus-input").addEventListener("click", () => {
    textarea.focus();
  });
  document.querySelector("#reset-record").addEventListener("click", async () => {
    textarea.value = "";
    transcriptStatus.textContent = "准备开始";
    state.training = await request("/api/training/session/current/draft", {
      method: "POST",
      body: JSON.stringify({ draftText: "" }),
    });
    textarea.focus();
  });

  document.querySelector("#submit-speaking").addEventListener("click", async () => {
    if (!textarea.value.trim()) {
      alert("先讲一点出来，再交给教练点评");
      return;
    }
    state.training.draftText = textarea.value;
    state.screen = "analyzing";
    render();
    document.querySelector("#analyzing-words").innerHTML = words.map(selectedChip).join("");

    try {
      state.feedback = await request("/api/training/session/current/submit", {
        method: "POST",
        body: JSON.stringify({ transcriptText: textarea.value }),
      });
      state.screen = "feedback";
      await refreshHistoryAndProfile();
      render();
    } catch (error) {
      alert(error.message || "提交给教练失败");
      state.screen = "speaking";
      render();
    }
  });
}

function renderAnalyzing() {
  const template = document.querySelector("#analyzing-template").content.cloneNode(true);
  app.replaceChildren(template);
  document.querySelector("#analyzing-words").innerHTML = state.training.selectedCards
    .map((item) => selectedChip(item.word))
    .join("");
}

function renderFeedback() {
  const template = document.querySelector("#feedback-template").content.cloneNode(true);
  app.replaceChildren(template);

  document.querySelector("#feedback-title").textContent = state.feedback.pairTitle || "本次点评";
  document.querySelector("#feedback-summary").textContent = state.feedback.summary || "你的教练已经完成这次分析。";
  document.querySelector("#feedback-score").textContent = state.feedback.totalScore ?? "-";
  document.querySelector("#feedback-model").textContent = state.feedback.aiModel
    ? `模型：${state.feedback.aiModel}`
    : "";
  const normalizedDetails = normalizeDetails(state.feedback.visibleDetails || state.feedback.details || []);

  document.querySelector("#feedback-radar").innerHTML = renderRadar(normalizedDetails);

  document.querySelector("#feedback-details").innerHTML = `
    <div class="panel-title-row">
      <h3>评分拆解</h3>
    </div>
    ${normalizedDetails
      .map(
        (item) => `
          <div class="feedback-detail">
            <div class="panel-title-row">
              <strong>${item.label || "维度"}</strong>
              <span>${item.score ?? "-"}</span>
            </div>
            <p>${item.note || ""}</p>
          </div>
        `
      )
      .join("")}
  `;

  document.querySelector("#feedback-suggestions").innerHTML = `
    <div class="panel-title-row">
      <h3>教练建议</h3>
    </div>
    <div class="guide-list guide-list--feedback">
      ${(state.feedback.suggestions || []).map((item, index) => `
        <div class="guide-item">
          <span>${String(index + 1).padStart(2, "0")}</span>
          <p>${item}</p>
        </div>
      `).join("")}
    </div>
  `;

  const thinkingPaths = state.feedback.thinkingPaths || [];
  const rewriteParagraphs = String(state.feedback.rewrite || "暂无参考表达。")
    .split(/\n{2,}/)
    .filter(Boolean);
  document.querySelector("#feedback-thinking").innerHTML = `
    <div class="panel-title-row">
      <h3>思考路径与参考表达</h3>
    </div>
    <div class="guide-list guide-list--feedback">
      ${thinkingPaths
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
    <div class="method-card" style="margin-top: 14px;">
      <strong>2 分钟参考表达</strong>
      ${rewriteParagraphs.map((item) => `<p>${item}</p>`).join("")}
    </div>
  `;

  if (!state.profile?.isRegistered) {
    const registerPanel = document.createElement("article");
    registerPanel.className = "soft-panel";
    registerPanel.innerHTML = `
      <div class="panel-title-row">
        <div>
          <span class="eyebrow">保存这次点评</span>
          <h3>先把这次结果保存下来</h3>
        </div>
      </div>
      <p>留下昵称和联系方式，下次回来还能接着练，也不会丢掉这次点评。</p>
      <button class="primary-btn" id="open-register-from-feedback">保存这次结果</button>
    `;
    app.appendChild(registerPanel);
    document.querySelector("#open-register-from-feedback").addEventListener("click", () => {
      state.registerContext = "feedback";
      state.registerMessage = "保存后，这次点评会留在你的历史里。";
      state.screen = "register";
      render();
    });
  }

  document.querySelector("#continue-training").addEventListener("click", async () => {
    const result = await request("/api/training/session/current/continue", { method: "POST" });
    if (result.route.includes("training")) {
      const session = await request("/api/training/session/current");
      state.training = {
        ...session,
        selectedCards: session?.selectedCount ? session.selectedCards : [],
      };
      state.screen = "training";
    } else if (result.route.includes("membership")) {
      state.screen = "membership";
    } else {
      state.screen = "landing";
    }
    render();
  });

  document.querySelector("#retry-speaking").addEventListener("click", async () => {
    state.training = await request("/api/training/session/current");
    if (!state.training.selectedCards?.length && state.feedback?.selectedWords?.length) {
      state.training.selectedCards = state.feedback.selectedWords.map((word, index) => ({
        id: `retry-word-${index}`,
        word,
      }));
    }
    state.screen = "speaking";
    render();
  });
}

function renderHistory() {
  const template = document.querySelector("#history-template").content.cloneNode(true);
  app.replaceChildren(template);
  document.querySelector("#history-list").innerHTML = state.history
    .map(
      (item) => `
        <article class="history-item">
          <div class="panel-title-row">
            <strong>${item.title}</strong>
            <span>${item.score}</span>
          </div>
      <p>${item.summary}</p>
      <p class="muted">${item.timeLabel}</p>
        </article>
      `
    )
    .join("");
}

function renderProfile() {
  const template = document.querySelector("#profile-template").content.cloneNode(true);
  app.replaceChildren(template);
  document.querySelector("#profile-plan").textContent = state.profile?.planName || "普通版";
  document.querySelector("#profile-quota").textContent = state.profile?.isMember
    ? "会员已开通，可以继续无限训练。"
    : state.profile?.isRegistered
      ? `今天已用 ${state.profile?.usedFreeRounds ?? 0} / 3，剩余 ${state.profile?.remainingQuota ?? 0} 次。`
      : "你现在是访客模式，注册后就能保住训练记录。";
  const button = document.querySelector("#open-membership");
  button.textContent = state.profile?.isRegistered ? "开通会员" : "保存我的进度";
  button.addEventListener("click", () => {
    if (state.profile?.isRegistered) {
      state.screen = "membership";
    } else {
      state.registerContext = "profile";
      state.registerMessage = "先保存这次进度，再继续领取会员权益。";
      state.screen = "register";
    }
    render();
  });
}

function renderRegister() {
  const template = document.querySelector("#register-template").content.cloneNode(true);
  app.replaceChildren(template);
  const nicknameInput = document.querySelector("#register-nickname");
  const contactInput = document.querySelector("#register-contact");
  const message = document.querySelector("#register-message");

  nicknameInput.value = state.profile?.isRegistered ? state.profile.nickname || "" : state.profile?.nickname || "";
  contactInput.value = state.profile?.contact || "";
  message.textContent = state.registerMessage;

  document.querySelector("#register-submit").addEventListener("click", async () => {
    try {
      state.profile = await request("/api/user/register", {
        method: "POST",
        body: JSON.stringify({
          nickname: nicknameInput.value.trim(),
          contact: contactInput.value.trim(),
        }),
      });
      state.summary = await request("/api/user/home-summary");
      state.registerMessage = "保存成功，这台设备上的训练记录已经绑定到你的账户。";
      if (state.registerContext === "feedback") {
        state.screen = "feedback";
      } else if (state.registerContext === "membership") {
        state.screen = "membership";
      } else {
        state.screen = "profile";
      }
      render();
    } catch (error) {
      message.textContent = error.message || "保存失败，请稍后再试。";
    }
  });

  document.querySelector("#register-skip").addEventListener("click", () => {
    state.screen = state.registerContext === "feedback" ? "feedback" : "profile";
    render();
  });
}

function renderMembership() {
  if (!state.profile?.isRegistered) {
    state.registerContext = "membership";
    state.registerMessage = "先保存你的进度，再领取兑换码和开通会员。";
    state.screen = "register";
    render();
    return;
  }
  const template = document.querySelector("#membership-template").content.cloneNode(true);
  app.replaceChildren(template);

  const input = document.querySelector("#redeem-code-input");
  const message = document.querySelector("#redeem-message");
  message.textContent = state.membershipMessage;

  document.querySelector("#copy-demo-code").addEventListener("click", () => {
    input.value = "GAOSHOU-2026-VIP";
    state.membershipMessage = "示例兑换码已填入，你可以直接试一次开通。";
    message.textContent = state.membershipMessage;
  });

  document.querySelector("#redeem-submit").addEventListener("click", async () => {
    const code = input.value.trim();
    if (!code) {
      state.membershipMessage = "先输入兑换码，再完成开通。";
      message.textContent = state.membershipMessage;
      return;
    }

    try {
      const result = await request("/api/membership/redeem", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
      state.profile = result.profile;
      state.summary = await request("/api/user/home-summary");
      state.membershipMessage = `${result.planName} 已开通，兑换码 ${result.code} 已生效。`;
      state.tab = "profile";
      state.screen = "profile";
      render();
    } catch (error) {
      state.membershipMessage = error.message || "兑换失败，请检查兑换码是否正确。";
      message.textContent = state.membershipMessage;
    }
  });
}

function render() {
  clearTimers();
  setActiveTab(state.tab);
  if (state.tab === "history") {
    renderHistory();
    return;
  }
  if (state.tab === "profile") {
    if (state.screen === "membership") {
      renderMembership();
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
    case "membership":
      renderMembership();
      break;
    case "register":
      renderRegister();
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

bottomLinks.forEach((button) => {
  button.addEventListener("click", async () => {
    state.tab = button.dataset.tab;
    if (state.tab === "history") {
      state.history = await request("/api/training/history");
    }
    if (state.tab === "profile") {
      state.profile = await request("/api/user/profile");
    }
    render();
  });
});

async function bootstrap() {
  try {
    await loadDashboardData();
    render();
  } catch (error) {
    app.innerHTML = `
      <section class="screen">
        <article class="hero-panel">
          <span class="eyebrow">暂时离线</span>
          <h2>暂时没连上服务。</h2>
          <p>稍后再刷新一次，或确认本地服务是否已经启动。</p>
        </article>
      </section>
    `;
  }
}

bootstrap();
