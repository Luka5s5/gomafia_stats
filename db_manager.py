import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, PlayerStats, Tournaments

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
        existing = session.query(PlayerStats).filter_by(user_id=data["user_id"]).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            print(f"Updated player {data['user_name']}")
        else:
            new_player = PlayerStats(**data)
            session.add(new_player)
            print(f"Added new player {data['user_name']}")

def username_to_id(username: str) -> int:
    return hash(username)

def user_exists(user_id: int) -> bool:
    with session_scope() as session:
        return session.query(PlayerStats).filter_by(user_id=user_id).first() is not None
# Optional: keep original function name for compatibility
# but now it uses the shared engine.
