"""我的关注 (watchlist.html): every watched user's ATP and WTA status side by side.

Watch lists live in the browser (localStorage ``ts.watch.v1``, shared with the
ranking pages' ☆ menu); this page only embeds per-user data for both tours as
JSON and renders the cards client-side.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Optional

import pandas as pd

from site_html.common import _inner_page_shell
from site_html.rank_ui import CSS_RANK, JS_HIST, ask_modal_html, history_modal_html

_TOUR_PAGES = {"ATP": "atp_ranking.html", "WTA": "wta_ranking.html"}

_LINK = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
         'aria-hidden="true"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/>'
         '<path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/></svg>')
_STAR = ('<svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">'
         '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg>')
_PLUS = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
         'aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>')


def _clean(v):
    """JSON-safe scalar: NA → None, whole floats → int, the rest as text."""
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return int(v) if float(v).is_integer() else float(v)
    s = str(v).strip()
    return s if s and s.lower() != "nan" else None


def _picks(raw) -> list[str]:
    """选人明细 as a list of names (same parsing as the ranking table's data-detail)."""
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        try:
            parsed = ast.literal_eval(s)
            return [str(x) for x in parsed] if isinstance(parsed, list) else [s]
        except Exception:
            return [s]
    return [] if _clean(raw) is None else [str(raw)]


# column → short JSON key (only what the cards and the history dialog use)
_FIELDS = {"即时排名": "r", "排名变化": "c", "即时积分": "p", "当前状态": "s", "今日主选": "m",
           "今日备选": "a", "杀手球员": "k", "存活天数": "d"}


def _tour_payload(df: Optional[pd.DataFrame], event: Optional[str]) -> dict:
    """{"event": name | None, "users": {username: {r, c, p, s, m, a, k, d, h}}}."""
    users: dict[str, dict] = {}
    if df is not None and not df.empty and "用户名" in df.columns:
        cols = [c for c in _FIELDS if c in df.columns]
        for row in df.to_dict("records"):
            name = _clean(row.get("用户名"))
            if name is None:
                continue
            u = {_FIELDS[c]: v for c in cols if (v := _clean(row.get(c))) is not None}
            if "选人明细" in row:
                u["h"] = _picks(row.get("选人明细"))
            users[str(name)] = u
    return {"event": event or None, "users": users}


def render_watch_page(
    atp_df: Optional[pd.DataFrame],
    wta_df: Optional[pd.DataFrame],
    updated: str,
    atp_event: Optional[str] = None,
    wta_event: Optional[str] = None,
    output_path: str | Path = "watchlist.html",
) -> str:
    """Write the watchlist page.

    ``atp_df`` / ``wta_df`` are the same views the live ranking pages render
    (after prepare_rank_change / hide_today_picks_for_eliminated …), so every
    number here matches the user's row there.
    """
    data = {
        "ATP": {**_tour_payload(atp_df, atp_event), "href": _TOUR_PAGES["ATP"]},
        "WTA": {**_tour_payload(wta_df, wta_event), "href": _TOUR_PAGES["WTA"]},
    }
    # "</" must not end the <script> block early
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    body = f"""\
<div class="rk wl" id="wl">
  <script type="application/json" id="wlData">{blob}</script>
  <div class="rk-card wl-share-in" id="wlImport" role="region" aria-label="收到分享的关注列表" hidden></div>
  <section class="rk-card wl-start" id="wlStart" hidden>
    <span class="wl-start-ic">{_STAR}</span>
    <h2>还没有关注任何人</h2>
    <p>先告诉我们你是谁，你的 ATP 和 WTA 状态会固定在最上面。之后可以新建列表。</p>
    <form class="wl-me-form" id="wlMeForm">
      <label class="rk-me-lbl" for="wlMeInput">你的用户名</label>
      <span class="wl-me-row"><input id="wlMeInput" class="rk-input" autocomplete="off" placeholder="输入你的用户名">
      <button type="submit" class="rk-btn rk-btn-pri">设为我</button>
      <div class="rk-pop rk-sug" id="wlMeSug" role="listbox" aria-label="用户名建议" hidden></div></span>
    </form>
    <div class="wl-start-act">
      <button type="button" class="rk-btn rk-tab-new" id="wlStartNew">+ 新建列表</button>
      <a class="rk-btn" href="atp_ranking.html">去 ATP 排名页挑人<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg></a>
    </div>
  </section>
  <section class="rk-card wl-bar" id="wlBar">
    <div class="rk-watch">
      <span class="rk-watch-t"><span class="rk-star-ic">{_STAR}</span>列表</span>
      <span class="rk-watch-tabs" id="wlTabs" role="group" aria-label="关注列表"></span>
      <span class="rk-watch-new" id="wlNew"></span>
      <div class="wl-add">
        <label class="wl-add-box">{_PLUS}<span class="rk-sr" id="wlAddLbl">添加用户</span>
          <input id="wlAdd" autocomplete="off" aria-labelledby="wlAddLbl">
          <button type="button" class="rk-btn rk-btn-sm rk-btn-pri" id="wlAddBtn">关注</button></label>
        <div class="rk-pop rk-sug wl-sug" id="wlSug" role="listbox" aria-label="用户名建议" hidden></div>
      </div>
    </div>
    <div class="rk-manage" id="wlManage" hidden></div>
  </section>
  <span class="rk-sr" id="wlLive" aria-live="polite"></span>
  <div class="wl-grid" id="wlGrid"></div>
  <div class="wl-empty" id="wlEmpty" hidden></div>
  <p class="rk-note wl-foot">关注列表只保存在本机浏览器，和排名页的 ☆ 菜单共用；“复制分享链接”可在其他设备打开同一份列表。▲▼ 为相对当前排名的变化。</p>
  {history_modal_html("ATP", tour_switch=True)}
  {ask_modal_html()}
</div>"""

    title_extra = (
        '<span class="wl-count" id="wlCount"></span>'
        '<span class="wl-share-wrap"><span class="wl-share-note" id="wlShareNote" aria-live="polite"></span>'
        f'<button type="button" class="wl-share" id="wlShare">'
        f'<span class="cp-in">{_LINK}复制分享链接</span></button></span>'
    )
    html_str = _inner_page_shell(
        page_title="我的关注",
        title="我的关注",
        tour="",
        eyebrow="Watchlist · ATP + WTA",
        updated=updated,
        extra_tags=None,
        body_content=body,
        extra_css=CSS_RANK + "\n" + CSS_WATCH,
        page=str(output_path),
        late_js=JS_HIST + JS_WATCH,
        title_extra=title_extra,
    )
    Path(output_path).write_text(html_str, encoding="utf-8")
    return html_str


CSS_WATCH = """\
.page-header{--tour:#1c3f94;}
body.dark .page-header{--tour:#8fb0ff;}
.page-header .page-eye{color:var(--tour);font-size:11px;font-weight:700;letter-spacing:.24em;}
.page-title .ttag:empty{display:none;}
.wl-count{font-family:'Space Mono',monospace;font-size:13px;font-weight:400;color:var(--muted);}
.wl-count:empty{display:none;}
.wl-share-wrap{margin-left:auto;display:inline-flex;align-items:center;gap:10px;}
.wl-share-wrap[hidden]{display:none;}
.wl-share-note{font-family:'Noto Sans SC',sans-serif;font-size:12px;font-weight:400;color:var(--ok);}
.wl-share-note.err{color:var(--bad);}
.page-header,.wl{--ok:#1e6b47;--bad:#9a3a28;--bad-bg:#f8e3dd;}
body.dark .page-header,body.dark .wl{--ok:#7dcea0;--bad:#ff9a7a;--bad-bg:rgba(255,122,84,.12);}
.wl-share{display:inline-flex;align-items:center;justify-content:center;min-height:44px;min-width:150px;padding:0 18px;border-radius:999px;
    border:1px solid var(--border);background:var(--surface);color:var(--ink);font-family:'Noto Sans SC',sans-serif;font-size:13px;font-weight:700;
    cursor:pointer;overflow:hidden;transition:background-color .2s ease-out,border-color .2s ease-out,color .2s ease-out;}
.wl-share:hover{border-color:var(--primary-rim);color:var(--primary-dark);}
.wl-share:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
.wl-share .cp-in{display:inline-flex;align-items:center;gap:6px;}
.wl-share.ok{background:var(--ok);border-color:var(--ok);color:#fff;animation:rkPress .24s ease-out;}
body.dark .wl-share.ok{color:#06140c;}
.wl-share.err{background:var(--bad-bg);border-color:var(--bad);color:var(--bad);}
.wl-share.ok .cp-in{animation:rkUp .2s ease-out both;}
.wl-share.err .cp-in{animation:rkShake .3s ease-out both;}
.wl-share.back .cp-in{animation:rkDown .2s ease-out both;}
.wl-share .cp-draw{stroke-dasharray:24;animation:rkDraw .28s .08s ease-out both;}
.wl[hidden],.wl [hidden]{display:none !important;}

/* toolbar */
.wl-bar{overflow:visible;}
.wl-bar .rk-watch{border-radius:12px;border-bottom:0;}
.wl-bar .rk-watch:has(+.rk-manage:not([hidden])){border-radius:12px 12px 0 0;border-bottom:1px solid var(--star-rim);}
.wl .rk-tab{min-height:40px;padding:0 14px;font-size:13px;}
.wl .rk-new-form .rk-input{min-height:40px;}
.wl-add{margin-left:auto;position:relative;}
.wl-add-box{display:flex;align-items:center;gap:8px;min-height:40px;padding:0 4px 0 14px;border-radius:999px;border:1px solid var(--border);
    background:var(--drop-bg);color:var(--muted);}
.wl-add-box:focus-within{border-color:var(--primary);}
.wl-add-box input{border:0;outline:0;background:transparent;font:inherit;font-size:14px;color:var(--ink);width:180px;min-width:0;}
.wl-add-box .rk-btn{min-height:32px;}
.wl-sug{top:46px;left:auto;right:0;width:280px;}
.wl-manage-t{flex:1;font-size:13px;color:var(--muted);}
.wl-manage-t b{font-family:'Noto Serif SC',serif;font-size:15px;color:var(--ink);}

/* share-link import + first visit */
.wl-share-in{border:1px solid var(--me-rim);border-top:3px solid var(--me);padding:18px 20px;display:flex;flex-direction:column;gap:12px;}
.wl-share-in h2,.wl-start h2{margin:0;font-family:'Noto Serif SC',serif;font-size:18px;color:var(--ink);}
.wl-share-in .rk-eye{color:var(--me);}
.wl-lists{display:flex;flex-wrap:wrap;gap:8px;}
.wl-lists span{padding:4px 12px;border-radius:999px;background:var(--star-dim);color:var(--ink2);font-size:13px;}
.wl-lists b{font-family:'Space Mono',monospace;font-weight:400;}
.wl-act{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}
.wl-start{padding:28px;display:flex;flex-direction:column;align-items:flex-start;gap:14px;max-width:640px;}
.wl-start-ic svg{width:40px;height:40px;fill:none;stroke:var(--star);stroke-width:1.6;}
.wl-start p{margin:0;font-size:14px;line-height:1.7;color:var(--muted);}
.wl-me-form{width:100%;display:flex;flex-direction:column;gap:6px;}
.wl-me-row{display:flex;gap:8px;position:relative;}
.wl-me-row .rk-input{flex:1;min-height:44px;}
.wl-start-act{display:flex;flex-wrap:wrap;gap:10px;}
.wl-start-act a{text-decoration:none;}

/* cards */
.wl-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;}
.wl-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 18px 18px;display:flex;flex-direction:column;gap:12px;
    min-width:0;transition:transform .2s ease-out,box-shadow .2s ease-out;}
.wl-card.hov{transform:translateY(-2px);box-shadow:0 6px 18px rgba(5,20,32,.08);}
body.dark .wl-card.hov{box-shadow:0 6px 18px rgba(0,0,0,.4);}
.wl-card.me{border-color:var(--me-rim);box-shadow:inset 3px 0 0 var(--me);}
.wl-card.me.hov{box-shadow:inset 3px 0 0 var(--me),0 6px 18px rgba(5,20,32,.08);}
.wl-hd{display:flex;align-items:center;gap:8px;min-width:0;}
.wl-name{font-family:'Noto Serif SC',serif;font-size:18px;font-weight:700;color:var(--ink);border:0;background:transparent;padding:0;min-height:44px;
    min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-decoration:underline;text-decoration-color:var(--primary-rim);text-underline-offset:4px;}
.wl-name:hover{color:var(--primary-dark);}
.wl-hd .rk-mebadge{flex-shrink:0;}
.wl-hd .rk-tags{overflow:hidden;text-overflow:ellipsis;font-size:12px;}
.wl-gone{margin-left:auto;flex-shrink:0;font-size:12px;font-weight:700;padding:3px 10px;border-radius:999px;background:var(--bad-bg);color:var(--bad);}
.wl-rm{margin-left:auto;flex-shrink:0;width:44px;height:44px;border:0;border-radius:50%;background:transparent;color:var(--muted);
    display:flex;align-items:center;justify-content:center;}
.wl-gone+.wl-rm{margin-left:0;}
.wl-rm:hover{background:var(--bad-bg);color:var(--bad);}
.wl-tours{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}
.wl-t{--c:var(--secondary);--eye:color-mix(in srgb,var(--secondary) 62%,var(--ink));border:1px solid var(--border);border-top:3px solid var(--c);border-radius:10px;
    padding:12px 14px;display:flex;flex-direction:column;gap:8px;min-width:0;background:var(--surface);color:var(--ink);text-decoration:none;}
.wl-t[data-t="WTA"]{--c:var(--primary);--eye:var(--primary-dark);}
body.dark .wl-t{--eye:var(--c);}
.wl-t.off{background:var(--surface2);}
.wl-t.lost{background:color-mix(in srgb,var(--bad-bg) 35%,var(--surface));}
.wl-t-eye{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.16em;color:var(--eye);
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.wl-t-big{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;}
.wl-t-rank{font-family:'Space Mono',monospace;font-size:28px;font-weight:700;line-height:1.1;}
.wl-t.lost .wl-t-rank{color:var(--muted);}
.wl-t-big .rank{font-family:'Space Mono',monospace;font-size:13px;font-weight:700;}
.wl-t-big .rank.up{color:var(--ok);}.wl-t-big .rank.down{color:var(--bad);}.wl-t-big .rank.same{color:var(--muted);}
.wl-t-pts{margin-left:auto;font-family:'Space Mono',monospace;font-size:14px;color:var(--ink2);}
.wl-t-pts small{font-family:'Noto Sans SC',sans-serif;font-size:11px;color:var(--muted);}
.wl-t .st-badge{align-self:flex-start;}
.wl-t-pk{display:grid;grid-template-columns:32px minmax(0,1fr);gap:4px 8px;font-size:13px;}
.wl-t-pk span{color:var(--muted);}
.wl-t-pk b{font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.wl-t-pk b.alt{font-weight:400;color:var(--muted);}
.wl-t-kill{display:flex;align-items:center;gap:5px;font-size:12px;font-weight:700;color:var(--bad);min-width:0;}
.wl-t-kill svg{flex-shrink:0;}
.wl-t-msg{font-size:13px;color:var(--muted);padding:6px 0;}
.wl-t-go{margin-top:auto;display:flex;align-items:center;gap:4px;min-height:32px;font-size:12px;color:var(--primary-dark);}
body.dark .wl-t-go{color:var(--primary);}
a.wl-t-go:hover{text-decoration:underline;}
.wl-empty{padding:40px;text-align:center;font-size:14px;line-height:1.7;color:var(--muted);background:var(--surface);border:1px dashed var(--border);border-radius:12px;}
.wl-foot{margin:0;line-height:1.6;}
.wl-card{animation:rkPop .22s ease-out both;}

@media(max-width:720px){
    .wl-count{font-size:12px;}
    .wl-share-wrap{margin-left:0;flex-basis:100%;}
    .wl-share{min-width:0;}
    .page-header .page-eye{font-size:13px;letter-spacing:.14em;}
    .wl .rk-watch{flex-wrap:wrap;overflow:visible;}
    .wl-bar .rk-watch>.rk-watch-t{display:none;}
    .wl .rk-tab{min-height:44px;}
    .wl-add{margin-left:0;flex:1 0 100%;}
    .wl-add-box{min-height:44px;}
    .wl-add-box input{flex:1;width:auto;font-size:16px;}
    .wl-add-box .rk-btn{min-height:36px;}
    .wl-sug{left:0;right:0;width:auto;}
    .wl-grid{grid-template-columns:minmax(0,1fr);gap:12px;}
    .wl-card{padding:8px 12px 12px;gap:10px;}
    .wl-name{font-size:17px;}
    .wl-tours{gap:8px;}
    .wl-t{padding:10px;gap:6px;}
    .wl-t-eye{font-size:13px;letter-spacing:.08em;}
    .wl-t-rank{font-size:22px;}
    .wl-t-pts{margin-left:0;flex-basis:100%;font-size:13px;}
    .wl-t-pk{grid-template-columns:minmax(0,1fr);gap:2px;}
    .wl-t-pk span{display:none;}
    .wl-t-pk b.alt::before{content:"备 ";}
    .wl-t-pk b.last::before{content:"最后一选 ";}
    .wl-start{padding:20px 16px;}
    .wl-me-row{flex-direction:column;}
    .wl-start-act{width:100%;flex-direction:column;}
    .wl-empty{padding:24px 16px;}
    .rk-dlg-act{gap:6px;}
    .rk-hist-seg button{padding:0 10px;}
}
@media(prefers-reduced-motion:reduce){
    .wl-card,.wl-share{transition:none;}
    .wl *,.wl-card,.wl-share,.wl-share *{animation:none !important;}
}"""


JS_WATCH = r"""
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
"""
