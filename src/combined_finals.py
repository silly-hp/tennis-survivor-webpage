"""Combined year-end finals for the combined ranking only.

丘网 has no combined board. Men's and women's finals stay on their own
champion rankings. This module scores 联合年终 from the detail pages and
keeps those points off the single-tour tables.

Before the ATP finals' first day is settled, every user who submitted a
pick is scored. Afterwards the field is the combined champion top 8 from
before the WTA finals (ties at 8th included). Someone in that field who
did not submit a day-1 primary at both events is replaced from the next
place; a tie at the replacement place all come in.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from finals_settlement import (
    _as_key,
    complete_day_results,
    day_matches_finished,
    fetch_pick_day_results,
    finals_score_name,
    is_year_end_final,
)
from live_ranking import remove_current_tournament
from live_settlement import settle_tour_scores, submission_to_detail_rows
from logger import get_logger
from points_calculation import (
    ATP_YEAR_END_FINALS,
    WTA_YEAR_END_FINAL,
    calculate_points,
    parse_events,
)

logger = get_logger(__name__)

# Surviving day 1..6. The site shows these numbers; the combined board
# counts half of each rung.
RAW_LADDER = (150, 300, 450, 600, 1000, 1500)
WTA_FINALS_EVENT_ID = "30808"
ATP_FINALS_EVENT_ID = "20605"
YEAR_END_NAMES = {
    "WTA": tuple(WTA_YEAR_END_FINAL),
    "ATP": tuple(ATP_YEAR_END_FINALS),
}


@dataclass
class YearEndResult:
    """Halved scores and whether the 8-person field is decided."""

    wta_half: dict[str, int] = field(default_factory=dict)
    atp_half: dict[str, int] = field(default_factory=dict)
    wta_status: dict[str, str] = field(default_factory=dict)
    atp_status: dict[str, str] = field(default_factory=dict)
    names: dict[str, str] = field(default_factory=dict)
    participated: set[str] = field(default_factory=set)
    locked: bool = False

    def counted(self, uid: str, roster: set[str] | None) -> tuple[int, int]:
        key = _as_key(uid)
        if roster is not None and key not in roster:
            return 0, 0
        return int(self.wta_half.get(key, 0)), int(self.atp_half.get(key, 0))


def raw_points(survived_days: int) -> int:
    """Game score after surviving this many days. A day-1 loss is 0."""
    days = int(survived_days or 0)
    if days <= 0:
        return 0
    return RAW_LADDER[min(days, len(RAW_LADDER)) - 1]


def half_points(survived_days: int) -> int:
    return raw_points(survived_days) // 2


def select_field(
    entries: list[tuple[str, int, str]],
    participated: set[str],
    *,
    locked: bool,
    spots: int = 8,
) -> set[str] | None:
    """Who keeps a combined year-end score.

    ``None`` means the cutoff is not applied yet, so every scored user
    stays. Once locked, rank 8 and better qualify, ties included. Vacant
    places are filled from the next rank; everyone tied at that rank who
    submitted both day-1 picks comes in together.
    """
    if not locked:
        return None
    cleaned = [
        (_as_key(uid), int(points), str(name or ""))
        for uid, points, name in entries
        if _as_key(uid)
    ]
    if not cleaned:
        return set()
    ordered_points = sorted((points for _uid, points, _name in cleaned), reverse=True)
    cutoff = ordered_points[min(spots, len(ordered_points)) - 1]
    initial = {uid for uid, points, _name in cleaned if points >= cutoff}
    kept = {uid for uid in initial if uid in participated}
    vacancies = len(initial) - len(kept)
    rest = sorted(
        (
            (uid, points, name)
            for uid, points, name in cleaned
            if uid not in initial
        ),
        key=lambda item: (-item[1], item[2], item[0]),
    )
    index = 0
    while vacancies > 0 and index < len(rest):
        rank_points = rest[index][1]
        group: list[str] = []
        while index < len(rest) and rest[index][1] == rank_points:
            uid = rest[index][0]
            if uid in participated:
                group.append(uid)
            index += 1
        if not group:
            continue
        kept.update(group)
        vacancies -= len(group)
    return kept


def _submitted_mask(frame: pd.DataFrame) -> pd.Series:
    if "存活天数" not in frame.columns:
        return pd.Series(False, index=frame.index)
    return frame["存活天数"].notna()


def _recompute_total(
    details_text: object,
    tour: str,
    *,
    removed_names: list[str],
    current_name: str,
    current_is_finals: bool,
    week_score: int,
    submitted: bool,
) -> int:
    parsed = parse_events(details_text if isinstance(details_text, str) else "")
    for name in removed_names:
        parsed, _removed = remove_current_tournament(parsed, name)
    for name in YEAR_END_NAMES.get(tour, ()):
        parsed.pop(name, None)
    if submitted and current_name and not current_is_finals:
        parsed[current_name] = int(week_score or 0)
    return int(calculate_points(parsed, tour=tour)["total_points"])


def _details_map(raw: pd.DataFrame | None) -> dict[str, str]:
    if raw is None or getattr(raw, "empty", True) or "user_id" not in raw.columns:
        return {}
    column = "details_text" if "details_text" in raw.columns else ""
    if not column:
        return {}
    found: dict[str, str] = {}
    for uid, text in zip(raw["user_id"], raw[column]):
        key = _as_key(uid)
        if key:
            found[key] = text if isinstance(text, str) else ""
    return found


def _names_of(removed: object) -> list[str]:
    if removed is None:
        return []
    if isinstance(removed, str):
        text = removed.strip()
        return [text] if text else []
    return [str(item).strip() for item in removed if str(item).strip()]


def strip_individual_finals(
    frame: pd.DataFrame,
    raw: pd.DataFrame | None,
    tour: str,
    *,
    removed_names: object = None,
    current_name: str = "",
    current_is_finals: bool = False,
) -> pd.DataFrame:
    """Drop individual year-end points from one tour table.

    Live and race totals are recomputed with those events left out. The
    current week's score stays, unless this week is itself a final.
    """
    if frame is None or frame.empty or "user_id" not in frame.columns:
        return frame
    if "即时积分" not in frame.columns:
        return frame
    out = frame.copy()
    details = _details_map(raw)
    removed = _names_of(removed_names)
    week = (
        pd.to_numeric(out["本站得分"], errors="coerce").fillna(0).astype(int)
        if "本站得分" in out.columns
        else pd.Series(0, index=out.index)
    )
    submitted = _submitted_mask(out)
    keys = out["user_id"].map(_as_key)
    published_live = pd.to_numeric(out["即时积分"], errors="coerce").fillna(0)
    totals = []
    for key, score, flag, published in zip(keys, week, submitted, published_live):
        if not key or key not in details:
            value = int(published or 0)
            if current_is_finals:
                value = max(0, value - int(score or 0))
            totals.append(value)
            continue
        totals.append(
            _recompute_total(
                details.get(key, ""),
                tour,
                removed_names=removed,
                current_name=str(current_name or ""),
                current_is_finals=current_is_finals,
                week_score=int(score),
                submitted=bool(flag),
            )
        )
    out["即时积分"] = totals
    if "当前积分" in out.columns and details:
        base = []
        published_base = pd.to_numeric(out["当前积分"], errors="coerce").fillna(0)
        for key, published in zip(keys, published_base):
            if key not in details:
                base.append(int(published or 0))
                continue
            parsed = parse_events(details.get(key, ""))
            full = int(calculate_points(parsed, tour=tour)["total_points"])
            for name in YEAR_END_NAMES.get(tour, ()):
                parsed.pop(name, None)
            stripped = int(calculate_points(parsed, tour=tour)["total_points"])
            base.append(max(0, int(published) - (full - stripped)))
        out["当前积分"] = base
    if current_is_finals and "本站得分" in out.columns:
        out["本站得分"] = 0
    return out


def _day1_users(submissions: pd.DataFrame | None) -> set[str]:
    if submissions is None or getattr(submissions, "empty", True):
        return set()
    if "user_id" not in submissions.columns or "day" not in submissions.columns:
        return set()
    found: set[str] = set()
    days = pd.to_numeric(submissions["day"], errors="coerce")
    players = submissions["player"] if "player" in submissions.columns else ""
    for uid, day, player in zip(submissions["user_id"], days, players):
        if int(day or 0) != 1:
            continue
        name = str(player or "").strip()
        if not name or name == "轮空":
            continue
        key = _as_key(uid)
        if key:
            found.add(key)
    return found


def _score_submissions(
    submissions: pd.DataFrame | None,
    draw,
    day_results: dict | None,
) -> tuple[dict[str, int], dict[str, str]]:
    settled, _counts, _bye, _play, _pending, _backups = settle_tour_scores(
        None,
        submissions,
        draw,
        base_score=0,
        day_results=day_results,
    )
    halves: dict[str, int] = {}
    statuses: dict[str, str] = {}
    if settled is None or settled.empty:
        return halves, statuses
    for row in settled.to_dict(orient="records"):
        key = _as_key(row.get("user_id"))
        if not key:
            continue
        halves[key] = half_points(int(row.get("day") or 0))
        status = str(row.get("fill_status") or "").strip()
        if status:
            statuses[key] = status
    return halves, statuses


def _remember_names(submissions: pd.DataFrame | None, names: dict[str, str]) -> None:
    if submissions is None or getattr(submissions, "empty", True):
        return
    if "user_id" not in submissions.columns:
        return
    username = submissions["username"] if "username" in submissions.columns else None
    if username is None:
        return
    for uid, name in zip(submissions["user_id"], username):
        key = _as_key(uid)
        text = str(name or "").strip()
        if key and text and key not in names:
            names[key] = text


def score_finals_event(
    event_id: str,
    year: int,
    tour_code: str,
) -> tuple[dict[str, int], dict[str, str], set[str], bool, dict[str, str]]:
    """Halved scores, day-1 submitters, and whether day 1 is settled.

    Picks come from the detail page. The score page is not read, so users
    outside that tour's own top 8 still get a score.
    """
    from draw_status import fetch_draw_status
    from parser import fetch_table

    submissions, _count = fetch_table(
        option="submission",
        tour=tour_code,
        event_id=event_id,
        year=year,
    )
    draw = fetch_draw_status(event_id, year, tour_code)
    rows = submission_to_detail_rows(submissions)
    results = complete_day_results(
        fetch_pick_day_results(event_id, getattr(draw, "pick_days", None)),
        draw,
        rows,
    )
    halves, statuses = _score_submissions(submissions, draw, results)
    names: dict[str, str] = {}
    _remember_names(submissions, names)
    settled = day_matches_finished((results or {}).get(1), 1)
    return halves, statuses, _day1_users(submissions), settled, names


def load_year_end(year: int) -> YearEndResult:
    """Fetch both finals and score them. ATP day 1 decides the lock."""
    result = YearEndResult()
    specs = (
        ("WTA", "WS", WTA_FINALS_EVENT_ID),
        ("ATP", "MS", ATP_FINALS_EVENT_ID),
    )
    day1: dict[str, set[str]] = {}
    atp_settled = False
    for tour, code, event_id in specs:
        try:
            halves, statuses, users, settled, names = score_finals_event(
                event_id, year, code
            )
        except Exception:
            logger.exception(f"联合年终 {tour} {event_id} 结算失败")
            continue
        if tour == "WTA":
            result.wta_half = halves
            result.wta_status = statuses
        else:
            result.atp_half = halves
            result.atp_status = statuses
            atp_settled = settled
        day1[tour] = users
        result.names.update(names)
        logger.info(
            f"联合年终 {tour} 选人 {len(users)} 人，"
            f"有分 {sum(1 for value in halves.values() if value)} 人，"
            f"首日{'已结算' if settled else '未结算'}"
        )
    result.participated = day1.get("WTA", set()) & day1.get("ATP", set())
    result.locked = atp_settled
    return result


def current_event_is_finals(name: str | None, event_id: object) -> bool:
    return is_year_end_final(name, None if event_id is None else str(event_id))


def points_event_name(name: str | None, event_id: object) -> str:
    return finals_score_name(name, None if event_id is None else str(event_id))
