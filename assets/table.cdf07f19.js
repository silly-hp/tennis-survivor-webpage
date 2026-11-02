// TS.ready + 'ts:ready' mark the end of setup (also on pages without a table), so page
// scripts start from that instead of relying on <script> / DOMContentLoaded order.
function tsReady(){
    window.TS=window.TS||{extra:[]};
    window.TS.ready=true;
    document.dispatchEvent(new Event('ts:ready'));
}
document.addEventListener('DOMContentLoaded',function(){
    const table=document.querySelector('.filterable-table');
    if(!table){ tsReady(); return; }
    const thead=table.querySelector('thead');
    const tbody=table.querySelector('tbody');
    // Rows are models: t = cell texts (what filters and sorts read), h = {col: html} for cells
    // whose markup is more than the text, c = tr class, u/p/d = uid / picked / detail.
    // Pages built with _df_to_table_data ship them as JSON in #tsData and a model's <tr> is
    // only created (TS.el) when it is shown; otherwise the models wrap the parsed rows.
    const dataEl=document.getElementById('tsData');
    let rows;
    if(dataEl){
        rows=JSON.parse(dataEl.textContent);
    } else {
        rows=Array.from(tbody.querySelectorAll('tr'),tr=>{
            const m={t:Array.from(tr.children,c=>c.textContent.trim()),c:tr.className,el:tr};
            if(tr.dataset.uid!==undefined)m.u=tr.dataset.uid;
            if(tr.dataset.picked!==undefined)m.p=+tr.dataset.picked;
            if(tr.dataset.detail!==undefined){ try{ m.d=JSON.parse(tr.dataset.detail||'[]'); }catch(e){ m.d=[]; } }
            tr._m=m;
            return m;
        });
    }
    const totalCount=rows.length;
    // every row lives in this array; tbody only holds the rows TS.render puts there,
    // so filtered-out (or paged-out) rows cost nothing in layout
    let order=rows.slice();
    // filter passes run during setup render nothing (see initDone below)
    let initDone=false, rendered=false;
    const zhCollator=new Intl.Collator('zh');
    const escCell=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#x27;'}[c]));
    const cellHtml=(m,i)=>m.h&&m.h[i]!=null?m.h[i]:escCell(m.t[i]);
    function rowEl(m){
        if(m.el)return m.el;
        const tr=document.createElement('tr');
        if(m.c)tr.className=m.c;
        if(m.u!==undefined)tr.dataset.uid=m.u;
        if(m.p!==undefined)tr.dataset.picked=m.p;
        if(m.d!==undefined)tr.dataset.detail=JSON.stringify(m.d);
        tr.innerHTML=m.t.map((_,i)=>'<td>'+cellHtml(m,i)+'</td>').join('');
        tr._m=m; m.el=tr;
        window.TS.onRow.forEach(f=>f(m,tr));
        return tr;
    }
    const totalEl=document.getElementById('total-count');
    const visibleEl=document.getElementById('visible-count');
    if(totalEl)totalEl.textContent=totalCount;
    if(visibleEl)visibleEl.textContent=totalCount;
    // page scripts add row predicates to TS.extra and call TS.refresh(); 'ts:filtered' fires after each pass.
    // TS.render(list) decides which of the matching models go into tbody (default: all of them);
    // TS.setOrder(arr) replaces the row order without refreshing; TS.el(m) gives a model's <tr>,
    // TS.html(m,i) a cell's markup, and TS.onRow hooks run once on every <tr> TS.el creates.
    window.TS=window.TS||{extra:[]};
    window.TS.onRow=window.TS.onRow||[];
    window.TS.refresh=()=>filterTable();
    window.TS.rows=rows;
    window.TS.visible=rows;
    window.TS.el=rowEl;
    window.TS.html=cellHtml;
    window.TS.render=list=>{
        const frag=document.createDocumentFragment();
        list.forEach(m=>frag.appendChild(rowEl(m)));
        tbody.textContent='';
        tbody.appendChild(frag);
    };
    window.TS.setOrder=arr=>{ order=arr.slice(); };
    const headerRow=thead.querySelector('tr');
    const headers=headerRow.querySelectorAll('th');
    const filterRow=document.createElement('tr');
    filterRow.className='filter-row';
    const allOptionContainers=[];
    const columnMeta=[]; // {type:'numeric'|'category', ...}

    // strip % , currency chars etc. before parsing
    function parseCellNumber(text){
        const cleaned=String(text).trim().replace(/[%,\s]/g,'');
        if(cleaned===''||cleaned==='-'||cleaned.toLowerCase()==='nan')return NaN;
        const n=parseFloat(cleaned);
        return n;
    }

    headers.forEach((header,index)=>{
        let sortDirection='none';
        const thCell=document.createElement('th');

        // collect all non-empty values for this column
        const rawValues=[];
        rows.forEach(row=>{
            const v=row.t[index];
            if(v!==undefined)rawValues.push(v);
        });
        const nonEmpty=rawValues.filter(v=>v!==''&&v.toLowerCase()!=='nan'&&v!=='-');
        const parsedNums=nonEmpty.map(parseCellNumber);
        const isNumericCol = nonEmpty.length>0 && parsedNums.every(n=>!isNaN(n));
        const headerText=header.textContent.trim();

        if(isNumericCol){
            // ── build slider filter ──────────────────────────────
            const forceInt=/天数|排名|周数|参赛|冠军数|亚军|连胜|连败|得分|积分/.test(headerText)
                && !/率/.test(headerText);
            const isIntCol=forceInt || parsedNums.every(n=>Number.isInteger(n));
            let minVal=parsedNums.reduce((a,b)=>a<b?a:b);
            let maxVal=parsedNums.reduce((a,b)=>a>b?a:b);
            if(isIntCol){ minVal=Math.floor(minVal); maxVal=Math.ceil(maxVal); }
            // step is 1 for wide ranges: snap the ends so the slider can reach the true max
            else if((maxVal-minVal)>20){ minVal=Math.floor(minVal); maxVal=Math.ceil(maxVal); }
            const step=isIntCol ? 1 : ((maxVal-minVal)>20 ? 1 : (maxVal-minVal)/100 || 1);

            columnMeta[index]={type:'numeric', min:minVal, max:maxVal,
                                curMin:minVal, curMax:maxVal, intCol:isIntCol,
                                header:headerText};

            const dropdownWrapper=document.createElement('div');
            dropdownWrapper.className='filter-dropdown';
            const trigger=document.createElement('div');
            trigger.className='filter-trigger';
            trigger.innerHTML='<span>全部</span><span style="font-size:10px">▼</span>';

            const panel=document.createElement('div');
            panel.className='dropdown-content filter-slider';

            const readout=document.createElement('div');
            readout.className='filter-slider-readout';
            const inMin=document.createElement('input');
            inMin.type='number'; inMin.value=minVal; inMin.step=step;
            if(isIntCol){ inMin.step='1'; inMin.setAttribute('inputmode','numeric'); }
            const sep=document.createElement('span');
            sep.className='filter-slider-sep'; sep.textContent='~';
            const inMax=document.createElement('input');
            inMax.type='number'; inMax.value=maxVal; inMax.step=step;
            if(isIntCol){ inMax.step='1'; inMax.setAttribute('inputmode','numeric'); }
            readout.append(inMin,sep,inMax);

            const rangeWrap=document.createElement('div');
            rangeWrap.className='filter-slider-range';
            const track=document.createElement('div');
            track.className='filter-slider-track';
            const fill=document.createElement('div');
            fill.className='filter-slider-fill';
            const rMin=document.createElement('input');
            rMin.type='range'; rMin.min=minVal; rMin.max=maxVal; rMin.step=step; rMin.value=minVal;
            const rMax=document.createElement('input');
            rMax.type='range'; rMax.min=minVal; rMax.max=maxVal; rMax.step=step; rMax.value=maxVal;
            rangeWrap.append(track,fill,rMin,rMax);

            const resetBtn=document.createElement('button');
            resetBtn.type='button'; resetBtn.className='filter-slider-reset';
            resetBtn.textContent='重置范围';

            panel.append(readout,rangeWrap,resetBtn);

            function syncUI(){
                let lo=parseFloat(rMin.value), hi=parseFloat(rMax.value);
                if(isIntCol){ lo=Math.round(lo); hi=Math.round(hi); }
                if(lo>hi){ const t=lo; lo=hi; hi=t; }
                columnMeta[index].curMin=lo;
                columnMeta[index].curMax=hi;
                inMin.value=isIntCol?String(lo):lo; inMax.value=isIntCol?String(hi):hi;
                rMin.value=lo; rMax.value=hi;
                const pct=v=>((v-minVal)/(maxVal-minVal||1))*100;
                fill.style.left=pct(lo)+'%';
                fill.style.width=(pct(hi)-pct(lo))+'%';
                const trigSpan=trigger.querySelector('span:first-child');
                trigSpan.textContent=(lo===minVal&&hi===maxVal)?'全部':(lo+' ~ '+hi);
                filterTable();
            }
            rMin.addEventListener('input',()=>{ if(+rMin.value>+rMax.value)rMin.value=rMax.value; syncUI(); });
            rMax.addEventListener('input',()=>{ if(+rMax.value<+rMin.value)rMax.value=rMin.value; syncUI(); });
            inMin.addEventListener('change',()=>{
                let v=parseFloat(inMin.value); if(isNaN(v))v=minVal;
                if(isIntCol) v=Math.round(v);
                rMin.value=v; syncUI();
            });
            inMax.addEventListener('change',()=>{
                let v=parseFloat(inMax.value); if(isNaN(v))v=maxVal;
                if(isIntCol) v=Math.round(v);
                rMax.value=v; syncUI();
            });
            resetBtn.addEventListener('click',()=>{ rMin.value=minVal; rMax.value=maxVal; syncUI(); });
            syncUI();

            dropdownWrapper.appendChild(trigger);
            document.body.appendChild(panel);
            allOptionContainers.push(panel);

            trigger.addEventListener('click',(e)=>{
                e.stopPropagation();
                document.querySelectorAll('.dropdown-content').forEach(d=>{
                    if(d!==panel)d.classList.remove('show');
                });
                const isOpen=panel.classList.contains('show');
                panel.classList.toggle('show');
                if(!isOpen){
                    const rect=trigger.getBoundingClientRect();
                    const w=Math.max(rect.width,190);
                    panel.style.width=w+'px';
                    // keep right-hand columns' panels inside the viewport
                    panel.style.left=Math.max(8,Math.min(rect.left,document.documentElement.clientWidth-w-8))+'px';
                    const dropH=panel.scrollHeight;
                    const spaceBelow=window.innerHeight-rect.bottom;
                    panel.style.top=(spaceBelow>=dropH||spaceBelow>=140?rect.bottom:(rect.top-dropH))+'px';
                }
            });
            panel.addEventListener('click',(e)=>e.stopPropagation());
            thCell.appendChild(dropdownWrapper);

        } else {
            // ── original categorical checkbox dropdown ───────────
            columnMeta[index]={type:'category', header:headerText};
            const dropdownWrapper=document.createElement('div');
            dropdownWrapper.className='filter-dropdown';
            const trigger=document.createElement('div');
            trigger.className='filter-trigger';
            trigger.innerHTML='<span>筛选...</span><span style="font-size:10px">▼</span>';
            const optionsContainer=document.createElement('div');
            optionsContainer.className='dropdown-content';
            const searchInput=document.createElement('input');
            searchInput.type='text';
            searchInput.className='dropdown-search';
            searchInput.placeholder='搜索...';
            optionsContainer.prepend(searchInput);
            searchInput.addEventListener('input',(e)=>{
                // comma/space separated terms match any of them (e.g. "zoe, eric")
                const terms=e.target.value.toLowerCase().split(/[,，\s]+/).filter(Boolean);
                optionsContainer.querySelectorAll('.option-item').forEach(item=>{
                    if(item.dataset.selectAll)return;
                    const label=item.querySelector('span').textContent.toLowerCase();
                    item.style.display=!terms.length||terms.some(q=>label.includes(q))?'flex':'none';
                });
                const visibleCbs=Array.from(
                    optionsContainer.querySelectorAll('.option-item:not([data-select-all])')
                ).filter(i=>i.style.display!=='none')
                 .map(i=>i.querySelector('input[type="checkbox"]'));
                selectAllCb.checked=visibleCbs.length>0&&visibleCbs.every(cb=>cb.checked);
            });
            const selectAllItem=document.createElement('div');
            selectAllItem.className='option-item select-all-item';
            selectAllItem.dataset.selectAll='1';
            selectAllItem.style.borderBottom='2px solid var(--border)';
            const selectAllCb=document.createElement('input');
            selectAllCb.type='checkbox';
            selectAllCb.checked=true;
            const selectAllLabel=document.createElement('span');
            selectAllLabel.textContent='全选';
            selectAllLabel.style.fontWeight='600';
            selectAllItem.appendChild(selectAllCb);
            selectAllItem.appendChild(selectAllLabel);
            optionsContainer.appendChild(selectAllItem);
            selectAllCb.addEventListener('change',()=>{
                const checked=selectAllCb.checked;
                optionsContainer.querySelectorAll('.option-item:not([data-select-all])').forEach(item=>{
                    if(item.style.display!=='none')
                        item.querySelector('input[type="checkbox"]').checked=checked;
                });
                filterTable();
            });
            // the value list is built on first open: most columns are never filtered,
            // and an unbuilt list means "everything selected" to filterTable
            const optionValues=Array.from(new Set(rawValues)).sort(zhCollator.compare);
            let optionsBuilt=false;
            function buildOptions(){
                if(optionsBuilt)return;
                optionsBuilt=true;
                const frag=document.createDocumentFragment();
                optionValues.forEach(val=>{
                    const item=document.createElement('div');
                    item.className='option-item';
                    const cb=document.createElement('input');
                    cb.type='checkbox';cb.value=val;cb.checked=true;
                    const label=document.createElement('span');
                    label.textContent=val;
                    item.appendChild(cb);item.appendChild(label);
                    frag.appendChild(item);
                });
                optionsContainer.appendChild(frag);
                // page scripts restyle the new items here
                optionsContainer.dispatchEvent(new CustomEvent('ts:options'));
            }
            optionsContainer.tsBuild=buildOptions;
            dropdownWrapper.appendChild(trigger);
            document.body.appendChild(optionsContainer);
            allOptionContainers.push(optionsContainer);
            thCell.appendChild(dropdownWrapper);

            trigger.addEventListener('click',(e)=>{
                e.stopPropagation();
                document.querySelectorAll('.dropdown-content').forEach(d=>{
                    if(d!==optionsContainer)d.classList.remove('show');
                });
                buildOptions();
                const isOpen=optionsContainer.classList.contains('show');
                optionsContainer.classList.toggle('show');
                if(!isOpen){
                    const rect=trigger.getBoundingClientRect();
                    const dropH=Math.min(250,optionsContainer.scrollHeight);
                    const spaceBelow=window.innerHeight-rect.bottom;
                    const w=Math.max(rect.width,200);
                    optionsContainer.style.width=w+'px';
                    optionsContainer.style.top=(spaceBelow>=dropH||spaceBelow>=120?rect.bottom:(rect.top-dropH))+'px';
                    optionsContainer.style.left=Math.max(8,Math.min(rect.left,document.documentElement.clientWidth-w-8))+'px';
                }
            });
            optionsContainer.addEventListener('change',(e)=>{
                if(!e.target.closest('[data-select-all]')){
                    const visibleCbs=Array.from(
                        optionsContainer.querySelectorAll('.option-item:not([data-select-all])')
                    ).filter(i=>i.style.display!=='none')
                     .map(i=>i.querySelector('input[type="checkbox"]'));
                    selectAllCb.checked=visibleCbs.length>0&&visibleCbs.every(cb=>cb.checked);
                }
                filterTable();
            });
            optionsContainer.addEventListener('click',(e)=>e.stopPropagation());
        }

        filterRow.appendChild(thCell);
        header.addEventListener('click',()=>{
            headers.forEach(h=>h.classList.remove('sort-asc','sort-desc'));
            if(sortDirection==='none')sortDirection='asc';
            else if(sortDirection==='asc')sortDirection='desc';
            else sortDirection='none';
            if(sortDirection!=='none'){
                header.classList.add('sort-'+sortDirection);
                const dir=sortDirection==='asc'?1:-1;
                const keyed=order.map(row=>{
                    const A=row.t[index]||'';
                    const em=A===''||A.toLowerCase()==='nan'||A==='-';
                    return {row,A,em,n:parseFloat(A)};
                });
                keyed.sort((a,b)=>{
                    if(a.em&&!b.em)return 1;
                    if(!a.em&&b.em)return -1;
                    if(a.em&&b.em)return 0;
                    if(!isNaN(a.n)&&!isNaN(b.n))return(a.n-b.n)*dir;
                    return zhCollator.compare(a.A,b.A)*dir;
                });
                order=keyed.map(k=>k.row);
                filterTable();
            }
        });
    });

    thead.appendChild(filterRow);
    document.querySelector('.table-wrapper').addEventListener('scroll',()=>{
        allOptionContainers.forEach(oc=>oc.classList.remove('show'));
    });
    function updateFilterRowTop(){
        filterRow.style.top=headerRow.getBoundingClientRect().height+'px';
    }
    updateFilterRowTop();
    new ResizeObserver(updateFilterRowTop).observe(headerRow);
    // setup above runs filter passes (slider init); they render nothing. The first real pass
    // comes from a page script's TS.refresh() on 'ts:ready' (fired just below), or else from here.
    initDone=true;
    setTimeout(()=>{ if(!rendered)filterTable(); },0);
    tsReady();

    function filterTable(){
        if(!initDone)return;
        rendered=true;
        let visibleCount=0;
        const statusIndex=columnMeta.findIndex(meta=>meta&&meta.type==='category'&&meta.header==='当前状态');
        // resolve each column's filter once per pass; untouched columns drop out entirely
        const active=[];
        columnMeta.forEach((meta,index)=>{
            if(!meta)return;
            if(meta.type==='numeric'){
                if(meta.curMin!==meta.min||meta.curMax!==meta.max)active.push({index,meta});
            } else {
                const cbs=allOptionContainers[index].querySelectorAll('.option-item:not([data-select-all]) input[type="checkbox"]');
                const selected=new Set();
                cbs.forEach(cb=>{ if(cb.checked)selected.add(cb.value); });
                // nothing ticked behaves like everything ticked
                if(selected.size>0&&selected.size<cbs.length)active.push({index,meta,selected});
            }
        });
        const extra=window.TS.extra;
        const visible=[];
        order.forEach(row=>{
            let showRow=true;
            const cells=row.t;
            for(const f of active){
                const v=cells[f.index];
                if(v===undefined)continue;
                if(f.selected){
                    if(!f.selected.has(v)){ showRow=false; break; }
                    continue;
                }
                const n=parseCellNumber(v);
                if(f.meta.header==='存活天数'){
                    const statusText=statusIndex>=0&&cells[statusIndex]!==undefined?cells[statusIndex]:'';
                    if(statusText==='未参赛'||isNaN(n)){ showRow=false; break; }
                }
                if(!isNaN(n) && (n<f.meta.curMin || n>f.meta.curMax)){ showRow=false; break; }
            }
            if(showRow&&extra.length)showRow=extra.every(f=>f(row));
            if(showRow)visible.push(row);
        });
        visibleCount=visible.length;
        window.TS.visible=visible;
        window.TS.render(visible);
        if(visibleEl)visibleEl.textContent=visibleCount;
        document.dispatchEvent(new Event('ts:filtered'));
    }

    document.addEventListener('click',()=>{
        allOptionContainers.forEach(oc=>oc.classList.remove('show'));
    });
});