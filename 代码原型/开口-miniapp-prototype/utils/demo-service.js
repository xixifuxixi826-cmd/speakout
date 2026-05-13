const {
  roundDecks,
  initialHistory,
  adminUsers,
  adminOrders
} = require("./mock-data");

function deepCopy(value) {
  return JSON.parse(JSON.stringify(value));
}

function buildRound(roundIndex, sessionIndex) {
  const deck = roundDecks[roundIndex % roundDecks.length];

  return {
    id: `round-${sessionIndex + 1}`,
    roundNo: sessionIndex + 1,
    sourceDeckId: deck.id,
    cards: deck.cards.map((card) => ({
      ...card,
      state: "hidden"
    }))
  };
}

function createStore() {
  return {
    freeQuotaLimit: 3,
    user: {
      nickname: "表达高手体验官",
      startedRoundsToday: 0
    },
    membership: {
      isMember: false,
      planName: "普通版"
    },
    history: deepCopy(initialHistory),
    currentRoundIndex: 0,
    currentRound: null,
    currentSelection: [],
    currentDraft: "",
    latestFeedback: null,
    latestHistoryId: initialHistory[0] ? initialHistory[0].id : "",
    adminUsers: deepCopy(adminUsers),
    adminOrders: deepCopy(adminOrders)
  };
}

const store = createStore();

function getRemainingQuota() {
  if (store.membership.isMember) {
    return -1;
  }

  return Math.max(0, store.freeQuotaLimit - store.user.startedRoundsToday);
}

function getCurrentRoundState() {
  const round = store.currentRound;
  if (!round) {
    return null;
  }

  const usedCount = round.cards.filter((card) => card.state === "used").length;
  const flippedCount = round.cards.filter((card) => card.state !== "hidden").length;
  const selectedCards = round.cards.filter((card) => store.currentSelection.includes(card.id));

  return {
    sessionId: round.id,
    roundNo: round.roundNo,
    usedCount,
    flippedCount,
    totalCount: round.cards.length,
    selectedCount: selectedCards.length,
    isComplete: usedCount === round.cards.length,
    cards: deepCopy(round.cards),
    selectedCards: deepCopy(selectedCards),
    remainingQuota: getRemainingQuota(),
    draftText: store.currentDraft,
    feedback: store.latestFeedback
  };
}

function buildFeedback(submissionText) {
  const selectedCards = getSelectedCards();
  const [first, second] = selectedCards;
  const textLength = (submissionText || "").trim().length;
  const totalScore = Math.min(95, 68 + Math.floor(textLength / 8));
  const summary =
    textLength > 50
      ? "你已经建立了两个词之间的关系，表达方向是成立的。"
      : "你已经开始建立词语联系，但还能再具体一些。";

  const details = [
    {
      label: "结构清晰度",
      score: Math.min(95, totalScore + 2),
      note: "能听出主线，但开头转入场景还可以更快。"
    },
    {
      label: "联想具体性",
      score: Math.max(62, totalScore - 6),
      note: "建议增加人物、动作或环境细节。"
    },
    {
      label: "连接自然度",
      score: Math.min(96, totalScore + 1),
      note: "两个词的关系是成立的，没有被词性限制住。"
    }
  ];

  return {
    id: `feedback-${Date.now()}`,
    pairTitle: `${first.word} + ${second.word}`,
    totalScore,
    summary,
    rewrite:
      `可以试着这样重说：${first.word}是一种${second.word}。` +
      "先把这句观点立住，再补一个具体场景去解释它为什么成立。",
    suggestions: [
      "先用“ A 是 B ”或“ A 是一种 B ”直接立观点。",
      "再补一层因果或场景，解释为什么这个判断说得通。",
      "结尾补一句你的理解，让这句观点更像完整判断。"
    ],
    details,
    visibleDetails: store.membership.isMember ? details : details.slice(0, 2),
    freeModeNote: store.membership.isMember ? "" : "免费用户当前只展示精简版 AI 点评，高手会员可查看完整拆解。"
  };
}

function getSelectedCards() {
  const round = store.currentRound;
  if (!round) {
    return [];
  }

  return round.cards.filter((card) => store.currentSelection.includes(card.id));
}

module.exports = {
  modeName: "demo",

  async getHomeSummary() {
    return {
      nickname: store.user.nickname,
      isMember: store.membership.isMember,
      planName: store.membership.planName,
      memberLabel: store.membership.isMember ? "高手会员" : "免费用户",
      remainingQuotaText: store.membership.isMember ? "无限次" : `${getRemainingQuota()} / ${store.freeQuotaLimit}`,
      activeRoundText: store.currentRound ? "当前轮次进行中" : "今日可开新轮次",
      startButtonText: `开始第 ${store.user.startedRoundsToday + 1} 轮`,
      hasLatestHistory: Boolean(store.history[0]),
      latestHistoryTitle: store.history[0] ? store.history[0].title : "",
      latestHistoryScore: store.history[0] ? String(store.history[0].score) : "",
      latestHistorySummary: store.history[0] ? store.history[0].summary : ""
    };
  },

  async startTrainingRound() {
    if (
      store.currentRound &&
      !store.currentRound.cards.every((card) => card.state === "used")
    ) {
      return { blocked: false, state: getCurrentRoundState() };
    }

    if (!store.membership.isMember && getRemainingQuota() <= 0) {
      return { blocked: true };
    }

    const sessionIndex = store.user.startedRoundsToday;
    store.currentRound = buildRound(store.currentRoundIndex, sessionIndex);
    store.currentSelection = [];
    store.currentDraft = "";
    store.latestFeedback = null;
    store.user.startedRoundsToday += 1;
    store.currentRoundIndex += 1;

    return { blocked: false, state: getCurrentRoundState() };
  },

  async getCurrentRoundState() {
    return getCurrentRoundState();
  },

  async revealOrToggleCard(cardId) {
    const round = store.currentRound;
    if (!round) {
      return { error: "round_missing" };
    }

    const card = round.cards.find((item) => item.id === cardId);
    if (!card || card.state === "used") {
      return { error: "card_locked" };
    }

    if (card.state === "hidden") {
      card.state = "flipped";
    }

    const selectedIndex = store.currentSelection.indexOf(cardId);
    if (selectedIndex >= 0) {
      store.currentSelection.splice(selectedIndex, 1);
    } else if (store.currentSelection.length < 2) {
      store.currentSelection.push(cardId);
    } else {
      return { error: "selection_full" };
    }

    return { ok: true, state: getCurrentRoundState() };
  },

  async saveDraft(draftText) {
    store.currentDraft = draftText;
    return getCurrentRoundState();
  },

  getCurrentDraft() {
    return store.currentDraft || "";
  },

  getSelectedCards() {
    return getSelectedCards();
  },

  async completeCurrentTraining(transcriptText) {
    const round = store.currentRound;
    const selectedCards = getSelectedCards();
    if (!round || selectedCards.length !== 2) {
      throw new Error("当前必须先选中两张卡片");
    }

    selectedCards.forEach((card) => {
      const target = round.cards.find((item) => item.id === card.id);
      if (target) {
        target.state = "used";
      }
    });

    const feedback = buildFeedback(transcriptText);
    const record = {
      id: `history-${Date.now()}`,
      title: `第${round.roundNo}轮｜${selectedCards[0].word} + ${selectedCards[1].word}`,
      timeLabel: "刚刚",
      pair: [selectedCards[0].word, selectedCards[1].word],
      excerpt: transcriptText,
      score: feedback.totalScore,
      summary: feedback.summary,
      details: feedback.details,
      suggestions: feedback.suggestions
    };

    store.history.unshift(record);
    store.currentSelection = [];
    store.currentDraft = "";
    store.latestFeedback = {
      ...feedback,
      isRoundComplete: round.cards.every((card) => card.state === "used"),
      latestHistoryId: record.id
    };
    store.latestHistoryId = record.id;

    return store.latestFeedback;
  },

  async getLatestFeedbackState() {
    return store.latestFeedback;
  },

  async continueAfterFeedback() {
    const round = store.currentRound;
    if (!round) {
      return { route: "/pages/home/index" };
    }

    if (round.cards.every((card) => card.state === "used")) {
      store.currentRound = null;
      store.currentSelection = [];
      store.currentDraft = "";
      store.latestFeedback = null;

      if (!store.membership.isMember && getRemainingQuota() <= 0) {
        return { route: "/pages/membership/index?from=quota" };
      }

      return { route: "/pages/training/index?mode=next" };
    }

    store.latestFeedback = null;
    return { route: "/pages/training/index" };
  },

  async getHistoryList() {
    return deepCopy(store.history);
  },

  async getHistoryById(recordId) {
    return deepCopy(store.history.find((item) => item.id === recordId) || null);
  },

  async activateMembership() {
    store.membership = {
      isMember: true,
      planName: "高手会员"
    };
    return {
      profile: await this.getProfileState(),
      orderNo: `DEMO-${Date.now()}`
    };
  },

  async getProfileState() {
    return {
      nickname: store.user.nickname,
      isMember: store.membership.isMember,
      planName: store.membership.planName,
      usedFreeRounds: Math.min(store.user.startedRoundsToday, store.freeQuotaLimit),
      remainingQuota: store.membership.isMember ? "无限次" : getRemainingQuota()
    };
  },

  async getAdminState() {
    const paidUsers = store.adminUsers.filter((item) => item.membershipStatus === "会员").length;

    return {
      overview: {
        registeredUsers: store.adminUsers.length,
        dailyActiveUsers: 126,
        trainingVolume: store.history.length,
        paidUsers,
        revenue: "¥4,980"
      },
      users: deepCopy(store.adminUsers),
      orders: deepCopy(store.adminOrders),
      words: deepCopy(
        roundDecks[0].cards.slice(0, 8).map((item) => ({
          word: item.word,
          status: "已发布",
          usedCount: 12
        }))
      ),
      prompts: [
        {
          promptKey: "card_association_feedback",
          promptName: "卡片联想评分",
          versionNo: 3,
          modelName: "local-scorer-v1",
          providerCode: "demo",
          status: "published",
          updatedAt: "本地演示模式",
          systemPrompt: "你是一名表达训练教练，重点判断观点句是否成立、解释是否具体。",
          userPromptTemplate: "训练词语：{{selected_words}} 用户表达：{{user_text}}"
        }
      ],
      jobs: []
    };
  }
};
