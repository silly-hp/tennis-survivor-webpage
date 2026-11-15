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
.st-event summary{list-style:none;cursor:pointer;}
.st-event summary::-webkit-details-marker{display:none;}
.st-head{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline;padding:12px 14px;border-bottom:1px solid var(--border2);}
.st-event:not([open]) .st-head{border-bottom:0;padding-bottom:4px;}
.st-head h3{margin:0;font-size:16px;}
.st-caret{margin-left:auto;color:var(--faint);font-size:12px;transition:transform .15s;}
.st-event[open] .st-caret{transform:rotate(180deg);color:var(--primary);}
.st-strip{display:flex;flex-wrap:wrap;gap:6px;padding:2px 14px 12px;}
.st-event[open] .st-strip{display:none;}
.st-chip{display:inline-flex;align-items:baseline;gap:4px;max-width:100%;padding:3px 8px;border-radius:999px;
    background:var(--surface2);border:1px solid var(--border2);font-size:13px;white-space:nowrap;}
.st-chip .st-day{margin-right:2px;}
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
.st-chart-wrap{margin-top:22px;padding:16px 16px 12px;border:1px solid var(--border);border-radius:16px;background:var(--surface);}
.st-chart-wrap h2{font-size:16px;margin:0 0 2px;}
.st-chart{width:100%;height:auto;display:block;}
.st-grid{stroke:var(--border);stroke-width:1;}
.st-axis{fill:var(--muted);font-size:11px;font-family:'Space Mono',ui-monospace,monospace;}
.st-chart-cap{color:var(--muted);font-size:12px;margin:8px 0 0;}
.st-pt circle{fill:var(--surface);stroke:var(--primary);stroke-width:2;}
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
    var w=720,h=248,left=48,right=16,top=16,bottom=34;
    var ys=ranks.map(function(r){return r.rank;});
    var min=Math.min.apply(null,ys), max=Math.max.apply(null,ys);
    var span=Math.max(1,max-min), gutter=Math.max(1,Math.round(span*0.12));
    var y0=Math.max(1,min-gutter), y1=max+gutter;
    function xAt(i){
      if(ranks.length===1) return (left+w-right)/2;
      return left+i*(w-left-right)/(ranks.length-1);
    }
    function yAt(rank){return top+(rank-y0)/(y1-y0)*(h-top-bottom);}
    var pts=ranks.map(function(r,i){return {x:xAt(i),y:yAt(r.rank),r:r};});
    var line=pts.map(function(p){return p.x.toFixed(1)+","+p.y.toFixed(1);}).join(" ");
    var floor=h-bottom;
    var area=pts[0].x.toFixed(1)+","+floor+" "+line+" "+pts[pts.length-1].x.toFixed(1)+","+floor;
    var grid="", seen={};
    for(var t=0;t<=4;t++){
      var rank=Math.round(y0+(y1-y0)*t/4);
      if(seen[rank]) continue;
      seen[rank]=1;
      var yy=yAt(rank);
      grid+='<line class="st-grid" x1="'+left+'" x2="'+(w-right)+'" y1="'+yy.toFixed(1)+'" y2="'+yy.toFixed(1)+'"/>'
        +'<text class="st-axis" x="'+(left-8)+'" y="'+(yy+4).toFixed(1)+'" text-anchor="end">'+rank+'</text>';
    }
    var marks=[0];
    if(ranks.length>2) marks.push(Math.floor((ranks.length-1)/2));
    if(ranks.length>1) marks.push(ranks.length-1);
    var labels=marks.filter(function(i,idx,arr){return arr.indexOf(i)===idx;}).map(function(i){
      var anchor=i===0?"start":(i===ranks.length-1?"end":"middle");
      return '<text class="st-axis" x="'+pts[i].x.toFixed(1)+'" y="'+(h-10)+'" text-anchor="'+anchor+'">'+esc(pts[i].r.city)+'</text>';
    }).join("");
    var dots=pts.map(function(p){
      return '<g class="st-pt"><circle cx="'+p.x.toFixed(1)+'" cy="'+p.y.toFixed(1)+'" r="3.5">'
        +'<title>'+esc(p.r.city)+' · 第 '+p.r.rank+' 名</title></circle></g>';
    }).join("");
    var last=pts[pts.length-1];
    var endLeft=last.x>w-64;
    return '<svg class="st-chart" viewBox="0 0 '+w+' '+h+'" role="img" aria-label="名次走势，越靠上名次越好">'
      +'<defs><linearGradient id="stArea" x1="0" y1="0" x2="0" y2="1">'
      +'<stop offset="0" stop-color="var(--primary)" stop-opacity="0.28"/>'
      +'<stop offset="1" stop-color="var(--primary)" stop-opacity="0"/></linearGradient></defs>'
      +grid
      +'<polygon points="'+area+'" fill="url(#stArea)"/>'
      +'<polyline points="'+line+'" fill="none" stroke="var(--primary)" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>'
      +dots
      +'<circle cx="'+last.x.toFixed(1)+'" cy="'+last.y.toFixed(1)+'" r="5" fill="var(--primary)"/>'
      +'<text class="st-axis" x="'+(endLeft?last.x-8:last.x+8).toFixed(1)+'" y="'+(Math.max(top+12,last.y-8)).toFixed(1)+'" text-anchor="'+(endLeft?"end":"start")+'">'+last.r.rank+'</text>'
      +labels+'</svg><p class="st-chart-cap">纵轴是名次，越靠上越好。停在点上可看站名。</p>';
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
      var chips=(e.picks||[]).map(function(p){
        return '<span class="st-chip"><span class="st-day">'+p.day+'</span>'+esc(p.player)
          +' <span class="'+(p.won?'st-win':'st-loss')+'">'+(p.won?'胜':'负')+'</span></span>';
      }).join("");
      return '<details class="st-event"><summary><div class="st-head"><h3>'+esc(e.city)+'</h3>'
        +'<span class="st-meta">'+esc(e.week)+' · '+esc(e.level)+' · '+e.survived+'/'+e.days+' 天</span>'
        +'<span class="st-meta">本站得分 <b>'+esc(e.score)+'</b></span>'
        +'<span class="st-meta">当时名次 <b>'+(e.rank==null?"—":e.rank)+'</b></span>'
        +'<span class="st-meta">'+esc(out)+'</span>'
        +'<span class="st-caret" aria-hidden="true">▾</span></div>'
        +'<div class="st-strip">'+chips+'</div></summary><ol class="st-picks">'
        +(e.picks||[]).map(dayLine).join("")+'</ol></details>';
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
