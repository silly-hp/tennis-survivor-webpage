"""Shared header for every inner page: home link, section tabs, tour switch,
update pill, theme button and back-to-top.

The active section and tour are read from the page's output filename, so
callers only pass ``page`` (the output path) and the timestamp.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from site_html.logos import _logo_pair

# section key → (tab label, {tour: filename}); no "ALL" key = no 合计 page
_SECTIONS: dict[str, tuple[str, dict[str, str]]] = {
    "live": ("即时排名", {"ATP": "atp_ranking.html", "WTA": "wta_ranking.html",
                          "ALL": "combined_instant_ranking.html"}),
    "race": ("冠军排名", {"ATP": "atp_race_ranking.html", "WTA": "wta_race_ranking.html",
                          "ALL": "combined_ranking.html"}),
    "killer": ("杀手榜", {"ATP": "atpkiller.html", "WTA": "wtakiller.html"}),
    "cal": ("赛历", {"ATP": "survivor_calendar_atp.html", "WTA": "survivor_calendar_wta.html"}),
    "career": ("生涯统计", {"ATP": "atp_show.html", "WTA": "wta_show.html"}),
    "h2h": ("H2H", {"ATP": "h2h_atp.html", "WTA": "h2h_wta.html"}),
}
_TOUR_LABEL = {"ATP": "ATP", "WTA": "WTA", "ALL": "合计"}


def _resolve(page: str) -> tuple[str, str, dict[str, str], str]:
    """Return (section, tour, {tour: href}, prefix) for an output path."""
    p = Path(page)
    name = p.name
    prefix = "../../" if "events" in p.parts else ""
    if prefix:  # events/{year}/{MS|WS}_{id}.html
        tour = "WTA" if name.startswith("WS") else "ATP"
        return "cal", tour, dict(_SECTIONS["cal"][1]), prefix
    if m := re.fullmatch(r"(\d{4})?(atp|wta)killer\.html", name):
        year = m.group(1) or ""
        links = {t: f"{year}{t.lower()}killer.html" for t in ("ATP", "WTA")}
        return "killer", m.group(2).upper(), links, prefix
    if m := re.fullmatch(r"(atp|wta)_champion\.html", name):
        links = {t: f"{t.lower()}_champion.html" for t in ("ATP", "WTA")}
        return "race", m.group(1).upper(), links, prefix
    if name == "survivor_calendar.html":  # legacy hub: no tour selected
        return "cal", "", dict(_SECTIONS["cal"][1]), prefix
    for key, (_, links) in _SECTIONS.items():
        for tour, fname in links.items():
            if fname == name:
                return key, tour, dict(links), prefix
    return "", "", {}, prefix


_SUN = ('<svg class="ic-sun" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/>'
        '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>')
_MOON = ('<svg class="ic-moon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
         '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>')
_UP = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
       'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>')


def site_header(updated: str, page: str = "", back_label: str = "← 首页",
                back_href: str = "index.html") -> str:
    """Header HTML for the page written to ``page`` (its output path)."""
    section, tour, links, prefix = _resolve(page)
    back = prefix + back_href if back_href == "index.html" else back_href
    esc = html.escape

    tabs = []
    for key, (label, sec_links) in _SECTIONS.items():
        href = links.get(tour) if key == section else None
        href = href or sec_links.get(tour) or sec_links["ATP"]
        cur = ' aria-current="page"' if key == section else ""
        tabs.append(f'<a class="hd-tab" href="{prefix}{esc(href)}"{cur}>{esc(label)}</a>')

    seg = []
    sec_label = _SECTIONS[section][0] if section else "本页"
    # pages outside the sections (watchlist.html) cover both tours: no switch
    for t in ("ATP", "WTA", "ALL") if links else ():
        label = _TOUR_LABEL[t]
        if t not in links:
            seg.append(f'<span class="hd-seg-btn" aria-disabled="true" tabindex="0" '
                       f'data-tip="{esc(sec_label)}暂无合计页">{label}</span>')
        else:
            on = ' aria-current="page"' if t == tour else ""
            seg.append(f'<a class="hd-seg-btn" href="{prefix}{esc(links[t])}"{on}>{label}</a>')

    return f"""\
<header class="site-hd">
  <a class="back-link" href="{esc(back)}">
    {_logo_pair(28)}
    {esc(back_label)}
  </a>
  <nav class="hd-tabs" aria-label="栏目">{"".join(tabs)}</nav>
  <div class="hd-right">
    {f'<div class="hd-seg" role="group" aria-label="巡回赛">{"".join(seg)}</div>' if seg else ""}
    <span class="hd-live"><span class="hd-dot"></span><span class="hd-time">{esc(updated)}</span><span class="hd-suffix"> 更新</span></span>
    <button type="button" class="theme-btn" id="themeBtn" onclick="toggleTheme()" aria-label="切换明暗">{_MOON}{_SUN}<span class="theme-label">暗色</span></button>
  </div>
</header>
<button type="button" class="to-top" id="toTop" aria-label="回到顶部" hidden>{_UP}</button>"""


CSS_HEADER = """\
.site-hd{display:flex;align-items:center;gap:20px;margin-bottom:28px;padding-bottom:14px;
    border-bottom:1px solid var(--border2);}
.site-hd .back-link{min-height:44px;flex-shrink:0;}
.hd-tabs{display:flex;gap:2px;font-size:14px;min-width:0;}
.hd-tab{display:flex;align-items:center;min-height:44px;padding:0 12px;color:var(--muted);text-decoration:none;
    white-space:nowrap;border-bottom:2px solid transparent;transition:color .15s,border-color .15s;}
.hd-tab:hover{color:var(--primary);}
.hd-tab[aria-current="page"]{color:var(--ink);font-weight:700;border-bottom-color:var(--primary);}
.hd-right{margin-left:auto;display:flex;align-items:center;gap:10px;flex-shrink:0;}
.hd-seg{display:flex;gap:3px;padding:3px;background:var(--surface2);border:1px solid var(--border);border-radius:999px;}
.hd-seg-btn{position:relative;display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:0 16px;
    border-radius:999px;font-size:13px;font-weight:700;color:var(--muted);text-decoration:none;transition:background .18s,color .18s;}
a.hd-seg-btn:hover{color:var(--primary);}
.hd-seg-btn[aria-current="page"],.hd-seg-btn[aria-current="page"]:hover{background:#1c3f94;color:#ffffff;}
.hd-seg-btn[aria-disabled="true"]{opacity:.45;cursor:not-allowed;}
.hd-seg-btn[data-tip]:hover::after,.hd-seg-btn[data-tip]:focus-visible::after{content:attr(data-tip);position:absolute;
    top:calc(100% + 8px);right:0;white-space:nowrap;background:var(--th-bg);color:#ddeef8;font-size:12px;font-weight:400;
    padding:6px 10px;border-radius:8px;z-index:30;opacity:1;}
.hd-live{display:inline-flex;align-items:center;gap:8px;min-height:40px;padding:0 14px;font-size:12px;color:var(--ink2);
    border:1px solid var(--border);border-radius:999px;background:var(--surface);white-space:nowrap;}
.hd-time{font-family:'Space Mono',monospace;}
.hd-dot{width:8px;height:8px;border-radius:50%;background:var(--primary);flex-shrink:0;animation:hdPulse 1.8s ease-out infinite;}
@keyframes hdPulse{0%{box-shadow:0 0 0 0 var(--primary-rim)}100%{box-shadow:0 0 0 9px transparent}}
.site-hd .theme-btn{display:inline-flex;align-items:center;gap:6px;min-height:40px;padding:0 14px;font-size:13px;
    color:var(--ink2);border-radius:999px;}
.theme-btn .ic-sun,body.dark .theme-btn .ic-moon{display:none;}
body.dark .theme-btn .ic-sun{display:block;}
.to-top{position:fixed;right:24px;bottom:24px;z-index:40;width:48px;height:48px;border-radius:50%;
    border:1px solid var(--border);background:var(--surface);color:var(--ink);cursor:pointer;
    box-shadow:0 6px 18px rgba(0,0,0,.14);display:flex;align-items:center;justify-content:center;
    animation:hdRise .22s ease-out both;}
.to-top[hidden]{display:none;}
.to-top:hover{border-color:var(--primary);color:var(--primary);}
@keyframes hdRise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.site-hd a:focus-visible,.site-hd button:focus-visible,.hd-seg-btn:focus-visible,.to-top:focus-visible{
    outline:2px solid var(--primary);outline-offset:2px;}

@media(max-width:1100px){
    .site-hd{flex-wrap:wrap;row-gap:6px;}
    .hd-tabs{order:3;flex:1 0 100%;overflow-x:auto;scrollbar-width:none;}
    .hd-tabs::-webkit-scrollbar{display:none;}
}
@media(max-width:720px){
    .site-hd{gap:8px;margin-bottom:18px;padding-bottom:0;}
    .hd-right{display:contents;}
    .hd-live{margin-left:auto;padding:0 10px;min-height:36px;}
    .hd-suffix{display:none;}
    .site-hd .theme-btn{width:44px;height:44px;padding:0;justify-content:center;}
    .site-hd .theme-label{display:none;}
    .hd-seg{order:2;flex:1 0 100%;}
    .hd-seg-btn{flex:1;min-height:40px;font-size:14px;}
    .hd-tabs{margin:0 -12px;padding:0 12px;
        -webkit-mask-image:linear-gradient(90deg,#000 85%,transparent);mask-image:linear-gradient(90deg,#000 85%,transparent);}
    .hd-seg-btn[data-tip]:hover::after,.hd-seg-btn[data-tip]:focus-visible::after{right:auto;left:50%;transform:translateX(-50%);}
    .to-top{right:16px;bottom:20px;}
}
@media(prefers-reduced-motion:reduce){
    .hd-dot,.to-top{animation:none;}
    .hd-tab,.hd-seg-btn{transition:none;}
}"""

# Own <script> block: kept apart from _JS_THEME (storage can throw in previews).
JS_HEADER = """\
(function(){
  const top=document.getElementById('toTop');
  if(top){
    const sync=()=>{top.hidden=window.scrollY<window.innerHeight;};
    window.addEventListener('scroll',sync,{passive:true});sync();
    top.addEventListener('click',()=>{
      const still=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({top:0,behavior:still?'auto':'smooth'});
    });
  }
  const cur=document.querySelector('.hd-tab[aria-current="page"]');
  if(cur&&cur.scrollIntoView)cur.parentNode.scrollLeft=cur.offsetLeft-24;
})();"""
