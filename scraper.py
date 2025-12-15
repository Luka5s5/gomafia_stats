import random
from datetime import datetime
from functools import partial

import requests
from bs4 import BeautifulSoup

from config import PROXY_LIST
from db_manager import username_to_id
from utils import compute_stars


def is_proxy_fast(proxy):
    try:
        # Test the proxy with a request to https://gomafia.pro/
        response = requests.get(
            "https://gomafia.pro/",
            proxies={"http": proxy, "https": proxy},
            timeout=1  # 1 second timeout
        )
        # Consider the proxy good if we get any response (even non-200 status codes)
        return True
    except requests.Timeout:
        # Proxy timed out
        return False
    except requests.RequestException:
        # Other request errors (connection errors, invalid proxy, etc.)
        return False

# Filter the proxy list
PROXY_LIST = [p for p in PROXY_LIST if is_proxy_fast(p)]

def get_random_proxy():
    proxy = random.choice(PROXY_LIST)
    print(proxy)
    return {"http": proxy}


original_session_request = requests.Session.request


def enforce_proxy_request(self, method, url, **kwargs):
    """Wrapper around Session.request to force proxy usage."""
    kwargs["proxies"] = get_random_proxy()
    # kwargs['']
    return original_session_request(self, method, url, **kwargs)


requests.Session.request = enforce_proxy_request

session = requests.Session()
for method in ("get", "post", "put", "delete", "patch", "head", "options"):
    setattr(requests, method, partial(getattr(session, method)))


def scrape_user(user_id):
    data = {
        "id": user_id,
        "period": "all",
        "gameType": "all",
        "tournamentType": "fsm",
    }
    response = requests.post("https://gomafia.pro/api/stats/get", data=data)
    rd = response.json()
    data_user = rd["data"]["user"]
    data_stats = rd["data"]["stats"]
    user_resp = {
        "user_id": int(user_id),
        "user_name": data_user["login"],
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
        "mafia_add": float(
            data_stats["advanced_points"]["black"]["points"]
        ),  # да, везде mafia, а тут black...
        "sheriff_add": float(data_stats["advanced_points"]["sheriff"]["points"]),
        "don_add": float(data_stats["advanced_points"]["don"]["points"]),
    }
    return user_resp


def scrape_tournament(tournament_id):
    def extract_main(Tournament_info):
        Tournament_info["id"] = str(tournament_id)
        url = f"https://gomafia.pro/tournament/{tournament_id}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error {response.status_code} for tournament {tournament_id}")
            Tournament_info = {}
            return

        soup = BeautifulSoup(response.text, "html.parser")

        if len(soup.select("div[class*=MainIntro_main-intro]")) > 0:
            print(f"Error: redirect to main page tournament: {tournament_id}")
            Tournament_info = {}
            return

        info_keys = ["dates", "city", "type", "players"]
        for info_name, info_piece in zip(
            info_keys, soup.select('div[class*="tournament__top-left-item__"]')
        ):
            if info_name == "dates":
                Tournament_info["date_begin"] = datetime.strptime(
                    info_piece.text[23 : 23 + 10], "%d.%m.%Y"
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
                Tournament_info["city"] = words[1]
                Tournament_info["country"] = words[0]
            if info_name == "type":
                Tournament_info["is_team"] = (
                    False if info_piece.text[11] == "Л" else True
                )
            if info_name == "players":
                ib = info_piece.text.index("из") + 2
                Tournament_info["num_of_participants"] = int(
                    info_piece.text[ib:].strip()
                )
            # print(info_name,info_piece.text,'!')

        if len(soup.select('div[class*="tournament__top-left-elo"]')) != 0:
            Tournament_info["website_elo"] = float(
                soup.select('div[class*="tournament__top-left-elo"]')[0].text
            )
        Tournament_info["name"] = soup.select(
            'div[class*="tournament__top-left-title"]'
        )[0].text
        for link in filter(
            lambda x: "ГС" in x.text or "Орг" in x.text, soup.find_all("a")
        ):
            txt = link.get("href").split("/")[-1]
            if txt == "null":
                continue
            if "ГС" in link.text:
                Tournament_info["head_judge_id"] = int(txt)
            if "Орг" in link.text:
                Tournament_info["org_id"] = int(txt)

        for link in filter(
            lambda x: "VK" in x.text, soup.select('a[class*="Links_links_primary"]')
        ):
            Tournament_info["vk_link"] = link.get("href")

        if len(soup.find_all("td")) >= 27:
            GG_pts_first = int(soup.find_all("td")[26].text)
            if GG_pts_first != 0:
                Tournament_info["is_rated"] = True
                stars_predict = compute_stars(
                    Tournament_info["num_of_participants"], GG_pts_first
                )
                Tournament_info["stars"] = stars_predict  # compare to real stars???
            else:
                Tournament_info["is_rated"] = False

    def extract_tables():
        pass

    def extract_games(games_arg, player_performances):
        url = f"https://gomafia.pro/tournament/{tournament_id}?tab=games"
        response = requests.get(url)

        users = {}

        if response.status_code != 200:
            print(f"Error {response.status_code} for tournament {tournament_id}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        tours = soup.select('div[class*="tid__tournament__games-tour___Xfzi"]')
        if len(tours) == 0:
            print(f"Error no tours for tournament {tournament_id}")
            return []

        for tour in tours:
            tour_title = tour.select_one('div[class*="games-tour-title"]').text
            # print(tour_title[4:])
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
                tj, wins = game.select('th[colspan="3"]')
                table, judge_name = tj.text.split(",")
                table = int(table[5:])
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
                    continue  # bad game -- no result

                game_dict["table_num"] = table
                game_dict["judge_id"] = username_to_id(judge_name)
                game_dict["round_num"] = int(tour_title[4:])
                games_arg.append(game_dict)

                for row in game.select_one("tbody").select("tr"):
                    player_perf = {
                        "seat": None,
                        "user_id": None,
                        "role": None,
                        "points": None,
                        "elo_delta": None,
                    }
                    for i, cell in enumerate(row.select("td")):
                        match i:
                            case 0:
                                player_perf["seat"] = int(cell.text)
                            case 1:
                                player_perf["user_id"] = username_to_id(cell.text)
                            case 2:
                                player_perf["role"] = {
                                    "Мир": "town",
                                    "Маф": "mafia",
                                    "Шер": "sheriff",
                                    "Дон": "don",
                                }[cell.text]
                            case 3:
                                player_perf["points"] = float(cell.text)
                            case 4:
                                player_perf["elo_delta"] = int(cell.text)
                    player_performances.append(player_perf)

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
    Player_perfomances = []
    extract_main(Tournament_info)
    extract_games(Games, Player_perfomances)
    # print(Games, Player_perfomances)
    return Tournament_info, Games, Player_perfomances
