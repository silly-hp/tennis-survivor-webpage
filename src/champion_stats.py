import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from logger import get_logger
from parser import fetch_table, fetch_survivor_calendar_event_df
from pathlib import Path
from typing import Union
import yaml

from survivor_html import apply_theme, render_champion_page

logger = get_logger(__name__)


def save_champions(df: pd.DataFrame, file_path: str = "../data/champions.csv") -> None:
    """
    Save dataframe to CSV.

    - If file exists: append without writing header again
    - If file does not exist: create new file with header
    """

    file_exists = Path(file_path).exists()

    df.to_csv(
        file_path,
        mode="a" if file_exists else "w",
        header=not file_exists,
        index=False,
        encoding="utf-8-sig",
    )


def build_winners_df(season: int, save_csv: bool = True) -> pd.DataFrame:
    """
    Build winners dataframe for a given season/year.

    Parameters
    ----------
    season : int
        Year of the season, e.g. 2024

    Returns
    -------
    pd.DataFrame
    """

    df, _ = fetch_survivor_calendar_event_df(season)
    winners = []

    for _, row in df.iterrows():
        event_id = row["event_id"]
        city = row["city"]

        try:
            event_df, _ = fetch_table(
                option="score",
                page_size=1000,
                event_id=event_id,
                year=row["year"],
                tour=row["tour"],
            )

            winner_df = event_df.loc[
                event_df["status"] == 2, ["user_id", "username", "score"]
            ].copy()
            logger.info(f"{city}: {len(winner_df)}人夺冠")

            winner_df.loc[:, ["tournament", "tour", "season", "week"]] = [
                city,
                row["tour"],
                row["year"],
                row["week_start_date"],
            ]

            winners.append(winner_df)
        except Exception as err:
            logger.error(err)
            continue
    winners_df = pd.concat(winners, ignore_index=True)

    # map tour names
    winners_df["tour"] = winners_df["tour"].map({"MS": "ATP", "WS": "WTA"})

    # build type column
    conditions = [
        winners_df["tournament"].eq("奥运会"),
        winners_df["score"].eq(2000),
        winners_df["score"].eq(1500),
        winners_df["score"].le(1000),
    ]

    choices = [
        "奥运会",
        "大满贯",
        "年终总决赛",
        winners_df["tour"].astype(str) + winners_df["score"].astype(str),
    ]

    winners_df["type"] = np.select(conditions, choices, default=None)

    if save_csv:
        save_champions(winners_df)

    return winners_df


def update_champion(
    event_id: Union[int, str],
    season: int,
    tour: str,
    file_path: str = "../data/champions.csv",
) -> pd.DataFrame:
    """
    Fetch and append champion info for a single tournament.

    Parameters
    ----------
    event_id : int
        Tournament event id

    season : int
        Tournament year

    tour : str
        "MS" or "WS"

    file_path : str
        CSV file path

    Returns
    -------
    pd.DataFrame
        Champion dataframe for this tournament
    """

    # fetch calendar info to get city/tournament name
    calendar_df, _ = fetch_survivor_calendar_event_df(season)

    event_row = calendar_df.loc[
        (calendar_df["event_id"] == str(event_id)) & (calendar_df["tour"] == tour)
    ]

    if event_row.empty:
        raise ValueError(
            f"Cannot find event_id={event_id}, season={season}, tour={tour}"
        )

    event_row = event_row.iloc[0]
    city = event_row["city"]
    week = event_row["week_start_date"]

    logger.info(f"开始更新赛事: {city}")

    # fetch event score table
    event_df, _ = fetch_table(
        option="score",
        page_size=1000,
        event_id=event_id,
        year=season,
        tour=tour,
    )

    # champion rows
    winner_df = event_df.loc[
        event_df["status"] == 2,
        ["user_id", "username", "score"],
    ].copy()

    logger.info(f"{city}: {len(winner_df)}人夺冠")

    # enrich metadata
    winner_df.loc[:, ["tournament", "tour", "season"]] = [
        city,
        tour,
        season,
    ]

    # map tour names
    winner_df["tour"] = winner_df["tour"].map(
        {
            "MS": "ATP",
            "WS": "WTA",
        }
    )

    winner_df["week"] = week

    # build type column
    conditions = [
        winner_df["tournament"].eq("奥运会"),
        winner_df["score"].eq(2000),
        winner_df["score"].eq(1500),
        winner_df["score"].le(1000),
    ]

    choices = [
        "奥运会",
        "大满贯",
        "年终总决赛",
        winner_df["tour"].astype(str) + winner_df["score"].astype(str),
    ]

    winner_df["type"] = np.select(
        conditions,
        choices,
        default=None,
    )

    # append to csv
    save_champions(winner_df, file_path=file_path)

    logger.info(f"{city} 已追加到 {file_path}")

    return winner_df


def extract_champion_rows(
    event_df: pd.DataFrame,
    city: str,
    tour_code: str,
    season: int,
    week_start_date,
) -> pd.DataFrame:
    """Build champion rows from an already-fetched score table, without any I/O."""
    tour_label = "ATP" if tour_code.upper() == "MS" else "WTA"
    winner_df = event_df.loc[
        event_df["status"] == 2, ["user_id", "username", "score"]
    ].copy()

    if winner_df.empty:
        return winner_df

    winner_df.loc[:, ["tournament", "tour", "season", "week"]] = [
        city, tour_label, season, week_start_date,
    ]

    conditions = [
        winner_df["tournament"].eq("奥运会"),
        winner_df["score"].eq(2000),
        winner_df["score"].eq(1500),
        winner_df["score"].le(1000),
    ]
    choices = [
        "奥运会",
        "大满贯",
        "年终总决赛",
        winner_df["tour"].astype(str) + winner_df["score"].astype(str),
    ]
    winner_df["type"] = np.select(conditions, choices, default=None)
    return winner_df


def render_champion_pages(
    champions_path: str = "../data/champions.csv",
    datetime_format: str = "%Y年%m月%d日 %H:%M:%S",
) -> None:
    """Re-render the ATP, WTA and 联合 Hall of Fame pages from the current champions.csv."""
    if not Path(champions_path).exists():
        logger.warning("[Champion] %s not found, skipping render.", champions_path)
        return

    champions_df = pd.read_csv(champions_path, encoding="utf-8-sig").dropna(how="all")
    updated = datetime.now().strftime(datetime_format)

    # refresh usernames from each tour's live rank table (user_id is the identity)
    parts = []
    for tour_code, tour_label in (("MS", "ATP"), ("WS", "WTA")):
        part = champions_df[champions_df["tour"] == tour_label]
        try:
            rank_df, _ = fetch_table(option="rank", tour=tour_code)
            part = update_username(rank_df.loc[:, ["user_id", "username"]], part)
        except Exception:
            logger.exception("[Champion] Could not refresh %s usernames; using champions.csv", tour_label)
        parts.append(part)
    df = pd.concat(parts, ignore_index=True)

    for tour, output in (("ATP", "../atp_champion.html"), ("WTA", "../wta_champion.html"),
                         ("ALL", "../combined_champion.html")):
        try:
            render_champion_page(df=df, tour=tour, updated=updated, output_path=output)
            logger.info("[Champion] Written: %s", output)
        except Exception:
            logger.exception("[Champion] Failed to render %s champion page", tour)


def update_username(rank: pd.DataFrame, champions: pd.DataFrame) -> pd.DataFrame:
    df = champions.merge(
        rank.rename({"username": "new_username"}, axis=1), on="user_id", how="left"
    )
    df.loc[
        (df["username"] != df["new_username"]) & (df["new_username"].notna()),
        "username",
    ] = df.loc[
        (df["username"] != df["new_username"]) & (df["new_username"].notna()),
        "new_username",
    ]
    return df.drop("new_username", axis=1)


if __name__ == "__main__":
    # for y in (2024, 2025, 2026):
    #     build_winners_df(y)
    with open("../config.yaml") as f:
        cfg = yaml.safe_load(f)
    apply_theme(cfg["theme"])
    # update_champion(event_id=cfg["wta"]["event"], season=cfg["year"], tour="WS")
    update_champion(event_id=cfg["atp"]["event"], season=cfg["year"], tour="MS")

    render_champion_pages()
