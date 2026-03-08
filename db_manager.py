import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Games, PlayerPerformances, Tournaments, Users

# Database configuration – use environment variable or hardcode
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mafia_user:secure_password_123@localhost:5435/mafia_analytics",
)

# Create engine once with connection pooling
engine = create_engine(
    DB_URL,
    pool_size=5,  # number of connections to keep in pool
    max_overflow=10,  # extra connections allowed when pool is full
    pool_timeout=30,  # seconds to wait for a connection from pool
    pool_recycle=1800,  # recycle connections after 30 minutes
    echo=False,  # set to True for SQL logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database():
    """Create tables if they don't exist. Call once at startup."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def insert_tournament_data(data):
    with session_scope() as session:
        existing = session.query(Tournaments).filter_by(id=data["id"]).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            print(f"Updated tournament {data['name']}")
        else:
            new_tournament = Tournaments(**data)
            session.add(new_tournament)
            print(f"Added new tournament {data['name']}")


def insert_player_data(data):
    with session_scope() as session:
        existing = session.query(Users).filter_by(id=data["id"]).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            print(f"Updated player {data['username']}")
        else:
            new_player = Users(**data)
            session.add(new_player)
            print(f"Added new player {data['username']}")


def insert_full_tournament(tournament_data, games_data, performances_data):
    """
    Insert or update a tournament, its games, and player performances.

    Parameters:
        tournament_data : dict
            Contains tournament fields: id, name, stars, is_rated, is_team,
            website_elo, date_begin, date_end, city, country, num_of_participants,
            vk_link, head_judge_id, org_id.
        games_data : list of dict
            Each dict has keys: round_num, table_num, judge_id, win.
        performances_data : list of dict
            Each dict has keys: seat, user_id, role, points, elo_delta (optional).
            Expected to be in order: first 10 entries for the first game,
            next 10 for the second game, etc.

    Raises:
        ValueError if the number of performances is not 10 × number of games.
    """
    with session_scope() as session:
        # ----- Upsert tournament -----
        tournament_id = tournament_data["id"]
        tournament = session.query(Tournaments).filter_by(id=tournament_id).first()
        if tournament:
            for key, value in tournament_data.items():
                setattr(tournament, key, value)
            print(f"Updated tournament {tournament_data.get('name', tournament_id)}")
        else:
            tournament = Tournaments(**tournament_data)
            session.add(tournament)
            session.flush()  # ensure it's persisted (though we already have the id)
            print(f"Added new tournament {tournament_data.get('name', tournament_id)}")

        # ----- Remove old games for this tournament (cascades to performances) -----
        deleted = session.query(Games).filter_by(tournament_id=tournament_id).delete()
        if deleted:
            print(f"Deleted {deleted} existing games for tournament {tournament_id}")

        # ----- Validate performance count -----
        expected = len(games_data) * 10
        if len(performances_data) != expected:
            raise ValueError(
                f"Performance count mismatch: expected {expected} (10 per game), "
                f"got {len(performances_data)}"
            )

        # ----- Insert games and their performances -----
        perf_index = 0
        for game_dict in games_data:
            # Create game
            game = Games(
                tournament_id=tournament_id,
                round_num=game_dict["round_num"],
                table_num=game_dict["table_num"],
                judge_id=game_dict["judge_id"],
                result=game_dict["win"],  # 'win' maps to result
            )
            session.add(game)
            session.flush()  # obtain game.id

            # Add the 10 performances for this game
            for seat_num in range(1, 11):
                perf = performances_data[perf_index]
                # Optional sanity check
                if perf["seat"] != seat_num:
                    print(
                        f"Warning: expected seat {seat_num}, got {perf['seat']} for game {game.id}"
                    )

                performance = PlayerPerformances(
                    game_id=game.id,
                    seat=perf["seat"],
                    player_id=perf["user_id"],
                    points=perf["points"],
                    role=perf["role"],
                    elo_delta=perf.get("elo_delta", 0.0),
                )
                session.add(performance)
                perf_index += 1

        print(
            f"Inserted {len(games_data)} games and {len(performances_data)} performances for tournament {tournament_id}"
        )


def username_to_id(username: str) -> int:
    with session_scope() as session:
        return session.query(Users).filter_by(username=username).first().id


def user_exists(user_id: int) -> bool:
    with session_scope() as session:
        return session.query(Users).filter_by(id=user_id).first() is not None


# Optional: keep original function name for compatibility
# but now it uses the shared engine.
