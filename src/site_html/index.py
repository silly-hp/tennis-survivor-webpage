"""Homepage renderer."""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from site_html import state
from site_html.css import _CSS_BASE, _FONTS
from site_html.js import _JS_THEME
from site_html.logos import _logo_pair
from site_html.state import VERSION

_TOURS = ("ATP", "WTA")
_SWING_LABEL = {"hard": "Hard-Court Swing", "clay": "Clay-Court Swing", "grass": "Grass-Court Swing"}


def _fmt_name_chips(names: list[str], limit: int = 4) -> str:
    """One chip per player; always show the full list (no collapse)."""
    del limit  # kept for call-site compatibility; never truncate
    clean = [html.escape(str(n).strip()) for n in names if str(n).strip()]
    if not clean:
        return ""
    chips = "".join(f'<span class="wk-chip">{n}</span>' for n in clean)
    return f'<span class="wk-chips">{chips}</span>'


def _mmdd(ts) -> str:
    if ts is None:
        return ""
    try:
        return pd.Timestamp(ts).strftime("%m/%d")
    except Exception:
        return ""


def _card(week_data: Optional[dict], tour: str, kind: str):
    tours = (week_data or {}).get("tours") or {}
    card = (tours.get(tour) or {}).get(kind)
    if card is None or getattr(card, "empty_label", ""):
        return None
    return card


# ── weather ──────────────────────────────────────────────────────────────────
def _weather_by_tour(weather) -> dict[str, str]:
    """Map ATP/WTA → weather cards HTML (a shared venue maps to both)."""
    if not weather or isinstance(weather, str):
        cards = weather if isinstance(weather, str) and weather.strip() else ""
        return {t: cards for t in _TOURS} if cards else {}
    out: dict[str, str] = {}
    for label, cards in weather:
        if not cards or not str(cards).strip():
            continue
        for tour in _TOURS:
            if str(label or "").find(tour) >= 0:
                out[tour] = cards
    return out


def _weather_now(cards: str) -> str:
    """One-line summary of the first (current-hour) weather card."""
    def grab(cls: str) -> str:
        m = re.search(rf'class="{cls}"[^>]*>(.*?)</', cards or "", re.S)
        return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""

    parts = [grab("wx-icon"), grab("wx-temp"), grab("wx-cond")]
    rain = grab("wx-rain").replace("💧", "")
    line = " ".join(p for p in parts if p)
    if rain and rain != "0%":
        line += f" · 降雨 {rain}"
    return line


# ── 本周赛况 ──────────────────────────────────────────────────────────────────
def _event_card_html(tour: str, card, trend: Optional[dict], wx_cards: str) -> str:
    t = tour.lower()
    participants = getattr(card, "participants", None)
    survivors = getattr(card, "survivors", None)
    if trend:
        participants = participants or trend["total"]
        if survivors is None:
            survivors = trend["days"][-1]["alive"]
    rate = (
        f"{round(survivors / participants * 100)}%"
        if participants and survivors is not None
        else "—"
    )
    level = html.escape(str(getattr(card, "level", "") or ""))
    level_html = f'<span class="ev-level">{level}</span>' if level else ""
    date = _mmdd(getattr(card, "week_start", None))
    stat = lambda label, v: (  # noqa: E731
        f'<div class="ev-stat"><b>{"—" if v is None else v}</b><span>{label}</span></div>'
    )

    chart = ""
    if not trend:
        chart = """\
            <div class="ev-pending"><span class="ev-pending-icon" aria-hidden="true">⏱</span>选人尚未开始</div>"""
    elif len(trend["days"]) > 1:
        chart = f"""\
            <div class="trend" data-tour="{tour}">
                <div class="trend-hd"><span>幸存人数走势 · 共 {len(trend["days"]) - 1} 个比赛日</span>
                    <button type="button" class="chip-btn trend-replay" aria-label="重播动画">↻ 重播</button></div>
                <svg class="trend-svg" viewBox="0 0 480 200" role="img" aria-label="{tour} 每日幸存人数折线图"></svg>
                <div class="trend-days" role="group" aria-label="选择比赛日"></div>
                <div class="trend-tip" aria-live="polite"></div>
            </div>"""

    wx = ""
    if wx_cards:
        wx = f"""\
            <div class="ev-wx-row">
                <span class="ev-wx-now">{html.escape(_weather_now(wx_cards))}</span>
                <button type="button" class="chip-btn wx-toggle" aria-expanded="false" aria-controls="wx-{t}">逐小时天气 <span class="chev">▾</span></button>
            </div>
            <div class="wx-panel" id="wx-{t}" hidden>
                <div class="weather-scroll">
{wx_cards}
                </div>
            </div>"""

    stats = (
        f'<div class="ev-stats">{stat("参赛", participants)}{stat("幸存", survivors)}{stat("存活率", rate)}</div>'
        if trend or participants is not None
        else ""
    )
    return f"""\
        <article class="ev-card {t}{"" if trend else " pending"}">
            <div class="ev-head">
                <span class="ev-city">{html.escape(str(getattr(card, "city", "") or ""))}{level_html}</span>
                <span class="ev-eye">{tour}{f" · {date} 开赛" if date else ""}</span>
            </div>
            {stats}
{chart}
{wx}
        </article>"""


def _rest_card_html(tour: str, next_card, last_card) -> str:
    t = tour.lower()
    if next_card is not None and getattr(next_card, "city", ""):
        lvl = html.escape(str(getattr(next_card, "level", "") or ""))
        date = _mmdd(getattr(next_card, "week_start", None))
        body = (
            f'<span class="rest-title">下一站 · {html.escape(next_card.city)}'
            f'{f"（{lvl}）" if lvl else ""}</span>'
            f'<span class="rest-sub">{date} 开赛 · 已公布</span>'
        )
    else:
        body = (
            '<span class="rest-title">下一站赛程待公布</span>'
            '<span class="rest-sub">通常在开赛前几天公布，公布后这里会自动显示</span>'
        )
    page = getattr(last_card, "page", "") if last_card is not None else ""
    if page:
        body += (
            f'<a class="text-link" href="{html.escape(page)}">'
            f"回顾上一站 · {html.escape(last_card.city)} →</a>"
        )
    return f"""\
        <article class="rest-card {t}">
            <span class="ev-eye">{tour} · 本周休赛</span>
            {body}
        </article>"""


def _off_week_html(week_data: Optional[dict]) -> str:
    items = []
    for tour in _TOURS:
        nxt = _card(week_data, tour, "next")
        if nxt is not None and getattr(nxt, "city", ""):
            lvl = html.escape(str(getattr(nxt, "level", "") or ""))
            items.append(
                f'<div class="off-next {tour.lower()}"><span class="ev-eye">{tour} · 下一站</span>'
                f"<b>{html.escape(nxt.city)}{f' · {lvl}' if lvl else ''}</b>"
                f"<span>{_mmdd(nxt.week_start)} 开赛 · 已公布</span></div>"
            )
        else:
            items.append(
                f'<div class="off-next {tour.lower()}"><span class="ev-eye">{tour} · 下一站</span>'
                "<b>待公布</b><span>通常开赛前几天公布</span></div>"
            )
    return f"""\
    <section class="off-week">
        <div>
            <span class="off-eye">Off Week</span>
            <h2>本周没有比赛，养精蓄锐</h2>
            <p>回顾上周战况，或提前研究下一站的签表。</p>
        </div>
        <div class="off-grid">{"".join(items)}</div>
    </section>"""


def _this_week_html(week_data, trends, weather) -> str:
    wx = _weather_by_tour(weather)
    live = {t: _card(week_data, t, "this") for t in _TOURS}
    if not any(live.values()):
        return _off_week_html(week_data)
    trends = trends or {}
    # 一站已有选人记录、另一站尚未开始时：有数据的放前面占宽列，待开始的收窄
    started = [t for t in _TOURS if live[t] is not None and trends.get(t)]
    pending = [t for t in _TOURS if live[t] is not None and not trends.get(t)]
    lopsided = len(started) == 1 and len(pending) == 1
    order = started + [t for t in _TOURS if t not in started] if lopsided else list(_TOURS)
    cards = []
    for tour in order:
        if live[tour] is not None:
            cards.append(
                _event_card_html(tour, live[tour], trends.get(tour), wx.get(tour, ""))
            )
        else:
            cards.append(
                _rest_card_html(tour, _card(week_data, tour, "next"), _card(week_data, tour, "last"))
            )
    solo = " solo" if sum(c is not None for c in live.values()) == 1 else ""
    solo += " lopsided" if lopsided else ""
    return f"""\
    <section class="block">
        <h2 class="block-hd">本周赛况</h2>
        <div class="ev-grid{solo}">
{"".join(cards)}
        </div>
    </section>"""


# ── 今日选人 ──────────────────────────────────────────────────────────────────
def _picks_html(week_data, picks: Optional[dict]) -> str:
    rows = []
    for tour in _TOURS:
        p = (picks or {}).get(tour)
        card = _card(week_data, tour, "this")
        if not p or card is None:
            continue
        top_n = p["top"][0]["n"] if p["top"] else 1
        bars = "".join(
            f'<div class="pk-row"><span class="pk-name">{html.escape(x["name"])}</span>'
            f'<span class="pk-track"><span class="pk-bar" style="width:{round(x["n"] / top_n * 100)}%"></span></span>'
            f'<span class="pk-pct">{x["pct"]}%</span></div>'
            for x in p["top"]
        )
        rows.append(f"""\
            <a class="pk-card {tour.lower()}" href="{tour.lower()}_ranking.html">
                <div class="pk-hd"><span class="ev-eye">{tour} · {html.escape(card.city)}</span>
                    <span class="pk-meta">已选 <b>{p["picked"]}</b> · 轮空 <b>{p["bye"]}</b> · 共 {p["total"]}</span></div>
                {bars}
                <span class="text-link">查看完整选人明细 →</span>
            </a>""")
    if not rows:
        return ""
    return f"""\
    <section class="block">
        <h2 class="block-hd">今日选人 <span class="block-note">仅在比赛日显示</span></h2>
        <div class="pk-grid">
{"".join(rows)}
        </div>
    </section>"""


# ── 上周赛况 ──────────────────────────────────────────────────────────────────
def _last_item_html(card) -> str:
    tour = card.tour
    date = _mmdd(getattr(card, "week_start", None))
    champs = list(getattr(card, "champions", []) or [])
    top = int(getattr(card, "top_score", 0) or 0)
    top_names = list(getattr(card, "top_names", []) or [])
    if champs:
        result = '<span class="lw-res win">夺冠</span>'
        people = _fmt_name_chips(champs)
    elif getattr(card, "ongoing", False):
        result = '<span class="lw-res pending">赛事进行中</span>'
        people = ""
    else:
        result = f'<span class="lw-res">本站无人生还{f" · 最高分 {top}" if top else ""}</span>'
        people = _fmt_name_chips(top_names)
    page = getattr(card, "page", "")
    link = (
        f'<a class="text-link" href="{html.escape(page)}">查看本站战报 →</a>' if page else ""
    )
    return f"""\
            <div class="lw-item {tour.lower()}">
                <div class="lw-head"><span class="lw-tag">{tour}</span><b>{html.escape(card.city)}</b>
                    <span class="lw-date">{f"{date} 开赛" if date else ""}</span></div>
                {result}
                <div class="lw-people">{people}</div>
                {link}
            </div>"""


def _last_week_html(week_data) -> str:
    items = [_last_item_html(c) for t in _TOURS if (c := _card(week_data, t, "last")) is not None]
    if not items:
        return ""
    return f"""\
    <section class="block">
        <details class="lw">
            <summary class="block-hd lw-sum">点击查看上周战况 <span class="chev">▾</span></summary>
            <div class="lw-grid">
{"".join(items)}
            </div>
        </details>
    </section>"""


# ── 数据查询 ──────────────────────────────────────────────────────────────────
def _nav_cards(season) -> dict[str, list[dict[str, Any]]]:
    def tour_cards(t: str, race: str) -> list[dict[str, Any]]:
        return [
            {"eye": "Live Ranking", "title": "即时排名", "desc": "当前幸存者积分排名",
             "href": f"{t}_ranking.html"},
            {"eye": race, "title": "即时冠军排名", "desc": "年终总决赛资格积分榜",
             "href": f"{t}_race_ranking.html"},
            {"eye": "Hall of Fame", "title": "历史冠军榜", "desc": "历年冠军次数排行", "dev": True},
            {"eye": "Survivor Killer Stats", "title": "杀手榜", "desc": "带走幸存者最多的球员",
             "links": [(f"{season} 赛季", f"{season}{t}killer.html"), ("历年总榜", f"{t}killer.html")]},
            {"eye": "Tour Calendar", "title": "幸存者赛历", "desc": "按年份与级别浏览本站得分",
             "href": f"survivor_calendar_{t}.html"},
            {"eye": "Survivor Career", "title": "幸存者生涯统计", "desc": "生涯数据与对战记录",
             "links": [("生涯统计", f"{t}_show.html"), ("H2H 对战", f"h2h_{t}.html")]},
        ]

    return {
        "ATP": tour_cards("atp", "Race to Turin"),
        "WTA": tour_cards("wta", "Race to IW"),
        "ALL": [
            {"eye": "Combined Live", "title": "联合即时排名", "desc": "ATP + WTA 即时积分合计",
             "href": "combined_instant_ranking.html"},
            {"eye": "Combined Race", "title": "联合冠军排名", "desc": "ATP + WTA 冠军积分合计",
             "href": "combined_ranking.html"},
            {"eye": "Hall of Fame", "title": "历史冠军榜", "desc": "历年冠军次数排行，标注 ATP / WTA", "dev": True},
        ],
    }


def _nav_card_html(c: dict[str, Any]) -> str:
    eye = html.escape(c["eye"])
    title = html.escape(c["title"])
    desc = html.escape(c["desc"])
    if c.get("dev"):
        return (
            f'<div class="nav-card off" aria-disabled="true"><span class="nav-eye">{eye}</span>'
            f'<span class="nav-title">{title}<span class="dev-badge">开发中</span></span>'
            f'<span class="nav-desc">{desc}</span></div>'
        )
    if c.get("links"):  # several entry points: no whole-card link
        links = "".join(
            f'<a class="nav-link" href="{html.escape(href)}">{html.escape(label)} →</a>'
            for label, href in c["links"]
        )
        return (
            f'<div class="nav-card"><span class="nav-eye">{eye}</span>'
            f'<span class="nav-title">{title}</span><span class="nav-desc">{desc}</span>'
            f'<div class="nav-links">{links}</div></div>'
        )
    return (
        f'<div class="nav-card"><span class="nav-eye">{eye}</span>'
        f'<a class="nav-title nav-main" href="{html.escape(c["href"])}">{title}</a>'
        f'<span class="nav-desc">{desc}</span></div>'
    )


def _nav_html(season) -> str:
    groups = []
    for key, cards in _nav_cards(season).items():
        hidden = "" if key == "ATP" else " hidden"
        groups.append(
            f'<div class="nav-grid" data-group="{key}"{hidden}>'
            + "".join(_nav_card_html(c) for c in cards)
            + "</div>"
        )
    return f"""\
    <section class="block">
        <div class="nav-hd">
            <h2 class="block-hd">数据查询</h2>
            <div class="seg" role="tablist" aria-label="选择巡回赛">
                <button type="button" role="tab" data-tour="ATP" aria-selected="true">ATP</button>
                <button type="button" role="tab" data-tour="WTA" aria-selected="false">WTA</button>
                <button type="button" role="tab" data-tour="ALL" aria-selected="false">合计</button>
            </div>
        </div>
{"".join(groups)}
    </section>"""


_GUIDE = [
    ("本周赛况", "本周每站的参赛、幸存人数和存活率；走势图悬停或点选比赛日可看当日淘汰明细，「逐小时天气」展开赛地天气。"),
    ("今日选人", "比赛日显示各站选人最多的球员与已选 / 轮空人数，点进去看完整明细。"),
    ("即时排名", "实时积分、今日主选 / 备选与存活状态；合计 = ATP + WTA 积分之和。"),
    ("即时冠军排名", "Race 积分榜，看谁离年终总决赛资格最近。"),
    ("历史冠军榜", "历年冠军 / 亚军次数排行（开发中）。"),
    ("杀手榜", "哪些球员淘汰了最多幸存者，可看本赛季与历年总榜。"),
    ("幸存者赛历", "按年份、级别浏览每站赛事的本站得分与冠军。"),
    ("幸存者生涯统计", "个人生涯参赛、夺冠、连胜与存活率；H2H 查你与某位球员的胜负。"),
]


_CSS_INDEX = """\
.page{position:relative;z-index:1;max-width:1080px;margin:0 auto;padding:32px 24px 72px;}
header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:32px;}
.logo{display:flex;align-items:center;gap:12px;text-decoration:none;}
.logo-text{display:flex;flex-direction:column;gap:3px;}
.logo-cn{font-family:'Noto Serif SC',serif;font-size:19px;font-weight:700;color:var(--ink);letter-spacing:.06em;line-height:1;}
.logo-en{font-family:'Space Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:.22em;text-transform:uppercase;line-height:1;}
.hd-actions{display:flex;gap:8px;align-items:center;}
.pill-btn,.theme-btn{display:inline-flex;align-items:center;gap:6px;min-height:44px;padding:0 16px;
    border:1px solid var(--border);background:var(--surface);color:var(--ink2);border-radius:999px;
    font:inherit;font-size:13px;cursor:pointer;transition:border-color .2s,color .2s;}
.pill-btn:hover,.theme-btn:hover{border-color:var(--primary);color:var(--primary);}
.pill-btn.off,.pill-btn.off:hover{opacity:.55;cursor:not-allowed;border-color:var(--border);color:var(--ink2);}
.pill-btn.off .dev-badge{margin-left:2px;}
.pill-btn{text-decoration:none;}
.pill-n{font-family:'Space Mono',monospace;font-size:12px;font-weight:700;color:var(--ink);}
button:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}

.hero{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:36px;}
.hero-main{border-left:3px solid var(--primary);padding-left:20px;}
.hero-label{font-family:'Space Mono',monospace;font-size:11px;letter-spacing:.24em;text-transform:uppercase;color:var(--primary);margin-bottom:10px;}
.hero-title{font-family:'Noto Serif SC',serif;font-size:clamp(26px,4.5vw,38px);font-weight:700;line-height:1.2;}
.live-pill{display:inline-flex;align-items:center;gap:8px;font-size:12px;color:var(--ink2);padding:9px 14px;
    border:1px solid var(--border);border-radius:999px;background:var(--surface);}
.live-dot{width:8px;height:8px;border-radius:50%;background:var(--primary);animation:pulse 1.8s ease-out infinite;}
@keyframes pulse{0%{box-shadow:0 0 0 0 var(--primary-rim)}100%{box-shadow:0 0 0 9px transparent}}

.block{margin-bottom:36px;}
.block-hd{font-size:15px;font-weight:500;color:var(--muted);margin-bottom:12px;display:flex;align-items:center;gap:8px;}
.block-note{font-size:12px;color:var(--muted);margin-left:auto;font-weight:400;}
.ev-eye{font-family:'Space Mono',monospace;font-size:12px;letter-spacing:.06em;color:var(--muted);}
.atp .ev-eye{color:var(--secondary);} .wta .ev-eye{color:var(--primary);}
body:not(.dark) .atp .ev-eye{filter:brightness(.72);}
.text-link{font-size:13px;color:var(--primary-dark);text-decoration:none;}
.text-link:hover{text-decoration:underline;}
.chip-btn{display:inline-flex;align-items:center;gap:6px;font:inherit;font-size:12px;min-height:36px;padding:0 12px;
    border-radius:999px;border:1px solid var(--border);background:var(--surface);color:var(--ink2);cursor:pointer;}
.chip-btn:hover{border-color:var(--primary-rim);}
.chev{display:inline-block;transition:transform .2s;}
[aria-expanded="true"] .chev,details[open] > summary .chev{transform:rotate(180deg);}

/* this week */
.ev-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px;align-items:start;}
.ev-card,.rest-card{min-width:0;background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;
    display:flex;flex-direction:column;gap:14px;border-top:3px solid var(--primary);}
.ev-card.atp,.rest-card.atp{border-top-color:var(--secondary);}
.ev-head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap;}
.ev-city{font-family:'Noto Serif SC',serif;font-size:22px;font-weight:700;}
.ev-level{font-family:'Noto Sans SC',sans-serif;font-size:12px;font-weight:400;color:var(--muted);margin-left:8px;}
.ev-stats{display:flex;gap:28px;}
.ev-stat{display:flex;flex-direction:column-reverse;gap:2px;font-size:12px;color:var(--muted);}
.ev-stat b{font-family:'Space Mono',monospace;font-size:22px;color:var(--ink);line-height:1.1;}
.ev-wx-row{display:flex;justify-content:space-between;align-items:center;gap:10px;border-top:1px solid var(--border2);padding-top:12px;}
.ev-wx-now{font-size:13px;color:var(--ink2);}
.wx-panel{animation:fadeUp .22s ease-out both;}
.ev-grid.lopsided{grid-template-columns:minmax(0,1.9fr) minmax(0,1fr);align-items:stretch;}
.ev-card.pending .ev-pending{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;
    min-height:160px;background:var(--surface2);border-radius:10px;font-size:15px;font-weight:700;color:var(--ink2);}
.ev-pending-icon{font-size:22px;color:var(--muted);}
.ev-card.pending .ev-wx-row{margin-top:auto;}
.rest-card{border-style:dashed;border-top-style:solid;background:var(--surface2);gap:8px;justify-content:center;}
.rest-title{font-size:16px;font-weight:700;}
.rest-sub{font-size:13px;color:var(--muted);line-height:1.5;}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}

/* trend chart */
.trend{display:flex;flex-direction:column;gap:8px;border-top:1px solid var(--border2);padding-top:12px;}
.trend-hd{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--muted);}
.trend-svg{width:100%;height:auto;display:block;overflow:visible;touch-action:pan-y;}
.trend-svg .grid{stroke:var(--border);}
.trend-svg text{fill:var(--muted);font-size:11px;font-family:'Space Mono',monospace;}
.trend-svg .line{fill:none;stroke-width:3;stroke-linejoin:round;stroke-linecap:round;}
.trend-svg .area{fill-opacity:.12;stroke:none;}
.trend-svg .dot{fill:var(--surface);stroke-width:2.5;transition:r .15s;}
.trend-svg .cursor{stroke:var(--faint);stroke-dasharray:3 4;}
.atp .trend-svg .line,.atp .trend-svg .dot{stroke:var(--secondary);} .atp .trend-svg .area{fill:var(--secondary);}
.wta .trend-svg .line,.wta .trend-svg .dot{stroke:var(--primary);} .wta .trend-svg .area{fill:var(--primary);}
.trend-svg .draw{animation:draw 1.4s cubic-bezier(.4,0,.2,1) both;}
.trend-svg .pop{animation:fadeUp .3s ease-out both;}
@keyframes draw{from{stroke-dashoffset:var(--len)}to{stroke-dashoffset:0}}
.trend-days{display:flex;gap:6px;flex-wrap:wrap;}
.trend-days button{font:inherit;font-size:12px;min-height:32px;padding:0 10px;border-radius:999px;border:0;
    background:var(--surface2);color:var(--ink2);cursor:pointer;}
.trend-days button[aria-pressed="true"]{background:var(--ink);color:var(--bg);}
.trend-tip{background:var(--th-bg);color:#ddeef8;border-radius:10px;padding:12px 14px;font-size:12px;display:flex;flex-direction:column;gap:4px;}
.trend-tip:empty{display:none;}
.trend-tip .tt-hd{display:flex;justify-content:space-between;}
.trend-tip b{font-family:'Space Mono',monospace;font-size:15px;}
.trend-tip .tt-sub{color:#9cbdd4;}

/* weather cards (reused markup from weather.py) */
.weather-scroll{display:flex;gap:8px;overflow-x:auto;padding:2px 2px 8px;scroll-snap-type:x proximity;}
.wx{flex:0 0 auto;width:76px;background:var(--surface);border:1px solid var(--border);border-radius:10px;
    padding:10px 6px;text-align:center;scroll-snap-align:start;}
.wx.now{border-color:var(--primary);background:var(--primary-dim);}
.wx-day{font-family:'Space Mono',monospace;font-size:10px;color:var(--muted);min-height:12px;text-transform:uppercase;}
.wx-time{font-family:'Space Mono',monospace;font-size:11px;color:var(--muted);margin-bottom:5px;}
.wx-icon{font-size:20px;line-height:1;margin-bottom:5px;}
.wx-temp{font-family:'Space Mono',monospace;font-size:15px;font-weight:700;}
.wx-cond{font-size:11px;color:var(--muted);min-height:14px;margin-bottom:4px;}
.wx-row{font-size:10px;color:var(--muted);line-height:1.6;}
.wx-rain{color:var(--secondary);}

/* off week */
.off-week{background:var(--th-bg);color:#ddeef8;border-radius:16px;padding:32px;display:flex;justify-content:space-between;
    align-items:center;gap:24px;flex-wrap:wrap;margin-bottom:36px;}
.off-eye{font-family:'Space Mono',monospace;font-size:11px;letter-spacing:.24em;text-transform:uppercase;color:var(--th-text);}
.off-week h2{font-family:'Noto Serif SC',serif;font-size:28px;margin:8px 0;}
.off-week p{font-size:14px;color:#9cbdd4;}
.off-grid{display:flex;gap:12px;flex-wrap:wrap;}
.off-next{background:rgba(255,255,255,.06);border-radius:12px;padding:14px 18px;display:flex;flex-direction:column;gap:4px;
    border-top:3px solid var(--primary);min-width:170px;}
.off-next.atp{border-top-color:var(--secondary);}
.off-next span:last-child{font-size:12px;color:#9cbdd4;}

/* picks */
.pk-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px;}
.pk-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:18px 20px;display:flex;
    flex-direction:column;gap:10px;text-decoration:none;color:inherit;transition:transform .2s,box-shadow .2s;}
.pk-card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.08);}
.pk-hd{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;font-size:12px;}
.pk-meta{color:var(--muted);} .pk-meta b{color:var(--ink);}
.pk-row{display:grid;grid-template-columns:110px 1fr 44px;gap:10px;align-items:center;font-size:13px;}
.pk-name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.pk-track{height:8px;border-radius:4px;background:var(--track-bg);overflow:hidden;}
.pk-bar{display:block;height:100%;background:var(--primary);transform-origin:left;animation:grow .7s cubic-bezier(.22,.68,0,1) both;}
.atp .pk-bar{background:var(--secondary);}
.pk-pct{font-family:'Space Mono',monospace;text-align:right;color:var(--muted);}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}

/* last week */
.lw-sum{cursor:pointer;list-style:none;}
.lw-sum::-webkit-details-marker{display:none;}
.lw-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;animation:fadeUp .22s ease-out both;}
.lw-item{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--primary);border-radius:12px;
    padding:16px 18px;display:flex;flex-direction:column;gap:8px;}
.lw-item.atp{border-left-color:var(--secondary);}
.lw-head{display:flex;align-items:baseline;gap:8px;font-size:15px;}
.lw-tag{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;color:var(--primary-dark);}
.atp .lw-tag{color:var(--secondary);} body:not(.dark) .atp .lw-tag{filter:brightness(.72);}
.lw-date{font-size:12px;color:var(--muted);}
.lw-res{font-size:13px;color:var(--muted);} .lw-res.win{color:#2a6b4f;font-weight:700;} .lw-res.pending{color:#8a5a18;}
body.dark .lw-res.win{color:#7dcea0;} body.dark .lw-res.pending{color:#e0b56a;}
.wk-chips{display:flex;flex-wrap:wrap;gap:5px;}
.wk-chip{padding:3px 9px;border-radius:999px;background:rgba(42,107,79,.08);border:.5px solid rgba(42,107,79,.18);
    color:#1f4f3a;font-size:12px;white-space:nowrap;}
body.dark .wk-chip{background:rgba(125,206,160,.12);border-color:rgba(125,206,160,.22);color:#b7e0c6;}

/* nav */
.nav-hd{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap;}
.nav-hd .block-hd{margin:0;}
.help-dot{width:30px;height:30px;border-radius:50%;border:1px solid var(--primary-rim);background:var(--surface);
    color:var(--primary-dark);font:inherit;font-size:13px;font-weight:700;cursor:pointer;}
.seg{display:flex;gap:4px;padding:4px;background:var(--surface2);border:1px solid var(--border2);border-radius:999px;}
.seg button{font:inherit;font-size:14px;font-weight:700;min-height:40px;padding:0 22px;border:0;border-radius:999px;
    background:transparent;color:var(--muted);cursor:pointer;transition:background .18s,color .18s;}
.seg button[aria-selected="true"]{background:#1c3f94;color:#ffffff;}
.nav-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;animation:fadeUp .22s ease-out both;}
.nav-grid[hidden]{display:none;}
.nav-card{position:relative;background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;
    display:flex;flex-direction:column;gap:6px;transition:transform .2s,box-shadow .2s,border-color .2s;}
.nav-card:not(.off):hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.08);border-color:var(--primary-rim);}
.nav-eye{font-family:'Space Mono',monospace;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--primary-dark);}
.nav-title{font-family:'Noto Serif SC',serif;font-size:19px;font-weight:700;color:var(--ink);text-decoration:none;}
.nav-main::after{content:'';position:absolute;inset:0;border-radius:12px;}
.nav-desc{font-size:13px;color:var(--muted);}
.nav-links{display:flex;gap:8px;flex-wrap:wrap;margin-top:4px;}
.nav-link{font-size:13px;color:var(--primary-dark);text-decoration:none;padding:6px 12px;min-height:32px;box-sizing:border-box;
    border:1px solid var(--primary-rim);border-radius:999px;background:var(--primary-dim);transition:background .15s;}
.nav-link:hover{background:var(--primary-rim);}
.nav-card.off{opacity:.5;cursor:not-allowed;}
.dev-badge{font-family:'Noto Sans SC',sans-serif;font-size:11px;font-weight:500;color:var(--muted);border:1px solid var(--border);
    border-radius:999px;padding:1px 8px;margin-left:8px;vertical-align:middle;white-space:nowrap;display:inline-block;}

/* guide */
.guide{border:0;border-radius:16px;padding:0;max-width:720px;width:calc(100% - 32px);background:var(--surface);color:var(--ink);
    box-shadow:0 20px 50px rgba(0,0,0,.25);}
.guide::backdrop{background:rgba(5,20,32,.45);}
.guide[open]{animation:fadeUp .22s ease-out both;}
.guide-inner{padding:24px;display:flex;flex-direction:column;gap:14px;}
.guide-hd{display:flex;justify-content:space-between;align-items:center;}
.guide-hd h2{font-family:'Noto Serif SC',serif;font-size:22px;}
.guide-close{width:40px;height:40px;border-radius:50%;border:0;background:var(--surface2);color:var(--ink);font:inherit;cursor:pointer;}
.guide p{font-size:14px;color:var(--muted);line-height:1.6;}
.guide-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.guide-item{background:var(--surface2);border-radius:10px;padding:12px 14px;font-size:13px;line-height:1.55;color:var(--muted);}
.guide-item b{display:block;color:var(--ink);font-size:14px;margin-bottom:2px;}

footer{margin-top:24px;padding-top:20px;border-top:1px solid var(--border2);display:flex;justify-content:space-between;
    align-items:flex-end;flex-wrap:wrap;gap:12px;}
.credits{font-size:12px;color:var(--muted);line-height:2;}
.credits a{color:var(--ink2);text-decoration:none;border-bottom:1px dashed var(--border);}
.credits a:hover{color:var(--primary);border-bottom-color:var(--primary);}
.ver{font-family:'Space Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:.16em;padding:5px 9px;
    border:1px solid var(--border2);border-radius:3px;}

/* ── mobile ── */
@media(max-width:720px){
    .page{padding:16px 16px 56px;}
    header{margin-bottom:20px;}
    .logo-en{display:none;}
    .pill-btn .pill-label{display:none;}
    .pill-btn{min-width:44px;padding:0 12px;justify-content:center;gap:4px;}
    .logo{gap:8px;} .logo svg{width:36px !important;height:36px !important;}
    .logo-cn{font-size:17px;white-space:nowrap;}
    .theme-btn{white-space:nowrap;min-height:40px;}
    .hd-actions{gap:6px;}
    .theme-btn{padding:0 12px;}
    .hero{margin-bottom:24px;}
    .hero-main{padding-left:14px;}
    .ev-grid,.ev-grid.lopsided,.pk-grid{grid-template-columns:minmax(0,1fr);}
    .ev-card.pending .ev-pending{min-height:96px;}
    .ev-card{padding:16px;}
    .ev-stats{display:grid;grid-template-columns:repeat(3,1fr);text-align:center;gap:8px;}
    .ev-stat{align-items:center;}
    .ev-wx-row{flex-direction:column;align-items:stretch;}
    .pk-card{padding:16px;}
    .pk-row{grid-template-columns:96px 1fr 40px;}
    /* 上周赛况: one combined card on phones */
    .lw-grid{grid-template-columns:1fr;gap:0;background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:6px 16px;}
    .lw-item{background:none;border:0;border-radius:0;padding:12px 0;}
    .lw-item + .lw-item{border-top:1px solid var(--border2);}
    .nav-grid{grid-template-columns:1fr 1fr;gap:10px;}
    .nav-card{padding:16px;min-height:84px;}
    .nav-eye{font-size:13px;font-weight:700;letter-spacing:.1em;}
    .nav-title{font-size:16px;}
    .nav-desc{display:none;}
    .seg{width:100%;} .seg button{flex:1;padding:0;}
    .guide{margin:auto auto 0;width:100%;max-width:none;border-radius:18px 18px 0 0;}
    .guide-grid{grid-template-columns:1fr;}
    .off-week{padding:24px;}
}
@media(prefers-reduced-motion:reduce){
    *,*::before,*::after{animation:none !important;transition:none !important;}
}
"""

_JS_INDEX = r"""
(function(){
  // ── tour switch for 数据查询 ──
  const seg=document.querySelectorAll('.seg button');
  function pick(t){
    seg.forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tour===t)));
    document.querySelectorAll('.nav-grid').forEach(g=>{g.hidden=g.dataset.group!==t;});
    try{localStorage.setItem('navTour',t);}catch(e){}
  }
  seg.forEach(b=>b.addEventListener('click',()=>pick(b.dataset.tour)));
  try{const t=localStorage.getItem('navTour');if(t&&document.querySelector('.nav-grid[data-group="'+t+'"]'))pick(t);}catch(e){}

  // ── hourly weather toggles ──
  document.querySelectorAll('.wx-toggle').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const panel=document.getElementById(btn.getAttribute('aria-controls'));
      const open=btn.getAttribute('aria-expanded')!=='true';
      btn.setAttribute('aria-expanded',String(open));
      panel.hidden=!open;
    });
  });

  // ── guide dialog ──
  const guide=document.getElementById('guide');
  document.querySelectorAll('.guide-open').forEach(b=>b.addEventListener('click',()=>guide.showModal()));
  guide.querySelector('.guide-close').addEventListener('click',()=>guide.close());
  guide.addEventListener('click',e=>{if(e.target===guide)guide.close();});

  // ── survivor trend charts ──
  const data=JSON.parse(document.getElementById('trend-data').textContent||'{}');
  const NS='http://www.w3.org/2000/svg', W=480, H=200, L=44, R=464, T=16, B=168;
  const el=(n,a)=>{const e=document.createElementNS(NS,n);for(const k in a)e.setAttribute(k,a[k]);return e;};
  // Monotone cubic (Fritsch–Carlson): one continuous smooth curve, no overshoot.
  function smooth(P){
    const n=P.length; if(n<2)return '';
    const h=P.map((p,i)=>i?p[0]-P[i-1][0]:0), d=[];
    for(let i=0;i<n-1;i++)d.push((P[i+1][1]-P[i][1])/(P[i+1][0]-P[i][0]));
    const m=P.map((p,i)=>i===0?d[0]:i===n-1?d[n-2]:(d[i-1]*d[i]<=0?0:(d[i-1]+d[i])/2));
    for(let i=0;i<n-1;i++){
      if(d[i]===0){m[i]=0;m[i+1]=0;continue;}
      const a=m[i]/d[i], b=m[i+1]/d[i], s=a*a+b*b;
      if(s>9){const t=3/Math.sqrt(s);m[i]=t*a*d[i];m[i+1]=t*b*d[i];}
    }
    let s='M'+P[0][0]+' '+P[0][1];
    for(let i=1;i<n;i++){const dx=(P[i][0]-P[i-1][0])/3;
      s+=' C'+(P[i-1][0]+dx)+' '+(P[i-1][1]+m[i-1]*dx)+' '+(P[i][0]-dx)+' '+(P[i][1]-m[i]*dx)+' '+P[i][0]+' '+P[i][1];}
    return s;
  }
  function detail(days,i){
    if(i===0)return '开赛前，全员在场';
    const c=days[i].checkin;
    if(c){ // current day: same counts as the ranking page's 今日选人统计
      const keep=['存活','未完赛','轮空','未选'], keys=keep.concat(Object.keys(c).filter(k=>!keep.includes(k)));
      const lost=Object.keys(c).filter(k=>!keep.includes(k)).reduce((s,k)=>s+c[k],0);
      return keys.filter(k=>c[k]).map(k=>k+' '+c[k]).join(' · ')+(lost?' · 共淘汰 '+lost:'');
    }
    const o=days[i].out||{}, parts=Object.keys(o).sort((a,b)=>a==='球员输球'?-1:b==='球员输球'?1:0).map(k=>k+' '+o[k]);
    const lost=days[i-1].alive-days[i].alive;
    return (parts.length?parts.join(' · '):'无人淘汰')+(lost?' · 共淘汰 '+lost:'');
  }
  document.querySelectorAll('.trend').forEach(box=>{
    const tr=data[box.dataset.tour]; if(!tr)return;
    const days=tr.days, n=days.length, svg=box.querySelector('.trend-svg');
    const x=i=>L+(n===1?0:i*(R-L)/(n-1)), y=v=>B-v/tr.total*(B-T);
    const P=days.map((d,i)=>[x(i),y(d.alive)]);
    let sel=n-1;
    function draw(){
      svg.innerHTML='';
      [0,Math.round(tr.total/2),tr.total].forEach(v=>{
        svg.appendChild(el('line',{class:'grid',x1:L,x2:R,y1:y(v),y2:y(v)}));
        const t=el('text',{x:L-8,y:y(v)+4,'text-anchor':'end'});t.textContent=v;svg.appendChild(t);
      });
      days.forEach((d,i)=>{const t=el('text',{x:x(i),y:H-8,'text-anchor':'middle'});t.textContent='Day '+i;svg.appendChild(t);});
      const path=smooth(P);
      svg.appendChild(el('path',{class:'area pop',d:path+' L'+x(n-1)+' '+B+' L'+x(0)+' '+B+' Z'}));
      const line=el('path',{class:'line draw',d:path});svg.appendChild(line);
      const len=Math.ceil(line.getTotalLength?line.getTotalLength():800);
      line.style.strokeDasharray=len;line.style.setProperty('--len',len);
      svg.appendChild(el('line',{class:'cursor',x1:0,x2:0,y1:T-6,y2:B}));
      P.forEach((p,i)=>{const c=el('circle',{class:'dot pop',cx:p[0],cy:p[1],r:4});c.style.animationDelay=(.25+i*.15)+'s';svg.appendChild(c);});
      show(sel);
    }
    const chips=box.querySelector('.trend-days'), tip=box.querySelector('.trend-tip');
    days.forEach((d,i)=>{const b=document.createElement('button');b.type='button';
      b.textContent='Day '+i;b.addEventListener('click',()=>show(i));chips.appendChild(b);});
    function show(i){
      sel=i;
      const cur=svg.querySelector('.cursor'); if(cur){cur.setAttribute('x1',x(i));cur.setAttribute('x2',x(i));}
      svg.querySelectorAll('.dot').forEach((c,k)=>c.setAttribute('r',k===i?6:4));
      chips.querySelectorAll('button').forEach((b,k)=>b.setAttribute('aria-pressed',String(k===i)));
      const live=tr.live&&i===n-1;
      tip.innerHTML='<div class="tt-hd"><span>Day '+i+(live?'（进行中）':'')+
        '</span><span>存活 <b>'+days[i].alive+'</b> / '+tr.total+'</span></div><span class="tt-sub">'+detail(days,i)+'</span>';
    }
    const at=e=>{const r=svg.getBoundingClientRect(), px=(e.clientX-r.left)/r.width*W;
      return Math.max(0,Math.min(n-1,Math.round((px-L)/((R-L)/Math.max(1,n-1)))));};
    // Mouse: follow the pointer. Touch: only a tap selects (scrolling must not).
    svg.addEventListener('pointermove',e=>{if(e.pointerType==='mouse')show(at(e));});
    svg.addEventListener('click',e=>show(at(e)));
    box.querySelector('.trend-replay').addEventListener('click',draw);
    draw();
  });
})();
"""


# Count of watched users (ranking page watch lists); storage throws on data: URLs.
_JS_WATCH_COUNT = """\
(function(){
  var el=document.getElementById('watchCount'); if(!el) return;
  var n=0;
  try{
    var s=JSON.parse(localStorage.getItem('ts.watch.v1')||'null'), seen={};
    (s&&s.lists||[]).forEach(function(l){ (l.users||[]).forEach(function(u){ if(!seen[u]){ seen[u]=1; n++; } }); });
  }catch(e){}
  if(n){ el.textContent=n; el.hidden=false; el.parentNode.setAttribute('aria-label','我的关注 · '+n+' 人'); }
})();"""


def render_index(
    stats: dict,
    version: str = VERSION,
    weather=None,
    weather_label: str = "赛地天气",
    week_data: Optional[dict] = None,
    trends: Optional[dict] = None,
    picks: Optional[dict] = None,
    output_path: str | Path = "index.html",
) -> str:
    """
    Build and write the homepage HTML.

    Parameters
    ----------
    stats : dict
        Keys used: "season" (killer links, footer).
    weather :
        None / str (one shared strip) / list of (label, cards_html); a label
        containing "ATP" / "WTA" attaches that strip to that tour's card.
    week_data : dict
        prepare_home_weeks() output (上周 / 本周 / 下周 cards per tour).
    trends : dict
        {"ATP"|"WTA": survivor_trend.survivor_series(...)} for the 走势图.
    picks : dict
        {"ATP"|"WTA": survivor_trend.pick_summary(...)} for 今日选人.
    """
    del weather_label  # weather now opens from each tournament card
    season = stats.get("season", datetime.now().year)
    swing = _SWING_LABEL.get(getattr(state, "theme_name", "hard"), "Season")
    updated = datetime.now().strftime("%m/%d %H:%M")
    trend_json = json.dumps(
        {t: v for t, v in (trends or {}).items() if v}, ensure_ascii=False
    ).replace("</", "<\\/")
    guide_items = "".join(
        f'<div class="guide-item"><b>{html.escape(t)}</b>{html.escape(d)}</div>' for t, d in _GUIDE
    )

    html_str = f"""\
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>签表幸存者数据中心</title>
    {_FONTS}
    <style>
{state.css_vars}
{_CSS_BASE}
{_CSS_INDEX}
    </style>
</head>
<body>
<div class="page">
    <header>
        <a class="logo" href="#">
            {_logo_pair(44)}
            <div class="logo-text">
                <span class="logo-cn">签表幸存者</span>
                <span class="logo-en">Data Center</span>
            </div>
        </a>
        <div class="hd-actions">
            <a class="pill-btn" href="watchlist.html" title="我的关注" aria-label="我的关注"><svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" style="fill:var(--secondary)"><path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg><span class="pill-label">我的关注</span><span class="pill-n" id="watchCount" hidden></span></a>
            <button class="theme-btn" id="themeBtn" onclick="toggleTheme()">🌙 暗色</button>
        </div>
    </header>

    <div class="hero">
        <div class="hero-main">
            <div class="hero-label">Tennis Draw Survivor · {html.escape(str(season))} {html.escape(swing)}</div>
            <h1 class="hero-title">每一场，都是生死之战</h1>
        </div>
        <span class="live-pill"><span class="live-dot"></span>{updated} 更新</span>
    </div>

{_this_week_html(week_data, trends, weather)}
{_picks_html(week_data, picks)}
{_last_week_html(week_data)}
{_nav_html(season)}

    <footer>
        <div class="credits">
            <div>开发者：哭的没分蛙</div>
            <div>数据来源：<a href="https://www.live-tennis.cn/zh/survivor/calendar/{season}" target="_blank">丘的网球</a></div>
            <div>特别鸣谢：<a href="https://zechen-3is.github.io/survivor_champion_ranking/" target="_blank">旧纳</a></div>
            <div>数据仅供参考，一切以官方数据为准</div>
        </div>
        <span class="ver">v{html.escape(version)}</span>
    </footer>
</div>

<dialog class="guide" id="guide" aria-label="使用指南">
    <div class="guide-inner">
        <div class="guide-hd"><h2>使用指南</h2><button type="button" class="guide-close" aria-label="关闭">✕</button></div>
        <p>每天选一名球员，赢了存活得分，输了淘汰。数据查询处可切换 ATP / WTA / 合计，以下是各板块能做什么：</p>
        <div class="guide-grid">{guide_items}</div>
    </div>
</dialog>

<script type="application/json" id="trend-data">{trend_json}</script>
<script>
{_JS_THEME}
</script>
<script>
{_JS_INDEX}
</script>
<script>
{_JS_WATCH_COUNT}
</script>
</body>
</html>"""

    Path(output_path).write_text(html_str, encoding="utf-8")
    return html_str
