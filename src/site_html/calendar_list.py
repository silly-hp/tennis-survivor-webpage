"""赛历列表 page (survivor_calendar_{atp,wta}.html): this week, events by week, my results."""
from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path
from typing import Any, Optional

from site_html.common import _inner_page_shell
from site_html.rank_ui import CSS_RANK, help_button_html, help_modal_html
from tournament_meta import classify_surface
from site_html.types_meta import (
    _type_order,
    champion_type_label,
    type_filters_for_tour,
)

_HELP_ICON = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14"/>'
              '<path d="M12 17.5h.01"/></svg>')


def _tour_code(tour: str) -> str:
    """"MS" / "WS", or "" for the combined (联合) page."""
    t = str(tour or "").upper()
    if t in {"", "ALL"}:
        return ""
    return "WS" if t in {"WS", "WTA"} else "MS"


# combined page: levels without the tour prefix (badges keep their ATP/WTA label)
_ALL_LEVELS = ["大满贯", "年终总决赛", "奥运会", "1000", "500", "250"]


def _week_no(week_start: str) -> int:
    try:
        return date.fromisoformat(week_start[:10]).isocalendar()[1]
    except ValueError:
        return 0


def _payload(events: list[dict[str, Any]], years: list[int], tour_code: str, tour_lbl: str,
             default_year: int) -> dict[str, Any]:
    """Compact JSON for the page: one array per event, user names interned once."""
    names: dict[str, int] = {}
    rows = []
    for ev in events:
        ev_tour = str(ev.get("tour") or "").upper()
        if tour_code and ev_tour != tour_code:
            continue
        city = str(ev.get("city") or "")
        label = str(ev.get("type") or "").strip() or champion_type_label(city, ev_tour)
        week = str(ev.get("week_start") or "")[:10]
        s = ev.get("summary") or {}
        st = s.get("st") if ev.get("has_scores") else "none"
        users: dict[str, list[int]] = {}
        for name, code in (s.get("users") or {}).items():
            users.setdefault(str(code), []).append(names.setdefault(name, len(names)))
        rows.append([
            int(ev.get("year") or 0), week, _week_no(week), city, label,
            str(ev.get("href") or "") if ev.get("has_scores") else "",
            int(ev.get("n_players") or 0), st or "none",
            int(s.get("day") or 0), int(s.get("alive") or 0), int(s.get("champs") or 0),
            int(s.get("top") or 0), users, "W" if ev_tour == "WS" else "A",
            surface_code(city, ev_tour, ev.get("year")),
        ])
    # newest week first; same week by level then city (sort is stable)
    rows.sort(key=lambda r: (_type_order(r[4]), r[3]))
    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
    return {
        "tour": tour_lbl,
        "years": sorted({int(y) for y in years}, reverse=True),
        "year": default_year,
        "levels": type_filters_for_tour(tour_code) if tour_code else _ALL_LEVELS,
        "names": list(names),
        "events": rows,
    }


def _help_steps(tour: str) -> list[tuple[str, str, str]]:
    combined = tour == "ALL"
    tour = "ATP" if combined else tour
    k = tour + "1000"
    city = "东京" if tour == "WTA" else "巴塞尔"
    t = "A" if tour == "ATP" else "W"
    ev = ('<span class="hp-cal{me}"><span class="hp-cal-hd"><span class="cl-tl" data-t="{t}">{lv}</span><b>{city}</b><em>{st}</em></span>'
          '<span class="hp-cal-sub">{res}</span>{tag}</span>')
    tag = '<span class="hp-me">我 · {}</span>'
    s1 = ("本周与赛季概览",
          "顶部卡片是本周正在进行的赛事：第几比赛日、还剩多少人存活，以及“我”当前的状态；右侧四个数字概括所选赛季的赛事数、参赛人次、冠军人次和我的夺冠次数。",
          f'<div class="hp-cal-live"><span class="hp-cal-eye"><i></i>THIS WEEK · 本周进行中</span><b>{city} · {tour}500</b>'
          '<span>第 3 比赛日 · 320 人中还有 <strong>58</strong> 人存活</span>'
          '<span class="hp-me hp-cal-pop">我 · 存活</span></div>'
          '<div class="hp-cal-kpi"><span>EVENTS<b>32</b></span><span>ENTRIES<b>10.4k</b></span><span>TITLES<b>61</b></span><span>MY TITLES<b>2</b></span></div>')
    s2 = ("按周浏览每一站",
          "赛事按开赛周从新到旧排列，并按月份分组。每站卡片显示级别、城市、参赛人数和结果（冠军人数，或无人夺冠时的最高分）；暂无得分的站点置灰、不能点击。",
          '<span class="hp-cal-month">十月 · OCT</span><div class="hp-cal-wk"><b>10-19</b>'
          + ev.format(t=t, me="", lv=tour + "250", city="阿拉木图", st="已完赛", res="315 人 · 冠军 2 人", tag="")
          + ev.format(t=t, me=" off", lv=tour + "250", city="斯德哥尔摩", st="暂无得分", res="本站无得分数据", tag="")
          + '</div><div class="hp-cal-wk"><b>10-05</b>'
          + ev.format(t=t, me="", lv=k, city="上海", st="已完赛", res="348 人 · 冠军 1 人", tag="") + '<span></span></div>')
    s3 = ("年份与级别筛选",
          "选年份切换赛季，选级别只看大满贯、1000、500 等；右侧显示筛到的站数。筛选结果为空时会给出一键恢复的按钮。"
          + ("联合页还可按 ATP / WTA 筛选，每站卡片标出所属巡回赛。" if combined else ""),
          '<div class="hp-row"><span class="hp-chip on">2026<i class="hp-ping"></i></span><span class="hp-chip">2025</span><span class="hp-chip">2024</span></div>'
          f'<div class="hp-row"><span class="hp-chip">全部</span><span class="hp-chip">大满贯</span><span class="hp-chip hp-cal-hl">{k}</span><span class="hp-chip">{tour}500</span></div>'
          '<div class="hp-lines"><i></i><i></i></div><span class="hp-foot">显示 9 / 32 站</span>')
    s4 = ("“我”的成绩",
          "在排名页把自己设为“我”后，每站卡片会标出你的成绩：夺冠、存活或第几日出局。打开“只看我参加的”只保留你参加过的赛事。",
          '<div class="hp-row"><span class="hp-chip on">只看我参加的<i class="hp-ping"></i></span></div>'
          '<div class="hp-cal-wk hp-cal-two">'
          + ev.format(t=t, me=" me", lv="大满贯", city="美网", st="已完赛", res="475 人 · 冠军 3 人", tag=tag.format("夺冠"))
          + ev.format(t=t, me=" me", lv=k, city="上海", st="已完赛", res="348 人 · 冠军 1 人", tag=tag.format("第 5 日出局"))
          + '</div>')
    s5 = ("进入赛事战报",
          "点任意赛事卡片进入该站战报，查看冠军、本站看点和完整得分表。手机上每站是一张卡片，整张都可以点。",
          '<div class="hp-cal-go">'
          + ev.format(t=t, me=" hl", lv=tour + "500", city="维也纳", st="已完赛", res="64 人 · 冠军 3 人", tag="")
          + '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
          '<span class="hp-cal-recap"><em>EVENT RECAP</em><b>维也纳 · 2026</b><span>冠军 · 看点 · 得分表</span></span></div>'
          '<svg class="hp-cur" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 2l16 9-7 2-3 7z"/></svg>')
    return [s1, s2, s3, s4, s5]


def render_calendar_page(
    events: list[dict[str, Any]],
    years: list[int],
    updated: str,
    output_path: str | Path,
    *,
    tour: str = "MS",
    default_year: Optional[int] = None,
) -> str:
    """Write one tour's 赛历 list page.

    ``events`` carry ``has_scores``, ``n_players`` and (when scored) ``summary``
    from ``calendar_event_summary``; all filtering happens client-side.
    """
    tour_code = _tour_code(tour)
    tour_lbl = {"WS": "WTA", "MS": "ATP"}.get(tour_code, "ALL")
    years_sorted = sorted({int(y) for y in years}, reverse=True)
    default_year = int(default_year or (years_sorted[0] if years_sorted else date.today().year))
    data = _payload(events, years_sorted, tour_code, tour_lbl, default_year)
    # "</" must not end the <script> block early
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    # the header's ATP / WTA / 联合 switch already names the tour
    title = "签表幸存者赛历"
    rank_href = {"WTA": "wta_ranking.html", "ATP": "atp_ranking.html"}.get(tour_lbl, "combined_instant_ranking.html")
    tour_row = (
        '<div class="cl-frow"><span class="cl-flbl" id="clLblT">巡回赛</span>'
        '<span class="rk-chip-row" id="clTours" role="group" aria-labelledby="clLblT"></span></div>'
        if tour_lbl == "ALL" else ""
    )

    body = f"""\
<div class="rk cl" id="cl" data-tour="{tour_lbl}" data-rank="{rank_href}">
  <script type="application/json" id="clData">{blob}</script>
  <div class="cl-kpis" id="clKpis" aria-label="赛季概览"></div>
  <div id="clNow"></div>

  <section class="rk-card cl-bar">
    {tour_row}
    <div class="cl-frow">
      <span class="cl-flbl" id="clLblY">年份</span>
      <span class="cl-seg" id="clYears" role="group" aria-labelledby="clLblY"></span>
      <button type="button" class="rk-chip cl-mine" id="clMine" aria-pressed="false">只看我参加的</button>
      <span class="cl-count" id="clCount" aria-live="polite"></span>
    </div>
    <div class="cl-frow">
      <span class="cl-flbl" id="clLblL">级别</span>
      <span class="rk-chip-row cl-lvls" id="clLevels" role="group" aria-labelledby="clLblL"></span>
    </div>
  </section>

  <section class="rk-card cl-list" id="clList">
    <div class="cl-head" aria-hidden="true"><span>开赛周</span><span>赛事 · 本站结果</span></div>
    <div id="clWeeks"></div>
    <p class="rk-note cl-foot">点击赛事查看战报 · 无得分的站点置灰不可点 · 数据对齐
      <a href="https://www.live-tennis.cn/zh/survivor/calendar/{default_year}" target="_blank" rel="noopener">丘的网球 · 签表幸存者赛历</a></p>
  </section>
  <div class="rk-card cl-empty" id="clEmpty" hidden></div>
  {help_modal_html(title, steps=_help_steps(tour_lbl))}
</div>"""

    title_extra = (help_button_html()
                   + f'<span class="cl-hint">点击【<span class="cl-hint-ic" role="img" aria-label="使用说明图标">{_HELP_ICON}</span>】查看页面介绍</span>')
    html_str = _inner_page_shell(
        page_title=title,
        title=title,
        tour="",
        eyebrow=f"Survivor Calendar · {'ATP + WTA' if tour_lbl == 'ALL' else tour_lbl}",
        updated=updated,
        extra_tags=None,
        body_content=body,
        extra_css=CSS_RANK + "\n" + CSS_SURFACE + CSS_CAL_LIST,
        page=str(output_path),
        late_js=JS_CAL_LIST,
        title_extra=title_extra,
    )
    Path(output_path).write_text(html_str, encoding="utf-8")
    return html_str


# court-surface palettes (primary of the hard / clay / grass themes); also used by the event recap page
CSS_SURFACE = """\
[data-sf="h"]{--sf:#0088bb;--sf-ink:#005f85;}
[data-sf="c"]{--sf:#e06040;--sf-ink:#c04830;}
[data-sf="g"]{--sf:#1b5e37;--sf-ink:#0f3d22;}
body.dark [data-sf="h"]{--sf:#00b8f0;--sf-ink:#40d0ff;}
body.dark [data-sf="c"]{--sf:#e8603c;--sf-ink:#ff7a54;}
body.dark [data-sf="g"]{--sf:#4ca86a;--sf-ink:#7acc90;}
"""


def surface_code(city: str, tour: str, year: int | str | None = None) -> str:
    """"h" / "c" / "g" for an event's court surface."""
    surface = classify_surface(city, year)
    if city == "斯图加特" and str(tour).upper() in {"MS", "ATP"}:  # ATP Stuttgart is the grass event
        surface = "草地"
    return {"红土": "c", "草地": "g"}.get(surface, "h")


CSS_CAL_LIST = """\
body:has(.cl[data-tour="ATP"]) .page-header{--tour:var(--secondary);}
body:has(.cl[data-tour="WTA"]) .page-header{--tour:var(--primary);}
.page-eye{color:var(--tour,var(--primary));}
.cl[data-tour="ATP"],.rk-modal[data-tour="ATP"]{--tour:var(--secondary);--tour-ink:color-mix(in srgb,var(--secondary) 62%,var(--ink));}
.cl[data-tour="WTA"],.rk-modal[data-tour="WTA"]{--tour:var(--primary);--tour-ink:var(--primary-dark);}
body:has(.cl[data-tour="ALL"]) .page-header{--tour:#1c3f94;}
body.dark:has(.cl[data-tour="ALL"]) .page-header{--tour:#8fb0ff;}
.cl[data-tour="ALL"],.rk-modal[data-tour="ALL"]{--tour:var(--me);--tour-ink:var(--me);}
.cl,.rk-modal{--atp:var(--secondary);--wta:var(--primary);}
.cl[data-tour="ATP"] .cl-tl,.rk-modal[data-tour="ATP"] .cl-tl{background:var(--atp);color:#051420;}
.page-title .ttag:empty{display:none;}
.cl-hint{flex-basis:100%;font-family:'Noto Sans SC',sans-serif;font-size:13px;font-weight:400;color:var(--muted);display:inline-flex;align-items:center;}
.cl-hint-ic{display:inline-flex;color:var(--me,#1c3f94);}
body.dark .cl-hint-ic{color:#8fb0ff;}
.cl{gap:16px;}
.cl [hidden]{display:none !important;}

/* season KPIs */
.cl-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;}
.cl-kpi{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:4px;min-width:0;}
.cl-kpi .rk-eye{letter-spacing:.12em;}
.cl-kpi b{font-family:'Space Mono',monospace;font-size:26px;line-height:1.1;color:var(--ink);}
.cl-kpi span:last-child{font-size:12px;color:var(--muted);}
.cl-kpi.me b{color:var(--me);}

/* this week */
.cl-now{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:16px;align-items:center;padding:16px 20px;border-top:3px solid var(--tour);
    color:var(--ink);text-decoration:none;transition:transform .2s ease-out,box-shadow .2s ease-out;}
.cl-now-t{display:flex;flex-direction:column;gap:2px;}
.cl-now-eye{display:inline-flex;align-items:center;gap:6px;color:var(--tour-ink);letter-spacing:.14em;}
.cl-now-eye i{width:8px;height:8px;border-radius:50%;background:var(--tour);animation:clPulse 1.6s ease-in-out infinite;}
.cl-now-name{font-family:'Noto Serif SC',serif;font-size:20px;font-weight:700;display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.cl-now-res{font-size:14px;color:var(--ink2);display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.cl-now-res b{font-family:'Space Mono',monospace;}
.cl-now-res .alive{color:var(--primary-dark);}
.cl-now-go{font-size:13px;font-weight:700;color:var(--me);white-space:nowrap;}
.cl-hint-line{display:flex;align-items:center;gap:10px;min-height:44px;padding:0 16px;border:1px dashed var(--border);border-radius:12px;
    font-size:13px;color:var(--muted);flex-wrap:wrap;}
.cl-hint-line .rk-eye{width:110px;}
.cl-hint-line b{color:var(--ink2);}
@keyframes clPulse{0%,100%{opacity:1}50%{opacity:.35}}

/* filters */
.cl-bar{padding:12px 20px;display:flex;flex-direction:column;gap:10px;}
.cl-frow{display:flex;align-items:center;gap:12px;min-width:0;}
.cl-flbl{width:36px;flex-shrink:0;font-size:12px;font-weight:700;color:var(--muted);}
.cl-seg{display:flex;gap:4px;padding:4px;background:var(--surface2);border:1px solid var(--border);border-radius:999px;}
.cl-seg button{min-height:36px;padding:0 16px;border:0;border-radius:999px;background:transparent;color:var(--muted);font:inherit;font-size:13px;font-weight:700;
    font-family:'Space Mono',monospace;transition:background-color .18s,color .18s;}
.cl-seg button[aria-pressed="true"]{background:var(--me);color:#fff;}
body.dark .cl-seg button[aria-pressed="true"]{color:#06142a;}
.cl .rk-chip{min-height:36px;font-size:13px;}
.cl-mine{margin-left:auto;}
.cl .rk-chip.cl-mine[aria-pressed="true"]{background:var(--me-dim);border-color:var(--me);color:var(--me);}
.cl-count{font-size:13px;color:var(--muted);white-space:nowrap;}
.cl-count b{font-family:'Space Mono',monospace;color:var(--ink);}

/* list */
.cl-list{overflow:hidden;}
.cl-head{display:grid;grid-template-columns:120px minmax(0,1fr);gap:16px;padding:0 20px;min-height:40px;align-items:center;
    background:var(--th-bg);color:#fff;font-size:12px;font-weight:700;}
.cl-month{padding:10px 20px 4px;background:var(--surface2);border-top:1px solid var(--border2);}
.cl-wk{display:grid;grid-template-columns:120px minmax(0,1fr);gap:16px;padding:12px 20px;border-top:1px solid var(--border2);align-items:start;}
.cl-wk-d{display:flex;flex-direction:column;gap:2px;padding-top:6px;}
.cl-wk-d b{font-family:'Space Mono',monospace;font-size:16px;color:var(--ink);}
.cl-wk-d span{font-size:12px;color:var(--muted);}
.cl-evs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}
.cl-ev{display:flex;flex-direction:column;gap:8px;padding:12px 14px;border-radius:12px;border:1px solid var(--border);background:var(--surface);
    color:var(--ink);text-decoration:none;min-width:0;transition:transform .2s ease-out,box-shadow .2s ease-out;}
.cl-ev.off{background:var(--surface2);opacity:.6;}
.cl-ev-hd{display:flex;align-items:center;gap:8px;min-width:0;}
.cl-ev-city{font-family:'Noto Serif SC',serif;font-size:17px;font-weight:700;min-width:0;overflow-wrap:anywhere;line-height:1.3;}
.cl-st{margin-left:auto;flex-shrink:0;font-size:12px;font-weight:700;padding:2px 9px;border-radius:999px;background:var(--surface2);color:var(--muted);}
.cl-st[data-st="live"]{background:var(--primary-dim);color:var(--primary-dark);}
.cl-st[data-st="none"]{background:transparent;}
.cl-ev-sub{display:flex;align-items:center;gap:12px;font-size:13px;color:var(--muted);flex-wrap:wrap;}
.cl-ev-sub b{font-family:'Space Mono',monospace;color:var(--ink);}
.cl-me{margin-left:auto;font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px;background:var(--me);color:#fff;white-space:nowrap;}
body.dark .cl-me{color:#06142a;}
.cl-foot{margin:0;padding:10px 20px;background:var(--surface2);border-top:1px solid var(--border2);}

/* surface palettes: each event card takes its court's theme colors (page keeps the configured theme).
   --atp / --wta are resolved on .cl, so they keep the page theme inside a card. */
.cl-ev[data-sf],.cl-now[data-sf]{--primary:var(--sf);--primary-dark:var(--sf-ink);
    --primary-dim:color-mix(in srgb,var(--sf) 10%,transparent);--primary-rim:color-mix(in srgb,var(--sf) 28%,transparent);
    border:1px solid color-mix(in srgb,var(--sf) 22%,var(--border));border-top:3px solid var(--sf);
    background:color-mix(in srgb,var(--sf) 4%,var(--surface));}
.cl-ev[data-sf] .cl-st,.cl-now[data-sf] .cl-st{background:color-mix(in srgb,var(--sf) 10%,transparent);color:var(--sf-ink);}
.cl-ev[data-sf] .cl-st[data-st="none"]{background:transparent;color:var(--muted);}
.cl-ev[data-sf]:is(:hover,:focus-visible){border-color:color-mix(in srgb,var(--sf) 45%,var(--border));}
.cl-now[data-sf] .cl-now-eye{color:var(--sf-ink);}
.cl-now[data-sf] .cl-now-eye i{background:var(--sf);}
/* chips on a card (tour + level, "我") take the surface color; the dark ink shade keeps white text readable */
.cl [data-sf] :is(.cl-tl,.cl-me){background:var(--sf-ink);color:#fff;}
body.dark .cl [data-sf] :is(.cl-tl,.cl-me){background:var(--sf);color:#051420;}

/* one square chip: tour + level (tour color) */
.cl-tl{flex-shrink:0;font-family:'Space Mono',monospace;font-size:11px;font-weight:700;padding:2px 7px;border-radius:4px;white-space:nowrap;
    color:#fff;background:var(--wta);}
.cl-tl[data-t="A"]{background:var(--atp);color:#051420;}

/* tour tag on the combined page */
.cl-nows{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:12px;}
.cl-nows .cl-now{grid-template-columns:minmax(0,1fr) auto;}
.cl-nows .cl-now-res{grid-column:1 / -1;order:3;}

/* empty */
.cl-empty{padding:36px 20px;display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center;border-style:dashed;}
.cl-empty b{font-size:15px;color:var(--ink);}
.cl-empty p{margin:0;font-size:13px;color:var(--muted);line-height:1.6;}
.cl-empty svg{color:var(--muted);}

/* 使用说明 previews */
.hp-cal{display:flex;flex-direction:column;gap:6px;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--surface);min-width:0;}
.hp-cal.me{box-shadow:inset 3px 0 0 var(--me);}
.hp-cal.off{background:var(--surface2);opacity:.6;}
.hp-cal.hl{animation:hpCalHl 2.4s ease-out infinite alternate;}
.hp-cal-hd{display:flex;align-items:center;gap:8px;}
.hp-cal-hd b{font-family:'Noto Serif SC',serif;}
.hp-cal-hd em{margin-left:auto;font-style:normal;font-size:11px;color:var(--muted);}
.hp-cal-sub{font-size:12px;color:var(--muted);}
.hp-cal .hp-me{align-self:flex-start;}
.hp-cal-live{background:var(--surface);border-radius:10px;border-top:3px solid var(--tour);padding:12px 14px;display:flex;flex-direction:column;gap:6px;
    animation:hpBump .5s cubic-bezier(.22,.68,0,1) both;}
.hp-cal-eye{display:inline-flex;align-items:center;gap:6px;font-family:'Space Mono',monospace;font-size:11px;font-weight:700;color:var(--tour-ink);}
.hp-cal-eye i{width:8px;height:8px;border-radius:50%;background:var(--tour);animation:clPulse 1.6s ease-in-out infinite;}
.hp-cal-live b{font-family:'Noto Serif SC',serif;font-size:17px;}
.hp-cal-live strong{color:var(--primary-dark);font-family:'Space Mono',monospace;}
.hp-cal-pop{align-self:flex-start;animation:hpMenu 2.4s ease-in-out infinite alternate;}
.hp-cal-kpi{margin-top:10px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;font-family:'Space Mono',monospace;font-size:11px;color:var(--muted);}
.hp-cal-kpi span{background:var(--surface);border-radius:8px;padding:6px 8px;}
.hp-cal-kpi b{display:block;font-size:17px;color:var(--ink);}
.hp-cal-month{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.2em;color:var(--muted);}
.hp-cal-wk{margin-top:8px;display:grid;grid-template-columns:52px minmax(0,1fr) minmax(0,1fr);gap:8px;align-items:start;}
.hp-cal-wk > b{font-family:'Space Mono',monospace;padding-top:8px;}
.hp-cal-two{grid-template-columns:repeat(2,minmax(0,1fr));margin-top:14px;}
.hp-cal-hl{animation:hpCalChip 2.4s ease-out infinite alternate;}
.hp-cal-go{display:grid;grid-template-columns:minmax(0,1fr) 32px minmax(0,1fr);gap:10px;align-items:center;margin-top:20px;}
.hp-cal-go > svg{width:28px;height:28px;fill:none;stroke:var(--me);stroke-width:2;}
.hp-cal-recap{background:var(--surface);border-radius:10px;border-left:3px solid var(--tour);padding:10px 12px;display:flex;flex-direction:column;gap:4px;
    animation:hpMenu 2.4s ease-in-out infinite alternate;}
.hp-cal-recap em{font-style:normal;font-family:'Space Mono',monospace;font-size:11px;font-weight:700;color:var(--tour-ink);}
.hp-cal-recap b{font-family:'Noto Serif SC',serif;}
.hp-cal-recap span{font-size:12px;color:var(--muted);}
@keyframes hpCalHl{0%,40%{box-shadow:none}60%,100%{box-shadow:0 0 0 2px var(--me)}}
@keyframes hpCalChip{0%,40%{background:var(--surface);color:inherit}60%,100%{background:var(--me-dim);color:var(--me);border-color:var(--me)}}

@media(hover:hover){.cl-ev[href]:hover,.cl-now:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(5,20,32,.08);}
}
@media(max-width:720px){
  .cl-kpis{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}
  .cl-kpi{padding:10px 12px;}
  .cl-kpi b{font-size:22px;}
  .cl-kpi .rk-eye{font-size:11px;}
  .cl-now{grid-template-columns:minmax(0,1fr);gap:8px;padding:14px 16px;}
  .cl-now-eye.rk-eye{font-size:13px;}
  .cl-now-name{font-size:18px;}
  .cl-now-res .cl-me{margin-left:0;}
  .cl-hint-line{padding:10px 14px;}
  .cl-bar{padding:10px 12px;}
  .cl-frow{flex-wrap:wrap;gap:8px;}
  .cl-mine{margin-left:0;}
  .cl-count{margin-left:auto;}
  .cl-lvls{flex-wrap:nowrap;overflow-x:auto;margin-right:-12px;padding-right:12px;-webkit-mask-image:linear-gradient(90deg,#000 85%,transparent);}
  .cl-lvls .rk-chip,.cl-mine,.cl-seg button{min-height:44px;flex-shrink:0;}
  .cl-head{display:none;}
  .cl-month{padding:10px 14px 4px;}
  .cl-wk{grid-template-columns:52px minmax(0,1fr);gap:10px;padding:10px 12px;}
  .cl-wk-d b{font-size:15px;}
  .cl-wk-d span{font-size:11px;}
  .cl-evs{grid-template-columns:minmax(0,1fr);gap:8px;}
  .cl-ev{min-height:44px;}
  .cl-foot{padding:10px 14px;}
  .hp-cal-kpi{display:none;}
  .hp-cal-wk{grid-template-columns:44px minmax(0,1fr);}
  .hp-cal-wk > .hp-cal:nth-child(3){display:none;}
  .hp-cal-two{grid-template-columns:minmax(0,1fr);}
  .hp-cal-two > .hp-cal:nth-child(2){display:none;}
}
@media (prefers-reduced-motion:reduce){
  .cl-now,.cl-ev{transition:none;}
  .cl-now-eye i,.hp-cal-eye i,.hp-cal.hl,.hp-cal-live,.hp-cal-pop,.hp-cal-hl,.hp-cal-recap{animation:none;}
}
"""


JS_CAL_LIST = r"""
(function(){
function ready(fn){ if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',fn); else fn(); }
ready(function(){
  const root=document.getElementById('cl'); if(!root) return;
  let D; try{ D=JSON.parse(document.getElementById('clData').textContent); }catch(e){ return; }
  const TOUR=D.tour, E=D.events, N=D.names;
  const KEY='ts.watch.v1', HELP_KEY='ts.help.cal.v1';
  const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const still=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $=id=>document.getElementById(id);
  const MONTHS=['一','二','三','四','五','六','七','八','九','十','十一','十二'];
  const MON_EN=['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];

  // ── "我" comes from the shared watch lists (storage throws on data: URLs) ──
  function loadMe(){ try{ const v=JSON.parse(localStorage.getItem(KEY)||'null'); if(v&&typeof v.me==='string') return v.me; }catch(e){} return ''; }
  let ME=loadMe();
  // event row: [year, week, weekNo, city, label, href, n, st, day, alive, champs, top, {code:[nameIdx]}]
  function myCode(e){
    if(!ME) return null; const i=N.indexOf(ME); if(i<0) return null;
    for(const c in e[12]) if(e[12][c].includes(i)) return c;
    return null;
  }
  function myLabel(e,c){
    if(c==null) return '';
    if(c==='C') return '夺冠';
    if(c==='A') return '存活';
    return '第 '+c+' 日出局';
  }
  const lvKey=l=>String(l).replace(/^(ATP|WTA)/,'');
  // combined page: the ATP / WTA tag sits beside the city, so badges drop the prefix
  // one square chip for tour + level, e.g. "WTA500" / "ATP 大满贯"
  const chip=e=>{ const t=e[13]==='A'?'ATP':'WTA', l=String(e[4]);
    return '<span class="cl-tl" data-t="'+e[13]+'">'+esc(/^(ATP|WTA)/.test(l)?l:t+' '+l)+'</span>'; };
  const ST={live:'进行中',done:'已完赛',none:'暂无得分'};
  function result(e){
    if(e[7]==='none') return '本站无得分数据';
    if(e[7]==='live') return '第 '+e[8]+' 日 · 存活 '+e[9];
    return e[10]>0?'冠军 '+e[10]+' 人':'无人夺冠 · 最高 '+e[11];
  }

  // ── state ──
  const ALL=TOUR==='ALL';
  const st={year:D.year, lv:'all', mine:false, tf:'all'};
  const inYear=()=>E.filter(e=>e[0]===st.year&&(st.tf==='all'||e[13]===st.tf));

  function renderChips(){
    $('clYears').innerHTML=D.years.map(y=>'<button type="button" data-y="'+y+'" aria-pressed="'+(y===st.year)+'">'+y+'</button>').join('');
    $('clLevels').innerHTML=[['all','全部']].concat(D.levels.map(l=>[l,l])).map(([v,l])=>
      '<button type="button" class="rk-chip" data-lv="'+esc(v)+'" aria-pressed="'+(st.lv===v)+'">'+esc(l)+'</button>').join('');
    $('clMine').setAttribute('aria-pressed',String(st.mine));
    if(ALL) $('clTours').innerHTML=[['all','全部'],['A','ATP'],['W','WTA']].map(([v,l])=>
      '<button type="button" class="rk-chip" data-tf="'+v+'" aria-pressed="'+(st.tf===v)+'">'+l+'</button>').join('');
  }

  function renderKpis(){
    const ys=inYear().filter(e=>e[7]!=='none');
    const entries=ys.reduce((a,e)=>a+e[6],0), titles=ys.reduce((a,e)=>a+(e[7]==='done'?e[10]:0),0);
    const mine=ME?ys.filter(e=>myCode(e)==='C').length:null;
    const fmt=n=>n>=10000?(n/1000).toFixed(1).replace(/\.0$/,'')+'k':String(n);
    const k=(eye,v,l,cls)=>'<div class="cl-kpi'+(cls||'')+'"><span class="rk-eye">'+eye+'</span><b>'+v+'</b><span>'+l+'</span></div>';
    $('clKpis').innerHTML=k('Events',ys.length,st.year+' 赛季赛事')+k('Entries',fmt(entries),'累计参赛人次')
      +k('Titles',titles,'产生冠军人次')+k('My titles',mine==null?'—':mine,ME?'我的夺冠':'未设置“我”',' me');
  }

  function renderNow(){
    const box=$('clNow');
    if(st.year!==D.years[0]){ box.innerHTML=''; return; }
    const lives=inYear().filter(e=>e[7]==='live');
    if(lives.length){
      const card=live=>{
        const c=myCode(live), tag=c!=null?'<span class="cl-me">我 · '+esc(myLabel(live,c))+'</span>':'';
        const inner='<span class="cl-now-t"><span class="rk-eye cl-now-eye"><i aria-hidden="true"></i>This week · 本周进行中</span>'
          +'<span class="cl-now-name">'+chip(live)+esc(live[3])+'</span></span>'
          +'<span class="cl-now-res"><span>第 <b>'+live[8]+'</b> 比赛日 · '+live[6]+' 人中还有 <b class="alive">'+live[9]+'</b> 人存活</span>'+tag+'</span>'
          +'<span class="cl-now-go">查看战报 →</span>';
        const t=' data-sf="'+live[14]+'"';
        return live[5]?'<a class="rk-card cl-now"'+t+' href="'+esc(live[5])+'">'+inner+'</a>':'<div class="rk-card cl-now"'+t+'>'+inner+'</div>';
      };
      box.innerHTML=lives.length>1?'<div class="cl-nows">'+lives.map(card).join('')+'</div>':card(lives[0]);
      return;
    }
    const today=new Date().toISOString().slice(0,10);
    const next=E.filter(e=>e[1]>today&&(st.tf==='all'||e[13]===st.tf)).sort((a,b)=>a[1]<b[1]?-1:1)[0];
    const last=E.find(e=>e[7]==='done'&&e[5]&&(st.tf==='all'||e[13]===st.tf));
    box.innerHTML='<div class="cl-hint-line"><span class="rk-eye">This week</span><b>本周无赛事</b>'
      +(next?'<span>下一站：'+esc(next[1].slice(5))+' '+esc(next[3])+' · '+esc(/^(ATP|WTA)/.test(next[4])?next[4]:(next[13]==='A'?'ATP ':'WTA ')+next[4])+'</span>':'')
      +(last?'<a href="'+esc(last[5])+'" style="margin-left:auto;font-weight:700;color:var(--me)">看上一站战报：'+esc(last[3])+' →</a>':'')+'</div>';
  }

  function emptyCard(icon,title,text,btn,act){
    const el=$('clEmpty');
    el.innerHTML=icon+'<b>'+esc(title)+'</b><p>'+esc(text)+'</p>'+(btn?(act==='rank'?'<a class="rk-btn" href="'+esc(root.dataset.rank)+'">'+esc(btn)+'</a>'
      :'<button type="button" class="rk-btn" data-act="'+act+'">'+esc(btn)+'</button>'):'');
    el.hidden=false; $('clList').hidden=true;
  }
  const IC_F='<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 5h18l-7 8v6l-4-2v-4z"/></svg>';
  const IC_U='<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>';
  const IC_C='<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>';

  function render(){
    renderKpis(); renderNow();
    $('clEmpty').hidden=true; $('clList').hidden=false;
    let evs=inYear();
    const total=evs.length;
    if(st.lv!=='all') evs=evs.filter(e=>(ALL?lvKey(e[4]):e[4])===st.lv);
    if(st.mine){
      if(!ME){ $('clCount').innerHTML=''; emptyCard(IC_U,'还没有设置“我”','在排名页点用户名旁的星标，选“设为我”。','去排名页设置','rank'); return; }
      evs=evs.filter(e=>myCode(e)!=null);
    }
    const weeks=[]; let cur=null;
    evs.forEach(e=>{ if(!cur||cur.w!==e[1]){ cur={w:e[1],no:e[2],evs:[]}; weeks.push(cur); } cur.evs.push(e); });
    $('clCount').innerHTML='显示 <b>'+evs.length+'</b> / '+total+' 站 · '+weeks.length+' 周';
    if(!total){ emptyCard(IC_C,st.year+' 赛季还没有赛历数据','换个年份看看。','',''); return; }
    if(!evs.length){
      if(st.mine&&st.lv==='all') emptyCard(IC_C,ME+' 在 '+st.year+' 年还没参加过'+(ALL?'':' '+TOUR)+'赛事','换个年份，或关闭“只看我参加的”。','显示全部赛事','mine');
      else emptyCard(IC_F,'这个筛选下没有赛事','换个级别，或清除筛选。','清除筛选','reset');
      return;
    }
    let lastM='', out='';
    weeks.forEach(w=>{
      const m=Number(w.w.slice(5,7))-1;
      if(String(m)!==lastM){ lastM=String(m); out+='<div class="rk-eye cl-month">'+MONTHS[m]+'月 · '+MON_EN[m]+'</div>'; }
      out+='<div class="cl-wk"><span class="cl-wk-d"><b>'+esc(w.w.slice(5))+'</b><span>第 '+w.no+' 周</span></span><div class="cl-evs">'
        +w.evs.map(e=>{
          const c=myCode(e), tag=c!=null?'<span class="cl-me">我 · '+esc(myLabel(e,c))+'</span>':'';
          const inner='<span class="cl-ev-hd">'+chip(e)+'<span class="cl-ev-city">'+esc(e[3])+'</span><span class="cl-st" data-st="'+e[7]+'">'+ST[e[7]]+'</span></span>'
            +'<span class="cl-ev-sub">'+(e[7]!=='none'?'<span><b>'+e[6]+'</b> 人参赛</span>':'')+'<span>'+esc(result(e))+'</span>'+tag+'</span>';
          const cls='cl-ev'+(c!=null?' me':'')+(e[5]?'':' off'), t=' data-sf="'+e[14]+'"';
          return e[5]?'<a class="'+cls+'"'+t+' href="'+esc(e[5])+'">'+inner+'</a>':'<span class="'+cls+'"'+t+' aria-disabled="true">'+inner+'</span>';
        }).join('')+'</div></div>';
    });
    $('clWeeks').innerHTML=out;
  }

  root.addEventListener('click',e=>{
    const y=e.target.closest('[data-y]'); if(y){ st.year=Number(y.dataset.y); keepYear(); renderChips(); render(); return; }
    const t=e.target.closest('#clTours [data-tf]'); if(t){ st.tf=t.dataset.tf; renderChips(); render(); return; }
    const l=e.target.closest('#clLevels [data-lv]'); if(l){ st.lv=l.dataset.lv; renderChips(); render(); return; }
    if(e.target.closest('#clMine')){ st.mine=!st.mine; renderChips(); render(); return; }
    const a=e.target.closest('[data-act]'); if(!a) return;
    if(a.dataset.act==='reset'){ st.lv='all'; st.mine=false; st.tf='all'; }
    if(a.dataset.act==='mine') st.mine=false;
    renderChips(); render();
  });
  window.addEventListener('storage',e=>{ if(e.key===KEY){ ME=loadMe(); render(); } });

  // ── dialogs ──
  let lastFocus=null;
  function openModal(m,from){ lastFocus=from||document.activeElement; m.hidden=false; document.body.style.overflow='hidden'; m.querySelector('.rk-dlg').focus(); }
  function closeModal(m){ if(m.hidden) return; m.hidden=true; document.body.style.overflow=''; if(m.id==='rkHelp') stopHelp();
    if(lastFocus&&lastFocus.focus) lastFocus.focus({preventScroll:true}); }
  [...root.querySelectorAll('.rk-modal')].forEach(m=>{
    m.dataset.tour=TOUR; document.body.appendChild(m);
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

  // #y=2025 (from an event page's back link) picks the season; year switches keep it in the URL
  const hashYear=()=>{ const m=/(?:^#|&)y=(\d{4})/.exec(location.hash); return m?Number(m[1]):0; };
  function keepYear(){ try{ history.replaceState(null,'',st.year===D.year?location.pathname+location.search:'#y='+st.year); }catch(e){} }
  if(hashYear()) st.year=hashYear();
  if(!D.years.includes(st.year)) st.year=D.years[0];
  renderChips(); render();
});
})();
"""
