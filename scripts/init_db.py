
import sys
sys.path.append('.')

from app.database import init_db, engine
from app.models import Base

def main():
    """Create all database tables"""
    print("🔧 Initializing database...")
    
    try:
        # Drop all tables (use with caution!)
        # Base.metadata.drop_all(bind=engine)
        # print("🗑️ Dropped existing tables")
        
        # Create all tables
        init_db()
        print("✅ Database initialization complete")
        
        # Print created tables
        print("\n📋 Created tables:")
        for table in Base.metadata.sorted_tables:
            print(f"  • {table.name}")
    
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()