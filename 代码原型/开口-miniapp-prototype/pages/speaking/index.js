const app = getApp();

function formatClock(totalSeconds) {
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

Page({
  data: {
    selectedCards: [],
    transcriptText: "",
    secondsLeft: 120,
    clockText: "02:00",
    isRecording: false,
    transcriptStatus: "idle",
    transcriptChunks: []
  },

  async onLoad() {
    try {
      const state = await app.getCurrentRoundState();
      const draftText = state ? state.draftText || "" : "";
      this.setData({
        selectedCards: state ? state.selectedCards : [],
        transcriptText: draftText,
        secondsLeft: 120,
        clockText: "02:00",
        isRecording: false,
        transcriptStatus: draftText ? "finished" : "idle"
      });
      this.startTimer();
    } catch (error) {
      wx.showToast({
        title: "表达页加载失败",
        icon: "none"
      });
    }
  },

  onUnload() {
    this.stopTimer();
    this.stopMockRecording();
  },

  startTimer() {
    this.stopTimer();
    this.timer = setInterval(() => {
      const nextValue = this.data.secondsLeft - 1;
      if (nextValue <= 0) {
        this.stopTimer();
        this.handleSubmit();
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

  buildMockTranscript() {
    const words = this.data.selectedCards.map((item) => item.word);
    const first = words[0] || "热烈";
    const second = words[1] || "松弛";

    return [
      `我的观点是，${first}是一种${second}。`,
      `因为真正的${second}，不一定是平的，它也可能带着很强的${first}感。`,
      `比如一个人在表达立场的时候，外面看起来很${first}，但内核其实是稳定和有控制感的。`,
      `所以我会把${first}理解成一种更外显的力量，而${second}是它背后更深的状态，这样这个判断就成立了。`
    ];
  },

  stopMockRecording() {
    if (this.recordTimer) {
      clearInterval(this.recordTimer);
      this.recordTimer = null;
    }
  },

  async handleStartRecording() {
    if (this.data.isRecording) {
      return;
    }

    const transcriptChunks = this.buildMockTranscript();
    this.setData({
      isRecording: true,
      transcriptStatus: "recording",
      transcriptText: "",
      transcriptChunks
    });
    try {
      await app.saveDraft("");
    } catch (error) {
      wx.showToast({
        title: "转写草稿初始化失败",
        icon: "none"
      });
    }

    let index = 0;
    this.stopMockRecording();
    this.recordTimer = setInterval(() => {
      const nextChunk = transcriptChunks[index];

      if (!nextChunk) {
        this.stopMockRecording();
        this.setData({
          isRecording: false,
          transcriptStatus: "finished"
        });
        return;
      }

      const transcriptText = `${this.data.transcriptText}${this.data.transcriptText ? "\n" : ""}${nextChunk}`;
      this.setData({
        transcriptText
      });
      app.saveDraft(transcriptText).catch(() => {});
      index += 1;
    }, 1100);
  },

  handleStopRecording() {
    this.stopMockRecording();
    this.setData({
      isRecording: false,
      transcriptStatus: this.data.transcriptText ? "finished" : "idle"
    });
  },

  async handleResetRecording() {
    this.stopMockRecording();
    this.setData({
      isRecording: false,
      transcriptStatus: "idle",
      transcriptText: ""
    });
    try {
      await app.saveDraft("");
      app.setPendingTranscript("");
    } catch (error) {
      wx.showToast({
        title: "转写草稿清空失败",
        icon: "none"
      });
    }
  },

  handleTranscriptInput(event) {
    const transcriptText = event.detail.value;
    this.setData({
      transcriptText,
      transcriptStatus: transcriptText.trim() ? "finished" : "idle"
    });
    app.setPendingTranscript(transcriptText);
    app.saveDraft(transcriptText).catch(() => {});
  },

  async handleSubmit() {
    if (!this.data.transcriptText.trim()) {
      wx.showToast({
        title: "请先完成一次录音",
        icon: "none"
      });
      return;
    }

    this.stopTimer();
    this.stopMockRecording();
    app.setPendingTranscript(this.data.transcriptText);
    wx.redirectTo({
      url: "/pages/analyzing/index"
    });
  }
});
