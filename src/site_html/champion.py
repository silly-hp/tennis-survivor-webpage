"""Hall of Fame (历史冠军榜) page: an event list and a per-user ranking.

One page per tour (atp_champion.html / wta_champion.html) plus 联合
(combined_champion.html). champions.csv only holds titles (one row per
champion per event), so everything here is built from titles alone.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

from site_html.common import _inner_page_shell
from site_html.rank_ui import CSS_RANK, help_button_html, help_modal_html

_HELP_ICON = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14"/>'
              '<path d="M12 17.5h.01"/></svg>')
_STAR = ('<svg width="16" height="16" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">'
         '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg>')
_SEARCH = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
           'aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>')
_CUP = ('<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
        'aria-hidden="true"><path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/></svg>')
_CLOSE = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
          'aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>')

_PAGES = {
    "ATP": ("ATP 历史冠军榜", "Hall of Fame · ATP"),
    "WTA": ("WTA 历史冠军榜", "Hall of Fame · WTA"),
    "ALL": ("联合 历史冠军榜", "Hall of Fame · ATP + WTA"),
}

# champions.csv `type` → level key used on the page
_LEVEL = {"大满贯": "大满贯", "年终总决赛": "年终总决赛", "奥运会": "奥运会",
          "ATP1000": "1000", "WTA1000": "1000", "ATP500": "500", "WTA500": "500",
          "ATP250": "250", "WTA250": "250"}
# tie-break tiers: 大满贯 > 年终总决赛 > 合赛/双周 1000 > 单周 1000 > 奥运会 > 500 > 250
_TIER = {"大满贯": 7, "年终总决赛": 6, "奥运会": 3, "500": 2, "250": 1}
_BIG_1000 = {
    "ATP": {"印第安维尔斯", "迈阿密", "马德里", "罗马", "蒙特利尔", "多伦多", "辛辛那提", "上海"},
    "WTA": {"印第安维尔斯", "迈阿密", "马德里", "罗马", "蒙特利尔", "多伦多", "辛辛那提", "北京"},
}


# Olympic years shrink the Canada and Cincinnati events to one week
_OLYMPIC_YEARS = {2024, 2028, 2032}
_OLYMPIC_ONE_WEEK = {"蒙特利尔", "多伦多", "辛辛那提"}


def _tier(level: str, tour: str, name: str, season: int) -> int:
    if level == "1000":
        if season in _OLYMPIC_YEARS and name in _OLYMPIC_ONE_WEEK:
            return 4
        return 5 if name in _BIG_1000.get(tour, set()) else 4
    return _TIER.get(level, 0)


def _payload(df: pd.DataFrame, tour: str) -> dict:
    """Events newest first as [tour, name, season, week, level, tier, [user ids]]."""
    d = df.dropna(subset=["user_id", "tournament", "week"]).copy()
    d = d[d["username"].notna()]
    if tour != "ALL":
        d = d[d["tour"] == tour]
    d["user_id"] = d["user_id"].astype(int)
    d["season"] = d["season"].astype(int)
    d["week"] = d["week"].astype(str).str.slice(0, 10)
    # latest username per user (usernames can change; user_id is the identity)
    users = (d.sort_values("week").groupby("user_id")["username"].last()
             .astype(str).to_dict())
    events = []
    for (t, name, season, week, typ), g in d.groupby(["tour", "tournament", "season", "week", "type"], sort=False):
        level = _LEVEL.get(str(typ), str(typ))
        uids = list(dict.fromkeys(g["user_id"].tolist()))
        events.append([t[0], str(name), int(season), week, level, _tier(level, t, str(name), int(season)), uids])
    events.sort(key=lambda e: (e[3], e[1]), reverse=True)
    return {"tour": tour, "events": events, "users": {str(k): v for k, v in users.items()}}


def _help_steps(tour: str) -> list[tuple[str, str, str]]:
    t = "WTA" if tour == "WTA" else "ATP"
    k = "1000" if tour == "ALL" else t + "1000"
    tour_note = "联合页还可按 ATP / WTA 筛选。" if tour == "ALL" else ""
    s1 = ("两种视图",
          "“赛事”按开赛周从新到旧列出每一站；“冠军”按用户汇总冠军数，前三名登上领奖台，下方表格可按冠军数、最高级别、最近夺冠排序。",
          '<div class="hp-row"><span class="hp-chip">赛事</span><span class="hp-chip on">冠军<i class="hp-ping"></i></span></div>'
          '<div class="hp-pod"><span><em>NO.1</em><b>用户A</b><strong>5</strong></span><span><em>NO.2</em><b>用户B</b><strong>3</strong></span>'
          '<span><em>NO.3</em><b>用户C</b><strong>3</strong></span></div><div class="hp-lines"><i></i><i></i></div>')
    s2 = ("按赛事查看冠军",
          "点击赛事卡片展开冠军名单，同一站可能有多位冠军。点任意名牌查看此人的全部冠军记录，不受当前筛选影响。",
          f'<div class="hp-ev"><span class="hp-ev-hd"><b>武汉</b><span class="hp-chip">{k}</span><em>3 位冠军</em></span>'
          '<span class="hp-ev-chips"><span class="hp-chip"><i>1</i>用户A</span><span class="hp-chip"><i>2</i>用户D</span>'
          '<span class="hp-chip"><i>3</i>用户F</span></span></div>'
          f'<div class="hp-menu hp-menu-r"><b>用户D 的冠军记录</b><span>共 3 冠 · {k} 1 · …</span></div>'
          '<svg class="hp-cur" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 2l16 9-7 2-3 7z"/></svg>')
    s3 = ("排名规则",
          "先比冠军数；相同时从大满贯开始逐级比较：大满贯 › 年终总决赛 › 合赛/双周 1000 › 单周 1000 › 奥运会 › 500 › 250，先多者在前。所有级别都相同则名次并列，按最近夺冠先后排列。奥运年的蒙特利尔 / 多伦多、辛辛那提按单周 1000 计。",
          '<div class="hp-row hp-tiers"><span>大满贯</span>›<span>总决赛</span>›<span>双周1000</span>›<span>单周1000</span>›<span>奥运会</span>›<span>500</span>›<span>250</span></div>'
          '<div class="hp-list"><span class="hp-bump"><b>2 · 用户C</b><em>2 冠 · 大满贯 1</em></span>'
          f'<span><b>3 · 用户F</b><em>2 冠 · {k} 2</em></span></div>')
    s4 = ("赛季与类型筛选",
          "赛季、类型筛选同时作用于两个视图，排名按筛选后的冠军重新计算，右侧显示筛到的赛事数。" + tour_note,
          '<div class="hp-row"><span class="hp-chip">全部</span><span class="hp-chip on">2026<i class="hp-ping"></i></span><span class="hp-chip">2025</span></div>'
          f'<div class="hp-row"><span class="hp-chip">全部</span><span class="hp-chip">大满贯</span><span class="hp-chip on">{k}</span></div>'
          '<div class="hp-lines"><i></i><i></i></div><span class="hp-foot">显示 4 / 12 场赛事</span>')
    s5 = ("关注与“我”",
          "点 ☆ 把用户加入关注列表或设为“我”，与排名页共用，只保存在本机。打开“只看关注”只显示他们的冠军。",
          '<div class="hp-row"><span class="hp-chip gold">★ 只看关注<i class="hp-ping"></i></span></div>'
          '<div class="hp-list"><span class="me"><b>用户A</b><em class="hp-me">我</em></span><span><b>☆ 用户B</b><em class="hp-tag">★好友</em></span></div>'
          '<div class="hp-menu hp-menu-l"><span class="hp-ck on">好友</span><span class="hp-ck">对手</span><span class="hp-blue">设为“我”</span></div>')
    return [s1, s2, s3, s4, s5]


def render_champion_page(
    df: pd.DataFrame,
    tour: str,
    updated: str,
    output_path: str | Path = "champion.html",
) -> str:
    """Write a 历史冠军榜 page.

    ``df`` is champions.csv (usernames already refreshed); ``tour`` is
    "ATP", "WTA" or "ALL" (联合: both tours, every title tagged).
    """
    tour = tour.upper()
    title, eyebrow = _PAGES[tour]
    data = _payload(df, tour)
    # "</" must not end the <script> block early
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tour_row = (
        '<div class="ch-frow"><span class="ch-flbl" id="chLblT">巡回赛</span>'
        '<span class="rk-chip-row" id="chTours" role="group" aria-labelledby="chLblT"></span></div>'
        if tour == "ALL" else ""
    )

    body = f"""\
<div class="rk ch" id="ch" data-tour="{tour}">
  <script type="application/json" id="chData">{blob}</script>
  <section class="rk-card ch-bar" id="chBar">
    <div class="ch-bar-top">
      <div class="ch-views" role="tablist" aria-label="视图">
        <button type="button" role="tab" id="chTabE" data-v="events" aria-selected="true" aria-controls="chEvents">赛事<span class="n" id="chNE"></span></button>
        <button type="button" role="tab" id="chTabP" data-v="players" aria-selected="false" aria-controls="chPlayers">冠军<span class="n" id="chNP"></span></button>
      </div>
      <button type="button" class="rk-chip ch-follow" id="chFollow" aria-pressed="false"><span class="rk-star-ic">{_STAR}</span>只看关注</button>
      <label class="ch-search" id="chSearch" hidden>{_SEARCH}<span class="rk-sr">搜索用户名</span><input id="chQ" type="search" autocomplete="off" placeholder="搜索用户名"></label>
      <span class="ch-count" id="chCount" aria-live="polite"></span>
    </div>
    <div class="ch-filters">
      {tour_row}
      <div class="ch-frow"><span class="ch-flbl" id="chLblS">赛季</span><span class="rk-chip-row" id="chSeasons" role="group" aria-labelledby="chLblS"></span></div>
      <div class="ch-frow"><span class="ch-flbl" id="chLblL">类型</span><span class="rk-chip-row" id="chLevels" role="group" aria-labelledby="chLblL"></span></div>
    </div>
  </section>

  <div class="ch-evs" id="chEvents" role="tabpanel" aria-labelledby="chTabE"></div>

  <div class="ch-players" id="chPlayers" role="tabpanel" aria-labelledby="chTabP" hidden>
    <div class="ch-podium" id="chPodium"></div>
    <div class="rk-chip-row ch-sorts" id="chSortsM" role="group" aria-label="排序"></div>
    <section class="rk-card ch-tcard">
      <table class="ch-t">
        <thead><tr id="chHead"></tr></thead>
        <tbody id="chRows"></tbody>
      </table>
      <p class="rk-note ch-tnote">冠军数相同时依次比较大满贯 › 年终总决赛 › 合赛/双周 1000 › 单周 1000 › 奥运会 › 500 › 250 的冠军数，奥运年的蒙特利尔 / 多伦多、辛辛那提按单周计；全部相同则名次并列 · 点击用户名查看全部冠军记录</p>
    </section>
  </div>

  <div class="rk-card ch-empty" id="chEmpty" hidden><p>这个筛选下没有冠军记录</p><button type="button" class="rk-btn rk-btn-pri" id="chReset">清除筛选</button></div>
  <div class="rk-card ch-none" id="chNone" hidden>{_CUP}<span class="rk-eye ch-eye-t">No titles yet</span>
    <h2>{html.escape(_PAGES[tour][0].split(' ')[0])} 还没有冠军记录</h2><p>第一站结束后这里会出现冠军名单。</p></div>

  <div class="rk-modal" id="chDlg" hidden>
    <div class="rk-dlg ch-dlg" role="dialog" aria-modal="true" aria-labelledby="chDlgName" tabindex="-1">
      <div class="rk-dlg-hd">
        <div class="rk-dlg-ttl"><span class="rk-eye rk-eye-tour">Titles · {html.escape(tour if tour != "ALL" else "ATP + WTA")}</span>
          <h2 id="chDlgName"></h2><span class="ch-dlg-sum" id="chDlgSum"></span></div>
        <span class="rk-dlg-act"><button type="button" class="rk-star" id="chDlgStar" aria-haspopup="dialog" aria-expanded="false">{_STAR}</button>
          <button type="button" class="rk-x" data-close="1" aria-label="关闭">{_CLOSE}</button></span>
      </div>
      <div class="ch-dlg-head"><span>开赛周</span><span>赛事</span><span>类型</span></div>
      <div class="ch-dlg-list" id="chDlgList"></div>
      <div class="rk-hist-ft"><span class="rk-note">不受当前筛选影响，列出全部冠军 · 点击空白处或按 Esc 关闭</span></div>
    </div>
  </div>
  <div class="rk-pop rk-picker" id="rkPicker" role="dialog" aria-label="加入哪个列表" hidden></div>
  {help_modal_html(title, steps=_help_steps(tour))}
</div>"""

    title_extra = (help_button_html()
                   + f'<span class="ch-hint">点击【<span class="ch-hint-ic" role="img" aria-label="使用说明图标">{_HELP_ICON}</span>】查看页面介绍</span>')
    html_str = _inner_page_shell(
        page_title=title,
        title=title,
        tour="",
        eyebrow=eyebrow,
        updated=updated,
        extra_tags=None,
        body_content=body,
        extra_css=CSS_RANK + "\n" + CSS_CHAMPION,
        page=str(output_path),
        late_js=JS_CHAMPION,
        title_extra=title_extra,
    )
    Path(output_path).write_text(html_str, encoding="utf-8")
    return html_str


CSS_CHAMPION = """\
.rk[data-tour="ALL"],.rk-modal[data-tour="ALL"]{--tour:var(--me);}
body:has(.ch[data-tour="ATP"]) .page-header{--tour:var(--secondary);}
body:has(.ch[data-tour="WTA"]) .page-header{--tour:var(--primary);}
body:has(.ch[data-tour="ALL"]) .page-header{--tour:#1c3f94;}
body.dark:has(.ch[data-tour="ALL"]) .page-header{--tour:#8fb0ff;}
.page-eye{color:var(--tour,var(--primary));}
.ch,.rk-modal,.rk-picker{--atp:var(--secondary);--wta:var(--primary);--atp-ink:color-mix(in srgb,var(--secondary) 62%,var(--ink));
    --wta-ink:var(--primary-dark);}
.page-title .ttag:empty{display:none;}
.ch-hint{flex-basis:100%;font-family:'Noto Sans SC',sans-serif;font-size:13px;font-weight:400;color:var(--muted);
    display:inline-flex;align-items:center;}
.ch-hint-ic{display:inline-flex;color:var(--me,#1c3f94);}
body.dark .ch-hint-ic{color:#8fb0ff;}

/* filter card */
.ch-bar-top{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 20px;border-bottom:1px solid var(--border2);}
.ch-views{display:flex;gap:4px;padding:4px;background:var(--surface2);border:1px solid var(--border);border-radius:999px;}
.ch-views button{min-height:36px;padding:0 18px;border:0;border-radius:999px;background:transparent;color:var(--muted);font-size:13px;font-weight:700;
    display:inline-flex;align-items:center;gap:6px;transition:background-color .18s,color .18s;}
.ch-views button[aria-selected="true"]{background:var(--me);color:#fff;}
body.dark .ch-views button[aria-selected="true"]{color:#06142a;}
.ch-views .n{font-family:'Space Mono',monospace;font-weight:400;opacity:.75;}
.ch-follow{display:inline-flex;align-items:center;gap:6px;min-height:36px;}
.ch-follow .rk-star-ic svg{fill:none;stroke:var(--star);}
.ch .rk-chip.ch-follow[aria-pressed="true"]{background:var(--star-dim);border-color:var(--star);color:var(--ink);}
.ch-follow[aria-pressed="true"] .rk-star-ic svg{fill:var(--star);}
.ch-search{display:flex;align-items:center;gap:8px;min-height:36px;padding:0 14px;border:1px solid var(--border);border-radius:999px;color:var(--muted);
    background:var(--drop-bg);}
.ch-search[hidden]{display:none;}
.ch-search input{border:0;outline:0;background:transparent;font:inherit;font-size:13px;color:var(--ink);width:130px;min-width:0;}
.ch-search:focus-within{border-color:var(--me);}
.ch-count{margin-left:auto;font-size:13px;color:var(--muted);}
.ch-count b{font-family:'Space Mono',monospace;color:var(--ink);}
.ch-filters{padding:12px 20px;display:flex;flex-direction:column;gap:10px;}
.ch-frow{display:flex;align-items:center;gap:10px;min-width:0;}
.ch-flbl{width:44px;flex-shrink:0;font-size:12px;font-weight:700;color:var(--muted);}
.ch .rk-chip{min-height:36px;font-size:13px;}

/* level badges: drawn from data-lv so list text stays plain */
.ch-lv{display:inline-flex;align-items:center;white-space:nowrap;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:700;
    border:1px solid transparent;background:var(--surface2);color:var(--ink2);}
.ch-lv[data-lv="大满贯"]{background:var(--th-bg);border-color:var(--th-bg);color:#fff;}
.ch-lv[data-lv="年终总决赛"]{background:var(--star-dim);border-color:var(--star-rim);color:var(--ink);}
.ch-lv[data-lv="1000"]{background:var(--primary-dim);border-color:var(--primary-rim);color:var(--primary-dark);}
.ch-lv[data-lv="奥运会"]{background:var(--surface);border-color:var(--me-rim);color:var(--me);}
.ch-lv[data-lv="250"]{background:var(--surface);border-color:var(--border);color:var(--muted);font-weight:500;}
.ch-lv b{font-family:'Space Mono',monospace;margin-left:4px;}
.ch-tt{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;padding:1px 6px;border-radius:4px;color:#fff;background:var(--wta);}
.ch-tt[data-t="A"]{background:var(--atp);color:#051420;}

/* event cards */
.ch-evs{display:flex;flex-direction:column;gap:12px;}
.ch-evs[hidden],.ch-players[hidden],.ch-empty[hidden],.ch-none[hidden],.ch-bar[hidden]{display:none;}
.ch-ev{border-top:3px solid var(--wta);overflow:hidden;transition:transform .2s ease-out,box-shadow .2s ease-out;}
.ch-ev[data-t="A"]{border-top-color:var(--atp);}
.ch-ev h3{margin:0;font:inherit;}
.ch-ev-hd{width:100%;min-height:60px;padding:10px 20px;border:0;background:transparent;color:inherit;text-align:left;
    display:grid;grid-template-columns:minmax(0,1fr) auto auto 20px;gap:14px;align-items:center;}
.ch-ev-t{display:flex;flex-direction:column;gap:2px;min-width:0;}
.ch-ev-eye{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.16em;color:var(--wta-ink);}
.ch-ev[data-t="A"] .ch-ev-eye{color:var(--atp-ink);}
.ch-ev-name{font-family:'Noto Serif SC',serif;font-size:18px;font-weight:700;color:var(--ink);}
.ch-ev-n{font-size:13px;color:var(--muted);white-space:nowrap;}
.ch-ev-n b{font-family:'Space Mono',monospace;font-size:15px;color:var(--ink);}
.ch-chev{color:var(--muted);transition:transform .2s ease-out;}
.ch-ev-hd[aria-expanded="true"] .ch-chev{transform:rotate(180deg);}
.ch-ev-body{padding:4px 20px 16px;display:flex;flex-wrap:wrap;gap:8px;animation:rkPop .18s ease-out both;}
.ch-ev-body[hidden]{display:none;}
.ch-chip{min-height:40px;padding:0 14px 0 6px;border-radius:999px;border:1px solid var(--border);background:var(--surface);color:var(--ink);
    font-size:13px;display:inline-flex;align-items:center;gap:8px;}
.ch-chip:hover{border-color:var(--primary-rim);}
.ch-chip i{font-style:normal;min-width:26px;height:26px;border-radius:999px;background:var(--surface2);font-family:'Space Mono',monospace;
    font-size:12px;color:var(--muted);display:inline-flex;align-items:center;justify-content:center;}
.ch-chip[data-fav]{border-color:var(--star-rim);}
.ch-chip[data-fav]::after{content:"★";color:var(--star);font-size:12px;}
.ch-chip[data-me]{border-color:var(--me);background:var(--me-dim);font-weight:700;}
.ch-chip[data-me]::after{content:"我";font-size:11px;font-weight:700;padding:1px 7px;border-radius:999px;background:var(--me);color:#fff;}
body.dark .ch-chip[data-me]::after{color:#06142a;}

/* podium */
.ch-podium{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;}
.ch-podium:empty{display:none;}
.ch-pod{font:inherit;color:inherit;text-align:left;border-top:3px solid var(--rank1);padding:18px 20px;display:flex;flex-direction:column;gap:10px;
    transition:transform .2s ease-out,box-shadow .2s ease-out;min-width:0;}
.ch-pod:nth-child(2){border-top-color:var(--rank2);}
.ch-pod:nth-child(3){border-top-color:var(--rank3);}
.ch-pod[data-me]{border-color:var(--me-rim);box-shadow:inset 3px 0 0 var(--me);}
.ch-pod-top{display:flex;justify-content:space-between;align-items:center;gap:8px;}
.ch-pod-no{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.2em;color:var(--muted);}
.ch-pod-tours{display:flex;gap:4px;}
.ch-pod-tours span{font-size:11px;font-weight:700;padding:1px 7px;border-radius:999px;background:var(--primary-dim);color:var(--wta-ink);}
.ch-pod-tours span:first-child{background:var(--secondary-dim);color:var(--atp-ink);}
.ch-pod-name{display:flex;align-items:center;gap:8px;min-width:0;font-family:'Noto Serif SC',serif;font-size:20px;font-weight:700;}
.ch-pod-name span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.ch-pod-n{display:flex;align-items:baseline;gap:6px;font-size:13px;color:var(--muted);}
.ch-pod-n b{font-family:'Space Mono',monospace;font-size:36px;line-height:1;color:var(--ink);}
.ch-pod-last{font-size:12px;color:var(--muted);border-top:1px solid var(--border2);padding-top:8px;}
.ch-me::after{content:"我";flex-shrink:0;font-family:'Noto Sans SC',sans-serif;font-size:11px;font-weight:700;padding:1px 7px;border-radius:999px;
    background:var(--me);color:#fff;}
body.dark .ch-me::after{color:#06142a;}
.ch-tags::after{content:attr(data-t);font-size:11px;color:var(--atp-ink);white-space:nowrap;}

/* ranking table */
.ch-sorts{display:none;}
.ch-tcard{overflow:hidden;}
.ch-t{width:100%;border-collapse:collapse;font-size:14px;table-layout:fixed;}
.ch-t th{background:var(--th-bg);color:#fff;font-size:12px;font-weight:700;text-align:left;padding:0 10px;height:44px;}
.ch-t .c-star{width:44px;}.ch-t .c-rank{width:56px;}.ch-t th.c-n{width:96px;}.ch-t th.c-lv{width:76px;text-align:center;}
.ch-t th.c-last{width:22%;}.ch-t .c-strip{display:none;}
.ch-t td.c-lv{text-align:center;}
.ch-t th.c-lv button{justify-content:center;white-space:nowrap;}
.ch-t th button{font:inherit;border:0;background:transparent;color:var(--th-text,#9cbdd4);min-height:44px;padding:0;cursor:pointer;
    display:inline-flex;align-items:center;gap:4px;}
.ch-t th[aria-sort="descending"] button{color:#fff;}
.ch-t th[aria-sort="descending"] button::after{content:"↓";}
.ch-t td{padding:6px 10px;border-top:1px solid var(--border2);vertical-align:middle;}
.ch-t tbody tr{transition:background-color .15s;}
.ch-t tbody tr:hover{background:var(--row-hover);}
.ch-t tr[data-me]{background:var(--me-dim);box-shadow:inset 3px 0 0 var(--me);}
.ch-rank{font-family:'Space Mono',monospace;font-weight:700;}
.ch-user{display:flex;align-items:center;gap:8px;min-width:0;}
.ch-uname{font:inherit;font-weight:500;color:var(--ink);border:0;background:transparent;padding:0;min-height:36px;min-width:0;cursor:pointer;
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:underline;text-decoration-color:var(--primary-rim);text-underline-offset:3px;}
.ch-n{display:flex;flex-direction:column;gap:1px;}
.ch-n b{font-family:'Space Mono',monospace;font-size:16px;}
.ch-aw{font-family:'Space Mono',monospace;font-size:11px;color:var(--muted);white-space:nowrap;}
.ch-aw i{font-style:normal;font-weight:700;color:var(--atp-ink);}
.ch-aw i+i,.ch-aw .w{color:var(--wta-ink);}
/* level columns: label once (header / small label), the cell holds only the count */
.ch-sw{width:8px;height:8px;border-radius:2px;flex-shrink:0;background:var(--surface2);border:1px solid var(--border);}
.ch-sw[data-lv="大满贯"]{background:#fff;border-color:#fff;}
.ch-sw[data-lv="年终总决赛"]{background:var(--star-dim);border-color:var(--star);}
.ch-sw[data-lv="1000"]{background:var(--primary-dim);border-color:var(--primary);}
.ch-sw[data-lv="奥运会"]{border-color:var(--me);}
.ch-cnt,.ch-sc{--lv-bg:var(--surface2);--lv-fg:var(--ink2);}
[data-lv="大满贯"]{--lv-bg:rgba(0,45,68,.10);--lv-fg:var(--ink);}
body.dark [data-lv="大满贯"]{--lv-bg:rgba(221,238,248,.12);}
[data-lv="年终总决赛"]{--lv-bg:var(--star-dim);--lv-fg:var(--atp-ink);}
[data-lv="1000"]{--lv-bg:var(--primary-dim);--lv-fg:var(--primary-dark);}
[data-lv="奥运会"]{--lv-bg:var(--me-dim);--lv-fg:var(--me);}
[data-lv="250"]{--lv-bg:var(--surface2);--lv-fg:var(--muted);}
.ch-cnt{display:inline-flex;align-items:center;justify-content:center;min-width:36px;height:30px;border-radius:8px;
    font-family:'Space Mono',monospace;font-size:15px;font-weight:700;background:var(--lv-bg);color:var(--lv-fg);}
.ch-cnt.z,.ch-sc.z{background:transparent;color:var(--faint,var(--muted));font-weight:400;}
.ch-strip{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);border:1px solid var(--border2);border-radius:10px;overflow:hidden;}
.ch-sc{display:flex;flex-direction:column;align-items:center;gap:2px;padding:6px 2px;background:var(--lv-bg);color:var(--lv-fg);min-width:0;}
.ch-sc+.ch-sc{border-left:1px solid var(--border2);}
.ch-sc small{font-size:11px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;}
.ch-sc b{font-family:'Space Mono',monospace;font-size:18px;line-height:1.1;}
.ch-sc.z small{color:var(--muted);font-weight:500;}
.ch-last{display:flex;flex-direction:column;gap:1px;min-width:0;}
.ch-last span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.ch-last small{font-family:'Space Mono',monospace;font-size:11px;color:var(--muted);}
.ch-tnote{margin:0;padding:12px 20px;border-top:1px solid var(--border2);}
.ch-empty,.ch-none{padding:40px;display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center;color:var(--muted);font-size:14px;}
.ch-empty{border-style:dashed;}
.ch-empty p,.ch-none p{margin:0;line-height:1.6;}
.ch-none{border-top:3px solid var(--tour);color:var(--muted);}
.ch-none svg{color:var(--tour);}
.ch-none h2{margin:0;font-family:'Noto Serif SC',serif;font-size:20px;color:var(--ink);}
.ch-eye-t{color:var(--tour);}

/* detail dialog */
.ch-dlg{border-top:3px solid var(--tour);width:min(680px,100%);}
.ch-dlg-sum{font-size:13px;color:var(--muted);}
.ch-dlg-sum b{font-family:'Space Mono',monospace;color:var(--ink);}
.ch-dlg .rk-star{margin:0;width:44px;height:44px;border:1px solid var(--border);}
.ch-dlg-head,.ch-dlg-row{display:grid;grid-template-columns:100px minmax(0,1fr) 128px;gap:12px;padding:10px 20px;align-items:center;}
.ch-dlg-head{font-size:12px;font-weight:700;color:var(--muted);background:var(--surface2);border-top:1px solid var(--border2);}
.ch-dlg-list{overflow-y:auto;}
.ch-dlg-row{font-size:14px;border-top:1px solid var(--border2);color:var(--ink);animation:rkRow .24s ease-out both;}
.ch-dlg-row .wk{font-family:'Space Mono',monospace;font-size:13px;color:var(--muted);}
.ch-dlg-row .ev{display:flex;align-items:center;gap:8px;min-width:0;font-weight:500;}
.ch-dlg-row .ch-lv{justify-self:start;}

/* guide stage pieces (the rest come from CSS_RANK) */
.hp-pod{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;}
.hp-pod span{background:var(--surface);border-radius:10px;border-top:3px solid var(--rank1);padding:8px 10px;display:flex;flex-direction:column;gap:2px;}
.hp-pod span:nth-child(2){border-top-color:var(--rank2);}.hp-pod span:nth-child(3){border-top-color:var(--rank3);}
.hp-pod em{font-style:normal;font-family:'Space Mono',monospace;font-size:11px;font-weight:700;color:var(--muted);}
.hp-pod strong{font-family:'Space Mono',monospace;font-size:22px;}
.hp-ev{background:var(--surface);border-radius:10px;border-top:3px solid var(--tour);padding:10px 12px;display:flex;flex-direction:column;gap:10px;}
.hp-ev-hd{display:flex;align-items:center;gap:10px;}
.hp-ev-hd b{font-family:'Noto Serif SC',serif;font-size:16px;margin-right:auto;}
.hp-ev-hd em{font-style:normal;color:var(--muted);}
.hp-ev-chips{display:flex;gap:6px;flex-wrap:wrap;animation:hpMenu 2.4s ease-in-out infinite;}
.hp-ev-chips .hp-chip{padding-left:4px;gap:6px;}
.hp-ev-chips i{font-style:normal;width:22px;height:22px;border-radius:50%;background:var(--surface2);font-family:'Space Mono',monospace;font-size:11px;
    display:inline-flex;align-items:center;justify-content:center;}
.hp-menu-r{left:auto;right:16px;top:auto;bottom:14px;width:220px;}
.hp-menu-r span{color:var(--muted);}
.hp-tiers{gap:4px;font-size:11px;color:var(--muted);}
.hp-tiers span{padding:3px 8px;border-radius:999px;background:var(--surface);border:1px solid var(--border);color:var(--ink);font-weight:700;}
.hp-tiers span:first-child{background:var(--th-bg);border-color:var(--th-bg);color:#fff;}

@media(hover:hover){.ch-ev:hover,.ch-pod:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(5,20,32,.08);}}
@media(max-width:720px){
    .ch-hint{font-size:13px;}
    .ch-bar-top{padding:10px 12px;gap:8px;}
    .ch-views{flex:1;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));}
    .ch-views button{min-height:40px;justify-content:center;font-size:14px;}
    .ch .ch-follow{width:44px;height:44px;padding:0;justify-content:center;font-size:0;gap:0;}
    .ch-follow .rk-star-ic svg{width:18px;height:18px;}
    .ch-search{order:3;flex:1 0 100%;min-height:44px;}
    .ch-search input{width:auto;flex:1;font-size:15px;}
    .ch-count{order:4;flex:1 0 100%;margin-left:0;font-size:12px;}
    .ch-filters{padding:10px 0 10px 12px;gap:6px;}
    .ch-frow .rk-chip-row{-webkit-mask-image:linear-gradient(90deg,#000 85%,transparent);mask-image:linear-gradient(90deg,#000 85%,transparent);
        padding-right:24px;}
    .ch-flbl{width:36px;}
    .ch .rk-chip{min-height:44px;}
    .ch-ev-hd{padding:10px 14px;grid-template-columns:minmax(0,1fr) auto 20px;gap:4px 10px;}
    .ch-ev-hd .ch-lv{grid-column:1;grid-row:2;justify-self:start;}
    .ch-ev-n{grid-column:2;grid-row:1/3;}
    .ch-chev{grid-column:3;grid-row:1/3;}
    .ch-ev-body{padding:4px 14px 14px;}
    .ch-chip{min-height:44px;}
    .ch-podium{grid-template-columns:minmax(0,1fr);gap:10px;}
    .ch-pod{padding:14px 16px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 12px;}
    .ch-pod-top,.ch-pod .ch-strip,.ch-pod-last{grid-column:1/-1;}
    .ch-pod-n{grid-column:2;grid-row:2;}
    .ch-pod-n b{font-size:30px;}
    .ch-pod-name{font-size:18px;}
    .ch-sorts{display:flex;flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;}
    .ch-tcard{background:transparent;border:0;overflow:visible;}
    .ch-t,.ch-t tbody{display:block;}
    .ch-t thead{display:none;}
    .ch-t tbody{display:flex;flex-direction:column;gap:10px;}
    .ch-t tr{display:grid;grid-template-columns:28px minmax(0,1fr) auto 44px;gap:4px 8px;align-items:center;padding:6px 6px 12px 12px;
        background:var(--surface);border:1px solid var(--border);border-radius:12px;}
    .ch-t tr[data-me]{border-color:var(--me-rim);}
    .ch-t td{display:block;padding:0;border:0;min-width:0;}
    .ch-t td.c-star{grid-column:4;grid-row:1;}
    .ch-t td.c-rank{grid-column:1;grid-row:1;color:var(--muted);}
    .ch-t td.c-user{grid-column:2;grid-row:1;}
    .ch-t td.c-n{grid-column:3;grid-row:1;}
    .ch-t td.c-lv{display:none;}
    .ch-t td.c-strip{display:block;grid-column:2/-1;grid-row:2;padding-right:6px;}
    .ch-t td.c-last{grid-column:2/-1;grid-row:3;}
    .ch-sc{padding:4px 0;}
    .ch-sc b{font-size:15px;}
    .ch-uname{font-size:16px;font-weight:700;min-height:44px;}
    .ch-n{flex-direction:row;align-items:baseline;gap:6px;}
    .ch-n b{font-size:20px;}
    .ch-n b::after{content:" 冠";font-family:'Noto Sans SC',sans-serif;font-size:12px;font-weight:400;color:var(--muted);}
    .ch-last{flex-direction:row;gap:8px;font-size:12px;color:var(--muted);}
    .ch-t .rk-star{width:44px;height:44px;margin:0;}
    .ch-tnote{padding:4px 0 0;border:0;}
    .ch-dlg-head{display:none;}
    .ch-dlg-row{grid-template-columns:minmax(0,1fr) auto;gap:4px 12px;padding:12px 16px;}
    .ch-dlg-row .wk{grid-column:1/-1;grid-row:2;font-size:12px;}
    .ch-empty,.ch-none{padding:32px 20px;}
}
@media(prefers-reduced-motion:reduce){.ch *{animation:none !important;transition:none !important;}}"""


JS_CHAMPION = r"""
(function(){
function ready(fn){ if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',fn); else fn(); }
ready(function(){
  const root=document.getElementById('ch'); if(!root) return;
  let D; try{ D=JSON.parse(document.getElementById('chData').textContent); }catch(e){ return; }
  const TOUR=D.tour, ALL=TOUR==='ALL', E=D.events, U=D.users;
  const KEY='ts.watch.v1', HELP_KEY='ts.help.champ.v1';
  const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const still=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $=id=>document.getElementById(id);

  // ── watch lists (shared with the ranking page; storage throws on data: URLs) ──
  function load(){ try{ const v=JSON.parse(localStorage.getItem(KEY)||'null'); if(v&&Array.isArray(v.lists)) return v; }catch(e){} return {me:'',lists:[]}; }
  let S=load();
  function save(){ try{ localStorage.setItem(KEY,JSON.stringify(S)); }catch(e){} }
  const tagsOf=u=>S.lists.filter(l=>l.users.includes(u)).map(l=>l.name);
  const isFav=u=>S.lists.some(l=>l.users.includes(u));

  // ── levels ──
  const ORDER=['大满贯','年终总决赛','1000','奥运会','500','250'];
  const lab=(lv,t)=>(!ALL&&(lv==='1000'||lv==='500'||lv==='250'))?(t==='A'?'ATP':'WTA')+lv:lv;
  const badge=(lv,t,n)=>'<span class="ch-lv" data-lv="'+esc(lv)+'">'+esc(lab(lv,t))+(n!=null?'<b>'+n+'</b>':'')+'</span>';
  const tl=TOUR==='ATP'?'A':'W';
  const tourTag=t=>ALL?'<span class="ch-tt" data-t="'+t+'">'+(t==='A'?'ATP':'WTA')+'</span>':'';
  const key=e=>e[0]+'|'+e[1]+'|'+e[3];

  if(!E.length){ $('chBar').hidden=true; $('chEvents').hidden=true; $('chNone').hidden=false; }

  // ── state ──
  const st={view:'events', season:'all', lv:'all', tf:'all', follow:false, q:'', sort:'titles'};
  const open=new Set(); let touched=false;

  // ── chips ──
  const seasons=[...new Set(E.map(e=>e[2]))].sort((a,b)=>b-a);
  const levels=ORDER.filter(l=>E.some(e=>e[4]===l));
  function chips(box,opts,cur,k){
    box.innerHTML=opts.map(([v,l])=>'<button type="button" class="rk-chip" data-k="'+k+'" data-v="'+esc(v)+'" aria-pressed="'+(String(cur)===String(v))+'">'+esc(l)+'</button>').join('');
  }
  function renderChips(){
    chips($('chSeasons'),[['all','全部']].concat(seasons.map(s=>[s,String(s)])),st.season,'season');
    chips($('chLevels'),[['all','全部']].concat(levels.map(l=>[l,lab(l,tl)])),st.lv,'lv');
    if(ALL) chips($('chTours'),[['all','全部'],['A','ATP'],['W','WTA']],st.tf,'tf');
    chips($('chSortsM'),[['titles','冠军数'],['last','最近夺冠'],['level','最高级别']],st.sort,'sort');
    $('chHead').innerHTML='<th scope="col" class="c-star"><span class="rk-sr">关注</span></th><th scope="col" class="c-rank">排名</th><th scope="col" class="c-user">用户名</th>'
      +sortTh('titles','冠军数','c-n')
      +levels.map(l=>sortTh('lv:'+l,'<i class="ch-sw" data-lv="'+esc(l)+'"></i>'+esc(lab(l,tl)),'c-lv',lab(l,tl)+' 冠军数')).join('')
      +sortTh('last','最近夺冠','c-last');
  }
  root.addEventListener('click',e=>{
    const b=e.target.closest('.rk-chip[data-k]'); if(!b) return;
    const k=b.dataset.k, v=b.dataset.v; st[k]=(k==='season'&&v!=='all')?parseInt(v,10):v; renderChips(); render();
  });
  function sortTh(k,label,cls,aria){ const on=st.sort===k;
    return '<th scope="col" class="'+cls+'" aria-sort="'+(on?'descending':'none')+'"><button type="button" data-sort="'+esc(k)+'"'+(aria?' aria-label="按'+esc(aria)+'排序"':'')+'>'+label+'</button></th>'; }
  $('chHead').addEventListener('click',e=>{ const b=e.target.closest('button[data-sort]'); if(!b) return; st.sort=b.dataset.sort; renderChips(); render(); });

  // ── aggregate ──
  function filtered(){
    return E.filter(e=>(st.tf==='all'||e[0]===st.tf)&&(st.season==='all'||e[2]===st.season)&&(st.lv==='all'||e[4]===st.lv));
  }
  function tie(a,b){ for(let t=7;t>=1;t--){ if(a.tv[t]!==b.tv[t]) return b.tv[t]-a.tv[t]; } return 0; }
  function aggregate(evs){
    const P={};
    evs.forEach(e=>e[6].forEach(id=>{
      const p=P[id]||(P[id]={id, name:U[id]||String(id), titles:0, a:0, w:0, by:{}, tv:[0,0,0,0,0,0,0,0], top:0, last:null});
      p.titles++; e[0]==='A'?p.a++:p.w++; p.by[e[4]]=(p.by[e[4]]||0)+1; p.tv[e[5]]++; if(e[5]>p.top){ p.top=e[5]; p.topLv=e[4]; p.topT=e[0]; }
      if(!p.last) p.last=e; }));
    const ps=Object.values(P).sort((a,b)=>b.titles-a.titles||tie(a,b)||b.last[3].localeCompare(a.last[3]));
    ps.forEach((p,i)=>{ const q=ps[i-1]; p.rank=i&&q.titles===p.titles&&tie(q,p)===0?q.rank:i+1; });
    return ps;
  }
  // one cell per level on the page: the level is labelled once, the cell only holds the count
  const strip=p=>'<span class="ch-strip">'+levels.map(l=>{ const n=p.by[l]||0;
    return '<span class="ch-sc'+(n?'':' z')+'" data-lv="'+esc(l)+'"><small>'+esc(lab(l,tl))+'</small><b>'+(n||'–')+'</b></span>'; }).join('')+'</span>';
  const cnt=(p,l)=>{ const n=p.by[l]||0; return '<span class="ch-cnt'+(n?'':' z')+'" data-lv="'+esc(l)+'">'+(n||'–')+'</span>'; };
  const lastText=e=>(ALL?(e[0]==='A'?'ATP ':'WTA '):'')+e[2]+' '+e[1];

  // ── render ──
  function nameCell(p){
    const me=p.name===S.me, t=tagsOf(p.name);
    return '<span class="ch-user"><button type="button" class="ch-uname'+(me?' ch-me':'')+'" data-u="'+p.id+'" aria-haspopup="dialog">'+esc(p.name)+'</button>'
      +'<span class="ch-tags" data-t="'+esc(t.map(x=>'★'+x).join(' '))+'"></span></span>';
  }
  function render(){
    if(!E.length) return;
    const base=filtered();
    const followSet=u=>u===S.me||isFav(u);
    const evs=st.follow?base.filter(e=>e[6].some(id=>followSet(U[id]))):base;
    const all=aggregate(base);
    let rows=st.follow?all.filter(p=>followSet(p.name)):all;
    if(st.q){ const q=st.q.toLowerCase(); rows=rows.filter(p=>p.name.toLowerCase().includes(q)); }
    const k=st.sort;
    rows=rows.slice().sort((a,b)=>k==='last'?b.last[3].localeCompare(a.last[3])||a.rank-b.rank:k==='level'?b.top-a.top||a.rank-b.rank:k.indexOf('lv:')===0?(b.by[k.slice(3)]||0)-(a.by[k.slice(3)]||0)||a.rank-b.rank:a.rank-b.rank);
    $('chNE').textContent=evs.length; $('chNP').textContent=all.length;
    const isE=st.view==='events';
    $('chTabE').setAttribute('aria-selected',isE); $('chTabP').setAttribute('aria-selected',!isE);
    $('chSearch').hidden=isE;
    $('chFollow').setAttribute('aria-pressed',st.follow);
    $('chCount').innerHTML=isE?'显示 <b>'+evs.length+'</b> / '+E.length+' 场赛事'
      :'显示 <b>'+rows.length+'</b> / '+all.length+' 位冠军 · '+base.length+' 场赛事';
    const empty=isE?!evs.length:!rows.length;
    $('chEmpty').hidden=!empty;
    $('chEvents').hidden=!isE||empty; $('chPlayers').hidden=isE||empty;
    if(isE&&!empty) renderEvents(evs); else if(!isE&&!empty) renderPlayers(all,rows);
  }
  const CHEV='<svg class="ch-chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
  function renderEvents(evs){
    if(!touched&&!open.size) open.add(key(evs[0]));
    $('chEvents').innerHTML=evs.map((e,i)=>{ const k=key(e), on=open.has(k), id='chEv'+i;
      return '<article class="rk-card ch-ev" data-t="'+e[0]+'"><h3><button type="button" class="ch-ev-hd" data-ev="'+esc(k)+'" aria-expanded="'+on+'" aria-controls="'+id+'">'
        +'<span class="ch-ev-t"><span class="ch-ev-eye">'+(ALL?(e[0]==='A'?'ATP':'WTA')+' · ':'')+e[2]+' · '+e[3].slice(5)+'</span><span class="ch-ev-name">'+esc(e[1])+'</span></span>'
        +badge(e[4],e[0])+'<span class="ch-ev-n"><b>'+e[6].length+'</b> 位冠军</span>'+CHEV+'</button></h3>'
        +'<div class="ch-ev-body" id="'+id+'"'+(on?'':' hidden')+'>'+e[6].map((uid,j)=>{ const n=U[uid]||String(uid);
          return '<button type="button" class="ch-chip" data-u="'+uid+'" aria-haspopup="dialog"'+(n===S.me?' data-me':'')+(isFav(n)?' data-fav':'')+'><i>'+(j+1)+'</i>'+esc(n)+'</button>'; }).join('')
        +'</div></article>'; }).join('');
  }
  function renderPlayers(all,rows){
    const pod=(st.q||st.follow)?[]:all.slice(0,3);
    $('chPodium').innerHTML=pod.map(p=>'<button type="button" class="rk-card ch-pod" data-u="'+p.id+'" aria-haspopup="dialog"'+(p.name===S.me?' data-me':'')+'>'
      +'<span class="ch-pod-top"><span class="ch-pod-no">NO.'+p.rank+'</span>'+(ALL?'<span class="ch-pod-tours"><span>ATP '+p.a+'</span><span>WTA '+p.w+'</span></span>':'')+'</span>'
      +'<span class="ch-pod-name"><span class="'+(p.name===S.me?'ch-me':'')+'">'+esc(p.name)+'</span></span>'
      +'<span class="ch-pod-n"><b>'+p.titles+'</b>冠</span>'+strip(p)
      +'<span class="ch-pod-last">最近夺冠 · '+esc(lastText(p.last))+' · '+esc(lab(p.last[4],p.last[0]))+'</span></button>').join('');
    $('chRows').innerHTML=rows.map(p=>{ const fav=isFav(p.name);
      return '<tr'+(p.name===S.me?' data-me':'')+'><td class="c-star"><button type="button" class="rk-star'+(fav?' on':'')+'" data-star="'+p.id+'" aria-haspopup="dialog" aria-expanded="false" aria-label="关注 '+esc(p.name)+'">'+STAR+'</button></td>'
        +'<td class="ch-rank c-rank">'+p.rank+'</td><td class="c-user">'+nameCell(p)+'</td>'
        +'<td class="c-n"><span class="ch-n"><b>'+p.titles+'</b>'+(ALL?'<span class="ch-aw"><i>A</i>'+p.a+' · <i class="w">W</i>'+p.w+'</span>':'')+'</span></td>'
        +levels.map(l=>'<td class="c-lv">'+cnt(p,l)+'</td>').join('')
        +'<td class="c-strip">'+strip(p)+'</td>'
        +'<td class="c-last"><span class="ch-last"><span>'+esc(lastText(p.last))+'</span><small>'+p.last[3]+'</small></span></td></tr>'; }).join('');
  }
  const STAR=document.querySelector('#chFollow svg').outerHTML;

  // ── view / follow / search / reset ──
  [$('chTabE'),$('chTabP')].forEach(b=>b.addEventListener('click',()=>{ st.view=b.dataset.v; render(); }));
  $('chFollow').addEventListener('click',()=>{ st.follow=!st.follow; render(); });
  $('chQ').addEventListener('input',e=>{ st.q=e.target.value.trim(); render(); });
  $('chReset').addEventListener('click',()=>{ Object.assign(st,{season:'all',lv:'all',tf:'all',follow:false,q:''}); $('chQ').value=''; renderChips(); render(); });
  $('chEvents').addEventListener('click',e=>{
    const h=e.target.closest('.ch-ev-hd'); if(!h) return; touched=true;
    const k=h.dataset.ev, on=h.getAttribute('aria-expanded')!=='true';
    on?open.add(k):open.delete(k); h.setAttribute('aria-expanded',on); $(h.getAttribute('aria-controls')).hidden=!on;
  });

  // ── dialogs (focus trap, Esc, backdrop) ──
  let lastFocus=null;
  function openModal(m,from){ lastFocus=from||document.activeElement; m.hidden=false; document.body.style.overflow='hidden'; m.querySelector('.rk-dlg').focus(); }
  function closeModal(m){ if(m.hidden) return; m.hidden=true; document.body.style.overflow=''; if(m.id==='rkHelp') stopHelp(); closePicker();
    if(lastFocus&&lastFocus.focus) lastFocus.focus({preventScroll:true}); }
  [...root.querySelectorAll('.rk-modal')].forEach(m=>{
    m.dataset.tour=TOUR; document.body.appendChild(m);
    m.addEventListener('click',e=>{ if(e.target===m||e.target.closest('[data-close]')) closeModal(m); });
    m.addEventListener('keydown',e=>{
      if(e.key==='Escape'){ e.stopPropagation(); if(!picker.hidden) closePicker(); else closeModal(m); return; }
      if(e.key!=='Tab') return;
      const f=[...m.querySelectorAll('button:not([disabled]),[href],input')].filter(x=>x.offsetParent!==null);
      if(!f.length) return; const a=f[0], z=f[f.length-1];
      if(e.shiftKey&&document.activeElement===a){ e.preventDefault(); z.focus(); }
      else if(!e.shiftKey&&document.activeElement===z){ e.preventDefault(); a.focus(); }
    });
  });

  // ── champion detail: every title of this user on this page, newest first ──
  const dlg=$('chDlg'); let dlgUser='';
  function openDetail(id,from){
    const name=U[id]||String(id), evs=E.filter(e=>e[6].includes(Number(id)));
    const by={}; evs.forEach(e=>{ by[e[4]]=(by[e[4]]||0)+1; });
    dlgUser=name;
    const h=$('chDlgName'); h.textContent=name+' 的冠军记录'; h.classList.toggle('ch-me',name===S.me);
    $('chDlgSum').innerHTML='共 <b>'+evs.length+'</b> 冠 · '+esc(ORDER.filter(l=>by[l]).map(l=>lab(l,tl)+' '+by[l]).join(' · '));
    paintDlgStar();
    $('chDlgList').innerHTML=evs.map((e,i)=>'<div class="ch-dlg-row" style="animation-delay:'+Math.min(i,12)*40+'ms"><span class="wk">'+e[3]+'</span>'
      +'<span class="ev">'+tourTag(e[0])+esc(e[2]+' '+e[1])+'</span>'+badge(e[4],e[0])+'</div>').join('');
    openModal(dlg,from);
  }
  function paintDlgStar(){ const b=$('chDlgStar'); b.classList.toggle('on',isFav(dlgUser)); b.dataset.name=dlgUser; b.setAttribute('aria-label','关注 '+dlgUser); }
  root.addEventListener('click',e=>{ const b=e.target.closest('[data-u]'); if(b) openDetail(b.dataset.u,b); });

  // ── ☆ picker (same menu as the ranking page) ──
  const picker=$('rkPicker'); let pickFor='', pickBtn=null;
  document.body.appendChild(picker);
  function openPicker(btn,name){
    if(pickBtn===btn&&!picker.hidden){ closePicker(); return; }
    pickFor=name; pickBtn=btn; renderPicker(); picker.hidden=false; btn.setAttribute('aria-expanded','true');
    const r=btn.getBoundingClientRect(), w=232;
    picker.style.left=Math.max(12,Math.min(window.scrollX+r.left,window.scrollX+document.documentElement.clientWidth-w-12))+'px';
    picker.style.top=(window.scrollY+r.bottom+6)+'px';
    picker.style.zIndex=dlg.hidden?'':'9100';
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
  function afterChange(){ save(); const y=window.scrollY; render(); if(!dlg.hidden) paintDlgStar(); window.scrollTo(0,y); }
  root.addEventListener('click',e=>{ const b=e.target.closest('[data-star]'); if(!b) return; e.stopPropagation(); openPicker(b,U[b.dataset.star]||b.dataset.star); },true);
  $('chDlgStar').addEventListener('click',e=>{ e.stopPropagation(); openPicker(e.currentTarget,dlgUser); });
  picker.addEventListener('click',e=>{ e.stopPropagation(); const b=e.target.closest('button'); if(!b) return;
    if(b.dataset.l){ const l=S.lists.find(x=>x.id===b.dataset.l); const i=l.users.indexOf(pickFor); i<0?l.users.push(pickFor):l.users.splice(i,1); afterChange(); renderPicker(); picker.querySelector('[data-l="'+l.id+'"]').focus(); }
    else if(b.dataset.me){ S.me=S.me===pickFor?'':pickFor; afterChange(); closePicker(); } });
  picker.addEventListener('submit',e=>{ e.preventDefault(); const n=e.target.n.value.trim(); if(!n) return;
    S.lists.push({id:'l'+Date.now().toString(36),name:n,users:[pickFor]}); afterChange(); renderPicker(); });
  picker.addEventListener('keydown',e=>{ if(e.key==='Escape'){ e.stopPropagation(); closePicker(); } });
  document.addEventListener('click',e=>{ if(!picker.contains(e.target)) closePicker(); });
  window.addEventListener('resize',closePicker);
  window.addEventListener('storage',e=>{ if(e.key===KEY){ S=load(); render(); } });

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

  if(location.hash==='#players') st.view='players';
  renderChips(); render();
});
})();
"""
