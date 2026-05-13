const { request, BASE_URL } = require("./utils/api");
const demoService = require("./utils/demo-service");

App({
  globalData: {
    baseUrl: BASE_URL,
    currentRound: null,
    currentDraft: "",
    latestFeedback: null,
    runtimeMode: "remote",
    pendingTranscript: ""
  },

  setCurrentRound(state) {
    this.globalData.currentRound = state;
    this.globalData.currentDraft = state && state.draftText ? state.draftText : "";
  },

  useDemoMode() {
    this.globalData.runtimeMode = "demo";
  },

  isDemoMode() {
    return this.globalData.runtimeMode === "demo";
  },

  async runWithFallback(remoteRunner, demoRunner) {
    if (this.isDemoMode()) {
      return demoRunner();
    }

    try {
      return await remoteRunner();
    } catch (error) {
      this.useDemoMode();
      return demoRunner();
    }
  },

  async getHomeSummary() {
    return this.runWithFallback(
      () =>
        request({
          url: "/api/user/home-summary"
        }),
      () => demoService.getHomeSummary()
    );
  },

  async startTrainingRound() {
    const result = await this.runWithFallback(
      () =>
        request({
          url: "/api/training/session/create",
          method: "POST"
        }),
      () => demoService.startTrainingRound()
    );

    if (result.state) {
      this.setCurrentRound(result.state);
    }

    return result;
  },

  async getCurrentRoundState() {
    const state = await this.runWithFallback(
      () =>
        request({
          url: "/api/training/session/current"
        }),
      () => demoService.getCurrentRoundState()
    );
    this.setCurrentRound(state);
    return state;
  },

  async revealOrToggleCard(cardId) {
    const result = await this.runWithFallback(
      () =>
        request({
          url: "/api/training/session/current/cards/toggle",
          method: "POST",
          data: { cardId }
        }),
      () => demoService.revealOrToggleCard(cardId)
    );

    if (result.state) {
      this.setCurrentRound(result.state);
    }

    return result;
  },

  async saveDraft(draftText) {
    this.globalData.currentDraft = draftText;
    const state = await this.runWithFallback(
      () =>
        request({
          url: "/api/training/session/current/draft",
          method: "POST",
          data: { draftText }
        }),
      () => demoService.saveDraft(draftText)
    );
    this.setCurrentRound(state);
    return state;
  },

  getCurrentDraft() {
    return this.globalData.currentDraft || "";
  },

  setPendingTranscript(text) {
    this.globalData.pendingTranscript = text || "";
  },

  getPendingTranscript() {
    return this.globalData.pendingTranscript || this.globalData.currentDraft || "";
  },

  getSelectedCards() {
    return this.globalData.currentRound ? this.globalData.currentRound.selectedCards || [] : [];
  },

  async completeCurrentTraining(transcriptText) {
    const feedback = await this.runWithFallback(
      () =>
        request({
          url: "/api/training/session/current/submit",
          method: "POST",
          data: { transcriptText }
        }),
      () => demoService.completeCurrentTraining(transcriptText)
    );
    this.globalData.latestFeedback = feedback;
    this.globalData.currentDraft = "";
    this.globalData.pendingTranscript = "";
    return feedback;
  },

  async getLatestFeedbackState() {
    if (this.globalData.latestFeedback) {
      return this.globalData.latestFeedback;
    }

    const feedback = await this.runWithFallback(
      () =>
        request({
          url: "/api/training/session/current/feedback"
        }),
      () => demoService.getLatestFeedbackState()
    );
    this.globalData.latestFeedback = feedback;
    return feedback;
  },

  async continueAfterFeedback() {
    this.globalData.latestFeedback = null;
    return this.runWithFallback(
      () =>
        request({
          url: "/api/training/session/current/continue",
          method: "POST"
        }),
      () => demoService.continueAfterFeedback()
    );
  },

  async getHistoryList() {
    return this.runWithFallback(
      () =>
        request({
          url: "/api/training/history"
        }),
      () => demoService.getHistoryList()
    );
  },

  async getHistoryById(recordId) {
    return this.runWithFallback(
      () =>
        request({
          url: `/api/training/history/${recordId}`
        }),
      () => demoService.getHistoryById(recordId)
    );
  },

  async activateMembership() {
    return this.runWithFallback(
      () =>
        request({
          url: "/api/membership/activate",
          method: "POST"
        }),
      () => demoService.activateMembership()
    );
  },

  async getProfileState() {
    return this.runWithFallback(
      () =>
        request({
          url: "/api/user/profile"
        }),
      () => demoService.getProfileState()
    );
  },

  async getAdminState() {
    return this.runWithFallback(
      async () => {
        const [overview, users, orders, words, prompts, jobs] = await Promise.all([
          request({ url: "/admin-api/dashboard/overview" }),
          request({ url: "/admin-api/users" }),
          request({ url: "/admin-api/orders" }),
          request({ url: "/admin-api/content/words" }),
          request({ url: "/admin-api/config/ai-prompts" }),
          request({ url: "/admin-api/ai-feedback/jobs" })
        ]);

        return {
          overview,
          users,
          orders,
          words,
          prompts,
          jobs
        };
      },
      () => demoService.getAdminState()
    );
  }
});
