"""Database session management"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import os
import logging

from .models import Base

logger = logging.getLogger(__name__)


def _build_sqlalchemy_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url[len("postgresql://"):]
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url[len("postgres://"):]
    return database_url


class DatabaseSessionManager:
    """Database session manager"""

    def __init__(self, database_url: str = None):
        if database_url is None:
            env_url = os.environ.get("APP_DATABASE_URL") or os.environ.get("DATABASE_URL")
            if env_url:
                database_url = env_url
            else:
                # Prefer APP_DATA_DIR so packaged builds keep data beside the executable.
                data_dir = os.environ.get('APP_DATA_DIR') or os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'data'
                )
                db_path = os.path.join(data_dir, 'database.db')
                # Make sure the directory exists
                os.makedirs(data_dir, exist_ok=True)
                database_url = f"sqlite:///{db_path}"

        self.database_url = _build_sqlalchemy_url(database_url)
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False} if self.database_url.startswith("sqlite") else {},
            echo=False,  # Set to True to view all SQL statements
            pool_pre_ping=True  # Connection pool pre-check
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_db(self) -> Generator[Session, None, None]:
        """Get the context manager for a database session
        Usage example:
            with get_db() as db:
                # Use db for database operations
                pass"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """transaction scope context manager
        Usage example:
            with session_scope() as session:
                # Database operations
                pass"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all tables (use with caution)"""
        Base.metadata.drop_all(bind=self.engine)

    def migrate_tables(self):
        """Database migration - adding missing columns
        Used to update table structure without deleting data"""
        if not self.database_url.startswith("sqlite"):
            logger.info("Non-SQLite databases, skip automatic migration")
            return

        # New columns to check and add
        migrations = [
            # (table name, column name, column type)
            ("accounts", "cpa_uploaded", "BOOLEAN DEFAULT 0"),
            ("accounts", "cpa_uploaded_at", "DATETIME"),
            ("accounts", "source", "VARCHAR(20) DEFAULT 'register'"),
            ("accounts", "subscription_type", "VARCHAR(20)"),
            ("accounts", "subscription_at", "DATETIME"),
            ("accounts", "cookies", "TEXT"),
            ("proxies", "is_default", "BOOLEAN DEFAULT 0"),
        ]

        # Make sure all current tables exist before applying column migrations.
        Base.metadata.create_all(bind=self.engine)

        with self.engine.connect() as conn:
            # Data migration: Unify old custom_domain records to moe_mail
            try:
                conn.execute(text("UPDATE email_services SET service_type='moe_mail' WHERE service_type='custom_domain'"))
                conn.execute(text("UPDATE accounts SET email_service='moe_mail' WHERE email_service='custom_domain'"))
                conn.commit()
            except Exception as e:
                logger.warning(f"Error migrating custom_domain -> moe_mail: {e}")

            for table_name, column_name, column_type in migrations:
                try:
                    # Check if column exists
                    result = conn.execute(text(
                        f"SELECT * FROM pragma_table_info('{table_name}') WHERE name='{column_name}'"
                    ))
                    if result.fetchone() is None:
                        # Column does not exist, add it
                        logger.info(f"Add column {table_name}.{column_name}")
                        conn.execute(text(
                            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                        ))
                        conn.commit()
                        logger.info(f"Column {table_name}.{column_name} added successfully")
                except Exception as e:
                    logger.warning(f"Error migrating column {table_name}.{column_name}: {e}")


# Global database session manager instance
_db_manager: DatabaseSessionManager = None


def init_database(database_url: str = None) -> DatabaseSessionManager:
    """Initialize the database session manager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseSessionManager(database_url)
        _db_manager.create_tables()
        # Perform database migration
        _db_manager.migrate_tables()
    return _db_manager


def get_session_manager() -> DatabaseSessionManager:
    """Get the database session manager"""
    if _db_manager is None:
        raise RuntimeError("The database has not been initialized, please call init_database() first")
    return _db_manager


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Shortcut function to get database session"""
    manager = get_session_manager()
    db = manager.SessionLocal()
    try:
        yield db
    finally:
        db.close()
