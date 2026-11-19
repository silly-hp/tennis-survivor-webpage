"""
ATP + WTA combined rankings (live / race).

Independent display pages built by outer-merging the two tour tables on
``user_id`` and summing live scores — same idea as chen_web ``build_combined``,
adapted to frog's flat ranking columns.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from combined_finals import (
    load_year_end,
    points_event_name,
    select_field,
    strip_individual_finals,
    current_event_is_finals,
)
from live_settlement import _as_key
from logger import get_logger

logger = get_logger(__name__)

DISPLAY_BASE = [
    "排名",
    "用户名",
    "总分",
    "排名变化",
    "WTA总分",
    "ATP总分",
    "WTA状态",
    "ATP状态",
]


def _to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)


def _pick_col(df: pd.DataFrame, *names: str) -> Optional[str]:
    for name in names:
        if name in df.columns:
            return name
    return None


def _event_label(name: Optional[str], year: Optional[Any], overlap: bool) -> str:
    base = (name or "").strip() or "本站"
    if overlap and year is not None and str(year).strip():
        return f"{base}{year}"
    return base


def _slice_tour(
    frame: pd.DataFrame,
    prefix: str,
    *,
    event_name: Optional[str],
    event_year: Optional[Any],
    removed_name: Optional[str],
    overlap_events: set[str],
    include_replace: bool,
) -> pd.DataFrame:
    uid_col = _pick_col(frame, "user_id", "主键")
    name_col = _pick_col(frame, "用户名", "username")
    score_col = _pick_col(frame, "即时积分", "live_score", "总分")
    base_col = _pick_col(frame, "当前积分", "current_score")
    status_col = _pick_col(frame, "当前状态", "fill_status", "状态")
    week_col = _pick_col(frame, "本站得分", "score")
    removed_col = _pick_col(frame, "扣除积分", "removed_point")

    if uid_col is None or score_col is None:
        raise ValueError(f"{prefix} ranking frame missing user_id / live score columns")

    out = pd.DataFrame(
        {
            "主键": frame[uid_col].map(_as_key),
            "用户名": frame[name_col].fillna("").astype(str) if name_col else "",
            f"{prefix}总分": _to_int(frame[score_col]),
            f"{prefix}上周总分": (
                _to_int(frame[base_col]) if base_col else _to_int(frame[score_col])
            ),
            f"{prefix}状态": (
                frame[status_col].fillna("").astype(str) if status_col else ""
            ),
        }
    )
    out = out[out["主键"].astype(str).str.len() > 0]

    if week_col and event_name:
        label = _event_label(
            event_name, event_year, overlap=(event_name in overlap_events)
        )
        if event_name in overlap_events and not label.startswith(prefix):
            label = f"{prefix}{label}"
        out[label] = _to_int(frame[week_col])

    # 替换列 = 去年同周赛事名（可能与本站不同名，如 武汉←宁波）
    if include_replace and removed_col and removed_name:
        label = (
            f"替换{prefix}{removed_name}"
            if removed_name in overlap_events
            else f"替换{removed_name}"
        )
        out[label] = _to_int(frame[removed_col])

    return out


def _normalize_removed(value: Optional[Any]) -> Optional[str]:
    """Config may store a string or a list of same-week cities; use the first label."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            text = str(item).strip()
            if text:
                return text
        return None
    text = str(value).strip()
    return text or None


def build_combined(
    atp_frame: pd.DataFrame,
    wta_frame: pd.DataFrame,
    *,
    instant: bool = False,
    atp_event: Optional[str] = None,
    wta_event: Optional[str] = None,
    atp_year: Optional[Any] = None,
    wta_year: Optional[Any] = None,
    atp_removed: Optional[Any] = None,
    wta_removed: Optional[Any] = None,
) -> pd.DataFrame:
    """
    Outer-merge ATP / WTA ranking tables into a combined board.

    Parameters
    ----------
    atp_frame, wta_frame
        Frog ranking tables (Chinese column names after ``COL_ZH_DICT`` rename),
        still containing ``user_id``.
    instant
        When True, include 扣除积分 as 「替换{去年同周}」 columns.
    atp_event / wta_event
        Current event city names used to label 本站得分 columns.
    atp_removed / wta_removed
        Last year's corresponding-week event name(s) for 替换 columns.
    """
    if atp_frame is None or atp_frame.empty:
        raise ValueError("atp_frame is required")
    if wta_frame is None or wta_frame.empty:
        raise ValueError("wta_frame is required")

    atp_removed_name = _normalize_removed(atp_removed)
    wta_removed_name = _normalize_removed(wta_removed)

    overlap: set[str] = set()
    if atp_event and wta_event and atp_event.strip() == wta_event.strip():
        overlap.add(atp_event.strip())
    if atp_removed_name and wta_removed_name and atp_removed_name == wta_removed_name:
        overlap.add(atp_removed_name)

    atp_part = _slice_tour(
        atp_frame,
        "ATP",
        event_name=atp_event,
        event_year=atp_year,
        removed_name=atp_removed_name,
        overlap_events=overlap,
        include_replace=instant,
    )
    wta_part = _slice_tour(
        wta_frame,
        "WTA",
        event_name=wta_event,
        event_year=wta_year,
        removed_name=wta_removed_name,
        overlap_events=overlap,
        include_replace=instant,
    )

    combined = pd.merge(wta_part, atp_part, on="主键", how="outer", suffixes=("_wta", "_atp"))
    if "用户名_wta" in combined.columns or "用户名_atp" in combined.columns:
        combined["用户名"] = combined.get("用户名_wta", pd.Series(dtype=str)).fillna(
            combined.get("用户名_atp", pd.Series(dtype=str))
        )
        combined = combined.drop(
            columns=[c for c in ("用户名_wta", "用户名_atp") if c in combined.columns]
        )
    elif "用户名" not in combined.columns:
        combined["用户名"] = ""

    for col in ("ATP总分", "WTA总分", "ATP上周总分", "WTA上周总分"):
        if col not in combined.columns:
            combined[col] = 0
        combined[col] = _to_int(combined[col])
    for col in ("ATP状态", "WTA状态"):
        if col not in combined.columns:
            combined[col] = ""
        combined[col] = combined[col].fillna("")

    combined["总分"] = combined["ATP总分"] + combined["WTA总分"]
    combined["上周总分"] = combined["ATP上周总分"] + combined["WTA上周总分"]
    combined["上周排名"] = combined["上周总分"].rank(ascending=False, method="min").astype(int)
    combined["排名"] = combined["总分"].rank(ascending=False, method="min").astype(int)
    # Positive = rose (aligned with frog 排名变化 / chen 升降)
    combined["排名变化"] = combined["上周排名"] - combined["排名"]
    combined["用户名"] = combined["用户名"].fillna("")
    combined = combined.sort_values(["排名", "用户名"]).reset_index(drop=True)

    # Preserve week / replace columns in WTA-then-ATP order
    extra_cols = [
        c
        for c in list(wta_part.columns) + list(atp_part.columns)
        if c not in {"主键", "用户名", "ATP总分", "WTA总分", "ATP上周总分", "WTA上周总分", "ATP状态", "WTA状态"}
        and c in combined.columns
    ]
    # Dedupe preserving order
    seen: set[str] = set()
    ordered_extra: list[str] = []
    for col in extra_cols:
        if col not in seen:
            seen.add(col)
            ordered_extra.append(col)
            combined[col] = _to_int(combined[col])

    # Keep 主键 for row click → breakdown charts (hidden in HTML render).
    # Last week's tour totals stay on the frame so 排名变化 can be recomputed
    # after year-end points are added; the page builder drops them before render.
    html_columns = ["主键"] + DISPLAY_BASE + ordered_extra
    for col in ("ATP上周总分", "WTA上周总分"):
        if col in combined.columns and col not in html_columns:
            html_columns.append(col)
    out = combined[html_columns].copy()
    out.attrs["instant"] = instant
    out.attrs["event_columns"] = ordered_extra
    return out


def _ranking_entries(frame: pd.DataFrame) -> list[tuple[str, int, str]]:
    entries: list[tuple[str, int, str]] = []
    if frame is None or frame.empty or "主键" not in frame.columns:
        return entries
    names = frame["用户名"] if "用户名" in frame.columns else pd.Series("", index=frame.index)
    points = pd.to_numeric(frame["总分"], errors="coerce").fillna(0)
    for uid, score, name in zip(frame["主键"], points, names):
        key = _as_key(uid)
        if key:
            entries.append((key, int(score), str(name or "")))
    return entries


def _status_by_year_end(frame: pd.DataFrame, roster: set[str] | None, result) -> pd.DataFrame:
    """On both combined boards, status follows the combined year-end.

    Before the ATP finals' first day is settled, ``roster`` is ``None`` and
    every status stays as recorded. Afterwards anyone outside the field is
    未参赛. People in the field use the finals settlement, because the
    single-tour board only keeps that tour's own top 8.
    """
    if roster is None or frame is None or frame.empty or "主键" not in frame.columns:
        return frame
    out = frame.copy()
    keys = out["主键"].map(_as_key)
    outside = ~keys.isin(roster)
    for col in ("WTA状态", "ATP状态"):
        if col in out.columns:
            out.loc[outside, col] = "未参赛"
    wta_status = getattr(result, "wta_status", {}) or {}
    atp_status = getattr(result, "atp_status", {}) or {}

    def _missing(value: object) -> bool:
        return str(value or "").strip() in {"", "未参赛"}

    for idx, key, is_out in zip(out.index, keys, outside):
        if is_out or not key:
            continue
        # The single-tour board drops anyone outside that tour's own top 8,
        # so their status is a blank 未参赛 even after they played the final.
        if "WTA状态" in out.columns and _missing(out.at[idx, "WTA状态"]):
            wta = wta_status.get(key)
            if wta:
                out.at[idx, "WTA状态"] = wta
        if "ATP状态" in out.columns and _missing(out.at[idx, "ATP状态"]):
            atp = atp_status.get(key)
            if atp:
                out.at[idx, "ATP状态"] = atp
    return out


def _with_year_end(
    frame: pd.DataFrame,
    result,
    roster: set[str] | None,
) -> pd.DataFrame:
    """Add the halved finals columns and rank again."""
    out = frame.copy()
    keys = out["主键"].map(_as_key) if "主键" in out.columns else pd.Series(dtype=str)
    wta_vals = []
    atp_vals = []
    present = set(keys)
    for key in keys:
        wta_half, atp_half = result.counted(key, roster)
        wta_vals.append(wta_half)
        atp_vals.append(atp_half)
    out["WTA年终"] = wta_vals
    out["ATP年终"] = atp_vals

    extras: list[dict[str, object]] = []
    for uid, name in result.names.items():
        if uid in present:
            continue
        wta_half, atp_half = result.counted(uid, roster)
        if wta_half <= 0 and atp_half <= 0:
            continue
        extras.append(
            {
                "主键": uid,
                "用户名": name,
                "ATP总分": 0,
                "WTA总分": 0,
                "ATP上周总分": 0,
                "WTA上周总分": 0,
                "ATP状态": "",
                "WTA状态": "",
                "上周总分": 0,
                "WTA年终": wta_half,
                "ATP年终": atp_half,
            }
        )
    if extras:
        out = pd.concat([out, pd.DataFrame(extras)], ignore_index=True)
    out["用户名"] = out["用户名"].fillna("")
    for col in ("ATP状态", "WTA状态"):
        if col in out.columns:
            out[col] = out[col].fillna("").astype(str)
    for col in out.columns:
        if col in {"主键", "用户名", "ATP状态", "WTA状态"}:
            continue
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype(int)

    for col in ("ATP总分", "WTA总分", "ATP上周总分", "WTA上周总分", "WTA年终", "ATP年终"):
        if col not in out.columns:
            out[col] = 0
        out[col] = _to_int(out[col])
    out["总分"] = out["ATP总分"] + out["WTA总分"] + out["WTA年终"] + out["ATP年终"]
    out["上周总分"] = out["ATP上周总分"] + out["WTA上周总分"]
    out["上周排名"] = out["上周总分"].rank(ascending=False, method="min").astype(int)
    out["排名"] = out["总分"].rank(ascending=False, method="min").astype(int)
    out["排名变化"] = out["上周排名"] - out["排名"]
    out["用户名"] = out["用户名"].fillna("")
    out = out.sort_values(["排名", "用户名"]).reset_index(drop=True)

    base = ["主键", *DISPLAY_BASE]
    year_cols = ["WTA年终", "ATP年终"]
    hidden = {"ATP上周总分", "WTA上周总分", "上周总分", "上周排名"}
    extras_cols = [
        col
        for col in out.columns
        if col not in set(base) | set(year_cols) | hidden
    ]
    ordered = [col for col in base if col in out.columns] + year_cols + extras_cols
    return out[ordered]


def update_combined_pages(
    atp_live: pd.DataFrame,
    wta_live: pd.DataFrame,
    atp_race: pd.DataFrame,
    wta_race: pd.DataFrame,
    *,
    atp_event: Optional[str] = None,
    wta_event: Optional[str] = None,
    atp_event_id: Optional[Any] = None,
    wta_event_id: Optional[Any] = None,
    atp_removed: Optional[Any] = None,
    wta_removed: Optional[Any] = None,
    year: Optional[Any] = None,
    updated: Optional[str] = None,
    output_dir: str | Path = "..",
    atp_rank_raw: Optional[pd.DataFrame] = None,
    wta_rank_raw: Optional[pd.DataFrame] = None,
    atp_race_raw: Optional[pd.DataFrame] = None,
    wta_race_raw: Optional[pd.DataFrame] = None,
) -> list[Path]:
    """Write ``combined_instant_ranking.html`` and ``combined_ranking.html``."""
    from survivor_html import render_ranking_page
    from user_breakdown import write_breakdown_bundle

    output_dir = Path(output_dir)
    data_dir = output_dir / "data"
    updated = updated or datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    written: list[Path] = []

    # Per-user event composition JSON (clicked from combined tables).
    # Raw frames supply details_text; live/race tables supply 本站得分 so
    # calculate_points matches 即时积分 on the board.
    try:
        write_breakdown_bundle(
            atp_live=atp_rank_raw if atp_rank_raw is not None else atp_live,
            wta_live=wta_rank_raw if wta_rank_raw is not None else wta_live,
            atp_race=atp_race_raw if atp_race_raw is not None else atp_race,
            wta_race=wta_race_raw if wta_race_raw is not None else wta_race,
            atp_live_table=atp_live,
            wta_live_table=wta_live,
            atp_race_table=atp_race,
            wta_race_table=wta_race,
            atp_event=atp_event,
            wta_event=wta_event,
            atp_event_id=atp_event_id,
            wta_event_id=wta_event_id,
            atp_removed=atp_removed,
            wta_removed=wta_removed,
            output_dir=data_dir,
            calendar_dir=data_dir,
            score_dir=data_dir / "event_scores",
            round_cache_dir=data_dir / "event_day_rounds",
            fetch_day_rounds=True,
        )
    except Exception:
        logger.exception("Failed to write user breakdown JSON")

    atp_finals = current_event_is_finals(atp_event, atp_event_id)
    wta_finals = current_event_is_finals(wta_event, wta_event_id)
    atp_points_name = points_event_name(atp_event, atp_event_id)
    wta_points_name = points_event_name(wta_event, wta_event_id)
    atp_live = strip_individual_finals(
        atp_live,
        atp_rank_raw,
        "ATP",
        removed_names=atp_removed,
        current_name=atp_points_name,
        current_is_finals=atp_finals,
    )
    wta_live = strip_individual_finals(
        wta_live,
        wta_rank_raw,
        "WTA",
        removed_names=wta_removed,
        current_name=wta_points_name,
        current_is_finals=wta_finals,
    )
    atp_race = strip_individual_finals(
        atp_race,
        atp_race_raw,
        "ATP",
        current_name=atp_points_name,
        current_is_finals=atp_finals,
    )
    wta_race = strip_individual_finals(
        wta_race,
        wta_race_raw,
        "WTA",
        current_name=wta_points_name,
        current_is_finals=wta_finals,
    )
    # A finals week has no ordinary 本站 column; WTA年终 / ATP年终 carry it.
    atp_label = None if atp_finals else atp_event
    wta_label = None if wta_finals else wta_event

    instant = build_combined(
        atp_live,
        wta_live,
        instant=True,
        atp_event=atp_label,
        wta_event=wta_label,
        atp_removed=atp_removed,
        wta_removed=wta_removed,
        atp_year=year,
        wta_year=year,
    )
    race = build_combined(
        atp_race,
        wta_race,
        instant=False,
        atp_event=atp_label,
        wta_event=wta_label,
        atp_year=year,
        wta_year=year,
    )
    try:
        year_end = load_year_end(int(year)) if year else None
    except Exception:
        logger.exception("联合年终结算失败，联合榜先不含这项分")
        year_end = None
    if year_end is not None:
        entries = _ranking_entries(race)
        known = {uid for uid, _points, _name in entries}
        for uid, name in year_end.names.items():
            if uid not in known:
                entries.append((uid, 0, name))
        roster = select_field(
            entries,
            year_end.participated,
            locked=year_end.locked,
        )
        if roster is None:
            logger.info("都灵首日未结算，联合年终先给所有选人记分")
        else:
            logger.info(f"都灵首日已结算，联合年终名单 {len(roster)} 人")
        instant = _status_by_year_end(
            _with_year_end(instant, year_end, roster), roster, year_end
        )
        race = _status_by_year_end(
            _with_year_end(race, year_end, roster), roster, year_end
        )

    specs = [
        (
            instant,
            "联合即时排名",
            "ALL · Combined Live Ranking",
            ["即时"],
            "combined_instant_ranking.html",
            "data/breakdown_live_atp.js",
            "data/breakdown_live_wta.js",
        ),
        (
            race,
            "联合冠军排名",
            "ALL · Combined Race Ranking",
            ["冠军积分"],
            "combined_ranking.html",
            "data/breakdown_race_atp.js",
            "data/breakdown_race_wta.js",
        ),
    ]
    for df, title, eyebrow, tags, filename, atp_url, wta_url in specs:
        out = output_dir / filename
        render_ranking_page(
            df=df,
            title=title,
            tour="ALL",
            eyebrow=eyebrow,
            updated=updated,
            summary_df=None,
            rank_change_col="排名变化",
            extra_tags=tags,
            available_players=None,
            enable_detail=False,
            enable_breakdown=True,
            breakdown_atp_url=atp_url,
            breakdown_wta_url=wta_url,
            output_path=str(out),
        )
        written.append(out)
        logger.info(f"wrote {out} ({len(df)} rows)")
    return written
