"""Ranking page v3: filter chips, watch lists, "me", mobile cards, route bar.

Everything here enhances the table built by ``_JS_TABLE``. The page script is
emitted in its own ``<script>`` block after the shared ones (storage throws on
``data:`` URLs, and the table must already be built when it runs).
"""
from __future__ import annotations

import html
import json
from typing import Optional

_STAR = ('<svg width="16" height="16" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">'
         '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg>')
_LINK = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
         'aria-hidden="true"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/>'
         '<path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/></svg>')
_SEARCH = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
           'aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>')
_CUP = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'aria-hidden="true"><path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/>'
        '<path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/></svg>')
_REPLAY = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
           'aria-hidden="true"><path d="M4 12a8 8 0 1 0 2.4-5.7"/><path d="M4 4v5h5"/></svg>')
_DOWN = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
         'aria-hidden="true"><path d="M12 5v14M6 13l6 6 6-6"/></svg>')


def me_card_html() -> str:
    """Sticky 我的状态 card; filled by JS_RANK."""
    return f"""\
<section class="rk-card rk-me" id="rkMe" aria-live="polite">
  <div class="rk-me-hd"><span class="rk-eye rk-eye-me">MY STATUS</span><span class="rk-me-name" id="rkMeName"></span></div>
  <div class="rk-me-set" id="rkMeSet">
    <label class="rk-me-lbl" for="rkMeInput">输入你的用户名，置顶显示你的状态</label>
    <div class="rk-me-row"><input id="rkMeInput" class="rk-input" autocomplete="off" placeholder="你的用户名">
    <button type="button" class="rk-btn rk-btn-pri" id="rkMeSave">设为我</button>
    <div class="rk-pop rk-sug" id="rkMeSug" role="listbox" aria-label="用户名建议" hidden></div></div>
    <span class="rk-note">也可在任意行的 ☆ 菜单里选“设为我”。只保存在本机浏览器。</span>
  </div>
  <div class="rk-me-body" id="rkMeBody" hidden>
    <div class="rk-me-big"><span class="rk-me-rank" id="rkMeRank"></span><span class="rk-me-pts" id="rkMePts"></span><span class="rk-me-d" id="rkMeD"></span></div>
    <div class="rk-me-pick" id="rkMePick"></div>
    <button type="button" class="rk-btn rk-btn-pri rk-btn-block" id="rkMeJump">跳到我的行{_DOWN}</button>
    <button type="button" class="rk-btn-text" id="rkMeChange">更换用户名</button>
  </div>
</section>"""


def route_bar_html(players: list[str]) -> str:
    """夺冠路线查询: dropdown multi-select whose result filters the main table."""
    if not players:
        return ""
    opts = "".join(
        f'<button type="button" role="option" aria-selected="false" class="rk-opt" data-v="{html.escape(p, quote=True)}">'
        f'<span class="rk-box" aria-hidden="true"></span><span class="rk-opt-l">{html.escape(p)}</span></button>'
        for p in players
    )
    return f"""\
<div class="rk-route" id="rkRoute">
  <span class="rk-route-t">{_CUP}夺冠路线查询</span>
  <span class="rk-route-if">你还能夺冠吗？</span>
  <div class="rk-dd">
    <button type="button" class="rk-dd-btn" id="rkRouteBtn" aria-haspopup="listbox" aria-expanded="false"><span id="rkRouteLbl">选择球员…</span><span class="rk-chev" aria-hidden="true">▾</span></button>
    <div class="rk-pop rk-dd-pop" id="rkRoutePop" role="listbox" aria-multiselectable="true" aria-label="选择冠军球员" hidden>
      <span class="rk-eye rk-pop-eye">CHAMPION IF</span>
      <input type="text" class="rk-input rk-pop-search" id="rkRouteSearch" placeholder="搜索球员…" aria-label="搜索球员">
      <div class="rk-opts">{opts}</div>
      <div class="rk-pop-ft"><button type="button" class="rk-btn-text" id="rkRouteClr">清除</button><button type="button" class="rk-btn rk-btn-pri" id="rkRouteDone">完成</button></div>
    </div>
  </div>
  <span class="rk-route-sel" id="rkRouteSel"></span>
  <span class="rk-route-res" id="rkRouteRes" aria-live="polite" hidden></span>
  <span class="rk-route-hint">可多选：只保留这些球员都还没用过、且仍存活的用户</span>
</div>"""


def table_card_open(players: list[str]) -> str:
    """Toolbar rows above the table: watch lists, status chips + search, route bar."""
    return f"""\
<section class="rk-card rk-tcard" id="watch">
  <div class="rk-share" id="rkShare" hidden></div>
  <div class="rk-watch" id="rkWatch">
    <span class="rk-watch-t"><span class="rk-star-ic">{_STAR}</span>关注</span>
    <span class="rk-watch-tabs" id="rkWatchTabs"></span>
    <span class="rk-watch-new" id="rkWatchNew"></span>
    <button type="button" class="rk-btn rk-btn-sm rk-share-btn" id="rkShareBtn">{_LINK}<span>复制分享链接</span></button>
  </div>
  <div class="rk-manage" id="rkManage" hidden></div>
  <div class="rk-finals-note" id="rkFinals" hidden><span class="rk-f" aria-hidden="true"></span><span>底色标出的前 <b id="rkFinalsN"></b> 名为当前年终总决赛入围用户，虚线为入围线</span></div>
  <div class="rk-chips">
    <span class="rk-chip-row" id="rkChips" role="group" aria-label="按状态筛选"></span>
  </div>
{route_bar_html(players)}"""


def table_card_close() -> str:
    return f"""\
  <div class="rk-cards" id="rkCards" aria-live="off"></div>
  <div class="rk-empty" id="rkEmpty" hidden>这个筛选下暂时没有人</div>
  <div class="rk-foot">
    <button type="button" class="rk-btn rk-btn-sm" id="rkReplay">{_REPLAY}<span>重播排名变化</span></button>
    <span class="rk-count">显示 <b id="visible-count">0</b> / <span id="total-count">0</span></span>
    <button type="button" class="rk-btn" id="rkMore" hidden>再显示 50 行</button>
  </div>
</section>
<div class="rk-pop rk-picker" id="rkPicker" role="dialog" aria-label="加入哪个列表" hidden></div>
{ask_modal_html()}"""


def ask_modal_html() -> str:
    """In-page confirm (window.confirm is blocked in embedded browsers and returns false)."""
    return """<div class="rk-modal" id="rkAsk" hidden>
  <div class="rk-dlg rk-ask" role="alertdialog" aria-modal="true" aria-labelledby="rkAskT" aria-describedby="rkAskD" tabindex="-1">
    <div class="rk-dlg-hd"><div class="rk-dlg-ttl"><span class="rk-eye">CONFIRM</span><h2 id="rkAskT"></h2></div></div>
    <p class="rk-ask-d" id="rkAskD"></p>
    <div class="rk-dlg-ft"><span></span><span class="rk-dlg-nav"><button type="button" class="rk-btn" data-close="1" data-v="0">取消</button><button type="button" class="rk-btn rk-ask-ok" data-v="1" id="rkAskOk"></button></span></div>
  </div>
</div>"""


_CLOSE = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
          'aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>')
_HELP = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
         'aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14"/>'
         '<path d="M12 17.5h.01"/></svg>')
_CURSOR = '<svg class="hp-cur" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 2l16 9-7 2-3 7z"/></svg>'


def help_button_html(hint: bool = False, expired: Optional[str] = None) -> str:
    """? button beside the page title, a quiet hint next to it, and (when ``expired`` is
    given) this settlement week's expiring points on a line of its own under the title."""
    out = f'<button type="button" class="rk-help-btn" id="rkHelpBtn" aria-haspopup="dialog" aria-label="使用说明" title="使用说明">{_HELP}</button>'
    if hint:
        out += f'<span class="rk-tnote">点击<span class="rk-tnote-ic" aria-hidden="true">{_HELP}</span>查看页面说明</span>'
    if expired is not None:
        out += (f'<span class="rk-tline"><span class="rk-tnote rk-tnote-exp" title="本结算周期失效的去年同周积分">'
                f'失效分数：{html.escape(expired.strip() or "无")}</span></span>')
    return out


def history_modal_html(eyebrow: str, tour_switch: bool = False) -> str:
    """选人历史 dialog; JS_RANK (or the watch page) fills it via ``tsHist``.

    ``tour_switch`` adds an ATP / WTA toggle (watch page: one user, two tours).
    """
    seg = (
        '<div class="rk-hist-seg" id="rkHistSeg" role="group" aria-label="巡回赛">'
        '<button type="button" data-t="ATP" aria-pressed="true">ATP</button>'
        '<button type="button" data-t="WTA" aria-pressed="false">WTA</button></div>'
        if tour_switch else ""
    )
    return f"""<div class="rk-modal" id="rkHist" hidden>
  <div class="rk-dlg rk-dlg-hist" role="dialog" aria-modal="true" aria-labelledby="rkHistName" tabindex="-1">
    <div class="rk-dlg-hd">
      <div class="rk-dlg-ttl"><span class="rk-eye rk-eye-tour" id="rkHistEye">PICK HISTORY · {html.escape(eyebrow)}</span><h2 id="rkHistName"></h2></div>
      <span class="rk-dlg-act">{seg}<button type="button" class="rk-x" data-close="1" aria-label="关闭">{_CLOSE}</button></span>
    </div>
    <div class="rk-hist-stats" id="rkHistStats"></div>
    <div class="rk-hist-head"><span>天数</span><span>选人</span><span>结果</span></div>
    <div class="rk-hist-list" id="rkHistList"></div>
    <div class="rk-hist-ft">
      <span class="rk-note" id="rkHistSum"></span>
    </div>
  </div>
</div>"""


def _help_steps(has_finals: bool) -> list[tuple[str, str, str]]:
    chip = '<span class="hp-chip">{}</span>'
    s1 = ("先看与你相关的人",
          "默认只显示今天已选人的用户。点状态标签切换存活 / 未完赛 / 淘汰等，底部显示筛到的人数，长表格每次加载 50 行。",
          '<div class="hp-row">' + chip.format("全部 756") + '<span class="hp-chip on">已选 80<i class="hp-ping"></i></span>'
          + chip.format("存活 41") + chip.format("未完赛 29") + '</div><div class="hp-lines"><i></i><i></i><i></i></div>'
          '<span class="hp-foot">显示 80 / 756 · 再显示 50 行</span>')
    s2 = ("每一列都能筛选",
          "表头下的筛选框：文字列可多选，排名、积分等数字列可按范围筛选；用户名可输入多个关键词（如 zoe, eric）。条件之间叠加生效。",
          '<div class="hp-grid"><b>排名</b><b>用户名</b><b>今日主选</b><b>即时积分</b>'
          '<span>1 ~ 10</span><span>zoe, eric</span><span class="on">西里奇 等 2 项</span><span>≥ 4000</span></div>'
          '<div class="hp-menu"><span class="hp-ck on">西里奇</span><span class="hp-ck on">蒂兰特</span><span class="hp-ck">武基奇</span></div>'
          + _CURSOR)
    s3 = ("夺冠路线查询",
          "选择一名或多名球员，表格只保留这些球员都还没用过、且仍存活的用户 —— 看看谁还能靠他们走到最后。",
          '<div class="hp-row"><b class="hp-blue">你还能夺冠吗？</b><span class="hp-dd">已选 1 名球员 ▾</span><span class="hp-sel">蒂兰特 ✕</span></div>'
          '<div class="hp-list"><span><b>Dagenais</b><em>仍可选</em></span><span class="gone"><b>逍遥笑叹红尘</b><em>已用过</em></span>'
          '<span><b>做丞琳永远的歌迷ya</b><em>仍可选</em></span></div>')
    s4 = ("关注与“我”",
          "点每行的 ☆ 把人加进自己的关注列表，或设为“我”：你的行会高亮，右侧显示我的状态。列表只存在本机，可用“复制分享链接”带到别的设备。",
          '<div class="hp-row"><b class="hp-gold">★ 关注</b><span class="hp-chip gold">好友 2</span>' + chip.format("对手 2") + '</div>'
          '<div class="hp-list"><span class="me"><b>wennuan78</b><em class="hp-me">我</em></span><span><b>☆ 逍遥笑叹红尘</b><em class="hp-tag">★好友</em></span></div>'
          '<div class="hp-menu hp-menu-l"><span class="hp-ck on">好友</span><span class="hp-ck">对手</span><span class="hp-blue">设为“我”</span></div>')
    last = "即时排名旁的 ▲▼ 是排名变化，页面加载时变化的行会滑到新位置。点用户名查看选人历史，“复制统计”一键复制今日选人。"
    if has_finals:
        last += "底色标出的前 8 名为当前年终总决赛入围用户。"
    s5 = ("排名变化与更多",
          last,
          '<div class="hp-list"><span><b>1 · wennuan78</b><em>—</em></span><span class="hp-bump"><b>2 · 逍遥笑叹红尘</b><em class="up">▲2</em></span>'
          '<span><b>3 · 年终的W</b><em class="down">▼1</em></span></div><div class="hp-row"><span class="hp-ok">✓ 已复制</span></div>')
    return [s1, s2, s3, s4, s5]


def _help_steps_combined() -> list[tuple[str, str, str]]:
    chip = '<span class="hp-chip">{}</span>'
    s1 = ("ATP + WTA 联合排名",
          "这一页把两个巡回赛的成绩合在一起：总分 = ATP 总分 + WTA 总分，按总分排名。右侧列出每站赛事的得分，状态列分别显示两边的今日状态；点任意一行可看积分构成。",
          '<div class="hp-grid"><b>排名</b><b>用户名</b><b>总分</b><b>ATP / WTA</b>'
          '<span>1 —</span><span>wennuan78</span><span class="on">9750</span><span>4778 / 4972</span>'
          '<span>2 ▲1</span><span>逍遥笑叹红尘</span><span>9412</span><span>4231 / 5181</span></div>')
    s2 = ("每一列都能筛选",
          "表头下的筛选框：文字列可多选，总分、各站得分等数字列可按范围筛选；用户名可输入多个关键词（如 zoe, eric）。条件之间叠加生效。",
          '<div class="hp-grid"><b>排名</b><b>用户名</b><b>WTA状态</b><b>总分</b>'
          '<span>1 ~ 20</span><span>zoe, eric</span><span class="on">存活 等 2 项</span><span>≥ 9000</span></div>'
          '<div class="hp-menu"><span class="hp-ck on">存活</span><span class="hp-ck on">未完赛</span><span class="hp-ck">球员输球</span></div>'
          + _CURSOR)
    s3 = ("点用户查看积分构成",
          "点表格里任意一行，弹出这位用户的积分构成：切换 ATP / WTA，按赛事级别、场地（硬地 / 红土 / 草地）或积分失效月份查看，左侧列出每站得分与轮次。",
          '<div class="hp-row"><span class="hp-seg"><i class="on">ATP</i><i>WTA</i></span>'
          '<span class="hp-seg"><i>赛事类型</i><i class="on">场地</i><i>失效时间</i></span></div>'
          '<div class="hp-bd"><div class="hp-bd-list"><span class="s-hard">硬地 · 上海 <b>1000</b></span>'
          '<span class="s-clay">红土 · 罗马 <b>360</b></span><span class="s-grass">草地 · 哈雷 <b>180</b></span></div>'
          '<div class="hp-donut"><b>4778</b></div></div>' + _CURSOR)
    s4 = ("关注与“我”",
          "点每行的 ☆ 把人加进自己的关注列表，或设为“我”：你的行会高亮，上方显示我的状态。列表只存在本机，可用“复制分享链接”带到别的设备。",
          '<div class="hp-row"><b class="hp-gold">★ 关注</b><span class="hp-chip gold">好友 2</span>' + chip.format("对手 2") + '</div>'
          '<div class="hp-list"><span class="me"><b>wennuan78</b><em class="hp-me">我</em></span><span><b>☆ 逍遥笑叹红尘</b><em class="hp-tag">★好友</em></span></div>')
    s5 = ("排名变化",
          "排名旁的 ▲▼ 是相对上一次更新的变化，页面加载时变化的行会滑到新位置；底部“重播排名变化”可以再看一次。",
          '<div class="hp-list"><span><b>1 · wennuan78</b><em>1 —</em></span><span class="hp-bump"><b>2 · 逍遥笑叹红尘</b><em class="up">2 ▲1</em></span>'
          '<span><b>3 · 年终的W</b><em class="down">3 ▼1</em></span></div>')
    return [s1, s2, s3, s4, s5]


def help_modal_html(page_title: str, has_finals: bool = False, combined: bool = False,
                    steps: list[tuple[str, str, str]] | None = None) -> str:
    """使用说明: five auto-advancing steps with small animated previews.

    ``steps`` ((title, body, demo html) tuples) replaces the ranking-page steps.
    """
    steps = steps or (_help_steps_combined() if combined else _help_steps(has_finals))
    n = len(steps)
    panes = "".join(
        f'<section class="hp-step" data-i="{i}" aria-label="{html.escape(t)}" hidden>'
        f'<div class="hp-stage" aria-hidden="true">{demo}</div><h3>{html.escape(t)}</h3><p>{html.escape(body)}</p></section>'
        for i, (t, body, demo) in enumerate(steps)
    )
    bars = "".join('<span class="hp-bar"><i></i></span>' for _ in steps)
    return f"""<div class="rk-modal" id="rkHelp" hidden>
  <div class="rk-dlg rk-dlg-help" role="dialog" aria-modal="true" aria-labelledby="rkHelpT" tabindex="-1">
    <div class="rk-dlg-hd">
      <div class="rk-dlg-ttl"><span class="rk-eye rk-eye-me">HOW IT WORKS · <span id="rkHelpNo">1</span> / {n}</span><h2 id="rkHelpT">{html.escape(page_title)} · 使用说明</h2></div>
      <button type="button" class="rk-x" data-close="1" aria-label="关闭使用说明">{_CLOSE}</button>
    </div>
    <div class="hp-bars" aria-hidden="true">{bars}</div>
    <div class="hp-body" aria-live="polite">{panes}</div>
    <div class="rk-dlg-ft">
      <button type="button" class="rk-btn-text" id="rkHelpMute">不再自动显示</button>
      <span class="rk-dlg-nav"><button type="button" class="rk-btn" id="rkHelpPrev">上一步</button><button type="button" class="rk-btn rk-btn-pri" id="rkHelpNext">下一步</button></span>
    </div>
  </div>
</div>"""


def rank_config_json(tour: str) -> str:
    return json.dumps({"tour": tour.upper()}, ensure_ascii=False)


CSS_RANK = """\
.rk,.rk-modal,.rk-picker{--tour:var(--secondary);--ok:#1e6b47;--ok-bg:#e3f3ea;--bad:#9a3a28;--bad-bg:#f8e3dd;--me:#1c3f94;
    --me-dim:rgba(28,63,148,.07);--me-rim:rgba(28,63,148,.30);--star:#c49800;--star-dim:rgba(196,152,0,.10);--star-rim:rgba(196,152,0,.35);
}
.rk{display:flex;flex-direction:column;gap:20px;}
.rk,.rk-modal{--fin:var(--primary);--fin-dim:var(--primary-dim);--fin-rim:var(--primary-rim);}
.rk[data-tour="WTA"],.rk-modal[data-tour="WTA"]{--tour:var(--primary);}
body.dark .rk,body.dark .rk-modal,body.dark .rk-picker{--ok:#7dcea0;--ok-bg:rgba(72,168,120,.14);--bad:#ff9a7a;--bad-bg:rgba(255,122,84,.12);--me:#8fb0ff;
    --me-dim:rgba(143,176,255,.10);--me-rim:rgba(143,176,255,.34);--star:#f0c000;--star-dim:rgba(240,192,0,.10);--star-rim:rgba(240,192,0,.32);}
.page-header{border-left:3px solid var(--tour,var(--primary));padding-left:18px;}
.rk-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;}
.rk-eye{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--muted);}
.rk-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;}
.rk button,.rk-modal button,.rk-picker button{font-family:inherit;cursor:pointer;}
.rk-modal button:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
.rk button:focus-visible,.rk a:focus-visible,.rk input:focus-visible,.rk-picker button:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
.rk-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-height:44px;padding:0 16px;border-radius:999px;
    border:1px solid var(--border);background:var(--surface);color:var(--ink);font-size:13px;white-space:nowrap;}
.rk-btn:hover{border-color:var(--primary-rim);color:var(--primary-dark);}
.rk-btn-sm{min-height:36px;padding:0 12px;}
.rk-btn-pri{background:var(--me);border-color:var(--me);color:#fff;font-weight:700;}
.rk-btn-pri:hover{color:#fff;border-color:var(--me);filter:brightness(1.08);}
body.dark .rk-btn-pri{color:#06142a;}
.rk-btn-block{width:100%;}
.rk-btn-text{border:0;background:transparent;color:var(--muted);font-size:12px;min-height:36px;padding:0 8px;}
.rk-btn-text:hover{color:var(--primary-dark);}
.rk-input{font:inherit;font-size:14px;min-height:40px;border:1px solid var(--border);border-radius:10px;padding:0 12px;
    background:var(--drop-bg);color:var(--ink);min-width:0;}
.rk-note{font-size:12px;color:var(--muted);}

/* top row: picks summary + aside */
.rk-top{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:20px;align-items:stretch;}
.rk-aside{display:flex;flex-direction:column;gap:16px;min-width:0;}
.rk-top-solo{grid-template-columns:minmax(0,1fr);}
.rk-top-solo .rk-aside{display:block;}
.rk-top-solo .rk-me{display:grid;grid-template-columns:200px minmax(0,1fr);align-items:center;column-gap:24px;row-gap:8px;padding:16px 20px;}
.rk-top-solo .rk-me-hd{flex-direction:column;align-items:flex-start;gap:4px;}
.rk-top-solo .rk-me-set{flex-direction:row;flex-wrap:wrap;align-items:center;gap:8px 16px;}
.rk-top-solo .rk-me-set .rk-me-row{flex:0 1 360px;}
.rk-top-solo .rk-me-body{flex-direction:row;flex-wrap:wrap;align-items:center;gap:12px 20px;}
.rk-top-solo .rk-me-rank{font-size:32px;}
.rk-top-solo .rk-me-pick{flex:1 1 220px;}
.rk-top-solo .rk-btn-block{width:auto;}
@media(max-width:720px){.rk-top-solo .rk-me{grid-template-columns:minmax(0,1fr);}}
.rk .sum-box{max-width:none;margin:0;border-radius:12px;border-top:3px solid var(--tour);transition:transform .2s ease-out,box-shadow .2s ease-out;}
.rk .sum-header{padding:18px 22px 12px;}
.rk .sum-title{font-family:'Noto Serif SC',serif;font-size:20px;font-weight:700;letter-spacing:0;text-transform:none;color:var(--ink);margin:0;}
.rk .sum-title::before{content:"TODAY'S PICKS";display:block;font-family:'Space Mono',monospace;font-size:11px;font-weight:700;
    letter-spacing:.2em;color:var(--tour);margin-bottom:4px;}
.rk .sum-title-row{align-items:flex-end;margin-bottom:12px;}
.rk .meta-chip{font-size:12px;padding:3px 10px;}
.rk .sum-col-hd,.rk .sbar-row,.rk .sbar-bak{padding-left:22px;padding-right:22px;}
.rk .sbar-name{font-size:14px;}
.rk .sbar-track{height:10px;}
.rk .sum-toggle{min-height:44px;font-size:13px;color:var(--primary-dark);}
.rk .sum-copy-btn{min-height:40px;min-width:100px;justify-content:center;padding:0 14px;font-family:'Noto Sans SC',sans-serif;
    font-size:12px;font-weight:700;color:var(--ink2);background:var(--surface);overflow:hidden;
    transition:background-color .2s ease-out,border-color .2s ease-out,color .2s ease-out;}
.rk .sum-copy-btn.ok{background:var(--ok);border-color:var(--ok);color:#fff;animation:rkPress .24s ease-out;}
body.dark .rk .sum-copy-btn.ok{color:#06140c;}
.rk .sum-copy-btn.err{background:var(--bad-bg);border-color:var(--bad);color:var(--bad);}
.rk .sum-copy-btn .cp-in{display:inline-flex;align-items:center;gap:6px;}
.rk .sum-copy-btn.ok .cp-in{animation:rkUp .2s ease-out both;}
.rk .sum-copy-btn.err .cp-in{animation:rkShake .3s ease-out both;}
.rk .sum-copy-btn.back .cp-in{animation:rkDown .2s ease-out both;}
.rk .cp-draw{stroke-dasharray:24;animation:rkDraw .28s .08s ease-out both;}
.sum-copy-note{font-size:12px;color:var(--bad);margin-right:8px;}
@keyframes rkPress{0%{transform:scale(1)}40%{transform:scale(.94)}100%{transform:scale(1)}}
@keyframes rkUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@keyframes rkDown{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
@keyframes rkShake{0%{opacity:0}30%{opacity:1;transform:translateX(-3px)}55%{transform:translateX(3px)}80%{transform:translateX(-2px)}100%{opacity:1;transform:none}}
@keyframes rkDraw{from{stroke-dashoffset:24}to{stroke-dashoffset:0}}

/* my status */
.rk-me{border-top:3px solid var(--me);padding:18px 20px;display:flex;flex-direction:column;gap:12px;flex:1;}
.rk-me-hd{display:flex;justify-content:space-between;align-items:baseline;gap:8px;}
.rk-eye-me{color:var(--me);}
.rk-me-name{font-size:13px;font-weight:700;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.rk-me-set{display:flex;flex-direction:column;gap:8px;}
.rk-me-lbl{font-size:13px;color:var(--muted);}
.rk-me-row{display:flex;gap:8px;position:relative;}
/* username suggestions (tsSuggest) */
.rk-sug{top:calc(100% + 6px);left:0;right:0;max-height:min(340px,50vh);overflow-y:auto;}
/* the hover lift (transform) makes a card its own stacking context: tsSuggest puts .rk-sug-open
   on the card (o.host) so the whole card sits above later content while its list is open */
.rk-sug-open{position:relative;z-index:30;}
.rk-sug .rk-opt{justify-content:space-between;}
.rk-sug .rk-opt[aria-selected="true"]{background:var(--row-hover);}
.rk-sug .t{font-family:'Space Mono',monospace;font-size:11px;color:var(--muted);flex-shrink:0;}
.rk-sug .rk-note{padding:6px 10px;}
.rk-me-row .rk-input{flex:1;}
.rk-me-body{display:flex;flex-direction:column;gap:12px;}
.rk-me-body[hidden],.rk-me-set[hidden]{display:none;}
.rk-me-big{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;}
.rk-me-rank{font-family:'Space Mono',monospace;font-size:40px;font-weight:700;line-height:1;color:var(--ink);}
.rk-me-pts{font-family:'Space Mono',monospace;font-size:15px;color:var(--muted);}
.rk-me-d{font-family:'Space Mono',monospace;font-size:13px;font-weight:700;}
.rk-me-pick{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 12px;background:var(--surface2);
    border-radius:10px;font-size:14px;color:var(--ink);}
.rk-me-pick:empty{display:none;}

/* daily killers */
.rk .dk-box{max-width:none;margin:0;border-radius:12px;border-top:3px solid var(--bad);}
.rk .dk-toggle{min-height:48px;justify-content:space-between;background:var(--surface);padding:12px 20px;color:var(--ink);}
.rk .dk-toggle-txt{font-family:'Noto Serif SC',serif;font-size:16px;font-weight:700;}
.rk .dk-toggle-txt::before{content:"KILLERS · DAILY";display:block;font-family:'Space Mono',monospace;font-size:11px;
    font-weight:700;letter-spacing:.2em;color:var(--bad);text-align:left;margin-bottom:2px;}
.rk .dk-arrow{color:var(--primary-dark);}
.rk .dk-hd,.rk .dk-row{grid-template-columns:44px minmax(0,1fr) minmax(0,1fr);padding-left:20px;padding-right:20px;}
.rk .dk-hd{font-size:11px;color:var(--muted);}
.rk .dk-day{font-size:12px;color:var(--muted);}
.rk .dk-k em{font-size:12px;color:var(--bad);}
.rk .dk-k.alt em{color:var(--muted);}
.rk .dk-k.alt b{font-weight:400;}

/* table card toolbars */
.rk-tcard{overflow:visible;}
.rk-share{padding:12px 20px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;background:var(--me-dim);border-bottom:1px solid var(--me-rim);
    border-radius:12px 12px 0 0;font-size:13px;color:var(--ink);}
.rk-share[hidden]{display:none;}
.rk-watch{padding:10px 20px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;background:var(--star-dim);border-bottom:1px solid var(--star-rim);}
.rk-share:not([hidden])+.rk-watch{border-radius:0;}
.rk-share[hidden]+.rk-watch{border-radius:12px 12px 0 0;}
.rk-watch-t{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;color:var(--ink);margin-right:4px;}
.rk-star-ic svg{fill:var(--star);stroke:var(--star);}
.rk-watch-tabs,.rk-watch-new{display:contents;}
.rk-tab,.rk-chip{flex-shrink:0;white-space:nowrap;}
.rk-tab{min-height:32px;padding:0 12px;border-radius:999px;border:1px solid var(--star-rim);background:var(--surface);color:var(--muted);font-size:11px;
    transition:background-color .15s,color .15s;}
.rk-tab[aria-pressed="true"]{background:var(--star);border-color:var(--star);color:#051420;font-weight:700;}
.rk-tab .n{font-family:'Space Mono',monospace;opacity:.75;margin-left:4px;}
.rk-tab-new{border-style:dashed;border-color:var(--border);background:transparent;color:var(--muted);}
.rk-new-form{display:inline-flex;gap:6px;align-items:center;}
.rk-new-form .rk-input{min-height:36px;width:140px;}
.rk-share-btn{margin-left:auto;}
.rk-manage{padding:10px 20px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;border-bottom:1px solid var(--border2);}
.rk-manage[hidden]{display:none;}
.rk-manage .rk-input{min-height:36px;}
.rk-chips{padding:12px 20px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;border-bottom:1px solid var(--border2);}
.rk-chip-row{display:flex;flex-wrap:wrap;gap:8px;}
.rk-chip{min-height:32px;padding:0 12px;border-radius:999px;border:1px solid var(--border);background:var(--surface);color:var(--muted);font-size:11px;
    transition:background-color .15s,color .15s;}
.rk-chip .n{font-family:'Space Mono',monospace;opacity:.8;margin-left:4px;}
.rk-chip[aria-pressed="true"]{background:var(--me);border-color:var(--me);color:#fff;font-weight:700;}
body.dark .rk-chip[aria-pressed="true"]{color:#06142a;}
.rk-route{padding:10px 20px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;background:var(--me-dim);border-bottom:1px solid var(--border2);}
.rk-route-t{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;color:var(--me);}
.rk-route-if{font-size:12px;color:var(--muted);}
.rk-route-sel{display:contents;}
.rk-route-hint{margin-left:auto;font-size:12px;color:var(--muted);}
.rk-dd{position:relative;}
.rk-dd-btn{min-height:40px;min-width:180px;padding:0 12px;border-radius:10px;border:1px solid var(--border);background:var(--drop-bg);color:var(--ink);
    font-size:13px;display:flex;align-items:center;justify-content:space-between;gap:8px;}
.rk-dd-btn.on{border-color:var(--me);}
.rk-chev{display:inline-block;transition:transform .2s;}
.rk-dd-btn[aria-expanded="true"] .rk-chev{transform:rotate(180deg);}
.rk-selchip{display:inline-flex;align-items:center;gap:2px;font-size:13px;font-weight:700;padding:0 2px 0 12px;min-height:36px;border-radius:999px;
    background:var(--me-dim);color:var(--me);border:1px solid var(--me-rim);animation:rkPop .18s ease-out both;}
.rk-selchip button{width:32px;height:32px;border:0;border-radius:50%;background:transparent;color:inherit;display:flex;align-items:center;justify-content:center;}
.rk-route-res{display:inline-flex;align-items:center;gap:6px;font-size:13px;min-height:36px;padding:0 14px;border-radius:999px;background:var(--me);color:#fff;}
body.dark .rk-route-res{color:#06142a;}
.rk-route-res[hidden]{display:none;}

/* popovers */
.rk-pop{position:absolute;z-index:60;background:var(--drop-bg);border:1px solid var(--border);border-radius:12px;
    box-shadow:0 10px 28px rgba(5,20,32,.16);padding:8px;display:flex;flex-direction:column;gap:2px;animation:rkPop .18s ease-out both;}
body.dark .rk-pop{box-shadow:0 10px 28px rgba(0,0,0,.5);}
.rk-pop[hidden]{display:none;}
.rk-dd-pop{top:46px;left:0;width:260px;}
.rk-pop-eye{padding:6px 8px;}
.rk-pop-search{margin:0 4px 4px;}
.rk-opts{max-height:280px;overflow-y:auto;display:flex;flex-direction:column;}
.rk-opt{min-height:40px;padding:0 10px;border:0;border-radius:8px;background:transparent;text-align:left;display:flex;align-items:center;gap:10px;
    color:var(--ink);font-size:14px;}
.rk-opt:hover{background:var(--row-hover);}
.rk-box{width:18px;height:18px;flex-shrink:0;border-radius:5px;border:1.5px solid var(--border);background:var(--surface);position:relative;}
.rk-opt[aria-selected="true"] .rk-box,.rk-opt[aria-pressed="true"] .rk-box{background:var(--me);border-color:var(--me);}
.rk-opt[aria-selected="true"] .rk-box::after,.rk-opt[aria-pressed="true"] .rk-box::after{content:"";position:absolute;left:5px;top:1px;width:5px;height:10px;
    border:solid #fff;border-width:0 2px 2px 0;transform:rotate(45deg);}
.rk-picker .rk-opt[aria-pressed="true"] .rk-box{background:var(--star);border-color:var(--star);}
.rk-opt-l{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.rk-pop-ft{display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--border2);margin-top:4px;padding-top:4px;}
.rk-picker{width:232px;}
.rk-picker .rk-pick-new{display:flex;gap:6px;padding:4px;}
.rk-picker .rk-pick-new .rk-input{flex:1;min-height:36px;}
.rk-pick-act{min-height:40px;padding:0 10px;border:0;border-radius:8px;background:transparent;text-align:left;color:var(--primary-dark);font-size:13px;}
.rk-pick-act:hover{background:var(--row-hover);}
.rk-pick-me{color:var(--me);font-weight:700;}
@keyframes rkPop{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}

/* table */
.rk .table-wrapper{border:0;border-radius:0;max-height:calc(100vh - 96px);overflow:auto;overscroll-behavior:contain;}
.rk .filterable-table{font-size:14px;}
.rk .filterable-table thead tr:first-child th{font-family:'Noto Sans SC',sans-serif;font-size:12px;font-weight:700;letter-spacing:0;
    text-transform:none;color:#fff;padding:12px 10px;}
.rk .filterable-table td{font-size:14px;padding:9px 10px;white-space:nowrap;}
.rk .filterable-table td:nth-child(3),.rk .filterable-table td:nth-child(4){font-family:inherit;font-weight:inherit;color:inherit;font-size:14px;}
.rk .filterable-table td:first-child{font-family:'Space Mono',monospace;font-weight:700;color:var(--ink);font-size:14px;}
.rk .filter-trigger{min-height:36px;font-size:12px;color:var(--muted);border-radius:8px;padding:0 8px;gap:4px;font-family:'Noto Sans SC',sans-serif;
    letter-spacing:0;background:var(--surface);border:1px solid var(--border);transition:border-color .15s,color .15s;}
.rk .filter-trigger>span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;}
.rk .filter-trigger .rk-chev{flex-shrink:0;font-size:11px;opacity:.7;}
.rk .filter-trigger.on{border-color:var(--me);color:var(--me);font-weight:700;background:var(--me-dim);}
.rk .filter-trigger[aria-expanded="true"]{border-color:var(--me);}
.rk .filter-trigger[aria-expanded="true"] .rk-chev{transform:rotate(180deg);}
.rk .filter-trigger:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
.rk .filterable-table .filter-row th{padding:6px 6px;}

/* column filter popovers (built by _JS_TABLE, moved to <body>: tokens defined here) */
.dropdown-content.rk-fpop{--me:#1c3f94;--me-dim:rgba(28,63,148,.07);border-radius:12px;padding:8px;min-width:220px;max-height:min(360px,60vh);
    box-shadow:0 10px 28px rgba(5,20,32,.16);flex-direction:column;gap:2px;overflow:hidden;}
body.dark .dropdown-content.rk-fpop{--me:#8fb0ff;--me-dim:rgba(143,176,255,.10);box-shadow:0 10px 28px rgba(0,0,0,.5);}
.dropdown-content.rk-fpop.show{display:flex;animation:rkPop .18s ease-out both;}
.rk-fpop .rk-pop-eye{padding:6px 8px;flex-shrink:0;}
.rk-fpop .rk-fopts{overflow-y:auto;display:flex;flex-direction:column;gap:2px;min-height:0;}
.rk-fpop .dropdown-search{font:inherit;font-size:14px;min-height:40px;border:1px solid var(--border);border-radius:10px;padding:0 12px;
    margin:0 0 4px;background:var(--drop-bg);color:var(--ink);flex-shrink:0;width:100%;box-sizing:border-box;}
.rk-fpop .dropdown-search:focus{border-color:var(--me);outline:0;}
.rk-fpop .option-item{min-height:40px;padding:0 10px;border:0 !important;border-radius:8px;gap:10px;font-size:14px;color:var(--ink);cursor:pointer;}
.rk-fpop .option-item:hover{background:var(--row-hover);}
.rk-fpop .option-item>span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.rk-fpop .option-item .n{flex:0 0 auto;font-family:'Space Mono',monospace;font-size:12px;color:var(--muted);font-style:normal;}
.rk-fpop .select-all-item{font-weight:700;border-bottom:1px solid var(--border2) !important;border-radius:8px 8px 0 0;flex-shrink:0;}
.rk-fpop .option-item input[type=checkbox]{-webkit-appearance:none;appearance:none;width:18px;height:18px;flex-shrink:0;margin:0;border-radius:5px;
    border:1.5px solid var(--border);background:var(--surface) center/12px no-repeat;cursor:pointer;}
.rk-fpop .option-item input[type=checkbox]:checked{background-color:var(--me);border-color:var(--me);
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3'%3E%3Cpath d='M5 12l5 5 9-10'/%3E%3C/svg%3E");}
.rk-fpop .option-item input[type=checkbox]:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
.rk-fpop .rk-pop-ft{flex-shrink:0;}
.rk-fpop .rk-btn-text{min-height:40px;font-size:13px;}
.rk-fpop .rk-btn{min-height:40px;font-size:13px;}
.rk-fpop.filter-slider{padding:8px;}
.rk-fpop .filter-slider-readout{margin:4px 8px 10px;gap:8px;font-size:12px;}
.rk-fpop .filter-slider-readout input[type=number]{width:auto;flex:1;min-width:0;min-height:40px;border-radius:8px;font-family:'Space Mono',monospace;font-size:14px;}
.rk-fpop .filter-slider-readout input[type=number]:focus{border-color:var(--me);}
.rk-fpop .filter-slider-range{margin:0 8px 6px;}
.rk-fpop .filter-slider-fill{background:var(--me);}
.rk-fpop .filter-slider-range input[type=range]::-webkit-slider-thumb{background:var(--me);width:18px;height:18px;}
.rk-fpop .filter-slider-range input[type=range]::-moz-range-thumb{background:var(--me);width:18px;height:18px;}
.rk-fpop .filter-slider-reset{display:none;}
@media(prefers-reduced-motion:reduce){.dropdown-content.rk-fpop.show{animation:none;}.rk .filter-trigger{transition:none;}}
.rk .filterable-table tr:nth-child(even) td{background:transparent;}
.rk .filterable-table tr:hover td,.rk .filterable-table tr:nth-child(even):hover td{background:var(--row-hover);}
.rk .filterable-table .rk-frz{position:sticky;z-index:2;background:var(--surface);}
.rk .filterable-table thead .rk-frz{z-index:22;}
.rk .filterable-table thead tr:first-child .rk-frz{background:var(--th-bg);}
.rk .filterable-table .filter-row .rk-frz{background:var(--filter-bg);}
/* frozen cells must stay opaque on every row (beats the even-row / hover / "me" tints) */
.rk .filterable-table tbody tr td.rk-frz{background:var(--surface);}
.rk .filterable-table tbody tr:hover td.rk-frz{background:linear-gradient(var(--row-hover),var(--row-hover)) var(--surface);}
.rk .filterable-table tbody tr.rk-mine td.rk-frz{background:linear-gradient(var(--me-dim),var(--me-dim)) var(--surface);}
.rk .filterable-table .rk-frz-last{box-shadow:6px 0 8px -6px rgba(5,20,32,.18);}
.rk .rank{font-family:'Space Mono',monospace;font-size:13px;font-weight:700;display:inline-block;}
.rk .rank.up{color:var(--ok);}.rk .rank.down{color:var(--bad);}.rk .rank.same{color:var(--muted);}
.rk .rank::before{content:none;}
.rank-a::after{content:attr(data-a);margin-left:6px;font-size:12px;}
.rk .filterable-table tbody tr.rk-final td,.rk .filterable-table tbody tr.rk-final td.rk-frz{background:linear-gradient(var(--fin-dim),var(--fin-dim)) var(--surface);}
.rk .filterable-table tbody tr.rk-final:hover td,.rk .filterable-table tbody tr.rk-final:hover td.rk-frz{background:linear-gradient(var(--fin-dim),var(--fin-dim)) var(--surface2);}
.rk tr.rk-final td:first-child{box-shadow:inset 3px 0 0 var(--fin);}
.rk tr.rk-final-last td{border-bottom:1px dashed var(--fin-rim);}
.rk-finals-note{display:flex;align-items:center;gap:8px;padding:8px 20px;font-size:12px;color:var(--ink2);border-bottom:1px solid var(--border2);}
.rk-finals-note[hidden]{display:none;}
.rk-f{width:14px;height:14px;border-radius:4px;background:var(--fin-dim);box-shadow:inset 3px 0 0 var(--fin);flex-shrink:0;}
.rk-card-row.rk-final{box-shadow:inset 3px 0 0 var(--fin);background-image:linear-gradient(var(--fin-dim),var(--fin-dim));}
.rk-c-cur{font-family:'Space Mono',monospace;font-size:12px;color:var(--muted);}
.rk-c-cur b{color:var(--ink);}

/* help button + dialogs */
.rk-help-btn{width:36px;height:36px;border-radius:50%;border:1px solid var(--border);background:var(--surface);color:var(--me,#1c3f94);
    display:inline-flex;align-items:center;justify-content:center;cursor:pointer;transition:transform .15s ease-out;}
.rk-help-btn:hover{transform:scale(1.06);}
.rk-help-btn:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
body.dark .rk-help-btn{color:#8fb0ff;}
/* quiet title notes: theme-tinted, small */
.rk-tnote{display:inline-flex;align-items:center;gap:4px;font-family:'Noto Sans SC',sans-serif;font-weight:400;font-size:12px;line-height:1;
    color:var(--muted);letter-spacing:0;}
.rk-tnote-ic{display:inline-flex;color:var(--muted);}
.rk-tnote-ic svg{width:14px;height:14px;}
/* own row under the title, left-aligned with it (.page-title wraps) */
.rk-tline{flex-basis:100%;display:flex;margin-top:-2px;}
.rk-tnote-exp{padding:6px 10px;border-radius:999px;background:var(--primary-dim);border:1px solid var(--primary-rim);color:var(--primary-dark);}
@media(max-width:720px){.rk-tnote:not(.rk-tnote-exp){flex-basis:100%;}}
.rk-modal{position:fixed;inset:0;z-index:9000;background:rgba(5,20,32,.45);display:flex;align-items:center;justify-content:center;padding:20px;
    animation:rkFade .2s ease-out both;}
.rk-modal[hidden]{display:none;}
.rk-dlg{width:min(600px,100%);max-height:min(88vh,860px);background:var(--surface);border-radius:14px;box-shadow:0 18px 50px rgba(5,20,32,.25);
    display:flex;flex-direction:column;overflow:hidden;animation:rkRise .26s cubic-bezier(.22,.68,0,1.2) both;outline:0;}
.rk-dlg-hist{border-top:3px solid var(--tour);}
.rk-dlg-help{border-top:3px solid var(--me);width:min(560px,100%);}
.rk-ask{width:min(420px,100%);border-top:3px solid var(--bad);}
.rk-ask h2{white-space:normal;font-size:18px;}
.rk-ask-d{margin:0;padding:0 20px 16px;font-size:14px;line-height:1.6;color:var(--muted);}
.rk-ask-ok{background:var(--bad);border-color:var(--bad);color:#fff;font-weight:700;}
.rk-ask-ok:hover{color:#fff;border-color:var(--bad);filter:brightness(1.08);}
body.dark .rk-ask-ok{color:#1a0904;}
.rk-dlg-hd{display:flex;justify-content:space-between;gap:12px;padding:18px 20px 12px;}
.rk-dlg-ttl{display:flex;flex-direction:column;gap:4px;min-width:0;}
.rk-dlg-ttl h2{margin:0;font-family:'Noto Serif SC',serif;font-size:22px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.rk-eye-tour{color:var(--tour);}
.rk-dlg-act{display:flex;align-items:flex-start;gap:10px;flex-shrink:0;}
.rk-hist-seg{display:flex;gap:3px;padding:3px;background:var(--surface2);border:1px solid var(--border);border-radius:999px;}
.rk-hist-seg button{min-height:36px;padding:0 14px;border:0;border-radius:999px;background:transparent;color:var(--muted);font-size:13px;font-weight:700;
    transition:background-color .18s,color .18s;}
.rk-hist-seg button[aria-pressed="true"]{background:#1c3f94;color:#fff;}
.rk-hist-seg button:disabled{opacity:.45;cursor:not-allowed;}
.rk-x{flex-shrink:0;width:44px;height:44px;border-radius:50%;border:1px solid var(--border);background:var(--surface);color:var(--ink);
    display:flex;align-items:center;justify-content:center;}
.rk-hist-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;padding:0 20px 14px;}
.rk-hist-stats>span{background:var(--surface2);border-radius:10px;padding:8px 10px;display:flex;flex-direction:column;gap:2px;font-size:11px;color:var(--muted);min-width:0;}
.rk-hist-stats b{font-family:'Space Mono',monospace;font-size:18px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.rk-hist-stats .st-badge{align-self:flex-start;margin-top:3px;}
.rk-hist-head,.rk-hist-row{display:grid;grid-template-columns:64px minmax(0,1fr) 110px;gap:10px;padding:8px 20px;align-items:center;}
.rk-hist-head{font-size:12px;font-weight:700;color:var(--muted);background:var(--surface2);border-top:1px solid var(--border2);}
.rk-hist-list{overflow-y:auto;}
.rk-hist-row{font-size:14px;border-top:1px solid var(--border2);color:var(--ink);animation:rkRow .24s ease-out both;}
.rk-hist-row.today{background:var(--star-dim);}
.rk-hist-row b{font-family:'Space Mono',monospace;font-size:13px;}
.rk-hist-row .p{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:700;}
.rk-hist-row .p.none{color:var(--muted);font-weight:400;}
.rk-hist-row .a{margin-left:8px;font-size:12px;font-weight:400;color:var(--muted);}
.rk-hist-ft{padding:12px 20px 16px;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:8px;}
.rk-dlg-ft{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:12px 20px;border-top:1px solid var(--border);}
.rk-dlg-nav{display:flex;gap:8px;}
.rk-dlg-nav .rk-btn[disabled]{opacity:.4;cursor:default;}
.hp-bars{display:flex;gap:6px;padding:0 20px 14px;}
.hp-bar{flex:1;height:4px;border-radius:2px;background:var(--surface2);overflow:hidden;}
.hp-bar i{display:block;height:100%;background:var(--me);transform-origin:left;transform:scaleX(0);}
.hp-bar.done i{transform:none;}
.hp-bar.now i{animation:hpFill 5s linear both;}
.hp-bar.now.paused i{animation-play-state:paused;}
.hp-body{padding:0 20px 18px;}
.hp-step{display:flex;flex-direction:column;gap:12px;animation:hpIn .3s ease-out both;}
.hp-step[hidden]{display:none;}
.hp-step h3{margin:4px 0 0;font-family:'Noto Serif SC',serif;font-size:18px;color:var(--ink);}
.hp-step p{margin:0;font-size:15px;line-height:1.7;color:var(--ink2);}
.hp-stage{position:relative;height:220px;border-radius:12px;background:var(--surface2);border:1px solid var(--border2);overflow:hidden;padding:16px;
    display:flex;flex-direction:column;gap:12px;font-size:13px;color:var(--ink);}
.hp-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}
.hp-chip{position:relative;display:inline-flex;align-items:center;min-height:32px;padding:0 12px;border-radius:999px;border:1px solid var(--border);background:var(--surface);}
.hp-chip.on{background:var(--me);border-color:var(--me);color:#fff;font-weight:700;}
.hp-chip.gold{background:var(--star);border-color:var(--star);color:#051420;font-weight:700;}
.hp-ping{position:absolute;inset:-4px;border-radius:999px;border:2px solid var(--me);animation:hpPing 1.4s ease-out infinite;}
.hp-lines{display:flex;flex-direction:column;gap:6px;}
.hp-lines i{height:26px;border-radius:8px;background:var(--surface);}
.hp-lines i:last-child{opacity:.5;}
.hp-foot{position:absolute;left:16px;bottom:14px;font-size:12px;color:var(--muted);}
.hp-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;}
.hp-grid b{font-size:12px;padding:7px 8px;border-radius:8px;background:var(--th-bg);color:#fff;}
.hp-grid span{font-size:12px;padding:6px 8px;border-radius:8px;background:var(--surface);border:1px solid var(--border);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.hp-grid span.on{border-color:var(--me);color:var(--me);font-weight:700;}
.hp-menu{position:absolute;left:calc(50% + 4px);top:96px;width:150px;background:var(--drop-bg);border:1px solid var(--border);border-radius:10px;
    box-shadow:0 8px 20px rgba(5,20,32,.12);padding:8px;display:flex;flex-direction:column;gap:6px;animation:hpMenu 2.4s ease-in-out infinite;}
.hp-menu-l{left:40px;top:120px;}
.hp-ck::before{content:"";display:inline-block;width:12px;height:12px;border-radius:3px;border:1.5px solid var(--border);margin-right:8px;vertical-align:-1px;}
.hp-ck.on::before{background:var(--me);border-color:var(--me);}
.hp-cur{position:absolute;left:40px;top:120px;width:18px;height:18px;fill:var(--ink);animation:hpCur 2.4s ease-in-out infinite;}
.hp-blue{color:var(--me);font-weight:700;}
.hp-gold{color:var(--star);}
.hp-dd{min-height:32px;padding:0 12px;border-radius:10px;border:1px solid var(--me);background:var(--surface);display:inline-flex;align-items:center;}
.hp-sel{min-height:30px;padding:0 12px;border-radius:999px;background:var(--me-dim);color:var(--me);font-weight:700;display:inline-flex;align-items:center;}
.hp-list{display:flex;flex-direction:column;gap:6px;}
.hp-list span{display:flex;justify-content:space-between;gap:8px;padding:7px 12px;border-radius:8px;background:var(--surface);}
.hp-list em{font-style:normal;color:var(--ok);font-family:'Space Mono',monospace;}
.hp-list em.up{color:var(--ok);}.hp-list em.down{color:var(--bad);}
.hp-list .gone{opacity:.4;text-decoration:line-through;animation:hpGone 2.4s ease-in-out infinite;}
.hp-list .me{background:var(--me-dim);box-shadow:inset 3px 0 0 var(--me);}
.hp-me{font-size:11px;font-weight:700;padding:1px 7px;border-radius:999px;background:var(--me);color:#fff !important;}
.hp-tag{color:var(--star) !important;font-family:inherit !important;font-size:11px;}
.hp-bump{background:rgba(196,152,0,.18) !important;animation:hpBump 1.2s cubic-bezier(.22,.68,0,1) infinite alternate;position:relative;z-index:1;}
.hp-seg{display:inline-flex;gap:2px;padding:2px;border-radius:999px;background:var(--surface);border:1px solid var(--border);}
.hp-seg i{font-style:normal;font-size:11px;padding:3px 10px;border-radius:999px;color:var(--muted);}
.hp-seg i.on{background:#1c3f94;color:#fff;font-weight:700;}
.hp-bd{display:grid;grid-template-columns:minmax(0,1fr) 110px;gap:14px;align-items:center;}
.hp-bd-list{display:flex;flex-direction:column;gap:6px;}
.hp-bd-list span{display:flex;justify-content:space-between;padding:6px 10px;border-radius:8px;background:var(--surface);font-size:12px;}
.hp-bd-list b{font-family:'Space Mono',monospace;}
.hp-bd-list .s-hard{box-shadow:inset 3px 0 0 #0088bb;}.hp-bd-list .s-clay{box-shadow:inset 3px 0 0 #d0573a;}.hp-bd-list .s-grass{box-shadow:inset 3px 0 0 #1b5e37;}
.hp-donut{width:110px;height:110px;border-radius:50%;display:flex;align-items:center;justify-content:center;
    background:conic-gradient(#0088bb 0 65%,#d0573a 0 88%,#1b5e37 0 100%);animation:hpSpin 2.4s cubic-bezier(.22,.68,0,1) infinite alternate;}
.hp-donut b{width:70px;height:70px;border-radius:50%;background:var(--surface2);display:flex;align-items:center;justify-content:center;
    font-family:'Space Mono',monospace;font-size:14px;color:var(--ink);}
@keyframes hpSpin{from{transform:rotate(-90deg) scale(.85);opacity:.4}to{transform:none;opacity:1}}
.hp-bars-demo{display:flex;flex-direction:column;gap:8px;}
.hp-bars-demo i{display:block;height:12px;border-radius:6px;background:var(--primary);transform-origin:left;animation:hpGrow 1.6s ease-out infinite alternate;}
.hp-bars-demo i:nth-child(2){background:var(--secondary);}
.hp-bars-demo i:nth-child(3){opacity:.5;}
@keyframes hpGrow{from{transform:scaleX(.2)}to{transform:none}}
.hp-ok{min-height:32px;padding:0 14px;border-radius:999px;background:var(--ok);color:#fff;font-weight:700;display:inline-flex;align-items:center;}
@keyframes rkFade{from{opacity:0}to{opacity:1}}
@keyframes rkRise{from{opacity:0;transform:translateY(10px) scale(.98)}to{opacity:1;transform:none}}
@keyframes rkRow{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}
@keyframes hpIn{from{opacity:0;transform:translateX(24px)}to{opacity:1;transform:none}}
@keyframes hpFill{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes hpPing{0%{transform:scale(.9);opacity:.9}100%{transform:scale(1.25);opacity:0}}
@keyframes hpCur{0%{transform:translate(0,0)}40%,100%{transform:translate(210px,-26px)}}
@keyframes hpMenu{0%,40%{opacity:0;transform:translateY(-4px)}55%,100%{opacity:1;transform:none}}
@keyframes hpGone{0%,30%{opacity:1;text-decoration:none}60%,100%{opacity:.4}}
@keyframes hpBump{from{transform:translateY(40px)}to{transform:none}}
.rk-user{display:flex;align-items:center;gap:6px;min-width:0;}
.rk-star{width:36px;height:36px;margin:-6px 0 -6px -6px;border:0;border-radius:50%;background:transparent;display:inline-flex;align-items:center;
    justify-content:center;flex-shrink:0;}
.rk-star svg{fill:none;stroke:var(--star);}
.rk-star.on svg{fill:var(--star);}
.rk-star:hover{background:var(--star-dim);}
.rk-uname{text-decoration:underline;text-decoration-color:var(--primary-rim);text-underline-offset:3px;}
.rk-mebadge{font-size:11px;font-weight:700;padding:1px 7px;border-radius:999px;background:var(--me);color:#fff;}
body.dark .rk-mebadge{color:#06142a;}
.rk-tags{font-size:11px;color:var(--star);white-space:nowrap;}
.rk-tags::after{content:attr(data-t);}
.rk-uname[data-me]::after{content:"我";display:inline-block;margin-left:6px;font-size:11px;font-weight:700;padding:1px 7px;border-radius:999px;
    background:var(--me);color:#fff;text-decoration:none;}
body.dark .rk-uname[data-me]::after{color:#06142a;}
body:not(.dark) .rk-tags{color:#8a6a00;}
.rk .filterable-table tr.rk-mine td{background:var(--me-dim);}
.rk .filterable-table tr.rk-mine td:first-child{box-shadow:inset 3px 0 0 var(--me);}
.rk-empty{padding:32px;text-align:center;font-size:13px;color:var(--muted);}
.rk-empty[hidden]{display:none;}
.rk-foot{padding:12px 20px;display:flex;gap:12px;align-items:center;justify-content:space-between;border-top:1px solid var(--border2);font-size:13px;color:var(--muted);}
.rk-count{margin-left:auto;}
.rk-count b{font-family:'Space Mono',monospace;color:var(--ink);}
.rk-foot #rkMore{color:var(--primary-dark);}
.rk-foot #rkMore[hidden]{display:none;}

/* rank-change motion (load + replay); transform/opacity only */
@keyframes rkMv{from{transform:translateY(var(--dy,0))}to{transform:none}}
@keyframes rkMv2{from{transform:translateY(var(--dy,0))}to{transform:none}}
@keyframes rkFlash{from{box-shadow:inset 0 0 0 999px var(--primary-rim)}to{box-shadow:inset 0 0 0 999px transparent}}
@keyframes rkDp{0%{opacity:0;transform:translateY(var(--dd,0)) scale(.7)}60%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:none}}
@keyframes rkDp2{0%{opacity:0;transform:translateY(var(--dd,0)) scale(.7)}60%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:none}}
.rk tr.rk-mv0,.rk .rk-card-row.rk-mv0{animation:rkMv 1.3s cubic-bezier(.22,.68,0,1) both;position:relative;z-index:1;}
.rk tr.rk-mv1,.rk .rk-card-row.rk-mv1{animation:rkMv2 1.3s cubic-bezier(.22,.68,0,1) both;position:relative;z-index:1;}
.rk tr.rk-mv0 td,.rk tr.rk-mv1 td{animation:rkFlash 2.4s ease-out;}
.rk .rk-dp0{animation:rkDp .6s 1.1s ease-out both;}
.rk .rk-dp1{animation:rkDp2 .6s 1.1s ease-out both;}

/* mobile cards */
.rk-cards{display:none;flex-direction:column;gap:8px;padding:12px;}
.rk-card-row{background:var(--surface);border:1px solid var(--border);border-radius:12px;}
.rk-card-row.rk-mine{background:var(--me-dim);border-color:var(--me-rim);}
.rk-card-main{display:flex;align-items:stretch;}
.rk-card-btn{flex:1;min-width:0;font:inherit;color:inherit;border:0;background:transparent;padding:12px 4px 12px 14px;display:grid;
    grid-template-columns:30px minmax(0,1fr) auto;gap:10px;align-items:center;text-align:left;min-height:60px;}
.rk-c-rank{font-family:'Space Mono',monospace;font-size:15px;font-weight:700;display:flex;flex-direction:column;gap:2px;}
.rk-c-rank .rank{font-size:11px;}
.rk-c-mid{display:flex;flex-direction:column;gap:4px;min-width:0;}
.rk-c-name{display:flex;gap:6px;align-items:center;min-width:0;font-weight:700;font-size:15px;}
.rk-c-name .t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.rk-c-sub{display:flex;gap:6px;align-items:center;min-width:0;font-size:12px;color:var(--muted);}
.rk-c-sub .p{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.rk-c-sub .p b{color:var(--ink);font-weight:500;}
.rk-c-right{display:flex;flex-direction:column;align-items:flex-end;gap:4px;}
.rk-c-pts{font-family:'Space Mono',monospace;font-size:15px;font-weight:700;}
.rk-card-row .rk-star{margin:0 8px 0 0;align-self:center;width:44px;height:44px;}
.rk-c-more{margin:0 14px;padding:12px 0 14px 40px;border-top:1px solid var(--border2);display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
    gap:10px 12px;font-size:12px;color:var(--muted);animation:rkPop .18s ease-out both;}
.rk-c-more[hidden]{display:none;}
.rk-c-more span{display:flex;flex-direction:column;gap:2px;min-width:0;}
.rk-c-more b{font-size:14px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.rk-c-more .rk-btn{grid-column:1/-1;min-height:44px;}

@media(hover:hover){.rk .sum-box:hover,.rk-me:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(5,20,32,.08);}}
@media(max-width:1000px){.rk-top{grid-template-columns:minmax(0,1fr);}}
@media(max-width:720px){
    .rk{gap:14px;}
    .rk-eye{font-size:13px;letter-spacing:.14em;}
    .rk .sum-title::before,.rk .dk-toggle-txt::before{font-size:13px;letter-spacing:.14em;}
    .rk .sum-header{padding:14px 16px 10px;}
    .rk .sum-col-hd,.rk .sbar-row,.rk .sbar-bak{padding-left:16px;padding-right:16px;}
    .rk-me{padding:12px 14px;gap:8px;}
    .rk-me-set{gap:6px;}
    .rk-me-lbl,.rk-me-set .rk-note{display:none;}
    .rk-me-body{display:grid;grid-template-columns:auto minmax(0,1fr);align-items:center;gap:8px 12px;}
    .rk-me-body[hidden]{display:none;}
    .rk-me-big{gap:8px;}
    .rk-me-rank{font-size:26px;}
    .rk-me-pick{grid-column:1/-1;padding:8px 10px;font-size:13px;}
    .rk-me-big{grid-column:1/2;grid-row:1;}
    .rk-me-body .rk-btn-block{grid-column:2/3;grid-row:1;justify-self:end;width:auto;min-height:40px;padding:0 12px;font-size:12px;}
    .rk-me-body .rk-btn-text{grid-column:1/-1;justify-self:start;min-height:32px;padding:0;}
    .rk-watch,.rk-chips,.rk-route,.rk-manage,.rk-share{padding:10px 12px;}
    .rk-watch,.rk-chip-row{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;}
    .rk-watch>*,.rk-chip-row>*{flex-shrink:0;}
    .rk-chip-row{width:100%;}
    .rk-share-btn{margin-left:0;}
    .rk-route-hint{margin-left:0;flex-basis:100%;}
    .rk-dd-pop{width:min(280px,calc(100vw - 48px));}
    .rk .table-wrapper{display:none;}
    .rk-cards{display:flex;}
    .rk-foot{flex-wrap:wrap;padding:12px;}
    .rk-count{margin-left:0;}
}
@media(max-width:720px){
    .rk-modal{align-items:flex-end;padding:0;}
    .rk-dlg{width:100%;max-height:92vh;border-radius:16px 16px 0 0;}
    .rk-hist-stats{grid-template-columns:repeat(2,minmax(0,1fr));}
    .rk-hist-head,.rk-hist-row{grid-template-columns:52px minmax(0,1fr) 96px;padding-left:16px;padding-right:16px;}
    .hp-stage{height:200px;}
    .rk-dlg-ft{flex-wrap:wrap;}
}
@media(prefers-reduced-motion:reduce){
    .rk *,.rk-pop,.rk-modal,.rk-modal *{animation:none !important;transition:none !important;}
    .hp-bar.now i{transform:none;}
}"""


# Shared by the ranking and watch pages: status groups + 选人历史 day alignment.
JS_HIST = r"""
function tsGrp(s){ if(s==='存活')return 'alive'; if(s==='未完赛')return 'live'; if(s==='轮空')return 'bye'; if(s==='未选')return 'none';
  if(s==='未参赛'||s==='')return 'absent'; if(s.indexOf('自杀')===0)return 'suicide'; if(s==='球员输球')return 'out'; return 'other'; }
function tsEsc(s){ return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
// same classes as _status_badge_html
function tsBadge(s){ s=String(s||'').trim(); if(!s) return '';
  const c=(s==='存活'||s==='轮空')?'st-alive':(s==='未完赛'||s==='未选')?'st-live':(s==='球员输球'||s==='未参赛'||s.indexOf('自杀')===0)?'st-out':'st-other';
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
"""

JS_RANK = JS_HIST + r"""
(function(){
function ready(fn){ if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',fn); else fn(); }
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
  const rows=[...table.tBodies[0].rows];
  const txt=(r,i)=>(i<0||!r.cells[i])?'':r.cells[i].textContent.trim();
  const uname=r=>txt(r,C.user);
  const byUser=new Map(rows.map(r=>[uname(r),r]));
  // the rank change rides inside 当前排名 (or the rank column): find whichever cell holds it
  C.d=rows.length?[...rows[0].cells].findIndex(c=>c.querySelector('.rank')):-1;
  const delta=r=>{ const s=r.cells[C.d]&&r.cells[C.d].querySelector('.rank'); return s?(parseInt(s.dataset.d||'0',10)||0):0; };

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
  const TODAY=rows.map((r,i)=>r.dataset.picked!==undefined?r.dataset.picked==='1'
    :['alive','live','bye'].includes(G[i])||(G[i]==='out'&&DAYS[i]===TODAY_D&&used(r).length>TODAY_D));
  const inChip=(k,i)=>{ const g=G[i]; return k==='all'||(k==='entered'?ENTERED.includes(g):k==='picked'?TODAY[i]:k==='nobye'?TODAY[i]&&g!=='bye'
    :k==='outall'?(g==='out'||g==='suicide'):g===k); };
  let chip=C.st>=0?'picked':'all', list='', routes=new Set(), limit=PAGE;
  const rowIdx=new Map(rows.map((r,i)=>[r,i]));

  // ── route query (夺冠路线) ──
  const ROUTE_OK=['存活','未完赛','未选','轮空'];
  function used(r){ try{ const d=JSON.parse(r.dataset.detail||'[]'); return Array.isArray(d)?d.map(String):[]; }catch(e){ return []; } }
  function routeOk(r){ if(!routes.size) return true; if(!ROUTE_OK.includes(txt(r,C.st))) return false;
    const u=used(r); for(const p of routes) if(u.includes(p)) return false; return true; }

  const allFav=()=>new Set(S.lists.flatMap(l=>l.users));
  function listOk(u){ if(!list) return true; if(list==='*') return allFav().has(u); const l=S.lists.find(x=>x.id===list); return !!l&&l.users.includes(u); }
  TS.extra.push(function(r){ const i=rowIdx.get(r), u=uname(r);
    return (list?true:inChip(chip,i)) && listOk(u) && routeOk(r); });

  // ── pagination + counts after every filter pass ──
  // _JS_TABLE hands over the matching rows in sort order; only the first `limit` go into tbody
  let matched=[];
  const tbody=table.tBodies[0];
  TS.render=list=>{ matched=list; paginate(); };
  function paginate(){
    const show=matched.slice(0,limit), frag=document.createDocumentFragment();
    show.forEach(r=>{ frzApply(r); frag.appendChild(r); });
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
  if(C.user>=0) rows.forEach(r=>{ const td=r.cells[C.user], u=td.textContent.trim();
    td.innerHTML='<span class="rk-user"><button type="button" class="rk-star" aria-label="关注 '+esc(u)+'" aria-haspopup="dialog" aria-expanded="false" data-u="'+esc(u)+'">'+STAR+'</button><span class="rk-uname">'+esc(u)+'</span><span class="rk-tags" data-t=""></span></span>'; });
  function tagsOf(u){ return S.lists.filter(l=>l.users.includes(u)).map(l=>l.name); }
  function paintRow(r){ const u=uname(r), t=tagsOf(u), td=r.cells[C.user]; if(!td) return;
    td.querySelector('.rk-star').classList.toggle('on',t.length>0);
    td.querySelector('.rk-tags').dataset.t=t.map(x=>'★'+x).join(' ');
    td.querySelector('.rk-uname').toggleAttribute('data-me',u===S.me);
    r.classList.toggle('rk-mine',u===S.me); }
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
    const st=C.st>=0&&r.cells[C.st]?r.cells[C.st].innerHTML:'';
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
    const target=mqMobile.matches?root.querySelector('.rk-card-row[data-u="'+CSS.escape(u)+'"]'):r;
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
      const st=C.st>=0&&r.cells[C.st]?r.cells[C.st].innerHTML:'';
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
        +'<div class="rk-c-more"'+(open?'':' hidden')+'>'+extra+(r.dataset.detail!==undefined?'<button type="button" class="rk-btn" data-hist="1">选人历史</button>':'')
        +(r.dataset.uid!==undefined?'<button type="button" class="rk-btn" data-bd-uid="'+esc(r.dataset.uid)+'">积分构成</button>':'')+'</div></div>';
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
  mqMobile.addEventListener('change',()=>{ renderCards(); freeze(); });

  // ── rank-change motion: slide from old position, flash, count up 即时积分 ──
  let run=0;
  function play(){
    if(C.d<0) return; run++;
    const k=run%2, mobile=mqMobile.matches;
    const view=mobile?[...cardsBox.children]:matched.slice(0,limit);
    const sample=view[0]; if(!sample) return;
    const h=sample.getBoundingClientRect().height+(mobile?8:0);
    view.forEach(el=>{
      const r=mobile?byUser.get(el.dataset.u):el; if(!r) return;
      const d=delta(r); el.classList.remove('rk-mv0','rk-mv1');
      const dp=(mobile?el:r.cells[C.d]).querySelector('.rank'); if(dp) dp.classList.remove('rk-dp0','rk-dp1');
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
    const cell=mobile?el.querySelector('.rk-c-pts'):r.cells[C.pts]; if(!cell) return;
    const v=r.cells[C.pts].dataset.v||txt(r,C.pts), to=parseFloat(v), gain=parseFloat(txt(r,C.gain))||0; if(isNaN(to)||!gain) return;
    const from=to-gain, t0=performance.now();
    (function step(now){ const p=Math.min(1,(now-t0)/1600), e=1-Math.pow(1-p,3);
      cell.textContent=String(Math.round(from+(to-from)*e)); if(p<1) requestAnimationFrame(step); else cell.textContent=v; })(t0);
  }
  // counting writes textContent: keep the true value for filters/sort
  if(C.pts>=0&&C.gain>=0) rows.forEach(r=>{ const c=r.cells[C.pts]; if(c) c.dataset.v=c.textContent.trim(); });
  document.getElementById('rkReplay').addEventListener('click',play);
  if(C.d<0) document.getElementById('rkReplay').hidden=true;

  // ── 年终总决赛 top-N (race pages) ──
  const finalsN=parseInt(root.dataset.finals||'0',10)||0;
  const finalsSet=new Set();
  if(finalsN&&C.rank>=0){
    rows.forEach(r=>{ const k=parseInt(txt(r,C.rank),10); if(k>0&&k<=finalsN){ finalsSet.add(r); r.classList.add('rk-final'); if(k===finalsN) r.classList.add('rk-final-last'); } });
    if(finalsSet.size){ document.getElementById('rkFinals').hidden=false; document.getElementById('rkFinalsN').textContent=finalsN; }
  }

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
    if(!hist||r.dataset.detail===undefined) return;
    let picks=[]; try{ picks=JSON.parse(r.dataset.detail||'[]'); }catch(e){}
    if(!Array.isArray(picks)) picks=[];
    const u=uname(r), stCell=C.st>=0&&r.cells[C.st]?r.cells[C.st].innerHTML:'';
    document.getElementById('rkHistName').textContent=u;
    const stat=(k,v)=>'<span>'+k+'<b>'+v+'</b></span>';
    document.getElementById('rkHistStats').innerHTML=stat(ths[C.rank]||'排名','#'+esc(txt(r,C.rank)))
      +(C.pts>=0?stat(ths[C.pts],esc(r.cells[C.pts].dataset.v||txt(r,C.pts))):'')
      +(C.days>=0?stat('存活天数',esc(txt(r,C.days)||'0')):'')
      +(C.st>=0?'<span>当前状态'+stCell+'</span>':'');
    const h=tsHist({picks, st:txt(r,C.st), stHtml:stCell, days:txt(r,C.days), hasSt:C.st>=0,
      main:C.main>=0?txt(r,C.main):'', alt:C.alt>=0?txt(r,C.alt):''});
    document.getElementById('rkHistList').innerHTML=h.rows;
    document.getElementById('rkHistSum').textContent=h.sum;
    openModal(hist,from);
  }
  table.addEventListener('click',e=>{ if(e.target.closest('.rk-star')) return; const r=e.target.closest('tbody tr'); if(r) openHist(r,r); });

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
  window.addEventListener('resize',()=>{ clearTimeout(freeze._t); freeze._t=setTimeout(freeze,150); });
  // #u=<name>: opened from the watch page — jump to that user's row
  const hu=location.hash.match(/^#u=(.+)$/);
  if(hu){ let u=''; try{ u=decodeURIComponent(hu[1]); }catch(e){}
    if(byUser.has(u)){ setTimeout(()=>jumpTo(u),300); return; } }
  requestAnimationFrame(()=>play());
});
})();
"""
