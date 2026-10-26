"""Ranking page renderer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd

from site_html.breakdown_ui import (
    _CSS_BREAKDOWN,
    breakdown_boot_script,
    breakdown_modal_html,
)
from site_html.common import (
    _df_to_html_table,
    _inner_page_shell,
    _killer_panel_html,
    _load_available_players,
    _summary_bar_html,
)
from site_html.rank_ui import (
    CSS_RANK,
    JS_RANK,
    help_button_html,
    help_modal_html,
    history_modal_html,
    me_card_html,
    table_card_close,
    table_card_open,
)
from site_html.js import (
    _CSS_CAREER_DETAIL,
    _JS_CAREER_DETAIL,
    _JS_RANKING_DETAIL,
)


def _rank_first(df: pd.DataFrame) -> tuple[pd.DataFrame, Optional[str]]:
    """Order columns as rank · 当前排名 · 用户名 · rest (frozen on desktop).

    Returns the reordered frame and the column that carries the rank change
    (the 即时排名 / 排名 column).
    """
    cols = list(df.columns)
    rank = next((c for c in ("即时排名", "排名") if c in cols), None)
    lead = [c for c in (rank, "当前排名", "用户名") if c and c in cols]
    target = rank
    return df[lead + [c for c in cols if c not in lead]], target


def render_ranking_page(
    df: pd.DataFrame,
    title: str,
    tour: str,
    eyebrow: str,
    updated: str,
    summary_df: Optional[pd.DataFrame] = None,
    summary_top_n: int = 3,
    killer_df: Optional[pd.DataFrame] = None,
    rank_change_col: Optional[str] = "排名变化",
    extra_tags: Optional[list[str]] = None,
    available_players: Union[list[str], str, Path, None] = None,
    finals_top: int = 0,
    live_players: Optional[list[str]] = None,
    eliminated_players: Optional[list[str]] = None,
    backup_events: Optional[list] = None,
    output_path: str | Path = "ranking.html",
    enable_detail: bool = True,
    enable_career_detail: bool = False,
    enable_breakdown: bool = False,
    breakdown_atp_url: str = "data/breakdown_live_atp.json",
    breakdown_wta_url: str = "data/breakdown_live_wta.json",
    expired_label: Optional[str] = None,
) -> str:
    """
    Build and write a ranking-table page.

    Parameters
    ----------
    df : pd.DataFrame
        Main ranking data. Every column becomes a filterable/sortable column.
    title : str
        Large page title, e.g. "即时冠军排名".
    tour : str
        "ATP" or "WTA" — controls pill colour.
    eyebrow : str
        Small label above the title, e.g. "ATP · Race to Turin · 2026".
    updated : str
        Timestamp string shown in the topbar, e.g. "2026年05月08日 16:22".
    summary_df : pd.DataFrame or None
        Output of generate_summary(). Pass None to hide the panel entirely.
        Mode (normal / bye) is auto-detected from column names:
        - Normal: columns contain "已选"
        - Day-1 bye: columns contain "非轮空" and "轮空"
    summary_top_n : int
        Number of player rows shown before the "show all" toggle (default 5).
    killer_df : pd.DataFrame or None
        Output of daily_killer_stats(); collapsible「每日杀手统计」panel.
    rank_change_col : str or None
        Column in df whose values are rendered as ▲/▼ badges.
    extra_tags : list[str] or None
        Additional pill tags next to the title (e.g. ["Race"]).
    available_players : list[str], str, Path, or None
        Players still alive in the draw, used to power the "夺冠路线查询"
        feature (a modal where the user multiselects players and sees
        which 存活 users have not picked any of them yet, alongside
        each matching user's 今日主选/今日备选). Pass a plain list, or a
        path to a JSON file (e.g. "available_players.json") containing
        a flat array of player names. Pass None to render the entry bar
        with an empty player list.
    live_players : list[str] or None
        Subset of available_players whose match is still in progress
        (未完赛). Used by the summary panel to distinguish 未完赛 vs
        已完赛确认存活.
    backup_events : list or None
        Aggregated early-retirement backup activations for the summary panel
        (``summarize_backup_events`` output).
    output_path : str or Path
        Destination file.
    enable_detail : bool
        When True (default), clicking a row opens the 选人明细 modal.
        Set False for pages without pick history.
    enable_career_detail : bool
        Career stats: row click opens 夺冠/夺亚 chip modal from ``_生涯明细``.
    enable_breakdown : bool
        Combined-ranking mode: row click opens ATP/WTA points charts.
    expired_label : str or None
        Bold line under the title, e.g. "2025九江"; "无" when nothing is removed.
        None hides the line.
    breakdown_atp_url / breakdown_wta_url : str
        JSON paths (relative to the HTML file) for per-user event composition.

    Returns
    -------
    str : the generated HTML string.
    """
    _players = _load_available_players(available_players)

    # Build optional summary panel
    if summary_df is not None:
        summary_block = _summary_bar_html(
            summary_df,
            top_n=summary_top_n,
            available_players=_players,
            live_players=live_players,
            eliminated_players=eliminated_players,
            backup_events=backup_events,
        )
        summary_js = ""  # JS is inlined inside _summary_bar_html
    else:
        summary_block = ""
        summary_js = ""

    killer_block = _killer_panel_html(killer_df)
    df, change_target = _rank_first(df)
    # day-1 bye: the summary is split 非轮空 / 轮空 (see _summary_bar_html)
    bye_day = summary_df is not None and any(
        "非轮空" in str(c) for c in summary_df.columns
    )

    if enable_career_detail:
        detail_col = "_生涯明细"
    elif enable_detail:
        detail_col = "选人明细"
    else:
        detail_col = None

    main_table_html = _df_to_html_table(
        df,
        rank_change_col=rank_change_col,
        detail_col=detail_col,
        hide_detail_col=True,
        uid_col="主键" if enable_breakdown else None,
        hide_uid_col=True,
        row_click_class="bd-clickable" if enable_breakdown else "",
        merge_change_into=change_target if rank_change_col else None,
    )

    detail_modal = ""
    no_detail_style = ""
    detail_title = "生涯明细" if enable_career_detail else "选人明细"
    rank_history = enable_detail and not enable_career_detail
    if rank_history:
        detail_modal = history_modal_html(eyebrow)
    elif enable_detail or enable_career_detail:
        detail_modal = f"""\
    <div id="detail-modal" class="detail-modal">
      <div class="detail-card">
        <div class="detail-hd">
          <div class="detail-title-wrap">
            <div class="detail-icon">📋</div>
            <div>
              <div class="detail-title">{detail_title}</div>
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
    elif not enable_breakdown:
        no_detail_style = "<style>.filterable-table tbody tr{{cursor:default;}}</style>"

    bd_modal = breakdown_modal_html() if enable_breakdown else ""
    bd_boot = (
        breakdown_boot_script(breakdown_atp_url, breakdown_wta_url)
        if enable_breakdown
        else ""
    )

    top = (
        f'<div class="rk-top">{summary_block}<aside class="rk-aside">{me_card_html()}{killer_block}</aside></div>'
        if summary_block
        else f'<div class="rk-top rk-top-solo"><aside class="rk-aside">{me_card_html()}{killer_block}</aside></div>'
    )
    body = f"""\
        {no_detail_style}
<div class="rk" id="rk" data-tour="{tour.upper()}" data-finals="{int(finals_top)}" data-byeday="{int(bye_day)}">
{top}
{table_card_open(_players)}
        <div class="table-wrapper">
            <div id="table-container">
            {main_table_html}
        </div>
    </div>
{table_card_close()}
{detail_modal}
{help_modal_html(title, bool(finals_top), combined=enable_breakdown)}
</div>"""

    if enable_career_detail:
        detail_js = _JS_CAREER_DETAIL
    elif enable_detail and not rank_history:
        detail_js = _JS_RANKING_DETAIL
    else:
        detail_js = ""
    extra_css_parts = [CSS_RANK]
    if enable_breakdown:
        extra_css_parts.append(_CSS_BREAKDOWN)
    if enable_career_detail:
        extra_css_parts.append(_CSS_CAREER_DETAIL)
    html_str = _inner_page_shell(
        page_title=title,
        title=title,
        tour=tour,
        eyebrow=eyebrow,
        updated=updated,
        extra_tags=extra_tags,
        body_content=body,
        extra_js=summary_js + "\n" + detail_js + "\n" + bd_boot,
        extra_css="\n".join(extra_css_parts),
        # Modal must sit outside .page stacking context or it can be covered
        after_page=bd_modal,
        page=str(output_path),
        late_js=JS_RANK,
        title_extra=help_button_html(
            hint=not enable_breakdown,
            expired=expired_label,
        ),
    )

    Path(output_path).write_text(html_str, encoding="utf-8")
    return html_str
