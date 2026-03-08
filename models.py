from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PlayerStats(Base):
    __tablename__ = "player_stats"

    user_id = Column(Integer, primary_key=True)
    user_name = Column(String(50), nullable=False)
    elo = Column(Float, default=1000.0)
    referee_license = Column(Boolean, default=False)

    # Game counts
    town_games = Column(Integer, default=0)
    mafia_games = Column(Integer, default=0)
    sheriff_games = Column(Integer, default=0)
    don_games = Column(Integer, default=0)

    # Win counts
    town_wins = Column(Integer, default=0)
    mafia_wins = Column(Integer, default=0)
    sheriff_wins = Column(Integer, default=0)
    don_wins = Column(Integer, default=0)

    # Win rate adjustments (%)
    town_add = Column(Float, default=0.0)
    mafia_add = Column(Float, default=0.0)
    sheriff_add = Column(Float, default=0.0)
    don_add = Column(Float, default=0.0)

    def __repr__(self):
        return (
            f"<Player(user_id={self.user_id}, name='{self.user_name}', elo={self.elo})>"
        )


class Tournaments(Base):
    __tablename__ = "tournaments"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    stars = Column(Integer)
    is_rated = Column(Boolean)
    is_team = Column(Boolean)
    website_elo = Column(Float)
    date_begin = Column(DateTime)
    date_end = Column(DateTime)
    city = Column(String(255))
    country = Column(String(255))
    num_of_participants = Column(Integer)
    vk_link = Column(String(255))
    head_judge_id = Column(Integer)
    org_id = Column(Integer)
