"""Year-end finals settlement helpers.

Group days 1–4 and knockout days 5–6 are judged from that day's singles
results, not from a knockout bracket. Only the pre-event champion-ranking
top 8 (ties at 8th included) stay in the field.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd
import requests

from draw_status import USER_AGENT, retirement_backup_allowed
from logger import get_logger
from points_calculation import calculate_points, parse_events

logger = get_logger(__name__)

# Cities that are the finals and nothing else. 印第安维尔斯 is also the
# March 1000 (WTA 30609 / ATP 20404), so the city alone is not a final.
FINALS_ONLY_CITIES = frozenset({"都灵", "利雅得"})
# 30808 stayed the WTA finals id when the city moved 利雅得 → 印第安维尔斯.
WTA_FINALS_EVENT_IDS = frozenset({"30808"})
ATP_FINALS_EVENT_IDS = frozenset({"20605"})
# Points key for the 2026 WTA finals. Not 印第安维尔斯, so the March 1000 stays.
WTA_FINALS_POINTS_NAME = "印第安维尔斯年终"
TOP_N = 8
KNOCKOUT_FROM = 5

_PLAYER_CLASS_RE = re.compile(r"cResultPlayer([A-Za-z0-9]+)")
_OPEN_STAT_RE = re.compile(
    r'open_stat\(\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,'
    r'\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"'
)
_RET_RE = re.compile(r"\bRet\.?\b|退赛", re.I)
_WO_RE = re.compile(r"\bW\s*/\s*O\b|\bWO\b", re.I)


def is_year_end_final(event_name: str | None = None, event_id: str | None = None) -> bool:
    """True for the year-end finals, including 2026 WTA at Indian Wells.

    Event 30808 is the finals even though its city is 印第安维尔斯.
    The March 1000 keeps that city and is not a final.
    """
    eid = str(event_id or "").strip()
    if eid in WTA_FINALS_EVENT_IDS or eid in ATP_FINALS_EVENT_IDS:
        return True
    return str(event_name or "").strip() in FINALS_ONLY_CITIES


def finals_score_name(event_name: str | None = None, event_id: str | None = None) -> str:
    """Name used in the points table for this event.

    The 2026 WTA finals share a city with the March 1000. Their points use
    a separate key so they do not replace that 1000.
    """
    name = str(event_name or "").strip()
    if (
        str(event_id or "").strip() in WTA_FINALS_EVENT_IDS
        and name == "印第安维尔斯"
    ):
        return WTA_FINALS_POINTS_NAME
    return name


def _as_key(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        try:
            float(text)
            return text[:-2]
        except ValueError:
            return text
    return text


@dataclass(frozen=True)
class FinalsMatch:
    left_id: str
    right_id: str
    left_name: str
    right_name: str
    winner_name: str = ""
    score: str = ""
    live: bool = False

    @property
    def decided(self) -> bool:
        return bool(self.winner_name) and not self.live


def same_phase_names(recorded: list[tuple[int, str]], day: int) -> list[str]:
    """Picks already used in this phase. Days 1–4 and days 5–6 are separate."""
    knock = int(day) >= KNOCKOUT_FROM
    return [name for prev, name in recorded if (int(prev) >= KNOCKOUT_FROM) == knock and name]


def eligible_user_ids(
    race_df: pd.DataFrame | None,
    tour: str,
    event_name: str,
    event_id: str | None = None,
) -> set[str]:
    """Pre-event single-tour champion ranking: top 8, plus anyone tied with 8th.

    This event's points are removed before the cutoff, so scoring inside the
    finals does not change who is eligible.
    """
    if race_df is None or getattr(race_df, "empty", True):
        return set()
    if "user_id" not in race_df.columns or "details_text" not in race_df.columns:
        return set()
    scored: list[tuple[str, int]] = []
    for uid, details in zip(race_df["user_id"], race_df["details_text"]):
        key = _as_key(uid)
        if not key:
            continue
        parsed = parse_events(details if isinstance(details, str) else "")
        # Drop this finals only. 印第安维尔斯 is the March 1000 and stays.
        strip = finals_score_name(event_name, event_id)
        if strip and strip != "印第安维尔斯":
            parsed.pop(strip, None)
        points = int(calculate_points(parsed, tour=tour)["total_points"])
        scored.append((key, points))
    if not scored:
        return set()
    order = sorted((points for _uid, points in scored), reverse=True)
    cutoff = order[TOP_N - 1] if len(order) >= TOP_N else order[-1]
    return {uid for uid, points in scored if points >= cutoff}


def filter_eligible(df: pd.DataFrame | None, eligible: set[str]) -> pd.DataFrame | None:
    """Drop rows whose user is outside the finals field. Empty eligible keeps the frame."""
    if df is None or getattr(df, "empty", True) or not eligible:
        return df
    if "user_id" not in df.columns:
        return df
    keys = df["user_id"].map(_as_key)
    return df.loc[keys.isin(eligible)].copy()


def day_matches_finished(matches: list[FinalsMatch] | None) -> bool:
    if not matches:
        return False
    return all(match.decided for match in matches)


def match_for(name: str, matches: list[FinalsMatch] | None) -> FinalsMatch | None:
    label = str(name or "").strip()
    if not label or label == "轮空":
        return None
    for match in matches or []:
        if label in {match.left_name, match.right_name}:
            return match
    return None


def _alt_detail(detail: dict) -> dict | None:
    alt = str(detail.get("player_alt") or "").strip()
    if not alt:
        return None
    out = dict(detail)
    fill_alt = str(detail.get("fill_alt") or "").strip()
    out["player"] = alt
    out["fill"] = fill_alt if fill_alt and fill_alt != "0" else detail.get("fill")
    match_alt = detail.get("normal_match_id_alt")
    if str(match_alt or "").strip() not in {"", "0"}:
        out["normal_match_id"] = match_alt
    out["player_alt"] = ""
    out["fill_alt"] = ""
    out["normal_match_id_alt"] = ""
    return out


def finals_pick_outcome(
    detail: dict,
    matches: list[FinalsMatch] | None,
    *,
    allow_backup: bool = True,
) -> tuple[str | None, dict]:
    """Win if the picked player won today's match. Pending until that match ends.

    An empty match list means the results page was not loaded: stay pending
    instead of eliminating the field. A primary who is not in today's matches
    is treated as withdrawn, so the backup is judged when one was submitted.
    """
    pick = str(detail.get("player") or "").strip()
    if not matches:
        return None, detail
    if not pick or pick == "轮空":
        return "loss", detail
    match = match_for(pick, matches)
    if match is None:
        if allow_backup:
            alt = _alt_detail(detail)
            if alt is not None:
                return finals_pick_outcome(alt, matches, allow_backup=False)
        return "loss", detail
    if not match.decided:
        return None, detail
    if match.winner_name == pick:
        return "win", detail
    if allow_backup and retirement_backup_allowed(match.score):
        alt = _alt_detail(detail)
        if alt is not None:
            return finals_pick_outcome(alt, matches, allow_backup=False)
    return "loss", detail


def _set_count(row) -> int:
    count = 0
    for node in row.select("div"):
        classes = node.get("class") or []
        if "hidden" in classes:
            continue
        text = node.get_text(strip=True)
        if text and text[0].isdigit():
            count += 1
    return count


def _match_score(match_node, rows) -> str:
    text = match_node.get_text(" ", strip=True)
    sets = max((_set_count(row) for row in rows), default=0)
    if sets >= 2:
        return "63 63"
    if _WO_RE.search(text):
        return "W/O"
    if _RET_RE.search(text):
        return "41 Ret." if sets == 1 else "Ret."
    return ""


def parse_result_matches(html: str, event_id: str | int) -> list[FinalsMatch]:
    """Singles matches for one event on a results page."""
    from bs4 import BeautifulSoup

    event = str(event_id or "").strip()
    if not event or not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    matches: list[FinalsMatch] = []
    for node in soup.select("div.cResultMatch"):
        if str(node.get("is-double") or "") == "1":
            continue
        classes = node.get("class") or []
        if f"cResultMatchTour{event}" not in classes:
            continue
        stat = node.select_one("a[onclick*='open_stat']")
        found = _OPEN_STAT_RE.search(stat.get("onclick") or "") if stat else None
        if found:
            left_id, right_id = found.group(5), found.group(6)
            left_name, right_name = found.group(7), found.group(8)
        else:
            ids = _PLAYER_CLASS_RE.findall(" ".join(classes))
            if len(ids) < 2:
                continue
            left_id, right_id = ids[0], ids[1]
            left_name, right_name = "", ""
        rows = node.select("tr")
        winner_name = ""
        live = str(node.get("match-status") or "") == "1" or any(
            "Live" in str(item) for item in classes
        )
        for row, name in zip(rows, (left_name, right_name)):
            row_classes = " ".join(row.get("class") or [])
            if "cResultMatchMidTableRowWinner" in row_classes and name:
                winner_name = name
                live = False
        matches.append(
            FinalsMatch(
                left_id=left_id,
                right_id=right_id,
                left_name=left_name,
                right_name=right_name,
                winner_name=winner_name,
                score=_match_score(node, rows),
                live=live,
            )
        )
    return matches


def fetch_pick_day_results(
    event_id: str | int,
    pick_days: list[dict] | None,
    *,
    session: requests.Session | None = None,
    timeout: int = 60,
) -> dict[int, list[FinalsMatch]]:
    """Results for each survivor pick day. A redirected date is ignored."""
    sess = session or requests.Session()
    out: dict[int, list[FinalsMatch]] = {}
    for item in pick_days or []:
        day = int(item.get("day") or 0)
        date = item.get("date")
        if day <= 0 or not date:
            continue
        iso = date.isoformat() if hasattr(date, "isoformat") else str(date)[:10]
        url = f"https://www.live-tennis.cn/zh/result/{iso}"
        try:
            response = sess.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
        except requests.RequestException as err:
            logger.warning(f"Finals results {iso} failed: {err}")
            out[day] = []
            continue
        if iso not in str(response.url):
            logger.info(f"Finals results {iso} redirected to {response.url}; skip")
            out[day] = []
            continue
        matches = parse_result_matches(response.text, event_id)
        out[day] = matches
        logger.info(f"Finals day {day} {iso}: {len(matches)} singles")
    return out
