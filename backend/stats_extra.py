"""
Supplementary Statistics v2 — ALL remaining computable features.

Covers:
  B1.6-7  send ratio, sent vs received
  B2.6-10 time distributions (hourly/weekday/yearly/streak/peak)
  B3.9   N-grams
  B4.3-5 emoji specificity, emoji commonality, emoji time distribution
  B5.3-5 type radar data, type evolution, red packet overview
  B6.4-5 interaction matrix, @mention stats
  B7.2-3 link time trends
  C8-17  enhanced chat DNA
  D4-5   clock fingerprint, group phase chart data
  E3-5   monthly sentiment, per-contact sentiment
  F9-12  more badge criteria
  H5-9   first chat, milestones, recall stats, famous quotes
  I7-12  dual report extras
  J1-12  annual summary
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Optional

from models import ChatMessage, ParticipantStat
from stats import _extract_message_emojis

_STICKER_RE = re.compile(r"\[[一-鿿_a-zA-Z]{2,12}\]")
URL_RE = re.compile(r"https?://[^\s]+")
DOMAIN_RE = re.compile(r"https?://([^/\s]+)")

_POS_WORDS = {"哈哈","哈哈哈","笑","开心","好","棒","牛","绝","爱","喜欢","谢谢","感谢","厉害","可以","行","对","懂","确实","真的","冲","顶","赞","nice","cool","good","great","完美","嘿嘿","嘻嘻","乐","快乐","幸福","美好","不错","有意思","好玩","有趣","惊喜","感动","温暖","贴心"}
_NEG_WORDS = {"烦","气","死","晕","吐","裂开","破防","无语","离谱","救命","难受","痛苦","累","困","饿","穷","惨","哭","崩溃","绝望","不行","不好","错了","别","不要","操","靠","淦","槽","啊啊啊","唉","哎","算了","随便","无所谓","没意思"}


# ── Helpers ──────────────────────────────────────────────────────

def _safe_parse(ts: str) -> datetime | None:
    try: return datetime.fromisoformat(ts)
    except: return None


def _parse_all(messages: list[ChatMessage]) -> list[tuple[ChatMessage, datetime]]:
    result = []
    for m in messages:
        dt = _safe_parse(m.ts)
        if dt: result.append((m, dt))
    return result

def _sorted_parsed(messages: list[ChatMessage]) -> list[tuple[ChatMessage, datetime]]:
    return sorted(_parse_all(messages), key=lambda x: x[1])


# ── B1.6-7: Send Ratio, Sent vs Received ─────────────────────────

def compute_send_ratio(participants: list[ParticipantStat]) -> list[dict]:
    """Each person's message percentage of total."""
    total = max(sum(p.message_count for p in participants), 1)
    return [
        {"name": p.name, "count": p.message_count,
         "pct": round(p.message_count / total * 100, 1),
         "avatar": p.avatar}
        for p in participants
    ]


# ── B2: Time Distributions ───────────────────────────────────────

def compute_hourly_distribution(messages: list[ChatMessage]) -> list[dict]:
    bins = [0] * 24
    for m, dt in _parse_all(messages):
        bins[dt.hour] += 1
    total = max(sum(bins), 1)
    return [{"hour": h, "count": bins[h], "pct": round(bins[h] / total * 100, 1)} for h in range(24)]


def compute_weekday_distribution(messages: list[ChatMessage]) -> list[dict]:
    day_names = ["周一","周二","周三","周四","周五","周六","周日"]
    bins = [0] * 7
    for _, dt in _parse_all(messages):
        bins[dt.weekday()] += 1
    total = max(sum(bins), 1)
    return [{"day": d, "label": day_names[d], "count": bins[d], "pct": round(bins[d] / total * 100, 1)} for d in range(7)]


def compute_yearly_monthly(messages: list[ChatMessage]) -> list[dict]:
    month_names = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
    bins = [0] * 12
    for _, dt in _parse_all(messages):
        bins[dt.month - 1] += 1
    total = max(sum(bins), 1)
    return [{"month": m+1, "label": month_names[m], "count": bins[m], "pct": round(bins[m] / total * 100, 1)} for m in range(12)]


def compute_streak(messages: list[ChatMessage]) -> dict:
    days = sorted(set(dt.strftime("%Y-%m-%d") for _, dt in _parse_all(messages)))
    if not days: return {"length": 0, "start": "", "end": ""}
    longest = cur = 1
    best_s = best_e = cur_s = days[0]
    for i in range(1, len(days)):
        d1, d2 = datetime.strptime(days[i-1], "%Y-%m-%d"), datetime.strptime(days[i], "%Y-%m-%d")
        if (d2 - d1).days == 1:
            cur += 1
        else:
            if cur > longest: longest = cur; best_s = cur_s; best_e = days[i-1]
            cur = 1; cur_s = days[i]
    if cur > longest: longest = cur; best_s = cur_s; best_e = days[-1]
    return {"length": longest, "start": best_s, "end": best_e}


def compute_peak_day(messages: list[ChatMessage]) -> dict:
    dc: Counter[str] = Counter()
    ds: dict[str, Counter[str]] = defaultdict(Counter)
    for m, dt in _parse_all(messages):
        day = dt.strftime("%Y-%m-%d")
        dc[day] += 1; ds[day][m.sender] += 1
    if not dc: return {"date": "", "count": 0, "top_sender": ""}
    peak, count = dc.most_common(1)[0]
    top = ds[peak].most_common(1)[0][0] if ds[peak] else ""
    return {"date": peak, "count": count, "top_sender": top}


def compute_avg_reply_time(messages: list[ChatMessage]) -> dict:
    """Average response time and fastest friend."""
    sorted_msgs = _sorted_parsed(messages)
    reply_times: dict[str, list[float]] = defaultdict(list)
    for i in range(1, len(sorted_msgs)):
        cur_m, cur_dt = sorted_msgs[i]
        prev_m, prev_dt = sorted_msgs[i-1]
        if cur_m.sender != prev_m.sender:
            gap = (cur_dt - prev_dt).total_seconds()
            if gap < 3600:  # within 1 hour
                reply_times[cur_m.sender].append(gap)
    if not reply_times: return {"avg_seconds": 0, "fastest_friend": "", "fastest_seconds": 0}
    all_times = [t for times in reply_times.values() for t in times]
    avg_per_person = {name: sum(t)/len(t) for name, t in reply_times.items()}
    fastest = min(avg_per_person.items(), key=lambda x: x[1])
    return {"avg_seconds": round(sum(all_times) / len(all_times), 0),
            "fastest_friend": fastest[0], "fastest_seconds": round(fastest[1], 0)}


def compute_social_initiative(messages: list[ChatMessage], participants: list[ParticipantStat]) -> dict:
    """Initiated vs received ratio."""
    sorted_msgs = _sorted_parsed(messages)
    silence_threshold = 1800  # 30 min
    init_counter: Counter[str] = Counter()
    for i in range(1, len(sorted_msgs)):
        gap = (sorted_msgs[i][1] - sorted_msgs[i-1][1]).total_seconds()
        if gap > silence_threshold:
            init_counter[sorted_msgs[i][0].sender] += 1
    total_init = max(sum(init_counter.values()), 1)
    top_initiator = init_counter.most_common(1)[0] if init_counter else ("", 0)
    total_msgs = len(messages)
    return {
        "total_initiations": sum(init_counter.values()),
        "top_initiator": top_initiator[0],
        "top_initiator_count": top_initiator[1],
        "initiation_rate": round(sum(init_counter.values()) / max(total_msgs, 1) * 100, 1),
    }


def compute_lost_friend(messages: list[ChatMessage], participants: list[ParticipantStat]) -> dict:
    """Contact with significant early engagement that dropped off."""
    parsed = _sorted_parsed(messages)
    if not parsed: return {"name": "", "early_count": 0, "late_count": 0}
    mid = parsed[0][1] + (parsed[-1][1] - parsed[0][1]) / 2
    early: Counter[str] = Counter()
    late: Counter[str] = Counter()
    for m, dt in parsed:
        if dt < mid: early[m.sender] += 1
        else: late[m.sender] += 1
    candidates = []
    for p in participants:
        e = early.get(p.name, 0)
        l = late.get(p.name, 0)
        if e > 10 and l < e * 0.3:
            candidates.append((p.name, e, l, e - l))
    if not candidates: return {"name": "", "early_count": 0, "late_count": 0}
    best = max(candidates, key=lambda x: x[3])
    return {"name": best[0], "early_count": best[1], "late_count": best[2]}


# ── B3.9: N-Grams ────────────────────────────────────────────────

def compute_ngrams(messages: list[ChatMessage], min_len=2, max_len=5, top_n=40) -> list[dict]:
    ngram_counter: Counter[str] = Counter()
    for m in messages:
        if m.type == "system": continue
        text = _STICKER_RE.sub(" ", m.content)
        text = re.sub(r"https?://\S+", " ", text)
        text = re.sub(r"[^一-鿿\w]", " ", text)
        chars = text.replace(" ", "")
        for n in range(min_len, min(max_len+1, len(chars)+1)):
            for i in range(len(chars)-n+1):
                g = chars[i:i+n]
                if not any(c.isdigit() for c in g):
                    ngram_counter[g] += 1
    return [{"phrase": p, "count": c} for p, c in ngram_counter.most_common(top_n)]


# ── B4: Emoji Analysis ───────────────────────────────────────────

def compute_emoji_specificity(messages: list[ChatMessage], participants: list[ParticipantStat]) -> list[dict]:
    person_emojis: dict[str, Counter[str]] = defaultdict(Counter)
    emoji_urls: dict[str, str] = {}
    for m in messages:
        for em, url in _extract_message_emojis(m):
            person_emojis[m.sender][em] += 1
            if url and em not in emoji_urls:
                emoji_urls[em] = url
    result = []
    for sender in [p.name for p in participants[:5]]:
        if sender not in person_emojis: continue
        my = person_emojis[sender]
        other: Counter[str] = Counter()
        for s, ec in person_emojis.items():
            if s != sender: other.update(ec)
        for em, cnt in my.most_common(6):
            oc = other.get(em, 0)
            total = cnt + oc
            spec = (cnt - oc) / max(total, 1) * max(cnt, oc)
            item = {"emoji": em, "sender": sender, "count": cnt, "specificity": round(spec, 3)}
            if em in emoji_urls:
                item["url"] = emoji_urls[em]
            result.append(item)
    result.sort(key=lambda x: abs(x["specificity"]), reverse=True)
    return result[:20]


def compute_emoji_commonality(messages: list[ChatMessage], participants: list[ParticipantStat]) -> list[dict]:
    """Shared emoji usage between top 2 participants."""
    if len(participants) < 2: return []
    n1, n2 = participants[0].name, participants[1].name
    ec1: Counter[str] = Counter()
    ec2: Counter[str] = Counter()
    emoji_urls: dict[str, str] = {}
    for m in messages:
        for em, url in _extract_message_emojis(m):
            if url and em not in emoji_urls:
                emoji_urls[em] = url
            if m.sender == n1: ec1[em] += 1
            elif m.sender == n2: ec2[em] += 1
    shared = set(ec1.keys()) & set(ec2.keys())
    result = []
    for em in shared:
        a, b = ec1[em], ec2[em]
        if a > 0 and b > 0:
            item = {"emoji": em, "count_a": a, "count_b": b,
                    "commonality": round(2/(1/a + 1/b), 2)}
            if em in emoji_urls:
                item["url"] = emoji_urls[em]
            result.append(item)
    result.sort(key=lambda x: x["commonality"], reverse=True)
    return result[:15]


def compute_emoji_time_distribution(messages: list[ChatMessage]) -> list[dict]:
    """Emoji usage by hour of day."""
    bins = [0] * 24
    for m, dt in _parse_all(messages):
        cnt = len(_extract_message_emojis(m))
        if cnt > 0: bins[dt.hour] += cnt
    total = max(sum(bins), 1)
    return [{"hour": h, "count": bins[h], "pct": round(bins[h]/total*100, 1)} for h in range(24)]


# ── B5: Message Type Analysis ────────────────────────────────────

def compute_message_type_evolution(messages: list[ChatMessage]) -> list[dict]:
    """Message type counts per month."""
    monthly: dict[str, Counter[str]] = defaultdict(Counter)
    for m, dt in _parse_all(messages):
        monthly[dt.strftime("%Y-%m")][m.type] += 1
    result = []
    for month in sorted(monthly.keys()):
        mc = monthly[month]
        total = max(sum(mc.values()), 1)
        dt = datetime.strptime(month, "%Y-%m")
        entry = {"month": month, "label": f"{dt.month}月", "total": sum(mc.values())}
        for t in ["text", "image", "emoji", "link", "file", "red_packet", "system"]:
            entry[f"{t}_count"] = mc.get(t, 0)
            entry[f"{t}_pct"] = round(mc.get(t, 0) / total * 100, 1)
        result.append(entry)
    return result


def compute_red_packet_overview(messages: list[ChatMessage]) -> dict:
    """Red packet / transfer summary."""
    senders: Counter[str] = Counter()
    for m in messages:
        if m.type in ("red_packet", "transfer"):
            senders[m.sender] += 1
    if not senders: return {"total": 0, "top_sender": "", "participant_count": 0}
    top = senders.most_common(1)[0]
    return {"total": sum(senders.values()), "top_sender": top[0],
            "top_count": top[1], "participant_count": len(senders)}


# ── B6: Interaction Analysis ─────────────────────────────────────

def compute_interaction_matrix(messages: list[ChatMessage], participants: list[ParticipantStat]) -> list[dict]:
    names = [p.name for p in participants[:8]]
    if len(names) < 2: return []
    sorted_msgs = _sorted_parsed(messages)
    matrix: dict[tuple[str, str], int] = defaultdict(int)
    for i in range(1, len(sorted_msgs)):
        prev_m, prev_dt = sorted_msgs[i-1]
        cur_m, cur_dt = sorted_msgs[i]
        if prev_m.sender == cur_m.sender: continue
        if (cur_dt - prev_dt).total_seconds() < 120:
            matrix[(prev_m.sender, cur_m.sender)] += 1
    result = []
    for i, fn in enumerate(names):
        for j, tn in enumerate(names):
            if fn != tn:
                cnt = matrix.get((fn, tn), 0)
                if cnt > 0:
                    result.append({"from": fn, "to": tn, "count": cnt, "from_idx": i, "to_idx": j})
    return sorted(result, key=lambda x: x["count"], reverse=True)


def compute_at_mention_stats(messages: list[ChatMessage]) -> list[dict]:
    """Who gets @mentioned most."""
    at_re = re.compile(r"@([^\s]+)")
    mentioned: Counter[str] = Counter()
    mentioners: dict[str, Counter[str]] = defaultdict(Counter)
    for m in messages:
        for match in at_re.finditer(m.content):
            name = match.group(1)
            mentioned[name] += 1
            mentioners[name][m.sender] += 1
    result = []
    for name, count in mentioned.most_common(10):
        top_mentioner = mentioners[name].most_common(1)[0][0] if mentioners[name] else ""
        result.append({"name": name, "count": count, "top_mentioner": top_mentioner})
    return result


def compute_reply_chain_stats(messages: list[ChatMessage]) -> dict:
    """Most replied-to messages."""
    reply_count: Counter[str] = Counter()
    for m in messages:
        if m.reply_to:
            reply_count[m.reply_to] += 1
    if not reply_count: return {"most_replied_msg": "", "most_replied_count": 0}
    top = reply_count.most_common(1)[0]
    return {"most_replied_msg": top[0], "most_replied_count": top[1],
            "total_replies": sum(reply_count.values())}


# ── B7: Link Analysis ────────────────────────────────────────────

def compute_link_time_trends(messages: list[ChatMessage]) -> list[dict]:
    """Links shared per month."""
    monthly: Counter[str] = Counter()
    for m, dt in _parse_all(messages):
        if URL_RE.search(m.content):
            monthly[dt.strftime("%Y-%m")] += 1
    result = []
    for month in sorted(monthly.keys()):
        dt = datetime.strptime(month, "%Y-%m")
        result.append({"month": month, "label": f"{dt.month}月", "count": monthly[month]})
    return result


# ── C: Enhanced Chat DNA ─────────────────────────────────────────

def compute_enhanced_chat_dna(
    messages: list[ChatMessage],
    participants: list[ParticipantStat],
) -> dict:
    """All remaining Chat DNA fields: core friends, balanced friend, etc."""
    parsed = _sorted_parsed(messages)
    if not parsed: return {}

    # Night king (00:00-06:00)
    night: Counter[str] = Counter()
    for m, dt in parsed:
        if 0 <= dt.hour < 6: night[m.sender] += 1
    night_king = night.most_common(1)[0] if night else ("", 0)
    night_king_pct = round(night_king[1] / max(len(messages), 1) * 100, 1)

    # Balanced friend (most even send/receive ratio, both >= 50)
    # Proxy: who has closest to 50% of messages of top 2
    balanced_friend = ""
    balanced_score = 999
    if len(participants) >= 2:
        # For group mode, find the person with closest count to the median
        med = sorted([p.message_count for p in participants])[len(participants)//2]
        for p in participants:
            diff = abs(p.message_count - med)
            if diff < balanced_score:
                balanced_score = diff
                balanced_friend = p.name

    # Core friends (top 3)
    core_friends = [p.name for p in participants[:3]]

    # Monthly top friend
    month_friend: dict[str, Counter[str]] = defaultdict(Counter)
    for m, dt in parsed:
        month_friend[dt.strftime("%Y-%m")][m.sender] += 1
    monthly_best = []
    for mk in sorted(month_friend.keys()):
        best = month_friend[mk].most_common(1)[0]
        monthly_best.append({"month": mk, "friend": best[0], "count": best[1]})

    # Social initiative
    init = compute_social_initiative(messages, participants)

    # Avg reply time
    reply = compute_avg_reply_time(messages)

    # Lost friend
    lost = compute_lost_friend(messages, participants)

    # Total friends and total chars
    total_friends = len(set(m.sender for m in messages))
    total_chars = sum(len(m.content) for m in messages)

    return {
        "core_friends": core_friends,
        "night_king": night_king[0],
        "night_king_count": night_king[1],
        "night_king_pct": night_king_pct,
        "balanced_friend": balanced_friend,
        "monthly_best": monthly_best,
        "top_initiator": init["top_initiator"],
        "top_initiator_count": init["top_initiator_count"],
        "initiation_rate": init["initiation_rate"],
        "avg_reply_seconds": reply["avg_seconds"],
        "fastest_friend": reply["fastest_friend"],
        "fastest_seconds": reply["fastest_seconds"],
        "lost_friend": lost["name"],
        "lost_friend_early": lost["early_count"],
        "lost_friend_late": lost["late_count"],
        "total_friends": total_friends,
        "total_chars": total_chars,
    }


# ── D4-5: Clock Fingerprint ─────────────────────────────────────

def compute_clock_fingerprint(messages: list[ChatMessage], participants: list[ParticipantStat]) -> list[dict]:
    """Per-person 24h distribution as fingerprint."""
    result = []
    for p in participants[:10]:
        bins = [0] * 24
        for m, dt in _parse_all(messages):
            if m.sender == p.name: bins[dt.hour] += 1
        total = max(sum(bins), 1)
        result.append({
            "name": p.name,
            "distribution": [{"hour": h, "count": bins[h], "pct": round(bins[h]/total*100, 1)} for h in range(24)],
            "peak_hour": bins.index(max(bins)),
            "total_msgs": total,
        })
    return result


# ── E: Sentiment Analysis ────────────────────────────────────────

def compute_monthly_sentiment(messages: list[ChatMessage]) -> list[dict]:
    monthly: dict[str, dict] = defaultdict(lambda: {"pos": 0, "neg": 0})
    for m in messages:
        if m.type == "system": continue
        try: month = datetime.fromisoformat(m.ts).strftime("%Y-%m")
        except: continue
        for w in _POS_WORDS:
            if w in m.content: monthly[month]["pos"] += m.content.count(w)
        for w in _NEG_WORDS:
            if w in m.content: monthly[month]["neg"] += m.content.count(w)
    result = []
    for month in sorted(monthly.keys()):
        d = monthly[month]
        total = max(d["pos"] + d["neg"], 1)
        dt = datetime.strptime(month, "%Y-%m")
        result.append({
            "month": month, "label": f"{dt.month}月",
            "positive_ratio": round(d["pos"]/total*100, 1),
            "negative_ratio": round(d["neg"]/total*100, 1),
            "neutral_ratio": round(max(0, 100-(d["pos"]+d["neg"])/total*100), 1),
        })
    return result


def compute_per_contact_sentiment(messages: list[ChatMessage], participants: list[ParticipantStat]) -> list[dict]:
    result = []
    for p in participants[:8]:
        pos = neg = 0
        for m in messages:
            if m.sender != p.name or m.type == "system": continue
            for w in _POS_WORDS:
                if w in m.content: pos += m.content.count(w)
            for w in _NEG_WORDS:
                if w in m.content: neg += m.content.count(w)
        total = max(pos + neg, 1)
        label = "阳光开朗" if pos > neg*2 else ("嘴上不饶人" if neg > pos*2 else "中性")
        result.append({
            "name": p.name, "positive_count": pos, "negative_count": neg,
            "positive_ratio": round(pos/total*100, 1),
            "negative_ratio": round(neg/total*100, 1),
            "label": label,
        })
    return result


# ── F: More Badges ───────────────────────────────────────────────

def compute_extra_badge_criteria(messages: list[ChatMessage], participants: list[ParticipantStat]) -> list[dict]:
    """Additional badge criteria beyond the 8 in stats.py."""
    criteria = []
    parsed = _parse_all(messages)

    # Silence breaker: most initiations after >= 30 min silence
    init_counter: Counter[str] = Counter()
    sorted_msgs = _sorted_parsed(messages)
    for i in range(1, len(sorted_msgs)):
        gap = (sorted_msgs[i][1] - sorted_msgs[i-1][1]).total_seconds()
        if gap > 1800: init_counter[sorted_msgs[i][0].sender] += 1
    if init_counter:
        top = init_counter.most_common(1)[0]
        criteria.append({"badge_id": "silence_breaker", "awarded_to": top[0], "value": top[1]})

    # Topic starter: most messages after long gaps
    # Already covered by initiative, but add distinct label
    if init_counter:
        top2 = init_counter.most_common(2)
        if len(top2) > 1 and top2[1][1] > 0:
            criteria.append({"badge_id": "topic_starter", "awarded_to": top2[0][0], "value": top2[0][1]})

    # Meme master: most hot-tone keywords used
    # (Simplified proxy: most [表情]/[图片] usage)
    emoji_counts = {p.name: 0 for p in participants}
    for m in messages:
        if m.sender in emoji_counts:
            emoji_counts[m.sender] += len(_extract_message_emojis(m))
    if emoji_counts:
        meme_king = max(emoji_counts.items(), key=lambda x: x[1])
        criteria.append({"badge_id": "meme_master", "awarded_to": meme_king[0], "value": meme_king[1]})

    # Peacemaker: person who sends messages between two others arguing
    # (Simplified: person with most messages after someone uses negative words)
    peace_counter: Counter[str] = Counter()
    for i in range(1, len(messages)):
        prev_content = messages[i-1].content
        cur_sender = messages[i].sender
        if any(w in prev_content for w in _NEG_WORDS) and cur_sender != messages[i-1].sender:
            peace_counter[cur_sender] += 1
    if peace_counter:
        peacemaker = peace_counter.most_common(1)[0]
        criteria.append({"badge_id": "peacemaker", "awarded_to": peacemaker[0], "value": peacemaker[1]})

    return criteria


# ── H5-9: First Chat, Milestones, Recall Stats, Quotes ──────────

def compute_first_chat(messages: list[ChatMessage]) -> dict:
    non_sys = [(m, dt) for m, dt in _parse_all(messages) if m.type != "system"]
    if not non_sys:
        non_sys = [(m, _safe_parse(m.ts)) for m in messages if m.type != "system" and _safe_parse(m.ts)]
    if not non_sys: return {"first_date": "", "first_sender": "", "first_content": "", "first_10": []}
    non_sys.sort(key=lambda x: x[1])
    return {
        "first_date": non_sys[0][1].strftime("%Y-%m-%d %H:%M"),
        "first_sender": non_sys[0][0].sender,
        "first_content": non_sys[0][0].content[:120],
        "first_10": [{"sender": m.sender, "content": m.content[:80], "ts": dt.isoformat()}
                      for m, dt in non_sys[:10]],
    }


def compute_relationship_milestones(messages: list[ChatMessage]) -> list[dict]:
    """Key relationship moments: first chat, first long msg, first late night, longest gap, reconnect."""
    sorted_msgs = _sorted_parsed(messages)
    non_sys = [(m, dt) for m, dt in sorted_msgs if m.type != "system"]
    if not non_sys: return []

    milestones = []

    # First chat
    milestones.append({"type": "first_chat", "time": non_sys[0][1].strftime("%m-%d %H:%M"),
                        "title": "初次相遇", "body": f"{non_sys[0][0].sender} 说了第一句话"})

    # First long message (>100 chars)
    for m, dt in non_sys:
        if len(m.content) > 100:
            milestones.append({"type": "first_long", "time": dt.strftime("%m-%d %H:%M"),
                              "title": "首次长谈", "body": f"{m.sender} 发了一条{len(m.content)}字的长消息"})
            break

    # First late night chat (after 23:00)
    for m, dt in non_sys:
        if dt.hour >= 23 or dt.hour <= 2:
            milestones.append({"type": "first_late", "time": dt.strftime("%m-%d %H:%M"),
                              "title": "首次深夜聊天", "body": f"{m.sender} 在深夜{dt.hour}点发来消息"})
            break

    # Longest gap
    longest_gap = 0
    gap_start = gap_end = non_sys[0][1]
    for i in range(1, len(non_sys)):
        gap = (non_sys[i][1] - non_sys[i-1][1]).total_seconds() / 3600
        if gap > longest_gap:
            longest_gap = gap
            gap_start = non_sys[i-1][1]
            gap_end = non_sys[i][1]
    if longest_gap > 24:
        milestones.append({"type": "longest_gap", "time": gap_start.strftime("%m-%d"),
                           "title": "最长断联",
                           "body": f"从{gap_start.strftime('%m月%d日')}到{gap_end.strftime('%m月%d日')}，间断{int(longest_gap/24)}天"})

    # Reconnect after long gap
    if longest_gap > 72:  # 3+ days
        milestones.append({"type": "reconnect", "time": gap_end.strftime("%m-%d %H:%M"),
                          "title": "重新连线", "body": f"断联{int(longest_gap/24)}天后，对话重新开始"})

    # Most active week
    week_counter: Counter[str] = Counter()
    for m, dt in non_sys:
        iso = dt.isocalendar()
        week_counter[f"{iso[0]}-W{iso[1]}"] += 1
    if week_counter:
        best_week, best_count = week_counter.most_common(1)[0]
        milestones.append({"type": "peak_week", "time": best_week,
                          "title": "最活跃的一周", "body": f"这一周内产生了{best_count}条消息"})

    return milestones


def compute_recall_stats(messages: list[ChatMessage]) -> dict:
    """Message recall/retraction detection."""
    # WeChat exports typically mark recalled messages with specific patterns
    recall_patterns = [re.compile(r"(撤回了一条消息|recalled|已撤回)")]
    recalls: Counter[str] = Counter()
    for m in messages:
        for pat in recall_patterns:
            if pat.search(m.content):
                recalls[m.sender] += 1
                break
    if not recalls: return {"total_recalls": 0, "top_recaller": "", "top_count": 0}
    top = recalls.most_common(1)[0]
    return {"total_recalls": sum(recalls.values()), "top_recaller": top[0], "top_count": top[1]}


def compute_famous_quotes(messages: list[ChatMessage]) -> list[dict]:
    """Messages most likely to be memorable (by reply count or length/quirkiness)."""
    candidates = []
    for m in messages:
        if m.type != "text" or len(m.content) < 8 or len(m.content) > 120:
            continue
        score = 0
        # Longer = more quotable (but not too long)
        if 15 <= len(m.content) <= 60: score += 3
        # Contains humor indicators
        if any(w in m.content for w in ["哈哈", "笑", "救命", "离谱", "绝了", "破防"]):
            score += 2
        # Contains unique characters
        if re.search(r"[?!？！…~]", m.content): score += 1
        if score >= 3:
            candidates.append({"msg_id": m.msg_id, "sender": m.sender,
                               "content": m.content, "ts": m.ts, "score": score})
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:10]


# ── I7-12: Dual Report Extras ────────────────────────────────────

def compute_dual_report_extras(messages: list[ChatMessage], p1_name: str, p2_name: str) -> dict:
    """Extra dual report fields from WeFlow DualReport."""
    p1_msgs = [m for m in messages if m.sender == p1_name]
    p2_msgs = [m for m in messages if m.sender == p2_name]

    # My/TA exclusive emojis (>= 75% ratio)
    ec1: Counter[str] = Counter()
    ec2: Counter[str] = Counter()
    emoji_urls: dict[str, str] = {}
    for m in p1_msgs:
        for em, url in _extract_message_emojis(m):
            ec1[em] += 1
            if url and em not in emoji_urls:
                emoji_urls[em] = url
    for m in p2_msgs:
        for em, url in _extract_message_emojis(m):
            ec2[em] += 1
            if url and em not in emoji_urls:
                emoji_urls[em] = url

    p1_exclusive_emojis = []
    for em, cnt in ec1.most_common(5):
        c2 = ec2.get(em, 0)
        if cnt >= 3 and (cnt >= c2 * 3 or c2 == 0):
            item = {"emoji": em, "count": cnt}
            if em in emoji_urls:
                item["url"] = emoji_urls[em]
            p1_exclusive_emojis.append(item)

    p2_exclusive_emojis = []
    for em, cnt in ec2.most_common(5):
        c1 = ec1.get(em, 0)
        if cnt >= 3 and (cnt >= c1 * 3 or c1 == 0):
            item = {"emoji": em, "count": cnt}
            if em in emoji_urls:
                item["url"] = emoji_urls[em]
            p2_exclusive_emojis.append(item)

    # Monthly message counts
    monthly: dict[str, dict[str, int]] = defaultdict(lambda: {"p1": 0, "p2": 0})
    for m, dt in _parse_all(messages):
        if m.sender in (p1_name, p2_name):
            mk = dt.strftime("%Y-%m")
            if m.sender == p1_name: monthly[mk]["p1"] += 1
            else: monthly[mk]["p2"] += 1

    monthly_list = []
    for mk in sorted(monthly.keys()):
        d = monthly[mk]
        dt = datetime.strptime(mk, "%Y-%m")
        monthly_list.append({"month": mk, "label": f"{dt.month}月",
                             "p1_count": d["p1"], "p2_count": d["p2"]})

    # First year chat
    first_year = None
    for m in sorted(messages, key=lambda m: m.ts):
        if m.type != "system" and m.sender in (p1_name, p2_name):
            try:
                first_year = datetime.fromisoformat(m.ts).strftime("%Y-%m-%d %H:%M")
            except: pass
            break

    return {
        "p1_exclusive_emojis": p1_exclusive_emojis,
        "p2_exclusive_emojis": p2_exclusive_emojis,
        "p1_message_count": len(p1_msgs),
        "p2_message_count": len(p2_msgs),
        "p1_char_count": sum(len(m.content) for m in p1_msgs),
        "p2_char_count": sum(len(m.content) for m in p2_msgs),
        "monthly": monthly_list,
        "first_year_chat": first_year or "",
    }


# ── J: Annual Summary ────────────────────────────────────────────

def compute_annual_summary(messages: list[ChatMessage], participants: list[ParticipantStat]) -> dict:
    parsed = _sorted_parsed(messages)
    if not parsed: return {}
    first_dt, last_dt = parsed[0][1], parsed[-1][1]
    active_days = len(set(dt.strftime("%Y-%m-%d") for _, dt in parsed))
    total_friends = len(set(m.sender for m in messages))
    total_chars = sum(len(m.content) for m in messages)

    # Monthly best friend
    month_friend: dict[str, Counter[str]] = defaultdict(Counter)
    for m, dt in parsed:
        month_friend[dt.strftime("%Y-%m")][m.sender] += 1
    monthly_best = []
    for mk in sorted(month_friend.keys()):
        best = month_friend[mk].most_common(1)[0]
        monthly_best.append({"month": mk, "friend": best[0], "count": best[1]})

    # Night king
    night: Counter[str] = Counter()
    for m, dt in parsed:
        if 0 <= dt.hour < 6: night[m.sender] += 1
    night_king = night.most_common(1)[0] if night else ("", 0)

    return {
        "year": str(first_dt.year),
        "total_messages": len(messages),
        "total_friends": total_friends,
        "first_date": first_dt.strftime("%Y-%m-%d"),
        "last_date": last_dt.strftime("%Y-%m-%d"),
        "active_days": active_days,
        "top_friends": [p.name for p in participants[:3]],
        "night_king": night_king[0],
        "night_king_count": night_king[1],
        "monthly_best": monthly_best,
        "total_chars": total_chars,
    }


# ── O4-5: Excel/CSV Export Data ─────────────────────────────────

def build_export_data(report_data: dict) -> tuple[str, str]:
    """Generate CSV and plain text table from report stats.
    Returns (csv_content, txt_table_content)."""

    participants = report_data.get("stats", {}).get("participants", [])
    lines_csv = ["姓名,消息数,字数,表情数,平均长度,图片数,链接数,红包数"]
    for p in participants:
        lines_csv.append(f'{p["name"]},{p["message_count"]},{p["character_count"]},{p["emoji_count"]},{p["average_length"]},{p.get("image_count",0)},{p.get("link_count",0)},{p.get("red_packet_count",0)}')

    csv_content = "\n".join(lines_csv)

    # TXT table
    txt_lines = ["赛博判官 - 数据导出", "=" * 60, ""]
    txt_lines.append(f'{"姓名":<12}{"消息":>6}{"字数":>8}{"表情":>6}{"均长":>6}{"图片":>6}{"链接":>6}')
    txt_lines.append("-" * 56)
    for p in participants:
        txt_lines.append(f'{p["name"]:<12}{p["message_count"]:>6}{p["character_count"]:>8}{p["emoji_count"]:>6}{p["average_length"]:>6}{p.get("image_count",0):>6}{p.get("link_count",0):>6}')
    txt_lines.append("")
    txt_lines.append(f'报告ID: {report_data.get("report_id","")}')
    txt_lines.append(f'生成时间: {report_data.get("created_at","")}')

    return csv_content, "\n".join(txt_lines)
