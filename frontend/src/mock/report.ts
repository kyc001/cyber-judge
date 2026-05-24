import type { ReportPayload, SharePayload } from "../contracts/report";

export const mockGroupReport: ReportPayload = {
  report_id: "demo-report-001",
  report_type: "group_roast",
  created_at: "2026-05-24T08:00:00.000Z",
  title: "赛博判官年度群聊锐评",
  tagline: "这不是聊天记录，这是当代年轻人的精神体检报告。",
  hero: {
    kicker: "群聊人格样本",
    quote: "你们群最可怕的不是话多，是每个人都像在给互联网留遗嘱。",
    visual: "判",
  },
  tags: ["深夜放毒群", "元宝语录矿区", "嘴硬互助会", "赛博龙王局"],
  sections: [
    {
      id: "summary",
      type: "summary",
      heading: "群体人设",
      body: "这是一个白天假装体面，晚上集体发癫的高密度互助群。群友之间的默契主要来自三件事：一起熬夜、一起嘴硬、一起把小事讲成连续剧。",
    },
    {
      id: "dragon",
      type: "dragon_rank",
      heading: "龙王榜",
      body: "真正的群聊发动机，从来不会承认自己在刷屏。",
      chart_ref: "participants",
    },
    {
      id: "heatmap",
      type: "heatmap",
      heading: "发疯时段热力图",
      body: "从数据看，你们不是没有作息，只是作息长得比较抽象。",
      chart_ref: "heatmap",
    },
    {
      id: "keywords",
      type: "keywords",
      heading: "高频梗词云",
      body: "这些词一出现，群里的空气就会开始变形。",
      chart_ref: "keywords",
    },
    {
      id: "radar",
      type: "radar",
      heading: "群聊人格雷达",
      body: "本群综合画像：嘴硬指数拉满，行动力视天气和 deadline 浮动。",
      chart_ref: "radar",
    },
    {
      id: "emoji",
      type: "emoji",
      heading: "表情包偏好",
      body: "表情包是本群第二官方语言，第一官方语言是阴阳怪气。",
      chart_ref: "emojis",
    },
    {
      id: "timeline",
      type: "timeline",
      heading: "神金时刻时间轴",
      body: "这些瞬间很难解释，但很适合截图保存。",
      chart_ref: "timeline",
    },
  ],
  quotes: [
    {
      id: "q1",
      speaker: "A 同学",
      text: "我只是随便说说，怎么就变成项目方向了？",
      comment: "典型无意识带节奏型人才，建议授予群聊产品经理称号。",
      icon: "sparkles",
    },
    {
      id: "q2",
      speaker: "C 同学",
      text: "我睡了，真的睡了，最后看一眼手机。",
      comment: "这句话在统计学上通常意味着接下来还有 47 条消息。",
      icon: "moon",
    },
    {
      id: "q3",
      speaker: "D 同学",
      text: "别吵，我正在严肃地摸鱼。",
      comment: "本群劳动伦理代表人物，精神状态稳定地不稳定。",
      icon: "coffee",
    },
  ],
  stats: {
    participants: [
      {
        id: "u1",
        name: "A 同学",
        avatar: "A",
        message_count: 1286,
        character_count: 18420,
        emoji_count: 216,
        average_length: 14.3,
        roast: "群聊永动机，负责把沉默五分钟的群强行开机。",
      },
      {
        id: "u2",
        name: "B 同学",
        avatar: "B",
        message_count: 942,
        character_count: 13500,
        emoji_count: 301,
        average_length: 14.8,
        roast: "表情包矿主，能用一张图结束一段关系。",
      },
      {
        id: "u3",
        name: "C 同学",
        avatar: "C",
        message_count: 731,
        character_count: 10212,
        emoji_count: 155,
        average_length: 13.9,
        roast: "嘴上说睡了，手上还在刷新。",
      },
      {
        id: "u4",
        name: "D 同学",
        avatar: "D",
        message_count: 518,
        character_count: 8830,
        emoji_count: 64,
        average_length: 17.0,
        roast: "低频高杀伤，出现一次群里安静三秒。",
      },
      {
        id: "u5",
        name: "E 同学",
        avatar: "E",
        message_count: 402,
        character_count: 6120,
        emoji_count: 89,
        average_length: 15.2,
        roast: "负责把话题从八卦拐到人生哲学。",
      },
    ],
    heatmap: Array.from({ length: 7 * 24 }, (_, index) => {
      const day = Math.floor(index / 24);
      const hour = index % 24;
      const night = hour >= 21 || hour <= 1 ? 0.75 : 0;
      const lunch = hour >= 12 && hour <= 14 ? 0.35 : 0;
      const weekend = day >= 5 ? 0.18 : 0;
      return {
        day,
        hour,
        value: Math.min(1, 0.08 + night + lunch + weekend + ((day * hour) % 7) / 30),
      };
    }),
    keywords: [
      { word: "哈哈哈", count: 620, tone: "hot" },
      { word: "离谱", count: 392, tone: "sharp" },
      { word: "救命", count: 340, tone: "hot" },
      { word: "懂了", count: 221, tone: "calm" },
      { word: "破防", count: 206, tone: "sharp" },
      { word: "晚安", count: 188, tone: "soft" },
      { word: "摸鱼", count: 174, tone: "calm" },
      { word: "绝了", count: 169, tone: "hot" },
      { word: "我服了", count: 150, tone: "sharp" },
      { word: "可以", count: 131, tone: "soft" },
    ],
    radar: [
      { label: "话密度", value: 92 },
      { label: "嘴硬度", value: 88 },
      { label: "深夜活跃", value: 95 },
      { label: "梗浓度", value: 84 },
      { label: "互助值", value: 73 },
      { label: "行动力", value: 61 },
    ],
    emojis: [
      { label: "[捂脸]", value: 216, owner: "B 同学" },
      { label: "[裂开]", value: 164, owner: "A 同学" },
      { label: "[旺柴]", value: 131, owner: "C 同学" },
      { label: "[让我看看]", value: 97, owner: "E 同学" },
    ],
    timeline: [
      {
        id: "t1",
        time: "23:48",
        title: "睡前最后一眼",
        body: "C 同学宣布睡觉后，群聊又持续了 41 分钟。",
      },
      {
        id: "t2",
        time: "12:16",
        title: "午休突发辩论",
        body: "一句“这个需求合理吗”引发 96 条讨论。",
      },
      {
        id: "t3",
        time: "01:07",
        title: "深夜人生会诊",
        body: "从外卖聊到人生意义，中间没有明显刹车痕迹。",
      },
    ],
    relationship_edges: [
      { from: "A 同学", to: "B 同学", weight: 0.8, label: "互相接梗" },
      { from: "C 同学", to: "A 同学", weight: 0.62, label: "深夜召唤" },
    ],
    relationship_metrics: [
      { label: "互相接梗", value: 78, caption: "群内互动密度较高" },
      { label: "主动开聊", value: 64, caption: "A 同学更常点火" },
      { label: "秒回概率", value: 52, caption: "看起来都在假装不在线" },
    ],
  },
  share: {
    slug: "demo-longwang",
    hook: "来测测你在群里是几号龙王",
    watermark: "赛博判官生成",
  },
};

export const mockRelationshipReport: ReportPayload = {
  report_id: "demo-relationship-001",
  report_type: "relationship",
  created_at: "2026-05-24T08:30:00.000Z",
  title: "你们俩的关系，AI 看完沉默了三秒",
  tagline: "这不是普通聊天，这是两个人把熟悉感聊成默认设置的过程。",
  hero: {
    kicker: "双人关系样本",
    quote: "你们最暧昧的地方不是说了什么，是废话都能接得像暗号。",
    visual: "双",
  },
  tags: ["默认搭子", "嘴硬关心", "互相接梗", "晚安观察组"],
  sections: [
    {
      id: "relationship-summary",
      type: "summary",
      heading: "关系定性",
      body: "你们的关系不像普通朋友，更像一种“有事先找你，没事也想烦你”的稳定互相占用。聊天里没有太多直球，但关心常常藏在吐槽和顺手回复里。",
    },
    {
      id: "relationship-map",
      type: "relationship",
      heading: "谁更主动",
      body: "A 同学更常开启话题，B 同学更擅长把话接住。一个负责点火，一个负责续命，整体属于可持续性互相打扰。",
      chart_ref: "relationship_edges",
    },
    {
      id: "relationship-keywords",
      type: "keywords",
      heading: "你们的高频暗号",
      body: "这些词本身没什么，但在你们之间会自动翻译成“我懂你又开始了”。",
      chart_ref: "keywords",
    },
    {
      id: "relationship-timeline",
      type: "timeline",
      heading: "关系升温时间轴",
      body: "真正的关系变化，往往藏在那些没人刻意定义的小瞬间里。",
      chart_ref: "timeline",
    },
    {
      id: "relationship-radar",
      type: "radar",
      heading: "相处模式雷达",
      body: "你们不是特别肉麻，但默契和稳定输出已经高到很难装不熟。",
      chart_ref: "radar",
    },
  ],
  quotes: [
    {
      id: "rq1",
      speaker: "A 同学",
      text: "你别管，我就是顺手问一下。",
      comment: "顺手问一下通常是本关系里最不顺手的关心。",
      icon: "heart",
    },
    {
      id: "rq2",
      speaker: "B 同学",
      text: "你又开始了，但我先听完。",
      comment: "嫌弃是假，继续听是真。嘴硬型陪伴的教科书案例。",
      icon: "message",
    },
    {
      id: "rq3",
      speaker: "A 同学",
      text: "算了，跟你说你肯定懂。",
      comment: "这句话的杀伤力在于：默认你懂，已经是一种关系认证。",
      icon: "sparkles",
    },
  ],
  stats: {
    participants: [
      {
        id: "r1",
        name: "A 同学",
        avatar: "A",
        message_count: 982,
        character_count: 14320,
        emoji_count: 168,
        average_length: 14.6,
        roast: "主动开聊担当，嘴上说随便问问，实际负责把关系续费。",
      },
      {
        id: "r2",
        name: "B 同学",
        avatar: "B",
        message_count: 876,
        character_count: 13240,
        emoji_count: 192,
        average_length: 15.1,
        roast: "稳定接话担当，擅长用嫌弃包装认真陪聊。",
      },
    ],
    heatmap: Array.from({ length: 7 * 24 }, (_, index) => {
      const day = Math.floor(index / 24);
      const hour = index % 24;
      const afterClass = hour >= 20 && hour <= 23 ? 0.78 : 0;
      const afternoon = hour >= 15 && hour <= 17 ? 0.28 : 0;
      const weekend = day >= 5 ? 0.22 : 0;
      return {
        day,
        hour,
        value: Math.min(1, 0.06 + afterClass + afternoon + weekend + ((day + hour) % 5) / 34),
      };
    }),
    keywords: [
      { word: "你又", count: 240, tone: "sharp" },
      { word: "懂", count: 221, tone: "soft" },
      { word: "哈哈哈", count: 216, tone: "hot" },
      { word: "别装", count: 178, tone: "sharp" },
      { word: "随便", count: 146, tone: "calm" },
      { word: "晚安", count: 132, tone: "soft" },
      { word: "等下", count: 118, tone: "calm" },
      { word: "救命", count: 96, tone: "hot" },
    ],
    radar: [
      { label: "默契度", value: 91 },
      { label: "主动值", value: 76 },
      { label: "嘴硬度", value: 89 },
      { label: "安全感", value: 82 },
      { label: "暧昧感", value: 68 },
      { label: "稳定陪伴", value: 87 },
    ],
    emojis: [
      { label: "[捂脸]", value: 120, owner: "B 同学" },
      { label: "[旺柴]", value: 92, owner: "A 同学" },
      { label: "[让我看看]", value: 74, owner: "B 同学" },
      { label: "[叹气]", value: 66, owner: "A 同学" },
    ],
    timeline: [
      {
        id: "rt1",
        time: "09:18",
        title: "第一次默认报备",
        body: "A 同学把一句“我到了”发得很自然，自然到像已经说过很多次。",
      },
      {
        id: "rt2",
        time: "22:46",
        title: "嘴硬式关心",
        body: "B 同学说“你随便”，三分钟后补了一句“别太晚”。",
      },
      {
        id: "rt3",
        time: "00:12",
        title: "晚安后续费",
        body: "互道晚安以后又聊了 28 分钟，晚安只是下半场开始铃。",
      },
    ],
    relationship_edges: [
      { from: "A 同学", to: "B 同学", weight: 0.82, label: "主动开聊" },
      { from: "B 同学", to: "A 同学", weight: 0.74, label: "稳定接话" },
      { from: "A 同学", to: "B 同学", weight: 0.66, label: "深夜分享" },
    ],
    relationship_metrics: [
      { label: "CP 感", value: 72, caption: "有梗但不油，像一对互相熟悉的默认搭子" },
      { label: "主动开聊", value: 81, caption: "A 同学更常发起，B 同学更常把话题养活" },
      { label: "回复稳定", value: 86, caption: "不是每条都秒回，但关键时候基本不掉线" },
      { label: "嘴硬关心", value: 94, caption: "关心含量高，表达方式偏别扭" },
    ],
  },
  share: {
    slug: "demo-relationship",
    hook: "来测测你和 TA 到底是什么关系",
    watermark: "赛博判官关系报告",
  },
};

export const mockReport = mockGroupReport;

export function getMockReportById(id: string): ReportPayload {
  if (id.includes("relationship")) {
    return {
      ...mockRelationshipReport,
      report_id: id,
    };
  }

  return {
    ...mockGroupReport,
    report_id: id || mockGroupReport.report_id,
  };
}

function getMockReportBySlug(slug: string): ReportPayload {
  return slug.includes("relationship") ? mockRelationshipReport : mockGroupReport;
}

export function getMockShareSlugForReport(id: string) {
  return id.includes("relationship") ? "demo-relationship" : "demo-longwang";
}

export function createMockSharePayload(slug = "demo-longwang"): SharePayload {
  const report = getMockReportBySlug(slug);
  const url =
    typeof window === "undefined"
      ? `https://example.com/share/${slug}`
      : `${window.location.origin}/share/${slug}`;

  return {
    slug,
    url,
    report: {
      ...report,
      share: {
        ...report.share,
        slug,
      },
    },
  };
}
