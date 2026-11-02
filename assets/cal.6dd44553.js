
(function(){
function ready(fn){ if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',fn); else fn(); }
ready(function(){
  const root=document.getElementById('cl'); if(!root) return;
  let D=window.__CL_DATA;
  if(!D){ try{ D=JSON.parse(document.getElementById('clData').textContent); }catch(e){ return; } }
  if(!D) return;
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
