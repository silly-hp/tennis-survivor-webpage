
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
