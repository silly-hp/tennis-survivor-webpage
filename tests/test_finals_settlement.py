"""Year-end finals: round-robin judging, match-id pairs and draw fallbacks.

Player ids, names and match ids are the real 2026 WTA Finals (event 30808)
values; the 2025 replacement case (2234 → 2235) is from that year's picks.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from draw_status import DrawPlayer, DrawStatus, parse_pick_days, parse_rr_results  # noqa: E402
from finals_settlement import (  # noqa: E402
    FinalsMatch,
    complete_day_results,
    day_matches_finished,
    fetch_pick_day_results,
    finals_conflict,
    finals_pick_outcome,
    finals_player_sets,
    match_id_pairs,
)
from live_settlement import settle_tour_scores  # noqa: E402

IDS = {
    "高芙": "328560",
    "佩古拉": "316956",
    "诺斯科娃": "329668",
    "科斯秋克": "326482",
    "萨巴莲卡": "320760",
    "米-安德烈耶娃": "331809",
    "斯维托丽娜": "316738",
    "穆霍娃": "322191",
    "替补": "399999",
}
MATCH_IDS = {
    "高芙": "2124",
    "诺斯科娃": "2124",
    "佩古拉": "2153",
    "科斯秋克": "2153",
    "萨巴莲卡": "2212",
    "米-安德烈耶娃": "2212",
    "斯维托丽娜": "2234",
    "穆霍娃": "2234",
}


def m(left: str, right: str, winner: str = "", score: str = "", names: bool = True) -> FinalsMatch:
    return FinalsMatch(
        left_id=IDS[left],
        right_id=IDS[right],
        left_name=left if names else "",
        right_name=right if names else "",
        winner_name=winner if names else "",
        score=score,
        winner_id=IDS[winner] if winner else "",
    )


def pick(day: int, player: str, alt: str = "", uid: int = 1) -> dict:
    return {
        "user_id": uid,
        "username": f"u{uid}",
        "day": day,
        "player": player,
        "fill": IDS.get(player, ""),
        "normal_match_id": MATCH_IDS.get(player, "0"),
        "player_alt": alt,
        "fill_alt": IDS.get(alt, "") if alt else "",
        "normal_match_id_alt": MATCH_IDS.get(alt, "0") if alt else "0",
    }


DAY1 = [m("科斯秋克", "佩古拉", "佩古拉", "63 63"), m("高芙", "诺斯科娃", "诺斯科娃", "63 63")]


# ── draw page parsing ───────────────────────────────────────────────────────

def _pname(name: str) -> str:
    return f'<pname data-id="{IDS[name]}"><b>{name}</b></pname>'


RR_HTML = f"""
<div class="cDrawPart" data-id="WS"><table class="cDrawBlockRow cDrawBlockRR"><tbody>
<tr><td><div>Group 2</div></td><td>{_pname("萨巴莲卡")}</td><td>{_pname("米-安德烈耶娃")}</td>
<td>{_pname("斯维托丽娜")}</td><td>{_pname("穆霍娃")}</td></tr>
<tr><td>{_pname("萨巴莲卡")}<table class="cDrawBlockRRSubTable"><tbody><tr><td>Match</td><td>1-0</td></tr></tbody></table></td>
<td></td><td><span class="unixtime"></span></td><td></td><td class="DataIn"><div>76(2) 75</div></td></tr>
<tr><td>{_pname("米-安德烈耶娃")}</td><td><span class="unixtime"></span></td><td></td>
<td class="DataIn"><div>64 60</div></td><td></td></tr>
<tr><td>{_pname("斯维托丽娜")}</td><td></td><td class="DataOut"><div>46 06</div></td><td></td>
<td><span class="unixtime"></span></td></tr>
<tr><td>{_pname("穆霍娃")}</td><td class="DataOut"><div>67(2) 57</div></td><td></td>
<td><span class="unixtime"></span></td><td></td></tr>
</tbody></table></div>
"""


def test_rr_grid_gives_winner_and_winner_side_score():
    grid = parse_rr_results(BeautifulSoup(RR_HTML, "html.parser"), "WS")
    sab_muc = grid[frozenset((IDS["萨巴莲卡"], IDS["穆霍娃"]))]
    assert sab_muc == (IDS["萨巴莲卡"], "76(2) 75")
    assert grid[frozenset((IDS["米-安德烈耶娃"], IDS["斯维托丽娜"]))] == (
        IDS["米-安德烈耶娃"],
        "64 60",
    )
    # Unplayed pairs are absent.
    assert frozenset((IDS["萨巴莲卡"], IDS["米-安德烈耶娃"])) not in grid
    assert len(grid) == 2


def test_pick_days_keep_card_match_ids():
    html = """
    <div class="cSurvivorDayPickSelector">Day 2 11/11</div>
    <div class="cSurvivorDayPickInfo" data-id="1">
      <div class="cSurvivorFillNotice">当前轮次：RR2</div>
      <div class="cSurvivorSmallCard" data-id="320760" data-name="萨巴莲卡"
           data-date="2026-11-11" data-day="2" data-fillable="0" data-normalid="2212"></div>
      <div class="cSurvivorSmallCard" data-id="326482" data-name="科斯秋克"
           data-date="2026-11-11" data-day="2" data-fillable="2" data-normalid="0"></div>
    </div>"""
    (day,) = parse_pick_days(html, 2026)
    assert day["round"] == "RR2" and day["open"]
    assert {"id": "320760", "name": "萨巴莲卡", "match_id": "2212"} in day["cards"]


# ── match-id pairs and 主备冲突 ───────────────────────────────────────────────

def test_match_id_pairs_from_cards_and_picks():
    cards = [
        {"day": 2, "cards": [
            {"id": IDS["斯维托丽娜"], "match_id": "2234"},
            {"id": IDS["穆霍娃"], "match_id": "2234"},
            {"id": IDS["高芙"], "match_id": "0"},
        ]}
    ]
    pairs = match_id_pairs([pick(1, "高芙", "佩古拉")], cards)
    assert pairs[1] == {"2124": {IDS["高芙"]}, "2153": {IDS["佩古拉"]}}
    assert pairs[2] == {"2234": {IDS["斯维托丽娜"], IDS["穆霍娃"]}}


def test_conflict_when_backup_is_todays_opponent():
    assert finals_conflict(pick(1, "高芙", "诺斯科娃"), DAY1, 1)
    assert not finals_conflict(pick(1, "高芙", "佩古拉"), DAY1, 1)


def test_conflict_survives_match_id_change_after_replacement():
    # 2025: the opponent was replaced, so the same match got a second id.
    rows = [
        {**pick(3, "米-安德烈耶娃"), "normal_match_id": "2234"},
        {**pick(3, "米-安德烈耶娃", uid=2), "normal_match_id": "2235"},
        {**pick(3, "替补", uid=3), "fill": IDS["替补"], "normal_match_id": "2235"},
    ]
    pairs = match_id_pairs(rows)
    detail = {
        **pick(3, "米-安德烈耶娃"),
        "normal_match_id": "2234",
        "player_alt": "替补",
        "fill_alt": IDS["替补"],
        "normal_match_id_alt": "2235",
    }
    # Ids differ, no results yet: only the pairs can see the conflict.
    assert finals_conflict(detail, [], 3, pairs)


# ── judging a pick ──────────────────────────────────────────────────────────

def test_pick_found_by_player_id_when_results_have_no_names():
    matches = [m("萨巴莲卡", "米-安德烈耶娃", "萨巴莲卡", "63 63", names=False)]
    outcome, _ = finals_pick_outcome(pick(2, "萨巴莲卡"), matches, day=2)
    assert outcome == "win"
    outcome, _ = finals_pick_outcome(pick(2, "米-安德烈耶娃"), matches, day=2)
    assert outcome == "loss"


def test_unlisted_pick_stays_pending_until_the_day_is_complete():
    only_one = [m("萨巴莲卡", "米-安德烈耶娃", "萨巴莲卡", "63 63")]
    detail = pick(2, "穆霍娃", "萨巴莲卡")
    outcome, _ = finals_pick_outcome(detail, only_one, day=2)
    assert outcome is None
    full = [*only_one, m("斯维托丽娜", "替补", "斯维托丽娜", "63 63")]
    outcome, effective = finals_pick_outcome(detail, full, day=2)
    assert outcome == "win" and effective["player"] == "萨巴莲卡"


def test_opponent_on_court_with_replacement_confirms_withdrawal():
    pairs = match_id_pairs([pick(2, "斯维托丽娜"), pick(2, "穆霍娃", uid=2)])
    listed = [m("斯维托丽娜", "替补")]
    outcome, effective = finals_pick_outcome(
        pick(2, "穆霍娃", "米-安德烈耶娃"), listed, day=2, pairs=pairs
    )
    # Withdrawal confirmed, so the backup is judged; her match is not listed.
    assert effective["player"] == "米-安德烈耶娃" and outcome is None


def test_first_set_retirement_hands_over_to_backup():
    matches = [m("萨巴莲卡", "米-安德烈耶娃", "米-安德烈耶娃", "41 Ret."),
               m("斯维托丽娜", "穆霍娃", "穆霍娃", "63 63")]
    outcome, effective = finals_pick_outcome(pick(2, "萨巴莲卡", "穆霍娃"), matches, day=2)
    assert (outcome, effective["player"]) == ("win", "穆霍娃")


def test_day_finished_needs_every_match():
    assert not day_matches_finished(DAY1[:1], 1)
    assert day_matches_finished(DAY1, 1)
    assert day_matches_finished([m("萨巴莲卡", "高芙", "高芙", "63 63")], 6)


# ── draw fallbacks for the results pages ────────────────────────────────────

def _draw(**kwargs) -> DrawStatus:
    by_id = {pid: DrawPlayer(player_id=pid, name=name, round="RR") for name, pid in IDS.items()}
    return DrawStatus(
        by_id=by_id,
        by_name={p.name: p for p in by_id.values()},
        day_points=[150, 300, 450, 600, 1000, 1500],
        **kwargs,
    )


def test_unfinished_result_is_filled_from_the_grid():
    grid = parse_rr_results(BeautifulSoup(RR_HTML, "html.parser"), "WS")
    draw = _draw(rr_results=grid)
    stale = {1: [m("萨巴莲卡", "穆霍娃", names=False)]}
    (match,) = complete_day_results(stale, draw)[1]
    assert match.left_name == "萨巴莲卡" and match.winner_name == "萨巴莲卡"
    assert match.score == "76(2) 75"


def test_empty_group_day_is_rebuilt_from_pairs_and_grid():
    grid = parse_rr_results(BeautifulSoup(RR_HTML, "html.parser"), "WS")
    draw = _draw(rr_results=grid)
    rows = [
        {**pick(1, "萨巴莲卡"), "normal_match_id": "2214"},
        {**pick(1, "穆霍娃", uid=2), "normal_match_id": "2214"},
    ]
    (match,) = complete_day_results({1: []}, draw, rows)[1]
    assert match.decided and match.winner_id == IDS["萨巴莲卡"]
    # A knockout day is never rebuilt from the group grid.
    assert complete_day_results({5: []}, draw, [{**pick(5, "萨巴莲卡")}])[5] == []


def test_future_days_are_not_requested():
    class Session:
        calls: list[str] = []

        def get(self, url, **_kwargs):
            self.calls.append(url)
            raise AssertionError("no request expected")

    days = [{"day": 4, "date": date(2026, 11, 13)}, {"day": 5, "date": date(2026, 11, 14)}]
    out = fetch_pick_day_results("30808", days, session=Session(), today=date(2026, 11, 11))
    assert out == {4: [], 5: []} and Session.calls == []


def test_player_sets_follow_todays_matches():
    names = list(IDS)[:8]
    live, out, remaining = finals_player_sets(
        names, {2: [m("斯维托丽娜", "穆霍娃"), m("萨巴莲卡", "米-安德烈耶娃", "萨巴莲卡", "63 63")]}, 2
    )
    assert out == ["米-安德烈耶娃"] and "穆霍娃" in live and remaining == names


# ── end to end through settle_tour_scores ───────────────────────────────────

def test_settlement_day2():
    rows = [
        pick(1, "佩古拉", uid=1), pick(2, "萨巴莲卡", uid=1),
        pick(1, "高芙", uid=2),
        pick(1, "高芙", "诺斯科娃", uid=3),
        pick(1, "诺斯科娃", uid=4), pick(2, "穆霍娃", "米-安德烈耶娃", uid=4),
        pick(1, "佩古拉", uid=5), pick(2, "穆霍娃", "萨巴莲卡", uid=5),
        pick(1, "诺斯科娃", uid=6), pick(2, "斯维托丽娜", uid=6),
    ]
    pick_days = [
        {"day": d, "date": date(2026, 11, 9 + d), "round": r, "open": False, "has_cards": False}
        for d, r in zip(range(1, 7), ["RR1", "RR2", "RR3", "RR4", "SF", "F"])
    ]
    draw = _draw(pick_days=pick_days)
    day_results = {
        1: DAY1,
        # 穆霍娃 withdrew; the alternate played 斯维托丽娜.
        2: [m("萨巴莲卡", "米-安德烈耶娃", "萨巴莲卡", "63 63"),
            m("斯维托丽娜", "替补", "替补", "63 63", names=False)],
    }
    day_results = complete_day_results(day_results, draw, rows)
    settled, counts, _bye, play_day, pending, backups = settle_tour_scores(
        None, pd.DataFrame(rows), draw, day_results=day_results
    )
    by_user = settled.set_index("user_id")
    assert play_day == 2 and not pending
    assert by_user.loc[1, "fill_status"] == "存活" and by_user.loc[1, "score"] == 300
    assert by_user.loc[2, "fill_status"] == "球员输球"
    assert by_user.loc[2, "killer"] == "高芙"
    assert by_user.loc[3, "fill_status"] == "自杀(主备冲突)"
    # Backup 米-安德烈耶娃 lost.
    assert by_user.loc[4, "fill_status"] == "球员输球"
    assert by_user.loc[4, "killer"] == "米-安德烈耶娃"
    # Backup 萨巴莲卡 won.
    assert by_user.loc[5, "fill_status"] == "存活" and by_user.loc[5, "score"] == 300
    # Lost to the alternate, matched by player id (no names on the page).
    assert by_user.loc[6, "fill_status"] == "球员输球"
    assert {e["backup"] for e in backups} == {"米-安德烈耶娃", "萨巴莲卡"}
    assert counts["suicide"] == 1
