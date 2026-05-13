const app = getApp();

Page({
  data: {
    feedback: null
  },

  async onShow() {
    try {
      const feedback = await app.getLatestFeedbackState();
      if (!feedback) {
        wx.redirectTo({
          url: "/pages/home/index"
        });
        return;
      }

      this.setData({ feedback });
    } catch (error) {
      wx.showToast({
        title: "点评数据加载失败",
        icon: "none"
      });
    }
  },

  handleRetry() {
    wx.redirectTo({
      url: "/pages/speaking/index"
    });
  },

  async handleContinue() {
    try {
      const result = await app.continueAfterFeedback();
      wx.redirectTo({
        url: result.route
      });
    } catch (error) {
      wx.showToast({
        title: "流程继续失败",
        icon: "none"
      });
    }
  },

  handleGoMembership() {
    wx.navigateTo({
      url: "/pages/membership/index?from=feedback"
    });
  },

  handleViewDetail() {
    wx.navigateTo({
      url: `/pages/history-detail/index?id=${this.data.feedback.latestHistoryId}`
    });
  }
});
