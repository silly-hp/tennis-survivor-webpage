(function(){
function _json(id, fallback){
    try{
        const node=document.getElementById(id);
        if(!node) return fallback;
        return JSON.parse(node.textContent);
    }catch(e){ return fallback; }
}
const RECORDS = _json('h2hRecords', []);
const USERS   = _json('h2hUsers', []);
const PLAYERS = _json('h2hPlayers', []);
const SEASONS = _json('h2hSeasons', []);

let selU = new Set(), selP = new Set(), selS = new Set();
let tagsExpanded = false;

function optLabel(u){
    return u.rank != null ? u.username+' ('+u.rank+')' : u.username+' (-)';
}

function buildList(listId, items, type){
    var el = document.getElementById(listId);
    el.innerHTML = '';
    if(!items.length){ el.innerHTML='<div class="opt-empty">无结果</div>'; return; }
    var saDiv = document.createElement('div');
    saDiv.className = 'opt-item opt-select-all';
    saDiv.style.borderBottom = '2px solid var(--border)';
    var saCb = document.createElement('input');
    saCb.type = 'checkbox';
    var saLbl = document.createElement('span');
    saLbl.className = 'opt-name'; saLbl.textContent = '全选'; saLbl.style.fontWeight = '600';
    saDiv.appendChild(saCb); saDiv.appendChild(saLbl);
    saDiv.addEventListener('click', function(e){ if(e.target !== saCb) saCb.click(); });
    el.appendChild(saDiv);
    items.forEach(function(item){
        var key   = type==='user' ? item.username : String(item);
        var label = type==='user' ? optLabel(item) : String(item);
        var sel   = type==='user' ? selU.has(key) : type==='player' ? selP.has(key) : selS.has(key);
        var div = document.createElement('div');
        div.className = 'opt-item'+(sel?' checked':'');
        var cb = document.createElement('input');
        cb.type='checkbox'; cb.checked=sel;
        cb.addEventListener('change',function(e){ toggle(key,type,e.target.checked); });
        var nameSpan = document.createElement('span');
        nameSpan.className='opt-name'; nameSpan.title=label; nameSpan.textContent=label;
        div.appendChild(cb); div.appendChild(nameSpan);
        div.addEventListener('click',function(e){ if(e.target!==cb) cb.click(); });
        el.appendChild(div);
    });
    var allCbs = Array.from(el.querySelectorAll('.opt-item:not(.opt-select-all) input'));
    saCb.checked = allCbs.length > 0 && allCbs.every(function(c){ return c.checked; });
    saCb.addEventListener('change', function(){
        var checked = saCb.checked;
        var src = type==='user' ? USERS : type==='player' ? PLAYERS : SEASONS;
        src.forEach(function(item){
            var key = type==='user' ? item.username : String(item);
            var label = type==='user' ? optLabel(item) : String(item);
            var q = type==='user' ? document.getElementById('uSearch').value
                  : type==='player' ? document.getElementById('pSearch').value
                  : document.getElementById('sSearch').value;
            if(label.toLowerCase().indexOf(q.toLowerCase()) !== -1){
                if(checked){
                    if(type==='user') selU.add(key);
                    else if(type==='player') selP.add(key);
                    else selS.add(key);
                } else {
                    if(type==='user') selU.delete(key);
                    else if(type==='player') selP.delete(key);
                    else selS.delete(key);
                }
            }
        });
        filterList('uList',  document.getElementById('uSearch').value, 'user');
        filterList('pList',  document.getElementById('pSearch').value, 'player');
        filterList('sList',  document.getElementById('sSearch').value, 'season');
        renderTags(); updateRunBtn();
    });
}

function filterList(listId, q, type){
    var src = type==='user' ? USERS : type==='player' ? PLAYERS : SEASONS;
    buildList(listId, src.filter(function(item){
        var label = type==='user' ? optLabel(item) : String(item);
        return label.toLowerCase().indexOf(q.toLowerCase()) !== -1;
    }), type);
}

function toggle(key, type, checked){
    if(type==='user')        { checked ? selU.add(key) : selU.delete(key); }
    else if(type==='player') { checked ? selP.add(key) : selP.delete(key); }
    else                     { checked ? selS.add(key) : selS.delete(key); }
    filterList('uList',  document.getElementById('uSearch').value, 'user');
    filterList('pList',  document.getElementById('pSearch').value, 'player');
    filterList('sList',  document.getElementById('sSearch').value, 'season');
    renderTags(); updateRunBtn();
}

function renderTags(){
    var el = document.getElementById('selTags');
    el.innerHTML = '';
    var box = document.createElement('div');
    box.className = 'sel-summary';
    var hasAny = (selU.size>0 || selP.size>0 || selS.size>0);
    if(!hasAny){
        var none = document.createElement('span');
        none.className = 'row-count';
        none.textContent = '未选择筛选条件';
        box.appendChild(none);
        tagsExpanded = false;
    } else {
        if(selU.size>0) box.appendChild(makeSummaryPill('用户', selU, ''));
        if(selP.size>0) box.appendChild(makeSummaryPill('球员', selP, 'player'));
        if(selS.size>0) box.appendChild(makeSummaryPill('赛季', selS, 'season'));
        var tg = document.createElement('button');
        tg.type = 'button';
        tg.className = 'sel-summary-toggle';
        tg.textContent = tagsExpanded ? '收起' : '展开';
        tg.addEventListener('click', function(){
            tagsExpanded = !tagsExpanded;
            renderTags();
        });
        box.appendChild(tg);
    }
    el.appendChild(box);

    if(hasAny && tagsExpanded){
        var expanded = document.createElement('div');
        expanded.className = 'sel-expanded';
        selU.forEach(function(u){ expanded.appendChild(makeTag(u,'user','')); });
        selP.forEach(function(p){ expanded.appendChild(makeTag(p,'player',' sel-tag-player')); });
        selS.forEach(function(s){ expanded.appendChild(makeTag(s,'season',' sel-tag-season')); });
        el.appendChild(expanded);
    }
}

function makeSummaryPill(label, setObj, extraClass){
    var arr = Array.from(setObj);
    var pill = document.createElement('span');
    pill.className = 'sel-summary-pill' + (extraClass ? (' ' + extraClass) : '');
    pill.innerHTML = label + ' <b>' + arr.length + '</b>';
    var preview = arr.slice(0, 8).join('、');
    if(arr.length > 8) preview += '…';
    pill.title = preview || ('已选择 ' + arr.length + ' 项');
    return pill;
}

function makeTag(key, type, extraClass){
    var tag = document.createElement('span');
    tag.className = 'sel-tag'+extraClass;
    var rm = document.createElement('button');
    rm.className='sel-tag-rm'; rm.textContent='\u00d7';
    rm.addEventListener('click',function(){ toggle(key,type,false); });
    tag.appendChild(document.createTextNode(key+' '));
    tag.appendChild(rm);
    return tag;
}

function updateRunBtn(){
    document.getElementById('runBtn').disabled = (selU.size===0 || selP.size===0);
}

window.clearAll = function(){
    selU.clear(); selP.clear(); selS.clear();
    tagsExpanded = false;
    ['uSearch','pSearch','sSearch'].forEach(function(id){ document.getElementById(id).value=''; });
    buildList('uList',USERS,'user');
    buildList('pList',PLAYERS,'player');
    buildList('sList',SEASONS,'season');
    renderTags(); updateRunBtn();
    document.getElementById('results').style.display    = 'none';
    document.getElementById('emptyState').style.display = '';
};

var _colDropdowns = [];

function _makeColDropdown(colIdx, vals){
    var wrap = document.createElement('div');
    wrap.className = 'filter-dropdown';
    var trigger = document.createElement('div');
    trigger.className = 'filter-trigger';
    trigger.innerHTML = '<span>\u5168\u90e8</span><span style="font-size:10px">\u25bc</span>';
    var dropdown = document.createElement('div');
    dropdown.className = 'dropdown-content';
    _colDropdowns.push(dropdown);
    var searchEl = document.createElement('input');
    searchEl.type='text'; searchEl.className='dropdown-search'; searchEl.placeholder='\u641c\u7d22...';
    dropdown.appendChild(searchEl);
    var saItem = document.createElement('div');
    saItem.className='option-item'; saItem.dataset.selectAll='1';
    saItem.style.borderBottom='2px solid var(--border)';
    var saCb = document.createElement('input');
    saCb.type='checkbox'; saCb.checked=true;
    var saLbl = document.createElement('span');
    saLbl.textContent='\u5168\u9009'; saLbl.style.fontWeight='600';
    saItem.appendChild(saCb); saItem.appendChild(saLbl);
    dropdown.appendChild(saItem);
    vals.forEach(function(val){
        var item = document.createElement('div');
        item.className='option-item';
        var cb = document.createElement('input');
        cb.type='checkbox'; cb.value=val; cb.checked=true;
        var lbl = document.createElement('span');
        lbl.textContent = val;
        item.appendChild(cb); item.appendChild(lbl);
        dropdown.appendChild(item);
    });
    function getVisibleCbs(){
        return Array.from(dropdown.querySelectorAll('.option-item:not([data-select-all])'))
            .filter(function(i){ return i.style.display!=='none'; })
            .map(function(i){ return i.querySelector('input'); });
    }
    searchEl.addEventListener('input',function(){
        var q = searchEl.value.toLowerCase();
        dropdown.querySelectorAll('.option-item:not([data-select-all])').forEach(function(it){
            it.style.display = it.querySelector('span').textContent.toLowerCase().includes(q)?'':'none';
        });
        var vis = getVisibleCbs();
        saCb.checked = vis.length>0 && vis.every(function(cb){ return cb.checked; });
    });
    saCb.addEventListener('change',function(){
        getVisibleCbs().forEach(function(cb){ cb.checked=saCb.checked; });
        applyColFilters();
    });
    dropdown.addEventListener('change',function(e){
        if(!e.target.closest('[data-select-all]')){
            var vis = getVisibleCbs();
            saCb.checked = vis.length>0 && vis.every(function(cb){ return cb.checked; });
        }
        var allCbs = Array.from(dropdown.querySelectorAll('.option-item:not([data-select-all]) input'));
        var sel = allCbs.filter(function(cb){ return cb.checked; });
        var trigSpan = trigger.querySelector('span:first-child');
        if(sel.length===0) trigSpan.textContent='\u5df2\u53d6\u6d88';
        else if(sel.length===allCbs.length) trigSpan.textContent='\u5168\u90e8';
        else trigSpan.textContent='\u5df2\u9009 '+sel.length+' \u9879';
        applyColFilters();
    });
    dropdown.addEventListener('click',function(e){ e.stopPropagation(); });
    trigger.addEventListener('click',function(e){
        e.stopPropagation();
        _colDropdowns.forEach(function(d){ if(d!==dropdown) d.classList.remove('show'); });
        var isOpen = dropdown.classList.contains('show');
        dropdown.classList.toggle('show');
        if(!isOpen){
            var rect = trigger.getBoundingClientRect();
            var spaceBelow = window.innerHeight-rect.bottom;
            var dropH = Math.min(250, dropdown.scrollHeight);
            dropdown.style.width  = rect.width+'px';
            dropdown.style.left   = rect.left+'px';
            dropdown.style.top    = (spaceBelow>=dropH||spaceBelow>=120 ? rect.bottom : rect.top-dropH)+'px';
        }
    });
    wrap.appendChild(trigger);
    document.body.appendChild(dropdown);
    return wrap;
}

var COL_KEYS = ['u','p','t','d','s','r'];
var _recs = [];   /* query result */
var _view = [];   /* query result after column filters */

function colVal(r, key){
    if(key==='r') return r.r===1?'W':r.r===0?'L':'?';
    return String(r[key]);
}

function rowHtml(r, i){
    var badge = r.r===1
        ? '<span class="result-badge badge-w">W</span>'
        : '<span class="result-badge badge-l">L</span>';
    /* striping by absolute index: nth-child would shift as the window moves */
    return '<tr'+(i%2?' class="even"':'')+'>'
        +'<td style="color:var(--ink2)">'+escHtml(r.u)+'</td>'
        +'<td style="font-weight:500">'+escHtml(r.p)+'</td>'
        +'<td><span class="tour-tag">'+escHtml(r.t)+'</span></td>'
        +'<td><span class="day-pill">Day '+r.d+'</span></td>'
        +'<td style="font-family:\'Space Mono\',monospace;font-size:11px;color:var(--faint)">'+r.s+'</td>'
        +'<td>'+badge+'</td>'
        +'</tr>';
}

/* ── virtual scroll ──
   Only rows near the viewport are in the DOM, between two spacer rows.
   Row heights start as an estimate and are replaced by measured heights as rows
   render; a Fenwick tree over the heights gives offset <-> index in O(log n). */
var EST_ROW_H = 37, OVERSCAN = 12;
var _vh = new Float64Array(0), _fw = new Float64Array(1), _vn = 0, _vsRaf = 0, _vsCalibrated = false;

function fwBuild(){
    _fw = new Float64Array(_vn+1);
    for(var i=1;i<=_vn;i++){
        _fw[i] += _vh[i-1];
        var j = i+(i&-i);
        if(j<=_vn) _fw[j] += _fw[i];
    }
}
function fwAdd(i, d){ for(i++; i<=_vn; i+=i&-i) _fw[i] += d; }
/* total height of the first i rows */
function fwSum(i){ var s=0; for(; i>0; i-=i&-i) s += _fw[i]; return s; }
/* index of the row containing offset y */
function fwFind(y){
    var pos=0, step=1;
    while(step*2<=_vn) step*=2;
    for(; step>0; step>>=1){
        if(pos+step<=_vn && _fw[pos+step]<=y){ pos+=step; y-=_fw[pos]; }
    }
    return Math.min(pos, _vn-1);
}

function padRow(h){
    return '<tr class="vs-pad"><td colspan="6" style="height:'+h+'px"></td></tr>';
}

function renderWindow(){
    _vsRaf = 0;
    var tbody = document.getElementById('recBody');
    if(_vn===0){
        tbody.innerHTML='<tr><td colspan="6" style="text-align:center;padding:32px;'
            +'color:var(--faint);font-family:\'Space Mono\',monospace;font-size:11px;">'
            +'\u6682\u65e0\u7b26\u5408\u6761\u4ef6\u7684\u8bb0\u5f55</td></tr>';
        return;
    }
    var wrapper = document.querySelector('.table-wrapper');
    var headH = document.querySelector('.h2h-table thead').offsetHeight;
    var top = Math.max(0, wrapper.scrollTop-headH);
    var viewH = wrapper.clientHeight || window.innerHeight;
    var firstVis = fwFind(top);
    var s = Math.max(0, firstVis-OVERSCAN);
    var e = Math.min(_vn, fwFind(top+viewH)+1+OVERSCAN);
    var html = padRow(fwSum(s));
    for(var i=s;i<e;i++) html += rowHtml(_view[i], i);
    html += padRow(fwSum(_vn)-fwSum(e));
    tbody.innerHTML = html;

    /* swap estimates for real heights; keep the first visible row in place */
    var trs = tbody.children, changed = false, shift = 0, total = 0;
    for(var k=1;k<trs.length-1;k++){
        var idx = s+k-1, h = trs[k].getBoundingClientRect().height;
        total += h;
        if(Math.abs(h-_vh[idx])>0.5){
            fwAdd(idx, h-_vh[idx]);
            if(idx<firstVis) shift += h-_vh[idx];
            _vh[idx] = h;
            changed = true;
        }
    }
    /* first render of a data set: use the measured average as the estimate
       for every unseen row (rows are much taller on phones, where cells wrap) */
    if(!_vsCalibrated){
        _vsCalibrated = true;
        var avg = total/(trs.length-2);
        if(Math.abs(avg-EST_ROW_H)>1){
            EST_ROW_H = avg;
            for(var m=e;m<_vn;m++) _vh[m] = avg;
            fwBuild();
            changed = true;
        }
    }
    if(changed){
        trs[trs.length-1].firstChild.style.height = (fwSum(_vn)-fwSum(e))+'px';
        if(shift) wrapper.scrollTop += shift;
        /* the window was sized from estimates; render again with real heights */
        scheduleWindow();
    }
}

function scheduleWindow(){
    if(!_vsRaf) _vsRaf = requestAnimationFrame(renderWindow);
}

/* new data set: forget measured heights and go back to the top */
function resetView(){
    _vn = _view.length;
    _vh = new Float64Array(_vn).fill(EST_ROW_H);
    fwBuild();
    _vsCalibrated = false;
    document.querySelector('.table-wrapper').scrollTop = 0;
    document.getElementById('visCount').textContent = fmtInt(_vn);
    renderWindow();
}

document.querySelector('.table-wrapper').addEventListener('scroll', scheduleWindow, {passive:true});
window.addEventListener('resize', function(){ _vsCalibrated = false; scheduleWindow(); });

function rebuildFilters(){
    _colDropdowns.forEach(function(d){ if(d.parentNode) d.parentNode.removeChild(d); });
    _colDropdowns = [];
    var table = document.querySelector('.h2h-table');
    if(!table) return;
    var thead = table.querySelector('thead');
    var old = thead.querySelector('.filter-row');
    if(old) thead.removeChild(old);
    var valSets = COL_KEYS.map(function(){ return new Set(); });
    _recs.forEach(function(r){
        for(var i=0;i<COL_KEYS.length;i++) valSets[i].add(colVal(r, COL_KEYS[i]));
    });
    var filterRow = document.createElement('tr');
    filterRow.className = 'filter-row';
    COL_KEYS.forEach(function(key, i){
        var sorted = Array.from(valSets[i]).sort(function(a,b){
            var nA=parseFloat(a), nB=parseFloat(b);
            if(!isNaN(nA)&&!isNaN(nB)) return nA-nB;
            return a.localeCompare(b,'zh');
        });
        var th = document.createElement('th');
        th.appendChild(_makeColDropdown(i, sorted));
        filterRow.appendChild(th);
    });
    thead.appendChild(filterRow);
    var wrapper = document.querySelector('.table-wrapper');
    if(wrapper){
        wrapper.addEventListener('scroll',function(){
            _colDropdowns.forEach(function(d){ d.classList.remove('show'); });
        });
    }
}

function applyColFilters(){
    /* a column with nothing or everything ticked does not filter */
    var active = [];
    _colDropdowns.forEach(function(dropdown, i){
        var cbs = dropdown.querySelectorAll('.option-item:not([data-select-all]) input');
        var sel = new Set();
        cbs.forEach(function(cb){ if(cb.checked) sel.add(cb.value); });
        if(sel.size>0 && sel.size<cbs.length) active.push({key:COL_KEYS[i], sel:sel});
    });
    _view = active.length ? _recs.filter(function(r){
        for(var j=0;j<active.length;j++){
            if(!active[j].sel.has(colVal(r, active[j].key))) return false;
        }
        return true;
    }) : _recs;
    resetView();
}

document.addEventListener('click',function(){
    _colDropdowns.forEach(function(d){ d.classList.remove('show'); });
});

/* newest first; within one tournament-day: wins, then losses, then unknown, then player name.
   sorted once on first query so the page itself loads without the cost */
var _recordsSorted = false;
function sortRecords(){
    if(_recordsSorted) return;
    var coll = new Intl.Collator('zh');
    RECORDS.sort(function(a,b){
        if(a.dt!==b.dt) return a.dt<b.dt?1:-1;
        if(a.d!==b.d) return b.d-a.d;
        if(a.t!==b.t) return coll.compare(a.t,b.t);
        var ra = a.r===-1?-2:a.r, rb = b.r===-1?-2:b.r;
        if(ra!==rb) return rb-ra;
        return coll.compare(a.p,b.p);
    });
    _recordsSorted = true;
}

window.runQuery = function(){
    sortRecords();
    var recs = RECORDS.filter(function(r){
        var uOk = selU.size===0 || selU.has(r.u);
        var pOk = selP.size===0 || selP.has(r.p);
        var sOk = selS.size===0 || selS.has(String(r.s));
        return uOk && pOk && sOk;
    });
    var W = 0, L = 0, seasonSet = new Set(), tourSet = new Set();
    recs.forEach(function(r){
        if(r.r===1) W++; else if(r.r===0) L++;
        seasonSet.add(r.s); tourSet.add(r.t);
    });
    var nSeasons = seasonSet.size;
    var nTours   = tourSet.size;
    document.getElementById('scoreW').textContent = fmtInt(W);
    document.getElementById('scoreL').textContent = fmtInt(L);
    var uArr=[...selU], pArr=[...selP];
    document.getElementById('scoreUsers').textContent   = uArr.slice(0,2).join('\u3001')+(uArr.length>2?'\u2026':'');
    document.getElementById('scorePlayers').textContent = pArr.slice(0,2).join('\u3001')+(pArr.length>2?'\u2026':'');
    document.getElementById('statTotal').textContent    = fmtInt(recs.length);
    document.getElementById('statWR').textContent       = recs.length?(W/recs.length*100).toFixed(1)+'%':'\u2014';
    document.getElementById('statSeasons').textContent  = fmtInt(nSeasons);
    document.getElementById('statTours').textContent    = fmtInt(nTours);
    _recs = recs;
    _view = recs;
    rebuildFilters();
    document.getElementById('results').style.display    = '';
    document.getElementById('emptyState').style.display = 'none';
    resetView();   /* after unhiding, so the viewport has a real height */
};

function escHtml(s){
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtInt(n){
    return Number(n || 0).toLocaleString('en-US');
}
function escAttr(s){ return escHtml(s); }

document.getElementById('uSearch').addEventListener('input',function(){ filterList('uList',this.value,'user'); });
document.getElementById('pSearch').addEventListener('input',function(){ filterList('pList',this.value,'player'); });
document.getElementById('sSearch').addEventListener('input',function(){ filterList('sList',this.value,'season'); });

buildList('uList',USERS,'user');
buildList('pList',PLAYERS,'player');
buildList('sList',SEASONS,'season');
updateRunBtn();

/* ── mode tabs ── */
window.switchMode = function(mode){
    var isQuery = (mode === 'query');
    document.getElementById('tabBtnQuery').classList.toggle('active', isQuery);
    document.getElementById('tabBtnSummary').classList.toggle('active', !isQuery);
    document.getElementById('tabQuery').classList.toggle('active', isQuery);
    document.getElementById('tabSummary').classList.toggle('active', !isQuery);
};

/* ── summary tab: single-user picker ── */
var sumSelectedUser = null;

function buildSumUserList(items){
    var el = document.getElementById('sumUList');
    el.innerHTML = '';
    if(!items.length){ el.innerHTML = '<div class="opt-empty">无结果</div>'; return; }
    items.forEach(function(item){
        var label = optLabel(item);
        var div = document.createElement('div');
        div.className = 'opt-item' + (sumSelectedUser === item.username ? ' checked' : '');
        var cb = document.createElement('input');
        cb.type = 'radio'; cb.name = 'sumUserRadio';
        cb.checked = (sumSelectedUser === item.username);
        cb.addEventListener('change', function(){
            sumSelectedUser = item.username;
            document.getElementById('sumUSearch').value = item.username;
            filterSumUserList('');
            renderUserSummary(sumSelectedUser);
        });
        var nameSpan = document.createElement('span');
        nameSpan.className = 'opt-name'; nameSpan.title = label; nameSpan.textContent = label;
        div.appendChild(cb); div.appendChild(nameSpan);
        div.addEventListener('click', function(e){ if(e.target !== cb) cb.click(); });
        el.appendChild(div);
    });
}

function filterSumUserList(q){
    buildSumUserList(USERS.filter(function(item){
        return optLabel(item).toLowerCase().indexOf(q.toLowerCase()) !== -1;
    }));
}

document.getElementById('sumUSearch').addEventListener('input', function(){
    filterSumUserList(this.value);
});

/* ── summary tab: donut chart ── */
function sumrDonutSvg(winPct){
    var r = 46, c = 2 * Math.PI * r;
    var winLen = c * (winPct / 100);
    return '<svg width="128" height="128" viewBox="0 0 128 128">'
        + '<circle cx="64" cy="64" r="' + r + '" fill="none" stroke="var(--primary)" stroke-width="16"/>'
        + '<circle cx="64" cy="64" r="' + r + '" fill="none" stroke="var(--th-bg)" stroke-width="16" '
        + 'stroke-dasharray="' + winLen.toFixed(1) + ' ' + c.toFixed(1) + '" '
        + 'transform="rotate(-90 64 64)" stroke-linecap="butt"/>'
        + '</svg>';
}

/* ── summary tab: season filter ── */
var sumSelectedSeason = null;  /* null = all time */

function buildSumSeasonList(){
    var el = document.getElementById('sumSList');
    el.innerHTML = '';
    var allDiv = document.createElement('div');
    allDiv.className = 'opt-item' + (sumSelectedSeason === null ? ' checked' : '');
    var allCb = document.createElement('input');
    allCb.type = 'radio'; allCb.name = 'sumSeasonRadio';
    allCb.checked = (sumSelectedSeason === null);
    allCb.addEventListener('change', function(){
        sumSelectedSeason = null;
        buildSumSeasonList();
        if(sumSelectedUser) renderUserSummary(sumSelectedUser);
    });
    var allSpan = document.createElement('span');
    allSpan.className = 'opt-name'; allSpan.textContent = '全部赛季';
    allDiv.appendChild(allCb); allDiv.appendChild(allSpan);
    allDiv.addEventListener('click', function(e){ if(e.target !== allCb) allCb.click(); });
    el.appendChild(allDiv);

    SEASONS.forEach(function(s){
        var div = document.createElement('div');
        div.className = 'opt-item' + (sumSelectedSeason === s ? ' checked' : '');
        var cb = document.createElement('input');
        cb.type = 'radio'; cb.name = 'sumSeasonRadio';
        cb.checked = (sumSelectedSeason === s);
        cb.addEventListener('change', function(){
            sumSelectedSeason = s;
            buildSumSeasonList();
            if(sumSelectedUser) renderUserSummary(sumSelectedUser);
        });
        var span = document.createElement('span');
        span.className = 'opt-name'; span.textContent = String(s);
        div.appendChild(cb); div.appendChild(span);
        div.addEventListener('click', function(e){ if(e.target !== cb) cb.click(); });
        el.appendChild(div);
    });
}

/* ── summary tab: main render ── */
function renderUserSummary(username){
    var container = document.getElementById('sumResults');
    var empty = document.getElementById('sumEmptyState');
    var recs = RECORDS.filter(function(r){ return r.u === username; });
    if(sumSelectedSeason !== null){
        recs = recs.filter(function(r){ return r.s === sumSelectedSeason; });
    }

    if(recs.length === 0){
        container.innerHTML = '';
        empty.style.display = '';
        return;
    }
    empty.style.display = 'none';

    var wins = recs.filter(function(r){ return r.r === 1; }).length;
    var losses = recs.filter(function(r){ return r.r === 0; }).length;
    var decided = wins + losses;
    var winPct = decided ? Math.round((wins / decided) * 100) : 0;
    var losePct = decided ? (100 - winPct) : 0;

    var byPlayer = {};
    recs.forEach(function(r){
        if(r.r !== 1 && r.r !== 0) return;
        if(!byPlayer[r.p]) byPlayer[r.p] = { w: 0, l: 0 };
        if(r.r === 1) byPlayer[r.p].w++; else byPlayer[r.p].l++;
    });

    var groups = {};
    Object.keys(byPlayer).forEach(function(p){
        var rec = byPlayer[p];
        var key = rec.w + ':' + rec.l;
        if(!groups[key]) groups[key] = { w: rec.w, l: rec.l, players: [] };
        groups[key].players.push(p);
    });
    var groupArr = Object.keys(groups).map(function(k){ return groups[k]; });
    groupArr.sort(function(a, b){
        if(b.w !== a.w) return b.w - a.w;
        return a.l - b.l;
    });

    var initials = username.trim().charAt(0).toUpperCase();
    var scopeLabel = sumSelectedSeason !== null ? String(sumSelectedSeason) + ' 赛季' : '全部赛季';

    var rowsHtml = groupArr.map(function(g){
        var playersHtml = g.players.map(function(p){
            return '<span class="sumr-oppo-player">' + escHtml(p) + '</span>';
        }).join('');
        return '<div class="sumr-oppo-row">'
            + '<div class="sumr-oppo-score">' + g.w + ':' + g.l + '</div>'
            + '<div class="sumr-oppo-players">' + playersHtml + '</div>'
            + '</div>';
    }).join('');

    container.innerHTML =
        '<div class="sumr-card">'
        + '<div class="sumr-headbar">'
        +   '<div class="sumr-head-name"><span class="sumr-avatar">' + escHtml(initials) + '</span>' + escHtml(username) + '</div>'
        +   '<div class="sumr-head-scope">共 ' + fmtInt(recs.length) + ' 场比赛 · ' + escHtml(scopeLabel) + '</div>'
        + '</div>'
        + '<div class="sumr-statrow">'
        +   '<div class="sumr-stat"><div class="sumr-stat-num win">' + fmtInt(wins) + '</div>'
        +     '<div class="sumr-stat-lbl win">胜 <b>' + winPct + '%</b></div></div>'
        +   '<div class="sumr-donut-wrap">' + sumrDonutSvg(winPct) + '</div>'
        +   '<div class="sumr-stat"><div class="sumr-stat-num lose">' + fmtInt(losses) + '</div>'
        +     '<div class="sumr-stat-lbl lose">负 <b>' + losePct + '%</b></div></div>'
        + '</div>'
        + '<div class="sumr-oppo-list">' + (rowsHtml || '<div class="sumr-empty">暂无对阵记录</div>') + '</div>'
        + '</div>';
}

filterSumUserList('');
buildSumSeasonList();
})();