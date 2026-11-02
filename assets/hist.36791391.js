
function tsGrp(s){ if(s==='存活')return 'alive'; if(s==='未完赛')return 'live'; if(s==='轮空')return 'bye'; if(s==='未选')return 'none';
  if(s==='未参赛'||s==='')return 'absent'; if(s.indexOf('自杀')===0)return 'suicide'; if(s==='球员输球'||s==='球员退赛')return 'out'; return 'other'; }
function tsEsc(s){ return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
// same classes as _status_badge_html
function tsBadge(s){ s=String(s||'').trim(); if(!s) return '';
  const c=(s==='存活'||s==='轮空')?'st-alive':(s==='未完赛'||s==='未选')?'st-live':(s==='球员输球'||s==='球员退赛'||s==='未参赛'||s.indexOf('自杀')===0)?'st-out':'st-other';
  return '<span class="st-badge '+c+'">'+tsEsc(s)+'</span>'; }
// Username combobox in the site's own popover (a native <datalist> popup can't be styled and
// renders white-on-white in some browsers). o: {match(q) → {opts, note}, meta(u) → text,
// pick(u, typed), eye, host (card raised while the list is open)}. Enter picks the highlighted option, or passes the typed text (typed=true).
function tsSuggest(input,pop,o){
  let opts=[], act=-1;
  input.setAttribute('role','combobox'); input.setAttribute('aria-autocomplete','list');
  input.setAttribute('aria-controls',pop.id); input.setAttribute('aria-expanded','false');
  const optId=i=>pop.id+'-o'+i;
  function paint(){ [...pop.querySelectorAll('.rk-opt')].forEach((b,i)=>b.setAttribute('aria-selected',String(i===act)));
    input.setAttribute('aria-activedescendant',act>=0?optId(act):''); }
  const lift=on=>{ if(o.host) o.host.classList.toggle('rk-sug-open',on); };
  function close(){ lift(false); pop.hidden=true; input.setAttribute('aria-expanded','false'); input.setAttribute('aria-activedescendant',''); }
  function show(){
    const q=input.value.trim(); if(!q){ opts=[]; act=-1; close(); return; }
    const r=o.match(q.toLowerCase()); opts=r.opts||[]; act=opts.length?0:-1;
    pop.innerHTML=opts.length?(o.eye?'<span class="rk-eye rk-pop-eye">'+o.eye+'</span>':'')+opts.map((u,i)=>
      '<button type="button" role="option" tabindex="-1" class="rk-opt" id="'+optId(i)+'" data-u="'+tsEsc(u)+'" aria-selected="'+(i===act)+'"><span class="rk-opt-l">'+tsEsc(u)+'</span>'
      +(o.meta?'<span class="t">'+tsEsc(o.meta(u))+'</span>':'')+'</button>').join('')
      :'<span class="rk-note">'+tsEsc(r.note||'')+'</span>';
    lift(true); pop.hidden=false; input.setAttribute('aria-expanded','true'); paint();
  }
  input.addEventListener('input',()=>{ input.setCustomValidity(''); show(); });
  input.addEventListener('focus',()=>{ if(input.value.trim()) show(); });
  input.addEventListener('keydown',e=>{
    if((e.key==='ArrowDown'||e.key==='ArrowUp')&&opts.length&&!pop.hidden){ e.preventDefault(); act=(act+(e.key==='ArrowDown'?1:-1)+opts.length)%opts.length; paint(); }
    else if(e.key==='Enter'){ e.preventDefault(); const u=!pop.hidden&&act>=0?opts[act]:''; close(); o.pick(u||input.value.trim(),!u); }
    else if(e.key==='Escape'&&!pop.hidden){ e.stopPropagation(); close(); } });
  pop.addEventListener('mousedown',e=>e.preventDefault());  // keep focus in the input
  pop.addEventListener('click',e=>{ e.stopPropagation(); const b=e.target.closest('.rk-opt'); if(b){ close(); o.pick(b.dataset.u,false); } });
  document.addEventListener('click',e=>{ if(e.target!==input&&!pop.contains(e.target)) close(); });
  // the highlighted option, for a separate submit button
  return {current:()=>!pop.hidden&&act>=0?opts[act]:'', refresh:show, close};
}
// default matcher: names containing q, earliest match then shortest first
function tsMatch(names,q,skip){
  const hit=names.filter(u=>u.toLowerCase().includes(q));
  const opts=hit.filter(u=>!(skip&&skip(u))).sort((a,b)=>(a.toLowerCase().indexOf(q)-b.toLowerCase().indexOf(q))||a.length-b.length).slice(0,8);
  return {opts, hit};
}
// o: {picks, st, stHtml, days, main, alt, hasSt} → {rows (html), sum (text)}
function tsHist(o){
  const picks=Array.isArray(o.picks)?o.picks:[];
  // picks are per-day entries (a bye is stored as 轮空). 存活天数 = settled days the user
  // survived, so entries [0, survived) are settled and the entry at [survived] — if any —
  // is the deciding day: today's pick, or the pick that knocked the user out. Without it
  // the status goes on a new row (today's pick, or "-" when nothing was submitted).
  const g=tsGrp(o.st||''), survived=parseInt(o.days,10);
  const items=picks.map(v=>{ const raw=String(v).trim(), bye=raw==='轮空';
    return {val:bye?'':raw, bye, res:null}; });
  const today={val:o.main||'', bye:g==='bye', res:o.stHtml, alt:o.alt||''};
  if(!isNaN(survived)){
    if(items.length>survived){ items.length=survived+1; const it=items[survived]; it.res=o.stHtml;
      if(o.main&&it.val===o.main) it.alt=o.alt||''; }
    else if(g!=='absent'&&o.hasSt){
      // live settlement can credit today's pick into picks (存活天数 advanced) while 今日主选
      // still shows it: that entry is today, not a new day. Players never repeat, and an
      // early-retirement backup lands in picks under the backup's name.
      const lastIt=items[items.length-1];
      const same=lastIt&&!lastIt.bye&&lastIt.val&&(lastIt.val===o.main||(o.alt&&lastIt.val===o.alt));
      if(items.length===survived&&same){ lastIt.res=o.stHtml; lastIt.alt=o.alt||''; }
      else items.push(today);
    }
  } else {
    // no 存活天数 (e.g. combined pages): players never repeat, so a last entry equal to
    // 今日主选 — or a bye while the status is 轮空 — is today, not a settled day
    const lastIt=items[items.length-1];
    if(lastIt&&((o.main&&lastIt.val===o.main)||(lastIt.bye&&g==='bye'))){ lastIt.res=o.stHtml; lastIt.alt=o.alt||''; }
    else if(g!=='absent'&&o.hasSt) items.push(today);
  }
  const last=items.length-1;
  const rows=items.length?items.map((it,i)=>{
    const empty=!it.val||it.val.toLowerCase()==='nan';
    const res=it.res!=null?it.res:it.bye?'<span class="st-badge st-alive">轮空</span>'
      :empty?'<span class="st-badge st-out">未选</span>':'<span class="st-badge st-alive">晋级</span>';
    const alt=it.alt&&!empty?'<span class="a">备 '+tsEsc(it.alt)+'</span>':'';
    return '<div class="rk-hist-row'+(i===last?' today':'')+'" style="animation-delay:'+Math.min(i,12)*50+'ms"><b>'+(i+1)+'</b>'
      +'<span class="p'+(empty?' none':'')+'">'+(empty?'-':tsEsc(it.val))+alt+'</span>'+res+'</div>';
  }).join(''):'<div class="rk-empty">暂无选人记录</div>';
  // a bye is a pick (the user entered); a pick that broke the rules (自杀) is not
  const valid=items.filter(it=>(it.bye||(it.val&&it.val.toLowerCase()!=='nan'))&&!(g==='suicide'&&it.res!=null)).length;
  return {rows, sum:'共 '+items.length+' 天 · '+valid+' 天有效选人 · 点击空白处或按 Esc 关闭'};
}
