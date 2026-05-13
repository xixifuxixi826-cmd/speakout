const roundDecks = [
  {
    id: "deck-a",
    cards: [
      { id: "a-1", word: "自由", kind: "concept" },
      { id: "a-2", word: "束缚", kind: "concept" },
      { id: "a-3", word: "谎言", kind: "concept" },
      { id: "a-4", word: "成长", kind: "concept" },
      { id: "a-5", word: "安全感", kind: "concept" },
      { id: "a-6", word: "孤独", kind: "concept" },
      { id: "a-7", word: "欲望", kind: "concept" },
      { id: "a-8", word: "秩序", kind: "concept" },
      { id: "a-9", word: "体面", kind: "concept" },
      { id: "a-10", word: "野心", kind: "concept" },
      { id: "a-11", word: "痛苦", kind: "concept" },
      { id: "a-12", word: "亲密", kind: "concept" },
      { id: "a-13", word: "稳定", kind: "concept" },
      { id: "a-14", word: "选择", kind: "concept" },
      { id: "a-15", word: "焦虑", kind: "concept" },
      { id: "a-16", word: "边界", kind: "concept" }
    ]
  },
  {
    id: "deck-b",
    cards: [
      { id: "b-1", word: "公平", kind: "concept" },
      { id: "b-2", word: "偏见", kind: "concept" },
      { id: "b-3", word: "效率", kind: "concept" },
      { id: "b-4", word: "善良", kind: "concept" },
      { id: "b-5", word: "责任", kind: "concept" },
      { id: "b-6", word: "天赋", kind: "concept" },
      { id: "b-7", word: "代价", kind: "concept" },
      { id: "b-8", word: "服从", kind: "concept" },
      { id: "b-9", word: "尊严", kind: "concept" },
      { id: "b-10", word: "控制", kind: "concept" },
      { id: "b-11", word: "信任", kind: "concept" },
      { id: "b-12", word: "脆弱", kind: "concept" },
      { id: "b-13", word: "嫉妒", kind: "concept" },
      { id: "b-14", word: "共情", kind: "concept" },
      { id: "b-15", word: "失败", kind: "concept" },
      { id: "b-16", word: "原谅", kind: "concept" }
    ]
  },
  {
    id: "deck-c",
    cards: [
      { id: "c-1", word: "原生家庭", kind: "concept" },
      { id: "c-2", word: "自律", kind: "concept" },
      { id: "c-3", word: "自由意志", kind: "concept" },
      { id: "c-4", word: "比较", kind: "concept" },
      { id: "c-5", word: "内耗", kind: "concept" },
      { id: "c-6", word: "爱情", kind: "concept" },
      { id: "c-7", word: "婚姻", kind: "concept" },
      { id: "c-8", word: "工作", kind: "concept" },
      { id: "c-9", word: "意义", kind: "concept" },
      { id: "c-10", word: "身份", kind: "concept" },
      { id: "c-11", word: "标签", kind: "concept" },
      { id: "c-12", word: "羞耻", kind: "concept" },
      { id: "c-13", word: "愤怒", kind: "concept" },
      { id: "c-14", word: "妥协", kind: "concept" },
      { id: "c-15", word: "冒险", kind: "concept" },
      { id: "c-16", word: "现实", kind: "concept" }
    ]
  }
];

const initialHistory = [
  {
    id: "history-seed-1",
    title: "第1轮｜自由 + 束缚",
    timeLabel: "04-19 10:32",
    pair: ["自由", "束缚"],
    excerpt: "我会把自由理解成一种看见束缚之后依然主动选择的能力，所以自由本身就是一种更高级的束缚。",
    score: 83,
    summary: "判断句有张力，解释也成立，但还可以补一个更具体的现实场景。",
    details: [
      { label: "结构清晰度", score: 86, note: "观点先行，因果线比较清楚。" },
      { label: "联想具体性", score: 78, note: "建议补进工作或亲密关系的例子。" },
      { label: "连接自然度", score: 85, note: "两词之间的张力被解释出来了。" }
    ],
    suggestions: [
      "把“主动选择限制”放进一个具体人物身上。",
      "补一句你为什么不把束缚理解成压迫。"
    ]
  },
  {
    id: "history-seed-2",
    title: "第1轮｜成长 + 谎言",
    timeLabel: "04-18 21:14",
    pair: ["成长", "谎言"],
    excerpt: "我觉得成长是一种不断拆穿旧谎言的过程，因为很多我们曾经深信不疑的东西，最后都要亲手推翻。",
    score: 88,
    summary: "观点有辨识度，语言也顺，但还能再增强情绪层次。",
    details: [
      { label: "结构清晰度", score: 89, note: "开头立场很稳，后续延展自然。" },
      { label: "联想具体性", score: 84, note: "如果补一段成长中的具体瞬间会更强。" },
      { label: "连接自然度", score: 90, note: "“拆穿”这个动作把两词连得很顺。" }
    ],
    suggestions: [
      "补一段你在哪个时刻意识到旧信念失效了。",
      "把“痛感”说得更具体一点。"
    ]
  }
];

const adminUsers = [
  {
    id: "U1001",
    nickname: "林乔",
    registeredAt: "2026-04-10 09:16",
    activityState: "近 24h 活跃",
    membershipStatus: "会员",
    trainingSummary: "12 轮 / 36 次表达"
  },
  {
    id: "U1002",
    nickname: "周沐",
    registeredAt: "2026-04-11 20:03",
    activityState: "近 7d 活跃",
    membershipStatus: "免费",
    trainingSummary: "3 轮 / 8 次表达"
  },
  {
    id: "U1003",
    nickname: "姜禾",
    registeredAt: "2026-04-14 12:48",
    activityState: "今日新增",
    membershipStatus: "会员",
    trainingSummary: "6 轮 / 18 次表达"
  }
];

const adminOrders = [
  {
    orderNo: "KK20260419001",
    user: "林乔",
    amount: "¥19",
    status: "已支付",
    paidAt: "2026-04-19 09:23"
  },
  {
    orderNo: "KK20260418007",
    user: "姜禾",
    amount: "¥19",
    status: "已支付",
    paidAt: "2026-04-18 22:10"
  }
];

module.exports = {
  roundDecks,
  initialHistory,
  adminUsers,
  adminOrders
};
