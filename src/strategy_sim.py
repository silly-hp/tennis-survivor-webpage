"""Offline survivor strategies for 2024–2026.

Picks come from tennis-data (pre-match rank and odds). The 2024 Olympics are
not in those workbooks, so they use a saved match file with the same fields.
Event scores use this site's published day ladder and the best-18 rule.
Olympic points sit on top of the 18. Year-end finals are left out. Each pick
day is the site's own date and round, not a raw count of calendar dates.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from openpyxl import load_workbook

from finals_settlement import is_year_end_final
from live_settlement import day1_out_points
from logger import get_logger
from points_calculation import (
    ATP_YEAR_END_FINALS,
    WTA_YEAR_END_FINAL,
    calculate_points,
)

logger = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
TENNIS_ROOT = Path("/Users/yinzechen/程序/幸存者AI/data/raw")
DRAWS = ROOT / "data" / "event_draws"
SCORES = ROOT / "data" / "event_scores"
PLAYER_EVENTS = ROOT / "data" / "player_events.json"
OUT_JSON = ROOT / "data" / "strategy_sim.json"
NAMES_JSON = ROOT / "data" / "strategy_names.json"
OLYMPIC_JSON = ROOT / "data" / "olympic_2024.json"
PICK_DAYS = ROOT / "data" / "event_pick_days"
# Site round label -> tennis-data round. A trailing /1 or /2 is the same round.
TENNIS_ROUND = {
    "1st Round": "R1",
    "2nd Round": "R2",
    "3rd Round": "R3",
    "4th Round": "R4",
    "Quarterfinals": "QF",
    "Semifinals": "SF",
    "The Final": "F",
}
YEARS = (2024, 2025, 2026)
MAIN_ROUNDS = {
    "1st Round",
    "2nd Round",
    "3rd Round",
    "4th Round",
    "Quarterfinals",
    "Semifinals",
    "The Final",
}
SKIP_CITIES = set(ATP_YEAR_END_FINALS) | set(WTA_YEAR_END_FINAL)
STRATEGIES = (
    ("rank", "排名最高"),
    ("favorite", "最被看好"),
)

# Tennis-data tournament title -> site city (or cities, when the English
# name covers both Canadian stops).
EN_CITIES: dict[str, tuple[str, ...]] = {
    "Australian Open": ("澳网",),
    "French Open": ("法网",),
    "Wimbledon": ("温网",),
    "US Open": ("美网",),
    "BNP Paribas Open": ("印第安维尔斯",),
    "Miami Open": ("迈阿密",),
    "Monte Carlo Masters": ("蒙特卡洛",),
    "Mutua Madrid Open": ("马德里",),
    "Internazionali BNL d'Italia": ("罗马",),
    "Canadian Open": ("蒙特利尔", "多伦多"),
    "Western & Southern Financial Group Masters": ("辛辛那提",),
    "Western & Southern Financial Group Women's Open": ("辛辛那提",),
    "Shanghai Masters": ("上海",),
    "BNP Paribas Masters": ("巴黎",),
    "Qatar Exxon Mobil Open": ("多哈",),
    "Qatar Open": ("多哈",),
    "Dubai Tennis Championships": ("迪拜",),
    "Dubai Duty Free Tennis Championships": ("迪拜",),
    "China Open": ("北京",),
    "Wuhan Open": ("武汉",),
    "Halle Open": ("哈雷",),
    "Hamburg Open": ("汉堡",),
    "Stuttgart Open": ("斯图加特",),
    "Porsche Tennis Grand Prix": ("斯图加特",),
    "Eastbourne International": ("伊斯特本",),
    "Eastbourne Open": ("伊斯特本",),
    "Rothesay International": ("伊斯特本",),
    "Citi Open": ("华盛顿",),
    "Winston-Salem Open at Wake Forest University": ("温斯顿塞勒姆",),
    "Hangzhou Open": ("杭州",),
    "Almaty Open": ("阿拉木图",),
    "Swiss Indoors": ("巴塞尔",),
    "Belgrade Open": ("贝尔格莱德",),
    "Hong Kong Tennis Open": ("香港",),
    "Adelaide International": ("阿德莱德",),
    "Brisbane International": ("布里斯班",),
    "Open Sud de France": ("蒙彼利埃",),
    "Dallas Open": ("达拉斯",),
    "Open 13": ("马赛",),
    "Tiriac Open": ("布加勒斯特",),
    "Mallorca Championships": ("马洛卡",),
    "Los Cabos Open": ("洛斯卡沃斯",),
    "Charleston Open": ("查尔斯顿",),
    "Internationaux de Strasbourg": ("斯特拉斯堡",),
    "Rosmalen Grass Court Championships": ("斯海尔托亨博斯",),
    "German Open": ("柏林",),
    "Bad Homburg Open": ("巴特洪堡",),
    "Queen's Club Championships": ("伦敦",),
    "Internazionali Femminili di Palermo": ("帕勒莫",),
    "Monterrey Open": ("蒙特雷",),
    "Korea Open": ("首尔",),
    "Ningbo Open": ("宁波",),
    "Japan Open": ("东京",),
    "Japan Open Tennis Championships": ("东京",),
    "Toray Pan Pacific Open Tennis Tournament": ("东京",),
    "Jiangxi Open": ("九江",),
    "Tennis in the Land": ("克利夫兰",),
    "Prague Open": ("布拉格",),
    "Singapore Open": ("新加坡",),
    "Abu Dhabi WTA Women's Tennis Open": ("阿布扎比",),
    "ATX Open": ("奥斯汀",),
    "Hobart International": ("霍巴特",),
    "ABN AMRO World Tennis Tournament": ("鹿特丹",),
    "Abierto Mexicano": ("阿卡普尔科",),
    "Merida Open": ("梅里达",),
    "U.S.Men's Clay Court Championships": ("休斯顿",),
    "Ladies Linz Open": ("林茨",),
    "BMW Open": ("慕尼黑",),
    "Suisse Open Gstaad": ("格施塔德",),
    "Athens Open": ("雅典",),
    "Generali Open": ("基茨比厄尔",),
    "Guadalajara Open": ("瓜达拉哈拉",),
}

# One English title covers two cities. Location picks the city.
PLACE_CITIES: dict[str, dict[str, str]] = {
    "European Open": {"Hamburg": "汉堡", "Antwerp": "安特卫普"},
}

# Anchors confirmed against the site's Chinese draw names. Further names are
# filled from a match that already has one side translated.
NAME_SEED: dict[str, str] = {
    "Alcaraz C.": "阿尔卡拉斯",
    "Sinner J.": "辛纳",
    "Djokovic N.": "德约科维奇",
    "Medvedev D.": "梅德韦杰夫",
    "Zverev A.": "亚-兹韦列夫",
    "Draper J.": "德雷珀",
    "Norrie C.": "诺里",
    "Fils A.": "菲斯",
    "Auger-Aliassime F.": "阿利亚西姆",
    "Tiafoe F.": "蒂亚福",
    "Davidovich Fokina A.": "达维多维奇",
    "Fonseca J.": "丰塞卡",
    "Michelsen A.": "米克尔森",
    "Tien L.": "勒纳-钱",
    "Bublik A.": "布勃利克",
    "Korda S.": "科达",
    "Baez S.": "巴埃斯",
    "Fritz T.": "弗里茨",
    "Ruud C.": "鲁德",
    "Shelton B.": "谢尔顿",
    "Paul T.": "保罗",
    "Khachanov K.": "哈恰诺夫",
    "Shapovalov D.": "沙波瓦洛夫",
    "Rublev A.": "卢布列夫",
    "Diallo G.": "迪亚洛",
    "Monfils G.": "孟菲尔斯",
    "Kecmanovic M.": "凯茨曼诺维奇",
    "Opelka R.": "奥佩尔卡",
    "Popyrin A.": "波佩林",
    "Nakashima B.": "中岛布兰登",
    "Cobolli F.": "科博利",
    "Berrettini M.": "贝雷蒂尼",
    "Mannarino A.": "曼纳里诺",
    "Struff J.": "施特鲁夫",
    "Tsitsipas S.": "西西帕斯",
    "Dimitrov G.": "迪米特洛夫",
    "De Minaur A.": "德米纳尔",
    "Rune H.": "鲁内",
    "Musetti L.": "穆塞蒂",
    "Hurkacz H.": "胡尔卡奇",
    "Griekspoor T.": "格里科斯普",
    "Humbert U.": "安贝尔",
    "Cerundolo F.": "弗-塞伦多洛",
    "Cerundolo J.": "胡-塞伦多洛",
    "Mensik J.": "门希克",
    "Machac T.": "马哈奇",
    "Lehecka J.": "莱赫奇卡",
    "Marozsan F.": "毛罗然",
    "Etcheverry T.": "埃切韦里",
    "Navone M.": "纳沃内",
    "Bautista Agut R.": "包蒂斯塔-阿古特",
    "Hijikata R.": "土方凛辉",
    "Bergs Z.": "贝尔赫斯",
    "Kovacevic A.": "科瓦切维奇",
    "Fearnley J.": "费恩利",
    "Fucsovics M.": "富乔维奇",
    "O Connell C.": "奥康尼尔",
    "Brooksby J.": "布鲁克斯比",
    "Altmaier D.": "阿尔特迈尔",
    "Cilic M.": "西里奇",
    "Arnaldi M.": "阿纳尔迪",
    "McDonald M.": "麦克唐纳",
    "Darderi L.": "达尔德里",
    "Sabalenka A.": "萨巴莲卡",
    "Samsonova L.": "萨姆索诺娃",
    "Paolini J.": "保利尼",
    "Gauff C.": "高芙",
    "Bencic B.": "本西奇",
    "Vekic D.": "维基奇",
    "Keys M.": "凯斯",
    "Rybakina E.": "雷巴金娜",
    "Andreeva M.": "米-安德烈耶娃",
    "Svitolina E.": "斯维托丽娜",
    "Pegula J.": "佩古拉",
    "Zheng Q.": "郑钦文",
    "Kostyuk M.": "科斯秋克",
    "Muchova K.": "穆霍娃",
    "Swiatek I.": "希维昂泰克",
    "Kessler M.": "凯斯勒",
    "Blinkova A.": "布林科娃",
    "Alexandrova E.": "亚历山德罗娃",
    "Kudermetova P.": "波-库德梅托娃",
    "Kudermetova V.": "库德梅托娃",
    "Haddad Maia B.": "玛雅",
    "Frech M.": "弗雷希",
    "Kenin S.": "克宁",
    "Kasatkina D.": "卡萨特金娜",
    "Fernandez L.": "蕾-费尔南德斯",
    "Raducanu E.": "拉杜卡努",
    "Kalinskaya A.": "卡林斯卡娅",
    "Sakkari M.": "萨卡里",
    "Anisimova A.": "阿尼西莫娃",
    "Navarro E.": "埃-纳瓦罗",
    "Mertens E.": "梅尔滕斯",
    "Potapova A.": "波塔波娃",
    "Bouzkova M.": "鲍兹科娃",
    "Osaka N.": "大坂直美",
    "Kvitova P.": "科维托娃",
    "Tauson C.": "陶森",
    "Boulter K.": "博尔特",
    "Joint M.": "乔因特",
    "Krueger A.": "克鲁格",
    "Wang X.": "王欣瑜",
    "Ostapenko J.": "奥斯塔彭科",
    "Stearns P.": "斯特恩斯",
    "Collins D.": "科林斯",
    "Azarenka V.": "阿扎伦卡",
    "Sun L.": "孙璐璐",
    "Noskova L.": "诺斯科娃",
    "Lys E.": "利斯",
    "Cocciaretto E.": "科恰雷托",
    "Siniakova K.": "西尼亚科娃",
    "Putintseva Y.": "普汀塞娃",
    "Jabeur O.": "贾贝乌尔",
    "Yastremska D.": "亚斯特列姆斯卡",
    "Yuan Y.": "袁悦",
    "Garcia C.": "加西亚",
}


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "")[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _as_int(value: Any) -> Optional[int]:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _as_odds(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 1 else None


def _odds_pair(row: tuple, idx: dict[str, int]) -> Optional[tuple[float, float]]:
    for win_key, lose_key in (
        ("PSW", "PSL"),
        ("B365W", "B365L"),
        ("MaxW", "MaxL"),
        ("AvgW", "AvgL"),
    ):
        if win_key not in idx or lose_key not in idx:
            continue
        win = _as_odds(row[idx[win_key]])
        lose = _as_odds(row[idx[lose_key]])
        if win and lose:
            return win, lose
    return None


def load_tennis(tour: str, year: int) -> list[dict[str, Any]]:
    """Main-draw matches with pre-match rank and decimal odds."""
    path = TENNIS_ROOT / tour / f"{year}.xlsx"
    if not path.exists():
        logger.warning(f"tennis-data missing: {path}")
        return []
    book = load_workbook(path, read_only=True, data_only=True)
    sheet = book.active
    rows = sheet.iter_rows(values_only=True)
    header = [str(cell) if cell else "" for cell in next(rows)]
    idx = {name: pos for pos, name in enumerate(header)}
    matches: list[dict[str, Any]] = []
    for row in rows:
        round_name = str(row[idx["Round"]] or "")
        if round_name not in MAIN_ROUNDS:
            continue
        played = _as_date(row[idx["Date"]])
        odds = _odds_pair(row, idx)
        winner = str(row[idx["Winner"]] or "").strip()
        loser = str(row[idx["Loser"]] or "").strip()
        if played is None or odds is None or not winner or not loser:
            continue
        matches.append(
            {
                "tournament": str(row[idx["Tournament"]] or "").strip(),
                "location": str(row[idx["Location"]] or "").strip() if "Location" in idx else "",
                "date": played,
                "round": round_name,
                "winner": winner,
                "loser": loser,
                "w_rank": _as_int(row[idx["WRank"]]) if "WRank" in idx else None,
                "l_rank": _as_int(row[idx["LRank"]]) if "LRank" in idx else None,
                "w_odds": odds[0],
                "l_odds": odds[1],
            }
        )
    book.close()
    return matches


def _text(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower() in {"nan", "nat", "none"}:
        return ""
    return text


def load_calendar(year: int) -> list[dict[str, Any]]:
    """Use the same fresh calendar fetch as the calendar pages.

    The JSON written beside the fetch is only a cache for this run. A copy
    committed earlier is not the source.
    """
    from event_calendar import load_or_fetch_calendar

    frame = load_or_fetch_calendar(year, calendar_dir=ROOT / "data", refresh=True)
    if frame is None or frame.empty:
        return []
    events = []
    for row in frame.to_dict(orient="records"):
        week = _as_date(row.get("week_start_date"))
        if week is None:
            continue
        event_id = _text(row.get("event_id"))
        if event_id.endswith(".0"):
            event_id = event_id[:-2]
        tour = _text(row.get("tour"))
        raw_year = row.get("event_year")
        if raw_year is None or _text(raw_year) == "":
            raw_year = row.get("year")
        try:
            event_year = int(float(raw_year))
        except (TypeError, ValueError):
            event_year = year
        events.append(
            {
                "year": event_year,
                "week": week,
                "tour": "WTA" if tour == "WS" else "ATP",
                "code": "WS" if tour == "WS" else "MS",
                "city": _text(row.get("city")),
                "event_id": event_id,
                "level": _text(row.get("level") or row.get("type")),
            }
        )
    return events


def load_ladders() -> dict[str, dict[str, Any]]:
    if not PLAYER_EVENTS.exists():
        return {}
    raw = json.loads(PLAYER_EVENTS.read_text(encoding="utf-8"))
    ladders: dict[str, dict[str, Any]] = {}
    for tour, events in raw.items():
        label = "WTA" if str(tour).lower() == "wta" else "ATP"
        for key, info in (events or {}).items():
            points = [int(item) for item in (info.get("day_points") or [])]
            if not points:
                continue
            ladders[f"{label}:{key}"] = {
                "city": str(info.get("name") or "").strip(),
                "points": points,
            }
    return ladders


def _group_tennis(matches: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for match in matches:
        grouped[match["tournament"]].append(match)
    return grouped


def _repair_schedule(schedule: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """December dates on a new-year event are sometimes stamped with the new year.

    The site then lists 12/30 and 1/1 as the same year, so the dates run backwards.
    Those December days belong to the previous year.
    """
    rows = []
    parsed: list[Optional[date]] = []
    for item in schedule:
        played = _as_date(item.get("date"))
        rows.append({**item, "date": played.isoformat() if played else ""})
        parsed.append(played)
    for index in range(1, len(parsed)):
        prev, nxt = parsed[index - 1], parsed[index]
        if not prev or not nxt or nxt + timedelta(days=14) >= prev:
            continue
        for earlier in range(index):
            played = parsed[earlier]
            if not played:
                continue
            fixed = played.replace(year=played.year - 1)
            parsed[earlier] = fixed
            rows[earlier]["date"] = fixed.isoformat()
        break
    return rows


def _matches_for_city(
    name: str, matches: list[dict[str, Any]], city: str
) -> list[dict[str, Any]]:
    places = PLACE_CITIES.get(name)
    if places:
        return [item for item in matches if places.get(item.get("location") or "") == city]
    cities = EN_CITIES.get(name)
    if not cities or city not in cities:
        return []
    return matches


def align_event(
    event: dict[str, Any],
    grouped: dict[str, list[dict[str, Any]]],
    schedule: Optional[list[dict[str, Any]]] = None,
) -> Optional[list[dict[str, Any]]]:
    """Tennis matches for this city whose dates sit on the site's pick days."""
    dates = [played for item in (schedule or []) if (played := _as_date(item.get("date")))]
    if dates:
        window_start = min(dates) - timedelta(days=1)
        window_end = max(dates) + timedelta(days=1)
    else:
        week = event["week"]
        window_start = week - timedelta(days=3)
        window_end = week + timedelta(days=16)
    city = event["city"]
    found: list[tuple[int, list[dict[str, Any]]]] = []
    for name, matches in grouped.items():
        pool = [
            item
            for item in _matches_for_city(name, matches, city)
            if window_start <= item["date"] <= window_end
        ]
        if not pool:
            continue
        first = min(item["date"] for item in pool)
        found.append((abs((first - event["week"]).days), pool))
    if not found:
        return None
    found.sort(key=lambda item: item[0])
    return found[0][1]


def _olympic_price(value: Any) -> Optional[float]:
    """Site draw prices include 1.00 for a heavy favorite."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 1 else None


def load_olympic(tour: str, year: int) -> Optional[list[dict[str, Any]]]:
    """2024 Olympic singles. Tennis-data does not list this event."""
    if year != 2024 or not OLYMPIC_JSON.exists():
        return None
    payload = json.loads(OLYMPIC_JSON.read_text(encoding="utf-8"))
    matches = []
    for row in payload.get(tour.lower()) or []:
        played = _as_date(row.get("date"))
        winner = str(row.get("winner") or "").strip()
        loser = str(row.get("loser") or "").strip()
        round_name = str(row.get("round") or "").strip()
        w_odds = _olympic_price(row.get("w_odds"))
        l_odds = _olympic_price(row.get("l_odds"))
        if (
            played is None
            or not winner
            or not loser
            or round_name not in MAIN_ROUNDS
            or w_odds is None
            or l_odds is None
        ):
            continue
        matches.append(
            {
                "tournament": "Olympics",
                "location": "Paris",
                "date": played,
                "round": round_name,
                "winner": winner,
                "loser": loser,
                "w_rank": _as_int(row.get("w_rank")),
                "l_rank": _as_int(row.get("l_rank")),
                "w_odds": w_odds,
                "l_odds": l_odds,
            }
        )
    return matches or None


def _entry_ranks(matches: list[dict[str, Any]]) -> dict[str, int]:
    """Rank at a player's first match of the event."""
    first: dict[str, tuple[date, int]] = {}
    for match in matches:
        for name, rank in (
            (match["winner"], match["w_rank"]),
            (match["loser"], match["l_rank"]),
        ):
            if not rank:
                continue
            current = first.get(name)
            if current is None or match["date"] < current[0]:
                first[name] = (match["date"], rank)
    return {name: rank for name, (_, rank) in first.items()}


def _days(matches: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    by_date: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for match in matches:
        by_date[match["date"]].append(match)
    return [by_date[key] for key in sorted(by_date)]


def load_pick_schedule(code: str, event_id: str, year: int) -> list[dict[str, Any]]:
    """Site pick days: date and round, cached after the first fetch."""
    path = PICK_DAYS / f"{code}_{event_id}_{year}.json"
    if path.exists():
        payload = list(json.loads(path.read_text(encoding="utf-8")) or [])
        repaired = _repair_schedule(payload)
        if repaired != payload:
            path.write_text(json.dumps(repaired, ensure_ascii=False), encoding="utf-8")
        return repaired
    from parser import fetch_event_detail

    try:
        detail = fetch_event_detail(event_id, year, code)
    except Exception:
        logger.exception(f"pick-day fetch failed {code} {event_id} {year}")
        return []
    days = []
    for key, info in sorted(
        (detail.get("days") or {}).items(),
        key=lambda item: int(item[0]),
    ):
        days.append(
            {
                "day": int(key),
                "date": str(info.get("date") or "")[:10],
                "round": str(info.get("round") or "").strip(),
            }
        )
    days = _repair_schedule(days)
    if days:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(days, ensure_ascii=False), encoding="utf-8")
    return days


def _round_base(label: str) -> str:
    return str(label or "").split("/", 1)[0].strip().upper()


def assign_pick_days(
    matches: list[dict[str, Any]], schedule: list[dict[str, Any]]
) -> list[list[dict[str, Any]]]:
    """Put each match on the site pick day of the same round.

    A match dated the day after the scheduled session stays with that session.
    It is not mixed into the next round, which often starts the same morning.
    """
    slots = []
    for item in sorted(schedule, key=lambda row: int(row["day"])):
        played = _as_date(item.get("date"))
        slots.append(
            {
                "date": played,
                "base": _round_base(item.get("round") or ""),
                "matches": [],
            }
        )
    by_base: dict[str, list[int]] = defaultdict(list)
    for index, slot in enumerate(slots):
        if slot["base"]:
            by_base[slot["base"]].append(index)
    for match in matches:
        base = TENNIS_ROUND.get(match.get("round") or "")
        indexes = by_base.get(base or "") or []
        if not indexes:
            continue
        dated = [index for index in indexes if slots[index]["date"] is not None]
        exact = [index for index in dated if slots[index]["date"] == match["date"]]
        if exact:
            slots[exact[0]]["matches"].append(match)
            continue

        def distance(index: int) -> tuple[int, int, int]:
            delta = (match["date"] - slots[index]["date"]).days
            # A result dated the morning after belongs to the earlier session.
            return (abs(delta), 0 if delta > 0 else 1, index)

        if dated:
            best = min(dated, key=distance)
            if abs((match["date"] - slots[best]["date"]).days) <= 1:
                slots[best]["matches"].append(match)
                continue
        # A final sometimes has a round and a score, but no published date.
        undated = [index for index in indexes if slots[index]["date"] is None]
        if len(undated) == 1:
            slots[undated[0]]["matches"].append(match)
    # One tennis date sometimes holds a whole round the site split across
    # several pick days. Share that date's matches across the empty days.
    for indexes in by_base.values():
        filled = [index for index in indexes if slots[index]["matches"]]
        if len(filled) != 1 or len(indexes) < 2:
            continue
        pool = slots[filled[0]]["matches"]
        size, extra = divmod(len(pool), len(indexes))
        start = 0
        for offset, index in enumerate(indexes):
            take = size + (1 if offset < extra else 0)
            slots[index]["matches"] = pool[start : start + take]
            start += take
    return [slot["matches"] for slot in slots]


def _players_on(day: list[dict[str, Any]], ranks: dict[str, int]) -> list[dict[str, Any]]:
    players = []
    for match in day:
        players.append(
            {
                "name": match["winner"],
                "opponent": match["loser"],
                "rank": ranks.get(match["winner"]) or 9999,
                "odds": match["w_odds"],
                "won": True,
            }
        )
        players.append(
            {
                "name": match["loser"],
                "opponent": match["winner"],
                "rank": ranks.get(match["loser"]) or 9999,
                "odds": match["l_odds"],
                "won": False,
            }
        )
    return players


def _choose(strategy: str, players: list[dict[str, Any]], used: set[str]) -> Optional[dict[str, Any]]:
    pool = [item for item in players if item["name"] not in used]
    if not pool:
        return None
    if strategy == "rank":
        pool.sort(key=lambda item: (item["rank"], item["name"]))
    elif strategy == "favorite":
        pool.sort(key=lambda item: (item["odds"], item["name"]))
    else:
        raise ValueError(f"unknown strategy {strategy}")
    return pool[0]


def _event_score(survived: int, ladder: list[int], city: str, tour: str) -> int:
    if survived <= 0:
        return day1_out_points(city, tour)
    return int(ladder[survived - 1])


def _latest_date(grouped: dict[str, list[dict[str, Any]]]) -> Optional[date]:
    latest = None
    for matches in grouped.values():
        for match in matches:
            played = match["date"]
            if latest is None or played > latest:
                latest = played
    return latest


def _unpublished_tail(
    day_groups: list[list[dict[str, Any]]],
    schedule: list[dict[str, Any]],
    cutoff: Optional[date],
) -> int:
    """Trailing pick days with no matches because the workbook has not reached them."""
    if cutoff is None or not day_groups:
        return 0
    pending = 0
    for group, day in zip(reversed(day_groups), reversed(schedule)):
        if group:
            break
        played = _as_date(day.get("date"))
        if played is None or played <= cutoff:
            break
        pending += 1
    if pending >= len(day_groups):
        return 0
    return pending


def simulate_event(
    strategy: str,
    matches: list[dict[str, Any]],
    ladder: list[int],
    city: str,
    tour: str,
    day_groups: Optional[list[list[dict[str, Any]]]] = None,
    pending: int = 0,
) -> dict[str, Any]:
    days = day_groups if day_groups is not None else _days(matches)
    pending = max(0, min(int(pending or 0), len(days)))
    playable = days[: len(days) - pending] if pending else days
    ranks = _entry_ranks(matches)
    used: set[str] = set()
    picks = []
    survived = 0
    running = 0
    status = "存活"
    for day_no, day in enumerate(playable, start=1):
        choice = _choose(strategy, _players_on(day, ranks), used)
        if choice is None:
            status = "无人可选"
            break
        won = bool(choice["won"])
        if won:
            survived = day_no
            running = int(ladder[day_no - 1])
        elif day_no == 1:
            running = day1_out_points(city, tour)
        picks.append(
            {
                "day": day_no,
                "player": choice["name"],
                "opponent": choice["opponent"],
                "won": won,
                "rank": None if choice["rank"] >= 9999 else choice["rank"],
                "odds": round(float(choice["odds"]), 2),
                "score": running,
            }
        )
        if not won:
            status = "球员输球"
            break
        used.add(choice["name"])
    if status == "存活" and pending:
        finished = False
        status_out = "进行中"
    else:
        finished = survived == len(days) and status == "存活" and not pending
        status_out = "存活" if finished else status
    return {
        "days": len(days),
        "counted_days": len(playable) if pending else len(days),
        "survived": survived,
        "score": _event_score(survived, ladder, city, tour),
        "status": status_out,
        "champion": finished,
        "picks": picks,
    }


def load_draw_pairs(code: str, event_id: str, year: int) -> list[tuple[str, str]]:
    path = DRAWS / f"{code}_{event_id}_{year}.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    pairs = []
    for match in payload.get("matches") or []:
        winner = str(match.get("winner") or "").strip()
        loser = str(match.get("loser") or "").strip()
        if winner and loser:
            pairs.append((winner, loser))
    return pairs


def _pending_pair(
    english_names: list[str],
    chinese_names: list[str],
    alias: dict[str, str],
    used: set[str],
) -> Optional[tuple[str, str]]:
    """Map the last unmatched opponent when every other result is already known."""
    pending_en = list(dict.fromkeys(name for name in english_names if name not in alias))
    assigned = {alias[name] for name in english_names if name in alias}
    pending_cn = list(
        dict.fromkeys(
            name for name in chinese_names if name not in assigned and name not in used
        )
    )
    if len(pending_en) == 1 and len(pending_cn) == 1:
        return pending_en[0], pending_cn[0]
    return None


def extend_names(
    alias: dict[str, str],
    english: list[tuple[str, str]],
    chinese: list[tuple[str, str]],
    bare: set[str],
    roots: dict[str, str],
) -> None:
    """Learn a name from the opponents a known player beat, or lost to."""
    if not chinese:
        return
    chinese = [(_bare_chinese(winner, bare), _bare_chinese(loser, bare)) for winner, loser in chinese]
    for key, value in list(alias.items()):
        alias[key] = _bare_chinese(value, bare)
    _apply_spelling(alias, roots)
    used = set(alias.values())
    changed = True
    while changed:
        changed = False
        beat_en: dict[str, list[str]] = defaultdict(list)
        lost_en: dict[str, list[str]] = defaultdict(list)
        beat_cn: dict[str, list[str]] = defaultdict(list)
        lost_cn: dict[str, list[str]] = defaultdict(list)
        for winner, loser in english:
            beat_en[winner].append(loser)
            lost_en[loser].append(winner)
        for winner, loser in chinese:
            beat_cn[winner].append(loser)
            lost_cn[loser].append(winner)
        for english_name, chinese_name in list(alias.items()):
            for pending in (
                _pending_pair(beat_en.get(english_name, []), beat_cn.get(chinese_name, []), alias, used),
                _pending_pair(lost_en.get(english_name, []), lost_cn.get(chinese_name, []), alias, used),
            ):
                if pending is None:
                    continue
                alias[pending[0]] = pending[1]
                used.add(pending[1])
                changed = True
        before = len(alias)
        _apply_spelling(alias, roots)
        if len(alias) != before:
            used = set(alias.values())
            changed = True


def load_user_scores(code: str, event_id: str, year: int, city: str) -> dict[str, dict[str, Any]]:
    path = SCORES / f"{code}_{event_id}_{year}.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    users: dict[str, dict[str, Any]] = {}
    for row in payload.get("rows") or []:
        user_id = str(row.get("user_id") or "").strip()
        if not user_id:
            continue
        try:
            score = int(row.get("score") or 0)
        except (TypeError, ValueError):
            continue
        name = str(row.get("username") or user_id).strip() or user_id
        users[user_id] = {"id": user_id, "name": name, "city": city, "score": score}
    return users


def _rank_of(bot_points: int, others: list[int]) -> int:
    """Minimum rank: every equal total shares the first place in the tie."""
    better = sum(1 for score in others if score > bot_points)
    return better + 1


def _totals(scores: dict[str, int], tour: str) -> int:
    if not scores:
        return 0
    result = calculate_points(scores, tour="WTA" if tour == "WTA" else "ATP")
    return int(result.get("total_points") or 0)


def _user_prefixes(
    events: list[dict[str, Any]], tour: str
) -> list[list[int]]:
    """After each event, every real user's best-18 total so far."""
    ordered = sorted(events, key=lambda item: (item["week"], item["city"]))
    users: dict[str, dict[str, int]] = defaultdict(dict)
    prefixes: list[list[int]] = []
    for event in ordered:
        for row in event["users"].values():
            users[row["id"]][event["city"]] = row["score"]
        prefixes.append([_totals(dict(scores), tour) for scores in users.values()])
    return prefixes


def _bot_series(
    events: list[dict[str, Any]],
    prefixes: list[list[int]],
    bot_scores: dict[str, int],
    tour: str,
) -> tuple[list[dict[str, Any]], int, int]:
    ordered = sorted(events, key=lambda item: (item["week"], item["city"]))
    bot: dict[str, int] = {}
    series = []
    for event, others in zip(ordered, prefixes):
        if event["city"] in bot_scores:
            bot[event["city"]] = bot_scores[event["city"]]
        total = _totals(bot, tour)
        series.append(
            {
                "week": event["week"].isoformat(),
                "city": event["city"],
                "year": event["year"],
                "rank": _rank_of(total, others),
                "points": total,
                "played": event["city"] in bot_scores,
            }
        )
    if not series:
        return [], 0, 1
    return series, series[-1]["points"], series[-1]["rank"]


def _summary(years: list[dict[str, Any]]) -> dict[str, Any]:
    played = sum(int(item["played"]) for item in years)
    titles = sum(int(item["titles"]) for item in years)
    days = sum(int(item["days"]) for item in years)
    survived = sum(int(item["survived_days"]) for item in years)
    points = sum(int(item["points"]) for item in years)
    ranks = [int(item["rank"]) for item in years if item.get("rank")]
    return {
        "points": points,
        "best_rank": min(ranks) if ranks else None,
        "titles": titles,
        "played": played,
        "avg_days": round(survived / played, 2) if played else 0,
        "finish_rate": round(titles / played, 3) if played else 0,
        "survival": round(survived / days, 3) if days else 0,
    }


# Tennis-data writes a full given name where the seed uses the initial.
# Wang Xiy. is a different player (王曦雨) and must not follow this.
SAME_SPELLING = {
    "Wang Xin.": "Wang X.",
}
_LATIN_PREFIX = re.compile(r"^([A-Za-z]) (.+)$")


def _tokens(name: str) -> tuple[str, ...]:
    return tuple(part.lower() for part in name.replace(".", " ").split() if part)


def _has_cjk(name: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in name)


def _same_initials(left: str, right: str) -> bool:
    """True when two English strings are the same player with a middle initial added."""
    a, b = _tokens(left), _tokens(right)
    if len(a) < 2 or len(b) < 2 or a[0] != b[0] or a[1] != b[1]:
        return False
    return all(len(token) == 1 for token in a[1:] + b[1:])


def _expands_initial(short: str, long: str, pool: list[str]) -> bool:
    """True when the longer given name is the only expansion of that initial."""
    a, b = _tokens(short), _tokens(long)
    if len(a) != 2 or len(b) != 2 or a[0] != b[0]:
        return False
    if len(a[1]) != 1 or len(b[1]) < 3 or not b[1].startswith(a[1]):
        return False
    letter = a[1]
    for name in pool:
        tokens = _tokens(name)
        if (
            len(tokens) == 2
            and tokens[0] == a[0]
            and len(tokens[1]) >= 3
            and tokens[1].startswith(letter)
            and tokens[1] != b[1]
        ):
            return False
    return True


def _bare_chinese(name: str, bare: set[str]) -> str:
    """Drop a site initial when that Chinese name is already used on its own."""
    match = _LATIN_PREFIX.match(name)
    if not match or not _has_cjk(match.group(2)):
        return name
    rest = match.group(2)
    return rest if rest in bare else name


def _safe_bare_names() -> set[str]:
    """Chinese names whose single leading initial is only a spelling variant."""
    prefixes: dict[str, set[str]] = defaultdict(set)
    bare: set[str] = set()
    if not DRAWS.exists():
        return set()
    for path in DRAWS.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for match in payload.get("matches") or []:
            for key in ("winner", "loser"):
                name = str(match.get(key) or "").strip()
                found = _LATIN_PREFIX.match(name)
                if found and _has_cjk(found.group(2)):
                    prefixes[found.group(2)].add(found.group(1))
                elif _has_cjk(name):
                    bare.add(name)
    return {rest for rest, letters in prefixes.items() if len(letters) == 1 and rest in bare}


def _spelling_roots(names: set[str]) -> dict[str, str]:
    """Group English strings that are the same player spelled two ways."""
    by_last: dict[str, list[str]] = defaultdict(list)
    parent = {name: name for name in names}
    for name in names:
        tokens = _tokens(name)
        if len(tokens) >= 2:
            by_last[tokens[0]].append(name)

    def find(name: str) -> str:
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    def unite(left: str, right: str) -> None:
        left, right = find(left), find(right)
        if left != right:
            parent[right] = left

    for group in by_last.values():
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                if (
                    _same_initials(left, right)
                    or _expands_initial(left, right, group)
                    or _expands_initial(right, left, group)
                    or SAME_SPELLING.get(left) == right
                    or SAME_SPELLING.get(right) == left
                ):
                    unite(left, right)
    return {name: find(name) for name in names}


def _apply_spelling(alias: dict[str, str], roots: dict[str, str]) -> None:
    groups: dict[str, list[str]] = defaultdict(list)
    for name in set(alias) | set(roots):
        groups[roots.get(name, name)].append(name)
    for group in groups.values():
        known = {alias[name] for name in group if name in alias}
        if len(known) != 1:
            continue
        chinese = next(iter(known))
        for name in group:
            alias.setdefault(name, chinese)


def _translate(name: str, alias: dict[str, str], bare: set[str] | None = None) -> str:
    chinese = alias.get(name) or name
    if bare:
        return _bare_chinese(chinese, bare)
    return chinese


def run_strategy_sim() -> dict[str, Any]:
    from site_html.strategy import render_strategy_pages

    ladders = load_ladders()
    span = range(min(YEARS) - 1, max(YEARS) + 1)
    loaded = {
        (tour, year): _group_tennis(load_tennis(tour.lower(), year))
        for tour in ("ATP", "WTA")
        for year in span
    }
    tennis = {key: value for key, value in loaded.items() if key[1] in YEARS}
    pools: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for tour_name in ("ATP", "WTA"):
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for file_year in span:
            for name, file_matches in loaded[(tour_name, file_year)].items():
                grouped[name].extend(file_matches)
        pools[tour_name] = grouped
    alias = dict(NAME_SEED)
    bare = _safe_bare_names()
    spellings = set(NAME_SEED)
    for grouped in tennis.values():
        for matches in grouped.values():
            for match in matches:
                spellings.add(match["winner"])
                spellings.add(match["loser"])
    if OLYMPIC_JSON.exists():
        olympic_names = json.loads(OLYMPIC_JSON.read_text(encoding="utf-8"))
        for key, chinese in (olympic_names.get("aliases") or {}).items():
            alias.setdefault(str(key), str(chinese))
        for key in ("atp", "wta"):
            for row in olympic_names.get(key) or []:
                spellings.add(str(row.get("winner") or ""))
                spellings.add(str(row.get("loser") or ""))
    roots = _spelling_roots(spellings)
    prepared: list[dict[str, Any]] = []
    ranked: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for year in YEARS:
        for event in load_calendar(year):
            tour = event["tour"]
            city = event["city"]
            base = {
                "tour": tour,
                "year": event["year"],
                "city": city,
                "event_id": event["event_id"],
                "level": event["level"],
            }
            users = load_user_scores(
                event["code"], event["event_id"], event["year"], city
            )
            year_end = (
                is_year_end_final(city, event["event_id"])
                or city in SKIP_CITIES
            )
            if year_end:
                skipped.append({**base, "reason": "年终总决赛"})
                continue
            schedule = load_pick_schedule(event["code"], event["event_id"], event["year"])
            pick_dates = [
                played for item in schedule if (played := _as_date(item.get("date")))
            ]
            if pick_dates and abs((min(pick_dates) - event["week"]).days) > 21:
                event["week"] = min(pick_dates)
            ranked.append({**event, "users": users})
            if city == "奥运会":
                matches = load_olympic(tour, event["year"])
            else:
                matches = align_event(event, pools[tour], schedule)
            if not matches:
                skipped.append({**base, "reason": "没有赛前赔率"})
                continue
            ladder = ladders.get(f"{tour}:{event['year']}:{event['event_id']}")
            if not ladder or ladder["city"] != city:
                ladder = next(
                    (
                        item
                        for key, item in ladders.items()
                        if key.startswith(f"{tour}:{event['year']}:")
                        and item["city"] == city
                    ),
                    None,
                )
            if not ladder:
                skipped.append({**base, "reason": "没有分数阶梯"})
                continue
            if len(schedule) != len(ladder["points"]):
                skipped.append(
                    {
                        **base,
                        "reason": "没有选人日日期" if not schedule else "选人日与分数阶梯不一致",
                        "site_days": len(ladder["points"]),
                        "match_days": len(schedule),
                    }
                )
                continue
            day_groups = assign_pick_days(matches, schedule)
            pending = _unpublished_tail(
                day_groups, schedule, _latest_date(tennis[(tour, year)])
            )
            extend_names(
                alias,
                [(item["winner"], item["loser"]) for item in matches],
                load_draw_pairs(event["code"], event["event_id"], event["year"]),
                bare,
                roots,
            )
            prepared.append(
                {
                    **event,
                    "matches": matches,
                    "day_groups": day_groups,
                    "ladder": ladder["points"],
                    "users": users,
                    "pending": pending,
                }
            )

    payload: dict[str, Any] = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "years": list(YEARS),
        "skipped": skipped,
        "tours": {},
    }
    unmapped: set[str] = set()
    for tour in ("ATP", "WTA"):
        tour_events = [item for item in prepared if item["tour"] == tour]
        prefixes_by_year = {
            year: _user_prefixes(
                [item for item in ranked if item["tour"] == tour and item["year"] == year],
                tour,
            )
            for year in YEARS
        }
        strategies: dict[str, Any] = {}
        for key, _label in STRATEGIES:
            simulated = []
            for event in tour_events:
                result = simulate_event(
                    key,
                    event["matches"],
                    event["ladder"],
                    event["city"],
                    tour,
                    day_groups=event["day_groups"],
                    pending=int(event.get("pending") or 0),
                )
                expected = _event_score(
                    result["survived"], event["ladder"], event["city"], tour
                )
                if result["score"] != expected:
                    raise RuntimeError(
                        f"{tour} {event['year']} {event['city']} score {result['score']} != {expected}"
                    )
                for pick in result["picks"]:
                    shown = _translate(pick["player"], alias, bare)
                    if shown == pick["player"]:
                        unmapped.add(pick["player"])
                    pick["player"] = shown
                    pick["opponent"] = _translate(pick["opponent"], alias, bare)
                simulated.append({**event, **result})
            by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
            for event in simulated:
                by_year[event["year"]].append(event)
            year_rows = []
            rank_series = []
            event_rows = []
            for year in YEARS:
                year_events = by_year.get(year) or []
                scored = [item for item in ranked if item["tour"] == tour and item["year"] == year]
                prefixes = prefixes_by_year[year]
                bot_scores = {item["city"]: item["score"] for item in year_events}
                series, points, rank = _bot_series(scored, prefixes, bot_scores, tour)
                rank_by_city = {item["city"]: item["rank"] for item in series}
                rank_series.extend(item for item in series if item["played"])
                played = len(year_events)
                titles = sum(1 for item in year_events if item["champion"])
                survived_days = sum(int(item["survived"]) for item in year_events)
                days = sum(
                    int(item.get("counted_days") or item["days"]) for item in year_events
                )
                year_rows.append(
                    {
                        "year": year,
                        "played": played,
                        "points": points,
                        "rank": rank,
                        "titles": titles,
                        "days": days,
                        "survived_days": survived_days,
                        "avg_days": round(survived_days / played, 2) if played else 0,
                        "survival": round(survived_days / days, 3) if days else 0,
                        "finish_rate": round(titles / played, 3) if played else 0,
                    }
                )
                for event in sorted(year_events, key=lambda item: item["week"]):
                    event_rows.append(
                        {
                            "year": year,
                            "week": event["week"].isoformat(),
                            "city": event["city"],
                            "level": event["level"],
                            "days": event["days"],
                            "survived": event["survived"],
                            "score": event["score"],
                            "status": event["status"],
                            "champion": event["champion"],
                            "rank": rank_by_city.get(event["city"]),
                            "picks": event["picks"],
                        }
                    )
            strategies[key] = {
                "summary": _summary(year_rows),
                "years": year_rows,
                "events": event_rows,
                "ranks": rank_series,
            }
        payload["tours"][tour] = {
            "strategies": strategies,
            "skipped": [item for item in skipped if item["tour"] == tour],
        }

    payload["unmapped"] = sorted(unmapped)
    payload["name_count"] = len(alias)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    NAMES_JSON.write_text(
        json.dumps(
            {"names": dict(sorted(alias.items())), "unmapped_picks": payload["unmapped"]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info(
        f"strategy sim: {len(prepared)} events, skipped {len(skipped)}, "
        f"names {len(alias)}, unmapped picks {len(unmapped)}"
    )
    render_strategy_pages(payload)
    _print_check(payload)
    return payload


def _print_check(payload: dict[str, Any]) -> None:
    """Madrid 2025 is a 1000 whose match days line up with the published ladder."""
    events = payload["tours"]["ATP"]["strategies"]["rank"]["events"]
    madrid = [
        item
        for item in events
        if item["year"] == 2025 and item["city"] == "马德里"
    ]
    if not madrid:
        logger.warning("hand check: 2025 马德里 was not simulated")
        return
    event = madrid[0]
    logger.info(
        "hand check ATP 2025 马德里 "
        f"survived {event['survived']}/{event['days']} score {event['score']} "
        f"status {event['status']}"
    )
    for pick in event["picks"]:
        mark = "胜" if pick["won"] else "负"
        logger.info(
            f"  Day {pick['day']} {pick['player']} {mark} "
            f"vs {pick['opponent']} rank {pick['rank']} odds {pick['odds']}"
        )
