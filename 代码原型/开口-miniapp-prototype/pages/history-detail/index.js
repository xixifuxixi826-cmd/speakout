const app = getApp();

Page({
  data: {
    record: null
  },

  async onLoad(options) {
    try {
      const record = await app.getHistoryById(options.id);
      this.setData({ record });
    } catch (error) {
      wx.showToast({
        title: "详情加载失败",
        icon: "none"
      });
    }
  }
});
