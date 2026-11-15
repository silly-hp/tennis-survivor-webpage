"""策略 page: one tour, two strategies, one year at a time."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from site_html.assets import write_page
from site_html.common import _inner_page_shell

ROOT = Path(__file__).resolve().parent.parent.parent
LABELS = (
    ("rank", "排名最高"),
    ("favorite", "最被看好"),
)

_CSS = """
.st-switch{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 14px;}
.st-switch button{min-height:40px;padding:0 16px;border-radius:999px;border:1px solid var(--border);
    background:var(--surface);color:var(--muted);font-weight:700;cursor:pointer;}
.st-switch button[aria-pressed="true"]{background:#1c3f94;color:#fff;border-color:#1c3f94;}
.st-sum{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:18px;}
.st-sum span{background:var(--surface2);border:1px solid var(--border);border-radius:12px;
    padding:10px 14px;min-width:108px;}
.st-sum b{display:block;font-size:20px;color:var(--ink);}
.st-sum i{font-style:normal;color:var(--muted);font-size:12px;}
.st-note{color:var(--muted);font-size:13px;margin:0 0 16px;}
.st-event{border:1px solid var(--border);border-radius:14px;margin:0 0 12px;background:var(--surface);overflow:hidden;}
.st-head{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline;padding:12px 14px;border-bottom:1px solid var(--border2);}
.st-head h3{margin:0;font-size:16px;}
.st-meta{color:var(--muted);font-size:13px;}
.st-meta b{color:var(--ink);}
.st-picks{list-style:none;margin:0;padding:0;}
.st-picks li{display:grid;grid-template-columns:58px minmax(0,1fr) auto;gap:8px;align-items:baseline;
    padding:8px 14px;border-bottom:1px solid var(--border2);font-size:14px;}
.st-picks li:last-child{border-bottom:0;}
.st-day{color:var(--muted);font-size:12px;font-weight:700;}
.st-who i{font-style:normal;color:var(--muted);font-size:12px;margin-left:6px;}
.st-win{color:var(--up,#1a7f37);font-weight:700;}
.st-loss{color:var(--down,#b42318);font-weight:700;}
.st-score{font-variant-numeric:tabular-nums;font-weight:700;}
.st-chart-wrap{margin-top:22px;}
.st-chart-wrap h2{font-size:16px;margin:0 0 4px;}
.st-chart{width:100%;height:180px;}
@media (max-width:720px){
    .st-picks li{grid-template-columns:48px minmax(0,1fr); }
    .st-score{grid-column:2;}
}
"""

_JS = r"""
(function(){
  var DATA = window.__ST || {strategies:{}, skipped:[]};
  var current = "rank";
  var year = 0;
  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function pct(n){return (Math.round((n||0)*1000)/10).toFixed(1)+"%";}
  function pack(){return DATA.strategies[current]||{summary:{},years:[],events:[],ranks:[]};}
  function years(){return pack().years||[];}
  function stat(v,label){return '<span><b>'+esc(v)+'</b><i>'+esc(label)+'</i></span>';}
  function chart(ranks){
    if(!ranks.length) return '<p class="st-note">这一年没有可画的名次。</p>';
    var w=640,h=170,pad=28;
    var ys=ranks.map(function(r){return r.rank;});
    var min=Math.min.apply(null,ys), max=Math.max.apply(null,ys);
    if(min===max) max=min+1;
    var pts=ranks.map(function(r,i){
      var x=pad+(ranks.length===1? (w-2*pad)/2 : i*(w-2*pad)/(ranks.length-1));
      var y=pad+(r.rank-min)/(max-min)*(h-2*pad);
      return {x:x,y:y,r:r};
    });
    var line=pts.map(function(p){return p.x.toFixed(1)+","+p.y.toFixed(1);}).join(" ");
    var last=pts[pts.length-1];
    return '<svg class="st-chart" viewBox="0 0 '+w+' '+h+'" role="img" aria-label="名次走势">'
      +'<polyline fill="none" stroke="#1c3f94" stroke-width="2" points="'+line+'"/>'
      +'<text x="'+pad+'" y="16" fill="currentColor" font-size="11">最好 '+min+'</text>'
      +'<text x="'+pad+'" y="'+(h-6)+'" fill="currentColor" font-size="11">最低 '+max+'</text>'
      +'<text x="'+(last.x-8)+'" y="'+(last.y-8)+'" fill="currentColor" font-size="11" text-anchor="end">'+esc(last.r.city)+' '+last.r.rank+'</text>'
      +'</svg>';
  }
  function dayLine(p){
    var extra=[];
    if(p.rank!=null) extra.push("排名 "+p.rank);
    if(p.odds!=null) extra.push(p.odds);
    return '<li><span class="st-day">Day '+p.day+'</span><span class="st-who">'+esc(p.player)
      +' <span class="'+(p.won?'st-win':'st-loss')+'">'+(p.won?'胜':'负')+'</span> '+esc(p.opponent)
      +(extra.length?'<i>'+esc(extra.join(" · "))+'</i>':'')
      +'</span><span class="st-score">'+esc(p.score)+'</span></li>';
  }
  function renderYears(){
    var list=years();
    if(!list.some(function(y){return y.year===year;})) year=list.length?list[list.length-1].year:0;
    document.getElementById("stYear").innerHTML=list.map(function(y){
      var on=y.year===year;
      return '<button type="button" data-year="'+y.year+'" aria-pressed="'+(on?"true":"false")+'">'+y.year+'</button>';
    }).join("");
  }
  function render(){
    renderYears();
    var row=years().filter(function(y){return y.year===year;})[0]||{};
    document.getElementById("stSum").innerHTML=
      stat(row.points==null?"—":row.points,"冠军积分")
      +stat(row.rank==null?"—":row.rank,"年终名次")
      +stat(row.titles==null?"—":row.titles,"夺冠站数")
      +stat(row.played==null?"—":row.played,"参赛站数")
      +stat(pct(row.survival),"存活率");
    var events=(pack().events||[]).filter(function(e){return e.year===year;});
    document.getElementById("stEvents").innerHTML=events.map(function(e){
      var out=e.champion?"冠军":(e.status||"");
      return '<article class="st-event"><div class="st-head"><h3>'+esc(e.city)+'</h3>'
        +'<span class="st-meta">'+esc(e.week)+' · '+esc(e.level)+' · '+e.survived+'/'+e.days+' 天</span>'
        +'<span class="st-meta">本站得分 <b>'+esc(e.score)+'</b></span>'
        +'<span class="st-meta">当时名次 <b>'+(e.rank==null?"—":e.rank)+'</b></span>'
        +'<span class="st-meta">'+esc(out)+'</span></div><ol class="st-picks">'
        +(e.picks||[]).map(dayLine).join("")+'</ol></article>';
    }).join("") || '<p class="st-note">这一年没有模拟站。</p>';
    var ranks=(pack().ranks||[]).filter(function(r){return r.year===year;});
    document.getElementById("stChart").innerHTML='<h2>名次走势</h2>'+chart(ranks);
  }
  document.getElementById("stSwitch").addEventListener("click",function(ev){
    var btn=ev.target.closest("button");
    if(!btn) return;
    current=btn.getAttribute("data-k");
    Array.prototype.forEach.call(document.querySelectorAll("#stSwitch button"),function(el){
      el.setAttribute("aria-pressed", el===btn ? "true" : "false");
    });
    render();
  });
  document.getElementById("stYear").addEventListener("click",function(ev){
    var btn=ev.target.closest("button");
    if(!btn) return;
    year=Number(btn.getAttribute("data-year"));
    render();
  });
  render();
})();
"""


def _pack(tour_payload: dict[str, Any]) -> dict[str, Any]:
    strategies = tour_payload.get("strategies") or {}
    return {
        "strategies": {
            key: strategies.get(key) or {}
            for key, _label in LABELS
        },
        "skipped": tour_payload.get("skipped") or [],
    }


def render_strategy_pages(payload: dict[str, Any]) -> None:
    unmapped = len(payload.get("unmapped") or [])
    for tour, filename in (("ATP", "strategy_atp.html"), ("WTA", "strategy_wta.html")):
        data = json.dumps(_pack((payload.get("tours") or {}).get(tour) or {}), ensure_ascii=False)
        buttons = "".join(
            f'<button type="button" data-k="{html.escape(key)}" aria-pressed="'
            f'{"true" if key == "rank" else "false"}">{html.escape(label)}</button>'
            for key, label in LABELS
        )
        skipped = (payload.get("tours") or {}).get(tour, {}).get("skipped") or []
        unaligned = sum(
            1
            for item in skipped
            if item.get("reason") in {"没有选人日日期", "选人日与分数阶梯不一致"}
        )
        unmapped_note = (
            f"未译成中文的选人 {unmapped} 个，明细里保留英文。"
            if unmapped
            else ""
        )
        align_note = f"未能按网站选人日对齐的站已跳过（{unaligned} 站）。" if unaligned else ""
        body = f"""
<div class="st-switch" id="stSwitch" role="group" aria-label="策略">{buttons}</div>
<div class="st-switch" id="stYear" role="group" aria-label="年份"></div>
<p class="st-note">按本站分数阶梯和最佳 18 站计分。年终总决赛不计入。奥运会加在最佳 18 站之上。选人日用网站公布的日期和轮次。{align_note}{unmapped_note}每天右侧的数字是活到这一天的本站得分。</p>
<div class="st-sum" id="stSum"></div>
<div id="stEvents"></div>
<div class="st-chart-wrap" id="stChart"></div>
<script>window.__ST={data};</script>
<script>{_JS}</script>
"""
        years = payload.get("years") or []
        if len(years) >= 2:
            span = f"{years[0]}–{years[-1]}"
        elif years:
            span = str(years[0])
        else:
            span = ""
        page = _inner_page_shell(
            page_title=f"策略模拟 · {tour}",
            title="策略模拟",
            tour=tour,
            eyebrow=f"{tour} · {span}",
            updated=str(payload.get("generated") or ""),
            extra_tags=["回测"],
            body_content=body,
            extra_css=_CSS,
            page=filename,
        )
        write_page(ROOT / filename, page)
