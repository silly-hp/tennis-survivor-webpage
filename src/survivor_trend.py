"""Day-by-day survivor counts for the homepage trend chart.

Built from the (live-settled) event score table, where each entrant row has
``day`` = days survived and ``fill_status`` = 存活 or the elimination reason
(球员输球 / 自杀（退赛） / 自杀（主备冲突） / …).
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

# Statuses that still count as "in the event".
STILL_IN = frozenset({"存活", "未完赛", "未选", "轮空", ""})


_OUT_KEYS = ("球员输球", "自杀（重复）", "自杀（主备冲突）", "自杀（退赛）")


def survivor_series(
    score_df: Optional[pd.DataFrame], cur_day: int, checkin: Optional[dict[str, int]] = None
) -> Optional[dict[str, Any]]:
    """Return ``{"total", "days": [{"day", "alive", "out": {reason: n}}], "live"}``.

    ``days[0]`` is the start (everyone in). Entrant eliminated after surviving
    ``d`` days is counted as out on day ``d + 1`` (capped at ``cur_day``).
    ``checkin`` (from ``summary_checkin``) replaces the current day's counts so
    the chart matches the ranking page's 今日选人统计.
    """
    if score_df is None or score_df.empty or not cur_day or cur_day < 1:
        return None
    if "day" not in score_df.columns or "fill_status" not in score_df.columns:
        return None

    df = score_df.loc[:, ["day", "fill_status"]].copy()
    df["fill_status"] = df["fill_status"].astype("string").fillna("").str.strip()
    df = df[df["fill_status"] != "未参赛"]
    total = int(len(df))
    if total == 0:
        return None

    df["day"] = pd.to_numeric(df["day"], errors="coerce").fillna(0).astype(int)
    out = df[~df["fill_status"].isin(STILL_IN)].copy()
    out["out_day"] = (out["day"] + 1).clip(upper=cur_day)

    days = [{"day": 0, "alive": total, "out": {}}]
    alive = total
    for d in range(1, int(cur_day) + 1):
        today = out[out["out_day"] == d]
        reasons = today["fill_status"].value_counts().to_dict()
        alive -= int(len(today))
        days.append({"day": d, "alive": alive, "out": {str(k): int(v) for k, v in reasons.items()}})

    live = bool((df["fill_status"] == "未完赛").any()) or int(cur_day) == 1
    if checkin and len(days) > 1:
        lost = sum(checkin.get(k, 0) for k in _OUT_KEYS)
        days[-1]["checkin"] = checkin
        days[-1]["alive"] = days[-2]["alive"] - lost
        live = checkin.get("未完赛", 0) > 0
    return {"total": total, "days": days, "live": live}


def summary_checkin(
    table: Optional[pd.DataFrame],
    cur_day: int,
    bye: bool = False,
    available_players: Optional[list] = None,
    live_players: Optional[list] = None,
    pending_uids: Optional[set] = None,
    eliminated_players: Optional[list] = None,
) -> Optional[dict[str, int]]:
    """Today's check-in counts, computed exactly like the ranking page's 今日选人统计.

    Same board prep and ``generate_summary`` as ``update_rank_pages``; each
    pick is then classed by its player's draw status the way
    ``site_html.common`` does: eliminated → 球员输球, still in a live match →
    未完赛, otherwise alive → 存活. Suicides and 轮空 come from the totals row.
    """
    if table is None or table.empty or not cur_day:
        return None
    from output_format import (
        generate_summary,
        mark_unfinished_status,
        mark_unpicked_status,
        prepare_rank_change,
    )

    board = prepare_rank_change(
        mark_unpicked_status(mark_unfinished_status(table, live_players, pending_uids))
    )
    summary = generate_summary(board, int(cur_day) == 1, bye)
    if summary is None or summary.empty or "今日主选" not in summary.columns:
        return None

    clean = lambda xs: {str(p).strip() for p in (xs or []) if str(p).strip()}  # noqa: E731
    alive, live, out = clean(available_players), clean(live_players), clean(eliminated_players)
    known = bool(alive) or bool(out)
    normal_col = "非轮空" if "非轮空" in summary.columns else "已选"
    is_total = summary["今日主选"] == "总计"
    counts = {"存活": 0, "未完赛": 0, "球员输球": 0}
    for _, row in summary[~is_total].iterrows():
        n = int(row.get(normal_col, 0) or 0)
        name = str(row["今日主选"]).strip()
        if name in out or (known and name not in live and name not in alive):
            counts["球员输球"] += n
        elif name in live or not known:
            counts["未完赛"] += n
        else:
            counts["存活"] += n
    total = summary[is_total].iloc[0] if is_total.any() else None
    for col in ("轮空", "自杀（重复）", "自杀（主备冲突）", "自杀（退赛）", "未选"):
        if total is not None and col in summary.columns:
            counts[col] = int(total.get(col, 0) or 0)
    return {k: v for k, v in counts.items() if v}


def pick_summary(table: Optional[pd.DataFrame], top_n: int = 3) -> Optional[dict[str, Any]]:
    """Today's picks from a ranking table: counts plus the most-picked players."""
    if table is None or table.empty or "今日主选" not in table.columns:
        return None
    pick = table["今日主选"].astype("string").fillna("").str.strip()
    status = (
        table["今日状态"].astype("string").fillna("").str.strip()
        if "今日状态" in table.columns
        else pd.Series("", index=table.index)
    )
    chosen = pick[(pick != "") & (pick != "轮空")]
    if chosen.empty:
        return None
    bye = int(((status == "轮空") & (pick != "")).sum())
    counts = chosen.value_counts()
    total = int(len(chosen))
    top = [
        {"name": str(name), "n": int(n), "pct": round(n / total * 100)}
        for name, n in counts.head(top_n).items()
    ]
    return {"total": total, "bye": bye, "picked": total - bye, "top": top}
