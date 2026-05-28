"""
Rule-based Fallback Report Generator — Complete Edition.

Covers ALL section types when LLM is unavailable.
"""

from __future__ import annotations

from models import (
    ChatDNASummary,
    ContentHighlight,
    DialogueLine,
    EmojiStat,
    HeatmapCell,
    HeroBlock,
    KeywordStat,
    ParticipantStat,
    QuoteItem,
    RadarMetric,
    RelationshipEdge,
    RelationshipMetric,
    ReportPayload,
    ReportSection,
    ReportStats,
    ShareBlock,
    TimelineEvent,
    new_id,
    now_iso,
)

_GROUP_TEMPLATES = {
    "titles": ["赛博判官群聊锐评报告", "你们群的AI体检报告", "这个群的含金量，AI看懂了"],
    "taglines": ["这不是聊天记录，这是当代年轻人的精神体检报告。", "数据不会说谎，只会锐评。", "每个群都有自己的性格，你们这个比较抽象。"],
    "hero_kickers": ["群聊人格样本", "群聊精神状态检测", "群聊DNA分析"],
    "hero_quotes": ["你们群最可怕的不是话多，是每个人都像在给互联网留遗嘱。", "一群人把废话聊成连续剧，这是天赋。"],
    "hero_visuals": ["判", "群", "锐"],
}

_RELATIONSHIP_TEMPLATES = {
    "titles": ["你们俩的关系，AI看完沉默了三秒", "双人关系锐评报告", "两个人把默契聊成了默认设置"],
    "taglines": ["这不是普通聊天，这是两个人把熟悉感聊成默认设置的过程。", "有些关系不用定义，看聊天记录就知道了。"],
    "hero_kickers": ["双人关系样本", "默契度检测报告", "相处模式分析"],
    "hero_quotes": ["你们最暧昧的地方不是说了什么，是废话都能接得像暗号。", "有事先找你，没事也想烦你，这就是默认搭子。"],
    "hero_visuals": ["双", "默", "懂"],
}


def _pick(items: list[str], index: int) -> str:
    return items[index % len(items)]


def generate_group_fallback(
    stats: ReportStats,
    participants: list[ParticipantStat],
    top_senders: list[str],
    highlight_windows: list[dict] | None = None,
) -> ReportPayload:
    report_id = new_id()
    idx = len(participants) % 3

    roast_templates = [
        "群聊发动机，负责把冷场重新点火。", "表情包矿主，能用一张图终结一段对话。",
        "嘴上说睡了，手上还在刷新消息。", "低频高杀伤，出现一次群聊安静三秒。",
        "负责把话题从八卦偏到人生哲学。", "深夜值班选手，白天是传说晚上是主力。",
        "群聊气氛组，主要负责哈哈哈和转发。", "潜水大师，沉默但从不缺席。",
    ]
    for i, p in enumerate(participants):
        p.roast = _pick(roast_templates, i)

    quotes = _build_fallback_quotes(top_senders, "group_roast")

    # Build Chat DNA text
    dna = stats.chat_dna
    dna_text = "数据暂未生成完整基因报告。" if not dna else (
        f"在过去{dna.date_range_days}天里，你们共发送了{dna.total_messages}条消息，"
        f"活跃了{dna.active_days}天。群聊的黄金时段是{dna.top_hour}点，"
        f"深夜消息占比{dna.late_night_ratio}%。{dna.top_sender_name}是当之无愧的龙王。"
    )

    return ReportPayload(
        report_id=report_id, report_type="group_roast", created_at=now_iso(),
        title=_pick(_GROUP_TEMPLATES["titles"], idx),
        tagline=_pick(_GROUP_TEMPLATES["taglines"], idx),
        hero=HeroBlock(
            kicker=_pick(_GROUP_TEMPLATES["hero_kickers"], idx),
            quote=_pick(_GROUP_TEMPLATES["hero_quotes"], idx),
            visual=_pick(_GROUP_TEMPLATES["hero_visuals"], idx),
        ),
        tags=["深夜放毒群", "元宝语录矿区", "嘴硬互助会", "赛博龙王局"],
        sections=[
            ReportSection(id="summary", type="summary", heading="群体人设",
                          body="这是一个充满生命力的群聊。群友们用高频的消息、丰富的表情包和独特的暗号体系，构建了一个只有内部人士才能完全理解的话语宇宙。"),
            ReportSection(id="dragon", type="dragon_rank", heading="龙王榜",
                          body="真正的群聊发动机，从来不会承认自己在刷屏。", chart_ref="participants"),
            ReportSection(id="heatmap", type="heatmap", heading="发疯时段热力图",
                          body="从数据看，你们不是没有作息，只是作息长得比较抽象。", chart_ref="heatmap"),
            ReportSection(id="keywords", type="keywords", heading="高频梗词云",
                          body="这些词一出现，群里的空气就会开始变形。", chart_ref="keywords"),
            ReportSection(id="msg-types", type="message_types", heading="消息类型分布",
                          body="文字是基础操作，表情包才是灵魂。", chart_ref="message_type_breakdown"),
            ReportSection(id="specificity", type="word_specificity", heading="谁最爱说什么",
                          body="每个人都有专属口头禅，这是群聊的语言DNA。", chart_ref="word_specificity"),
            ReportSection(id="chronotype", type="chronotype", heading="群聊作息鉴定",
                          body="深夜战神、早起冠军、午后活跃——全群作息一览。", chart_ref="chronotypes"),
            ReportSection(id="sentiment", type="sentiment", heading="群聊情绪检测",
                          body="嘴上吐槽不断，心里其实热乎着呢。", chart_ref="sentiment_overview"),
            ReportSection(id="radar", type="radar", heading="群聊人格雷达",
                          body="本群综合画像：梗浓度拉满，嘴硬度与深夜活跃度正相关。", chart_ref="radar"),
            ReportSection(id="emoji", type="emoji", heading="表情包偏好",
                          body="表情包是本群第二官方语言，第一是阴阳怪气。", chart_ref="emojis"),
            ReportSection(id="monthly", type="monthly", heading="月度活跃趋势",
                          body="活跃度随季节和假期波动，年底是高潮。", chart_ref="monthly_activity"),
            ReportSection(id="initiative", type="initiative", heading="话题发动机排行",
                          body="有些人是群聊的永动机，永远第一个打破沉默。", chart_ref="initiative_scores"),
            ReportSection(id="links", type="links", heading="最爱分享的链接",
                          body="群聊信息流的主要来源，看看谁是资讯搬运工。", chart_ref="link_stats"),
            ReportSection(id="timeline", type="timeline", heading="神金时刻时间轴",
                          body="这些瞬间很难解释，但很适合截图保存。", chart_ref="timeline"),
            ReportSection(id="chat-dna", type="chat_dna", heading="群聊基因报告",
                          body=dna_text),
            ReportSection(id="badges", type="personality_badges", heading="群友荣誉勋章",
                          body="基于数据自动颁发的荣誉，请对号入座。", chart_ref="personality_badges"),
            ReportSection(id="predictions", type="predictions", heading="赛博占卜",
                          body="AI 掐指一算，群聊的未来走向是这样的——", chart_ref="predictions"),
        ],
        quotes=quotes,
        content_highlights=_build_fallback_highlights(highlight_windows, quotes, "group_roast"),
        stats=stats,
        share=ShareBlock(hook="来测测你在群里是几号龙王", watermark="赛博判官生成"),
    )


def generate_relationship_fallback(
    stats: ReportStats,
    participants: list[ParticipantStat],
    top_senders: list[str],
    highlight_windows: list[dict] | None = None,
) -> ReportPayload:
    report_id = new_id()
    idx = len(participants) % 2

    if len(participants) >= 2:
        participants[0].roast = "主动开聊担当，嘴上说随便问问，实际负责把关系续费。"
        participants[1].roast = "稳定接话担当，擅长用嫌弃包装认真陪聊。"

    quotes = _build_fallback_quotes(top_senders, "relationship")

    dna = stats.chat_dna
    dna_text = "数据暂未生成完整基因报告。" if not dna else (
        f"在过去{dna.date_range_days}天里，你们互发了{dna.total_messages}条消息，"
        f"活跃了{dna.active_days}天。{dna.late_night_ratio}%的消息发生在深夜，"
        f"你们的聊天已经形成了一种只有两个人懂的默契。"
    )

    return ReportPayload(
        report_id=report_id, report_type="relationship", created_at=now_iso(),
        title=_pick(_RELATIONSHIP_TEMPLATES["titles"], idx),
        tagline=_pick(_RELATIONSHIP_TEMPLATES["taglines"], idx),
        hero=HeroBlock(
            kicker=_pick(_RELATIONSHIP_TEMPLATES["hero_kickers"], idx),
            quote=_pick(_RELATIONSHIP_TEMPLATES["hero_quotes"], idx),
            visual=_pick(_RELATIONSHIP_TEMPLATES["hero_visuals"], idx),
        ),
        tags=["默认搭子", "嘴硬关心", "互相接梗", "晚安观察组"],
        sections=[
            ReportSection(id="relationship-summary", type="summary", heading="关系定性",
                          body="你们的关系不像普通朋友，更像一种「有事先找你，没事也想烦你」的稳定互相占用。聊天里没有太多直白的表达，但关心藏在吐槽和顺手回复里。"),
            ReportSection(id="relationship-map", type="relationship", heading="谁更主动",
                          body=f"{participants[0].name if participants else 'A'} 更常开启话题，另一个更擅长把话接住。", chart_ref="relationship_edges"),
            ReportSection(id="relationship-keywords", type="keywords", heading="你们的高频暗号",
                          body="这些词本身没什么，但在你们之间会自动翻译成「我懂你又开始了」。", chart_ref="keywords"),
            ReportSection(id="commonality", type="word_commonality", heading="共同语言",
                          body="两个人共享的高频词汇，是长期相处的语言证据。", chart_ref="word_commonality"),
            ReportSection(id="relationship-timeline", type="timeline", heading="关系升温时间轴",
                          body="真正的关系变化，往往藏在那些没人刻意定义的小瞬间里。", chart_ref="timeline"),
            ReportSection(id="relationship-radar", type="radar", heading="相处模式雷达",
                          body="你们不是特别肉麻，但默契和稳定输出已经高到很难装不熟。", chart_ref="radar"),
            ReportSection(id="sentiment", type="sentiment", heading="聊天情绪分析",
                          body="虽然嘴上吐槽不断，但关心和温暖才是底色。", chart_ref="sentiment_overview"),
            ReportSection(id="chat-dna", type="chat_dna", heading="关系基因报告",
                          body=dna_text),
            ReportSection(id="predictions", type="predictions", heading="关系预测",
                          body="AI 掐指一算，你们的关系走向是这样的——", chart_ref="predictions"),
        ],
        quotes=quotes,
        content_highlights=_build_fallback_highlights(highlight_windows, quotes, "relationship"),
        stats=stats,
        share=ShareBlock(hook="来测测你和 TA 到底是什么关系", watermark="赛博判官关系报告"),
    )


def _build_fallback_highlights(
    highlight_windows: list[dict] | None,
    quotes: list[QuoteItem],
    report_type: str,
) -> list[ContentHighlight]:
    highlights: list[ContentHighlight] = []
    titles = (
        ["群聊梗点", "接话节奏", "名场面候选"]
        if report_type == "group_roast"
        else ["默契证据", "接话节奏", "关系暗号"]
    )
    tags = (
        ["meme", "rhythm", "content"]
        if report_type == "group_roast"
        else ["relationship", "rhythm", "warmth"]
    )

    for index, window in enumerate((highlight_windows or [])[:3], start=1):
        evidence: list[DialogueLine] = []
        for line in window.get("evidence", [])[:4]:
            text = str(line.get("text") or line.get("content") or "").strip()
            if not text:
                continue
            evidence.append(DialogueLine(
                sender=str(line.get("sender", "")),
                text=text[:180],
                ts=line.get("ts") or None,
            ))
        if not evidence:
            continue
        title = titles[(index - 1) % len(titles)]
        insight = (
            "这段对话比单条金句更能说明群聊氛围：有人抛梗、有人接住，信息密度和情绪反应都比较集中。"
            if report_type == "group_roast"
            else "这段对话能看出两个人的互动模式：不是只看谁说得多，而是看谁会接话、补充和把情绪稳住。"
        )
        highlights.append(ContentHighlight(
            id=f"h{index}",
            title=title,
            insight=insight,
            tag=tags[(index - 1) % len(tags)],
            evidence=evidence,
        ))

    if highlights:
        return highlights

    for index, quote in enumerate(quotes[:3], start=1):
        highlights.append(ContentHighlight(
            id=f"h{index}",
            title="金句证据",
            insight="LLM 不可用时，系统会先把候选金句保留下来，作为后续内容点评和名场面回放的证据。",
            tag="content",
            evidence=[DialogueLine(sender=quote.speaker, text=quote.text)],
        ))
    return highlights


def _build_fallback_quotes(top_senders: list[str], report_type: str) -> list[QuoteItem]:
    if report_type == "group_roast":
        templates = [
            ("sparkles", "我只是随便说说，怎么就变成项目方向了？", "典型无意识带节奏型人才。"),
            ("moon", "我睡了，真的睡了，最后看一眼手机。", "这句话在统计学上意味着还有47条消息。"),
            ("coffee", "别吵，我正在严肃地摸鱼。", "本群劳动伦理代表人物。"),
            ("zap", "刚才那个谁说的，我觉得不太行。", "群聊里最危险的开场白之一。"),
            ("heart", "你们继续，我就看看不说话。", "说完这句通常再发20条。"),
        ]
    else:
        templates = [
            ("heart", "你别管，我就是顺手问一下。", "顺手问一下通常是本关系里最不顺手的关心。"),
            ("message", "你又开始了，但我先听完。", "嫌弃是假，继续听是真。"),
            ("sparkles", "算了，跟你说你肯定懂。", "默认你懂，已经是一种关系认证。"),
            ("coffee", "我就知道你会这么说。", "这种预判能力通常需要长期相处才能获得。"),
            ("moon", "晚安啦，早点睡。", "说完这句之后通常还有半小时的聊天。"),
        ]

    quotes: list[QuoteItem] = []
    for i, (icon, text, comment) in enumerate(templates[:5]):
        speaker = top_senders[i % len(top_senders)] if top_senders else f"{chr(65 + i)}同学"
        quotes.append(QuoteItem(id=f"q{i + 1}", speaker=speaker, text=text, comment=comment, icon=icon))
    return quotes
