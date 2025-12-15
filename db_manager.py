from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import *
from models import Base, PlayerStats, Tournaments

# Database configuration
DB_URL = "postgresql://mafia_user:secure_password_123@localhost:5435/mafia_analytics"

def init_database():
    # Create engine with connection pooling
    engine = create_engine(
        DB_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    Session = sessionmaker(bind=engine)
    return Session

def insert_tournament_data(data):
    Session = init_database()
    session = Session()
    
    try:
        # Check if player exists
        existing = session.query(Tournaments).filter_by(id=data['id']).first()
        
        if existing:
            # Update existing record
            for key, value in data.items():
                setattr(existing, key, value)
            print(f"Updated tournament {data['name']}")
        else:
            # Create new record
            new_tournament = Tournaments(**data)
            session.add(new_tournament)
            print(f"Added new tournament {data['name']}")
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error: {str(e)}")
    finally:
        session.close()

def insert_player_data(data):
    Session = init_database()
    session = Session()
    
    try:
        # Check if player exists
        existing = session.query(PlayerStats).filter_by(user_id=data['user_id']).first()
        
        if existing:
            # Update existing record
            for key, value in data.items():
                setattr(existing, key, value)
            print(f"Updated player {data['user_name']}")
        else:
            # Create new record
            new_player = PlayerStats(**data)
            session.add(new_player)
            print(f"Added new player {data['user_name']}")
        
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error: {str(e)}")
    finally:
        session.close()



if __name__ == "__main__":
    session_maker = init_database()
    print("Database initialized successfully!")
    print("Table created: player_stats")


def username_to_id(username: str) -> int:
    return hash(username)
