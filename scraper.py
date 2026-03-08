from datetime import datetime

from bs4 import BeautifulSoup

from db_manager import username_to_id
from http_client import HttpClient  # our async client
from utils import compute_stars


async def scrape_user(client: HttpClient, user_id: int) -> dict:
    """
    Scrape user statistics from gomafia.pro asynchronously.
    """
    data = {
        "id": user_id,
        "period": "all",
        "gameType": "all",
        "tournamentType": "fsm",
    }
    # POST request with proxy rotation
    response = await client.post("https://gomafia.pro/api/stats/get", data=data)
    rd = await response.json()
    data_user = rd["data"]["user"]
    data_stats = rd["data"]["stats"]

    user_resp = {
        "id": int(user_id),
        "username": data_user["login"],
        "elo": float(data_user["elo"]),
        "referee_license": bool(int(data_user["referee_license"])),
        "town_games": int(data_stats["primary"]["red"]),
        "mafia_games": int(data_stats["primary"]["mafia"]),
        "sheriff_games": int(data_stats["primary"]["sheriff"]),
        "don_games": int(data_stats["primary"]["don"]),
        "town_wins": int(data_stats["win_rate"]["red"]["win"]["value"]),
        "mafia_wins": int(data_stats["win_rate"]["mafia"]["win"]["value"]),
        "sheriff_wins": int(data_stats["win_rate"]["sheriff"]["win"]["value"]),
        "don_wins": int(data_stats["win_rate"]["don"]["win"]["value"]),
        "town_add": float(data_stats["advanced_points"]["red"]["points"]),
        "mafia_add": float(data_stats["advanced_points"]["black"]["points"]),
        "sheriff_add": float(data_stats["advanced_points"]["sheriff"]["points"]),
        "don_add": float(data_stats["advanced_points"]["don"]["points"]),
    }
    return user_resp


async def scrape_tournament(client: HttpClient, tournament_id: int) -> tuple:
    """
    Scrape tournament details, games, and player performances asynchronously.
    Returns (Tournament_info, Games, Player_performances).
    """
    Tournament_info = {
        "id": None,
        "name": None,
        "stars": None,
        "is_rated": None,
        "is_team": None,
        "website_elo": None,
        "date_begin": None,
        "date_end": None,
        "city": None,
        "country": None,
        "num_of_participants": None,
        "vk_link": None,
        "head_judge_id": None,
        "org_id": None,
    }
    Games = []
    Player_performances = []

    # Inner function for main tournament info
    async def extract_main():
        url = f"https://gomafia.pro/tournament/{tournament_id}"
        response = await client.get(url)
        if response.status != 200:
            print(f"Error {response.status} for tournament {tournament_id}")
            return

        Tournament_info["id"] = tournament_id
        soup = BeautifulSoup(await response.text(), "html.parser")

        # Check for redirect to main page
        if len(soup.select("div[class*=MainIntro_main-intro]")) > 0:
            print(f"Error: redirect to main page tournament: {tournament_id}")
            return

        info_keys = ["dates", "city", "type", "players"]
        for info_name, info_piece in zip(
            info_keys, soup.select('div[class*="tournament__top-left-item__"]')
        ):
            if info_name == "dates":
                Tournament_info["date_begin"] = datetime.strptime(
                    info_piece.text[23:33], "%d.%m.%Y"
                ).date()
                Tournament_info["date_end"] = datetime.strptime(
                    info_piece.text[23 + 13 : 23 + 13 + 10], "%d.%m.%Y"
                ).date()
                if Tournament_info["date_begin"] > Tournament_info["date_end"]:
                    Tournament_info["date_begin"], Tournament_info["date_end"] = (
                        Tournament_info["date_end"],
                        Tournament_info["date_begin"],
                    )
            if info_name == "city":
                words = [i.strip() for i in info_piece.text[5:].split(",")]
                Tournament_info["city"] = words[1] if len(words) > 1 else words[0]
                Tournament_info["country"] = words[0]
            if info_name == "type":
                Tournament_info["is_team"] = (
                    info_piece.text[11] != "Л"
                )  # True if "Командный"
            if info_name == "players":
                ib = info_piece.text.index("из") + 2
                Tournament_info["num_of_participants"] = int(
                    info_piece.text[ib:].strip()
                )

        # Website ELO
        elo_elem = soup.select_one('div[class*="tournament__top-left-elo"]')
        if elo_elem:
            Tournament_info["website_elo"] = float(elo_elem.text)

        # Title
        title_elem = soup.select_one('div[class*="tournament__top-left-title"]')
        if title_elem:
            Tournament_info["name"] = title_elem.text

        # Head judge and organiser
        for link in soup.find_all("a"):
            txt = link.get("href", "").split("/")[-1]
            if txt == "null":
                continue
            if "ГС" in link.text:
                Tournament_info["head_judge_id"] = int(txt)
            if "Орг" in link.text:
                Tournament_info["org_id"] = int(txt)

        # VK link
        vk_link = soup.select_one('a[class*="Links_links_primary"]')
        if vk_link and "VK" in vk_link.text:
            Tournament_info["vk_link"] = vk_link.get("href")

        # Check if rated
        tds = soup.find_all("td")
        if len(tds) >= 27:
            GG_pts_first = int(tds[26].text)
            if GG_pts_first != 0:
                Tournament_info["is_rated"] = True
                stars_predict = compute_stars(
                    Tournament_info["num_of_participants"], GG_pts_first
                )
                Tournament_info["stars"] = stars_predict
            else:
                Tournament_info["is_rated"] = False

    # Inner function for games and player performances
    async def extract_games():
        url = f"https://gomafia.pro/tournament/{tournament_id}?tab=games"
        response = await client.get(url)
        if response.status != 200:
            print(f"Error {response.status} for tournament {tournament_id}")
            return

        soup = BeautifulSoup(await response.text(), "html.parser")
        tours = soup.select('div[class*="tid__tournament__games-tour___Xfzi"]')
        if len(tours) == 0:
            print(f"Error no tours for tournament {tournament_id}")
            return

        for tour in tours:
            tour_title = tour.select_one('div[class*="games-tour-title"]').text
            games = tour.select(
                'table[class*="TableTournamentResultGame_table-tournament-result-game"]'
            )
            for game in games:
                game_dict = {
                    "round_num": None,
                    "table_num": None,
                    "tournament_id": tournament_id,
                    "judge_id": None,
                    "win": None,
                }
                ths = game.select('th[colspan="3"]')
                if len(ths) < 2:
                    continue
                tj, wins = ths[:2]
                table_part, judge_name = tj.text.split(",")
                table = int(table_part[5:].strip())
                judge_name = judge_name.strip()

                if "маф" in wins.text:
                    game_dict["win"] = "mafia"
                elif "мир" in wins.text:
                    game_dict["win"] = "town"
                elif "ичья" in wins.text:
                    game_dict["win"] = "draw"
                else:
                    print(
                        f"Error: no game result tournament: {tournament_id}, tour {tour_title}, table {table}"
                    )
                    continue

                game_dict["table_num"] = table
                game_dict["judge_id"] = username_to_id(judge_name)
                game_dict["round_num"] = int(tour_title[4:])
                Games.append(game_dict)

                for row in game.select_one("tbody").select("tr"):
                    player_perf = {
                        "seat": None,
                        "user_id": None,
                        "role": None,
                        "points": None,
                        "elo_delta": None,
                    }
                    cells = row.select("td")
                    for i, cell in enumerate(cells):
                        if i == 0:
                            player_perf["seat"] = int(cell.text)
                        elif i == 1:
                            player_perf["user_id"] = username_to_id(cell.text)
                        elif i == 2:
                            player_perf["role"] = {
                                "Мир": "town",
                                "Маф": "mafia",
                                "Шер": "sheriff",
                                "Дон": "don",
                            }[cell.text]
                        elif i == 3:
                            player_perf["points"] = float(cell.text)
                        elif i == 4:
                            player_perf["elo_delta"] = int(cell.text)
                    Player_performances.append(player_perf)

    # Execute both extraction steps
    await extract_main()
    await extract_games()

    return Tournament_info, Games, Player_performances
