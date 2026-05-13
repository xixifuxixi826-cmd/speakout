const app = getApp();

function decorateState(state) {
  if (!state) {
    return null;
  }

  return {
    ...state,
    cards: state.cards.map((card) => ({
      ...card,
      isSelected: state.selectedCards.some((item) => item.id === card.id)
    }))
  };
}

Page({
  data: {
    state: null
  },

  async ensureRound() {
    let state = await app.getCurrentRoundState();
    if (state) {
      return state;
    }

    const result = await app.startTrainingRound();
    if (result.blocked) {
      wx.redirectTo({
        url: "/pages/membership/index?from=quota"
      });
      return null;
    }

    return result.state || null;
  },

  async onLoad(options) {
    if (options.mode === "next") {
      const result = await app.startTrainingRound();
      if (result.blocked) {
        wx.redirectTo({
          url: "/pages/membership/index?from=quota"
        });
        return;
      }
    }
  },

  async onShow() {
    try {
      const state = await this.ensureRound();
      if (!state) {
        return;
      }

      this.setData({
        state: decorateState(state)
      });
    } catch (error) {
      wx.showToast({
        title: "训练数据加载失败",
        icon: "none"
      });
    }
  },

  async handleCardTap(event) {
    const { id } = event.currentTarget.dataset;
    try {
      const result = await app.revealOrToggleCard(id);
      if (result.error === "selection_full") {
        wx.showToast({
          title: "一次只能选 2 张卡",
          icon: "none"
        });
        return;
      }

      this.setData({
        state: decorateState(result.state)
      });
    } catch (error) {
      wx.showToast({
        title: "卡片状态更新失败",
        icon: "none"
      });
    }
  },

  async handleProceed() {
    try {
      const state = await app.getCurrentRoundState();
      if (!state) {
        return;
      }

      if (state.isComplete) {
        const result = await app.startTrainingRound();
        if (result.blocked) {
          wx.redirectTo({
            url: "/pages/membership/index?from=quota"
          });
          return;
        }

        this.setData({
          state: decorateState(result.state)
        });
        return;
      }

      if (state.selectedCount !== 2) {
        wx.showToast({
          title: "先选 2 张卡",
          icon: "none"
        });
        return;
      }

      wx.navigateTo({
        url: "/pages/thinking/index"
      });
    } catch (error) {
      wx.showToast({
        title: "当前轮次状态异常",
        icon: "none"
      });
    }
  }
});
