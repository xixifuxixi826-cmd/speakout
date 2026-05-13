const app = getApp();

Page({
  data: {
    records: []
  },

  async onShow() {
    try {
      this.setData({
        records: await app.getHistoryList()
      });
    } catch (error) {
      wx.showToast({
        title: "记录加载失败",
        icon: "none"
      });
    }
  },

  handleOpenDetail(event) {
    const { id } = event.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/history-detail/index?id=${id}`
    });
  }
});
