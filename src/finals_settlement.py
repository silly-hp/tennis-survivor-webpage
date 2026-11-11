"""Year-end finals settlement helpers.

Group days 1–4 and knockout days 5–6 are judged from that day's singles
results, not from a knockout bracket. Only the pre-event champion-ranking
top 8 (ties at 8th included) stay in the field.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date as date_type, timedelta

import pandas as pd
import requests

from draw_status import USER_AGENT, beijing_now, retirement_backup_allowed
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
    winner_id: str = ""

    @property
    def decided(self) -> bool:
        return bool(self.winner_name or self.winner_id) and not self.live

    def side(self, player_id: str = "", name: str = "") -> str:
        """``"left"`` / ``"right"`` for the given player, else ``""``.

        Names are tried first; the player id covers a results page whose
        names are missing or spelled differently.
        """
        label = str(name or "").strip()
        if label:
            if label == self.left_name:
                return "left"
            if label == self.right_name:
                return "right"
        pid = _player_id(player_id)
        if pid:
            if pid == self.left_id:
                return "left"
            if pid == self.right_id:
                return "right"
        return ""

    def won_by(self, player_id: str = "", name: str = "") -> bool:
        side = self.side(player_id, name)
        if not side or not self.decided:
            return False
        if self.winner_id:
            return self.winner_id == (self.left_id if side == "left" else self.right_id)
        return self.winner_name == (self.left_name if side == "left" else self.right_name)


def _player_id(value: object) -> str:
    key = _as_key(value)
    return "" if key in {"", "0"} else key


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


def expected_match_count(day: int) -> int:
    """Singles per finals day: two group matches, two semifinals, one final."""
    return 1 if int(day) > KNOCKOUT_FROM else 2


def day_complete(matches: list[FinalsMatch] | None, day: int = 0) -> bool:
    """Every match of the day is listed. ``day=0`` (unknown) trusts the list."""
    if not matches:
        return False
    if int(day or 0) <= 0:
        return True
    return len(matches) >= expected_match_count(day)


def day_matches_finished(matches: list[FinalsMatch] | None, day: int = 0) -> bool:
    if not day_complete(matches, day):
        return False
    return all(match.decided for match in matches)


def _loser_name(match: FinalsMatch) -> str:
    if not match.decided:
        return ""
    if match.won_by(match.left_id, match.left_name):
        return match.right_name
    if match.won_by(match.right_id, match.right_name):
        return match.left_name
    return ""


def finals_player_sets(
    draw_names: list[str],
    day_results: dict[int, list[FinalsMatch]] | None,
    day: int,
) -> tuple[list[str], list[str], list[str]]:
    """(live, eliminated, remaining) player names for the pick summary.

    The draw entry list's 淘汰 flag means nothing in round robin, so the
    status comes from today's matches: the loser of a finished match is
    淘汰, both sides of an unfinished one are 未完赛. Remaining is the whole
    field during the group stage; from the semifinals on it is the players
    on the knockout days minus anyone who lost there.
    """
    results = day_results or {}
    live: list[str] = []
    eliminated: list[str] = []
    for match in results.get(int(day)) or []:
        if match.decided:
            loser = _loser_name(match)
            if loser:
                eliminated.append(loser)
        else:
            live.extend(name for name in (match.left_name, match.right_name) if name)
    names = [str(name).strip() for name in draw_names or [] if str(name or "").strip()]
    remaining = names
    if int(day) >= KNOCKOUT_FROM:
        knock = [
            match
            for key, matches in results.items()
            if int(key) >= KNOCKOUT_FROM
            for match in matches or []
        ]
        players = {
            name for match in knock for name in (match.left_name, match.right_name) if name
        }
        if players:
            out = {_loser_name(match) for match in knock} - {""}
            remaining = [name for name in names if name in players and name not in out]
    return (
        list(dict.fromkeys(live)),
        list(dict.fromkeys(eliminated)),
        list(dict.fromkeys(remaining)),
    )


def match_for(
    name: str,
    matches: list[FinalsMatch] | None,
    player_id: object = None,
) -> FinalsMatch | None:
    """Today's match for a pick: by name first, then by player id."""
    label = str(name or "").strip()
    if label == "轮空":
        return None
    pid = _player_id(player_id)
    if not label and not pid:
        return None
    for match in matches or []:
        if label and label in {match.left_name, match.right_name}:
            return match
    if pid:
        for match in matches or []:
            if pid in {match.left_id, match.right_id}:
                return match
    return None


MatchPairs = dict[int, dict[str, set[str]]]


def match_id_pairs(
    detail_rows: list[dict] | None,
    pick_days: list[dict] | None = None,
) -> MatchPairs:
    """Day → match id → player ids that carry that id.

    A finals match id is ``2`` + group + two group slots in round robin
    (``2212``, a replacement takes slot 5 as in ``2153``) and ``2`` + round
    + match number in the knockout (``2101`` SF1, ``2201`` F). The id does
    not name the players, so they come from the survivor page cards of the
    open day and from every submitted primary / backup. When a player is
    replaced mid-group the same match gets a new id (2025: ``2234`` →
    ``2235``), so ids are only compared within one day.
    """
    out: MatchPairs = {}

    def _add(day: object, match_id: object, player_id: object) -> None:
        try:
            key_day = int(day or 0)
        except (TypeError, ValueError):
            return
        mid, pid = _player_id(match_id), _player_id(player_id)
        if key_day <= 0 or not mid or not pid:
            return
        out.setdefault(key_day, {}).setdefault(mid, set()).add(pid)

    for item in pick_days or []:
        for card in item.get("cards") or []:
            _add(item.get("day"), card.get("match_id"), card.get("id"))
    for row in detail_rows or []:
        _add(row.get("day"), row.get("normal_match_id"), row.get("fill"))
        _add(row.get("day"), row.get("normal_match_id_alt"), row.get("fill_alt"))
    return out


def _opponent_ids(pairs: MatchPairs | None, day: int, player_id: object) -> set[str]:
    pid = _player_id(player_id)
    if not pid:
        return set()
    found: set[str] = set()
    for players in (pairs or {}).get(int(day or 0), {}).values():
        if pid in players:
            found |= players - {pid}
    return found


def _absent_confirmed(
    detail: dict,
    matches: list[FinalsMatch] | None,
    day: int,
    pairs: MatchPairs | None,
) -> bool:
    """The pick is not in today's matches because they really withdrew.

    True once the day's match list is complete, or when the scheduled
    opponent is on court against someone else (replacement). Otherwise the
    results page may just not list the match yet, so stay pending.
    """
    if day_complete(matches, day):
        return True
    for opp in _opponent_ids(pairs, day, detail.get("fill")):
        if match_for("", matches, opp) is not None:
            return True
    return False


def primary_state(
    detail: dict,
    matches: list[FinalsMatch] | None,
    day: int = 0,
    pairs: MatchPairs | None = None,
) -> tuple[str, FinalsMatch | None]:
    """Where the primary pick stands on ``day``.

    ``won`` / ``lost`` / ``early`` (lost by W/O or retirement inside set 1)
    / ``absent`` (withdrew before the match) / ``pending`` (not decided or
    not listed yet).
    """
    pick = str(detail.get("player") or "").strip()
    match = match_for(pick, matches, detail.get("fill"))
    if match is None:
        if matches and _absent_confirmed(detail, matches, day, pairs):
            return "absent", None
        return "pending", None
    if not match.decided:
        return "pending", match
    if match.won_by(detail.get("fill"), pick):
        return "won", match
    if retirement_backup_allowed(match.score):
        return "early", match
    return "lost", match


def finals_conflict(
    detail: dict,
    matches: list[FinalsMatch] | None,
    day: int = 0,
    pairs: MatchPairs | None = None,
) -> bool:
    """Primary and backup are the two sides of one match (自杀(主备冲突)).

    Uses today's matches and the day's match-id pairs by player id, so a
    match whose id changed after a replacement is still caught.
    """
    pick = str(detail.get("player") or "").strip()
    alt = str(detail.get("player_alt") or "").strip()
    if not pick or not alt or "轮空" in {pick, alt} or pick == alt:
        return False
    first = match_for(pick, matches, detail.get("fill"))
    if first is not None and first.side(detail.get("fill_alt"), alt):
        return True
    alt_id = _player_id(detail.get("fill_alt"))
    return bool(alt_id) and alt_id in _opponent_ids(pairs, day, detail.get("fill"))


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
    day: int = 0,
    pairs: MatchPairs | None = None,
    allow_backup: bool = True,
) -> tuple[str | None, dict]:
    """Win if the picked player won today's match. Pending until that match ends.

    An empty match list means the results page was not loaded: stay pending
    instead of eliminating the field. A primary who is not in today's matches
    counts as withdrawn only once the day's list is complete or the opponent
    is on court against a replacement; the backup is then judged when one
    was submitted. W/O or retirement inside set 1 also hands over to it.
    """
    pick = str(detail.get("player") or "").strip()
    if not matches:
        return None, detail
    if not pick or pick == "轮空":
        return "loss", detail
    state, _match = primary_state(detail, matches, day, pairs)
    if state == "pending":
        return None, detail
    if state == "won":
        return "win", detail
    if allow_backup and state in {"absent", "early"}:
        alt = _alt_detail(detail)
        if alt is not None:
            return finals_pick_outcome(
                alt, matches, day=day, pairs=pairs, allow_backup=False
            )
    return "loss", detail


def complete_day_results(
    day_results: dict[int, list[FinalsMatch]] | None,
    draw,
    detail_rows: list[dict] | None = None,
) -> dict[int, list[FinalsMatch]] | None:
    """Fill gaps in the results pages from the draw.

    * Missing names (no stat link on the results page) come from the draw.
    * A group match the results page still shows as unfinished takes its
      result from the round-robin grid, which has no dates and so cannot
      miss a match that ran past midnight.
    * A group day whose results page gave nothing is rebuilt from the
      day's match-id pairs plus the grid; such a list may be short, so an
      absent pick there stays pending.
    """
    if day_results is None or draw is None:
        return day_results
    by_id = getattr(draw, "by_id", None) or {}
    names = {pid: str(p.name or "").strip() for pid, p in by_id.items()}
    grid = getattr(draw, "rr_results", None) or {}

    def _from_grid(match: FinalsMatch, day: int) -> FinalsMatch:
        left = match.left_name or names.get(match.left_id, "")
        right = match.right_name or names.get(match.right_id, "")
        winner_name = match.winner_name or names.get(match.winner_id, "")
        out = replace(match, left_name=left, right_name=right, winner_name=winner_name)
        if out.decided or out.live or day >= KNOCKOUT_FROM:
            return out
        hit = grid.get(frozenset((match.left_id, match.right_id)))
        if not hit:
            return out
        winner_id, score = hit
        return replace(
            out, winner_id=winner_id, winner_name=names.get(winner_id, ""), score=score
        )

    pairs = match_id_pairs(detail_rows, getattr(draw, "pick_days", None))
    filled: dict[int, list[FinalsMatch]] = {}
    for day, matches in day_results.items():
        day = int(day)
        fixed = [_from_grid(match, day) for match in matches or []]
        if not fixed and day < KNOCKOUT_FROM:
            for players in pairs.get(day, {}).values():
                if len(players) != 2:
                    continue
                left_id, right_id = sorted(players)
                fixed.append(
                    _from_grid(FinalsMatch(left_id, right_id, "", ""), day)
                )
            if fixed:
                logger.info(f"Finals day {day}: rebuilt {len(fixed)} matches from draw")
        filled[day] = fixed
    return filled


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
        winner_id = ""
        live = str(node.get("match-status") or "") == "1" or any(
            "Live" in str(item) for item in classes
        )
        for row, name, pid in zip(rows, (left_name, right_name), (left_id, right_id)):
            row_classes = " ".join(row.get("class") or [])
            if "cResultMatchMidTableRowWinner" in row_classes:
                winner_name = name
                winner_id = pid
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
                winner_id=winner_id,
            )
        )
    return matches


def fetch_pick_day_results(
    event_id: str | int,
    pick_days: list[dict] | None,
    *,
    session: requests.Session | None = None,
    timeout: int = 60,
    today: date_type | None = None,
) -> dict[int, list[FinalsMatch]]:
    """Results for each survivor pick day. A redirected date is ignored.

    Days dated after tomorrow (Beijing) cannot have been played and are
    left empty without a request; pick days use the venue's date, which is
    never ahead of Beijing.
    """
    sess = session or requests.Session()
    out: dict[int, list[FinalsMatch]] = {}
    last = (today or beijing_now().date()) + timedelta(days=1)
    for item in pick_days or []:
        day = int(item.get("day") or 0)
        date = item.get("date")
        if day <= 0 or not date:
            continue
        iso = date.isoformat() if hasattr(date, "isoformat") else str(date)[:10]
        if iso > last.isoformat():
            out[day] = []
            continue
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
