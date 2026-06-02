function resolveBaseUrl() {
  const host = window.location.hostname;
  const privateLanPattern = /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[0-1])\.)/;
  if (host === "getspeakout.com" || host.endsWith(".getspeakout.com")) {
    return "https://imaginative-love-production.up.railway.app";
  }
  if (host === "127.0.0.1" || host === "localhost") {
    return "http://127.0.0.1:8765";
  }
  if (privateLanPattern.test(host)) {
    return `${window.location.protocol}//${host}:8765`;
  }
  return window.location.origin;
}

const BASE_URL = resolveBaseUrl();
const adminState = {
  prompts: [],
  promptVersions: [],
  models: [],
  users: [],
  userSearch: "",
  pendingEntitlements: [],
  entitlementHistory: [],
  showPlainPhones: false,
  activePromptTab: "runtime",
  evalPollTimer: null
};

function qs(selector) {
  return document.querySelector(selector);
}

function qsa(selector) {
  return Array.from(document.querySelectorAll(selector));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function maskPhone(value) {
  const text = String(value ?? "");
  const digits = text.replace(/\D/g, "");
  if (digits.length === 11) {
    return text.replace(digits, `${digits.slice(0, 3)}****${digits.slice(-4)}`);
  }
  return text;
}

function renderPhone(value) {
  return escapeHtml(adminState.showPlainPhones ? (value || "-") : maskPhone(value || "-"));
}

function summarizeText(value, limit = 48) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!text) return "暂无内容";
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
}

function prettyJson(value) {
  if (!value || (Array.isArray(value) && value.length === 0)) {
    return "暂无数据";
  }
  return JSON.stringify(value, null, 2);
}

function setPromptStatus(text, state = "idle") {
  const status = qs("#prompt-test-status");
  if (!status) return;
  status.textContent = text;
  status.dataset.state = state;
}

async function getJson(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json"
    },
    ...options
  });
  const payload = await response.json();
  if (!response.ok || payload.code !== 0) {
    throw new Error(payload.message || "request failed");
  }
  return payload.data;
}

function activateView(viewName) {
  qsa(".nav-link").forEach((button) => {
    button.classList.toggle("nav-link--active", button.dataset.view === viewName);
  });

  qsa(".admin-view").forEach((section) => {
    section.classList.toggle("admin-view--active", section.dataset.view === viewName);
  });
}

function renderOverview(overview) {
  const groups = [
    {
      title: "用户相关",
      items: [
        ["注册用户数", overview.users?.registeredUsers || 0],
        ["付费用户数", overview.users?.paidUsers || 0],
        ["免费权益用户数", overview.users?.freeBenefitUsers || 0],
        ["有权益用户数", overview.users?.benefitUsers || 0]
      ]
    },
    {
      title: "订单相关",
      items: [
        ["已支付订单数", overview.orders?.paidOrders || 0],
        ["待支付订单数", overview.orders?.pendingOrders || 0],
        ["订单收入", overview.orders?.revenue || "¥0.00"],
        ["复购订单数", overview.orders?.repurchaseOrders || 0]
      ]
    },
    {
      title: "训练数据",
      items: [
        ["累计点评次数", overview.training?.feedbackCount || 0],
        ["进入表达页词组数", overview.training?.enteredPairCount || 0],
        ["提交教练点评词组数", overview.training?.submittedPairCount || 0],
        ["点评成功词组数", overview.training?.coachSuccessPairCount || 0],
        ["平均训练轮次", overview.training?.avgAttemptCount || 0],
        ["点评平均分", overview.training?.avgScore || 0]
      ]
    }
  ];

  qs("#overview-metrics").innerHTML = groups
    .map(
      (group) => `
        <section class="metric-group">
          <h3>${group.title}</h3>
          <div class="metric-group__grid">
            ${group.items
              .map(
                ([label, value]) => `
                  <article class="metric-card">
                    <span>${label}</span>
                    <strong>${value}</strong>
                  </article>
                `
              )
              .join("")}
          </div>
        </section>
      `
    )
    .join("");
}

function renderUsers(users) {
  adminState.users = users || adminState.users || [];
  const keyword = (adminState.userSearch || "").replace(/\D/g, "");
  const visibleUsers = keyword
    ? adminState.users.filter((item) => String(item.phone || item.nickname || "").replace(/\D/g, "").includes(keyword))
    : adminState.users;
  qs("#users-table").innerHTML = visibleUsers.length
    ? visibleUsers
    .map(
      (item) => `
        <tr>
          <td><span class="phone-value">${renderPhone(item.phone || item.nickname)}</span></td>
          <td>${escapeHtml(item.registeredAt)}</td>
          <td>${escapeHtml(item.activityState)}</td>
          <td>${escapeHtml(item.membershipStatus)}</td>
          <td>${escapeHtml(item.totalTrainingCount || 0)}</td>
          <td>${escapeHtml(item.remainingCredits || 0)}</td>
          <td>${escapeHtml(item.expireAt || "-")}</td>
          <td>${escapeHtml(item.paidOrderCount || 0)}</td>
          <td>
            <button class="ghost-button user-grant-shortcut" type="button" data-phone="${escapeHtml(item.phone || item.nickname)}">加权益</button>
            ${item.pendingEntitlement ? "" : `<button class="ghost-button user-expire-shortcut" type="button" data-phone="${escapeHtml(item.phone || item.nickname)}">改到期</button>`}
            <button class="ghost-button danger-button user-delete" type="button" data-phone="${escapeHtml(item.phone || item.nickname)}">删除</button>
          </td>
        </tr>
      `
    )
    .join("")
    : `<tr><td colspan="9">没有找到这个手机号</td></tr>`;

  qsa(".user-grant-shortcut").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      qs("#grant-phone").value = button.dataset.phone || "";
      switchUserTab("manual");
      qs("#grant-credits").focus();
    });
  });
  qsa(".user-expire-shortcut").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      qs("#grant-phone").value = button.dataset.phone || "";
      switchUserTab("manual");
      qs("#expire-date").focus();
    });
  });
  qsa(".user-delete").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      const phone = button.dataset.phone || "";
      if (!confirm(`确认删除 ${phone} 的用户、订单和训练测试数据？删除后这个手机号可以重新注册。`)) return;
      try {
        const result = await getJson("/admin-api/users/delete", {
          method: "POST",
          body: JSON.stringify({ phone })
        });
        renderUsers(result.users || []);
        if (result.orders) renderOrders(result.orders);
        if (result.pendingEntitlements) renderPendingEntitlements(result.pendingEntitlements);
        if (result.history) renderEntitlementHistory(result.history);
        await refreshOverview();
      } catch (error) {
        alert(`删除失败：${error.message}`);
      }
    });
  });
}

function renderPendingEntitlements(items) {
  qs("#pending-entitlements-summary").textContent = items.length
    ? `当前有 ${items.length} 个手机号已提前加好权益，等用户注册后自动到账。`
    : "暂无待注册到账手机号。";
  qs("#pending-entitlements-table").innerHTML = items.length
    ? items
      .map(
        (item) => `
          <tr>
            <td><span class="phone-value">${renderPhone(item.phone)}</span></td>
            <td>${escapeHtml(item.credits)}</td>
            <td>${escapeHtml(item.days)}</td>
            <td>${escapeHtml(item.note || "-")}</td>
            <td>${escapeHtml((item.updatedAt || item.createdAt || "-").slice(0, 16))}</td>
          </tr>
        `
      )
      .join("")
    : `<tr><td colspan="5">暂无</td></tr>`;
}

function renderEntitlementHistory(items) {
  qs("#entitlement-history-table").innerHTML = items.length
    ? items
      .map(
        (item) => `
          <tr>
            <td>${escapeHtml((item.createdAt || "-").slice(0, 16))}</td>
            <td>${escapeHtml(item.type || "-")}</td>
            <td><span class="phone-value">${renderPhone(item.phone && item.phone !== "-" ? item.phone : "-")}</span></td>
            <td>${escapeHtml(item.credits)}</td>
            <td>${escapeHtml(item.days)}</td>
            <td>${escapeHtml(item.statusLabel || item.status || "-")}</td>
            <td>${escapeHtml(item.note || "-")}</td>
          </tr>
        `
      )
      .join("")
    : `<tr><td colspan="7">暂无操作历史</td></tr>`;
}

function renderOrders(orders) {
  qs("#orders-table").innerHTML = orders
    .map(
      (item) => `
        <tr>
          <td>${item.orderNo}</td>
          <td>${escapeHtml(maskPhone(item.user))}</td>
          <td>${escapeHtml(item.planName || "-")}</td>
          <td>${item.amount}</td>
          <td>${item.status}</td>
          <td>${item.paidAt}</td>
          <td><button class="ghost-button danger-button order-delete" type="button" data-order-no="${escapeHtml(item.orderNo)}">删除</button></td>
        </tr>
      `
    )
    .join("");
  qsa(".order-delete").forEach((button) => {
    button.addEventListener("click", async () => {
      const orderNo = button.dataset.orderNo || "";
      if (!confirm(`确认删除订单 ${orderNo}？`)) return;
      try {
        renderOrders(await getJson("/admin-api/orders/delete", {
          method: "POST",
          body: JSON.stringify({ orderNo })
        }));
        await refreshOverview();
      } catch (error) {
        alert(`删除失败：${error.message}`);
      }
    });
  });
}

function renderScoreDetails(details) {
  if (!Array.isArray(details) || details.length === 0) {
    return `<p class="empty-note">暂无维度详情</p>`;
  }
  return `
    <div class="score-detail-grid">
      ${details
        .map((detail) => {
          const label = detail.label || detail.name || "未命名维度";
          const score = detail.score ?? "-";
          const note = detail.note || detail.reason || detail.comment || detail.feedback || "";
          return `
            <article class="score-detail-card">
              <strong>${escapeHtml(label)}：${escapeHtml(score)}</strong>
              <p>${escapeHtml(note || "模型未返回具体原因")}</p>
            </article>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderAttemptCard(attempt, index) {
  const feedback = attempt.feedback || attempt.coachFeedback || {};
  const details = feedback.visibleDetails || feedback.details || attempt.details || [];
  const transcript = attempt.transcriptText || attempt.userText || attempt.text || "暂无本轮表达文本";
  const score = feedback.totalScore ?? attempt.score ?? "-";
  const improvement = feedback.improvement || feedback.nextTask || feedback.next_task || "";
  const rewrite = feedback.rewrite || "";
  return `
    <article class="attempt-card">
      <div class="attempt-card__head">
        <span>第 ${attempt.attemptNo || index + 1} 轮</span>
        <strong>${escapeHtml(score)} 分</strong>
      </div>
      <h5>用户表达</h5>
      <p class="attempt-card__text">${escapeHtml(transcript)}</p>
      <h5>评分详情</h5>
      ${renderScoreDetails(details)}
      ${improvement ? `<h5>下一步建议</h5><p class="attempt-card__text">${escapeHtml(improvement)}</p>` : ""}
      ${rewrite ? `<h5>教练整理版</h5><p class="attempt-card__text">${escapeHtml(rewrite)}</p>` : ""}
    </article>
  `;
}

function renderModelOutputCard(output) {
  return `
    <details class="model-output-card">
      <summary>${escapeHtml(output.modelName || "-")} · ${escapeHtml(output.status || "-")} · ${escapeHtml(output.updatedAt || output.createdAt || "-")}</summary>
      <div class="model-output-card__body">
        <h5>请求参数</h5>
        <pre>${escapeHtml(prettyJson(output.requestJson))}</pre>
        <h5>模型原始返回</h5>
        <pre>${escapeHtml(prettyJson(output.responseJson))}</pre>
      </div>
    </details>
  `;
}

function renderTrainingHistory(records) {
  qs("#history-table").innerHTML = records
    .map(
      (item) => {
        const pair = Array.isArray(item.pair) ? item.pair : [];
        const attempts = Array.isArray(item.attempts) && item.attempts.length
          ? item.attempts
          : [{ attemptNo: 1, transcriptText: item.transcriptText, feedback: item.finalFeedback || {} }];
        const modelOutputs = Array.isArray(item.modelOutputs) ? item.modelOutputs : [];
        return `
        <tr>
          <td>${escapeHtml(maskPhone(item.user))}</td>
          <td>
            <details class="record-detail">
              <summary>
                <span class="pair-chips">${pair.map((word) => `<em>${escapeHtml(word)}</em>`).join("")}</span>
                ${escapeHtml(pair.length ? `${pair.join(" + ")}｜共 ${item.attemptCount || attempts.length || 1} 轮` : "表达训练")}
              </summary>
              <div class="record-detail__body">
                <div class="record-meta">
                  <span>词组：${pair.map(escapeHtml).join(" / ") || "暂无"}</span>
                  <span>Session：${escapeHtml(item.sessionId || item.id)}</span>
                  <span>时间：${escapeHtml(item.timeLabel)}</span>
                </div>
                <h4>本组摘要</h4>
                <p class="empty-note">${escapeHtml(summarizeText(item.transcriptText || item.excerpt || attempts[attempts.length - 1]?.transcriptText || ""))}</p>
                <h4>每轮表达与评分</h4>
                <div class="attempt-list">${attempts.map(renderAttemptCard).join("")}</div>
                <h4>最终教练输出</h4>
                ${renderScoreDetails((item.finalFeedback || {}).visibleDetails || (item.finalFeedback || {}).details || item.details)}
                <pre>${escapeHtml(prettyJson(item.finalFeedback))}</pre>
                <h4>模型调用原始数据</h4>
                ${modelOutputs.length ? modelOutputs.map(renderModelOutputCard).join("") : `<p class="empty-note">暂无模型调用记录</p>`}
              </div>
            </details>
          </td>
          <td>${item.score}</td>
          <td>${item.attemptCount || 1} 轮</td>
          <td>${escapeHtml(item.timeLabel)}</td>
          <td><button class="ghost-button danger-button history-delete" type="button" data-id="${escapeHtml(item.id)}" data-session-id="${escapeHtml(item.sessionId || "")}">删除</button></td>
        </tr>
      `;
      }
    )
    .join("");
  qsa(".history-delete").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!confirm("确认删除这条训练记录和关联模型调用？")) return;
      try {
        renderTrainingHistory(await getJson("/admin-api/training-history/delete", {
          method: "POST",
          body: JSON.stringify({ id: button.dataset.id, sessionId: button.dataset.sessionId })
        }));
        await refreshOverview();
      } catch (error) {
        alert(`删除失败：${error.message}`);
      }
    });
  });
}

function renderWords(words) {
  qs("#words-summary").textContent = `当前 C 端实际使用“新手混合抽词池”：${words.activeBeginnerWords || 0} 个词，分成 ${words.activeBeginnerDeckCount || 0} 类；旧主题词库保留 ${words.totalWords} 个词，暂不作为主抽取逻辑。每轮会从新手池混合抽 16 张。`;

  qs("#words-grid").innerHTML = [...(words.beginnerPools || []), ...(words.decks || [])]
    .map(
      (deck) => `
        <section class="word-deck ${deck.activePool ? "word-deck--active-pool" : ""}">
          <div class="word-deck__head">
            <h3>${deck.title}${deck.activePool ? '<em class="word-deck__flag">实际抽取</em>' : deck.starter ? '<em class="word-deck__flag">旧优先</em>' : ""}</h3>
            <span>${deck.count} 词</span>
          </div>
          <div class="word-chip-list">
            ${deck.words
              .map(
                (item) => `
                  <span class="word-chip" title="最近使用 ${item.usedCount} 次">
                    <strong>${item.word}</strong>
                    <em>${item.usedCount}</em>
                    <button class="word-delete" type="button" data-id="${escapeHtml(item.id || "")}" data-deck-id="${escapeHtml(item.deckId || deck.deckId)}" data-word="${escapeHtml(item.word)}" aria-label="删除 ${escapeHtml(item.word)}">×</button>
                  </span>
                `
              )
              .join("")}
          </div>
        </section>
      `
    )
    .join("");
  qsa(".word-delete").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const word = button.dataset.word || "";
      if (!confirm(`确认删除词语「${word}」？实际抽取池里的词删除后也不会再被抽到。`)) return;
      try {
        renderWords(await getJson("/admin-api/content/words/delete", {
          method: "POST",
          body: JSON.stringify({
            id: button.dataset.id,
            deckId: button.dataset.deckId,
            word
          })
        }));
        await refreshOverview();
      } catch (error) {
        alert(`删除失败：${error.message}`);
      }
    });
  });
}

function renderQuotes(quotes) {
  const publishedCount = quotes.filter((item) => item.status === "published").length;
  qs("#quotes-summary").textContent = `当前共 ${quotes.length} 条金句，${publishedCount} 条会进入首页每日随机池。删除会直接移出金句池。`;
  qs("#quotes-table").innerHTML = quotes
    .map(
      (item) => `
        <tr>
          <td>
            <details class="record-detail">
              <summary>${escapeHtml(item.text)}</summary>
              <div class="record-detail__body">
                <h4>来源</h4>
                <pre>${escapeHtml(`${item.sourceLabel || "未填写"}\n${item.sourceUrl || ""}`)}</pre>
              </div>
            </details>
          </td>
          <td>${escapeHtml(item.author)}</td>
          <td>${escapeHtml(item.theme || "-")}</td>
          <td>展示中</td>
          <td>
            <button class="ghost-button quote-delete" type="button" data-id="${item.id}">删除</button>
          </td>
        </tr>
      `
    )
    .join("");

  qsa(".quote-delete").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      try {
        const quotes = await getJson("/admin-api/content/quotes/delete", {
          method: "POST",
          body: JSON.stringify({ id: button.dataset.id })
        });
        renderQuotes(quotes);
      } catch (error) {
        qs("#quote-save-result").textContent = `删除失败：${error.message}`;
      }
    });
  });
}

function renderPromptSummary(prompts) {
  adminState.prompts = prompts || [];
  const prompt = prompts[0];
  if (!prompt) {
    qs("#prompt-summary").innerHTML = "<p>暂无 Prompt 配置</p>";
    return;
  }

  qs("#prompt-system-text").value = prompt.systemPrompt;
  qs("#prompt-user-template").value = prompt.userPromptTemplate;
  qs("#published-system-prompt").textContent = prompt.systemPrompt;
  qs("#published-user-prompt").textContent = prompt.userPromptTemplate;

  qs("#prompt-summary").innerHTML = `
    <div class="prompt-card__head">
      <div>
        <p class="prompt-card__eyebrow">当前生效版本</p>
        <h3>${prompt.promptName}</h3>
      </div>
    </div>
    <div class="prompt-meta">
      <span>Prompt Key：${prompt.promptKey}</span>
      <span>Model：${prompt.modelName}</span>
      <span>Provider：${prompt.providerCode}</span>
      <span>更新时间：${prompt.updatedAt}</span>
    </div>
  `;
}

function renderPromptVersions(versions) {
  adminState.promptVersions = versions || [];
  const list = qs("#prompt-versions-list");
  if (!versions || versions.length === 0) {
    list.textContent = "暂无版本记录";
    return;
  }
  list.innerHTML = versions
    .map(
      (item, index) => `
        <button class="prompt-version-item ${index === 0 ? "prompt-version-item--active" : ""}" data-version-no="${item.versionNo}">
          <strong>v${item.versionNo}</strong>
          <span>${escapeHtml(item.createdAt)}</span>
          <em>${escapeHtml(item.changeNote || "无备注")}</em>
        </button>
      `
    )
    .join("");

  qsa(".prompt-version-item").forEach((button) => {
    button.addEventListener("click", () => {
      qsa(".prompt-version-item").forEach((item) => item.classList.remove("prompt-version-item--active"));
      button.classList.add("prompt-version-item--active");
      renderPromptVersionDetail(Number(button.dataset.versionNo));
    });
  });
  renderPromptVersionDetail(versions[0].versionNo);
}

function renderPromptVersionDetail(versionNo) {
  const version = adminState.promptVersions.find((item) => Number(item.versionNo) === Number(versionNo));
  if (!version) return;
  qs("#prompt-version-detail").innerHTML = `
    <div class="prompt-card__head">
      <div>
        <p class="prompt-card__eyebrow">v${version.versionNo} · ${escapeHtml(version.status)}</p>
        <h3>${escapeHtml(version.promptName)}</h3>
      </div>
      <button class="secondary-button" id="rollback-prompt-version" data-version-no="${version.versionNo}">回退到这个版本</button>
    </div>
    <div class="prompt-meta">
      <span>Model：${escapeHtml(version.modelName)}</span>
      <span>Provider：${escapeHtml(version.providerCode)}</span>
      <span>创建时间：${escapeHtml(version.createdAt)}</span>
      <span>备注：${escapeHtml(version.changeNote || "无")}</span>
    </div>
    <h4>System Prompt</h4>
    <pre class="prompt-readonly">${escapeHtml(version.systemPrompt)}</pre>
    <h4>User Prompt Template</h4>
    <pre class="prompt-readonly">${escapeHtml(version.userPromptTemplate)}</pre>
  `;

  qs("#rollback-prompt-version").addEventListener("click", () => {
    rollbackPromptVersion(version.versionNo).catch((error) => {
      qs("#prompt-version-detail").insertAdjacentHTML("afterbegin", `<div class="admin-error">回退失败：${escapeHtml(error.message)}</div>`);
    });
  });
}

function switchPromptTab(tabName) {
  adminState.activePromptTab = tabName;
  qsa(".prompt-tab-button").forEach((button) => {
    button.classList.toggle("prompt-tab-button--active", button.dataset.promptTab === tabName);
  });
  qsa(".prompt-tab-panel").forEach((panel) => {
    panel.classList.toggle("prompt-tab-panel--active", panel.dataset.promptPanel === tabName);
  });
}

function switchQuoteTab(tabName) {
  qsa(".prompt-tab-button[data-quote-tab]").forEach((button) => {
    button.classList.toggle("prompt-tab-button--active", button.dataset.quoteTab === tabName);
  });
  qsa(".quote-tab-panel").forEach((panel) => {
    panel.classList.toggle("quote-tab-panel--active", panel.dataset.quotePanel === tabName);
  });
}

function switchEvalTab(tabName) {
  qsa(".prompt-tab-button[data-eval-tab]").forEach((button) => {
    button.classList.toggle("prompt-tab-button--active", button.dataset.evalTab === tabName);
  });
  qsa(".eval-tab-panel").forEach((panel) => {
    panel.classList.toggle("eval-tab-panel--active", panel.dataset.evalPanel === tabName);
  });
}

function switchUserTab(tabName) {
  qsa(".prompt-tab-button[data-user-tab]").forEach((button) => {
    button.classList.toggle("prompt-tab-button--active", button.dataset.userTab === tabName);
  });
  qsa(".user-tab-panel").forEach((panel) => {
    panel.classList.toggle("user-tab-panel--active", panel.dataset.userPanel === tabName);
  });
}

function switchModelTab(tabName) {
  qsa(".prompt-tab-button[data-model-tab]").forEach((button) => {
    button.classList.toggle("prompt-tab-button--active", button.dataset.modelTab === tabName);
  });
  qsa(".model-tab-panel").forEach((panel) => {
    panel.classList.toggle("model-tab-panel--active", panel.dataset.modelPanel === tabName);
  });
}

function renderRuntimeConfig(config) {
  qs("#runtime-api-url").value = config.modelApiUrl || "";
  qs("#runtime-api-key").value = config.modelApiKey || "";
  qs("#runtime-model-name").value = config.modelApiModel || "gpt-4o";
  qs("#runtime-provider-code").value = config.modelProviderCode || "yunwu";
  qs("#runtime-require-real-ai").checked = Boolean(config.requireRealAi);
}

function modelOptions(selectedId = "") {
  return adminState.models
    .filter((item) => item.status !== "deprecated")
    .map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === selectedId ? "selected" : ""}>${escapeHtml(item.displayName || item.modelName)} · ${escapeHtml(item.modelName)}</option>`)
    .join("");
}

function renderModelSelects() {
  ["#connection-model-select", "#schema-model-select", "#eval-model-select"].forEach((selector) => {
    const node = qs(selector);
    if (node) node.innerHTML = modelOptions(node.value);
  });
}

function renderModels(models) {
  adminState.models = models || [];
  qs("#models-table").innerHTML = adminState.models.length
    ? adminState.models.map((item) => `
      <tr>
        <td><strong>${escapeHtml(item.displayName || item.modelName)}</strong><br /><small>${escapeHtml(item.modelName)} · 云雾</small></td>
        <td>${escapeHtml(item.status)}</td>
        <td>${item.apiKeyConfigured ? "已配置" : "未配置"}</td>
        <td>${escapeHtml(item.lastTestStatus || "-")}<br /><small>${escapeHtml(item.lastTestAt || item.lastTestMessage || "-")}</small></td>
        <td>${escapeHtml(item.versionNote || "-")}</td>
        <td>
          <button class="ghost-button model-edit" data-id="${escapeHtml(item.id)}">编辑</button>
          <button class="ghost-button model-active" data-id="${escapeHtml(item.id)}">设为运行模型</button>
        </td>
      </tr>
    `).join("")
    : `<tr><td colspan="6">暂无模型，请先新增一个云雾模型。</td></tr>`;
  renderModelSelects();
  qsa(".model-edit").forEach((button) => {
    button.addEventListener("click", () => {
      const model = adminState.models.find((item) => item.id === button.dataset.id);
      if (!model) return;
      qs("#model-id").value = model.id;
      qs("#model-display-name").value = model.displayName || "";
      qs("#model-name").value = model.modelName || "";
      qs("#model-status").value = model.status || "active";
      qs("#model-version-note").value = model.versionNote || "";
      qs("#model-api-key").value = "";
      qs("#model-save-result").textContent = "正在编辑已有模型；API Key 留空会沿用旧 Key。";
      switchModelTab("create");
    });
  });
  qsa(".model-active").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        const result = await getJson("/admin-api/models/set-active", {
          method: "POST",
          body: JSON.stringify({ id: button.dataset.id })
        });
        renderModels(result.models);
        renderRuntimeConfig(result.runtime);
        qs("#model-save-result").textContent = "已设为线上运行模型。";
      } catch (error) {
        alert(`设置失败：${error.message}`);
      }
    });
  });
}

function clearModelForm() {
  ["#model-id", "#model-display-name", "#model-name", "#model-api-key", "#model-version-note"].forEach((selector) => {
    qs(selector).value = "";
  });
  qs("#model-status").value = "active";
}

async function saveModel() {
  const models = await getJson("/admin-api/models/save", {
    method: "POST",
    body: JSON.stringify({
      id: qs("#model-id").value.trim(),
      displayName: qs("#model-display-name").value.trim(),
      modelName: qs("#model-name").value.trim(),
      apiKey: qs("#model-api-key").value.trim(),
      status: qs("#model-status").value,
      versionNote: qs("#model-version-note").value.trim()
    })
  });
  renderModels(models);
  qs("#model-save-result").textContent = "模型已保存。可以去连接测试或解析测试验证。";
  clearModelForm();
}

async function testModelConnection() {
  qs("#model-connection-status").textContent = "测试中";
  qs("#model-connection-status").dataset.state = "running";
  const result = await getJson("/admin-api/models/test-connection", {
    method: "POST",
    body: JSON.stringify({ id: qs("#connection-model-select").value })
  });
  renderModels(result.models);
  qs("#model-connection-status").textContent = result.ok ? "连接成功" : "连接失败";
  qs("#model-connection-status").dataset.state = result.ok ? "success" : "error";
  qs("#model-connection-result").textContent = JSON.stringify(result, null, 2);
}

async function testModelSchema() {
  qs("#model-schema-status").textContent = "测试中";
  qs("#model-schema-status").dataset.state = "running";
  const selectedWords = qs("#schema-selected-words").value.split("/").map((item) => item.trim()).filter(Boolean);
  const result = await getJson("/admin-api/models/test-schema", {
    method: "POST",
    body: JSON.stringify({
      id: qs("#schema-model-select").value,
      selectedWords,
      attemptNo: Number(qs("#schema-attempt-no").value || 1),
      userText: qs("#schema-user-text").value.trim()
    })
  });
  qs("#model-schema-status").textContent = result.ok ? "解析通过" : "解析失败";
  qs("#model-schema-status").dataset.state = result.ok ? "success" : "error";
  qs("#model-schema-result").textContent = JSON.stringify(result, null, 2);
}

function renderUserBenefitsConfig(config) {
  qs("#user-free-trial-credits").value = config.freeTrialCredits ?? 1;
  qs("#user-free-trial-days").value = config.freeTrialDays ?? 7;
  qs("#user-benefits-config-result").textContent =
    `新用户注册后会自动获得 ${config.freeTrialCredits ?? 1} 次点评，有效期 ${config.freeTrialDays ?? 7} 天。`;
}

function renderJobs(jobs) {
  qs("#jobs-table").innerHTML = jobs
    .map(
      (item) => `
        <tr>
          <td>${item.jobId}</td>
          <td>${item.sessionId}</td>
          <td>${item.promptKey} v${item.versionNo}</td>
          <td>${item.modelName}</td>
          <td>${item.status}</td>
          <td>
            <details class="record-detail">
              <summary>${escapeHtml(item.updatedAt)}</summary>
              <div class="record-detail__body">
                <h4>用户输入</h4>
                <pre>${escapeHtml(item.transcriptText || "暂无")}</pre>
                <h4>模型请求</h4>
                <pre>${escapeHtml(prettyJson(item.requestJson))}</pre>
                <h4>模型原始返回</h4>
                <pre>${escapeHtml(prettyJson(item.responseJson))}</pre>
              </div>
            </details>
          </td>
        </tr>
      `
    )
    .join("");
}

function renderEvalBatches(batches) {
  qs("#eval-batches-table").innerHTML = batches.length
    ? batches
      .map(
        (item) => {
          const processed = item.processedCount ?? ((item.successCount || 0) + (item.errorCount || 0));
          const percent = item.sampleCount ? Math.round((processed / item.sampleCount) * 100) : 0;
          return `
          <tr>
            <td>${escapeHtml(item.name)}<br /><small>${escapeHtml(item.id)}</small></td>
            <td>${escapeHtml(item.promptKey)} v${item.versionNo}</td>
            <td>${escapeHtml(item.modelName)}</td>
            <td>
              <strong>${processed}/${item.sampleCount} · ${percent}%</strong><br />
              <small>${escapeHtml(item.status)}，成功 ${item.successCount}，失败 ${item.errorCount}</small>
            </td>
            <td>${escapeHtml(item.createdAt)}</td>
            <td><button class="ghost-button eval-download" data-batch-id="${item.id}">下载 CSV</button></td>
          </tr>
        `;
        }
      )
      .join("")
    : `<tr><td colspan="6">暂无评测批次</td></tr>`;

  qsa(".eval-download").forEach((button) => {
    button.addEventListener("click", () => {
      window.open(`${BASE_URL}/admin-api/prompt-evals/batches/${button.dataset.batchId}/download`, "_blank");
    });
  });
}

async function runPromptTest() {
  const promptKey = "card_association_feedback";
  const selectedWords = qs("#test-selected-words").value.split("/").map((item) => item.trim()).filter(Boolean);
  const userText = qs("#test-user-text").value.trim();
  const button = qs("#run-prompt-test");
  button.disabled = true;
  setPromptStatus("正在调用模型，等待真实返回…", "running");
  qs("#test-result").textContent = "请求已发出：正在等待模型生成结构化点评。";
  try {
    const result = await getJson("/admin-api/config/ai-prompts/test", {
      method: "POST",
      body: JSON.stringify({
        promptKey,
        selectedWords,
        userText,
        attemptNo: Number(qs("#test-attempt-no").value || 1),
        previousContext: qs("#test-previous-context").value.trim(),
        testGoal: qs("#test-goal").value.trim(),
        expectedFocus: qs("#test-expected-focus").value.trim(),
        membershipLevel: "free",
        systemPrompt: qs("#prompt-system-text").value.trim(),
        userPromptTemplate: qs("#prompt-user-template").value.trim()
      })
    });

    qs("#test-result").textContent = JSON.stringify(
      {
        testId: result.testId,
        providerCode: result.providerCode,
        modelName: result.modelName,
        input: result.input,
        modelInput: result.modelInput,
        feedback: result.feedback,
        rawResponse: result.rawResponse
      },
      null,
      2
    );
    setPromptStatus("试跑完成，已拿到模型返回", "success");
  } catch (error) {
    setPromptStatus("试跑失败", "error");
    qs("#test-result").textContent = `试跑失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
}

async function savePromptConfig() {
  const button = qs("#save-prompt-config");
  button.disabled = true;
  setPromptStatus("正在保存新版本…", "running");
  try {
    const result = await getJson("/admin-api/config/ai-prompts/update", {
      method: "POST",
      body: JSON.stringify({
        promptKey: "card_association_feedback",
        systemPrompt: qs("#prompt-system-text").value.trim(),
        userPromptTemplate: qs("#prompt-user-template").value.trim(),
        changeNote: qs("#prompt-change-note").value.trim()
      })
    });
    renderPromptSummary(result);
    await loadPromptVersions();
    qs("#test-result").textContent = "Prompt 已保存为新版本，可以直接点“试跑一次”验证。";
    setPromptStatus("保存完成", "success");
  } catch (error) {
    setPromptStatus("保存失败", "error");
    qs("#test-result").textContent = `保存失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
}

async function loadPromptVersions() {
  const versions = await getJson("/admin-api/config/ai-prompts/versions?promptKey=card_association_feedback");
  renderPromptVersions(versions);
}

async function rollbackPromptVersion(versionNo) {
  const result = await getJson("/admin-api/config/ai-prompts/rollback", {
    method: "POST",
    body: JSON.stringify({
      promptKey: "card_association_feedback",
      versionNo
    })
  });
  renderPromptSummary(result.prompts);
  renderPromptVersions(result.versions);
  switchPromptTab("published");
}

async function saveRuntimeConfig() {
  const result = await getJson("/admin-api/config/runtime/update", {
    method: "POST",
    body: JSON.stringify({
      modelApiUrl: qs("#runtime-api-url").value.trim(),
      modelApiKey: qs("#runtime-api-key").value.trim(),
      modelApiModel: qs("#runtime-model-name").value.trim(),
      modelProviderCode: qs("#runtime-provider-code").value.trim(),
      requireRealAi: qs("#runtime-require-real-ai").checked
    })
  });
  renderRuntimeConfig(result);
  qs("#runtime-save-result").textContent = JSON.stringify(
    {
      modelApiUrl: result.modelApiUrl,
      modelApiModel: result.modelApiModel,
      modelProviderCode: result.modelProviderCode,
      requireRealAi: result.requireRealAi,
      savedAt: new Date().toLocaleString()
    },
    null,
    2
  );
}

async function saveUserBenefitsConfig() {
  const result = await getJson("/admin-api/users/benefits-config/update", {
    method: "POST",
    body: JSON.stringify({
      freeTrialCredits: Number(qs("#user-free-trial-credits").value || 0),
      freeTrialDays: Number(qs("#user-free-trial-days").value || 1)
    })
  });
  renderUserBenefitsConfig(result);
  const history = await getJson("/admin-api/users/entitlement-history");
  renderEntitlementHistory(history);
  qs("#user-benefits-config-result").textContent = JSON.stringify(
    {
      保存结果: "注册赠送权益已更新",
      注册赠送点评次数: result.freeTrialCredits,
      赠送有效天数: result.freeTrialDays,
      保存时间: new Date().toLocaleString()
    },
    null,
    2
  );
}

async function grantEntitlement() {
  const result = await getJson("/admin-api/users/grant-entitlement", {
    method: "POST",
    body: JSON.stringify({
      phone: qs("#grant-phone").value.trim(),
      credits: Number(qs("#grant-credits").value || 0),
      days: Number(qs("#grant-days").value || 0),
      note: qs("#grant-note").value.trim()
    })
  });
  renderUsers(result.users || []);
  renderUserBenefitsConfig(result.benefitsConfig || {});
  adminState.pendingEntitlements = result.pendingEntitlements || [];
  adminState.entitlementHistory = result.history || [];
  renderPendingEntitlements(result.pendingEntitlements || []);
  renderEntitlementHistory(result.history || []);
  qs("#grant-result").textContent = result.status === "applied"
    ? "已注册用户：权益已立即增加。"
    : "这个手机号还没注册：已先记下权益，等用户用这个手机号注册后会自动到账。";
  qs("#grant-credits").value = "0";
  qs("#grant-days").value = "0";
  qs("#grant-note").value = "";
}

async function setExpireAt() {
  const result = await getJson("/admin-api/users/set-expire-at", {
    method: "POST",
    body: JSON.stringify({
      phone: qs("#grant-phone").value.trim(),
      expireDate: qs("#expire-date").value,
      note: qs("#grant-note").value.trim()
    })
  });
  renderUsers(result.users || []);
  adminState.entitlementHistory = result.history || [];
  renderEntitlementHistory(result.history || []);
  qs("#grant-result").textContent = `到期时间已设置为 ${qs("#expire-date").value} 23:59:59。这个用户从次日 00:00:00 起不可再提交点评。`;
}

async function createQuote() {
  const quotes = await getJson("/admin-api/content/quotes/create", {
    method: "POST",
    body: JSON.stringify({
      text: qs("#quote-text").value.trim(),
      author: qs("#quote-author").value.trim(),
      theme: qs("#quote-theme").value.trim(),
      sourceLabel: qs("#quote-source-label").value.trim(),
      sourceUrl: qs("#quote-source-url").value.trim()
    })
  });
  qs("#quote-save-result").textContent = "金句已新增，并进入首页每日随机池。";
  qs("#quote-text").value = "";
  qs("#quote-author").value = "";
  qs("#quote-theme").value = "";
  qs("#quote-source-label").value = "";
  qs("#quote-source-url").value = "";
  renderQuotes(quotes);
}

async function loadEvalBatches() {
  const batches = await getJson("/admin-api/prompt-evals/batches");
  renderEvalBatches(batches);
  return batches;
}

function updateEvalProgress(batch) {
  if (!batch) return false;
  const processed = batch.processedCount ?? ((batch.successCount || 0) + (batch.errorCount || 0));
  const percent = batch.sampleCount ? Math.round((processed / batch.sampleCount) * 100) : 0;
  qs("#eval-status").textContent = `${processed}/${batch.sampleCount} · ${percent}%`;
  qs("#eval-status").dataset.state = batch.status === "failed" ? "error" : batch.status === "completed" ? "success" : "running";
  qs("#eval-run-result").textContent = `批次 ${batch.id}
状态：${batch.status}
进度：${processed}/${batch.sampleCount}（${percent}%）
成功：${batch.successCount}
失败：${batch.errorCount}

完成后可以到「批次下载」下载 CSV。失败样本会保留 error，不会生成假点评。`;
  return batch.status === "completed" || batch.status === "failed";
}

async function pollEvalBatch(batchId) {
  if (adminState.evalPollTimer) {
    window.clearInterval(adminState.evalPollTimer);
  }
  const tick = async () => {
    const batches = await loadEvalBatches();
    const batch = batches.find((item) => item.id === batchId);
    const done = updateEvalProgress(batch);
    if (done && adminState.evalPollTimer) {
      window.clearInterval(adminState.evalPollTimer);
      adminState.evalPollTimer = null;
      qs("#run-prompt-eval").disabled = false;
      qs("#run-prompt-eval").textContent = "开始批量评测";
      switchEvalTab("batches");
    }
  };
  await tick();
  adminState.evalPollTimer = window.setInterval(() => {
    tick().catch((error) => {
      qs("#eval-status").textContent = "进度查询失败";
      qs("#eval-status").dataset.state = "error";
      qs("#eval-run-result").textContent = `进度查询失败：${error.message}`;
    });
  }, 1500);
}

async function runPromptEvalBatch() {
  const button = qs("#run-prompt-eval");
  button.disabled = true;
  button.textContent = "创建批次中…";
  qs("#eval-status").textContent = "0%";
  qs("#eval-status").dataset.state = "running";
  qs("#eval-run-result").textContent = "正在创建批次，创建后会显示逐条调用进度。";
  await new Promise((resolve) => window.setTimeout(resolve, 80));
  try {
    const result = await getJson("/admin-api/prompt-evals/run", {
      method: "POST",
      body: JSON.stringify({
        name: qs("#eval-batch-name").value.trim(),
        modelId: qs("#eval-model-select").value,
        maxCount: Number(qs("#eval-max-count").value || 50),
        samplesText: qs("#eval-samples-text").value.trim()
      })
    });
    button.textContent = "评测进行中…";
    updateEvalProgress(result.batch);
    await pollEvalBatch(result.batch.id);
  } catch (error) {
    qs("#eval-status").textContent = "评测失败";
    qs("#eval-status").dataset.state = "error";
    qs("#eval-run-result").textContent = `评测失败：${error.message}`;
    button.disabled = false;
    button.textContent = "开始批量评测";
  }
}

function exportTodayData() {
  window.open(`${BASE_URL}/admin-api/dashboard/export-today`, "_blank");
}

async function bootstrap() {
  try {
    const [overview, users, userBenefitsConfig, pendingEntitlements, entitlementHistory, orders, history, words, quotes, prompts, promptVersions, jobs, evalBatches, runtimeConfig, models] = await Promise.all([
      getJson("/admin-api/dashboard/overview"),
      getJson("/admin-api/users"),
      getJson("/admin-api/users/benefits-config"),
      getJson("/admin-api/users/pending-entitlements"),
      getJson("/admin-api/users/entitlement-history"),
      getJson("/admin-api/orders"),
      getJson("/admin-api/training-history"),
      getJson("/admin-api/content/words"),
      getJson("/admin-api/content/quotes"),
      getJson("/admin-api/config/ai-prompts"),
      getJson("/admin-api/config/ai-prompts/versions?promptKey=card_association_feedback"),
      getJson("/admin-api/ai-feedback/jobs"),
      getJson("/admin-api/prompt-evals/batches"),
      getJson("/admin-api/config/runtime"),
      getJson("/admin-api/models")
    ]);

    renderOverview(overview);
    renderUsers(users);
    renderUserBenefitsConfig(userBenefitsConfig);
    adminState.pendingEntitlements = pendingEntitlements || [];
    adminState.entitlementHistory = entitlementHistory || [];
    renderPendingEntitlements(pendingEntitlements);
    renderEntitlementHistory(entitlementHistory);
    renderOrders(orders);
    renderTrainingHistory(history);
    renderWords(words);
    renderQuotes(quotes);
    renderPromptSummary(prompts);
    renderPromptVersions(promptVersions);
    renderJobs(jobs);
    renderEvalBatches(evalBatches);
    renderRuntimeConfig(runtimeConfig);
    renderModels(models);
  } catch (error) {
    console.error(error);
    document.body.insertAdjacentHTML(
      "afterbegin",
      `<div class="admin-error">后台数据加载失败，请刷新重试；如果你在本地开发环境打开后台，再启动本地服务：python3 /Users/lisa888/Documents/表达高手/backend/server.py</div>`
    );
  }
}

qsa(".nav-link").forEach((button) => {
  button.addEventListener("click", () => activateView(button.dataset.view));
});

qsa(".prompt-tab-button").forEach((button) => {
  if (button.dataset.userTab) {
    button.addEventListener("click", () => switchUserTab(button.dataset.userTab));
  }
  if (button.dataset.promptTab) {
    button.addEventListener("click", () => switchPromptTab(button.dataset.promptTab));
  }
  if (button.dataset.quoteTab) {
    button.addEventListener("click", () => switchQuoteTab(button.dataset.quoteTab));
  }
  if (button.dataset.evalTab) {
    button.addEventListener("click", () => switchEvalTab(button.dataset.evalTab));
  }
  if (button.dataset.modelTab) {
    button.addEventListener("click", () => switchModelTab(button.dataset.modelTab));
  }
});

qs("#user-phone-search").addEventListener("input", (event) => {
  adminState.userSearch = event.target.value.trim();
  renderUsers();
});

qs("#clear-user-search").addEventListener("click", () => {
  adminState.userSearch = "";
  qs("#user-phone-search").value = "";
  renderUsers();
});

qs("#toggle-phone-visibility").addEventListener("click", () => {
  adminState.showPlainPhones = !adminState.showPlainPhones;
  qs("#toggle-phone-visibility").textContent = adminState.showPlainPhones ? "隐藏明文手机号" : "显示明文手机号";
  renderUsers();
  renderPendingEntitlements(adminState.pendingEntitlements);
  renderEntitlementHistory(adminState.entitlementHistory);
});

qs("#run-prompt-test").addEventListener("click", () => {
  runPromptTest().catch((error) => {
    qs("#test-result").textContent = `试跑失败：${error.message}`;
  });
});

qs("#save-prompt-config").addEventListener("click", () => {
  savePromptConfig().catch((error) => {
    qs("#test-result").textContent = `保存失败：${error.message}`;
  });
});

qs("#save-runtime-config").addEventListener("click", () => {
  saveRuntimeConfig().catch((error) => {
    qs("#runtime-save-result").textContent = `保存失败：${error.message}`;
  });
});

qs("#save-model").addEventListener("click", () => {
  saveModel().catch((error) => {
    qs("#model-save-result").textContent = `保存失败：${error.message}`;
  });
});

qs("#clear-model-form").addEventListener("click", clearModelForm);

qs("#test-model-connection").addEventListener("click", () => {
  testModelConnection().catch((error) => {
    qs("#model-connection-status").textContent = "连接失败";
    qs("#model-connection-status").dataset.state = "error";
    qs("#model-connection-result").textContent = `连接失败：${error.message}`;
  });
});

qs("#test-model-schema").addEventListener("click", () => {
  testModelSchema().catch((error) => {
    qs("#model-schema-status").textContent = "解析失败";
    qs("#model-schema-status").dataset.state = "error";
    qs("#model-schema-result").textContent = `解析失败：${error.message}`;
  });
});

qs("#save-user-benefits-config").addEventListener("click", () => {
  saveUserBenefitsConfig().catch((error) => {
    qs("#user-benefits-config-result").textContent = `保存失败：${error.message}`;
  });
});

qs("#grant-entitlement").addEventListener("click", () => {
  grantEntitlement().catch((error) => {
    qs("#grant-result").textContent = `增加失败：${error.message}`;
  });
});

qs("#set-expire-at").addEventListener("click", () => {
  setExpireAt().catch((error) => {
    qs("#grant-result").textContent = `设置到期时间失败：${error.message}`;
  });
});

qs("#create-quote").addEventListener("click", () => {
  createQuote().catch((error) => {
    qs("#quote-save-result").textContent = `新增失败：${error.message}`;
  });
});

qs("#run-prompt-eval").addEventListener("click", () => {
  runPromptEvalBatch().catch((error) => {
    qs("#eval-run-result").textContent = `评测失败：${error.message}`;
  });
});

if (qs("#export-today-data")) {
  qs("#export-today-data").addEventListener("click", exportTodayData);
}

bootstrap();
