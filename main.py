import asyncio
import logging

from db_manager import (init_database, insert_player_data,
                        insert_tournament_data, user_exists)
from http_client import HttpClient
from scraper import scrape_tournament, scrape_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scrape_users_range(
    client: HttpClient, min_id: int, max_id: int, concurrency: int = 5
):
    """
    Scrape users with IDs in [min_id, max_id) in parallel, with limited concurrency.
    Each user is scraped and inserted in a separate task, but no more than
    `concurrency` tasks run simultaneously.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def process_one(user_id: int):
        async with semaphore:
            exists = await asyncio.to_thread(user_exists, user_id)
            if exists:
                logger.info(f"User {user_id} already in database, skipping")
                return
            try:
                user_data = await scrape_user(client, user_id)
                if user_data:
                    # insert_player_data is synchronous – run in a thread
                    await asyncio.to_thread(insert_player_data, user_data)
                    logger.info(f"Inserted user {user_id}")
                else:
                    logger.warning(f"No data for user {user_id}")
            except Exception as e:
                logger.error(f"Error scraping user {user_id}: {e}")

    # Create a task for each user ID
    tasks = [process_one(user_id) for user_id in range(min_id, max_id)]
    await asyncio.gather(*tasks)

async def scrape_tournaments_range(
    client: HttpClient, min_id: int, max_id: int, concurrency: int = 5
):
    """
    Scrape users with IDs in [min_id, max_id) in parallel, with limited concurrency.
    Each user is scraped and inserted in a separate task, but no more than
    `concurrency` tasks run simultaneously.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def process_one(tournament_id: int):
        async with semaphore:
            try:
                tournament_data = await scrape_tournament(client, tournament_id)
                if tournament_data:
                    # insert_player_data is synchronous – run in a thread
                    await asyncio.to_thread(insert_tournament_data, tournament_data[0])
                    logger.info(f"Inserted tournament {tournament_id}")
                else:
                    logger.warning(f"No data for tournament {tournament_id}")
            except Exception as e:
                logger.error(f"Error scraping tournament {tournament_id}: {e}")

    # Create a task for each user ID
    tasks = [process_one(user_id) for user_id in range(min_id, max_id)]
    await asyncio.gather(*tasks)


async def main():
    init_database()
    """
    Main async entry point: sets up HTTP client, scrapes a tournament and a range of users.
    """
    async with HttpClient() as client:
        # try:
        #     tournament_info, games, performances = await scrape_tournament(client, 1842)
        #     # Insert tournament data (synchronous) in a thread
        #     await asyncio.to_thread(insert_tournament_data, tournament_info)
        #     # You might also want to insert games and performances similarly
        #     logger.info(f"Inserted tournament {1842}")
        # except Exception as e:
        #     logger.error(f"Failed to scrape tournament 1842: {e}")
        #
        await scrape_tournaments_range(client, 1400, 1500)


if __name__ == "__main__":
    asyncio.run(main())
