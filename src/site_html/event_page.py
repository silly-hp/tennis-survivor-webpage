"""赛事战报 page (events/{year}/{MS|WS}_{id}.html): recap, highlight cards, score table."""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from site_html.calendar_list import CSS_SURFACE, surface_code
from site_html import state
from site_html.common import _inner_page_shell
from site_html.rank_ui import (
    CSS_RANK,
    _SEARCH,
    _STAR,
    help_button_html,
    help_modal_html,
)
from points_calculation import ATP_YEAR_END_FINALS, WTA_YEAR_END_FINAL
from site_html.types_meta import champion_type_label
from themes import THEMES

_SURFACE_THEME = {"h": "hard", "c": "clay", "g": "grass"}
# Same series across years even when the city flips.
_CANADA_SERIES = frozenset({"蒙特利尔", "多伦多"})
_FINALS_TYPE = "年终总决赛"

_HELP_ICON = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14"/>'
              '<path d="M12 17.5h.01"/></svg>')
_CUP = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
        '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/></svg>')


def _status_group(status: str) -> str:
    s = str(status or "").strip()
    if s == "存活":
        return "A"
    if s.startswith("自杀"):
        return "S"
    return "O"


def _out_label(status: str) -> str:
    """Result of the pick that ended a run, e.g. 输球 / 退赛 / 自杀 · 重复."""
    s = str(status or "").strip()
    if s.startswith("自杀"):
        reason = s[2:].strip("()（）")
        return f"自杀 · {reason}" if reason else "自杀"
    if s.startswith("球员"):
        return s[2:] or s
    return s or "出局"


def _rows(df: pd.DataFrame) -> list[list[Any]]:
    """[rank, name, status, group, days, score, picks] with tied ranks (score, then days)."""
    out = []
    prev, rank = None, 0
    for i, r in enumerate(df.itertuples(index=False)):
        name = str(getattr(r, "用户名", "") or "")
        status = str(getattr(r, "当前状态", "") or "")
        days = int(getattr(r, "存活天数", 0) or 0)
        score = int(getattr(r, "本站得分", 0) or 0)
        picks = [str(p) for p in (getattr(r, "选人明细", None) or []) if str(p).strip() and str(p) != "nan"]
        key = (score, days)
        if key != prev:
            rank, prev = i + 1, key
        out.append([rank, name, status, _status_group(status), days, score, picks])
    return out


def _kill_line(d: dict[str, Any]) -> list[str]:
    return [f"D{int(d.get('day_index') or 0) + 1}",
            f"胜{str(d.get('loser') or '?')} · 带走 {int(d.get('kills') or 0)} 人"]


def _cards(stats: dict[str, Any]) -> list[dict[str, Any]]:
    """Highlight cards; ``empty`` carries the one-line hint when there is nothing to show."""
    live = not stats.get("completed")
    cards = []
    day_killer = str(stats.get("day_killer") or "").strip()
    detail = stats.get("day_detail")
    card = {"k": "day", "eye": "SPOILER OF THE DAY", "title": "最佳反杀"}
    if day_killer:
        d = detail if isinstance(detail, dict) else {
            "day_index": stats.get("day_index"), "loser": stats.get("day_loser"), "kills": stats.get("day_kills")}
        card.update(main=day_killer, tag=f"{int(d.get('kills') or 0)} 人", lines=[_kill_line(d)])
    else:
        card["empty"] = "首个比赛日结束后统计" if live else "缺少对阵数据，未能统计"
    cards.append(card)

    total_killer = str(stats.get("total_killer") or stats.get("top_killer") or "").strip()
    total = int(stats.get("total_kills") or stats.get("top_kills") or 0)
    card = {"k": "total", "eye": "MASTER SPOILER", "title": "反杀专家"}
    if total_killer:
        lines = [_kill_line(d) for d in (stats.get("total_details") or []) if isinstance(d, dict)]
        card.update(main=total_killer, tag=f"合计 {total} 人",
                    lines=lines or [["", f"共带走 {total} 人"]])
    else:
        card["empty"] = "首个比赛日结束后统计" if live else "缺少对阵数据，未能统计"
    cards.append(card)

    upset = stats.get("biggest_upset")
    card = {"k": "upset", "eye": "BIGGEST UPSET", "title": "最大冷门"}
    if isinstance(upset, dict) and upset.get("winner") and upset.get("loser"):
        nw, nl = int(upset.get("winner_picks") or 0), int(upset.get("loser_picks") or 0)
        users = [str(u).strip() for u in (upset.get("winner_users") or []) if str(u).strip()]
        card.update(main=f"{upset['winner']} 胜 {upset['loser']}", tag=f"选人 {nw} : {nl}",
                    lines=[["", f"慧眼识珠 · {nw} 人" if nw else "无人押中冷门"]], users=users)
    else:
        card["empty"] = "暂未出现爆冷：被选的热门全部取胜" if live else "本站没有爆冷：被选的热门全部取胜"
    cards.append(card)
    return cards


def _help_steps(tour: str, sf: str) -> list[tuple[str, str, str]]:
    t = "A" if tour == "ATP" else "W"
    row = ('<span class="hp-ev-row"><b>{r}</b><b>{n}</b>{me}<span>{d}</span><strong>{s}</strong></span>')
    s1 = ("一眼看懂这一站",
          "顶部是战报：赛事城市、级别和结果。完赛显示冠军（无人夺冠时显示最高分），进行中显示第几比赛日、还剩多少人存活；右侧四个数字是参赛、存活或夺冠人数、存活率和比赛日。",
          f'<div class="hp-ev-hero" data-sf="{sf}"><span class="hp-ev-eye">EVENT RECAP · {tour} · 2026</span>'
          f'<b>维也纳 · 2026 <span class="cl-tl" data-t="{t}">{tour}500</span></b>'
          '<span class="hp-ev-res">决赛日结束，3 位用户全程存活夺冠：</span>'
          '<span class="hp-ev-champs"><i>用户A</i><i>用户B</i><i class="me">用户C · 我</i></span></div>'
          '<div class="hp-ev-kpi"><span>ENTRANTS<b>64</b></span><span>CHAMPIONS<b>3</b></span><span>SURVIVAL<b>4.7%</b></span><span>DAYS<b>7</b></span></div>')
    s2 = ("本站看点",
          "最佳反杀、反杀专家、最大冷门三张卡片总结本站看点，每条淘汰记录单独一行，合计写在球员名旁。还没有数据的卡片收成一行提示，例如“冠军将在决赛后产生”。",
          '<div class="hp-ev-cards"><span class="hp-ev-card hl"><em>SPOILER OF THE DAY</em><b>最佳反杀</b><span>德米纳尔 <i>18 人</i></span><small>D3 胜鲁布列夫</small></span>'
          '<span class="hp-ev-card"><em>MASTER SPOILER</em><b>反杀专家</b><span>辛纳 <i>合计 21 人</i></span><small>D2 胜菲尔斯 · 9 人</small><small>D6 胜德雷珀 · 12 人</small></span>'
          '<span class="hp-ev-card"><em>BIGGEST UPSET</em><b>最大冷门</b><span>博尔赫斯 胜 弗里茨</span><small>选人 2 : 15</small></span></div>'
          '<div class="hp-ev-hint">冠军将在决赛后产生</div>')
    s3 = ("筛选与排序",
          "按状态筛选存活、出局或自杀，用搜索框找用户名；点深色表头的“排名”“存活天数”“本站得分”切换排序，下方显示筛到的人数。",
          '<div class="hp-row"><span class="hp-chip">全部 64</span><span class="hp-chip on">存活 3<i class="hp-ping"></i></span>'
          '<span class="hp-chip">出局 52</span><span class="hp-chip">自杀 9</span></div>'
          '<div class="hp-ev-th"><span>排名</span><span>用户名</span><span>存活天数 ↕</span><span>本站得分 ↓</span></div>'
          + row.format(r=1, n="用户A", me="", d="7", s="1000") + row.format(r=1, n="用户B", me="", d="7", s="1000")
          + '<span class="hp-foot">显示 3 / 64 位用户</span>')
    s4 = ("选人明细与手机卡片",
          "点“选人明细”在该行下方展开抽屉，逐日列出此人选了谁、哪天出局。手机上表格变成卡片，点卡片展开同样的明细。",
          '<div class="hp-ev-drw"><span class="hp-ev-row on"><b>4</b><b>用户D</b><span>6</span><strong>600</strong><em>选人明细 ▴</em></span>'
          '<span class="hp-ev-hist"><i>D1 辛纳 <u>晋级</u></i><i>D2 鲁内 <u>晋级</u></i><i>D3 弗里茨 <u class="x">输球</u></i></span></div>')
    s5 = ("关注与“我”",
          "点用户名前的 ☆ 把用户加入关注列表或设为“我”，与排名页共用，只保存在本机。打开“只看关注”只看他们这一站的成绩。",
          '<div class="hp-row"><span class="hp-chip gold">★ 只看关注<i class="hp-ping"></i></span></div>'
          '<div class="hp-list"><span class="me"><b>用户C</b><em class="hp-me">我</em></span><span><b>☆ 用户D</b><em class="hp-tag">★对手</em></span></div>'
          '<div class="hp-menu hp-menu-l"><span class="hp-ck on">好友</span><span class="hp-ck">对手</span><span class="hp-blue">设为“我”</span></div>')
    return [s1, s2, s3, s4, s5]


def event_year_series_key(
    city: str,
    tour: str,
    type_label: str = "",
) -> str:
    """Group key for year-jump: tour + city, with Canada / finals aliases."""
    tour_key = "WS" if str(tour).upper() in {"WS", "WTA"} else "MS"
    name = str(city or "").strip()
    typ = str(type_label or "").strip() or champion_type_label(name, tour_key)
    if name in _CANADA_SERIES:
        return f"{tour_key}|canada"
    if (
        typ == _FINALS_TYPE
        or name in ATP_YEAR_END_FINALS
        or name in WTA_YEAR_END_FINAL
    ):
        return f"{tour_key}|finals"
    return f"{tour_key}|{name}"


def _year_jump_html(
    year: int,
    city: str,
    year_siblings: list[tuple[int, str, str]],
) -> str:
    """Dropdown of other years in the same series; empty if fewer than two."""
    by_year: dict[int, tuple[str, str]] = {}
    for y, href, sibling_city in year_siblings:
        if not href:
            continue
        by_year[int(y)] = (str(href), str(sibling_city or "").strip())
    options = sorted(by_year.items(), key=lambda item: -item[0])
    if len(options) < 2:
        return ""
    current_city = str(city or "").strip()
    parts = [
        '<select class="year-jump" aria-label="切换年份" '
        'onchange="if(this.value) location.href=this.value">'
    ]
    for y, (href, sibling_city) in options:
        selected = " selected" if int(y) == int(year) else ""
        value = "" if int(y) == int(year) else html.escape(href, quote=True)
        if sibling_city and sibling_city != current_city:
            label = f"{int(y)} · {sibling_city}"
        else:
            label = str(int(y))
        parts.append(
            f'<option value="{value}"{selected}>{html.escape(label)}</option>'
        )
    parts.append("</select>")
    return "".join(parts)


def render_event_score_page(
    df: pd.DataFrame,
    *,
    city: str,
    tour: str,
    year: int,
    event_id: str,
    updated: str,
    output_path: str | Path,
    source_url: str = "",
    stats: Optional[dict[str, Any]] = None,
    type_label: str = "",
    year_siblings: Optional[list[tuple[int, str, str]]] = None,
) -> str:
    """Write one event's 战报 page; table, filters and drawers are drawn client-side from JSON."""
    del source_url  # kept for call-site compat
    tour_code = "WS" if str(tour).upper() in {"WS", "WTA"} else "MS"
    tour_lbl = "WTA" if tour_code == "WS" else "ATP"
    stats = stats or {}
    label = str(type_label or "").strip() or champion_type_label(city, tour_code)
    chip = label if label.startswith(("ATP", "WTA")) else f"{tour_lbl} {label}"
    sf = surface_code(city, tour_code, year)
    year_jump = _year_jump_html(int(year), city, list(year_siblings or []))
    rows = _rows(df)
    n = len(rows)
    alive = sum(1 for r in rows if r[3] == "A")
    day = max((len(r[6]) for r in rows), default=0)
    completed = bool(stats.get("completed"))
    champions = [str(x).strip() for x in (stats.get("champions") or []) if str(x).strip()]
    top = max((r[5] for r in rows), default=0)
    data = {
        "tour": tour_lbl, "city": city, "year": int(year), "live": not completed,
        "n": n, "alive": alive, "day": day, "champions": champions, "top": top,
        "topUsers": [r[1] for r in rows if r[5] == top] if n else [],
        "cards": _cards(stats), "rows": rows,
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    cal_href = f"../../survivor_calendar_{tour_lbl.lower()}.html#y={int(year)}"
    state_lbl = "IN PROGRESS" if not completed else "FINISHED"

    body = f"""\
<div class="rk ev" id="ev" data-tour="{tour_lbl}" data-sf="{sf}">
  <script type="application/json" id="evData">{blob}</script>
  <section class="ev-hero">
    <div class="ev-res" id="evRes"></div>
    <div class="ev-kpis" id="evKpis" aria-label="本站数据"></div>
  </section>
  <div id="evChamp"></div>
  <section class="ev-cards" id="evCards" aria-label="本站看点"></section>

  <section class="rk-card ev-board">
    <div class="ev-bar">
      <span class="ev-bar-t"><span class="rk-eye">Scoreboard</span><b>本站得分</b></span>
      <span class="ev-seg" id="evSt" role="group" aria-label="状态"></span>
      <button type="button" class="rk-chip ev-follow" id="evFollow" aria-pressed="false"><span class="rk-star-ic">{_STAR}</span>只看关注</button>
      <label class="ev-search">{_SEARCH}<span class="rk-sr">搜索用户名</span><input id="evQ" type="search" autocomplete="off" placeholder="搜索用户名"></label>
    </div>
    <div class="ev-tw">
      <table class="ev-t">
        <thead><tr>
          <th scope="col"><button type="button" data-sort="rank" aria-label="按排名排序">排名</button></th>
          <th scope="col">用户名</th><th scope="col">当前状态</th>
          <th scope="col"><button type="button" data-sort="days">存活天数</button></th>
          <th scope="col"><button type="button" data-sort="score">本站得分</button></th>
          <th scope="col"><span class="rk-sr">选人明细</span></th>
        </tr></thead>
        <tbody id="evRows"></tbody>
      </table>
    </div>
    <div class="rk-cards ev-cardsm" id="evCardsM"></div>
    <div class="ev-empty" id="evEmpty" hidden></div>
    <p class="rk-note ev-foot" id="evCount" aria-live="polite"></p>
  </section>
  <div class="rk-pop rk-picker" id="rkPicker" role="dialog" aria-label="加入哪个列表" hidden></div>
  {help_modal_html(f"{city} {int(year)} 战报", steps=_help_steps(tour_lbl, sf))}
</div>"""

    back = f'<a class="ev-back" href="{cal_href}">← {tour_lbl} 赛历 · {int(year)}</a>'
    title_text = city if year_jump else f"{city} · {year}"
    title_extra = (
        (year_jump or "")
        + f'<span class="cl-tl ev-tl" data-t="{tour_lbl[0]}" data-sf="{sf}">{html.escape(chip)}</span>'
        + help_button_html()
        + f'<span class="ev-hint">点击【<span class="ev-hint-ic" role="img" aria-label="使用说明图标">{_HELP_ICON}</span>】查看页面介绍</span>'
    )
    # the whole page wears the event's court-surface theme, not the site-wide one
    site_vars = state.css_vars
    state.set_css_vars(THEMES[_SURFACE_THEME[sf]])
    try:
        html_str = _render_shell(
            city,
            year,
            tour_lbl,
            state_lbl=state_lbl,
            updated=updated,
            body=body,
            output_path=output_path,
            title_extra=title_extra,
            pre_header=back,
            title_text=title_text,
        )
    finally:
        state.set_css_vars(site_vars)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_str, encoding="utf-8")
    return html_str


def _render_shell(
    city: str,
    year: int,
    tour_lbl: str,
    *,
    state_lbl: str,
    updated: str,
    body: str,
    output_path: str | Path,
    title_extra: str,
    pre_header: str,
    title_text: Optional[str] = None,
) -> str:
    return _inner_page_shell(
        page_title=f"{city} {year} 战报",
        title=title_text or f"{city} · {year}",
        tour="",
        eyebrow=f"Event Recap · {tour_lbl} · {int(year)} · {state_lbl}",
        updated=updated,
        extra_tags=None,
        body_content=body,
        extra_css=CSS_RANK + "\n" + CSS_SURFACE + CSS_EVENT,
        page=str(output_path),
        late_js=JS_EVENT,
        title_extra=title_extra,
        pre_header=pre_header,
    )


CSS_EVENT = """\
/* the page keeps the configured theme; the event's court surface tints its accents */
body:has(.ev) .page-header{--tour:var(--sf);}
body:has(.ev[data-sf="h"]) .page-header{--sf:#0088bb;--sf-ink:#005f85;}
body:has(.ev[data-sf="c"]) .page-header{--sf:#e06040;--sf-ink:#c04830;}
body:has(.ev[data-sf="g"]) .page-header{--sf:#1b5e37;--sf-ink:#0f3d22;}
body.dark:has(.ev[data-sf="h"]) .page-header{--sf:#00b8f0;--sf-ink:#40d0ff;}
body.dark:has(.ev[data-sf="c"]) .page-header{--sf:#e8603c;--sf-ink:#ff7a54;}
body.dark:has(.ev[data-sf="g"]) .page-header{--sf:#4ca86a;--sf-ink:#7acc90;}
body:has(.ev) .page-eye{color:var(--sf-ink);}
.page-title .ttag:empty{display:none;}
.year-jump{appearance:none;-webkit-appearance:none;cursor:pointer;flex-shrink:0;
    font-family:'Space Mono',monospace;font-size:14px;font-weight:600;letter-spacing:.04em;
    color:var(--ink);background:var(--surface2);border:1px solid var(--border);border-radius:6px;
    padding:4px 28px 4px 10px;line-height:1.2;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' fill='none' stroke='%23888' stroke-width='1.5'/%3E%3C/svg%3E");
    background-repeat:no-repeat;background-position:right 8px center;}
.year-jump:hover,.year-jump:focus{border-color:var(--sf, var(--primary-rim));outline:none;}
body.dark .year-jump{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' fill='none' stroke='%23aaa' stroke-width='1.5'/%3E%3C/svg%3E");}
.cl-tl{flex-shrink:0;font-family:'Space Mono',monospace;font-size:11px;font-weight:700;padding:2px 7px;border-radius:4px;white-space:nowrap;
    background:var(--sf-ink);color:#fff;}
body.dark .cl-tl{background:var(--sf);color:#051420;}
.ev-tl{font-size:13px;padding:3px 9px;align-self:center;}
.ev-hint{flex-basis:100%;font-family:'Noto Sans SC',sans-serif;font-size:13px;font-weight:400;color:var(--muted);display:inline-flex;align-items:center;}
.ev-hint-ic{display:inline-flex;color:var(--me,#1c3f94);}
body.dark .ev-hint-ic{color:#8fb0ff;}
.ev{gap:16px;}
.ev [hidden]{display:none !important;}
.ev-back{display:inline-flex;align-items:center;min-height:44px;margin:4px 0 8px;font-size:13px;color:var(--muted);text-decoration:none;}
.ev-back:hover{color:var(--ink);}

.ev-fx{position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:8000;}

/* recap */
/* type scale: title 32 · card value 17 · section title 15 · body 14 · meta 12–13 */
/* the result lines continue the title's accent bar, so the whole recap reads as one block */
body:has(.ev) .page-header{margin-bottom:0;padding-bottom:10px;}
.ev-hero{display:flex;flex-direction:column;gap:20px;}
.ev-res{display:flex;flex-direction:column;gap:8px;border-left:3px solid var(--primary);padding:0 0 2px 18px;
    font-size:14px;line-height:1.6;color:var(--ink2);}
.ev-res:empty{display:none;}
.ev-res-line{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.ev-res-line svg{color:var(--sf);flex-shrink:0;}
.ev-res b{font-weight:700;}
.ev-res .num{font-family:'Space Mono',monospace;color:var(--sf-ink);}
.ev-chips{display:flex;gap:6px;flex-wrap:wrap;align-items:center;padding-left:24px;}
.ev-chip{font-size:13px;font-weight:700;padding:2px 10px;border-radius:999px;background:var(--star-dim);color:var(--ink);}
.ev-chip.me{background:var(--me-dim);color:var(--me);box-shadow:inset 0 0 0 1px var(--me-rim);}
/* "我" / action controls (filters, 选人明细, badges, dialogs, ☆ menu) follow the surface theme here */
body:has(.ev) :is(.rk,.rk-modal,.rk-picker,.page-header){--me:var(--primary-dark);--me-dim:var(--primary-dim);--me-rim:var(--primary-rim);}
body.dark:has(.ev) :is(.rk,.rk-modal,.rk-picker,.page-header){--me:var(--primary);--me-dim:var(--primary-dim);--me-rim:var(--primary-rim);}
body.dark:has(.ev) .ev-hint-ic{color:var(--primary);}
.ev-more-n{align-self:center;font-size:14px;color:var(--muted);}
.ev-toggle{display:inline-flex;align-items:center;gap:4px;margin-left:2px;min-height:32px;padding:0 4px;border:0;background:transparent;
    font:inherit;font-size:14px;font-weight:700;color:var(--me);cursor:pointer;vertical-align:middle;}
.ev-toggle svg{transition:transform .2s ease-out;}
.ev-toggle[aria-expanded="true"] svg{transform:rotate(180deg);}
@media(prefers-reduced-motion:reduce){.ev-toggle svg{transition:none;}}
@media(max-width:720px){.ev-toggle{min-height:44px;}}
/* the header's ATP / WTA / 联合 switch follows the surface theme here */
body:has(.ev) .hd-seg-btn[aria-current="page"],body:has(.ev) .hd-seg-btn[aria-current="page"]:hover{background:var(--primary-dark);color:#fff;}
body.dark:has(.ev) .hd-seg-btn[aria-current="page"],body.dark:has(.ev) .hd-seg-btn[aria-current="page"]:hover{background:var(--primary);color:#051420;}
.ev-prog{width:min(520px,100%);height:6px;border-radius:3px;background:var(--track-bg);overflow:hidden;margin-left:24px;}
.ev-prog i{display:block;height:100%;background:var(--sf);transform-origin:left;animation:evGrow .6s ease-out both;}
.ev-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;}
.ev-kpi{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 18px;display:flex;flex-direction:column;gap:4px;min-width:0;}
.ev-kpi .rk-eye{letter-spacing:.12em;}
.ev-kpi b{font-family:'Space Mono',monospace;font-size:24px;line-height:1.1;color:var(--ink);}
.ev-kpi span:last-child{font-size:12px;color:var(--muted);}
.ev-kpi.hi b{color:var(--sf-ink);}

/* one-line hints (empty cards) */
.ev-hintline{display:flex;align-items:center;gap:10px;min-height:44px;padding:0 16px;border:1px dashed var(--border);border-radius:12px;
    font-size:13px;color:var(--muted);}
.ev-hintline .rk-eye{width:190px;flex-shrink:0;}
.ev-hintline b{color:var(--ink2);flex-shrink:0;}
.ev-hints{display:flex;flex-direction:column;gap:8px;}

/* highlight cards */
.ev-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;}
.ev-cards:empty{display:none;}
.ev-card{padding:16px 18px;display:flex;flex-direction:column;gap:8px;border-top:3px solid var(--sf);min-width:0;
    transition:transform .2s ease-out,box-shadow .2s ease-out;}
.ev-card-hd{display:flex;align-items:center;gap:10px;}
.ev-card-t{display:flex;flex-direction:column;min-width:0;}
.ev-card-t .rk-eye{letter-spacing:.14em;}
.ev-card-t b{font-family:'Noto Serif SC',serif;font-size:15px;color:var(--ink);}
.ev-card-main{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;font-size:17px;font-weight:700;color:var(--ink);}
.ev-card-tag{font-size:12px;font-weight:700;padding:2px 9px;border-radius:999px;background:var(--me-dim);color:var(--me);}
.ev-card ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--muted);line-height:1.5;}
.ev-card li{display:flex;gap:8px;}
.ev-card li em{font-style:normal;font-family:'Space Mono',monospace;font-size:11px;font-weight:700;min-width:28px;padding-top:2px;}
.ev-card-users{display:flex;gap:6px;flex-wrap:wrap;}
.ev-card-users span{font-size:12px;padding:2px 9px;border-radius:999px;background:var(--surface2);border:1px solid var(--border2);color:var(--ink2);}
.ev-card-users span.me{background:var(--me-dim);border-color:var(--me-rim);color:var(--me);font-weight:700;}

/* board */
.ev-board{overflow:hidden;}
.ev-bar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 20px;border-bottom:1px solid var(--border2);}
.ev-bar-t{display:flex;flex-direction:column;margin-right:4px;}
.ev-bar-t b{font-family:'Noto Serif SC',serif;font-size:15px;color:var(--ink);}
.ev-seg{display:flex;gap:4px;padding:4px;background:var(--surface2);border:1px solid var(--border);border-radius:999px;}
.ev-seg button{min-height:36px;padding:0 14px;border:0;border-radius:999px;background:transparent;color:var(--muted);font:inherit;font-size:13px;font-weight:700;
    display:inline-flex;align-items:center;gap:6px;transition:background-color .18s,color .18s;}
.ev-seg button .n{font-family:'Space Mono',monospace;font-weight:400;opacity:.75;}
.ev-seg button[aria-pressed="true"]{background:var(--me);color:#fff;}
body.dark .ev-seg button[aria-pressed="true"]{color:#06142a;}
.ev .rk-chip{min-height:36px;font-size:13px;}
.ev-follow{display:inline-flex;align-items:center;gap:6px;}
.ev-follow .rk-star-ic svg{fill:none;stroke:var(--star);}
.ev .rk-chip.ev-follow[aria-pressed="true"]{background:var(--star-dim);border-color:var(--star);color:var(--ink);}
.ev-follow[aria-pressed="true"] .rk-star-ic svg{fill:var(--star);}
.ev-search{margin-left:auto;display:flex;align-items:center;gap:8px;min-height:40px;padding:0 14px;border:1px solid var(--border);border-radius:999px;
    color:var(--muted);background:var(--drop-bg);width:220px;}
.ev-search input{border:0;outline:0;background:transparent;font:inherit;font-size:13px;color:var(--ink);min-width:0;flex:1;}
.ev-search:focus-within{border-color:var(--me);}

.ev-tw{overflow-x:auto;}
.ev-t{width:100%;border-collapse:collapse;font-size:14px;}
.ev-t th{background:var(--th-bg);color:#fff;font-size:12px;font-weight:700;text-align:left;padding:0 12px;height:44px;white-space:nowrap;}
.ev-t th:first-child,.ev-t td:first-child{padding-left:20px;width:64px;}
.ev-t th:last-child,.ev-t td:last-child{padding-right:20px;text-align:right;}
.ev-t th button{font:inherit;color:rgba(255,255,255,.72);background:transparent;border:0;padding:0;min-height:44px;display:inline-flex;align-items:center;gap:4px;}
.ev-t th button::after{content:'↕';opacity:.6;}
.ev-t th[aria-sort="descending"] button,.ev-t th[aria-sort="ascending"] button{color:#fff;}
.ev-t th[aria-sort="descending"] button::after{content:'↓';opacity:1;}
.ev-t th[aria-sort="ascending"] button::after{content:'↑';opacity:1;}
.ev-t td{padding:0 12px;height:52px;border-top:1px solid var(--border2);color:var(--ink);}
.ev-t tbody tr.r{transition:background-color .15s;}
.ev-t tbody tr.r.mine td{background:var(--me-dim);}
.ev-t tbody tr.r.mine td:first-child{box-shadow:inset 3px 0 0 var(--me);}
.ev-t tbody tr.r.open td{background:color-mix(in srgb,var(--me) 6%,var(--surface));border-bottom:0;}
.ev-t tbody tr.r.open td:first-child{box-shadow:inset 3px 0 0 var(--me);}
.ev-rank{font-family:'Space Mono',monospace;font-weight:700;color:var(--muted);}
.ev-rank[data-m="1"]{color:var(--rank1);}
.ev-name{display:flex;align-items:center;gap:4px;min-width:0;}
.ev-name .t{font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.ev-name .rk-star{flex-shrink:0;}
.ev-tag{font-size:11px;color:var(--star-ink,#8a6a00);white-space:nowrap;}
body.dark .ev-tag{color:var(--star);}
.ev-mebadge{font-size:11px;font-weight:700;padding:1px 7px;border-radius:999px;background:var(--me);color:#fff;flex-shrink:0;}
body.dark .ev-mebadge{color:#06142a;}
.ev-st{display:inline-flex;font-size:12px;font-weight:700;padding:2px 9px;border-radius:999px;background:var(--surface2);color:var(--muted);white-space:nowrap;}
.ev-st[data-g="A"]{background:color-mix(in srgb,var(--sf) 12%,transparent);color:var(--sf-ink);}
.ev-st[data-g="S"]{background:var(--bad-bg);color:var(--bad);}
.ev-num{font-family:'Space Mono',monospace;}
.ev-score{font-family:'Space Mono',monospace;font-weight:700;font-size:15px;}
.ev-more{min-height:36px;padding:0 12px;border-radius:999px;border:1px solid var(--me-rim);background:var(--surface);color:var(--me);font:inherit;font-size:13px;
    white-space:nowrap;}
.ev-more[aria-expanded="true"]{background:var(--me);border-color:var(--me);color:#fff;}
body.dark .ev-more[aria-expanded="true"]{color:#06142a;}

/* pick-history drawer under its row */
.ev-t tr.drw td{padding:0 20px 14px;height:auto;border-top:0;background:color-mix(in srgb,var(--me) 6%,var(--surface));box-shadow:inset 3px 0 0 var(--me);text-align:left;}
.ev-drw{animation:evDrw .24s cubic-bezier(.22,.68,0,1) both;transform-origin:top;padding-left:44px;}
.ev-drw-hd{display:flex;align-items:center;gap:10px;padding:4px 0 10px;}
.ev-drw-hd b{font-size:14px;}
.ev-hist{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;}
.ev-hist li{display:flex;align-items:center;gap:10px;min-height:44px;padding:0 12px;border-radius:10px;background:var(--surface);border:1px solid var(--border2);font-size:14px;min-width:0;}
.ev-hist li em{font-style:normal;font-family:'Space Mono',monospace;font-size:11px;font-weight:700;color:var(--muted);}
.ev-hist li b{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.ev-res-p{font-size:12px;font-weight:700;padding:2px 8px;border-radius:999px;white-space:nowrap;
    background:color-mix(in srgb,var(--sf) 12%,transparent);color:var(--sf-ink);}
.ev-res-p[data-r="x"]{background:var(--bad-bg);color:var(--bad);}
.ev-res-p[data-r="p"]{background:var(--surface2);color:var(--muted);}
.ev-empty{padding:36px 20px;display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center;}
.ev-empty b{font-size:15px;color:var(--ink);}
.ev-empty p{margin:0;font-size:13px;color:var(--muted);}
.ev-foot{margin:0;padding:10px 20px;background:var(--surface2);border-top:1px solid var(--border2);}

/* phone cards: same pattern as the ranking pages */
.ev-cardsm .rk-c-rank{color:var(--muted);}
.ev-cardsm .rk-c-rank[data-m="1"]{color:var(--rank1);}
.ev-cardsm .rk-card-row.rk-mine{box-shadow:inset 3px 0 0 var(--me);}
.ev-cardsm .rk-chev{transition:transform .2s ease-out;}
.ev-cardsm [aria-expanded="true"] .rk-chev{transform:rotate(180deg);}
.ev-cardsm .rk-c-more{display:flex;flex-direction:column;gap:6px;padding-left:44px;}
.ev-cardsm .rk-c-more[hidden]{display:none;}
.ev-cardsm .ev-hist{grid-template-columns:minmax(0,1fr);gap:6px;}
.ev-cardsm .ev-hist li{min-height:40px;}

/* 使用说明 previews */
.hp-ev-hero{display:flex;flex-direction:column;gap:6px;border-left:3px solid var(--sf);padding-left:14px;}
.hp-ev-eye{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.16em;color:var(--sf-ink);}
.hp-ev-hero b{font-family:'Noto Serif SC',serif;font-size:20px;display:flex;align-items:center;gap:8px;}
.hp-ev-res{font-size:13px;}
.hp-ev-champs{display:flex;gap:6px;animation:hpMenu 2.4s ease-in-out infinite alternate;}
.hp-ev-champs i{font-style:normal;font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px;background:var(--star-dim);}
.hp-ev-champs i.me{background:var(--me-dim);color:var(--me);}
.hp-ev-kpi{margin-top:12px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;font-family:'Space Mono',monospace;font-size:11px;color:var(--muted);}
.hp-ev-kpi span{background:var(--surface);border-radius:8px;padding:6px 8px;animation:hpBump .5s cubic-bezier(.22,.68,0,1) both;}
.hp-ev-kpi b{display:block;font-size:17px;color:var(--ink);}
.hp-ev-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;}
.hp-ev-card{background:var(--surface);border-radius:10px;border-top:3px solid var(--sf);padding:8px 10px;display:flex;flex-direction:column;gap:3px;font-size:12px;min-width:0;}
.hp-ev-card em{font-style:normal;font-family:'Space Mono',monospace;font-size:11px;font-weight:700;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.hp-ev-card i{font-style:normal;font-size:11px;font-weight:700;padding:0 6px;border-radius:999px;background:var(--me-dim);color:var(--me);}
.hp-ev-card small{font-size:11px;color:var(--muted);}
.hp-ev-card.hl{animation:hpEvHl 2.4s ease-out infinite alternate;}
.hp-ev-hint{margin-top:12px;min-height:34px;display:flex;align-items:center;padding:0 12px;border:1px dashed var(--border);border-radius:10px;font-size:12px;color:var(--muted);
    background:var(--surface);animation:hpMenu 2.4s ease-in-out infinite alternate;}
.hp-ev-th,.hp-ev-row{display:grid;grid-template-columns:36px minmax(0,1fr) 72px 72px;gap:8px;align-items:center;padding:0 10px;font-size:12px;}
.hp-ev-th{margin-top:12px;min-height:30px;border-radius:8px 8px 0 0;background:var(--th-bg);color:#fff;font-weight:700;}
.hp-ev-row{min-height:32px;background:var(--surface);border-top:1px solid var(--border2);}
.hp-ev-row strong{font-family:'Space Mono',monospace;}
.hp-ev-drw .hp-ev-row{grid-template-columns:36px minmax(0,1fr) 40px 56px auto;border-radius:8px 8px 0 0;box-shadow:inset 3px 0 0 var(--me);}
.hp-ev-drw .hp-ev-row em{font-style:normal;color:var(--me);font-weight:700;}
.hp-ev-hist{display:flex;gap:6px;flex-wrap:wrap;padding:8px 10px 10px 46px;background:var(--surface);border-radius:0 0 8px 8px;box-shadow:inset 3px 0 0 var(--me);
    animation:hpMenu 2.4s ease-in-out infinite alternate;}
.hp-ev-hist i{font-style:normal;font-size:12px;padding:3px 8px;border-radius:8px;background:var(--surface2);}
.hp-ev-hist u{text-decoration:none;font-weight:700;color:var(--sf-ink);}
.hp-ev-hist u.x{color:var(--bad);}
@keyframes hpEvHl{0%,40%{box-shadow:none}60%,100%{box-shadow:0 0 0 2px var(--me)}}
@keyframes evDrw{from{opacity:0;transform:translateY(-6px) scaleY(.96)}to{opacity:1;transform:none}}
@keyframes evGrow{from{transform:scaleX(0)}to{transform:none}}

@media(hover:hover){.ev-card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(5,20,32,.08);}
  .ev-t tbody tr.r:not(.open):hover td{background:var(--row-hover);}}
@media(max-width:1000px){
  .ev-hist{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media(max-width:720px){
  .ev-kpis{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}
  .ev-kpi{padding:10px 12px;}
  .ev-kpi b{font-size:22px;}
  .ev-chips,.ev-prog{padding-left:0;margin-left:0;}
  .ev-cards{grid-template-columns:minmax(0,1fr);gap:10px;}
  .ev-card{padding:14px 16px;}
  .ev-hintline{flex-wrap:wrap;gap:4px 10px;padding:10px 14px;}
  .ev-hintline .rk-eye{width:auto;}
  .ev-bar{padding:10px 12px;gap:8px;}
  .ev-bar-t{display:none;}
  .ev-seg{flex:1 1 100%;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));}
  .ev-seg button{min-height:40px;padding:0 4px;justify-content:center;gap:4px;white-space:nowrap;}
  .ev-seg button .n{font-size:11px;}
  .ev-follow{flex:1;justify-content:center;}
  .ev .rk-chip.ev-follow{min-height:44px;}
  .ev-search{flex:2;width:auto;margin-left:0;min-height:44px;}
  .ev-search input{font-size:15px;}
  .ev-tw{display:none;}
  .ev .rk-cards{display:flex;}
  .ev-foot{padding:10px 12px;}
  .hp-ev-kpi{display:none;}
  .hp-ev-cards{grid-template-columns:minmax(0,1fr);}
  .hp-ev-cards .hp-ev-card:not(.hl){display:none;}
}
@media (prefers-reduced-motion:reduce){
  .ev-card,.ev-t tbody tr.r,.ev-cardsm .rk-chev{transition:none;}
  .ev-drw,.ev-prog i,.hp-ev-champs,.hp-ev-kpi span,.hp-ev-card.hl,.hp-ev-hint,.hp-ev-hist{animation:none;}
}
"""


JS_EVENT = r"""
(function(){
function ready(fn){ if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',fn); else fn(); }
ready(function(){
  const root=document.getElementById('ev'); if(!root) return;
  let D; try{ D=JSON.parse(document.getElementById('evData').textContent); }catch(e){ return; }
  const R=D.rows, LIVE=D.live;
  const KEY='ts.watch.v1', HELP_KEY='ts.help.event.v1';
  const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const still=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $=id=>document.getElementById(id);
  const STAR=document.querySelector('.ev-follow .rk-star-ic').innerHTML;
  const CUP='CUP_SVG';

  // ── watch lists (shared with the ranking pages; storage throws on data: URLs) ──
  function load(){ try{ const v=JSON.parse(localStorage.getItem(KEY)||'null'); if(v&&Array.isArray(v.lists)) return v; }catch(e){} return {me:'',lists:[]}; }
  let S=load();
  function save(){ try{ localStorage.setItem(KEY,JSON.stringify(S)); }catch(e){} }
  const tagsOf=u=>S.lists.filter(l=>l.users.includes(u)).map(l=>l.name);
  const isFav=u=>S.lists.some(l=>l.users.includes(u));

  // row: [rank, name, status, group, days, score, picks]
  const G={A:'存活',O:'出局',S:'自杀'};
  const st={g:'all', follow:false, q:'', sort:'rank', dir:-1, open:''};
  if(LIVE&&D.alive>0) st.g='A';
  const me=()=>S.me&&R.some(r=>r[1]===S.me)?S.me:'';

  // ── recap: result line + KPIs + champion hint ──
  // long name lists show the first 8 (我 first) and a 展开 / 收起 toggle
  let chipsOpen=false;
  function chips(names){
    const m=me(), list=m&&names.includes(m)?[m].concat(names.filter(n=>n!==m)):names, SHOW=8;
    const shown=chipsOpen?list:list.slice(0,SHOW);
    let h=shown.map(n=>'<span class="ev-chip'+(n===m?' me':'')+'">'+esc(n)+(n===m?' · 我':'')+'</span>').join('');
    if(list.length>SHOW) h+=(chipsOpen?'':'<span class="ev-more-n">等 '+list.length+' 人</span>')
      +'<button type="button" class="ev-toggle" data-chips aria-expanded="'+chipsOpen+'">'+(chipsOpen?'收起':'展开')
      +'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>';
    return '<div class="ev-chips">'+h+'</div>';
  }
  function renderRecap(){
    const m=me(), mr=m?R.find(r=>r[1]===m):null;
    let h='';
    if(LIVE){
      const mine=mr?' <span class="ev-chip me">我 · '+(mr[3]==='A'?'存活 · '+mr[5]+' 分':'第 '+mr[6].length+' 日出局')+'</span>':'';
      h='<div class="ev-res-line">'+CUP+'<span>战至 <b>第 '+D.day+' 比赛日</b>，'+D.n+' 人中还有 <b class="num">'+D.alive+'</b> 人存活</span>'+mine+'</div>'
        +'<div class="ev-prog" role="img" aria-label="存活 '+D.alive+' / '+D.n+'"><i style="width:'+(D.n?D.alive/D.n*100:0).toFixed(1)+'%"></i></div>';
    }else if(D.champions.length){
      h='<div class="ev-res-line">'+CUP+'<span>决赛日结束，<b>'+D.champions.length+' 位</b>用户全程存活夺冠：</span></div>'+chips(D.champions);
    }else if(D.n){
      h='<div class="ev-res-line">'+CUP+'<span>本站无人满分通关。最高 <b class="num">'+D.top+'</b> 分：</span></div>'+chips(D.topUsers);
    }
    $('evRes').innerHTML=h;
    const champs=D.champions.length, k=(eye,v,l,hi)=>'<div class="ev-kpi'+(hi?' hi':'')+'"><span class="rk-eye">'+eye+'</span><b>'+v+'</b><span>'+l+'</span></div>';
    $('evKpis').innerHTML=k('Entrants',D.n,'参赛人数')
      +(LIVE?k('Alive',D.alive,'仍存活',1):k('Champions',champs,'成功夺冠',1))
      +k('Survival',(D.n?(D.alive/D.n*100):0).toFixed(1).replace(/\.0$/,'')+'%',LIVE?'当前存活率':'存活率')
      +k(LIVE?'Day':'Days',D.day,LIVE?'已进行比赛日':'比赛日');
    $('evChamp').innerHTML=LIVE?'<div class="ev-hintline"><span class="rk-eye">Champion</span><b>冠军</b><span>冠军将在决赛后产生 · 存活到最后一日且满分的用户即为冠军</span></div>':'';
  }

  // ── highlight cards (empty ones collapse into one-line hints) ──
  function renderCards(){
    const m=me(), full=D.cards.filter(c=>!c.empty), empty=D.cards.filter(c=>c.empty);
    $('evCards').innerHTML=full.map(c=>'<article class="rk-card ev-card"><span class="ev-card-hd">'
      +'<span class="ev-card-t"><span class="rk-eye">'+esc(c.eye)+'</span><b>'+esc(c.title)+'</b></span></span>'
      +'<span class="ev-card-main">'+esc(c.main)+(c.tag?'<span class="ev-card-tag">'+esc(c.tag)+'</span>':'')+'</span>'
      +'<ul>'+(c.lines||[]).map(l=>'<li>'+(l[0]?'<em>'+esc(l[0])+'</em>':'')+'<span>'+esc(l[1])+'</span></li>').join('')+'</ul>'
      +(c.users&&c.users.length?'<span class="ev-card-users">'+c.users.map(u=>'<span'+(u===m?' class="me"':'')+'>'+esc(u)+'</span>').join('')+'</span>':'')
      +'</article>').join('');
    const hints=empty.map(c=>'<div class="ev-hintline"><span class="rk-eye">'+esc(c.eye)+'</span><b>'+esc(c.title)+'</b><span>'+esc(c.empty)+'</span></div>').join('');
    let box=document.getElementById('evHints');
    if(!box){ box=document.createElement('div'); box.id='evHints'; box.className='ev-hints'; $('evCards').after(box); }
    box.innerHTML=hints; box.hidden=!hints;
  }

  // ── table ──
  function result(r,i,n){
    const last=i===n-1;
    if(!last) return ['晋级',''];
    if(r[3]==='A') return LIVE?['进行中','p']:['晋级',''];
    const s=String(r[2]);
    if(s.indexOf('自杀')===0){ const why=s.slice(2).replace(/[()（）]/g,''); return [why?'自杀 · '+why:'自杀','x']; }
    return [s.indexOf('球员')===0?s.slice(2):(s||'出局'),'x'];
  }
  // an out user whose picks only cover the days survived (e.g. 自杀(退赛): no pick that day) gets an empty last day
  const picksOf=r=>r[3]!=='A'&&r[6].length===r[4]?r[6].concat([null]):r[6];
  const hist=r=>{ const ps=picksOf(r); return '<ol class="ev-hist">'+ps.map((p,i)=>{ const [t,c]=result(r,i,ps.length);
    return '<li><em>D'+(i+1)+'</em><b>'+(p==null?'—':esc(p))+'</b><span class="ev-res-p"'+(c?' data-r="'+c+'"':'')+'>'+t+'</span></li>'; }).join('')+'</ol>'; };
  function filtered(){
    const q=st.q.trim().toLowerCase(), m=me();
    let rows=R.filter(r=>(st.g==='all'||r[3]===st.g)&&(!q||r[1].toLowerCase().includes(q))&&(!st.follow||r[1]===m||isFav(r[1])));
    const k={rank:0,days:4,score:5}[st.sort];
    // dir -1 = the column's natural order: rank ascending, days / score descending
    const f=st.dir<0?1:-1;
    rows=rows.slice().sort((a,b)=>st.sort==='rank'?(a[0]-b[0])*f:((b[k]-a[k])*f||a[0]-b[0]));
    return rows;
  }
  function renderSeg(){
    const n={all:R.length,A:0,O:0,S:0}; R.forEach(r=>n[r[3]]++);
    $('evSt').innerHTML=[['all','全部'],['A','存活'],['O','出局'],['S','自杀']].map(([v,l])=>
      '<button type="button" data-g="'+v+'" aria-pressed="'+(st.g===v)+'">'+l+' <span class="n">'+n[v]+'</span></button>').join('');
    $('evFollow').setAttribute('aria-pressed',String(st.follow));
    document.querySelectorAll('.ev-t th').forEach(th=>{ const b=th.querySelector('[data-sort]'); if(!b) return;
      const nat=b.dataset.sort==='rank'?'ascending':'descending', rev=nat==='ascending'?'descending':'ascending';
      th.setAttribute('aria-sort',b.dataset.sort===st.sort?(st.dir<0?nat:rev):'none'); });
  }
  function nameCell(r,m){
    const tags=tagsOf(r[1]);
    return '<span class="ev-name"><button type="button" class="rk-star'+(isFav(r[1])||r[1]===m?' on':'')+'" data-star="'+esc(r[1])+'" aria-haspopup="dialog" aria-expanded="false" aria-label="关注 '+esc(r[1])+'">'+STAR+'</button>'
      +'<span class="t">'+esc(r[1])+'</span>'+(r[1]===m?'<span class="ev-mebadge">我</span>':'')+(tags.length?'<span class="ev-tag">'+esc(tags.join(' · '))+'</span>':'')+'</span>';
  }
  function render(){
    renderSeg();
    const rows=filtered(), m=me();
    $('evRows').innerHTML=rows.map(r=>{
      const open=st.open===r[1];
      return '<tr class="r'+(r[1]===m?' mine':'')+(open?' open':'')+'"><td><span class="ev-rank"'+(r[0]===1?' data-m="1"':'')+'>'+r[0]+'</span></td>'
        +'<td>'+nameCell(r,m)+'</td><td><span class="ev-st" data-g="'+r[3]+'">'+esc(r[2])+'</span></td>'
        +'<td class="ev-num">'+r[4]+'</td><td class="ev-score">'+r[5]+'</td>'
        +'<td><button type="button" class="ev-more" data-open="'+esc(r[1])+'" aria-expanded="'+open+'">选人明细 '+(open?'▴':'›')+'</button></td></tr>'
        +(open?'<tr class="drw"><td colspan="6"><div class="ev-drw" role="region" aria-label="'+esc(r[1])+' 的选人历史"><div class="ev-drw-hd"><span class="rk-eye">Pick history</span>'
          +'<b>'+esc(r[1])+' · '+esc(r[2])+' · 存活 '+r[4]+' 天 · '+r[5]+' 分</b></div>'+(r[6].length?hist(r):'<p class="rk-note">暂无选人记录</p>')+'</div></td></tr>':'');
    }).join('');
    $('evCardsM').innerHTML=rows.map(r=>{
      const open=st.open===r[1];
      return '<div class="rk-card-row'+(r[1]===m?' rk-mine':'')+'"><div class="rk-card-main">'
        +'<button type="button" class="rk-card-btn" data-open="'+esc(r[1])+'" aria-expanded="'+open+'">'
        +'<span class="rk-c-rank"'+(r[0]===1?' data-m="1"':'')+'>'+r[0]+'</span>'
        +'<span class="rk-c-mid"><span class="rk-c-name"><span class="t">'+esc(r[1])+'</span>'+(r[1]===m?'<span class="ev-mebadge">我</span>':'')+'</span>'
        +'<span class="rk-c-sub"><span class="ev-st" data-g="'+r[3]+'">'+esc(r[2])+'</span><span>'+r[4]+' 天</span></span></span>'
        +'<span class="rk-c-right"><span class="rk-c-pts">'+r[5]+'</span><svg class="rk-chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></span></button>'
        +'<button type="button" class="rk-star'+(isFav(r[1])||r[1]===m?' on':'')+'" data-star="'+esc(r[1])+'" aria-haspopup="dialog" aria-expanded="false" aria-label="关注 '+esc(r[1])+'">'+STAR+'</button></div>'
        +'<div class="rk-c-more"'+(open?'':' hidden')+'>'+(r[6].length?hist(r):'<span>暂无选人记录</span>')+'</div></div>';
    }).join('');
    const empty=!rows.length;
    $('evEmpty').hidden=!empty; document.querySelector('.ev-tw').style.visibility=empty?'hidden':'';
    if(empty){
      const followEmpty=st.follow&&!S.lists.some(l=>l.users.length)&&!me();
      $('evEmpty').innerHTML=followEmpty
        ?'<b>还没有关注的用户</b><p>点用户名前的星标把用户加入关注列表。</p><button type="button" class="rk-btn" data-act="all">显示全部用户</button>'
        :st.follow?'<b>关注的人都没参加这一站</b><p>关闭“只看关注”查看全部用户。</p><button type="button" class="rk-btn" data-act="all">显示全部用户</button>'
        :'<b>没有符合条件的用户</b><p>换个关键词，或清除状态筛选。</p><button type="button" class="rk-btn" data-act="reset">清除筛选</button>';
    }
    $('evCount').innerHTML='显示 <b>'+rows.length+'</b> / '+R.length+' 位用户 · 点表头排序 · 点「选人明细」查看选人历史';
  }

  root.addEventListener('click',e=>{
    if(e.target.closest('[data-chips]')){ chipsOpen=!chipsOpen; renderRecap(); const b=root.querySelector('[data-chips]'); if(b) b.focus({preventScroll:true}); return; }
    const g=e.target.closest('#evSt [data-g]'); if(g){ st.g=g.dataset.g; st.open=''; render(); return; }
    if(e.target.closest('#evFollow')){ st.follow=!st.follow; render(); return; }
    const s=e.target.closest('[data-sort]'); if(s){ const k=s.dataset.sort; if(st.sort===k) st.dir=-st.dir; else { st.sort=k; st.dir=-1; } render(); return; }
    const o=e.target.closest('[data-open]'); if(o){ st.open=st.open===o.dataset.open?'':o.dataset.open; render();
      const b=root.querySelector('[data-open="'+CSS.escape(o.dataset.open)+'"]'+(o.classList.contains('rk-card-btn')?'.rk-card-btn':'.ev-more')); if(b) b.focus({preventScroll:true}); return; }
    const a=e.target.closest('[data-act]'); if(a){ if(a.dataset.act==='reset'){ st.g='all'; st.q=''; $('evQ').value=''; } st.follow=false; render(); }
  });
  $('evQ').addEventListener('input',e=>{ st.q=e.target.value; render(); });

  // ── ☆ picker (same menu as the ranking page) ──
  const picker=$('rkPicker'); let pickFor='', pickBtn=null;
  document.body.appendChild(picker);
  function openPicker(btn,name){
    if(pickBtn===btn&&!picker.hidden){ closePicker(); return; }
    pickFor=name; pickBtn=btn; renderPicker(); picker.hidden=false; btn.setAttribute('aria-expanded','true');
    const r=btn.getBoundingClientRect(), w=232;
    picker.style.left=Math.max(12,Math.min(window.scrollX+r.left,window.scrollX+document.documentElement.clientWidth-w-12))+'px';
    picker.style.top=(window.scrollY+r.bottom+6)+'px';
    const f=picker.querySelector('button'); if(f) f.focus();
  }
  function closePicker(){ if(picker.hidden) return; picker.hidden=true; if(pickBtn){ pickBtn.setAttribute('aria-expanded','false'); if(document.body.contains(pickBtn)) pickBtn.focus({preventScroll:true}); } pickBtn=null; }
  function renderPicker(){
    const u=pickFor;
    picker.innerHTML='<span class="rk-eye rk-pop-eye">ADD TO LIST · '+esc(u)+'</span>'
      +S.lists.map(l=>'<button type="button" class="rk-opt" data-l="'+l.id+'" aria-pressed="'+l.users.includes(u)+'"><span class="rk-box" aria-hidden="true"></span><span class="rk-opt-l">'+esc(l.name)+'</span></button>').join('')
      +'<form class="rk-pick-new"><input class="rk-input" name="n" placeholder="新建列表名" aria-label="新建列表名"><button type="submit" class="rk-btn rk-btn-sm">新建</button></form>'
      +'<button type="button" class="rk-pick-act rk-pick-me" data-me="1">'+(S.me===u?'取消设为“我”':'设为“我”')+'</button>';
  }
  function afterChange(){ save(); const y=window.scrollY; renderRecap(); renderCards(); render(); window.scrollTo(0,y); }
  root.addEventListener('click',e=>{ const b=e.target.closest('[data-star]'); if(!b) return; e.stopPropagation(); openPicker(b,b.dataset.star); },true);
  picker.addEventListener('click',e=>{ e.stopPropagation(); const b=e.target.closest('button'); if(!b) return;
    if(b.dataset.l){ const l=S.lists.find(x=>x.id===b.dataset.l); const i=l.users.indexOf(pickFor); i<0?l.users.push(pickFor):l.users.splice(i,1); afterChange(); renderPicker(); picker.querySelector('[data-l="'+l.id+'"]').focus(); }
    else if(b.dataset.me){ S.me=S.me===pickFor?'':pickFor; afterChange(); closePicker(); } });
  picker.addEventListener('submit',e=>{ e.preventDefault(); const n=e.target.n.value.trim(); if(!n) return;
    S.lists.push({id:'l'+Date.now().toString(36),name:n,users:[pickFor]}); afterChange(); renderPicker(); });
  picker.addEventListener('keydown',e=>{ if(e.key==='Escape'){ e.stopPropagation(); closePicker(); } });
  document.addEventListener('click',e=>{ if(!picker.contains(e.target)) closePicker(); });
  window.addEventListener('resize',closePicker);
  window.addEventListener('storage',e=>{ if(e.key===KEY){ S=load(); renderRecap(); renderCards(); render(); } });

  // ── dialogs ──
  let lastFocus=null;
  function openModal(m,from){ lastFocus=from||document.activeElement; m.hidden=false; document.body.style.overflow='hidden'; m.querySelector('.rk-dlg').focus(); }
  function closeModal(m){ if(m.hidden) return; m.hidden=true; document.body.style.overflow=''; if(m.id==='rkHelp') stopHelp(); closePicker();
    if(lastFocus&&lastFocus.focus) lastFocus.focus({preventScroll:true}); }
  [...root.querySelectorAll('.rk-modal')].forEach(m=>{
    m.dataset.tour=D.tour; m.dataset.sf=root.dataset.sf; document.body.appendChild(m);
    m.addEventListener('click',e=>{ if(e.target===m||e.target.closest('[data-close]')) closeModal(m); });
    m.addEventListener('keydown',e=>{
      if(e.key==='Escape'){ e.stopPropagation(); closeModal(m); return; }
      if(e.key!=='Tab') return;
      const f=[...m.querySelectorAll('button:not([disabled]),[href],input')].filter(x=>x.offsetParent!==null);
      if(!f.length) return; const a=f[0], z=f[f.length-1];
      if(e.shiftKey&&document.activeElement===a){ e.preventDefault(); z.focus(); }
      else if(!e.shiftKey&&document.activeElement===z){ e.preventDefault(); a.focus(); }
    });
  });

  // ── 使用说明 (auto-advancing steps, shown once on first visit) ──
  const help=$('rkHelp');
  const steps=help?[...help.querySelectorAll('.hp-step')]:[], bars=help?[...help.querySelectorAll('.hp-bar')]:[];
  let step=0, helpT=0;
  function showStep(i){
    step=Math.max(0,Math.min(steps.length-1,i));
    steps.forEach((s,k)=>{ s.hidden=k!==step; });
    bars.forEach((b,k)=>{ b.classList.toggle('done',k<step); b.classList.remove('now'); });
    void help.offsetWidth; bars[step].classList.add('now');
    $('rkHelpNo').textContent=step+1;
    $('rkHelpPrev').disabled=step===0;
    $('rkHelpNext').textContent=step===steps.length-1?'开始使用':'下一步';
    clearTimeout(helpT);
    if(!still()) helpT=setTimeout(()=>showStep(step===steps.length-1?0:step+1),5000);
  }
  function stopHelp(){ clearTimeout(helpT); }
  if(help){
    const btn=$('rkHelpBtn');
    if(btn) btn.addEventListener('click',()=>{ openModal(help,btn); showStep(0); });
    $('rkHelpPrev').addEventListener('click',()=>showStep(step-1));
    $('rkHelpNext').addEventListener('click',()=>{ if(step===steps.length-1) closeModal(help); else showStep(step+1); });
    $('rkHelpMute').addEventListener('click',()=>{ try{ localStorage.setItem(HELP_KEY,'1'); }catch(e){} closeModal(help); });
    const hd=help.querySelector('.rk-dlg');
    hd.addEventListener('pointerenter',e=>{ if(e.pointerType==='mouse'){ stopHelp(); bars[step]&&bars[step].classList.add('paused'); } });
    hd.addEventListener('pointerleave',e=>{ if(e.pointerType==='mouse'){ bars[step]&&bars[step].classList.remove('paused'); showStep(step); } });
    let seen=false; try{ seen=localStorage.getItem(HELP_KEY)==='1'; }catch(e){ seen=true; }
    if(!seen&&!location.hash){ try{ localStorage.setItem(HELP_KEY,'1'); }catch(e){} setTimeout(()=>{ openModal(help,btn); showStep(0); },600); }
  }

  // ── 3s fireworks when the event produced champions ──
  function fireworks(){
    if(LIVE||!D.champions.length||still()) return;
    const cv=document.createElement('canvas'); cv.className='ev-fx'; cv.setAttribute('aria-hidden','true');
    document.body.appendChild(cv);
    const dpr=Math.min(window.devicePixelRatio||1,2), W=innerWidth, H=innerHeight;
    cv.width=W*dpr; cv.height=H*dpr; const x=cv.getContext('2d'); x.scale(dpr,dpr);
    const cs=getComputedStyle(root), col=[cs.getPropertyValue('--primary'),cs.getPropertyValue('--rank1'),cs.getPropertyValue('--secondary'),'#ffffff']
      .map(c=>c.trim()).filter(Boolean);
    const P=[], t0=performance.now();
    function burst(){
      const cx=W*(.15+Math.random()*.7), cy=H*(.12+Math.random()*.35), c=col[Math.floor(Math.random()*col.length)];
      for(let i=0;i<46;i++){ const a=Math.PI*2*i/46+Math.random()*.2, v=2+Math.random()*3.2;
        P.push({x:cx,y:cy,vx:Math.cos(a)*v,vy:Math.sin(a)*v,life:1,c}); }
    }
    let next=0;
    (function frame(now){
      const t=now-t0;
      if(t<2200&&t>=next){ burst(); next=t+380; }
      x.clearRect(0,0,W,H);
      x.globalAlpha=t>2400?Math.max(0,1-(t-2400)/600):1;
      P.forEach(p=>{ p.x+=p.vx; p.y+=p.vy; p.vy+=.06; p.vx*=.985; p.vy*=.985; p.life-=.012;
        if(p.life<=0) return; x.fillStyle=p.c; x.globalAlpha*=1; x.beginPath(); x.arc(p.x,p.y,2.2*p.life+.6,0,Math.PI*2); x.fill(); });
      if(t<3000) requestAnimationFrame(frame); else cv.remove();
    })(t0);
  }

  renderRecap(); renderCards(); render(); fireworks();
});
})();
""".replace("CUP_SVG", _CUP)
