const app = getApp();

Page({
  data: {
    fromQuota: false,
    profile: null,
    showPaySheet: false,
    isPaying: false,
    paymentState: "idle"
  },

  onLoad(options) {
    this.setData({
      fromQuota: options.from === "quota"
    });
  },

  async onShow() {
    try {
      this.setData({
        profile: await app.getProfileState()
      });
    } catch (error) {
      wx.showToast({
        title: "会员信息加载失败",
        icon: "none"
      });
    }
  },

  handleOpenPay() {
    this.setData({
      showPaySheet: true,
      paymentState: "confirm",
      isPaying: false
    });
  },

  handleClosePay() {
    if (this.data.isPaying) {
      return;
    }

    this.setData({
      showPaySheet: false,
      paymentState: "idle"
    });
  },

  async handleActivate() {
    this.setData({
      isPaying: true,
      paymentState: "processing"
    });

    try {
      await new Promise((resolve) => setTimeout(resolve, 900));
      const result = await app.activateMembership();
      this.setData({
        profile: result.profile,
        isPaying: false,
        paymentState: "success",
        showPaySheet: false
      });
      wx.showToast({
        title: "支付成功，已开通高手会员",
        icon: "none"
      });
    } catch (error) {
      this.setData({
        isPaying: false,
        paymentState: "idle"
      });
      wx.showToast({
        title: "会员开通失败",
        icon: "none"
      });
    }
  },

  handleGoProfile() {
    if (!this.data.profile || !this.data.profile.isMember) {
      return;
    }

    wx.switchTab({
      url: "/pages/profile/index"
    });
  }
});
