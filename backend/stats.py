"""
Comprehensive Statistics Engine — all features from all 10 reference projects.

Integrated capabilities:
  WeFlow          → participant stats, message breakdown, annual view
  WechatExporter  → message type taxonomy
  WechatVisualization → word specificity/commonality, emoji specificity/commonality
  chat-analytics  → sentiment proxy, link analysis, interaction patterns
  echotrace       → message type radar, first/last dates
  relationship-candlestick-lab → relationship scoring dimensions
  welink          → Chat DNA, chronotype, social breadth, interaction matrix
  whatsapp-wrapped-v3 → chronotype, initiation scoring, personality badges
  AnnualReport    → monthly activity, date-range stats
"""

from __future__ import annotations

import re
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import jieba

from models import (
    ChatDNASummary, ChatMessage, ChronotypeInfo, EmojiStat, HeatmapCell,
    HourlyBin, InitiativeScore, InteractionMatrixItem, KeywordStat, LinkStat,
    MessageTypeBreakdown, MonthlyActivity, MonthlySentimentItem, NgramItem,
    ParticipantStat, PeakDayInfo, PersonalityBadge, Prediction, RadarMetric,
    RelationshipEdge, RelationshipMetric, ReportStats, SentimentOverview,
    StreakInfo, TimelineEvent, ToneType, WeekdayBin, WordCommonalityItem,
    WordSpecificityItem, YearlyMonthBin, AnnualSummary, FirstChatInfo,
    EmojiSpecificityItem,
)

# ── Stop Words ───────────────────────────────────────────────────

_STOP_WORDS: set[str] = {
    "的", "了", "在", "是", "我", "你", "他", "她", "它", "们",
    "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也",
    "很", "到", "说", "要", "去", "会", "着", "没", "看", "好",
    "这", "那", "什么", "怎么", "哪", "为什么", "谁", "吗", "吧",
    "呢", "啊", "哦", "嗯", "哈", "呀", "哇", "嘿", "哼", "喂",
    "还", "但", "与", "或", "及", "被", "把", "从", "以", "之",
    "而", "且", "所", "为", "其", "于", "对", "等", "该", "已",
    "所以", "因为", "如果", "虽然", "但是", "然后", "可以", "这个",
    "那个", "这样", "那样", "真的", "觉得", "知道", "应该", "可能",
    "已经", "现在", "今天", "明天", "昨天", "一下", "一点", "有点",
    "没", "太", "挺", "比较", "非常", "特别", "最", "更", "只",
    "又", "再", "才", "刚", "正", "在", "过", "啦", "喽", "嘛",
    "么", "嗒", "噗", "诶", "噶", "咯", "哎", "唉", "唔",
    "like", "just", "can", "dont", "dun", "lol", "??", "!!", "...",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    # WeChat system artifacts
    "引用", "回复", "撤回", "已撤回", "撤回了一条消息",
}

# Catches ALL bracket patterns: [xxx], [xxx yyy], etc.
_WECHAT_BRACKET_RE = re.compile(r"\[[^\]]+\]")
_REPLY_QUOTE_RE = re.compile(r"[\r\n]+\s*(?:↳\s*)?回复\b[\s\S]*$", re.S)
_INLINE_QUOTE_RE = re.compile(r"\[引用[^\]\r\n]*\][\s\S]*$", re.S)

# These bracket patterns are media indicators, not emoji stickers
_NON_EMOJI_BRACKETS = frozenset({
    "[表情包]", "[图片]", "[视频]", "[语音]", "[文件]", "[链接]",
    "[红包]", "[转账]", "[小程序]", "[视频号]", "[位置]", "[定位]",
    "[动画表情]", "[表情]", "[聊天记录]", "[名片]", "[消息]",
    "[转发的聊天记录]", "[音乐]",
})

_URL_RE = re.compile(r"https?://[^\s]+")
_DOMAIN_RE = re.compile(r"https?://([^/\s]+)")

# Sentiment word lists (proxy-based, no ML)
_POSITIVE_WORDS = {
    "哈哈", "哈哈哈", "笑", "开心", "好", "棒", "牛", "绝", "爱", "喜欢",
    "谢谢", "感谢", "厉害", "可以", "行", "对", "懂", "确实", "真的",
    "冲", "顶", "赞", "nice", "cool", "good", "great", "完美", "太棒了",
    "嘿嘿", "嘻嘻", "乐", "快乐", "幸福", "美好", "不错", "有意思",
    "好玩", "有趣", "惊喜", "感动", "温暖", "贴心",
}
_NEGATIVE_WORDS = {
    "烦", "气", "死", "晕", "吐", "裂开", "破防", "无语", "离谱", "救命",
    "难受", "痛苦", "累", "困", "饿", "穷", "惨", "哭", "崩溃", "绝望",
    "不行", "不好", "错了", "别", "不要", "操", "靠", "淦", "槽",
    "啊啊啊", "唉", "哎", "算了", "随便", "无所谓", "没意思",
}

# Badge definitions
_BADGE_DEFS: list[dict] = [
    {"id": "night_owl", "name": "深夜战神", "icon": "🦉", "description": "深夜活跃度远超常人，月亮不睡你不睡"},
    {"id": "early_bird", "name": "早起冠军", "icon": "🌅", "description": "大清早就开始水群，太阳都没你起得早"},
    {"id": "emoji_king", "name": "表情包之王", "icon": "👑", "description": "表情包使用量群内第一，一图胜千言"},
    {"id": "long_text_master", "name": "小作文大师", "icon": "📝", "description": "平均每条消息字数最多，说话最爱展开"},
    {"id": "speed_replier", "name": "秒回机器", "icon": "⚡", "description": "回复速度最快，仿佛手机长在手上"},
    {"id": "silence_breaker", "name": "冷场粉碎机", "icon": "🔨", "description": "最常在群聊沉默时第一个开口"},
    {"id": "topic_starter", "name": "话题发动机", "icon": "🚀", "description": "最常发起新话题，群聊永动机"},
    {"id": "goodnight_fraud", "name": "晚安诈骗犯", "icon": "🌙", "description": "说了晚安之后还在继续聊，晚安只是下半场开始铃"},
    {"id": "lurker", "name": "潜水专家", "icon": "🤿", "description": "发言最少但从不退群，默默关注一切"},
    {"id": "meme_master", "name": "梗王", "icon": "🎯", "description": "最常使用网络热梗和流行语"},
    {"id": "peacemaker", "name": "和平使者", "icon": "🕊️", "description": "最常在争论中打圆场或转移话题"},
    {"id": "red_packet_god", "name": "红包仙人", "icon": "🧧", "description": "发红包最多的人，散财童子"},
]


# ── Helper Functions ─────────────────────────────────────────────

# Only short bracket patterns with Chinese/ASCII (sticker names like [捂脸], [Facepalm])
_STICKER_NAME_RE = re.compile(r"\[[一-鿿_a-zA-Z]{2,12}\]")

_EMOJI_ENG_TO_CN: dict[str, str] = {
    "Smirk": "奸笑", "Awesome": "666", "MyBad": "打脸", "Drowsy": "困",
    "LetDown": "失望", "Whimper": "可怜", "OMG": "天啊", "Grimace": "撇嘴",
    "Facepalm": "捂脸", "Surprised": "惊讶", "Surprise": "惊讶", "Scowl": "发呆",
    "Poop": "便便", "Joyful": "可爱", "Bomb": "炸弹", "ThumbsUp": "赞",
    "Clap": "鼓掌", "Sun": "太阳", "Trick": "坏笑", "Fireworks": "烟花",
    "Shocked": "疑问", "Lips": "示爱", "Lip": "示爱", "Party": "庆祝",
    "Waddle": "跳跳", "BrokenHeart": "心碎", "NosePick": "抠鼻", "Sly": "阴险",
    "Peace": "胜利", "GoForIt": "加油", "Puke": "吐", "Sob": "流泪",
    "Hey": "嘿哈", "Flushed": "脸红", "Strong": "强壮", "Shrunken": "委屈",
    "Beer": "啤酒", "Moon": "月亮", "OK": "OK", "Tremble": "发抖",
    "Rose": "玫瑰", "Panic": "惊恐", "LetMeSee": "让我看看", "Smile": "微笑",
    "Worship": "合十", "Lol": "破涕为笑", "Tongue": "调皮", "Speechless": "擦汗",
    "Awkward": "尴尬", "Doge": "旺柴", "Drool": "色", "Duh": "无语",
    "Cry": "大哭", "Respect": "社会社会", "Toasted": "衰", "TearingUp": "快哭了",
    "Commando": "悠闲", "Concerned": "皱眉", "Boring": "翻白眼", "Shake": "握手",
    "Hungry": "饥饿", "Blush": "囧", "Laugh": "憨笑", "Hurt": "苦涩",
    "Broken": "裂开", "CoolGuy": "得意", "Smart": "机智", "Dizzy": "晕",
    "Onlooker": "吃瓜", "Blowkiss": "飞吻", "Shutup": "闭嘴", "Sweats": "汗",
    "Sigh": "叹气", "Sleep": "睡", "Twirl": "转圈", "NoProb": "好的",
    "Beckon": "勾引", "Grin": "呲牙", "Wow": "哇", "Scream": "抓狂",
    "Sick": "生病", "Hug": "拥抱", "Happy": "笑脸", "Angry": "发怒",
    "Fist": "拳头", "Chuckle": "偷笑", "Hammer": "敲打", "Frown": "难过",
    "Smug": "傲慢", "Salute": "抱拳", "Emm": "Emm", "Slight": "白眼",
    "Skull": "骷髅", "Terror": "恐惧", "Heart": "爱心", "ThumbsDown": "踩",
    "Kiss": "亲亲", "Shy": "害羞", "Wilt": "凋谢", "Pig": "猪头",
}

_EMOJI_CN_ALIASES: dict[str, str] = {
    "捂脸": "捂脸", "Facepalm": "捂脸", "打脸": "打脸", "MyBad": "打脸",
    "赞": "赞", "强": "赞", "ThumbsUp": "赞", "踩": "踩", "弱": "踩",
    "流泪": "流泪", "Sob": "流泪", "大哭": "大哭", "Cry": "大哭",
    "破涕为笑": "破涕为笑", "Lol": "破涕为笑", "可爱": "可爱", "Joyful": "可爱",
    "无语": "无语", "Duh": "无语", "白眼": "白眼", "Slight": "白眼",
    "抱拳": "抱拳", "Salute": "抱拳", "合十": "合十", "Worship": "合十",
}

def _normalize_emoji_label(label: str) -> str:
    """Canonicalize WeChat sticker labels so English/Chinese aliases merge.

    The mapping follows references/WechatVisualization/input_data/emoji.txt:
    for example [Facepalm] and [捂脸] are the same WeChat sticker and should
    be counted as one bucket.
    """
    if not label:
        return label
    inner = label[1:-1] if label.startswith("[") and label.endswith("]") else label
    canonical = _EMOJI_CN_ALIASES.get(inner) or _EMOJI_ENG_TO_CN.get(inner) or inner
    return f"[{canonical}]"

_GENERIC_EMOJI_CAPTIONS = {
    "", "表情", "表情包", "动画表情", "[表情]", "[表情包]", "[动画表情]",
}

def _emoji_label_from_meta(caption: object, url: object = "", md5: object = "") -> str:
    raw = str(caption or "").strip()
    if raw and raw not in _GENERIC_EMOJI_CAPTIONS and not raw.startswith("表情_"):
        return _normalize_emoji_label(raw)

    md5_text = str(md5 or "").strip()
    if md5_text:
        return f"[表情包:{md5_text[:12]}]"

    url_text = str(url or "").strip()
    if url_text:
        digest = hashlib.sha1(url_text.encode("utf-8")).hexdigest()[:12]
        return f"[表情包:{digest}]"

    return ""

def _strip_reply_quote(content: str) -> str:
    text = content or ""
    text = _REPLY_QUOTE_RE.sub("", text)
    text = _INLINE_QUOTE_RE.sub("", text)
    return text

def _extract_emojis(content: str) -> list[str]:
    raw = _STICKER_NAME_RE.findall(_strip_reply_quote(content))
    return [_normalize_emoji_label(r) for r in raw if r not in _NON_EMOJI_BRACKETS]

def _extract_message_emojis(msg: ChatMessage) -> list[tuple[str, str]]:
    if msg.type == "emoji":
        meta = msg.meta or {}
        url = str(meta.get("url", "") or "")
        label = _emoji_label_from_meta(meta.get("caption", ""), url, meta.get("md5", ""))
        return [(label, url)] if label else []
    return [(label, "") for label in _extract_emojis(msg.content)]


def _extract_urls(content: str) -> list[str]:
    return _URL_RE.findall(content)


def _tokenize(text: str) -> list[str]:
    # Strip ALL bracket patterns and quoted-reply markers
    clean = _WECHAT_BRACKET_RE.sub(" ", _strip_reply_quote(text))
    clean = re.sub(r"[「【].*?[」】]", " ", clean)
    words = jieba.lcut(clean)
    result: list[str] = []
    for w in words:
        w = w.strip()
        if len(w) < 2:
            continue
        if w in _STOP_WORDS:
            continue
        if w.isdigit():
            continue
        if re.match(r"^[^\w一-鿿]+$", w):
            continue
        result.append(w)
    return result


def _tone_classify(word: str, count: int, total: int) -> ToneType:
    hot_chars = {"哈", "啊", "笑", "死", "绝", "牛", "疯", "草", "顶", "爆", "杀", "冲"}
    sharp_chars = {"怼", "骂", "烦", "滚", "淦", "靠", "擦", "槽", "傻", "破", "裂", "离", "崩"}
    soft_chars = {"安", "晚安", "好", "乖", "贴", "暖", "心", "想", "念", "爱", "宝"}
    calm_chars = {"懂", "行", "可以", "嗯", "对", "是", "明白", "确认", "收到"}
    for ch in word:
        if ch in hot_chars: return "hot"
        if ch in sharp_chars: return "sharp"
        if ch in soft_chars: return "soft"
        if ch in calm_chars: return "calm"
    ratio = count / max(total, 1)
    if ratio > 0.05: return "hot"
    if ratio > 0.02: return "sharp"
    return "calm"


def _iso_parse(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


# ── Main Statistics Engine ───────────────────────────────────────

def compute_stats(messages: list[ChatMessage], report_type: str) -> ReportStats:
    total = len(messages)
    if total == 0:
        return _empty_stats()

    # Parse all timestamps
    parsed: list[tuple[ChatMessage, datetime | None]] = [
        (m, _iso_parse(m.ts)) for m in messages
    ]

    # ── Participant Stats ────────────────────────────────────────
    participants = _compute_participants(messages)
    top_names = [p.name for p in participants]

    # ── Heatmap ──────────────────────────────────────────────────
    heatmap = _compute_heatmap(parsed)

    # ── Keywords ─────────────────────────────────────────────────
    keywords = _compute_keywords(messages, total)

    # ── Radar ────────────────────────────────────────────────────
    radar = _compute_radar(messages, participants, parsed, report_type)

    # ── Emojis ───────────────────────────────────────────────────
    emojis = _compute_emojis(messages)

    # ── Timeline ─────────────────────────────────────────────────
    timeline = _compute_timeline(messages, participants, parsed)

    # ── Relationship Edges ───────────────────────────────────────
    edges = _compute_relationship_edges(messages, participants, parsed, report_type)

    # ── Relationship Metrics ─────────────────────────────────────
    rel_metrics = None
    if report_type == "relationship" and len(participants) >= 2:
        rel_metrics = _compute_relationship_metrics(messages, participants, parsed)

    # ── NEW: Word Specificity (WechatVisualization) ──────────────
    word_specificity = _compute_word_specificity(messages, participants)

    # ── NEW: Word Commonality (WechatVisualization) ──────────────
    word_commonality = _compute_word_commonality(messages, participants)

    # ── NEW: Message Type Breakdown (echotrace) ──────────────────
    msg_type_breakdown = _compute_message_type_breakdown(messages)

    # ── NEW: Chat DNA (welink, whatsapp-wrapped-v3) ──────────────
    chat_dna = _compute_chat_dna(messages, participants, parsed)

    # ── NEW: Chronotypes (whatsapp-wrapped-v3) ───────────────────
    chronotypes = _compute_chronotypes(messages, participants, parsed)

    # ── NEW: Sentiment Overview (chat-analytics) ─────────────────
    sentiment = _compute_sentiment(messages)

    # ── NEW: Monthly Activity (AnnualReport, WeFlow) ─────────────
    monthly = _compute_monthly_activity(parsed)

    # ── NEW: Initiative Scores (whatsapp-wrapped-v3) ─────────────
    initiative = _compute_initiative_scores(messages, participants, parsed)

    # ── NEW: Link Stats (chat-analytics) ─────────────────────────
    links = _compute_link_stats(messages)

    # ── NEW: Personality Badges (whatsapp-wrapped-v3) ────────────
    badges = _compute_personality_badges(messages, participants, parsed)

    # ── NEW: Predictions placeholder (filled by LLM) ─────────────
    predictions = _compute_predictions(messages, participants, report_type)

    # ── EXTRA stats from stats_extra ─────────────────────────────
    import stats_extra
    hourly_dist = [HourlyBin(**h) for h in stats_extra.compute_hourly_distribution(messages)]
    weekday_dist = [WeekdayBin(**w) for w in stats_extra.compute_weekday_distribution(messages)]
    yearly_mo = [YearlyMonthBin(**y) for y in stats_extra.compute_yearly_monthly(messages)]
    streak_data = stats_extra.compute_streak(messages)
    streak = StreakInfo(**streak_data)
    peak_data = stats_extra.compute_peak_day(messages)
    peak = PeakDayInfo(**peak_data)
    ngrams = [NgramItem(**ng) for ng in stats_extra.compute_ngrams(messages)]
    emoji_spec = [EmojiSpecificityItem(**es) for es in stats_extra.compute_emoji_specificity(messages, participants)]
    int_matrix = [InteractionMatrixItem(**im) for im in stats_extra.compute_interaction_matrix(messages, participants)]
    first_chat_data = stats_extra.compute_first_chat(messages)
    first_chat = FirstChatInfo(**first_chat_data)
    monthly_sent = [MonthlySentimentItem(**ms) for ms in stats_extra.compute_monthly_sentiment(messages)]
    annual_data = stats_extra.compute_annual_summary(messages, participants)
    annual = AnnualSummary(**annual_data) if annual_data else None

    # Extra v2 computations
    emoji_comm = stats_extra.compute_emoji_commonality(messages, participants)
    emoji_time = stats_extra.compute_emoji_time_distribution(messages)
    msg_type_evo = stats_extra.compute_message_type_evolution(messages)
    rp_overview = stats_extra.compute_red_packet_overview(messages)
    link_trends = stats_extra.compute_link_time_trends(messages)
    enhanced_dna = stats_extra.compute_enhanced_chat_dna(messages, participants)
    clock_fp = stats_extra.compute_clock_fingerprint(messages, participants)
    pc_sentiment = stats_extra.compute_per_contact_sentiment(messages, participants)
    extra_badges = stats_extra.compute_extra_badge_criteria(messages, participants)
    rel_milestones = stats_extra.compute_relationship_milestones(messages)
    recall_s = stats_extra.compute_recall_stats(messages)
    famous_q = stats_extra.compute_famous_quotes(messages)
    at_mentions = stats_extra.compute_at_mention_stats(messages)
    send_r = stats_extra.compute_send_ratio(participants)

    # Dual report extras (only for relationship type)
    dual_extras = None
    if report_type == "relationship" and len(participants) >= 2:
        dual_extras = stats_extra.compute_dual_report_extras(
            messages, participants[0].name, participants[1].name)

    return ReportStats(
        participants=participants,
        heatmap=heatmap,
        keywords=keywords,
        radar=radar,
        emojis=emojis,
        timeline=timeline,
        relationship_edges=edges,
        relationship_metrics=rel_metrics,
        word_specificity=word_specificity,
        word_commonality=word_commonality,
        message_type_breakdown=msg_type_breakdown,
        chat_dna=chat_dna,
        chronotypes=chronotypes,
        sentiment_overview=sentiment,
        monthly_activity=monthly,
        initiative_scores=initiative,
        link_stats=links,
        personality_badges=badges,
        predictions=predictions,
        # Extra stats
        hourly_distribution=hourly_dist,
        weekday_distribution=weekday_dist,
        yearly_monthly=yearly_mo,
        streak=streak,
        peak_day=peak,
        ngrams=ngrams,
        emoji_specificity=emoji_spec,
        interaction_matrix=int_matrix,
        first_chat=first_chat,
        monthly_sentiment=monthly_sent,
        annual_summary=annual,
        # Extra v2
        emoji_commonality=emoji_comm,
        emoji_time_distribution=emoji_time,
        message_type_evolution=msg_type_evo,
        red_packet_overview=rp_overview,
        link_time_trends=link_trends,
        enhanced_chat_dna=enhanced_dna,
        clock_fingerprints=clock_fp,
        per_contact_sentiment=pc_sentiment,
        extra_badge_criteria=extra_badges,
        relationship_milestones=rel_milestones,
        recall_stats=recall_s,
        famous_quotes=famous_q,
        dual_report_extras=dual_extras,
        at_mention_stats=at_mentions,
        send_ratio=send_r,
    )


def _empty_stats() -> ReportStats:
    return ReportStats(
        participants=[], heatmap=[], keywords=[], radar=[], emojis=[],
        timeline=[], relationship_edges=[],
    )


# ── Participant Stats ────────────────────────────────────────────

def _compute_participants(messages: list[ChatMessage]) -> list[ParticipantStat]:
    sender_stats: dict[str, dict] = defaultdict(
        lambda: {"msg_count": 0, "char_count": 0, "emoji_count": 0,
                  "image_count": 0, "link_count": 0, "red_packet_count": 0}
    )
    senders_order: list[str] = []

    for msg in messages:
        s = msg.sender
        if s not in sender_stats:
            senders_order.append(s)
        st = sender_stats[s]
        st["msg_count"] += 1
        st["char_count"] += len(msg.content)
        st["emoji_count"] += len(_extract_message_emojis(msg))
        if msg.type == "image":
            st["image_count"] += 1
        if msg.type == "link" or _URL_RE.search(msg.content):
            st["link_count"] += 1
        if msg.type in ("red_packet", "transfer"):
            st["red_packet_count"] += 1

    participants: list[ParticipantStat] = []
    for i, sender in enumerate(senders_order):
        st = sender_stats[sender]
        avg_len = st["char_count"] / max(st["msg_count"], 1)
        participants.append(ParticipantStat(
            id=f"u{i}", name=sender, avatar=sender[0] if sender else "?",
            message_count=st["msg_count"], character_count=st["char_count"],
            emoji_count=st["emoji_count"], image_count=st["image_count"],
            link_count=st["link_count"], red_packet_count=st["red_packet_count"],
            average_length=round(avg_len, 1), roast="",
        ))

    participants.sort(key=lambda p: p.message_count, reverse=True)
    return participants


# ── Heatmap ──────────────────────────────────────────────────────

def _compute_heatmap(parsed: list[tuple[ChatMessage, datetime | None]]) -> list[HeatmapCell]:
    bins = [[0.0 for _ in range(24)] for _ in range(7)]
    for _, dt in parsed:
        if dt is None:
            continue
        bins[dt.weekday()][dt.hour] += 1

    max_bin = max((v for row in bins for v in row), default=1)
    cells: list[HeatmapCell] = []
    for day in range(7):
        for hour in range(24):
            val = bins[day][hour] / max(max_bin, 1)
            cells.append(HeatmapCell(day=day, hour=hour, value=round(min(val, 1.0), 4)))
    return cells


# ── Keywords ─────────────────────────────────────────────────────

def _compute_keywords(messages: list[ChatMessage], total: int) -> list[KeywordStat]:
    word_counter: Counter[str] = Counter()
    for msg in messages:
        if msg.type == "system":
            continue
        word_counter.update(_tokenize(msg.content))

    keywords: list[KeywordStat] = []
    for word, count in word_counter.most_common(200):
        tone = _tone_classify(word, count, total)
        keywords.append(KeywordStat(word=word, count=count, tone=tone))

    by_tone: dict[ToneType, list[KeywordStat]] = {"hot": [], "soft": [], "sharp": [], "calm": []}
    for kw in keywords:
        if len(by_tone[kw.tone]) < 10:
            by_tone[kw.tone].append(kw)
    selected: list[KeywordStat] = []
    for tone in ("hot", "sharp", "soft", "calm"):
        selected.extend(by_tone[tone])
    for kw in keywords:
        if kw not in selected:
            selected.append(kw)
        if len(selected) >= 30:
            break
    return selected[:30]


# ── Radar ────────────────────────────────────────────────────────

def _compute_radar(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
    parsed: list[tuple[ChatMessage, datetime | None]],
    report_type: str,
) -> list[RadarMetric]:
    total = max(len(messages), 1)

    active_days: set[str] = set()
    night_msgs = 0
    emoji_total = sum(p.emoji_count for p in participants)
    reply_count = sum(1 for m in messages if m.reply_to)

    for _, dt in parsed:
        if dt is None:
            continue
        active_days.add(dt.strftime("%Y-%m-%d"))
        if dt.hour >= 22 or dt.hour <= 2:
            night_msgs += 1

    density = min(100, round(len(messages) / max(len(active_days), 1) * 2))
    night_ratio = min(100, round(night_msgs / total * 100))
    emoji_ratio = min(100, round(emoji_total / total * 100))
    reply_ratio = min(100, round(reply_count / total * 100))

    # Diversity
    if len(participants) > 1:
        counts = [p.message_count for p in participants]
        diversity = min(100, round((1 - (max(counts) - min(counts)) / max(max(counts), 1)) * 100))
    else:
        diversity = 50

    avg_len = sum(p.character_count for p in participants) / max(total, 1)
    length_score = min(100, round(avg_len / 3))

    if report_type == "group_roast":
        return [
            RadarMetric(label="话密度", value=density),
            RadarMetric(label="梗浓度", value=emoji_ratio),
            RadarMetric(label="深夜活跃", value=night_ratio),
            RadarMetric(label="嘴硬度", value=round(night_ratio * 0.9)),
            RadarMetric(label="互助值", value=reply_ratio),
            RadarMetric(label="活跃分布", value=diversity),
        ]
    else:
        return [
            RadarMetric(label="接话密度", value=round(reply_ratio * 1.2)),
            RadarMetric(label="主动值", value=density),
            RadarMetric(label="嘴硬度", value=round(night_ratio * 0.8)),
            RadarMetric(label="安全感", value=round(reply_ratio * 0.9)),
            RadarMetric(label="暧昧感", value=round(emoji_ratio * 1.1)),
            RadarMetric(label="稳定陪伴", value=round((100 - night_ratio * 0.3))),
        ]


# ── Emojis ───────────────────────────────────────────────────────

def _compute_emojis(messages: list[ChatMessage]) -> list[EmojiStat]:
    emoji_counter: Counter[str] = Counter()
    emoji_owners: dict[str, str] = {}
    emoji_urls: dict[str, str] = {}

    for msg in messages:
        if msg.type == "emoji":
            caption = (msg.meta or {}).get("caption", "") if msg.meta else ""
            url = str((msg.meta or {}).get("url", "") or "") if msg.meta else ""
            label = _emoji_label_from_meta(caption, url, (msg.meta or {}).get("md5", "") if msg.meta else "")
            if label:
                emoji_counter[label] += 1
                if label not in emoji_owners:
                    emoji_owners[label] = msg.sender
                if url and label not in emoji_urls:
                    emoji_urls[label] = url
            continue

        for em, _ in _extract_message_emojis(msg):
            emoji_counter[em] += 1
            if em not in emoji_owners:
                emoji_owners[em] = msg.sender

    result: list[EmojiStat] = []
    for em, count in emoji_counter.most_common(12):
        result.append(EmojiStat(label=em, value=count, owner=emoji_owners.get(em),
                                url=emoji_urls.get(em)))

    return result[:12]


# ── Timeline ─────────────────────────────────────────────────────

def _compute_timeline(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
    parsed: list[tuple[ChatMessage, datetime | None]],
) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    eid = 0

    # Sort by time
    sorted_items = sorted(
        [(m, d) for m, d in parsed if d is not None],
        key=lambda x: x[1],
    )
    if not sorted_items:
        return events

    # Burst detection: 5-min window with >= 8 messages
    i = 0
    bursts: list[tuple[str, int]] = []
    while i < len(sorted_items):
        start_dt = sorted_items[i][1]
        count = 0
        j = i
        while j < len(sorted_items):
            if (sorted_items[j][1] - start_dt).total_seconds() <= 300:
                count += 1
                j += 1
            else:
                break
        if count >= 8:
            bursts.append((start_dt.strftime("%H:%M"), count))
        i = j if j > i else i + 1

    bursts.sort(key=lambda b: b[1], reverse=True)
    for time_label, count in bursts[:3]:
        events.append(TimelineEvent(
            id=f"t{eid}", time=time_label,
            title="群聊爆发时刻" if count >= 15 else "活跃峰值",
            body=f"在 {time_label} 附近短时间内产生了 {count} 条消息。",
        ))
        eid += 1

    # Goodnight detection
    for p in participants[:3]:
        gn_msgs = [(m, d) for m, d in sorted_items
                    if m.sender == p.name and d is not None
                    and ("晚安" in m.content or "睡了" in m.content)]
        if gn_msgs:
            last_dt = gn_msgs[-1][1]
            events.append(TimelineEvent(
                id=f"t{eid}", time=last_dt.strftime("%H:%M"),
                title=f"{p.name} 的晚安仪式",
                body=f"共说了 {len(gn_msgs)} 次晚安，平均时间 {last_dt.strftime('%H:%M')} 左右。",
            ))
            eid += 1
            if eid >= 6:
                break

    # Longest message
    text_msgs = [(m, d) for m, d in sorted_items if m.type == "text" and len(m.content) > 50]
    if text_msgs:
        longest_msg, longest_dt = max(text_msgs, key=lambda x: len(x[0].content))
        events.append(TimelineEvent(
            id=f"t{eid}", time=longest_dt.strftime("%H:%M"),
            title="最长发言",
            body=f"{longest_msg.sender} 发了一条 {len(longest_msg.content)} 字的长消息。",
        ))
        eid += 1

    # First message
    first_msg, first_dt = sorted_items[0]
    events.append(TimelineEvent(
        id=f"t{eid}", time=first_dt.strftime("%H:%M"),
        title="记录起点",
        body=f"从 {first_dt.strftime('%m月%d日')} 开始，{first_msg.sender} 说出第一条记录。",
    ))
    eid += 1

    # Last message
    last_msg, last_dt = sorted_items[-1]
    events.append(TimelineEvent(
        id=f"t{eid}", time=last_dt.strftime("%H:%M"),
        title="最新记录",
        body=f"截至 {last_dt.strftime('%m月%d日')}，{last_msg.sender} 留下了最后一条消息。",
    ))

    return events[:7]


# ── Relationship Edges ───────────────────────────────────────────

def _compute_relationship_edges(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
    parsed: list[tuple[ChatMessage, datetime | None]],
    report_type: str,
) -> list[RelationshipEdge]:
    edges: list[RelationshipEdge] = []
    if len(participants) < 2:
        return edges

    sorted_items = sorted(
        [(m, d) for m, d in parsed if d is not None],
        key=lambda x: x[1],
    )

    reply_pairs: Counter[tuple[str, str]] = Counter()
    for i in range(1, len(sorted_items)):
        prev_msg, prev_dt = sorted_items[i - 1]
        cur_msg, cur_dt = sorted_items[i]
        if prev_msg.sender == cur_msg.sender:
            continue
        diff = (cur_dt - prev_dt).total_seconds()
        if diff < 120:
            reply_pairs[(cur_msg.sender, prev_msg.sender)] += 1

    if report_type == "relationship" and len(participants) >= 2:
        p1, p2 = participants[0].name, participants[1].name
        p1_to_p2 = reply_pairs.get((p1, p2), 0)
        p2_to_p1 = reply_pairs.get((p2, p1), 0)
        total_inter = max(p1_to_p2 + p2_to_p1, 1)
        edges = [
            RelationshipEdge(**{"from": p1, "to": p2, "weight": round(p1_to_p2 / total_inter, 2), "label": "主动开聊"}),
            RelationshipEdge(**{"from": p2, "to": p1, "weight": round(p2_to_p1 / total_inter, 2), "label": "稳定接话"}),
        ]
    else:
        for (sender_a, sender_b), count in reply_pairs.most_common(5):
            edges.append(RelationshipEdge(**{
                "from": sender_a, "to": sender_b,
                "weight": round(min(count / max(len(messages), 1) * 5, 1.0), 2),
                "label": "频繁互动" if count > 10 else "互动",
            }))

    return edges


# ── Relationship Metrics ─────────────────────────────────────────

def _compute_relationship_metrics(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
    parsed: list[tuple[ChatMessage, datetime | None]],
) -> list[RelationshipMetric]:
    if len(participants) < 2:
        return []

    p1, p2 = participants[0], participants[1]
    sorted_items = sorted(
        [(m, d) for m, d in parsed if d is not None],
        key=lambda x: x[1],
    )

    mutual_replies = 0
    for i in range(1, len(sorted_items)):
        if sorted_items[i][0].sender != sorted_items[i - 1][0].sender:
            diff = (sorted_items[i][1] - sorted_items[i - 1][1]).total_seconds()
            if diff < 60:
                mutual_replies += 1

    total = max(len(messages), 1)
    two_way_signal = min(100, round(mutual_replies / total * 500))
    initiative = min(100, round(p1.message_count / max(p1.message_count + p2.message_count, 1) * 100))
    reply_stability = min(100, round(mutual_replies / total * 300 + 40))

    tsundere_patterns = re.compile(r"(随便|不管|别管|不用|算了|没事|懒得|才不|又不是)")
    tsundere_count = sum(1 for m in messages if tsundere_patterns.search(m.content))
    care_expression = min(100, round(tsundere_count / total * 400 + 30))

    return [
        RelationshipMetric(label="双向互动", value=two_way_signal, caption="对话里有较多你来我往的接话记录"),
        RelationshipMetric(label="主动开聊", value=initiative, caption=f"{p1.name} 更常发起对话"),
        RelationshipMetric(label="回复稳定", value=reply_stability, caption="不是每条都秒回，但关键时刻不掉线"),
        RelationshipMetric(label="关心表达", value=care_expression, caption="聊天里出现过一些别扭但有照应感的表达"),
    ]


# ── NEW: Word Specificity (WechatVisualization) ──────────────────

def _compute_word_specificity(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
) -> list[WordSpecificityItem]:
    """Who says what: word uniqueness per person.
    specificity = (x-y)/(x+y) * max(x,y) for each pair for each word.
    Returns top items per person.
    """
    if len(participants) < 2:
        return []

    # Build per-person word counts
    person_words: dict[str, Counter[str]] = defaultdict(Counter)
    for msg in messages:
        if msg.type == "system":
            continue
        tokens = _tokenize(msg.content)
        person_words[msg.sender].update(tokens)

    items: list[WordSpecificityItem] = []
    top_senders = [p.name for p in participants[:5]]

    for sender in top_senders:
        if sender not in person_words:
            continue
        my_words = person_words[sender]
        # Get aggregate of all other senders
        other_words: Counter[str] = Counter()
        for s, wc in person_words.items():
            if s != sender:
                other_words.update(wc)

        for word, my_count in my_words.most_common(15):
            other_count = other_words.get(word, 0)
            total_both = my_count + other_count
            if total_both == 0:
                continue
            specificity = (my_count - other_count) / total_both * max(my_count, other_count)
            items.append(WordSpecificityItem(
                word=word, sender=sender, count=my_count,
                specificity=round(specificity, 3),
            ))

    # Sort by absolute specificity desc
    items.sort(key=lambda x: abs(x.specificity), reverse=True)
    return items[:15]


# ── NEW: Word Commonality (WechatVisualization) ──────────────────

def _compute_word_commonality(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
) -> list[WordCommonalityItem]:
    """Shared vocabulary: harmonic mean of two people's word frequencies."""
    if len(participants) < 2:
        return []

    top2 = [p.name for p in participants[:2]]
    if len(top2) < 2:
        return []

    wc1: Counter[str] = Counter()
    wc2: Counter[str] = Counter()
    for msg in messages:
        if msg.type == "system":
            continue
        tokens = _tokenize(msg.content)
        if msg.sender == top2[0]:
            wc1.update(tokens)
        elif msg.sender == top2[1]:
            wc2.update(tokens)

    items: list[WordCommonalityItem] = []
    all_words = set(wc1.keys()) & set(wc2.keys())
    for word in all_words:
        a, b = wc1[word], wc2[word]
        # Harmonic mean: 2/(1/a + 1/b)
        if a > 0 and b > 0:
            commonality = 2 / (1 / a + 1 / b)
            items.append(WordCommonalityItem(
                word=word, count_a=a, count_b=b,
                commonality=round(commonality, 2),
            ))

    items.sort(key=lambda x: x.commonality, reverse=True)
    return items[:15]


# ── NEW: Message Type Breakdown (echotrace) ──────────────────────

_TYPE_LABELS: dict[str, str] = {
    "text": "文字", "image": "图片/视频", "emoji": "表情",
    "file": "文件", "link": "链接", "system": "系统消息",
    "red_packet": "红包", "transfer": "转账", "unknown": "其他",
}

def _compute_message_type_breakdown(messages: list[ChatMessage]) -> list[MessageTypeBreakdown]:
    counter: Counter[str] = Counter()
    for m in messages:
        counter[m.type] += 1

    total = max(len(messages), 1)
    result: list[MessageTypeBreakdown] = []
    type_order = ["text", "image", "emoji", "link", "file", "red_packet", "transfer", "system", "unknown"]
    for t in type_order:
        if counter[t] > 0:
            result.append(MessageTypeBreakdown(
                type=t, label=_TYPE_LABELS.get(t, t),
                count=counter[t],
                percentage=round(counter[t] / total * 100, 1),
            ))
    return result


# ── NEW: Chat DNA (welink, whatsapp-wrapped-v3) ──────────────────

def _compute_chat_dna(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
    parsed: list[tuple[ChatMessage, datetime | None]],
) -> ChatDNASummary:
    valid = [(m, d) for m, d in parsed if d is not None]
    if not valid:
        return ChatDNASummary(
            total_messages=len(messages), total_words=0, active_days=0, active_months=0,
            date_range_days=0, first_date="", last_date="", top_hour=0, top_day=0,
            top_emoji="", top_word="", top_sender_name="", top_sender_count=0,
            avg_daily_messages=0, longest_gap_days=0, late_night_ratio=0,
        )

    sorted_valid = sorted(valid, key=lambda x: x[1])
    first_dt = sorted_valid[0][1]
    last_dt = sorted_valid[-1][1]
    date_range = (last_dt - first_dt).days + 1

    active_days_set: set[str] = set()
    hour_counter: Counter[int] = Counter()
    day_counter: Counter[int] = Counter()
    total_chars = 0

    for _, dt in valid:
        active_days_set.add(dt.strftime("%Y-%m-%d"))
        hour_counter[dt.hour] += 1
        day_counter[dt.weekday()] += 1
    for m in messages:
        total_chars += len(m.content)

    active_days = len(active_days_set)
    active_months_set: set[str] = set(d[:7] for d in active_days_set)

    # Top hour and day
    top_hour = hour_counter.most_common(1)[0][0] if hour_counter else 0
    top_day = day_counter.most_common(1)[0][0] if day_counter else 0

    # Top emoji (simple count)
    emoji_counter: Counter[str] = Counter()
    for m in messages:
        emoji_counter.update(em for em, _ in _extract_message_emojis(m))
    top_emoji = emoji_counter.most_common(1)[0][0] if emoji_counter else ""

    # Top word
    word_counter: Counter[str] = Counter()
    for m in messages:
        if m.type != "system":
            word_counter.update(_tokenize(m.content))
    top_word = word_counter.most_common(1)[0][0] if word_counter else ""

    # Top sender
    top_p = participants[0] if participants else None

    # Longest gap between consecutive messages
    longest_gap = 0
    for i in range(1, len(sorted_valid)):
        gap = (sorted_valid[i][1] - sorted_valid[i - 1][1]).total_seconds() / 3600
        if gap > longest_gap:
            longest_gap = int(gap)

    # Night ratio
    night_count = sum(1 for _, dt in valid if dt.hour >= 22 or dt.hour <= 5)
    late_night_ratio = round(night_count / max(len(valid), 1) * 100, 1)

    return ChatDNASummary(
        total_messages=len(messages),
        total_words=total_chars,
        active_days=active_days,
        active_months=len(active_months_set),
        date_range_days=date_range,
        first_date=first_dt.strftime("%Y-%m-%d"),
        last_date=last_dt.strftime("%Y-%m-%d"),
        top_hour=top_hour,
        top_day=top_day,
        top_emoji=top_emoji,
        top_word=top_word,
        top_sender_name=top_p.name if top_p else "",
        top_sender_count=top_p.message_count if top_p else 0,
        avg_daily_messages=round(len(messages) / max(active_days, 1), 1),
        longest_gap_days=longest_gap // 24 if longest_gap else 0,
        late_night_ratio=late_night_ratio,
    )


# ── NEW: Chronotypes (whatsapp-wrapped-v3) ───────────────────────

def _compute_chronotypes(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
    parsed: list[tuple[ChatMessage, datetime | None]],
) -> list[ChronotypeInfo]:
    result: list[ChronotypeInfo] = []
    for p in participants[:10]:
        p_times = [d for m, d in parsed if m.sender == p.name and d is not None]
        if not p_times:
            continue
        total = len(p_times)
        night = sum(1 for d in p_times if d.hour >= 22 or d.hour <= 5)
        morning = sum(1 for d in p_times if 5 <= d.hour <= 9)
        afternoon = sum(1 for d in p_times if 13 <= d.hour <= 17)

        night_r = night / total
        morning_r = morning / total

        # Peak hour
        hour_counts: Counter[int] = Counter(d.hour for d in p_times)
        peak = hour_counts.most_common(1)[0][0] if hour_counts else 12

        # Classify
        if night_r > 0.35:
            chronotype = "night_owl"
            label = "深夜战神"
        elif morning_r > 0.2:
            chronotype = "early_bird"
            label = "早起冠军"
        elif afternoon > total * 0.3:
            chronotype = "afternoon_peak"
            label = "午后活跃型"
        else:
            chronotype = "balanced"
            label = "全天均匀型"

        result.append(ChronotypeInfo(
            name=p.name, chronotype=chronotype, peak_hour=peak,
            night_ratio=round(night_r * 100, 1),
            morning_ratio=round(morning_r * 100, 1),
            label=label,
        ))
    return result


# ── NEW: Sentiment (chat-analytics) ──────────────────────────────

def _compute_sentiment(messages: list[ChatMessage]) -> SentimentOverview:
    pos = 0
    neg = 0
    total = 0
    for m in messages:
        if m.type == "system":
            continue
        text = m.content
        for word in _tokenize(text):
            total += 1
            if word in _POSITIVE_WORDS:
                pos += 1
            elif word in _NEGATIVE_WORDS:
                neg += 1

    if total == 0:
        pos_r = neg_r = neu_r = 33.3
        label = "数据不足，难以判断"
    else:
        pos_r = round(pos / total * 100, 1)
        neg_r = round(neg / total * 100, 1)
        neu_r = round(100 - pos_r - neg_r, 1)

        if neu_r > 85:
            label = "情绪平稳，波澜不惊"
        elif pos_r > neg_r * 2:
            label = "总体积极向上"
        elif neg_r > pos_r * 2:
            label = "嘴上不饶人但心里热乎"
        elif pos_r > 15 and neg_r < 10:
            label = "气氛活跃，正能量满满"
        elif neg_r > 15:
            label = "情绪起伏较大，但有话直说"
        else:
            label = "中性偏暖，偶有吐槽"

    return SentimentOverview(
        positive_ratio=pos_r, neutral_ratio=neu_r, negative_ratio=neg_r, label=label,
    )


# ── NEW: Monthly Activity (AnnualReport, WeFlow) ─────────────────

def _compute_monthly_activity(
    parsed: list[tuple[ChatMessage, datetime | None]],
) -> list[MonthlyActivity]:
    month_counter: Counter[str] = Counter()
    for _, dt in parsed:
        if dt is None:
            continue
        month_counter[dt.strftime("%Y-%m")] += 1

    result: list[MonthlyActivity] = []
    for month in sorted(month_counter.keys()):
        dt = datetime.strptime(month, "%Y-%m")
        result.append(MonthlyActivity(
            month=month, count=month_counter[month],
            label=f"{dt.month}月",
        ))
    return result


# ── NEW: Initiative Scores (whatsapp-wrapped-v3) ─────────────────

def _compute_initiative_scores(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
    parsed: list[tuple[ChatMessage, datetime | None]],
) -> list[InitiativeScore]:
    """Who starts conversations after a silence of >30 minutes."""
    sorted_items = sorted(
        [(m, d) for m, d in parsed if d is not None],
        key=lambda x: x[1],
    )
    if len(sorted_items) < 2:
        return []

    init_counter: Counter[str] = Counter()
    silence_threshold = 1800  # 30 minutes in seconds

    for i in range(1, len(sorted_items)):
        prev_msg, prev_dt = sorted_items[i - 1]
        cur_msg, cur_dt = sorted_items[i]
        gap = (cur_dt - prev_dt).total_seconds()
        if gap > silence_threshold:
            init_counter[cur_msg.sender] += 1

    total_inits = max(sum(init_counter.values()), 1)
    result: list[InitiativeScore] = []
    for p in participants:
        count = init_counter.get(p.name, 0)
        score = round(count / total_inits * 100, 1) if total_inits > 0 else 0
        label = "话题发动机" if score > 30 else ("稳定参与" if score > 10 else "随缘出现")
        result.append(InitiativeScore(name=p.name, score=score, initiations=count, label=label))

    result.sort(key=lambda x: x.score, reverse=True)
    return result


# ── NEW: Link Stats (chat-analytics) ─────────────────────────────

def _compute_link_stats(messages: list[ChatMessage]) -> list[LinkStat]:
    domain_counter: Counter[str] = Counter()
    domain_sharer: dict[str, str] = {}

    for m in messages:
        urls = _extract_urls(m.content)
        for url in urls:
            m2 = _DOMAIN_RE.search(url)
            if m2:
                domain = m2.group(1).lower()
                # Simplify: remove www.
                if domain.startswith("www."):
                    domain = domain[4:]
                domain_counter[domain] += 1
                if domain not in domain_sharer:
                    domain_sharer[domain] = m.sender

    result: list[LinkStat] = []
    for domain, count in domain_counter.most_common(8):
        result.append(LinkStat(domain=domain, count=count, top_sharer=domain_sharer.get(domain, "")))
    return result


# ── NEW: Personality Badges (whatsapp-wrapped-v3) ────────────────

def _compute_personality_badges(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
    parsed: list[tuple[ChatMessage, datetime | None]],
) -> list[PersonalityBadge]:
    badges: list[PersonalityBadge] = []
    if not participants:
        return badges

    top_p = participants[0]
    bottom_p = participants[-1] if len(participants) > 1 else None

    # Per-person metrics
    person_metrics: dict[str, dict] = defaultdict(lambda: {
        "emoji_count": 0, "avg_len": 0, "night_count": 0, "total": 0,
        "initiations": 0, "goodnight_fraud": 0, "red_packet": 0,
    })

    # Build reply times
    sorted_valid = sorted(
        [(m, d) for m, d in parsed if d is not None],
        key=lambda x: x[1],
    )
    reply_times: dict[str, list[float]] = defaultdict(list)

    for i in range(1, len(sorted_valid)):
        cur_msg, cur_dt = sorted_valid[i]
        prev_msg, prev_dt = sorted_valid[i - 1]
        if cur_msg.sender != prev_msg.sender:
            gap = (cur_dt - prev_dt).total_seconds()
            if gap < 300:
                reply_times[cur_msg.sender].append(gap)

    for p in participants:
        pm = person_metrics[p.name]
        for m in messages:
            if m.sender != p.name:
                continue
            pm["total"] += 1
            pm["emoji_count"] += len(_extract_message_emojis(m))
            pm["avg_len"] += len(m.content)
            if m.type in ("red_packet", "transfer"):
                pm["red_packet"] += 1
        if pm["total"] > 0:
            pm["avg_len"] /= pm["total"]

        # Night count
        for _, dt in [(m, d) for m, d in parsed if m.sender == p.name and d is not None]:
            if dt.hour >= 22 or dt.hour <= 5:
                pm["night_count"] += 1

        # Goodnight fraud detection
        gn_msgs = [m for m in messages if m.sender == p.name and ("晚安" in m.content or "睡了" in m.content)]
        if gn_msgs:
            gn_indices = [i for i, m in enumerate(messages) if m.msg_id == gn_msgs[-1].msg_id]
            if gn_indices:
                remaining = len(messages) - gn_indices[0] - 1
                if remaining > 3:
                    pm["goodnight_fraud"] = remaining

    # Award badges
    awarded: set[str] = set()

    # Night owl badge
    night_owl = max(person_metrics.items(), key=lambda x: x[1]["night_count"] / max(x[1]["total"], 1))
    if night_owl[1]["night_count"] / max(night_owl[1]["total"], 1) > 0.25:
        b = _BADGE_DEFS[0]
        badges.append(PersonalityBadge(id=b["id"], name=b["name"], icon=b["icon"],
                                        description=b["description"], awarded_to=night_owl[0]))
        awarded.add("night_owl")

    # Early bird badge
    morning_counts: dict[str, int] = defaultdict(int)
    for _, dt in [(m, d) for m, d in parsed if d is not None]:
        if 5 <= dt.hour <= 8:
            morning_counts[dt.strftime("%H-%M")] += 0  # placeholder
    for p in participants:
        for _, dt in [(m, d) for m, d in parsed if m.sender == p.name and d is not None]:
            if 5 <= dt.hour <= 8:
                morning_counts[p.name] += 1
    if morning_counts:
        early_bird = max(morning_counts.items(), key=lambda x: x[1])
        if early_bird[1] > 2:
            b = _BADGE_DEFS[1]
            badges.append(PersonalityBadge(id=b["id"], name=b["name"], icon=b["icon"],
                                            description=b["description"], awarded_to=early_bird[0]))
            awarded.add("early_bird")

    # Emoji king
    emoji_king = max(person_metrics.items(), key=lambda x: x[1]["emoji_count"])
    if emoji_king[1]["emoji_count"] > 5:
        b = _BADGE_DEFS[2]
        badges.append(PersonalityBadge(id=b["id"], name=b["name"], icon=b["icon"],
                                        description=b["description"], awarded_to=emoji_king[0]))
        awarded.add("emoji_king")

    # Long text master
    long_text = max(person_metrics.items(), key=lambda x: x[1]["avg_len"])
    if long_text[1]["avg_len"] > 15:
        b = _BADGE_DEFS[3]
        badges.append(PersonalityBadge(id=b["id"], name=b["name"], icon=b["icon"],
                                        description=b["description"], awarded_to=long_text[0]))
        awarded.add("long_text_master")

    # Speed replier
    avg_reply: dict[str, float] = {}
    for name, times in reply_times.items():
        if times:
            avg_reply[name] = sum(times) / len(times)
    if avg_reply:
        speedster = min(avg_reply.items(), key=lambda x: x[1])
        b = _BADGE_DEFS[4]
        badges.append(PersonalityBadge(id=b["id"], name=b["name"], icon=b["icon"],
                                        description=b["description"], awarded_to=speedster[0]))
        awarded.add("speed_replier")

    # Goodnight fraud
    gn_fraud = max(person_metrics.items(), key=lambda x: x[1]["goodnight_fraud"])
    if gn_fraud[1]["goodnight_fraud"] > 0:
        b = _BADGE_DEFS[7]
        badges.append(PersonalityBadge(id=b["id"], name=b["name"], icon=b["icon"],
                                        description=b["description"], awarded_to=gn_fraud[0]))
        awarded.add("goodnight_fraud")

    # Lurker badge for least active
    if bottom_p and bottom_p.message_count < top_p.message_count * 0.2:
        b = _BADGE_DEFS[8]
        badges.append(PersonalityBadge(id=b["id"], name=b["name"], icon=b["icon"],
                                        description=b["description"], awarded_to=bottom_p.name))
        awarded.add("lurker")

    # Red packet god
    rp_god = max(person_metrics.items(), key=lambda x: x[1]["red_packet"])
    if rp_god[1]["red_packet"] > 0:
        b = _BADGE_DEFS[11]
        badges.append(PersonalityBadge(id=b["id"], name=b["name"], icon=b["icon"],
                                        description=b["description"], awarded_to=rp_god[0]))
        awarded.add("red_packet_god")

    return badges


# ── NEW: Predictions (whatsapp-wrapped-v3) ───────────────────────

def _compute_predictions(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
    report_type: str,
) -> list[Prediction]:
    """Generate placeholder predictions — actual content filled by LLM."""
    if report_type == "group_roast":
        return [
            Prediction(id="p1", title="下个月龙王预测", body="根据当前活跃度趋势，龙王之位可能易主。", probability="中"),
            Prediction(id="p2", title="群聊主题演变", body="话题将从工作吐槽转向生活分享，美食类内容将显著增加。", probability="中"),
            Prediction(id="p3", title="新梗预警", body="下一个高频词将来自近期热点事件，预计在两周内爆发。", probability="中"),
        ]
    else:
        return [
            Prediction(id="p1", title="关系发展趋势", body="共同语言持续增加，预计下个月会有更多深夜长聊。", probability="中"),
            Prediction(id="p2", title="下一个里程碑", body="按照当前聊天频率，总消息数可能在30天内明显增长。", probability="中"),
        ]
