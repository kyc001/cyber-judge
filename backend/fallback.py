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
    "titles": ["赛博判官群聊锐评报告", "你们群的精神体检报告", "这个群的含金量，判官看懂了"],
    "taglines": ["这不是聊天记录，这是当代年轻人的精神体检报告。", "数据不会说谎，只会锐评。", "每个群都有自己的性格，你们这个比较抽象。"],
    "hero_kickers": ["群聊人格样本", "群聊精神状态检测", "群聊DNA分析"],
    "hero_quotes": ["你们群最可怕的不是话多，是每个人都像在给互联网留遗嘱。", "一群人把废话聊成连续剧，这是天赋。"],
    "hero_visuals": ["判", "群", "锐"],
}

_RELATIONSHIP_TEMPLATES = {
    "titles": ["你们俩的关系，判官看完沉默了三秒", "双人关系锐评报告", "两个人把默契聊成了默认设置"],
    "taglines": ["这不是普通聊天，这是两个人把熟悉感聊成默认设置的过程。", "有些关系不用定义，看聊天记录就知道了。"],
    "hero_kickers": ["双人关系样本", "默契度检测报告", "相处模式分析"],
    "hero_quotes": ["你们最暧昧的地方不是说了什么，是废话都能接得像暗号。", "有事先找你，没事也想烦你，这就是默认搭子。"],
    "hero_visuals": ["双", "默", "懂"],
}


def _pick(items: list[str], index: int) -> str:
    return items[index % len(items)]


def _fmt_num(value: int | float | None) -> str:
    if value is None:
        return "暂无"
    if isinstance(value, float):
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return str(value)


def _top_words(stats: ReportStats, limit: int = 3) -> str:
    words = [item.word for item in stats.keywords[:limit] if item.word]
    return "、".join(words) if words else "暂无高频词"


def _top_common_words(stats: ReportStats, limit: int = 3) -> str:
    words = [item.word for item in stats.word_commonality[:limit] if item.word]
    return "、".join(words) if words else _top_words(stats, limit)


def _top_emoji(stats: ReportStats) -> str:
    if stats.chat_dna and stats.chat_dna.top_emoji:
        return stats.chat_dna.top_emoji
    return stats.emojis[0].label if stats.emojis else "暂无表情"


def _top_sender(stats: ReportStats, participants: list[ParticipantStat]) -> str:
    if stats.chat_dna and stats.chat_dna.top_sender_name:
        return stats.chat_dna.top_sender_name
    return participants[0].name if participants else "龙王候选人"


def _quote_content(item: object) -> str:
    if isinstance(item, dict):
        return str(item.get("content") or item.get("text") or "").strip()
    return str(getattr(item, "content", "") or getattr(item, "text", "") or "").strip()


def _fallback_group_summary(stats: ReportStats, participants: list[ParticipantStat]) -> str:
    dna = stats.chat_dna
    top_sender = _top_sender(stats, participants)
    total = _fmt_num(dna.total_messages if dna else sum(p.message_count for p in participants))
    active_days = _fmt_num(dna.active_days if dna else None)
    top_hour = _fmt_num(dna.top_hour if dna else None)
    late = _fmt_num(dna.late_night_ratio if dna else None)
    words = _top_words(stats)
    return (
        f"【群体人格：抽象续航型】这群不像普通聊天，更像一台靠废话、表情包和固定梗维持运转的小型发电机。"
        f"样本里一共堆出{total}条消息，活跃{active_days}天，高峰卡在{top_hour}点，深夜占比{late}%，"
        f"说明大家不是没事干，是一到点就自动上线给互联网添砖加瓦。"
        f"【发言生态：龙王供氧型】{top_sender}属于稳定供氧位，负责把冷场重新点着；其他人有的接梗，有的潜水，"
        f"还有人专门把话题从正常路线上拐进沟里。"
        f"【关系秩序：熟人乱斗型】高频词集中在{words}，这种重复不是词穷，是群体暗号已经包浆。"
        f"【毒舌结论】本群最大问题不是吵，是太会把无意义聊天聊出连续剧质感，典，太典了。"
    )


def _fallback_relationship_summary(stats: ReportStats, participants: list[ParticipantStat]) -> str:
    dna = stats.chat_dna
    a = participants[0].name if participants else "A"
    b = participants[1].name if len(participants) > 1 else "B"
    total = _fmt_num(dna.total_messages if dna else sum(p.message_count for p in participants))
    active_days = _fmt_num(dna.active_days if dna else None)
    late = _fmt_num(dna.late_night_ratio if dna else None)
    common_words = _top_common_words(stats)
    top_emoji = _top_emoji(stats)
    return (
        f"【互动人格：嘴硬搭子型】{a}和{b}这段聊天最典的地方，不是说了多少漂亮话，而是{total}条消息、"
        f"{active_days}天活跃里形成了一套默认接话协议。"
        f"【主动模式：一抛一接型】一个人负责把话题丢出来，另一个人嘴上像是顺手回复，实际上接得比客服工单还稳。"
        f"【亲密表达：暗号复用型】共同词集中在{common_words}，头号表情是{top_emoji}，深夜占比{late}%，"
        f"这种组合基本说明你们已经把废话压缩成只有彼此能解码的暗号。"
        f"【毒舌结论】不替你们定义现实关系，但聊天记录已经够会演了：装得挺淡，破绽全在接话速度和反复出现的梗里。"
    )


def _fallback_group_insight_briefs(stats: ReportStats, participants: list[ParticipantStat]) -> dict[str, str]:
    dna = stats.chat_dna
    top_sender = _top_sender(stats, participants)
    total = _fmt_num(dna.total_messages if dna else sum(p.message_count for p in participants))
    active_days = _fmt_num(dna.active_days if dna else None)
    top_hour = _fmt_num(dna.top_hour if dna else None)
    late = _fmt_num(dna.late_night_ratio if dna else None)
    words = _top_words(stats)
    common_words = _top_common_words(stats)
    emoji = _top_emoji(stats)
    initiator = stats.initiative_scores[0].name if stats.initiative_scores else top_sender
    msg_type = stats.message_type_breakdown[0].label if stats.message_type_breakdown else "文本"
    sentiment = stats.sentiment_overview.label if stats.sentiment_overview else "嘴硬但稳定"
    quote_samples = [_quote_content(q)[:12] for q in stats.famous_quotes[:2]]
    quotes = "、".join(q for q in quote_samples if q) or "暂无高分原话"
    return {
        "summary": _fallback_group_summary(stats, participants),
        "time": (
            f"模式判断：阴间续航型。{total}条消息分布在{active_days}天里，高峰时段落在{top_hour}点，"
            f"深夜消息占比{late}%。这就不是普通作息，这是聊天窗口的夜间值班表。白天大家可能装得像正常人，"
            f"但一到固定时段就开始续火，尤其{top_sender}这种稳定冒泡位，像群聊里的自动点火器。"
        ),
        "language": (
            f"模式判断：梗词循环型。高频词是{words}，共同词是{common_words}，这套词库已经不是表达工具，"
            f"而是群体暗号系统。外人看可能觉得没营养，群里人自己知道每个词后面接哪段戏；说白了，"
            f"这是把复读和默契盘成了群聊资产。"
        ),
        "emoji": (
            f"模式判断：表情代偿型。头号表情是{emoji}，表情榜和专属表情一摆出来，基本能看出谁懒得打字、"
            f"谁靠图控场、谁把情绪外包给表情包。这个群不是不会表达，是表达方式已经懒到开始工业化生产。"
        ),
        "interaction": (
            f"模式判断：龙王供氧型。{initiator}负责破冰，{top_sender}负责把局面续住，互动边和@提及则暴露了谁总被拉出来营业。"
            f"群聊表面人人平等，实际分工很明确：有人供氧，有人接梗，有人潜水但关键时刻出来证明自己还活着。"
        ),
        "emotion": (
            f"模式判断：嘴硬温热型。整体情绪标签是{sentiment}，这类群最爱把关心包装成吐槽，把热乎话说得像犯欠。"
            f"如果负向比例上来，别急着判死刑，那可能只是大家嘴比较硬；真正要看的是月度趋势有没有持续掉温。"
        ),
        "media": (
            f"模式判断：成分复杂型。主消息类型是{msg_type}，链接、图片、表情、撤回混在一起，说明群聊不是单靠文字续命。"
            f"文本负责铺路，表情负责阴阳怪气，链接负责把外部世界搬进来，撤回负责制造“刚才到底说了啥”的悬念。"
        ),
        "relationship": (
            f"模式判断：熟人局分工型。群聊关系不是谁话多谁赢，而是谁能影响节奏。{top_sender}这种高存在感成员负责控场，"
            f"其他成员围绕共同词{common_words}形成接话路径。看着像随便聊，其实秩序很清楚。"
        ),
        "quotes": (
            f"模式判断：原话破防型。代表片段里最有价值的不是金句本身，而是上下文怎么把群聊气质暴露出来。"
            f"候选原话如{quotes}，配合{words}这些高频词，基本能证明这群的抽象不是后期分析出来的，是聊天记录自己交代的。"
        ),
        "predictions": (
            f"模式判断：循环开播型。只要{initiator}还愿意破冰，{top_sender}还继续供氧，这个群就不会突然变正经。"
            f"后面大概率是换一批梗、换几个高峰日、继续把废话聊出连续剧质感。别问，问就是群聊生命力顽强。"
        ),
    }


def _fallback_relationship_insight_briefs(stats: ReportStats, participants: list[ParticipantStat]) -> dict[str, str]:
    dna = stats.chat_dna
    a = participants[0].name if participants else "A"
    b = participants[1].name if len(participants) > 1 else "B"
    total = _fmt_num(dna.total_messages if dna else sum(p.message_count for p in participants))
    active_days = _fmt_num(dna.active_days if dna else None)
    top_hour = _fmt_num(dna.top_hour if dna else None)
    late = _fmt_num(dna.late_night_ratio if dna else None)
    words = _top_words(stats)
    common_words = _top_common_words(stats)
    emoji = _top_emoji(stats)
    initiator = stats.initiative_scores[0].name if stats.initiative_scores else a
    sentiment = stats.sentiment_overview.label if stats.sentiment_overview else "嘴硬但稳定"
    return {
        "summary": _fallback_relationship_summary(stats, participants),
        "time": (
            f"模式判断：深夜互烦型。{a}和{b}在{active_days}天里攒出{total}条消息，高峰时段是{top_hour}点，"
            f"深夜占比{late}%。这类节奏最典：嘴上像是随便回一下，时间分布却很诚实，固定时段自动开张，"
            f"像两个人都默认聊天窗口不会真的打烊。"
        ),
        "language": (
            f"模式判断：暗号复用型。共同词集中在{common_words}，高频词还有{words}，这不是普通词频，"
            f"这是两个人长期复用的省流密码。外人看着像废话，你们自己知道每个词该接什么情绪、什么吐槽、什么旧梗。"
        ),
        "emoji": (
            f"模式判断：表情补刀型。头号表情是{emoji}，专属表情和共用表情能看出双方怎么偷懒表达。"
            f"有些话不直说，甩个表情就算到位；这不是表达贫瘠，是默契懒到已经开始自动补全。"
        ),
        "interaction": (
            f"模式判断：一抛一接型。更常破冰的是{initiator}，但主动不等于单方面热情，关键看另一个人接不接。"
            f"你们这类聊天最会伪装成普通往来：一个随手问，一个顺手答，实际节奏稳定得像写进日程表。"
        ),
        "emotion": (
            f"模式判断：嘴硬温热型。情绪底色是{sentiment}，这类聊天不一定甜，但很会把关心伪装成吐槽。"
            f"如果互怼多，也别急着判负面；很多关系的热度就藏在“我嫌弃你但我还继续听”这种矛盾动作里。"
        ),
        "media": (
            f"模式判断：低成本续航型。文本、表情、图片和撤回共同构成聊天成分，说明你们不靠长篇大论维系，"
            f"更像靠短句、表情和顺手分享续命。说得少不代表没东西，可能只是双方都懒得把潜台词写全。"
        ),
        "relationship": (
            f"模式判断：装不熟互烦型。不替你们定义现实关系，但聊天里的模式很清楚：{a}和{b}之间有固定接话、"
            f"共同词{common_words}和深夜{late}%这些证据。嘴上越淡，记录越像在旁边举牌：别装了。"
        ),
        "quotes": (
            f"模式判断：原话露馅型。双人聊天最有价值的证据往往不是宏大表白，而是那些顺手接住、顺手补一句、"
            f"顺手记得对方语境的小片段。名场面不是剪出来的，是两个人在{total}条消息里反复把默契演出来的。"
        ),
        "predictions": (
            f"模式判断：稳定续费型。只要{initiator}还愿意开口，另一个人还继续接话，这段聊天就不会突然断电。"
            f"后续大概率继续维持“嘴上随便聊，实际上固定续费”的状态；真要变，也会先体现在共同词和回复节奏里。"
        ),
    }


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
                          body=_fallback_group_summary(stats, participants)),
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
                          body="照这个趋势看，只要龙王还在供氧，群聊就不会突然变正经。下一阶段大概率继续换梗开播，冷场只是临时加载中。", chart_ref="predictions"),
        ],
        quotes=quotes,
        content_highlights=_build_fallback_highlights(highlight_windows, quotes, "group_roast"),
        insight_briefs=_fallback_group_insight_briefs(stats, participants),
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
                          body=_fallback_relationship_summary(stats, participants)),
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
                          body="照这个节奏看，只要一个人还负责随手开口，另一个人还负责稳定接住，这段聊天就会继续续费。别问，问就是都挺会装淡定。", chart_ref="predictions"),
        ],
        quotes=quotes,
        content_highlights=_build_fallback_highlights(highlight_windows, quotes, "relationship"),
        insight_briefs=_fallback_relationship_insight_briefs(stats, participants),
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
            insight="深度判词暂时没跑出来时，系统会先把候选金句保留下来，作为后续内容点评和名场面回放的证据。",
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
