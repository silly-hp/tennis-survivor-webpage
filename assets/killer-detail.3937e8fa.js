(function(){
function ready(fn){ if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',fn); else fn(); }
ready(function(){
    const modal=document.getElementById('detail-modal');
    const closeBtn=document.getElementById('detail-close');
    const body=document.getElementById('detail-body');
    const metaLine=document.getElementById('detail-meta-line');
    const footer=document.getElementById('detail-footer');
    if(!modal||!closeBtn||!body)return;
    const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    function closeModal(){
        const card=modal.querySelector('.detail-card');
        if(card){ card.style.transform='translateY(10px) scale(.97)'; card.style.opacity='0'; }
        setTimeout(()=>{ modal.classList.remove('show'); if(card){ card.style.transform=''; card.style.opacity=''; } },220);
    }
    closeBtn.addEventListener('click',closeModal);
    modal.addEventListener('click',e=>{ if(e.target===modal)closeModal(); });
    document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&modal.classList.contains('show'))closeModal(); });

    const nameIdx=[...document.querySelectorAll('.filterable-table thead tr:first-child th')]
        .findIndex(th=>th.textContent.trim()==='球员');
    function open(name,details){
        if(metaLine) metaLine.textContent=name;
        body.className='dz-list';
        body.innerHTML=details.map((v,i)=>{
            const f=String(v).split('|');
            if(f.length<4) return '<div class="dz-empty"><span class="dz-rank">'+(i+1)+'</span>暂无记录</div>';
            return '<div class="dz-item'+(i===0?' top':'')+'"><span class="dz-rank">'+(i+1)+'</span>'
                +'<div class="dz-main"><div class="dz-where">'+esc(f[0])+' · '+esc(f[1])+'</div>'
                +'<div class="dz-who">'+(f[2]?'<i>'+esc(f[4]||'负')+'</i>'+esc(f[2]):'<i>对手待更新</i>')+'</div></div>'
                +'<div class="dz-kills">'+esc(f[3])+'<small>'+esc((window.CFG&&CFG.unit)||'')+'</small></div></div>';
        }).join('');
        if(footer) footer.textContent=(window.CFG&&CFG.foot)||'';
        modal.classList.add('show');
    }
    function parse(el){
        let d=[]; try{ d=JSON.parse(el.dataset.detail||'[]'); }catch(_e){ d=[]; }
        return Array.isArray(d)?d:[];
    }
    // delegated: the table script creates and swaps rows as it filters and sorts
    const tbody=document.querySelector('.filterable-table tbody');
    if(tbody) tbody.addEventListener('click',e=>{
        const row=e.target.closest('tr[data-detail]');
        if(!row||row.parentNode!==tbody) return;
        const cell=row.querySelectorAll('td')[nameIdx>=0?nameIdx:1];
        open(cell?cell.textContent.trim():'',parse(row));
    });
    document.querySelectorAll('.pod-card[data-detail]').forEach(card=>{
        card.addEventListener('click',()=>open(card.dataset.name||'',parse(card)));
    });
});
})();
