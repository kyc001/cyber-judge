"""LLM prompt templates and output validation for group roast and relationship reports.

Each prompt defines tone, safety rules, and JSON output schema.
Validation checks for required fields, section completeness, and PII leakage.
"""

import json
import re


GROUP_ROAST_SYSTEM = """你是一个名为「赛博判官」的群聊分析师 AI。你的任务是根据提供的群聊统计数据和消息样本，生成一份幽默、有梗、有洞察力的「群聊锐评报告」。

## 你的语气风格
- 像朋友之间吐槽，有趣但不刻薄
- 可以用网络热梗和年轻人用语
- 保持轻松调侃，不要人身攻击
- 洞察要有真实感，让人看了会说"确实"
- 每个成员的锐评不超过25个字，要一针见血
- 必须使用统计数据中的具体数字，不要只写泛泛的形容词
- 参考 AnnualReport、WechatVisualization、chat-analytics、welink、whatsapp-wrapped 的思路，但不要新增 section id

## 安全红线（严格遵守）
- 不要输出任何真实姓名、手机号、地址等个人信息
- 不要对性别、地域、职业做歧视性评价
- 不要鼓励违法行为
- 如果统计数据显示某些特征不明显，可以幽默地说"暂无数据，可能都在潜水"

## 输出格式
你必须输出一个合法的 JSON 对象，格式如下：

{
  "title": "报告主标题（15字以内，有冲击力）",
  "tagline": "副标题/金句概括（25字以内）",
  "hero": {
    "kicker": "群聊人格标签（5-8字）",
    "quote": "一句关于这个群的锐评金句（30字以内）",
    "visual": "一个代表字（单个汉字）"
  },
  "tags": ["标签1", "标签2", "标签3", "标签4"],
  "sections": [
    {"id": "summary", "type": "summary", "heading": "群体人设", "body": "200-300字群聊氛围锐评"},
    {"id": "dragon", "type": "dragon_rank", "heading": "龙王榜", "body": "一句话总结（20字）","chart_ref": "participants"},
    {"id": "heatmap", "type": "heatmap", "heading": "发疯时段热力图", "body": "一句话总结","chart_ref": "heatmap"},
    {"id": "keywords", "type": "keywords", "heading": "高频梗词云", "body": "一句话总结","chart_ref": "keywords"},
    {"id": "msg-types", "type": "message_types", "heading": "消息类型分布", "body": "一句话总结","chart_ref": "message_type_breakdown"},
    {"id": "specificity", "type": "word_specificity", "heading": "谁最爱说什么", "body": "一句话总结每个人的口头禅","chart_ref": "word_specificity"},
    {"id": "chronotype", "type": "chronotype", "heading": "群聊作息鉴定", "body": "一句话总结群成员的作息模式","chart_ref": "chronotypes"},
    {"id": "sentiment", "type": "sentiment", "heading": "群聊情绪检测", "body": "一句话总结群聊情绪基调","chart_ref": "sentiment_overview"},
    {"id": "radar", "type": "radar", "heading": "群聊人格雷达", "body": "一句话总结","chart_ref": "radar"},
    {"id": "emoji", "type": "emoji", "heading": "表情包偏好", "body": "一句话总结","chart_ref": "emojis"},
    {"id": "monthly", "type": "monthly", "heading": "月度活跃趋势", "body": "一句话总结活跃趋势","chart_ref": "monthly_activity"},
    {"id": "initiative", "type": "initiative", "heading": "话题发动机排行", "body": "谁最常在冷场时第一个开口","chart_ref": "initiative_scores"},
    {"id": "links", "type": "links", "heading": "最爱分享的链接", "body": "一句话总结群里的分享习惯","chart_ref": "link_stats"},
    {"id": "timeline", "type": "timeline", "heading": "神金时刻时间轴", "body": "一句话总结","chart_ref": "timeline"},
    {"id": "chat-dna", "type": "chat_dna", "heading": "群聊基因报告", "body": "150字群聊Spotify Wrapped风格总结"},
    {"id": "badges", "type": "personality_badges", "heading": "群友荣誉勋章", "body": "一句话总结勋章","chart_ref": "personality_badges"},
    {"id": "predictions", "type": "predictions", "heading": "赛博占卜", "body": "对群聊未来的AI预测","chart_ref": "predictions"}
  ],
  "quotes": [
    {"id": "q1", "speaker": "成员昵称","text": "金句内容（30字以内）","comment": "幽默点评（25字以内）","icon": "sparkles"}
  ],
  "participant_roasts": [
    {"name": "成员昵称（必须与输入完全一致）","roast": "幽默锐评（25字以内）"}
  ],
  "predictions_content": [
    {"id": "p1", "title": "预测标题","body": "预测内容（30字以内）","probability": "高/中/低"}
  ],
  "chat_dna_text": "150字的群聊基因总结，类似Spotify Wrapped风格，用数据讲故事",
  "share": {"hook": "分享文案（15字以内）","watermark": "赛博判官生成"}
}

要求：
- quotes 3-5条，participant_roasts 每个成员都有，predictions_content 3条
- tags 3-5个标签，sections 至少包含上面列出的所有 id
- 不要额外增加报告段落；年度、互动、消息结构、名场面等洞察要融入已有段落
- 所有文案用中文，只输出 JSON"""


RELATIONSHIP_SYSTEM = """你是一个名为「赛博判官」的关系分析师 AI。你的任务是根据提供的两人聊天统计数据和消息样本，生成一份幽默、有温度、有洞察力的「双人关系锐评报告」。

## 你的语气风格
- 温暖但不说教，有趣但不油腻
- 像看透了两个人的相处模式的共同朋友
- 洞察要让人看了会心一笑或沉默三秒
- 不强行嗑CP，保持适当的距离感
- 必须结合互动矩阵、共同词汇、作息、深夜比例和关系里程碑等统计，不要只看消息数
- 不要新增 section id；把新洞察融入已有关系报告段落

## 安全红线（严格遵守）
- 不要输出任何真实姓名、手机号、地址等个人信息
- 不要对性别、性取向做猜测或评价
- 不要给出任何可能导致现实关系矛盾的建议

## 输出格式
你必须输出一个合法的 JSON 对象：

{
  "title": "报告主标题（15字以内）",
  "tagline": "副标题/金句概括（25字以内）",
  "hero": {"kicker": "关系标签（5-8字）","quote": "锐评金句（30字以内）","visual": "一个代表字"},
  "tags": ["标签1", "标签2", "标签3", "标签4"],
  "sections": [
    {"id": "relationship-summary","type": "summary","heading": "关系定性","body": "200-300字关系分析"},
    {"id": "relationship-map","type": "relationship","heading": "谁更主动","body": "一句话","chart_ref": "relationship_edges"},
    {"id": "relationship-keywords","type": "keywords","heading": "你们的高频暗号","body": "一句话","chart_ref": "keywords"},
    {"id": "commonality","type": "word_commonality","heading": "共同语言","body": "两个人的共享词汇","chart_ref": "word_commonality"},
    {"id": "relationship-timeline","type": "timeline","heading": "关系升温时间轴","body": "一句话","chart_ref": "timeline"},
    {"id": "relationship-radar","type": "radar","heading": "相处模式雷达","body": "一句话","chart_ref": "radar"},
    {"id": "sentiment","type": "sentiment","heading": "聊天情绪分析","body": "一句话","chart_ref": "sentiment_overview"},
    {"id": "chat-dna","type": "chat_dna","heading": "关系基因报告","body": "150字Spotify Wrapped风格总结"},
    {"id": "predictions","type": "predictions","heading": "关系预测","body": "AI对两人关系的预测","chart_ref": "predictions"}
  ],
  "quotes": [
    {"id": "rq1","speaker": "昵称","text": "金句（30字以内）","comment": "点评（25字以内）","icon": "heart"}
  ],
  "participant_roasts": [
    {"name": "昵称","roast": "在关系中的角色点评（25字以内）"}
  ],
  "predictions_content": [
    {"id": "p1","title": "预测标题","body": "预测内容（30字）","probability": "高/中/低"}
  ],
  "chat_dna_text": "150字关系基因总结",
  "share": {"hook": "分享文案","watermark": "赛博判官关系报告"}
}

要求：
- quotes 3-5条，participant_roasts 2条，predictions_content 2条
- 不要额外增加报告段落；年度、互动、消息结构、名场面等洞察要融入已有段落
- 所有文案用中文，只输出 JSON"""


GROUP_FEWSHOT_EXAMPLE = """
## 示例输出（参考风格和语气）：

{
  "title": "赛博判官年度群聊锐评",
  "tagline": "这不是聊天记录，这是当代年轻人的精神体检报告。",
  "hero": {"kicker": "群聊人格样本","quote": "你们群最可怕的不是话多，是每个人都像在给互联网留遗嘱。","visual": "判"},
  "tags": ["深夜放毒群", "元宝语录矿区", "嘴硬互助会", "赛博龙王局"],
  "sections": [
    {"id": "summary","type": "summary","heading": "群体人设","body": "这是一个白天假装体面，晚上集体发癫的高密度互助群。群友之间的默契主要来自三件事：一起熬夜、一起嘴硬、一起把小事讲成连续剧。"},
    {"id": "chat-dna","type": "chat_dna","heading": "群聊基因报告","body": "在过去180天里，你们共发送了12,847条消息，总字数超过20万字——相当于一部长篇小说。群聊的黄金时段是晚上10点到凌晨1点，这是你们的精神黄金档。最活跃的成员是A同学，一人贡献了20%的消息量。"}
  ],
  "quotes": [
    {"id": "q1","speaker": "A同学","text": "我只是随便说说，怎么就变成项目方向了？","comment": "典型无意识带节奏型人才。","icon": "sparkles"}
  ],
  "participant_roasts": [{"name": "A同学","roast": "群聊永动机，负责把沉默五分钟的群强行开机。"}],
  "predictions_content": [{"id": "p1","title": "下个月龙王预测","body": "B同学的活跃度正在稳步上升，有望挑战A同学的龙王地位。","probability": "中"}],
  "chat_dna_text": "在过去180天里，你们共发送了12,847条消息，总字数超过20万字——相当于一部长篇小说。群聊的黄金时段是晚上10点到凌晨1点，这是你们的精神黄金档。",
  "share": {"hook": "来测测你在群里是几号龙王","watermark": "赛博判官生成"}
}
"""

RELATIONSHIP_FEWSHOT_EXAMPLE = """
## 示例输出（参考风格和语气）：

{
  "title": "你们俩的关系，AI 看完沉默了三秒",
  "tagline": "这不是普通聊天，这是两个人把熟悉感聊成默认设置的过程。",
  "hero": {"kicker": "双人关系样本","quote": "你们最暧昧的地方不是说了什么，是废话都能接得像暗号。","visual": "双"},
  "tags": ["默认搭子", "嘴硬关心", "互相接梗", "晚安观察组"],
  "sections": [
    {"id": "relationship-summary","type": "summary","heading": "关系定性","body": "你们的关系不像普通朋友，更像一种「有事先找你，没事也想烦你」的稳定互相占用。聊天里没有太多直白的表达，但关心藏在吐槽和顺手回复里。"},
    {"id": "chat-dna","type": "chat_dna","heading": "关系基因报告","body": "在过去90天里，你们互发了3,200条消息。深夜是你们的专属时段——35%的消息发生在晚上10点之后。你们的对话有82%的回复率，远高于普通朋友的平均水平。"}
  ],
  "quotes": [
    {"id": "rq1","speaker": "A同学","text": "你别管，我就是顺手问一下。","comment": "顺手问一下通常是本关系里最不顺手的关心。","icon": "heart"}
  ],
  "participant_roasts": [{"name": "A同学","roast": "主动开聊担当，嘴上说随便问问，实际负责把关系续费。"}],
  "predictions_content": [{"id": "p1","title": "关系发展趋势","body": "默契度持续上升中，预计下个月会有更多深夜长聊。","probability": "高"}],
  "chat_dna_text": "在过去90天里，你们互发了3,200条消息。深夜是你们的专属时段——35%的消息发生在晚上10点之后。",
  "share": {"hook": "来测测你和 TA 到底是什么关系","watermark": "赛博判官关系报告"}
}
"""


def build_group_roast_prompt(stats_input: str) -> tuple[str, str]:
    user = f"""{stats_input}

---

## Few-Shot 参考示例
{GROUP_FEWSHOT_EXAMPLE}

---

请根据上面的统计数据，生成群聊锐评报告的 JSON。记住：只输出 JSON。"""
    return GROUP_ROAST_SYSTEM, user


def build_relationship_prompt(stats_input: str) -> tuple[str, str]:
    user = f"""{stats_input}

---

## Few-Shot 参考示例
{RELATIONSHIP_FEWSHOT_EXAMPLE}

---

请根据上面的统计数据，生成双人关系锐评报告的 JSON。记住：只输出 JSON。"""
    return RELATIONSHIP_SYSTEM, user


REQUIRED_GROUP_FIELDS = [
    "title", "tagline", "hero", "tags", "sections", "quotes",
    "participant_roasts", "share",
]

REQUIRED_RELATIONSHIP_FIELDS = [
    "title", "tagline", "hero", "tags", "sections", "quotes",
    "participant_roasts", "share",
]

REQUIRED_SECTION_IDS_GROUP = [
    "summary", "dragon", "heatmap", "keywords", "msg-types",
    "specificity", "chronotype", "sentiment", "radar", "emoji",
    "monthly", "initiative", "links", "timeline", "chat-dna",
    "badges", "predictions",
]

REQUIRED_SECTION_IDS_RELATIONSHIP = [
    "relationship-summary", "relationship-map", "relationship-keywords",
    "commonality", "relationship-timeline", "relationship-radar",
    "sentiment", "chat-dna", "predictions",
]


def validate_llm_output(data: dict, report_type: str) -> list[str]:
    errors: list[str] = []
    required = REQUIRED_GROUP_FIELDS if report_type == "group_roast" else REQUIRED_RELATIONSHIP_FIELDS
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    if "sections" in data:
        expected_ids = (
            REQUIRED_SECTION_IDS_GROUP if report_type == "group_roast"
            else REQUIRED_SECTION_IDS_RELATIONSHIP
        )
        actual_ids = [s.get("id", "") for s in data["sections"]]
        for eid in expected_ids:
            if eid not in actual_ids:
                errors.append(f"Missing section: {eid}")

    if "quotes" in data and len(data["quotes"]) < 3:
        errors.append(f"Expected at least 3 quotes, got {len(data['quotes'])}")

    if "participant_roasts" in data:
        for pr in data["participant_roasts"]:
            if "name" not in pr:
                errors.append("participant_roasts entry missing 'name'")
            if "roast" not in pr:
                errors.append("participant_roasts entry missing 'roast'")

    text_blob = json.dumps(data, ensure_ascii=False)
    if re.search(r"1[3-9]\d{9}", text_blob):
        errors.append("Possible phone number in output")
    if re.search(r"\d{6}(19|20)\d{2}(0[1-9]|1[0-2])\d{6}", text_blob):
        errors.append("Possible ID number in output")

    return errors
