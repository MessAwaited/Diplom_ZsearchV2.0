import logging
from datetime import datetime
from contextlib import contextmanager
from collections.abc import Generator
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from sqlalchemy.exc import SQLAlchemyError

from .models import engine, User, QueryHistory, Product

logger_session = logging.getLogger(__name__)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_session() -> Generator[SQLAlchemySession, None, None]:
    db: SQLAlchemySession | None = None
    try:
        db = SessionLocal()
        yield db
        db.commit()
    except SQLAlchemyError as e_sql:
        if db:
            db.rollback()
        logger_session.error(f"SQLAlchemyError: {e_sql}", exc_info=True)
        raise
    except Exception as e_generic:
        if db:
            db.rollback()
        logger_session.error(f"Generic error in session: {e_generic}", exc_info=True)
        raise
    finally:
        if db:
            db.close()

def get_user_data_by_username(username: str) -> dict | None:
    try:
        with get_db_session() as db:
            user_orm = db.query(User).filter(User.username == username).first()
            if user_orm:
                user_data = {
                    "id": user_orm.id,
                    "username": user_orm.username,
                    "password_hash": user_orm.password_hash
                }
                return user_data
            return None
    except Exception as e:
        logger_session.error(f"Error in get_user_data_by_username for {username}: {e}", exc_info=True)
        return None

def add_user(username: str, password: str) -> bool:
    try:
        with get_db_session() as db:
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                logger_session.warning(f"User {username} already exists.")
                return False
            new_user = User(username=username)
            new_user.set_password(password)
            db.add(new_user)
        logger_session.info(f"User {username} added.")
        return True
    except Exception as e:
        logger_session.error(f"Error adding user {username}: {e}", exc_info=True)
        return False

def save_user_query(user_id: int, query_text: str) -> None:
    try:
        with get_db_session() as db:
            query_entry = QueryHistory(
                user_id=user_id,
                query_text=query_text,
                timestamp=datetime.now().isoformat()
            )
            db.add(query_entry)
        logger_session.debug(f"Query saved for user_id {user_id}.")
    except Exception as e:
        logger_session.error(f"Error saving query for user_id {user_id}: {e}", exc_info=True)

def get_user_queries(user_id: int, limit: int = 20) -> list[str]:
    try:
        with get_db_session() as db:
            queries_orm = (
                db.query(QueryHistory.query_text)
                .filter(QueryHistory.user_id == user_id)
                .order_by(QueryHistory.timestamp.desc())
                .limit(limit)
                .all()
            )
            queries_list = [q[0] for q in queries_orm]
            return queries_list
    except Exception as e:
        logger_session.error(f"Error retrieving queries for user_id {user_id}: {e}", exc_info=True)
        return []

def save_products_batch(products_data: list[dict]) -> None:
    logger_session.debug(f"Mock save_products_batch called with {len(products_data)} products.")
    pass

def get_products_by_search_query(query: str) -> list[Product]:
    logger_session.debug(f"Mock get_products_by_search_query for '{query}'. Returning [].")
    return []