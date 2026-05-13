const app = getApp();

Page({
  data: {
    profile: null
  },

  async onShow() {
    try {
      this.setData({
        profile: await app.getProfileState()
      });
    } catch (error) {
      wx.showToast({
        title: "个人信息加载失败",
        icon: "none"
      });
    }
  },

  handleOpenMembership() {
    wx.navigateTo({
      url: "/pages/membership/index"
    });
  },

  handleOpenHistory() {
    wx.switchTab({
      url: "/pages/history/index"
    });
  }
});
