"""
Database initialization and initialization data
"""

from .session import init_database
from .models import Base


def initialize_database(database_url: str = None):
    """
    Initialize database
    Create all tables and set default configuration
    """
    #Initialize database connection and table
    db_manager = init_database(database_url)

    #Create table
    db_manager.create_tables()

    # Initialize default settings (imported from settings module to avoid circular imports)
    from ..config.settings import init_default_settings
    init_default_settings()

    return db_manager


def reset_database(database_url: str = None):
    """
    Reset database (drop all tables and recreate)
    Warning: All data will be lost!
    """
    db_manager = init_database(database_url)

    # Delete all tables
    db_manager.drop_tables()
    print("All tables have been deleted")

    # Recreate all tables
    db_manager.create_tables()
    print("All tables have been recreated")

    #Initialize default settings
    from ..config.settings import init_default_settings
    init_default_settings()

    print("Database reset completed")
    return db_manager


def check_database_connection(database_url: str = None) -> bool:
    """
    Check whether the database connection is normal
    """
    try:
        db_manager = init_database(database_url)
        with db_manager.get_db() as db:
            # Try executing a simple query
            db.execute("SELECT 1")
        print("Database connection is normal")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


if __name__ == "__main__":
    # When running this script directly, initialize the database
    import argparse

    parser = argparse.ArgumentParser(description="database initialization script")
    parser.add_argument("--reset", action="store_true", help="Reset database (delete all data)")
    parser.add_argument("--check", action="store_true", help="Check database connection")
    parser.add_argument("--url", help="database connection string")

    args = parser.parse_args()

    if args.check:
        check_database_connection(args.url)
    elif args.reset:
        confirm = input("Warning: This will delete all data! Confirm reset? (y/N): ")
        if confirm.lower() == 'y':
            reset_database(args.url)
        else:
            print("Operation canceled")
    else:
        initialize_database(args.url)
