"""Killer-board page renderer."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from site_html.common import _df_to_html_table, _inner_page_shell

_CSS_KILLER = """\
.pod-card[data-detail],.filterable-table tr.killer-clickable{cursor:pointer;}
.pod-card[data-detail]:hover{border-color:var(--primary);}
.pod-hint{margin-top:6px;font-size:10px;color:var(--faint);}
.dz-list{display:grid;gap:8px;padding:6px 4px;}
.dz-item{display:flex;align-items:center;gap:12px;padding:12px 14px;
    background:var(--surface2);border:1px solid var(--border2);border-radius:10px;}
.dz-item.top{border-color:var(--primary);background:var(--primary-dim);}
.dz-rank{flex-shrink:0;width:22px;height:22px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    font-family:'Space Mono',monospace;font-size:11px;font-weight:700;
    background:var(--border2);color:var(--muted);}
.dz-item.top .dz-rank{background:var(--primary);color:#fff;}
.dz-main{flex:1;min-width:0;}
.dz-where{font-size:11px;color:var(--muted);letter-spacing:.02em;}
.dz-who{margin-top:3px;font-size:14px;color:var(--ink);font-weight:600;
    font-family:'Noto Serif SC',serif;}
.dz-who i{font-style:normal;font-size:11px;font-weight:400;color:var(--faint);margin-right:6px;}
.dz-kills{flex-shrink:0;text-align:right;font-family:'Space Mono',monospace;
    font-size:22px;font-weight:700;color:var(--primary);line-height:1;}
.dz-kills small{display:block;margin-top:4px;font-size:10px;font-weight:400;color:var(--faint);}
.kn-bar{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 16px;}
.kn-seg{display:inline-flex;border:1px solid var(--border);border-radius:999px;
    overflow:hidden;background:var(--surface);}
.kn-seg a{padding:7px 16px;font-size:12px;color:var(--muted);text-decoration:none;
    letter-spacing:.04em;transition:background .15s,color .15s;}
.kn-seg a:hover{color:var(--primary);}
.kn-seg a[aria-current="page"]{background:var(--primary);color:#fff;font-weight:700;}
.dz-empty{display:flex;align-items:center;gap:12px;padding:12px 14px;
    border:1px dashed var(--border);border-radius:10px;color:var(--faint);font-size:13px;}
"""

_JS_KILLER_DETAIL = """\
document.addEventListener('DOMContentLoaded',()=>{
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
                +'<div class="dz-kills">'+esc(f[3])+'<small>__UNIT__</small></div></div>';
        }).join('');
        if(footer) footer.textContent='__FOOT__';
        modal.classList.add('show');
    }
    function parse(el){
        let d=[]; try{ d=JSON.parse(el.dataset.detail||'[]'); }catch(_e){ d=[]; }
        return Array.isArray(d)?d:[];
    }
    document.querySelectorAll('.filterable-table tbody tr[data-detail]').forEach(row=>{
        row.addEventListener('click',()=>{
            const cell=row.querySelectorAll('td')[nameIdx>=0?nameIdx:1];
            open(cell?cell.textContent.trim():'',parse(row));
        });
    });
    document.querySelectorAll('.pod-card[data-detail]').forEach(card=>{
        card.addEventListener('click',()=>open(card.dataset.name||'',parse(card)));
    });
});
"""

_DETAIL_MODAL = """\
<div id="detail-modal" class="detail-modal">
  <div class="detail-card">
    <div class="detail-hd">
      <div class="detail-title-wrap">
        <div class="detail-icon">☠</div>
        <div>
          <div class="detail-title">__TITLE__</div>
          <div class="detail-meta" id="detail-meta-line"></div>
        </div>
      </div>
      <button id="detail-close" class="detail-close" type="button">✕ 关闭</button>
    </div>
    <div class="detail-scroll">
      <div id="detail-body" class="detail-list"></div>
    </div>
    <div class="detail-footer" id="detail-footer"></div>
  </div>
</div>"""


_BOARDS = (("killer", "杀手榜"), ("nemesis", "克星榜"))
_FILE_RE = re.compile(r"(\d{4})?(atp|wta)(killer|nemesis)\.html")


def _switch_html(output_path: str | Path, season: int | None) -> str:
    """Board (杀手榜 / 克星榜) and range (赛季 / 历年总榜) switches for this page."""
    m = _FILE_RE.fullmatch(Path(output_path).name)
    if not m:
        return ""
    year, tour, board = m.group(1) or "", m.group(2), m.group(3)

    def seg(items: list[tuple[str, str, bool]], label: str) -> str:
        links = "".join(
            '<a href="{href}"{cur}>{text}</a>'.format(
                href=href,
                cur=' aria-current="page"' if cur else "",
                text=html.escape(text),
            )
            for text, href, cur in items
        )
        return f'<div class="kn-seg" role="group" aria-label="{label}">{links}</div>'

    groups = [
        seg(
            [(text, f"{year}{tour}{key}.html", key == board) for key, text in _BOARDS],
            "榜单",
        )
    ]
    if season:
        groups.append(
            seg(
                [
                    (f"{season} 赛季", f"{season}{tour}{board}.html", bool(year)),
                    ("历年总榜", f"{tour}{board}.html", not year),
                ],
                "范围",
            )
        )
    return f'<div class="kn-bar">{"".join(groups)}</div>'


def render_killer_page(
    df: pd.DataFrame,
    tour: str,
    eyebrow: str,
    updated: str,
    title: str = "幸存者杀手榜",
    extra_tags: Optional[list[str]] = None,
    kills_col: str = "带走人数",
    rate_col: str = "杀人率",
    name_col: str = "球员",
    output_path: str | Path = "killer.html",
    detail_col: str = "_惨案",
    subtitle: str = "不含年终总决赛(循环赛制、仅 8 人参赛)",
    rate_label: str = "杀人率",
    modal_title: str = "惨案记录",
    hint: str = "点击查看惨案",
    unit_label: str = "人被带走",
    footer_label: str = "带走人数最多的 3 次",
    season: int | None = None,
) -> str:
    """
    Build and write a killer-board page with a top-3 podium.

    Parameters
    ----------
    df : pd.DataFrame
        Killer stats data. Expected columns (in order):
        排名 | 球员 | 带走人数 | 杀人率 | 最高单次带走人数 | 选择人数
    title : str
        Large page title, e.g. "幸存者杀手榜".
    tour : str
        "ATP" or "WTA".
    eyebrow : str
        Small label above the title.
    updated : str
        Timestamp string.
    extra_tags : list[str] or None
        Additional pill tags, e.g. ["历年总榜"] or ["2026"].
    kills_col : str
        Column name for kill count (shown large in podium).
    rate_col : str
        Column name for kill rate.
    name_col : str
        Column name for player name.
    rate_label, modal_title, hint, unit_label, footer_label : str
        Podium rate caption, detail-modal title, podium click hint and the
        modal's unit/footer wording (the nemesis board reuses this page with
        its own wording).
    season : int or None
        Current season; enables the 赛季 / 历年总榜 switch (the board switch
        needs only the output file name).
    output_path : str or Path

    Returns
    -------
    str : the generated HTML string.
    """
    # Build podium from first 3 rows
    pod_classes = ["p1", "p2", "p3"]
    medals = ["#1", "#2", "#3"]
    podium_cards = []
    for i, (_, row) in enumerate(df.head(3).iterrows()):
        name = html.escape(str(row.get(name_col, "")))
        kills = html.escape(str(row.get(kills_col, "")))
        rate = html.escape(str(row.get(rate_col, "")))
        detail_attr = ""
        if detail_col in df.columns:
            detail_json = html.escape(
                json.dumps(list(row[detail_col]), ensure_ascii=False), quote=True
            )
            detail_attr = f' data-detail="{detail_json}" data-name="{name}"'
        podium_cards.append(f"""\
<div class="pod-card {pod_classes[i]}"{detail_attr}>
  <div class="pod-medal">{medals[i]}</div>
  <div class="pod-name">{name}</div>
  <div class="pod-kills">{kills}</div>
  <div class="pod-kills-lbl">{html.escape(kills_col)}</div>
  <div class="pod-rate">{html.escape(rate_label)} {rate}</div>
  {f'<div class="pod-hint">{html.escape(hint)}</div>' if detail_attr else ''}
</div>""")

    podium_html = '<div class="podium">\n' + "\n".join(podium_cards) + "\n</div>"
    has_detail = detail_col in df.columns
    main_table_html = _df_to_html_table(
        df,
        rank_change_col=None,
        detail_col=detail_col if has_detail else None,
        row_click_class="killer-clickable" if has_detail else "",
    )

    body = f"""\
{_switch_html(output_path, season)}

{podium_html}

<div class="stats-row">
  <div class="row-count">显示 <b id="visible-count">0</b> / <b id="total-count">0</b> 行</div>
</div>

<div class="table-wrapper">
  <div id="table-container">
    {main_table_html}
  </div>
</div>
{_DETAIL_MODAL.replace("__TITLE__", html.escape(modal_title)) if has_detail else ""}"""

    html_str = _inner_page_shell(
        page_title=title,
        title=title,
        tour=tour,
        eyebrow=eyebrow,
        updated=updated,
        extra_tags=extra_tags,
        body_content=body,
        extra_js=_JS_KILLER_DETAIL.replace("__UNIT__", unit_label).replace("__FOOT__", footer_label)
        if has_detail
        else "",
        extra_css=_CSS_KILLER,
        subtitle=subtitle,
        page=str(output_path),
    )

    Path(output_path).write_text(html_str, encoding="utf-8")
    return html_str

