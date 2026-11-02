
(function(){
// starts once the shared table script has built TS (see tsReady in _JS_TABLE)
function ready(fn){ if(window.TS&&window.TS.ready) fn(); else document.addEventListener('ts:ready',fn,{once:true}); }
ready(function(){
  const root=document.getElementById('rk');
  const table=root&&root.querySelector('.filterable-table');
  if(!root||!table||!window.TS) return;
  const KEY='ts.watch.v1', PAGE=50;
  const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const mqMobile=window.matchMedia('(max-width:720px)');
  const still=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── storage (throws on data: URLs / private mode) ──
  function load(){ try{ const v=JSON.parse(localStorage.getItem(KEY)||'null'); if(v&&Array.isArray(v.lists)) return v; }catch(e){} return {me:'',lists:[]}; }
  let S=load();
  function save(){ try{ localStorage.setItem(KEY,JSON.stringify(S)); }catch(e){} }

  // ── columns ──
  const ths=[...table.querySelectorAll('thead tr:first-child th')].map(t=>t.textContent.trim());
  const col=(...ns)=>{ for(const n of ns){ const i=ths.indexOf(n); if(i>=0) return i; } return -1; };
  const C={rank:col('即时排名','排名'), cur:col('当前排名'), user:col('用户名'), st:col('当前状态'), pts:col('即时积分','总分'),
           d:col('排名变化'), main:col('今日主选'), alt:col('今日备选'), gain:col('本站得分'),
           minus:(()=>{ const i=ths.findIndex(t=>t==='扣除积分'||t.startsWith('扣除积分（')); return i; })(),
           killer:col('杀手球员'), days:col('存活天数'), d:-1};
  // rows are _JS_TABLE's models (r.t texts, r.h cell markup, r.u/r.p/r.d); a model's <tr>
  // exists only while it is shown (TS.el creates it), so read the model, not the DOM
  const rows=TS.rows;
  const txt=(r,i)=>(i<0||r.t[i]==null)?'':r.t[i];
  const cellHtml=(r,i)=>i<0||r.t[i]==null?'':TS.html(r,i);
  const uname=r=>txt(r,C.user);
  const byUser=new Map(rows.map(r=>[uname(r),r]));
  // the rank change rides inside 当前排名 (or the rank column): find whichever cell holds it
  const hasRank=(r,i)=>!!(r.h&&r.h[i]&&r.h[i].indexOf('class="rank ')>=0);
  C.d=rows.length?rows[0].t.findIndex((_,i)=>hasRank(rows[0],i)):-1;
  const delta=r=>{ if(r._d===undefined){ const m=C.d>=0&&r.h&&r.h[C.d]&&r.h[C.d].match(/data-d="(-?\d+)"/); r._d=m?(parseInt(m[1],10)||0):0; } return r._d; };

  // ── status groups ──
  const grp=tsGrp;
  const G=rows.map(r=>grp(txt(r,C.st)));
  // 轮空 / 未轮空 only on a day-1 bye; 自杀 is a subset of 淘汰
  const BYE_DAY=root.dataset.byeday==='1';
  // 参赛 = picked on day 1 (anyone not 未参赛, incl. today's 未选); 已选 = made a valid pick today (matches 今日选人统计):
  // still in today (存活/未完赛/轮空) or knocked out by today's pick. Earlier losers have 存活天数 < today's.
  const CHIPS=[['all','全部'],['entered','参赛'],['picked','已选'],...(BYE_DAY?[['bye','轮空'],['nobye','未轮空']]:[]),['alive','存活'],['live','未完赛'],
               ['outall','淘汰'],['suicide','自杀'],['none','未选']];
  const ENTERED=['alive','live','bye','out','suicide','none'];
  const DAYS=rows.map(r=>parseInt(txt(r,C.days),10));
  const TODAY_D=Math.max(-1,...DAYS.filter((d,i)=>G[i]!=='absent'&&!isNaN(d)));
  // data-picked (from settlement) covers today's losers/suicides; fallback for old pages.
  const TODAY=rows.map((r,i)=>r.p!==undefined?r.p===1
    :['alive','live','bye'].includes(G[i])||(G[i]==='out'&&DAYS[i]===TODAY_D&&used(r).length>TODAY_D));
  const inChip=(k,i)=>{ const g=G[i]; return k==='all'||(k==='entered'?ENTERED.includes(g):k==='picked'?TODAY[i]:k==='nobye'?TODAY[i]&&g!=='bye'
    :k==='outall'?(g==='out'||g==='suicide'):g===k); };
  let chip=C.st>=0?'picked':'all', list='', routes=new Set(), limit=PAGE;
  const rowIdx=new Map(rows.map((r,i)=>[r,i]));

  // ── route query (夺冠路线) ──
  const ROUTE_OK=['存活','未完赛','未选','轮空'];
  function used(r){ return Array.isArray(r.d)?r.d.map(String):[]; }
  function routeOk(r){ if(!routes.size) return true; if(!ROUTE_OK.includes(txt(r,C.st))) return false;
    const u=used(r); for(const p of routes) if(u.includes(p)) return false; return true; }

  const allFav=()=>new Set(S.lists.flatMap(l=>l.users));
  function listOk(u){ if(!list) return true; if(list==='*') return allFav().has(u); const l=S.lists.find(x=>x.id===list); return !!l&&l.users.includes(u); }
  TS.extra.push(function(r){ const i=rowIdx.get(r), u=uname(r);
    return (list?true:inChip(chip,i)) && listOk(u) && routeOk(r); });

  // ── pagination + counts after every filter pass ──
  // _JS_TABLE hands over the matching rows in sort order; only the first `limit` go into tbody
  let matched=[], lastMobile=null;
  const tbody=table.tBodies[0];
  TS.render=list=>{ matched=list; paginate(); };
  function paginate(){
    // phones show the cards and hide the table (CSS): build only the side that is visible
    lastMobile=mqMobile.matches;
    const show=lastMobile?[]:matched.slice(0,limit), frag=document.createDocumentFragment();
    show.forEach(r=>{ const el=TS.el(r); frzApply(el); frag.appendChild(el); });
    tbody.textContent=''; tbody.appendChild(frag);
    document.getElementById('visible-count').textContent=matched.length;
    document.getElementById('total-count').textContent=rows.length;
    const more=document.getElementById('rkMore');
    more.hidden=matched.length<=limit;
    more.textContent='再显示 '+Math.min(PAGE,matched.length-limit)+' 行';
    document.getElementById('rkEmpty').hidden=matched.length>0;
    renderCards();
  }
  document.getElementById('rkMore').addEventListener('click',()=>{ limit+=PAGE; paginate(); });
  function refresh(resetPage){ if(resetPage) limit=PAGE; TS.refresh(); }

  // ── status chips ──
  const chipBox=document.getElementById('rkChips');
  function renderChips(){
    if(C.st<0){ chipBox.hidden=true; return; }
    chipBox.innerHTML=CHIPS.map(([k,l])=>{ const n=G.filter((g,i)=>inChip(k,i)).length;
      return '<button type="button" class="rk-chip" data-k="'+k+'" aria-pressed="'+(!list&&chip===k)+'">'+l+'<span class="n">'+n+'</span></button>'; }).join('');
  }
  chipBox.addEventListener('click',e=>{ const b=e.target.closest('.rk-chip'); if(!b) return; chip=b.dataset.k; list=''; renderChips(); renderWatch(); refresh(true); });


  // ── route bar ──
  const rBtn=document.getElementById('rkRouteBtn');
  if(rBtn){
    const pop=document.getElementById('rkRoutePop'), sel=document.getElementById('rkRouteSel'), res=document.getElementById('rkRouteRes');
    const opts=[...pop.querySelectorAll('.rk-opt')];
    // picks are a draft until 完成; closing any other way drops the draft
    let draft=new Set();
    const openPop=o=>{ if(o===!pop.hidden) return; pop.hidden=!o; rBtn.setAttribute('aria-expanded',String(o));
      if(o){ draft=new Set(routes); paintOpts(); document.getElementById('rkRouteSearch').focus(); } else { draft=new Set(routes); paintOpts(); } };
    const paintOpts=()=>{ opts.forEach(o=>o.setAttribute('aria-selected',String(draft.has(o.dataset.v))));
      document.getElementById('rkRouteLbl').textContent=draft.size?('已选 '+draft.size+' 名球员'):'选择球员…'; };
    rBtn.addEventListener('click',e=>{ e.stopPropagation(); openPop(pop.hidden); });
    pop.addEventListener('click',e=>e.stopPropagation());
    document.getElementById('rkRouteDone').addEventListener('click',()=>{ routes=new Set(draft); syncRoute(); openPop(false); rBtn.focus(); });
    document.getElementById('rkRouteClr').addEventListener('click',()=>{ draft.clear(); paintOpts(); });
    document.getElementById('rkRouteSearch').addEventListener('input',e=>{ const q=e.target.value.trim().toLowerCase();
      opts.forEach(o=>{ o.style.display=o.dataset.v.toLowerCase().includes(q)?'':'none'; }); });
    opts.forEach(o=>o.addEventListener('click',()=>{ const v=o.dataset.v; draft.has(v)?draft.delete(v):draft.add(v); paintOpts(); }));
    document.addEventListener('click',()=>openPop(false));
    pop.addEventListener('keydown',e=>{ if(e.key==='Escape'){ openPop(false); rBtn.focus(); } });
    sel.addEventListener('click',e=>{ const b=e.target.closest('[data-rm]'); if(!b) return; routes.delete(b.dataset.rm); syncRoute(); });
    function syncRoute(){
      draft=new Set(routes); paintOpts();
      rBtn.classList.toggle('on',routes.size>0);
      sel.innerHTML=[...routes].map(p=>'<span class="rk-selchip">'+esc(p)+'<button type="button" data-rm="'+esc(p)+'" aria-label="移除 '+esc(p)+'"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg></button></span>').join('');
      refresh(true);
      res.hidden=!routes.size;
      if(routes.size) res.textContent='仍可选以上球员的存活用户 · '+rows.filter(routeOk).length+' 人';
    }
  }

  // ── stars, tags, "me" badge inside the user cell ──
  const STAR='<svg width="16" height="16" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true"><path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg>';
  // user cell markup, added to each <tr> as TS.el creates it (see the onRow hook below)
  function userCell(td,u){
    td.innerHTML='<span class="rk-user"><button type="button" class="rk-star" aria-label="关注 '+esc(u)+'" aria-haspopup="dialog" aria-expanded="false" data-u="'+esc(u)+'">'+STAR+'</button><span class="rk-uname">'+esc(u)+'</span><span class="rk-tags" data-t=""></span></span>'; }
  function tagsOf(u){ return S.lists.filter(l=>l.users.includes(u)).map(l=>l.name); }
  function paintRow(r){ if(!r.el) return; const u=uname(r), t=tagsOf(u), td=r.el.cells[C.user]; if(!td) return;
    td.querySelector('.rk-star').classList.toggle('on',t.length>0);
    td.querySelector('.rk-tags').dataset.t=t.map(x=>'★'+x).join(' ');
    td.querySelector('.rk-uname').toggleAttribute('data-me',u===S.me);
    r.el.classList.toggle('rk-mine',u===S.me); }
  const paintAll=()=>rows.forEach(paintRow);
  // badges/tags are CSS ::after content so the cell's textContent stays the bare name (filters, sort)
  table.addEventListener('click',e=>{ const b=e.target.closest('.rk-star'); if(b){ e.stopPropagation(); openPicker(b); } },true);

  // ── picker popover ──
  const picker=document.getElementById('rkPicker'); let pickFor='', pickBtn=null;
  document.body.appendChild(picker);  // page coordinates; .page is position:relative
  function openPicker(btn){
    if(pickBtn===btn&&!picker.hidden){ closePicker(); return; }
    pickFor=btn.dataset.u; pickBtn=btn; renderPicker();
    picker.hidden=false; btn.setAttribute('aria-expanded','true');
    const r=btn.getBoundingClientRect(); const w=232;
    picker.style.left=Math.max(12,Math.min(window.scrollX+r.left,window.scrollX+document.documentElement.clientWidth-w-12))+'px';
    picker.style.top=(window.scrollY+r.bottom+6)+'px';
    const f=picker.querySelector('button'); if(f) f.focus();
  }
  function closePicker(){ if(picker.hidden) return; picker.hidden=true; if(pickBtn){ pickBtn.setAttribute('aria-expanded','false'); pickBtn.focus({preventScroll:true}); } pickBtn=null; }
  function renderPicker(){
    const u=pickFor;
    picker.innerHTML='<span class="rk-eye rk-pop-eye">ADD TO LIST · '+esc(u)+'</span>'
      +S.lists.map(l=>'<button type="button" class="rk-opt" data-l="'+l.id+'" aria-pressed="'+l.users.includes(u)+'"><span class="rk-box" aria-hidden="true"></span><span class="rk-opt-l">'+esc(l.name)+'</span></button>').join('')
      +'<form class="rk-pick-new"><input class="rk-input" name="n" placeholder="新建列表名" aria-label="新建列表名"><button type="submit" class="rk-btn rk-btn-sm">新建</button></form>'
      +'<button type="button" class="rk-pick-act rk-pick-me" data-me="1">'+(S.me===u?'取消设为“我”':'设为“我”')+'</button>';
  }
  picker.addEventListener('click',e=>{ e.stopPropagation(); const b=e.target.closest('button'); if(!b) return;
    if(b.dataset.l){ const l=S.lists.find(x=>x.id===b.dataset.l); const i=l.users.indexOf(pickFor); i<0?l.users.push(pickFor):l.users.splice(i,1); afterChange(); renderPicker(); picker.querySelector('[data-l="'+l.id+'"]').focus(); }
    else if(b.dataset.me){ S.me=S.me===pickFor?'':pickFor; afterChange(); closePicker(); } });
  picker.addEventListener('submit',e=>{ e.preventDefault(); const n=e.target.n.value.trim(); if(!n) return;
    S.lists.push({id:'l'+Date.now().toString(36),name:n,users:[pickFor]}); afterChange(); renderPicker(); });
  picker.addEventListener('keydown',e=>{ if(e.key==='Escape') closePicker(); });
  document.addEventListener('click',closePicker);
  window.addEventListener('resize',closePicker);

  // ── watch tabs + manage ──
  const tabs=document.getElementById('rkWatchTabs'), newBox=document.getElementById('rkWatchNew'), manage=document.getElementById('rkManage');
  let creating=false;
  function renderWatch(){
    if(list&&list!=='*'&&!S.lists.find(l=>l.id===list)) list='';
    const fav=allFav();
    const defs=[['','不筛选',''],['*','全部关注',fav.size],...S.lists.map(l=>[l.id,l.name,l.users.length])];
    tabs.innerHTML=defs.map(([id,n,c])=>'<button type="button" class="rk-tab" data-l="'+id+'" aria-pressed="'+(list===id)+'">'+esc(n)+(c!==''?'<span class="n">'+c+'</span>':'')+'</button>').join('');
    newBox.innerHTML=creating
      ?'<form class="rk-new-form" id="rkNewForm"><input class="rk-input" name="n" placeholder="列表名，如 上海群友" aria-label="新列表名"><button type="submit" class="rk-btn rk-btn-sm rk-btn-pri">创建</button><button type="button" class="rk-btn-text" data-cancel="1">取消</button></form>'
      :'<button type="button" class="rk-tab rk-tab-new" id="rkNewBtn">+ 新建列表</button>';
    if(creating){ const i=newBox.querySelector('input'); i&&i.focus(); }
    const cur=S.lists.find(l=>l.id===list);
    manage.hidden=!cur;
    if(cur) manage.innerHTML='<label class="rk-note" for="rkRename">名称</label><input class="rk-input" id="rkRename" value="'+esc(cur.name)+'"><button type="button" class="rk-btn rk-btn-sm rk-btn-pri" id="rkRenameSave">保存</button><button type="button" class="rk-btn rk-btn-sm" id="rkDel" style="color:var(--bad)">删除列表</button>'
      +(cur.users.length?'':'<span class="rk-note">这个列表还是空的。点击任意行的 ☆ 把人加进来。</span>');
  }
  tabs.addEventListener('click',e=>{ const b=e.target.closest('.rk-tab'); if(!b) return; list=b.dataset.l; renderWatch(); renderChips(); refresh(true); });
  newBox.addEventListener('click',e=>{ if(e.target.id==='rkNewBtn'){ creating=true; renderWatch(); } else if(e.target.dataset.cancel){ creating=false; renderWatch(); } });
  newBox.addEventListener('submit',e=>{ e.preventDefault(); const n=e.target.n.value.trim(); creating=false;
    if(n){ const id='l'+Date.now().toString(36); S.lists.push({id,name:n,users:[]}); list=id; save(); } renderWatch(); renderChips(); refresh(true); });
  manage.addEventListener('click',e=>{ const cur=S.lists.find(l=>l.id===list); if(!cur) return;
    if(e.target.id==='rkRenameSave'){ const n=document.getElementById('rkRename').value.trim(); if(n){ cur.name=n; afterChange(); } }
    if(e.target.id==='rkDel') ask('删除列表「'+cur.name+'」？','列表里的 '+cur.users.length+' 人只会从这个列表移出，其他列表不受影响。','删除列表',e.target,()=>{
      S.lists=S.lists.filter(l=>l!==cur); list=''; afterChange(); renderChips(); refresh(true); }); });
  // in-page confirm: window.confirm is blocked in embedded browsers (returns false)
  const askM=document.getElementById('rkAsk'); let askFn=null;
  function ask(title,desc,okLabel,from,fn){
    document.getElementById('rkAskT').textContent=title; document.getElementById('rkAskD').textContent=desc;
    document.getElementById('rkAskOk').textContent=okLabel; askFn=fn; openModal(askM,from);
    askM.querySelector('[data-v="0"]').focus(); }
  askM.addEventListener('click',e=>{ if(!e.target.closest('[data-v="1"]')) return; const fn=askFn; askFn=null; closeModal(askM); if(fn) fn(); });
  function afterChange(){ save(); paintAll(); renderWatch(); renderMe(); if(list) refresh(false); else renderCards(); }

  // ── share link (#w=) ──
  const b64e=s=>btoa(unescape(encodeURIComponent(s))), b64d=s=>decodeURIComponent(escape(atob(s)));
  const shareBtn=document.getElementById('rkShareBtn'), shareLbl=shareBtn.querySelector('span');
  shareBtn.addEventListener('click',()=>{
    const data=S.lists.map(l=>({n:l.name,u:l.users}));
    const url=location.href.split('#')[0]+'#w='+encodeURIComponent(b64e(JSON.stringify(data)));
    const done=ok=>{ shareLbl.textContent=ok?'已复制链接':'复制失败'; setTimeout(()=>{ shareLbl.textContent='复制分享链接'; },1500); };
    if(!S.lists.length){ shareLbl.textContent='先新建一个列表'; setTimeout(()=>{ shareLbl.textContent='复制分享链接'; },1500); return; }
    try{ navigator.clipboard.writeText(url).then(()=>done(true),()=>done(false)); }catch(e){ done(false); }
  });
  (function readShare(){
    const m=location.hash.match(/^#w=(.+)$/); if(!m) return;
    let data; try{ data=JSON.parse(b64d(decodeURIComponent(m[1]))); }catch(e){ return; }
    if(!Array.isArray(data)||!data.length) return;
    const box=document.getElementById('rkShare'); box.hidden=false;
    box.innerHTML='<span>收到分享的关注列表 · <b>'+data.length+'</b> 个（'+esc(data.map(d=>d.n).join('、'))+'）</span><button type="button" class="rk-btn rk-btn-sm rk-btn-pri" data-a="merge">合并到我的列表</button><button type="button" class="rk-btn rk-btn-sm" data-a="replace">替换</button><button type="button" class="rk-btn-text" data-a="no">忽略</button>';
    box.addEventListener('click',e=>{ const a=e.target.dataset.a; if(!a) return;
      const inc=data.map((d,i)=>({id:'s'+Date.now().toString(36)+i,name:String(d.n||'分享列表'),users:(d.u||[]).map(String)}));
      if(a==='replace') S.lists=inc;
      if(a==='merge') inc.forEach(x=>{ const same=S.lists.find(l=>l.name===x.name); if(same) x.users.forEach(u=>{ if(!same.users.includes(u)) same.users.push(u); }); else S.lists.push(x); });
      box.hidden=true; try{ history.replaceState(null,'',location.pathname+location.search+'#watch'); }catch(err){}
      if(a!=='no') afterChange(); });
  })();

  // ── "me" card ──
  const meSet=document.getElementById('rkMeSet'), meBody=document.getElementById('rkMeBody');
  function deltaHtml(d){ return d>0?'<span class="rank up">▲'+d+'</span>':d<0?'<span class="rank down">▼'+(-d)+'</span>':'<span class="rank same">—</span>'; }
  function renderMe(){
    const r=S.me&&byUser.get(S.me);
    meSet.hidden=!!r; meBody.hidden=!r;
    document.getElementById('rkMeName').textContent=r?S.me:'';
    if(!r) return;
    document.getElementById('rkMeRank').textContent='#'+txt(r,C.rank);
    document.getElementById('rkMePts').textContent=C.pts>=0?txt(r,C.pts)+' 分':'';
    document.getElementById('rkMeD').innerHTML=C.d>=0?deltaHtml(delta(r)):'';
    const st=cellHtml(r,C.st);
    const pick=C.main>=0?(txt(r,C.main)||'今日未选'):'';
    document.getElementById('rkMePick').innerHTML=(pick||st)?'<span>'+esc(pick)+'</span>'+st:'';
  }
  const meIn=document.getElementById('rkMeInput'), NAMES=[...byUser.keys()];
  function setMe(v){ if(byUser.has(v)){ meIn.value=''; S.me=v; afterChange(); } else { meIn.setCustomValidity('找不到这个用户名'); meIn.reportValidity(); } }
  const meSug=tsSuggest(meIn,document.getElementById('rkMeSug'),{
    match:q=>{ const m=tsMatch(NAMES,q); return {opts:m.opts, note:'找不到包含「'+meIn.value.trim()+'」的用户'}; },
    pick:u=>setMe(u), host:document.getElementById('rkMe')});
  document.getElementById('rkMeSave').addEventListener('click',()=>setMe(meSug.current()||meIn.value.trim()));
  document.getElementById('rkMeChange').addEventListener('click',()=>{ S.me=''; afterChange(); document.getElementById('rkMeInput').focus(); });
  document.getElementById('rkMeJump').addEventListener('click',()=>jumpTo(S.me));
  // reveal a user's row (clears filters that hide it), scroll to it and flash it
  function jumpTo(u){
    const r=byUser.get(u); if(!r) return;
    if(!matched.includes(r)){ chip='all'; list=''; routes.clear(); renderChips(); renderWatch();
      if(rBtn){ routes.clear(); document.getElementById('rkRouteSel').innerHTML=''; document.getElementById('rkRouteRes').hidden=true; document.getElementById('rkRouteLbl').textContent='选择球员…'; } TS.refresh(); }
    const idx=matched.indexOf(r); if(idx>=limit){ limit=Math.ceil((idx+1)/PAGE)*PAGE; paginate(); }
    const target=mqMobile.matches?root.querySelector('.rk-card-row[data-u="'+CSS.escape(u)+'"]'):TS.el(r);
    if(target){ target.scrollIntoView({block:'center',behavior:still()?'auto':'smooth'}); flash(target); }
  }
  function flash(el){ el.classList.remove('rk-mv0','rk-mv1'); void el.offsetWidth; el.style.setProperty('--dy','0px'); el.classList.add('rk-mv0'); }

  // ── frozen rank / change / user columns (desktop) ──
  // offsets are computed once per layout change; rows pick them up when they enter tbody
  let frzLeft=null, frzV=0;
  function frzApply(tr){
    if(tr._frzV===frzV) return; tr._frzV=frzV;
    [...tr.children].forEach((c,i)=>{ const on=!!frzLeft&&i<frzLeft.length;
      c.classList.toggle('rk-frz',on); c.classList.toggle('rk-frz-last',on&&i===frzLeft.length-1); c.style.left=on?frzLeft[i]+'px':''; });
  }
  function freeze(){
    frzV++; frzLeft=null;
    if(!mqMobile.matches&&C.user>=0){
      const head=table.querySelector('thead tr').children; let left=0; frzLeft=[];
      for(let i=0;i<=C.user;i++){ frzLeft.push(left); left+=head[i].getBoundingClientRect().width; }
    }
    table.querySelectorAll('tr').forEach(frzApply);
  }
  // column widths shift after load (web fonts, re-rendered / filtered rows): re-pin on any header resize
  if(window.ResizeObserver){ let fq=0; const ro=new ResizeObserver(()=>{ if(!fq) fq=requestAnimationFrame(()=>{ fq=0; freeze(); }); });
    [...table.querySelector('thead tr').children].forEach(th=>ro.observe(th)); }

  // ── mobile cards (mirror the visible page of rows) ──
  const cardsBox=document.getElementById('rkCards'); const openCards=new Set();
  const CORE=new Set([C.rank,C.user,C.st,C.pts,C.d,C.main,C.alt]);
  function renderCards(){
    if(!mqMobile.matches){ cardsBox.innerHTML=''; return; }
    const show=matched.slice(0,limit);
    cardsBox.innerHTML=show.map(r=>{
      const u=uname(r), open=openCards.has(u), d=C.d>=0?delta(r):0, t=tagsOf(u);
      const st=cellHtml(r,C.st);
      let sub='';
      if(C.main>=0){ const m=txt(r,C.main), a=txt(r,C.alt), k=txt(r,C.killer);
        const g=grp(txt(r,C.st));
        sub=(g==='out'||g==='suicide')?(k?'杀手 <b>'+esc(k)+'</b>':''):g==='absent'?'':m?'<b>'+esc(m)+'</b> · 备 '+esc(a||'—'):'今日未选'; }
      const extra=ths.map((h,i)=>CORE.has(i)||i<0?'':'<span>'+esc(h)+'<b>'+esc(txt(r,i)||'—')+'</b></span>').join('');
      return '<div class="rk-card-row'+(u===S.me?' rk-mine':'')+(finalsSet.has(r)?' rk-final':'')+'" data-u="'+esc(u)+'">'
        +'<div class="rk-card-main"><button type="button" class="rk-card-btn" aria-expanded="'+open+'">'
        +'<span class="rk-c-rank">'+esc(txt(r,C.rank))+(C.d>=0?'<span class="rk-dpw">'+deltaHtml(d)+'</span>':'')+'</span>'
        +'<span class="rk-c-mid"><span class="rk-c-name"><span class="t">'+esc(u)+'</span>'+(u===S.me?'<span class="rk-mebadge">我</span>':'')+(t.length?'<span class="rk-tags">'+esc(t.map(x=>'★'+x).join(' '))+'</span>':'')+'</span>'
        +'<span class="rk-c-sub">'+st+(sub?'<span class="p">'+sub+'</span>':'')+'</span></span>'
        +'<span class="rk-c-right"><span class="rk-c-pts">'+esc(C.pts>=0?txt(r,C.pts):'')+'</span>'+(C.cur>=0?'<span class="rk-c-cur">当前 <b>'+esc(txt(r,C.cur))+'</b></span>':'')+'</span>'
        +'</button><button type="button" class="rk-star'+(t.length?' on':'')+'" aria-label="关注 '+esc(u)+'" aria-haspopup="dialog" aria-expanded="false" data-u="'+esc(u)+'">'+STAR+'</button></div>'
        +'<div class="rk-c-more"'+(open?'':' hidden')+'>'+extra+(r.d!==undefined?'<button type="button" class="rk-btn" data-hist="1">选人历史</button>':'')
        +(r.u!==undefined?'<button type="button" class="rk-btn" data-bd-uid="'+esc(r.u)+'">积分构成</button>':'')+'</div></div>';
    }).join('');
  }
  cardsBox.addEventListener('click',e=>{
    const card=e.target.closest('.rk-card-row'); if(!card) return; const u=card.dataset.u;
    const star=e.target.closest('.rk-star'); if(star){ e.stopPropagation(); openPicker(star); return; }
    if(e.target.closest('[data-hist]')){ const r=byUser.get(u); if(r) openHist(r,e.target.closest('[data-hist]')); return; }
    const btn=e.target.closest('.rk-card-btn'); if(!btn) return;
    const more=card.querySelector('.rk-c-more'); const o=more.hidden;
    more.hidden=!o; btn.setAttribute('aria-expanded',String(o)); o?openCards.add(u):openCards.delete(u);
  });
  // rebuild for the other layout; resize is a fallback for browsers that skip the change event
  const syncLayout=()=>{ if(mqMobile.matches!==lastMobile) paginate(); freeze(); };
  mqMobile.addEventListener('change',syncLayout);

  // ── rank-change motion: slide from old position, flash, count up 即时积分 ──
  let run=0;
  function play(){
    if(C.d<0) return; run++;
    const k=run%2, mobile=mqMobile.matches;
    const view=mobile?[...cardsBox.children]:matched.slice(0,limit).map(TS.el);
    const sample=view[0]; if(!sample) return;
    const h=sample.getBoundingClientRect().height+(mobile?8:0);
    view.forEach(el=>{
      const r=mobile?byUser.get(el.dataset.u):el._m; if(!r) return;
      const d=delta(r); el.classList.remove('rk-mv0','rk-mv1');
      const dp=(mobile?el:el.cells[C.d]).querySelector('.rank'); if(dp) dp.classList.remove('rk-dp0','rk-dp1');
      if(!d) return;
      void el.offsetWidth;
      el.style.setProperty('--dy',(Math.max(-8,Math.min(8,d))*h)+'px');
      el.classList.add('rk-mv'+k);
      if(dp){ dp.style.setProperty('--dd',d>0?'6px':'-6px'); dp.classList.add('rk-dp'+k); }
      if(!still()) countUp(r,el,mobile);
    });
  }
  function countUp(r,el,mobile){
    if(C.pts<0||C.gain<0) return;
    const cell=mobile?el.querySelector('.rk-c-pts'):el.cells[C.pts]; if(!cell) return;
    const v=txt(r,C.pts), to=parseFloat(v), gain=parseFloat(txt(r,C.gain))||0; if(isNaN(to)||!gain) return;
    const from=to-gain, t0=performance.now();
    (function step(now){ const p=Math.min(1,(now-t0)/1600), e=1-Math.pow(1-p,3);
      cell.textContent=String(Math.round(from+(to-from)*e)); if(p<1) requestAnimationFrame(step); else cell.textContent=v; })(t0);
  }
  // counting writes the cell's textContent only; filters/sort read the model text
  document.getElementById('rkReplay').addEventListener('click',play);
  if(C.d<0) document.getElementById('rkReplay').hidden=true;

  // ── 年终总决赛 top-N (race pages) ──
  const finalsN=parseInt(root.dataset.finals||'0',10)||0;
  const finalsSet=new Set();
  if(finalsN&&C.rank>=0){
    rows.forEach(r=>{ const k=parseInt(txt(r,C.rank),10); if(k>0&&k<=finalsN){ finalsSet.add(r); if(k===finalsN) r._finLast=true; } });
    if(finalsSet.size){ document.getElementById('rkFinals').hidden=false; document.getElementById('rkFinalsN').textContent=finalsN; }
  }

  // ── per-<tr> setup, run as TS.el creates each row (and now for rows that already exist) ──
  function decorate(r,tr){
    if(C.user>=0&&tr.cells[C.user]) userCell(tr.cells[C.user],uname(r));
    if(finalsSet.has(r)){ tr.classList.add('rk-final'); if(r._finLast) tr.classList.add('rk-final-last'); }
    paintRow(r);
  }
  TS.onRow.push(decorate);
  rows.forEach(r=>{ if(r.el) decorate(r,r.el); });

  // ── dialogs (focus trap, Esc, backdrop) ──
  let lastFocus=null;
  function openModal(m,from){ lastFocus=from||document.activeElement; m.hidden=false; document.body.style.overflow='hidden';
    const d=m.querySelector('.rk-dlg'); d.focus(); }
  function closeModal(m){ if(m.hidden) return; m.hidden=true; document.body.style.overflow=''; if(m.id==='rkHelp') stopHelp();
    if(lastFocus&&lastFocus.focus) lastFocus.focus({preventScroll:true}); }
  [...root.querySelectorAll('.rk-modal')].forEach(m=>{
    m.dataset.tour=root.dataset.tour||''; document.body.appendChild(m);
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

  // ── 选人历史 ──
  const hist=document.getElementById('rkHist');
  function openHist(r,from){
    if(!hist||r.d===undefined) return;
    const picks=Array.isArray(r.d)?r.d:[];
    const u=uname(r), stCell=cellHtml(r,C.st);
    document.getElementById('rkHistName').textContent=u;
    const stat=(k,v)=>'<span>'+k+'<b>'+v+'</b></span>';
    document.getElementById('rkHistStats').innerHTML=stat(ths[C.rank]||'排名','#'+esc(txt(r,C.rank)))
      +(C.pts>=0?stat(ths[C.pts],esc(txt(r,C.pts))):'')
      +(C.days>=0?stat('存活天数',esc(txt(r,C.days)||'0')):'')
      +(C.st>=0?'<span>当前状态'+stCell+'</span>':'');
    const h=tsHist({picks, st:txt(r,C.st), stHtml:stCell, days:txt(r,C.days), hasSt:C.st>=0,
      main:C.main>=0?txt(r,C.main):'', alt:C.alt>=0?txt(r,C.alt):''});
    document.getElementById('rkHistList').innerHTML=h.rows;
    document.getElementById('rkHistSum').textContent=h.sum;
    openModal(hist,from);
  }
  table.addEventListener('click',e=>{ if(e.target.closest('.rk-star')) return; const tr=e.target.closest('tbody tr'); if(tr&&tr._m) openHist(tr._m,tr); });

  // ── 使用说明 ──
  const help=document.getElementById('rkHelp'), HELP_KEY='ts.help.v1';
  const steps=help?[...help.querySelectorAll('.hp-step')]:[], bars=help?[...help.querySelectorAll('.hp-bar')]:[];
  let step=0, helpT=0;
  function showStep(i){
    step=Math.max(0,Math.min(steps.length-1,i));
    steps.forEach((s,k)=>{ s.hidden=k!==step; });
    bars.forEach((b,k)=>{ b.classList.toggle('done',k<step); b.classList.remove('now'); });
    void help.offsetWidth; bars[step].classList.add('now');
    document.getElementById('rkHelpNo').textContent=step+1;
    document.getElementById('rkHelpPrev').disabled=step===0;
    document.getElementById('rkHelpNext').textContent=step===steps.length-1?'开始使用':'下一步';
    clearTimeout(helpT);
    if(!still()) helpT=setTimeout(()=>showStep(step===steps.length-1?0:step+1),5000);
  }
  function stopHelp(){ clearTimeout(helpT); }
  if(help){
    const btn=document.getElementById('rkHelpBtn');
    if(btn) btn.addEventListener('click',()=>{ openModal(help,btn); showStep(0); });
    document.getElementById('rkHelpPrev').addEventListener('click',()=>showStep(step-1));
    document.getElementById('rkHelpNext').addEventListener('click',()=>{ if(step===steps.length-1) closeModal(help); else showStep(step+1); });
    document.getElementById('rkHelpMute').addEventListener('click',()=>{ try{ localStorage.setItem(HELP_KEY,'1'); }catch(e){} closeModal(help); });
    // pause the auto-advance while the pointer or focus is inside
    const dlg=help.querySelector('.rk-dlg');
    dlg.addEventListener('pointerenter',e=>{ if(e.pointerType==='mouse'){ stopHelp(); bars[step]&&bars[step].classList.add('paused'); } });
    dlg.addEventListener('pointerleave',e=>{ if(e.pointerType==='mouse'){ bars[step]&&bars[step].classList.remove('paused'); showStep(step); } });
    let seen=false; try{ seen=localStorage.getItem(HELP_KEY)==='1'; }catch(e){ seen=true; }
    if(!seen&&!location.hash){ try{ localStorage.setItem(HELP_KEY,'1'); }catch(e){} setTimeout(()=>{ openModal(help,btn); showStep(0); },600); }
  }

  // ── default order: rank ascending (the table's own header sort stays available) ──
  if(C.rank>=0){
    const num=r=>{ const n=parseFloat(txt(r,C.rank)); return isNaN(n)?Infinity:n; };
    TS.setOrder(rows.slice().sort((a,b)=>num(a)-num(b)));
  }

  // ── column filters: v3 popovers on top of _JS_TABLE's dropdowns (moved to <body>, same order as columns) ──
  const fTrig=[...table.querySelectorAll('.filter-row .filter-trigger')];
  const fPops=[...document.querySelectorAll('body > .dropdown-content')];
  const fCbs=pop=>[...pop.querySelectorAll('.option-item:not([data-select-all]) input[type="checkbox"]')];
  if(fTrig.length&&fTrig.length===fPops.length){
    fTrig.forEach((tr,i)=>{
      const pop=fPops[i], head=ths[i]||'', range=pop.classList.contains('filter-slider');
      pop.classList.add('rk-fpop'); pop.setAttribute('role','dialog'); pop.setAttribute('aria-label','筛选 '+head);
      tr.setAttribute('role','button'); tr.tabIndex=0; tr.setAttribute('aria-haspopup','dialog');
      tr.setAttribute('aria-expanded','false'); tr.setAttribute('aria-label','筛选 '+head);
      const chev=tr.lastElementChild; chev.removeAttribute('style'); chev.className='rk-chev'; chev.setAttribute('aria-hidden','true'); chev.textContent='▾';
      pop.insertAdjacentHTML('afterbegin','<span class="rk-eye rk-pop-eye">'+esc(head)+' · '+(range?'RANGE':'FILTER')+'</span>');
      if(!range){
        const all=pop.querySelector('.select-all-item'); if(all) all.removeAttribute('style');
        const box=document.createElement('div'); box.className='rk-fopts';
        pop.appendChild(box);
        // _JS_TABLE builds the value list on first open: count and move the items in then
        pop.addEventListener('ts:options',()=>{
          const counts=new Map(); rows.forEach(r=>{ const v=txt(r,i); counts.set(v,(counts.get(v)||0)+1); });
          pop.querySelectorAll(':scope > .option-item:not([data-select-all])').forEach(it=>{
            const v=it.querySelector('input').value;
            if(v==='') it.querySelector('span').textContent='（空）';
            it.insertAdjacentHTML('beforeend','<em class="n">'+(counts.get(v)||0)+'</em>'); box.appendChild(it); });
        });
      }
      pop.insertAdjacentHTML('beforeend','<div class="rk-pop-ft"><button type="button" class="rk-btn-text" data-f="clr">清除</button><button type="button" class="rk-btn rk-btn-pri" data-f="done">完成</button></div>');
      const close=()=>{ pop.classList.remove('show'); tr.focus({preventScroll:true}); };
      pop.addEventListener('click',e=>{ const b=e.target.closest('[data-f]'); if(!b) return;
        if(b.dataset.f==='done') return close();
        if(range){ const rs=pop.querySelector('.filter-slider-reset'); if(rs) rs.click(); return; }
        const q=pop.querySelector('.dropdown-search'); if(q&&q.value){ q.value=''; q.dispatchEvent(new Event('input')); }
        const sa=pop.querySelector('[data-select-all] input'); if(sa){ sa.checked=true; sa.dispatchEvent(new Event('change',{bubbles:true})); } });
      pop.addEventListener('keydown',e=>{ if(e.key==='Escape'){ e.stopPropagation(); close(); } });
      tr.addEventListener('keydown',e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); tr.click(); } });
      // aria-expanded follows _JS_TABLE's .show toggling; focus the first field on open
      new MutationObserver(()=>{ const o=pop.classList.contains('show'); if(tr.getAttribute('aria-expanded')===String(o)) return;
        tr.setAttribute('aria-expanded',String(o));
        if(o){ const f=pop.querySelector('.dropdown-search,input[type=number]'); if(f) f.focus({preventScroll:true}); } }).observe(pop,{attributes:true,attributeFilter:['class']});
    });
    // trigger shows what is selected ("西里奇 等 2 项" / "1 ~ 10"); .on marks an active column filter
    const paintTriggers=()=>fTrig.forEach((tr,i)=>{
      const pop=fPops[i], lbl=tr.firstElementChild; let on;
      if(pop.classList.contains('filter-slider')) on=lbl.textContent!=='全部';
      else { const cbs=fCbs(pop), sel=cbs.filter(c=>c.checked); on=sel.length>0&&sel.length<cbs.length;
        lbl.textContent=on?((sel[0].value||'（空）')+(sel.length>1?' 等 '+sel.length+' 项':'')):'全部'; }
      tr.classList.toggle('on',on); });
    document.addEventListener('ts:filtered',paintTriggers); paintTriggers();
  }

  // ── boot ──
  renderChips(); renderWatch(); paintAll(); renderMe();
  if(location.hash==='#watch'&&allFav().size){ list='*'; renderWatch(); renderChips(); }
  TS.refresh(); freeze();
  window.addEventListener('resize',()=>{ clearTimeout(freeze._t); freeze._t=setTimeout(syncLayout,150); });
  // #u=<name>: opened from the watch page — jump to that user's row
  const hu=location.hash.match(/^#u=(.+)$/);
  if(hu){ let u=''; try{ u=decodeURIComponent(hu[1]); }catch(e){}
    if(byUser.has(u)){ setTimeout(()=>jumpTo(u),300); return; } }
  requestAnimationFrame(()=>play());
});
})();
