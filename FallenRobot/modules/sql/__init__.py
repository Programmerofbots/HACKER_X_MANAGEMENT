from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from FallenRobot import DB_URI
from FallenRobot import LOGGER as log

if DB_URI and DB_URI.startswith("postgres://"):
    DB_URI = DB_URI.replace("postgres://", "postgresql://", 1)


BASE = declarative_base()
SESSION = None


def start() -> scoped_session:
    if not DB_URI:
        log.warning("[PostgreSQL] DATABASE_URL not set; SQL features will be disabled.")
        return None

    engine = create_engine(DB_URI, client_encoding="utf8")
    log.info("[PostgreSQL] Connecting to database......")
    BASE.metadata.bind = engine
    BASE.metadata.create_all(engine)
    return scoped_session(sessionmaker(bind=engine, autoflush=False))


try:
    SESSION = start()
except Exception as e:
    log.exception(f"[PostgreSQL] Failed to connect due to {e}")
    log.warning("[PostgreSQL] Continuing without SQL database support.")
    SESSION = None

if SESSION is not None:
    log.info("[PostgreSQL] Connection successful, session started.")
