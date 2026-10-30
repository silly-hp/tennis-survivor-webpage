"""Survivor calendar + per-event score detail page renderers."""
from __future__ import annotations

from pathlib import Path

from site_html.calendar_list import render_calendar_page  # noqa: F401  (re-export)
from site_html.common import _inner_page_shell
from site_html.event_page import (  # noqa: F401  (re-export)
    event_year_series_key,
    render_event_score_page,
)

_CSS_CALENDAR = """\
.filter-bar{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;padding:14px;
    background:var(--surface);border:1px solid var(--border2);border-radius:8px;
    align-items:center;}
.filter-group{display:flex;align-items:center;gap:6px;flex-wrap:wrap;}
.filter-lbl{font-family:'Space Mono',monospace;font-size:11px;color:var(--muted);
    letter-spacing:.06em;white-space:nowrap;}
.filter-chips{display:flex;gap:5px;flex-wrap:wrap;}
.filter-divider{width:1px;height:20px;background:var(--border2);flex-shrink:0;}
.fchip{font-size:11px;padding:3px 10px;border-radius:20px;cursor:pointer;
    border:1px solid var(--border);background:var(--surface2);color:var(--muted);
    transition:all .15s;white-space:nowrap;}
.fchip:hover{border-color:var(--primary-rim);color:var(--primary-dark);}
.fchip.active{background:var(--primary-dim);color:var(--primary-dark);
    border-color:var(--primary-rim);font-weight:500;}
body.dark .fchip.active{color:var(--primary);}
.result-count{font-family:'Space Mono',monospace;font-size:11px;color:var(--faint);
    margin-left:auto;}
.result-count b{color:var(--primary);}

.cal-legend{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px;
    font-size:11px;color:var(--muted);}
.cal-legend span{display:inline-flex;align-items:center;gap:6px;}

.cal-table{width:100%;border-collapse:separate;border-spacing:0 8px;}
.cal-table th{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:.12em;
    text-transform:uppercase;color:var(--faint);font-weight:500;text-align:left;
    padding:0 12px 4px;}
.cal-row{display:none;}
.cal-row.show{display:table-row;}
.cal-table td{background:var(--surface);border-top:1px solid var(--border2);
    border-bottom:1px solid var(--border2);padding:12px 14px;vertical-align:middle;}
.cal-table td:first-child{border-left:1px solid var(--border2);border-radius:8px 0 0 8px;}
.cal-table td:last-child{border-right:1px solid var(--border2);border-radius:0 8px 8px 0;}
.cal-date{font-family:'Space Mono',monospace;font-size:13px;font-weight:600;
    color:var(--ink);white-space:nowrap;width:72px;}
.cal-cells{display:flex;flex-wrap:wrap;gap:8px;}
.cal-link{display:inline-flex;align-items:center;gap:8px;padding:7px 12px;
    border-radius:6px;border:1px solid var(--border2);text-decoration:none;
    background:var(--surface2);color:var(--ink);font-size:13px;font-weight:500;
    transition:border-color .15s,transform .15s;}
.cal-link:hover{border-color:var(--primary-rim);transform:translateY(-1px);}
.cal-link.disabled{opacity:.45;pointer-events:none;cursor:default;}
.cal-link.hide{display:none;}
.cal-city{font-size:13px;font-weight:600;color:var(--ink);}
.cal-meta{font-family:'Space Mono',monospace;font-size:10px;color:var(--faint);}
.cal-empty{padding:28px 12px;color:var(--faint);font-size:13px;}
.cal-note{margin-top:16px;font-size:12px;color:var(--faint);line-height:1.7;}
.cal-note a{color:var(--muted);}

/* type pills — same palette as champion hall */
.t-type{font-size:10px;padding:2px 8px;border-radius:10px;
    font-weight:500;white-space:nowrap;}
.t-type.gs     {background:rgba(138,96,48,.10); color:#7a5020;
    border:.5px solid rgba(138,96,48,.28);}
.t-type.finals {background:rgba(100,60,160,.10);color:#5a30a0;
    border:.5px solid rgba(100,60,160,.28);}
.t-type.m1000  {background:var(--secondary-dim);color:var(--secondary);
    border:.5px solid var(--secondary-rim);}
.t-type.w1000  {background:var(--primary-dim);  color:var(--primary-dark);
    border:.5px solid var(--primary-rim);}
.t-type.m500   {background:rgba(40,86,168,.08); color:#4a6aaa;
    border:.5px solid rgba(40,86,168,.20);}
.t-type.w500   {background:rgba(224,96,64,.08); color:#b84828;
    border:.5px solid rgba(224,96,64,.20);}
.t-type.m250   {background:rgba(40,86,168,.05); color:#6a8ab8;
    border:.5px solid rgba(40,86,168,.14);}
.t-type.w250   {background:rgba(224,96,64,.05); color:#c86048;
    border:.5px solid rgba(224,96,64,.14);}
.t-type.other  {background:rgba(26,26,26,.05);  color:var(--muted);
    border:.5px solid var(--border);}
body.dark .t-type.gs     {color:#c8a060;}
body.dark .t-type.finals {color:#b090f0;}
body.dark .t-type.m500   {color:#90b8f4;}
body.dark .t-type.w500   {color:#e8806a;}
body.dark .t-type.m250   {color:#7898c8;}
body.dark .t-type.w250   {color:#d87060;}
body.dark .t-type.m1000  {color:var(--secondary);}
body.dark .t-type.w1000  {color:var(--primary);}

.score-meta{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;
    font-size:12px;color:var(--muted);align-items:center;}
.score-meta b{color:var(--ink);font-weight:600;}
.score-meta a{color:var(--muted);}

.score-stats{display:flex;flex-direction:column;gap:10px;margin-bottom:16px;}
.score-stats-row{display:grid;gap:10px;}
.score-stats-row.solo{grid-template-columns:1fr;}
.score-stats-row.pair{grid-template-columns:1fr 1fr;}
@media(max-width:640px){
    .score-stats-row.pair{grid-template-columns:1fr;}
}
.score-stat{padding:12px 14px;border:1px solid var(--border2);border-radius:8px;
    background:var(--surface);}
.score-stat-lbl{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:.1em;
    color:var(--faint);margin-bottom:6px;}
.score-stat-val{font-size:14px;font-weight:600;color:var(--ink);line-height:1.45;
    word-break:break-word;}
.score-stat-val .muted{font-weight:500;color:var(--muted);font-size:12px;}
.score-stat-val .sub{display:block;margin-top:4px;font-size:11px;font-weight:500;
    color:var(--faint);font-family:'Space Mono',monospace;}
.score-stat-val .sub + .sub{margin-top:2px;}
/* Champion / upset pickers — same chips as homepage 赛况 */
.score-stat-val .wk-chips{display:flex;flex-wrap:wrap;gap:5px;font-weight:400;}
.score-stat-val .wk-chip{display:inline-block;max-width:100%;padding:3px 9px;border-radius:999px;
    background:rgba(42,107,79,.08);border:0.5px solid rgba(42,107,79,.18);
    color:#1f4f3a;font-size:12px;line-height:1.35;font-weight:500;white-space:nowrap;
    overflow:hidden;text-overflow:ellipsis;}
body.dark .score-stat-val .wk-chip{background:rgba(125,206,160,.12);
    border-color:rgba(125,206,160,.22);color:#b7e0c6;}



.cal-hub{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;
    margin-top:8px;}
.cal-hub a{display:block;padding:20px 18px;border:1px solid var(--border2);border-radius:10px;
    background:var(--surface);text-decoration:none;color:var(--ink);
    transition:border-color .15s,transform .15s;}
.cal-hub a:hover{border-color:var(--primary-rim);transform:translateY(-1px);}
.cal-hub .eye{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:.12em;
    color:var(--faint);margin-bottom:8px;}
.cal-hub .ttl{font-family:'Noto Serif SC',serif;font-size:20px;font-weight:700;margin-bottom:6px;}
.cal-hub .desc{font-size:13px;color:var(--muted);line-height:1.5;}

@media(max-width:640px){
    .filter-divider{display:none;}
    .filter-group{width:100%;}
    .result-count{width:100%;margin-left:0;}
}
"""

def render_calendar_hub_page(
    *,
    updated: str,
    output_path: str | Path,
) -> str:
    """Legacy combined URL → choose ATP / WTA calendar."""
    body = """\
<div class="cal-hub">
  <a href="survivor_calendar_atp.html" class="atp">
    <div class="eye">ATP · MEN</div>
    <div class="ttl">ATP 幸存者赛历</div>
    <div class="desc">男单赛程 · 按年份与级别浏览，查看本站得分</div>
  </a>
  <a href="survivor_calendar_wta.html" class="wta">
    <div class="eye">WTA · WOMEN</div>
    <div class="ttl">WTA 幸存者赛历</div>
    <div class="desc">女单赛程 · 按年份与级别浏览，查看本站得分</div>
  </a>
</div>
"""
    html_str = _inner_page_shell(
        page_title="幸存者赛历",
        title="幸存者赛历",
        tour="ALL",
        eyebrow="Survivor · Calendar",
        updated=updated,
        extra_tags=["ATP", "WTA"],
        body_content=body,
        extra_css=_CSS_CALENDAR,
        page=str(output_path),
    )
    Path(output_path).write_text(html_str, encoding="utf-8")
    return html_str
