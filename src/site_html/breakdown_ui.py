"""HTML/CSS/JS fragments for combined-ranking points breakdown modal."""
from __future__ import annotations

_CSS_BREAKDOWN = """\
.filterable-table tbody tr.bd-clickable{cursor:pointer;}
/* surface colours: AO blue / Roland-Garros clay / Wimbledon green (also read by the charts) */
.bd-modal{--bd-hard:#0088bb;--bd-clay:#d0573a;--bd-grass:#1b5e37;
    display:none;position:fixed;inset:0;z-index:10050;background:rgba(5,20,32,.45);
    align-items:center;justify-content:center;padding:20px;}
body.dark .bd-modal{--bd-hard:#00b8f0;--bd-clay:#ff7a54;--bd-grass:#4ca86a;}
.bd-modal.open{display:flex;animation:bdFade .2s ease-out both;}
.bd-card{width:min(1120px,96vw);max-height:92vh;background:var(--surface);border-radius:14px;border-top:3px solid var(--primary);
    box-shadow:0 18px 50px rgba(5,20,32,.25);display:flex;flex-direction:column;overflow:hidden;color:var(--ink);
    animation:bdRise .26s cubic-bezier(.22,.68,0,1.2) both;}
.bd-hd{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:18px 20px 12px;}
.bd-hd::before{content:none;}
.bd-eye{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.2em;color:var(--primary);margin-bottom:4px;}
.bd-title{font-family:'Noto Serif SC',serif;font-size:22px;font-weight:700;}
.bd-sub{font-size:13px;color:var(--muted);margin-top:4px;}
.bd-sub b{font-family:'Space Mono',monospace;color:var(--ink);}
.bd-close{flex-shrink:0;width:44px;height:44px;border-radius:50%;border:1px solid var(--border);background:var(--surface);color:var(--ink);
    cursor:pointer;font-size:0;display:flex;align-items:center;justify-content:center;}
.bd-close::before{content:"";width:14px;height:14px;background:currentColor;
    -webkit-mask:linear-gradient(45deg,transparent 45%,#000 45%,#000 55%,transparent 55%),linear-gradient(-45deg,transparent 45%,#000 45%,#000 55%,transparent 55%);
    mask:linear-gradient(45deg,transparent 45%,#000 45%,#000 55%,transparent 55%),linear-gradient(-45deg,transparent 45%,#000 45%,#000 55%,transparent 55%);}
.bd-close:hover{border-color:var(--primary-rim);color:var(--primary-dark);}
.bd-close:focus-visible,.bd-chip:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
.bd-body{padding:4px 20px 20px;overflow:auto;}
.bd-filters{display:flex;flex-wrap:wrap;gap:10px 20px;margin-bottom:14px;}
.bd-filter-row{display:flex;gap:4px;align-items:center;padding:3px;background:var(--surface2);border:1px solid var(--border);border-radius:999px;}
.bd-gender-lbl,.bd-view-lbl{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);}
.bd-chip{font-family:inherit;font-size:12px;min-height:36px;padding:0 14px;border-radius:999px;border:0;background:transparent;color:var(--muted);
    cursor:pointer;transition:background-color .18s,color .18s;}
.bd-chip:hover{color:var(--primary-dark);}
.bd-chip.active,.bd-chip.active:hover{background:#1c3f94;color:#fff;font-weight:700;}
.bd-view{display:none;}
.bd-view.active{display:block;animation:bdIn .22s ease-out both;}
.bd-split{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:14px;}
.bd-panel{border:1px solid var(--border);border-radius:12px;background:var(--surface);overflow:hidden;}
.bd-panel-hd{padding:10px 14px;border-bottom:1px solid var(--border2);font-family:'Space Mono',monospace;font-size:11px;font-weight:700;
    letter-spacing:.12em;color:var(--muted);}
.bd-list{max-height:420px;overflow:auto;}
.bd-group-hd{padding:8px 14px;font-size:12px;font-weight:700;background:var(--surface2);color:var(--ink2);border-top:1px solid var(--border2);
    position:sticky;top:0;box-shadow:inset 3px 0 0 var(--border);}
.bd-group-hd.surf-hard{box-shadow:inset 3px 0 0 var(--bd-hard);}
.bd-group-hd.surf-clay{box-shadow:inset 3px 0 0 var(--bd-clay);}
.bd-group-hd.surf-grass{box-shadow:inset 3px 0 0 var(--bd-grass);}
.bd-row{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,.7fr) minmax(0,.9fr) minmax(0,1fr);gap:8px;padding:9px 14px;
    font-size:13px;border-top:1px solid var(--border2);color:var(--ink);}
.bd-row:hover{background:var(--row-hover);}
.bd-row .pts{font-family:'Space Mono',monospace;font-weight:700;}
.bd-row>div:nth-child(n+3){color:var(--muted);}
.bd-chart{height:420px;width:100%;}
.bd-chart.tall{height:460px;}
.bd-empty{padding:28px;text-align:center;color:var(--muted);font-size:13px;}
@keyframes bdFade{from{opacity:0}to{opacity:1}}
@keyframes bdRise{from{opacity:0;transform:translateY(10px) scale(.98)}to{opacity:1;transform:none}}
@keyframes bdIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
@media(max-width:860px){
  .bd-split{grid-template-columns:minmax(0,1fr);}
  .bd-chart{height:340px;}
}
@media(max-width:720px){
  .bd-modal{padding:0;align-items:flex-end;}
  .bd-card{width:100%;max-height:94vh;border-radius:16px 16px 0 0;}
  .bd-hd,.bd-body{padding-left:16px;padding-right:16px;}
}
@media(prefers-reduced-motion:reduce){.bd-modal.open,.bd-card,.bd-view.active{animation:none;}.bd-chip{transition:none;}}
"""

_JS_BREAKDOWN = r"""
(function(){
  if (!window.__BREAKDOWN__) return;
  var CFG = window.__BREAKDOWN__;
  var cache = {atp:null, wta:null};
  var state = {uid:null, name:'', gender:'atp', view:'level', loading:false};
  var charts = {level:null, surface:null, month:null};
  // chart colours come from the page theme (and the modal's surface tokens)
  function cv(name, el){ return getComputedStyle(el || document.body).getPropertyValue(name).trim(); }
  function surfaceColors(){ var m = $('bd-modal');
    return {'硬地':cv('--bd-hard',m), '红土':cv('--bd-clay',m), '草地':cv('--bd-grass',m)}; }
  function levelColors(){ return [cv('--primary'), cv('--secondary'), cv('--primary-dark'), cv('--muted')]; }

  function $(id){ return document.getElementById(id); }
  function ensureCharts(){
    if (!window.echarts) return false;
    if (!charts.level) charts.level = echarts.init($('bd-chart-level'), null, {renderer:'canvas'});
    if (!charts.surface) charts.surface = echarts.init($('bd-chart-surface'), null, {renderer:'canvas'});
    if (!charts.month) charts.month = echarts.init($('bd-chart-month'), null, {renderer:'canvas'});
    return true;
  }
  function disposeCharts(){
    Object.keys(charts).forEach(function(k){
      if (charts[k]) { charts[k].dispose(); charts[k]=null; }
    });
  }
  function loadScript(src){
    return new Promise(function(resolve, reject){
      if (window.echarts) { resolve(); return; }
      var s = document.createElement('script');
      s.src = src; s.async = true;
      s.onload = function(){ resolve(); };
      s.onerror = function(){ reject(new Error('echarts load failed')); };
      document.head.appendChild(s);
    });
  }
  function globalBag(tour){
    if (tour==='atp') return CFG.atpGlobal || '__BD_LIVE_ATP';
    return CFG.wtaGlobal || '__BD_LIVE_WTA';
  }
  function loadScriptOnce(src){
    return new Promise(function(resolve, reject){
      var existed = document.querySelector('script[data-bd-src="'+src+'"]');
      if (existed){
        if (existed.getAttribute('data-bd-ready')==='1') resolve();
        else existed.addEventListener('load', function(){ resolve(); });
        return;
      }
      var s = document.createElement('script');
      s.src = src;
      s.async = true;
      s.setAttribute('data-bd-src', src);
      s.onload = function(){ s.setAttribute('data-bd-ready','1'); resolve(); };
      s.onerror = function(){ reject(new Error('脚本加载失败: '+src)); };
      document.head.appendChild(s);
    });
  }
  function fetchTour(tour){
    if (cache[tour]) return Promise.resolve(cache[tour]);
    var gname = globalBag(tour);
    if (window[gname]) {
      cache[tour] = window[gname] || {};
      return Promise.resolve(cache[tour]);
    }
    var jsUrl = (tour==='atp' ? CFG.atpUrl : CFG.wtaUrl).replace(/\.json$/i, '.js');
    return loadScriptOnce(jsUrl).then(function(){
      if (!window[gname]) throw new Error('数据未就绪');
      cache[tour] = window[gname] || {};
      return cache[tour];
    });
  }
  function userPayload(){
    var bag = cache[state.gender] || {};
    return bag[state.uid] || null;
  }
  function levelOrder(payload){
    return (payload && payload.levels) || (state.gender==='wta'
      ? ['大满贯','W1000','W500','W250']
      : ['大满贯','M1000','M500','M250']);
  }
  function surfaceOrder(payload){
    return (payload && payload.surfaces) || ['硬地','红土','草地'];
  }
  function totalOf(payload){
    if (!payload) return 0;
    var sum = 0;
    (payload.events||[]).forEach(function(e){ if ((e.points||0)>0) sum += e.points; });
    return sum || payload.total || 0;
  }
  function esc(s){
    return String(s).replace(/[&<>"']/g, function(c){
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]);
    });
  }
  function renderGroupedList(listId, payload, groupKey, order){
    var box = $(listId);
    if (!payload || !(payload.events||[]).length){
      box.innerHTML = '<div class="bd-empty">暂无赛事积分明细</div>';
      return;
    }
    var groups = {};
    order.forEach(function(g){ groups[g]=[]; });
    payload.events.forEach(function(e){
      if ((e.points||0)<=0) return;
      var g = e[groupKey] || order[order.length-1];
      if (!groups[g]) groups[g]=[];
      groups[g].push(e);
    });
    var html = '';
    order.forEach(function(g){
      var rows = groups[g] || [];
      if (!rows.length) return;
      var surfCls = g==='硬地'?' surf-hard':(g==='红土'?' surf-clay':(g==='草地'?' surf-grass':''));
      html += '<div class="bd-group-hd'+surfCls+'">'+esc(g)+'</div>';
      rows.forEach(function(e){
        html += '<div class="bd-row">'
          + '<div>'+esc(e.name||'')+'</div>'
          + '<div class="pts">'+(e.points||0)+'</div>'
          + '<div>'+esc(e.round||'—')+'</div>'
          + '<div>'+esc(e.expires_month || (e.expires ? String(e.expires).slice(0,7).replace('-','.') : '') || '—')+'</div>'
          + '</div>';
      });
    });
    box.innerHTML = html || '<div class="bd-empty">暂无赛事</div>';
  }
  function renderCategoryDonut(chartKey, elId, payload, groupKey, order, titleTip){
    if (!ensureCharts()) return;
    var totals = {};
    order.forEach(function(g){ totals[g]=0; });
    (payload.events||[]).forEach(function(e){
      var p = e.points||0;
      if (p<=0) return;
      var g = e[groupKey] || order[order.length-1];
      totals[g] = (totals[g]||0) + p;
    });
    var total = totalOf(payload);
    var SC = surfaceColors(), LC = levelColors();
    var data = order.filter(function(g){ return (totals[g]||0)>0; }).map(function(g){
      var item = {name:g, value:totals[g]};
      if (groupKey==='surface' && SC[g]) item.itemStyle = {color: SC[g]};
      else item.itemStyle = {color: LC[order.indexOf(g) % LC.length]};
      return item;
    });
    var ink = cv('--ink'), muted = cv('--muted'), surf = cv('--surface');
    if (!charts[chartKey]) charts[chartKey] = echarts.init($(elId), null, {renderer:'canvas'});
    charts[chartKey].setOption({
      backgroundColor:'transparent',
      tooltip:{trigger:'item', formatter:function(p){
        var pct = total? ((p.value/total)*100).toFixed(1):'0';
        return (titleTip? (titleTip+' · ') : '')+p.name+'<br/>积分：'+p.value+'（'+pct+'%）';
      }},
      series:[{
        type:'pie', radius:['48%','72%'],
        itemStyle:{borderColor:surf, borderWidth:3, borderRadius:4},
        label:{color:ink, fontSize:12, lineHeight:16, formatter:function(p){
          var pct = total? ((p.value/total)*100).toFixed(1):'0';
          return p.name+'\n'+p.value+' · '+pct+'%';
        }},
        data:data,
        emphasis:{itemStyle:{shadowBlur:12, shadowColor:'rgba(0,0,0,.18)'}}
      }],
      graphic:[{
        type:'group', left:'center', top:'center',
        children:[
          {type:'text', style:{text:'总分', fill:muted, fontSize:12, textAlign:'center'}, top:-14},
          {type:'text', style:{text:String(total), fill:ink, fontSize:22, fontWeight:700, textAlign:'center', fontFamily:'Space Mono, monospace'}, top:6}
        ]
      }]
    }, true);
  }
  function renderMonthBars(payload){
    if (!ensureCharts()) return;
    var byMonth = {};
    (payload.events||[]).forEach(function(e){
      if ((e.points||0)<=0) return;
      var m = e.expires_month || '';
      if (!m && e.expires) m = String(e.expires).slice(0,7).replace('-','.');
      if (!m) m = '未知';
      if (!byMonth[m]) byMonth[m] = {points:0, events:[]};
      byMonth[m].events.push(e);
      byMonth[m].points += e.points;
    });
    // Latest expiry first in data → ECharts category axis draws index 0 at BOTTOM.
    var months = Object.keys(byMonth).sort().reverse();
    var values = months.map(function(m){ return byMonth[m].points; });
    var ink = cv('--ink'), muted = cv('--muted'), line = cv('--border');
    charts.month.setOption({
      backgroundColor:'transparent',
      tooltip:{trigger:'axis', axisPointer:{type:'shadow'}, formatter:function(params){
        var p = params[0];
        var m = p.name;
        var g = byMonth[m];
        var lines = [(m+' · 合计 '+((g&&g.points)||0))];
        (g&&g.events||[]).forEach(function(e){
          lines.push((e.name||'')+'：'+(e.points||0));
        });
        return lines.join('<br/>');
      }},
      grid:{left:72, right:72, top:20, bottom:24, containLabel:false},
      xAxis:{type:'value', name:'积分', nameTextStyle:{color:muted}, splitLine:{lineStyle:{color:line}}, axisLabel:{color:muted}},
      yAxis:{type:'category', data:months, axisLabel:{color:ink}, axisTick:{show:false}, axisLine:{lineStyle:{color:line}}},
      series:[{
        type:'bar', data:values, barWidth:14,
        itemStyle:{borderRadius:[0,6,6,0], color:cv('--primary')},
        label:{show:true, position:'right', color:ink, fontFamily:'Space Mono, monospace',
          formatter:function(p){ return p.value>0 ? p.value : ''; }}
      }],
      graphic:[]
    }, true);
    var H = $('bd-chart-month').clientHeight || 460;
    var n = months.length || 1;
    var topPad = 20, botPad = 24;
    var plotH = H - topPad - botPad;
    var children = [];
    // Index 0 is at the bottom of the plot; place detail text just under each bar.
    months.forEach(function(m, i){
      var g = byMonth[m];
      var text = (g.events||[]).map(function(e){ return (e.name||'')+' '+(e.points||0); }).join('  ·  ');
      var y = topPad + (plotH / n) * ((n - 1 - i) + 0.82);
      children.push({
        type:'text', left:78, top:y, z:10,
        style:{text:text, fill:muted, fontSize:11, width: Math.max(200, ($('bd-chart-month').clientWidth||600)-160), overflow:'truncate'}
      });
    });
    charts.month.setOption({graphic:children});
  }
  function applyView(){
    document.querySelectorAll('.bd-view').forEach(function(pane){
      pane.classList.toggle('active', pane.getAttribute('data-view')===state.view);
    });
    document.querySelectorAll('.bd-chip[data-view]').forEach(function(btn){
      btn.classList.toggle('active', btn.getAttribute('data-view')===state.view);
    });
  }
  function renderAll(){
    var payload = userPayload();
    var total = totalOf(payload);
    $('bd-title').textContent = state.name || '用户';
    $('bd-sub').innerHTML = (state.gender==='atp'?'ATP 男单':'WTA 女单') + ' · 总分 <b>' + total + '</b>';
    applyView();
    if (!payload){
      ['bd-list-level','bd-list-surface'].forEach(function(id){
        $(id).innerHTML = '<div class="bd-empty">暂无该侧积分明细</div>';
      });
      if (ensureCharts()){
        Object.keys(charts).forEach(function(k){ if (charts[k]) charts[k].clear(); });
      }
      return;
    }
    renderGroupedList('bd-list-level', payload, 'level', levelOrder(payload));
    renderGroupedList('bd-list-surface', payload, 'surface', surfaceOrder(payload));
    renderCategoryDonut('level', 'bd-chart-level', payload, 'level', levelOrder(payload), '赛事类型');
    renderCategoryDonut('surface', 'bd-chart-surface', payload, 'surface', surfaceOrder(payload), '场地类型');
    renderMonthBars(payload);
    setTimeout(function(){
      Object.keys(charts).forEach(function(k){ if (charts[k]) charts[k].resize(); });
    }, 50);
  }
  function setGender(g){
    state.gender = g;
    document.querySelectorAll('.bd-chip[data-gender]').forEach(function(btn){
      btn.classList.toggle('active', btn.getAttribute('data-gender')===g);
    });
    state.loading = true;
    fetchTour(g).then(function(){
      state.loading = false;
      renderAll();
    }).catch(function(err){
      state.loading = false;
      ['bd-list-level','bd-list-surface'].forEach(function(id){
        $(id).innerHTML = '<div class="bd-empty">加载失败：'+esc(err.message||err)+'</div>';
      });
    });
  }
  function setView(v){
    state.view = v || 'level';
    applyView();
    setTimeout(function(){
      Object.keys(charts).forEach(function(k){ if (charts[k]) charts[k].resize(); });
    }, 30);
  }
  function openModal(uid, name, prefer){
    state.uid = String(uid||'');
    state.name = name||'';
    var modal = $('bd-modal');
    if (!modal) return;
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
    $('bd-title').textContent = state.name || '用户';
    $('bd-sub').textContent = '加载中…';
    ['bd-list-level','bd-list-surface'].forEach(function(id){
      $(id).innerHTML = '<div class="bd-empty">加载积分数据中…</div>';
    });
    setView(state.view || 'level');
    var first = prefer || 'atp';
    var echartsUrls = [CFG.echartsUrl, CFG.echartsCdn].filter(Boolean);
    (function loadE(i){
      if (i >= echartsUrls.length){
        $('bd-list-level').innerHTML = '<div class="bd-empty">图表库加载失败</div>';
        return;
      }
      loadScript(echartsUrls[i]).then(function(){ setGender(first); })
        .catch(function(){ loadE(i+1); });
    })(0);
  }
  function closeModal(){
    var modal = $('bd-modal');
    if (modal) modal.classList.remove('open');
    document.body.style.overflow = '';
    disposeCharts();
  }
  function eventEl(ev){
    var t = ev.target;
    if (!t) return null;
    if (t.nodeType === 3) t = t.parentElement;
    return t && t.nodeType === 1 ? t : null;
  }
  document.addEventListener('click', function(ev){
    var el = eventEl(ev);
    if (!el) return;
    if (el.closest && el.closest('.bd-card')) {
      if (el.id === 'bd-close' || (el.closest && el.closest('#bd-close'))) closeModal();
      return;
    }
    var tr = el.closest ? el.closest('table.filterable-table tbody tr[data-uid]') : null;
    if (tr){
      var uid = tr.getAttribute('data-uid');
      var table = tr.closest('table');
      var heads = Array.prototype.map.call(table.querySelectorAll('thead th'), function(th){ return th.textContent.trim(); });
      var nameIdx = heads.indexOf('用户名');
      var name = nameIdx>=0 ? (tr.children[nameIdx].textContent||'').trim() : '';
      var atpIdx = heads.indexOf('ATP总分');
      var wtaIdx = heads.indexOf('WTA总分');
      var atp = atpIdx>=0 ? parseInt((tr.children[atpIdx].textContent||'0').replace(/\D/g,''),10)||0 : 0;
      var wta = wtaIdx>=0 ? parseInt((tr.children[wtaIdx].textContent||'0').replace(/\D/g,''),10)||0 : 0;
      openModal(uid, name, (wta>atp) ? 'wta' : 'atp');
      return;
    }
    if (el.id==='bd-close' || el=== $('bd-modal') || (el.classList && el.classList.contains('bd-modal'))) closeModal();
  });
  document.addEventListener('keydown', function(ev){
    if (ev.key==='Escape') closeModal();
  });
  document.querySelectorAll('.bd-chip[data-gender]').forEach(function(btn){
    btn.addEventListener('click', function(ev){
      ev.preventDefault(); ev.stopPropagation();
      setGender(btn.getAttribute('data-gender'));
    });
  });
  document.querySelectorAll('.bd-chip[data-view]').forEach(function(btn){
    btn.addEventListener('click', function(ev){
      ev.preventDefault(); ev.stopPropagation();
      setView(btn.getAttribute('data-view'));
    });
  });
  window.addEventListener('resize', function(){
    Object.keys(charts).forEach(function(k){ if (charts[k]) charts[k].resize(); });
  });
})();
"""


def breakdown_modal_html() -> str:
    return """\
<div id="bd-modal" class="bd-modal" aria-hidden="true">
  <div class="bd-card" role="dialog" aria-modal="true" aria-labelledby="bd-title">
    <div class="bd-hd">
      <div>
        <div class="bd-eye">POINTS BREAKDOWN · 积分构成</div>
        <div class="bd-title" id="bd-title">积分构成</div>
        <div class="bd-sub" id="bd-sub"></div>
      </div>
      <button type="button" class="bd-close" id="bd-close" aria-label="关闭">关闭</button>
    </div>
    <div class="bd-body">
      <div class="bd-filters">
        <div class="bd-filter-row">
          <span class="bd-gender-lbl">巡回赛</span>
          <button type="button" class="bd-chip active" data-gender="atp">ATP</button>
          <button type="button" class="bd-chip" data-gender="wta">WTA</button>
        </div>
        <div class="bd-filter-row">
          <span class="bd-view-lbl">视图</span>
          <button type="button" class="bd-chip active" data-view="level">按赛事类型</button>
          <button type="button" class="bd-chip" data-view="surface">按场地类型</button>
          <button type="button" class="bd-chip" data-view="month">按失效时间</button>
        </div>
      </div>

      <div class="bd-view active" data-view="level">
        <div class="bd-split">
          <div class="bd-panel">
            <div class="bd-panel-hd">赛事清单 · 按级别</div>
            <div class="bd-list" id="bd-list-level"></div>
          </div>
          <div class="bd-panel">
            <div class="bd-panel-hd">赛事类型聚合</div>
            <div class="bd-chart" id="bd-chart-level"></div>
          </div>
        </div>
      </div>

      <div class="bd-view" data-view="surface">
        <div class="bd-split">
          <div class="bd-panel">
            <div class="bd-panel-hd">赛事清单 · 按场地</div>
            <div class="bd-list" id="bd-list-surface"></div>
          </div>
          <div class="bd-panel">
            <div class="bd-panel-hd">场地类型聚合</div>
            <div class="bd-chart" id="bd-chart-surface"></div>
          </div>
        </div>
      </div>

      <div class="bd-view" data-view="month">
        <div class="bd-panel">
          <div class="bd-panel-hd">积分失效月度分布</div>
          <div class="bd-chart tall" id="bd-chart-month"></div>
        </div>
      </div>
    </div>
  </div>
</div>
"""


def breakdown_boot_script(atp_url: str, wta_url: str) -> str:
    import json

    def _global_for(url: str) -> str:
        name = str(url).rsplit("/", 1)[-1].lower()
        return {
            "breakdown_live_atp.json": "__BD_LIVE_ATP",
            "breakdown_live_wta.json": "__BD_LIVE_WTA",
            "breakdown_race_atp.json": "__BD_RACE_ATP",
            "breakdown_race_wta.json": "__BD_RACE_WTA",
            "breakdown_live_atp.js": "__BD_LIVE_ATP",
            "breakdown_live_wta.js": "__BD_LIVE_WTA",
            "breakdown_race_atp.js": "__BD_RACE_ATP",
            "breakdown_race_wta.js": "__BD_RACE_WTA",
        }.get(name, "__BD_DATA")

    cfg = {
        "atpUrl": atp_url,
        "wtaUrl": wta_url,
        "atpGlobal": _global_for(atp_url),
        "wtaGlobal": _global_for(wta_url),
        "echartsUrl": "assets/echarts.min.js",
        "echartsCdn": "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js",
    }
    # Bare JS only — injected inside the page's single <script> block.
    return (
        f"window.__BREAKDOWN__ = {json.dumps(cfg, ensure_ascii=False)};\n"
        f"{_JS_BREAKDOWN}\n"
    )
