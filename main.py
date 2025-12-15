from db_manager import insert_player_data, insert_tournament_data
from scraper import scrape_tournament, scrape_user


def scrape_users(min_id, max_id):
    for idx in range(min_id, max_id):
        user_data = None
        try:
            user_data = scrape_user(idx)
        except:
            pass
        if user_data:
            insert_player_data(user_data)
        else:
            print(f"Cannot parse user with id {idx}")


if __name__ == '__main__':
    tournament_info, games, performances = scrape_tournament(1842)
    insert_tournament_data(tournament_data)
