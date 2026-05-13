const app = getApp();

function formatClock(totalSeconds) {
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

Page({
  data: {
    selectedCards: [],
    secondsLeft: 30,
    clockText: "00:30"
  },

  async onLoad() {
    try {
      const state = await app.getCurrentRoundState();
      this.setData({
        selectedCards: state ? state.selectedCards : [],
        secondsLeft: 30,
        clockText: "00:30"
      });
      this.startTimer();
    } catch (error) {
      wx.showToast({
        title: "构思页加载失败",
        icon: "none"
      });
    }
  },

  onUnload() {
    this.stopTimer();
  },

  startTimer() {
    this.stopTimer();
    this.timer = setInterval(() => {
      const nextValue = this.data.secondsLeft - 1;
      if (nextValue <= 0) {
        this.stopTimer();
        this.goNext();
        return;
      }

      this.setData({
        secondsLeft: nextValue,
        clockText: formatClock(nextValue)
      });
    }, 1000);
  },

  stopTimer() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  },

  goNext() {
    wx.redirectTo({
      url: "/pages/speaking/index"
    });
  },

  handleSkip() {
    this.stopTimer();
    this.goNext();
  }
});
