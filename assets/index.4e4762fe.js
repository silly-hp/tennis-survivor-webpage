
(function(){
  // ── tour switch for 数据查询 ──
  const seg=document.querySelectorAll('.seg button');
  function pick(t){
    seg.forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tour===t)));
    document.querySelectorAll('.nav-grid').forEach(g=>{g.hidden=g.dataset.group!==t;});
    try{localStorage.setItem('navTour',t);}catch(e){}
  }
  seg.forEach(b=>b.addEventListener('click',()=>pick(b.dataset.tour)));
  try{const t=localStorage.getItem('navTour');if(t&&document.querySelector('.nav-grid[data-group="'+t+'"]'))pick(t);}catch(e){}

  // ── hourly weather toggles ──
  document.querySelectorAll('.wx-toggle').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const panel=document.getElementById(btn.getAttribute('aria-controls'));
      const open=btn.getAttribute('aria-expanded')!=='true';
      btn.setAttribute('aria-expanded',String(open));
      panel.hidden=!open;
    });
  });

  // ── guide dialog ──
  const guide=document.getElementById('guide');
  document.querySelectorAll('.guide-open').forEach(b=>b.addEventListener('click',()=>guide.showModal()));
  guide.querySelector('.guide-close').addEventListener('click',()=>guide.close());
  guide.addEventListener('click',e=>{if(e.target===guide)guide.close();});

  // ── survivor trend charts ──
  const data=JSON.parse(document.getElementById('trend-data').textContent||'{}');
  const NS='http://www.w3.org/2000/svg', W=480, H=200, L=44, R=464, T=16, B=168;
  const el=(n,a)=>{const e=document.createElementNS(NS,n);for(const k in a)e.setAttribute(k,a[k]);return e;};
  // Monotone cubic (Fritsch–Carlson): one continuous smooth curve, no overshoot.
  function smooth(P){
    const n=P.length; if(n<2)return '';
    const h=P.map((p,i)=>i?p[0]-P[i-1][0]:0), d=[];
    for(let i=0;i<n-1;i++)d.push((P[i+1][1]-P[i][1])/(P[i+1][0]-P[i][0]));
    const m=P.map((p,i)=>i===0?d[0]:i===n-1?d[n-2]:(d[i-1]*d[i]<=0?0:(d[i-1]+d[i])/2));
    for(let i=0;i<n-1;i++){
      if(d[i]===0){m[i]=0;m[i+1]=0;continue;}
      const a=m[i]/d[i], b=m[i+1]/d[i], s=a*a+b*b;
      if(s>9){const t=3/Math.sqrt(s);m[i]=t*a*d[i];m[i+1]=t*b*d[i];}
    }
    let s='M'+P[0][0]+' '+P[0][1];
    for(let i=1;i<n;i++){const dx=(P[i][0]-P[i-1][0])/3;
      s+=' C'+(P[i-1][0]+dx)+' '+(P[i-1][1]+m[i-1]*dx)+' '+(P[i][0]-dx)+' '+(P[i][1]-m[i]*dx)+' '+P[i][0]+' '+P[i][1];}
    return s;
  }
  function detail(days,i){
    if(i===0)return '开赛前，全员在场';
    const c=days[i].checkin;
    if(c){ // current day: same counts as the ranking page's 今日选人统计
      const keep=['存活','未完赛','轮空','未选'], keys=keep.concat(Object.keys(c).filter(k=>!keep.includes(k)));
      const lost=Object.keys(c).filter(k=>!keep.includes(k)).reduce((s,k)=>s+c[k],0);
      return keys.filter(k=>c[k]).map(k=>k+' '+c[k]).join(' · ')+(lost?' · 共淘汰 '+lost:'');
    }
    const o=days[i].out||{}, parts=Object.keys(o).sort((a,b)=>a==='球员输球'?-1:b==='球员输球'?1:0).map(k=>k+' '+o[k]);
    const lost=days[i-1].alive-days[i].alive;
    return (parts.length?parts.join(' · '):'无人淘汰')+(lost?' · 共淘汰 '+lost:'');
  }
  document.querySelectorAll('.trend').forEach(box=>{
    const tr=data[box.dataset.tour]; if(!tr)return;
    const days=tr.days, n=days.length, svg=box.querySelector('.trend-svg');
    const x=i=>L+(n===1?0:i*(R-L)/(n-1)), y=v=>B-v/tr.total*(B-T);
    const P=days.map((d,i)=>[x(i),y(d.alive)]);
    let sel=n-1;
    function draw(){
      svg.innerHTML='';
      [0,Math.round(tr.total/2),tr.total].forEach(v=>{
        svg.appendChild(el('line',{class:'grid',x1:L,x2:R,y1:y(v),y2:y(v)}));
        const t=el('text',{x:L-8,y:y(v)+4,'text-anchor':'end'});t.textContent=v;svg.appendChild(t);
      });
      days.forEach((d,i)=>{const t=el('text',{x:x(i),y:H-8,'text-anchor':'middle'});t.textContent='Day '+i;svg.appendChild(t);});
      const path=smooth(P);
      svg.appendChild(el('path',{class:'area pop',d:path+' L'+x(n-1)+' '+B+' L'+x(0)+' '+B+' Z'}));
      const line=el('path',{class:'line draw',d:path});svg.appendChild(line);
      const len=Math.ceil(line.getTotalLength?line.getTotalLength():800);
      line.style.strokeDasharray=len;line.style.setProperty('--len',len);
      svg.appendChild(el('line',{class:'cursor',x1:0,x2:0,y1:T-6,y2:B}));
      P.forEach((p,i)=>{const c=el('circle',{class:'dot pop',cx:p[0],cy:p[1],r:4});c.style.animationDelay=(.25+i*.15)+'s';svg.appendChild(c);});
      show(sel);
    }
    const chips=box.querySelector('.trend-days'), tip=box.querySelector('.trend-tip');
    days.forEach((d,i)=>{const b=document.createElement('button');b.type='button';
      b.textContent='Day '+i;b.addEventListener('click',()=>show(i));chips.appendChild(b);});
    function show(i){
      sel=i;
      const cur=svg.querySelector('.cursor'); if(cur){cur.setAttribute('x1',x(i));cur.setAttribute('x2',x(i));}
      svg.querySelectorAll('.dot').forEach((c,k)=>c.setAttribute('r',k===i?6:4));
      chips.querySelectorAll('button').forEach((b,k)=>b.setAttribute('aria-pressed',String(k===i)));
      const live=tr.live&&i===n-1;
      tip.innerHTML='<div class="tt-hd"><span>Day '+i+(live?'（进行中）':'')+
        '</span><span>存活 <b>'+days[i].alive+'</b> / '+tr.total+'</span></div><span class="tt-sub">'+detail(days,i)+'</span>';
    }
    const at=e=>{const r=svg.getBoundingClientRect(), px=(e.clientX-r.left)/r.width*W;
      return Math.max(0,Math.min(n-1,Math.round((px-L)/((R-L)/Math.max(1,n-1)))));};
    // Mouse: follow the pointer. Touch: only a tap selects (scrolling must not).
    svg.addEventListener('pointermove',e=>{if(e.pointerType==='mouse')show(at(e));});
    svg.addEventListener('click',e=>show(at(e)));
    box.querySelector('.trend-replay').addEventListener('click',draw);
    draw();
  });
})();
