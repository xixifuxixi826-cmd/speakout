const BASE_URL = "http://127.0.0.1:8765";

function qs(selector) {
  return document.querySelector(selector);
}

function qsa(selector) {
  return Array.from(document.querySelectorAll(selector));
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
  const metrics = [
    ["注册用户", overview.registeredUsers, "累计注册人数"],
    ["DAU", overview.dailyActiveUsers, "当日活跃用户"],
    ["训练量", overview.trainingVolume, "累计表达记录"],
    ["付费用户", overview.paidUsers, `总收入 ${overview.revenue}`]
  ];

  qs("#overview-metrics").innerHTML = metrics
    .map(
      ([label, value, note]) => `
        <article class="metric-card">
          <span>${label}</span>
          <strong>${value}</strong>
          <small>${note}</small>
        </article>
      `
    )
    .join("");
}

function renderUsers(users) {
  qs("#users-table").innerHTML = users
    .map(
      (item) => `
        <tr>
          <td>${item.nickname}</td>
          <td>${item.registeredAt}</td>
          <td>${item.activityState}</td>
          <td>${item.membershipStatus}</td>
          <td>${item.trainingSummary}</td>
        </tr>
      `
    )
    .join("");
}

function renderOrders(orders) {
  qs("#orders-table").innerHTML = orders
    .map(
      (item) => `
        <tr>
          <td>${item.orderNo}</td>
          <td>${item.user}</td>
          <td>${item.amount}</td>
          <td>${item.status}</td>
          <td>${item.paidAt}</td>
        </tr>
      `
    )
    .join("");
}

function renderRedeemCodes(codes) {
  qs("#redeem-codes-table").innerHTML = codes
    .map(
      (item) => `
        <tr>
          <td>${item.code}</td>
          <td>${item.planName}</td>
          <td>${item.status}</td>
          <td>${item.usedBy}</td>
          <td>${item.usedAt}</td>
          <td>
            ${item.status === "active" ? `<button class="ghost-button redeem-toggle" data-code="${item.code}" data-status="inactive">停用</button>` : ""}
            ${item.status === "inactive" ? `<button class="ghost-button redeem-toggle" data-code="${item.code}" data-status="active">恢复</button>` : ""}
          </td>
        </tr>
      `
    )
    .join("");

  qsa(".redeem-toggle").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await getJson("/admin-api/redeem-codes/status", {
          method: "POST",
          body: JSON.stringify({
            code: button.dataset.code,
            status: button.dataset.status
          })
        });
        await refreshRedeemCodes();
      } catch (error) {
        qs("#redeem-generate-result").textContent = `状态更新失败：${error.message}`;
      }
    });
  });
}

function renderWords(words) {
  qs("#words-grid").innerHTML = words
    .map(
      (item) => `
        <article class="word-card">
          <span class="tag">议题词</span>
          <h3>${item.word}</h3>
          <p>状态：${item.status}</p>
          <p>最近使用：${item.usedCount} 次</p>
        </article>
      `
    )
    .join("");
}

function renderPromptSummary(prompts) {
  const prompt = prompts[0];
  if (!prompt) {
    qs("#prompt-summary").innerHTML = "<p>暂无 Prompt 配置</p>";
    return;
  }

  qs("#prompt-system-text").value = prompt.systemPrompt;
  qs("#prompt-user-template").value = prompt.userPromptTemplate;

  qs("#prompt-summary").innerHTML = `
    <div class="prompt-card__head">
      <div>
        <p class="prompt-card__eyebrow">当前生效版本</p>
        <h3>${prompt.promptName}</h3>
      </div>
      <span class="tag">v${prompt.versionNo} 已发布</span>
    </div>
    <div class="prompt-meta">
      <span>Prompt Key：${prompt.promptKey}</span>
      <span>Model：${prompt.modelName}</span>
      <span>Provider：${prompt.providerCode}</span>
      <span>更新时间：${prompt.updatedAt}</span>
      <span>System Prompt：${prompt.systemPrompt}</span>
      <span>User Prompt：${prompt.userPromptTemplate}</span>
    </div>
    <div class="prompt-actions">
      <button class="primary-button" type="button" id="save-prompt-shortcut">保存当前版本为新版本</button>
      <button class="ghost-button" type="button">当前已直接走真实模型试跑</button>
    </div>
  `;

  qs("#save-prompt-shortcut").addEventListener("click", () => {
    savePromptConfig().catch((error) => {
      qs("#test-result").textContent = `保存失败：${error.message}`;
    });
  });
}

function renderRuntimeConfig(config) {
  qs("#runtime-api-url").value = config.modelApiUrl || "";
  qs("#runtime-api-key").value = config.modelApiKey || "";
  qs("#runtime-model-name").value = config.modelApiModel || "gpt-4o";
  qs("#runtime-provider-code").value = config.modelProviderCode || "yunwu";
  qs("#runtime-require-real-ai").checked = Boolean(config.requireRealAi);
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
          <td>${item.updatedAt}</td>
        </tr>
      `
    )
    .join("");
}

async function runPromptTest() {
  const promptKey = "card_association_feedback";
  const selectedWords = qs("#test-selected-words").value.split("/").map((item) => item.trim()).filter(Boolean);
  const userText = qs("#test-user-text").value.trim();
  const result = await getJson("/admin-api/config/ai-prompts/test", {
    method: "POST",
    body: JSON.stringify({
      promptKey,
      selectedWords,
      userText,
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
      feedback: result.feedback,
      rawResponse: result.rawResponse
    },
    null,
    2
  );
}

async function savePromptConfig() {
  const result = await getJson("/admin-api/config/ai-prompts/update", {
    method: "POST",
    body: JSON.stringify({
      promptKey: "card_association_feedback",
      systemPrompt: qs("#prompt-system-text").value.trim(),
      userPromptTemplate: qs("#prompt-user-template").value.trim()
    })
  });
  renderPromptSummary(result);
  qs("#test-result").textContent = "Prompt 已保存为新版本，可以直接点“试跑一次”验证。";
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

async function refreshRedeemCodes() {
  const codes = await getJson("/admin-api/redeem-codes");
  renderRedeemCodes(codes);
}

async function generateRedeemCodes() {
  const result = await getJson("/admin-api/redeem-codes/generate", {
    method: "POST",
    body: JSON.stringify({
      quantity: Number(qs("#redeem-generate-quantity").value || 10),
      prefix: qs("#redeem-generate-prefix").value.trim(),
      planName: qs("#redeem-generate-plan").value.trim()
    })
  });

  qs("#redeem-generate-result").textContent = result.codes.map((item) => item.code).join("\n");
  renderRedeemCodes([...(result.codes || []), ...((await getJson("/admin-api/redeem-codes")).filter((item) => !result.codes.some((created) => created.code === item.code)))]);
}

async function bootstrap() {
  try {
    const [overview, users, orders, words, prompts, jobs, runtimeConfig, redeemCodes] = await Promise.all([
      getJson("/admin-api/dashboard/overview"),
      getJson("/admin-api/users"),
      getJson("/admin-api/orders"),
      getJson("/admin-api/content/words"),
      getJson("/admin-api/config/ai-prompts"),
      getJson("/admin-api/ai-feedback/jobs"),
      getJson("/admin-api/config/runtime"),
      getJson("/admin-api/redeem-codes")
    ]);

    renderOverview(overview);
    renderUsers(users);
    renderOrders(orders);
    renderWords(words);
    renderPromptSummary(prompts);
    renderJobs(jobs);
    renderRuntimeConfig(runtimeConfig);
    renderRedeemCodes(redeemCodes);
  } catch (error) {
    console.error(error);
    document.body.insertAdjacentHTML(
      "afterbegin",
      `<div class="admin-error">后台数据加载失败，请先启动本地服务：python3 /Users/lisa888/Documents/表达高手/backend/server.py</div>`
    );
  }
}

qsa(".nav-link").forEach((button) => {
  button.addEventListener("click", () => activateView(button.dataset.view));
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

qs("#generate-redeem-codes").addEventListener("click", () => {
  generateRedeemCodes().catch((error) => {
    qs("#redeem-generate-result").textContent = `生成失败：${error.message}`;
  });
});

bootstrap();
