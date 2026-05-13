const app = getApp();

Page({
  data: {
    selectedCards: [],
    statusText: "导师正在分析你的表达...",
    subStatusText: "我们会先判断你的判断句是否成立，再分析解释是否具体、自然。"
  },

  async onLoad() {
    try {
      const state = await app.getCurrentRoundState();
      this.setData({
        selectedCards: state ? state.selectedCards : []
      });

      const transcriptText = app.getPendingTranscript();
      const feedback = await app.completeCurrentTraining(transcriptText);
      this.setData({
        statusText: "分析完成，正在生成反馈页...",
        subStatusText: feedback && feedback.aiSource ? `评分来源：${feedback.aiSource}` : "即将展示本次点评。"
      });

      setTimeout(() => {
        wx.redirectTo({
          url: "/pages/feedback/index"
        });
      }, 500);
    } catch (error) {
      wx.showToast({
        title: error.message || "导师分析失败",
        icon: "none"
      });
      setTimeout(() => {
        wx.redirectTo({
          url: "/pages/speaking/index"
        });
      }, 800);
    }
  }
});
