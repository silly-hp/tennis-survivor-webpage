
(function(){
function ready(fn){ if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',fn); else fn(); }
ready(function(){
  const root=document.getElementById('wl'); if(!root) return;
  let D; try{ D=JSON.parse(document.getElementById('wlData').textContent); }catch(e){ return; }
  const TOURS=['ATP','WTA'], KEY='ts.watch.v1', esc=tsEsc;
  const $=id=>document.getElementById(id);
  const has=u=>TOURS.some(t=>D[t].users[u]);
  const ALL=[...new Set(TOURS.flatMap(t=>Object.keys(D[t].users)))];

  // ── storage (throws on data: URLs / private mode) ──
  function load(){ try{ const v=JSON.parse(localStorage.getItem(KEY)||'null'); if(v&&Array.isArray(v.lists)) return v; }catch(e){} return {me:'',lists:[]}; }
  let S=load(); if(typeof S.me!=='string') S.me='';
  function save(){ try{ localStorage.setItem(KEY,JSON.stringify(S)); }catch(e){} }
  const newId=()=>'l'+Date.now().toString(36)+Math.random().toString(36).slice(2,5);

  let tab='', creating=false;   // '' = 全部
  const cur=()=>S.lists.find(l=>l.id===tab);
  const listed=()=>[...new Set(S.lists.flatMap(l=>l.users))];
  const tagsOf=u=>S.lists.filter(l=>l.users.includes(u)).map(l=>l.name);
  function shown(){ const l=cur(); const base=(l?l.users:listed()).filter(u=>u!==S.me);
    // users out on every tour they play sink below the rest; "me" stays first
    const out=base.filter(goneAll), rest=base.filter(u=>!goneAll(u));
    return (S.me?[S.me]:[]).concat(rest,out); }
  function goneAll(u){ const st=TOURS.map(t=>D[t].users[u]).filter(Boolean).map(x=>tsGrp(x.s||''));
    return st.length>0&&st.every(g=>g==='out'||g==='suicide'); }
  const live=msg=>{ $('wlLive').textContent=msg; };

  // ── list tabs, create, rename, delete ──
  const tabsBox=$('wlTabs'), newBox=$('wlNew'), manage=$('wlManage');
  function renderTabs(){
    if(tab&&!cur()) tab='';
    const n=listed().filter(u=>u!==S.me).length+(S.me?1:0);
    tabsBox.innerHTML=[['','全部',n],...S.lists.map(l=>[l.id,l.name,l.users.length])].map(([id,name,c])=>
      '<button type="button" class="rk-tab" data-l="'+id+'" aria-pressed="'+(tab===id)+'">'+esc(name)+'<span class="n">'+c+'</span></button>').join('');
    newBox.innerHTML=creating
      ?'<form class="rk-new-form" id="wlNewForm"><input class="rk-input" name="n" maxlength="20" placeholder="列表名，如 上海群友" aria-label="新列表名"><button type="submit" class="rk-btn rk-btn-sm rk-btn-pri">创建</button><button type="button" class="rk-btn-text" data-cancel="1">取消</button></form>'
      :'<button type="button" class="rk-tab rk-tab-new" id="wlNewBtn">+ 新建列表</button>';
    if(creating){ const i=newBox.querySelector('input'); i&&i.focus(); }
    const l=cur(); manage.hidden=!l;
    if(l&&!manage.dataset.edit) manage.innerHTML='<span class="wl-manage-t">当前列表 <b>'+esc(l.name)+'</b> · 点卡片右上角 ✕ 移出此列表</span>'
      +'<button type="button" class="rk-btn rk-btn-sm" data-a="rename">重命名</button><button type="button" class="rk-btn rk-btn-sm" data-a="del" style="color:var(--bad)">删除列表</button>';
    $('wlAdd').placeholder='添加到「'+(l?l.name:(S.lists[0]?S.lists[0].name:'关注'))+'」';
    $('wlCount').textContent=n?n+' 人':'';
  }
  tabsBox.addEventListener('click',e=>{ const b=e.target.closest('.rk-tab'); if(!b) return; tab=b.dataset.l; delete manage.dataset.edit; render(); });
  newBox.addEventListener('click',e=>{ if(e.target.id==='wlNewBtn'){ creating=true; renderTabs(); } else if(e.target.dataset.cancel){ creating=false; renderTabs(); } });
  newBox.addEventListener('submit',e=>{ e.preventDefault(); const n=e.target.n.value.trim(); creating=false;
    if(n){ const id=newId(); S.lists.push({id,name:n,users:[]}); tab=id; save(); live('已新建列表「'+n+'」'); } render(); });
  newBox.addEventListener('keydown',e=>{ if(e.key==='Escape'){ creating=false; renderTabs(); $('wlNewBtn')&&$('wlNewBtn').focus(); } });
  manage.addEventListener('click',e=>{ const l=cur(); if(!l) return; const a=e.target.closest('[data-a]'); if(!a) return;
    if(a.dataset.a==='rename'){ manage.dataset.edit='1';
      manage.innerHTML='<label class="rk-note" for="wlRename">名称</label><input class="rk-input" id="wlRename" maxlength="20" value="'+esc(l.name)+'"><button type="button" class="rk-btn rk-btn-sm rk-btn-pri" data-a="save">保存</button><button type="button" class="rk-btn-text" data-a="cancel">取消</button>';
      const i=$('wlRename'); i.focus(); i.select(); }
    if(a.dataset.a==='save'){ const n=$('wlRename').value.trim(); if(n){ l.name=n; save(); } delete manage.dataset.edit; render(); }
    if(a.dataset.a==='cancel'){ delete manage.dataset.edit; renderTabs(); }
    if(a.dataset.a==='del') ask('删除列表「'+l.name+'」？','列表里的 '+l.users.length+' 人只会从这个列表移出，其他列表不受影响。','删除列表',a,()=>{
      S.lists=S.lists.filter(x=>x!==l); tab=''; save(); live('已删除列表「'+l.name+'」'); render(); $('wlTabs').querySelector('.rk-tab').focus(); }); });
  manage.addEventListener('keydown',e=>{ if(e.target.id!=='wlRename') return;
    if(e.key==='Enter'){ e.preventDefault(); manage.querySelector('[data-a="save"]').click(); }
    if(e.key==='Escape'){ delete manage.dataset.edit; renderTabs(); } });

  // ── add a user (suggestions from both tours) ──
  const add=$('wlAdd'), tours=u=>TOURS.filter(t=>D[t].users[u]).join(' · ');
  function addUser(u){
    if(!u||!has(u)){ add.setCustomValidity('找不到这个用户名'); add.reportValidity(); return; }
    let l=cur(); if(!l){ l=S.lists[0]; if(!l){ l={id:newId(),name:'关注',users:[]}; S.lists.push(l); } }
    if(!l.users.includes(u)) l.users.push(u);
    save(); add.value=''; addSug.close(); render(); live('已把 '+u+' 加入「'+l.name+'」');
  }
  const addSug=tsSuggest(add,$('wlSug'),{eye:'ATP + WTA USERS', meta:tours, pick:u=>addUser(u), host:$('wlBar'),
    match:q=>{ const l=cur(), inList=new Set(l?l.users:listed());
      const m=tsMatch(ALL,q,u=>inList.has(u)||u===S.me);
      return {opts:m.opts, note:m.hit.length?'匹配的用户都已在这个列表里':'找不到包含「'+add.value.trim()+'」的用户'}; }});
  $('wlAddBtn').addEventListener('click',()=>addUser(addSug.current()||add.value.trim()));

  // ── first visit: set "me" / create a list ──
  const meIn=$('wlMeInput');
  function setMe(v){ if(!has(v)){ meIn.setCustomValidity('找不到这个用户名'); meIn.reportValidity(); return; } S.me=v; meIn.value=''; save(); render(); }
  const meSug=tsSuggest(meIn,$('wlMeSug'),{eye:'ATP + WTA USERS', meta:tours, pick:u=>setMe(u), host:$('wlStart'),
    match:q=>{ const m=tsMatch(ALL,q); return {opts:m.opts, note:'找不到包含「'+meIn.value.trim()+'」的用户'}; }});
  $('wlMeForm').addEventListener('submit',e=>{ e.preventDefault(); setMe(meSug.current()||meIn.value.trim()); });
  $('wlStartNew').addEventListener('click',()=>{ creating=true; S.lists.length||S.me||($('wlStart').hidden=true); $('wlBar').hidden=false; renderTabs(); });

  // ── cards ──
  const KILL='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M14.5 4.5l5 5L9 20H4v-5z"/></svg>';
  const GO='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>';
  const X='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
  function deltaHtml(d){ d=parseInt(d,10)||0; return d>0?'<span class="rank up">▲'+d+'</span>':d<0?'<span class="rank down">▼'+(-d)+'</span>':'<span class="rank same">—</span>'; }
  const dash=v=>v==null||v===''?'—':esc(v);
  function panel(t,u){
    const T=D[t], x=T.users[u], ev=T.event?t+' · '+esc(T.event):t;
    const head='<span class="wl-t-eye">'+ev+'</span>';
    if(!T.event) return '<div class="wl-t off" data-t="'+t+'">'+head+'<span class="wl-t-msg">本周无赛事</span></div>';
    if(!x) return '<div class="wl-t off" data-t="'+t+'">'+head+'<span class="wl-t-msg">未参加本站</span></div>';
    const g=tsGrp(x.s||''), lost=g==='out'||g==='suicide', h=x.h||[];
    const big='<div class="wl-t-big"><span class="wl-t-rank">#'+dash(x.r)+'</span>'+deltaHtml(x.c)
      +'<span class="wl-t-pts">'+dash(x.p)+'<small> 分</small></span></div>';
    let body;
    if(lost){ const lastPick=h.length?h[h.length-1]:'';
      body=(x.k?'<span class="wl-t-kill">'+KILL+'<span>'+esc(x.k)+' · 存活 '+dash(x.d)+' 天</span></span>':'<span class="wl-t-kill">存活 '+dash(x.d)+' 天</span>')
        +(lastPick&&lastPick!=='轮空'?'<div class="wl-t-pk"><span>最后</span><b class="alt last">'+esc(lastPick)+'</b></div>':''); }
    else body='<div class="wl-t-pk"><span>主选</span><b>'+(x.m?esc(x.m):'今日未选')+'</b><span>备选</span><b class="alt">'+dash(x.a)+'</b></div>';
    return '<a class="wl-t'+(lost?' lost':'')+'" data-t="'+t+'" href="'+T.href+'#u='+encodeURIComponent(u)+'" aria-label="在 '+t+' 排名中定位 '+esc(u)+'">'
      +head+big+tsBadge(x.s)+body+'<span class="wl-t-go">在 '+t+' 排名中定位'+GO+'</span></a>';
  }
  function card(u){
    const me=u===S.me, l=cur(), t=me?[]:tagsOf(u);
    // badge only when out on both tours (absent from one tour does not count)
    const gone=TOURS.every(k=>D[k].users[u]&&['out','suicide'].includes(tsGrp(D[k].users[u].s||'')));
    return '<article class="wl-card'+(me?' me':'')+'" data-u="'+esc(u)+'"><div class="wl-hd">'
      +'<button type="button" class="wl-name" data-hist="1" aria-haspopup="dialog" title="查看选人历史">'+esc(u)+'</button>'
      +(me?'<span class="rk-mebadge">我</span>':'')
      +(t.length&&!l?'<span class="rk-tags">'+esc(t.join(' · '))+'</span>':'')
      +(gone?'<span class="wl-gone">本周已全部出局</span>':'')
      +(l&&!me?'<button type="button" class="wl-rm" data-rm="1" aria-label="把 '+esc(u)+' 移出「'+esc(l.name)+'」" title="移出此列表">'+X+'</button>':'')
      +'</div><div class="wl-tours">'+TOURS.map(k=>panel(k,u)).join('')+'</div></article>';
  }
  const grid=$('wlGrid'), empty=$('wlEmpty');
  function render(){
    const fresh=!S.me&&!S.lists.length;
    $('wlStart').hidden=!fresh; $('wlBar').hidden=fresh&&!creating;
    $('wlShare').parentNode.hidden=fresh;
    renderTabs();
    const us=shown().filter(has);
    grid.innerHTML=us.map(card).join('');
    const l=cur();
    empty.hidden=fresh||us.length>(S.me&&has(S.me)?1:0);
    empty.innerHTML=l?'「'+esc(l.name)+'」还没有人。<br>在上方输入用户名添加，或在排名页点任意行的 ☆。'
      :'还没有关注任何人。<br>在上方输入用户名添加，或在排名页点任意行的 ☆。';
  }
  grid.addEventListener('click',e=>{
    const c=e.target.closest('.wl-card'); if(!c) return; const u=c.dataset.u;
    const rm=e.target.closest('[data-rm]');
    if(rm){ const l=cur(); if(!l) return;
      ask('把 '+u+' 移出「'+l.name+'」？','只从这个列表移出，不影响其他列表。','移出',rm,()=>{
        l.users=l.users.filter(x=>x!==u); save(); render(); live('已把 '+u+' 移出「'+l.name+'」'); $('wlAdd').focus(); });
      return; }
    if(e.target.closest('[data-hist]')) openHist(u,e.target.closest('[data-hist]'));
  });
  // hover lift for mouse only (touch scrolling fires pointer events too)
  grid.addEventListener('pointerover',e=>{ if(e.pointerType!=='mouse') return; const c=e.target.closest('.wl-card'); if(c) c.classList.add('hov'); });
  grid.addEventListener('pointerout',e=>{ const c=e.target.closest('.wl-card'); if(c&&!c.contains(e.relatedTarget)) c.classList.remove('hov'); });

  // ── 复制分享链接 (#w=) ──
  const b64e=s=>btoa(unescape(encodeURIComponent(s))), b64d=s=>decodeURIComponent(escape(atob(s)));
  const shareBtn=$('wlShare'), shareIn=shareBtn.querySelector('.cp-in'), note=$('wlShareNote'), IDLE=shareIn.innerHTML;
  const OK='<svg class="cp-draw" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg>已复制';
  const ERR='<svg class="cp-draw" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>复制失败';
  let shareT=0;
  function shareState(ok,msg){
    clearTimeout(shareT); shareBtn.classList.remove('ok','err','back'); void shareBtn.offsetWidth;
    shareBtn.classList.add(ok?'ok':'err'); shareIn.innerHTML=ok?OK:ERR;
    note.textContent=msg; note.classList.toggle('err',!ok);
    shareT=setTimeout(()=>{ shareBtn.classList.remove('ok','err'); shareBtn.classList.add('back'); shareIn.innerHTML=IDLE; note.textContent=''; },1500);
  }
  shareBtn.addEventListener('click',()=>{
    if(!S.lists.length){ shareState(false,'先新建一个列表'); return; }
    const url=location.href.split('#')[0]+'#w='+encodeURIComponent(b64e(JSON.stringify(S.lists.map(l=>({n:l.name,u:l.users})))));
    // no clipboard: put the link in the address bar so it can be copied by hand
    const fail=()=>{ try{ history.replaceState(null,'',url); }catch(e){} shareState(false,'剪贴板不可用，链接已放在地址栏，请手动复制'); };
    try{ navigator.clipboard.writeText(url).then(()=>shareState(true,'链接含全部 '+S.lists.length+' 个列表'),fail); }catch(e){ fail(); }
  });
  (function readShare(){
    const m=location.hash.match(/^#w=(.+)$/); if(!m) return;
    let data; try{ data=JSON.parse(b64d(decodeURIComponent(m[1]))); }catch(e){ return; }
    if(!Array.isArray(data)||!data.length) return;
    // our own link (e.g. left in the address bar after a failed copy): nothing to import
    if(JSON.stringify(data)===JSON.stringify(S.lists.map(l=>({n:l.name,u:l.users})))){ try{ history.replaceState(null,'',location.pathname+location.search); }catch(e){} return; }
    const box=$('wlImport'); box.hidden=false;
    box.innerHTML='<div><span class="rk-eye">SHARED WITH YOU</span><h2>收到分享的关注列表 · '+data.length+' 个</h2></div>'
      +'<div class="wl-lists">'+data.map(d=>'<span>'+esc(String(d.n||'分享列表'))+' <b>'+((d.u||[]).length)+'</b> 人</span>').join('')+'</div>'
      +'<span class="rk-note">合并：同名列表合并成员，新列表直接加入。替换：用分享的列表覆盖你本机的全部列表（“我”保留）。</span>'
      +'<div class="wl-act"><button type="button" class="rk-btn rk-btn-pri" data-a="merge">合并到我的列表</button><button type="button" class="rk-btn" data-a="replace">替换</button><button type="button" class="rk-btn-text" data-a="no">忽略</button></div>';
    box.addEventListener('click',e=>{ const b=e.target.closest('[data-a]'); if(!b) return; const a=b.dataset.a;
      const inc=data.map((d,i)=>({id:'s'+Date.now().toString(36)+i,name:String(d.n||'分享列表'),users:(d.u||[]).map(String)}));
      if(a==='replace') S.lists=inc;
      if(a==='merge') inc.forEach(x=>{ const same=S.lists.find(l=>l.name===x.name); if(same) x.users.forEach(u=>{ if(!same.users.includes(u)) same.users.push(u); }); else S.lists.push(x); });
      box.hidden=true; try{ history.replaceState(null,'',location.pathname+location.search); }catch(err){}
      if(a!=='no'){ save(); tab=''; render(); live(a==='merge'?'已合并分享的列表':'已替换为分享的列表'); } });
  })();

  // ── 选人历史 (same dialog + day alignment as the ranking page) ──
  const hist=$('rkHist'); let hUser='', hTour='ATP', lastFocus=null;
  document.body.appendChild(hist);
  const seg=$('rkHistSeg');
  function fillHist(){
    const T=D[hTour], x=T.users[hUser]||{};
    hist.dataset.tour=hTour;
    $('rkHistEye').textContent='PICK HISTORY · '+hTour+(T.event?' '+T.event:'');
    $('rkHistName').textContent=hUser;
    [...seg.querySelectorAll('button')].forEach(b=>{ b.setAttribute('aria-pressed',String(b.dataset.t===hTour)); b.disabled=!D[b.dataset.t].users[hUser]; });
    const stHtml=tsBadge(x.s), stat=(k,v)=>'<span>'+k+'<b>'+v+'</b></span>';
    $('rkHistStats').innerHTML=stat('即时排名','#'+dash(x.r))+stat('即时积分',dash(x.p))+stat('存活天数',dash(x.d==null?0:x.d))+'<span>当前状态'+stHtml+'</span>';
    const h=tsHist({picks:x.h||[], st:x.s||'', stHtml, days:x.d, main:x.m||'', alt:x.a||'', hasSt:true});
    $('rkHistList').innerHTML=h.rows; $('rkHistSum').textContent=h.sum;
  }
  function openHist(u,from){
    hUser=u; hTour=D.ATP.users[u]?'ATP':'WTA'; if(!D[hTour].users[u]) return;
    fillHist(); lastFocus=from; hist.hidden=false; document.body.style.overflow='hidden'; hist.querySelector('.rk-dlg').focus();
  }
  function closeHist(){ if(hist.hidden) return; hist.hidden=true; document.body.style.overflow=''; if(lastFocus) lastFocus.focus({preventScroll:true}); }
  seg.addEventListener('click',e=>{ const b=e.target.closest('button'); if(!b||b.disabled) return; hTour=b.dataset.t; fillHist(); });
  hist.addEventListener('click',e=>{ if(e.target===hist||e.target.closest('[data-close]')) closeHist(); });
  hist.addEventListener('keydown',e=>{
    if(e.key==='Escape'){ e.stopPropagation(); closeHist(); return; }
    if(e.key!=='Tab') return;
    const f=[...hist.querySelectorAll('button:not([disabled]),[href],input')].filter(x=>x.offsetParent!==null);
    if(!f.length) return; const a=f[0], z=f[f.length-1];
    if(e.shiftKey&&document.activeElement===a){ e.preventDefault(); z.focus(); }
    else if(!e.shiftKey&&document.activeElement===z){ e.preventDefault(); a.focus(); }
  });

  // ── in-page confirm (window.confirm is blocked in embedded browsers and returns false) ──
  const askBox=$('rkAsk'); document.body.appendChild(askBox);
  let askDo=null, askFrom=null;
  function ask(title,desc,okLabel,from,fn){
    $('rkAskT').textContent=title; $('rkAskD').textContent=desc; $('rkAskOk').textContent=okLabel;
    askDo=fn; askFrom=from; askBox.hidden=false; document.body.style.overflow='hidden';
    askBox.querySelector('[data-v="0"]').focus();
  }
  function askEnd(ok){ if(askBox.hidden) return; askBox.hidden=true; document.body.style.overflow='';
    const fn=askDo; askDo=null;
    if(ok&&fn) fn(); else if(askFrom&&askFrom.isConnected) askFrom.focus({preventScroll:true}); }
  askBox.addEventListener('click',e=>{ if(e.target===askBox) return askEnd(false); const b=e.target.closest('[data-v]'); if(b) askEnd(b.dataset.v==='1'); });
  askBox.addEventListener('keydown',e=>{
    if(e.key==='Escape'){ e.stopPropagation(); askEnd(false); return; }
    if(e.key!=='Tab') return;
    const f=[...askBox.querySelectorAll('button')], a=f[0], z=f[f.length-1];
    if(e.shiftKey&&document.activeElement===a){ e.preventDefault(); z.focus(); }
    else if(!e.shiftKey&&document.activeElement===z){ e.preventDefault(); a.focus(); }
  });

  // another tab edited the lists (ranking page ☆ menu)
  window.addEventListener('storage',e=>{ if(e.key===KEY){ S=load(); render(); } });
  render();
});
})();
