
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
  const CUP='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/></svg>';

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
