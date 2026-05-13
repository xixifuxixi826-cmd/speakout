const app = getApp();

Page({
  data: {
    isMember: false,
    planName: "普通版",
    memberLabel: "免费用户",
    remainingQuotaText: "3 / 3",
    activeRoundText: "今日可开新轮次",
    startButtonText: "开始第 1 轮",
    latestHistoryTitle: "第1轮｜热烈 + 松弛",
    latestHistoryScore: "83",
    latestHistorySummary: "主线已经成立，表达自然，但场景细节还可以继续补充。",
    hasLatestHistory: true
  },

  async onShow() {
    try {
      const summary = await app.getHomeSummary();
      this.setData(summary);
    } catch (error) {
      wx.showToast({
        title: "首页数据加载失败",
        icon: "none"
      });
    }
  },

  async handleStart() {
    try {
      const result = await app.startTrainingRound();
      if (result.blocked) {
        wx.navigateTo({
          url: "/pages/membership/index?from=quota"
        });
        return;
      }

      wx.navigateTo({
        url: "/pages/training/index"
      });
    } catch (error) {
      wx.showToast({
        title: "训练启动失败",
        icon: "none"
      });
    }
  }
});
