
import sys
sys.path.append('.')

from app.services.vector_store import vector_store
from app.database import get_db
from app.models import Player
from sqlalchemy.orm import joinedload


def populate_vector_store():
    """Populate Qdrant with existing player data"""
    print("🔧 Populating Qdrant vector store...")
    
    try:
        with get_db() as db:
            # Get all players with stats
            players = db.query(Player).options(
                joinedload(Player.batting_stats),
                joinedload(Player.bowling_stats)
            ).all()
            
            print(f"📊 Found {len(players)} players in database")
            
            if not players:
                print("⚠️ No players found. Run scraper first.")
                return
            
            successful = 0
            
            for player in players:
                # Convert to dict
                player_data = {
                    'cricbuzz_id': player.cricbuzz_id,
                    'name': player.name,
                    'role': player.role,
                    'country': player.country,
                    'batting_style': player.batting_style,
                    'bowling_style': player.bowling_style,
                    'batting_stats': [
                        {
                            'format': s.format,
                            'runs': s.runs,
                            'average': s.average,
                            'strike_rate': s.strike_rate,
                        } for s in player.batting_stats
                    ],
                    'bowling_stats': [
                        {
                            'format': s.format,
                            'wickets': s.wickets,
                            'economy': s.economy,
                        } for s in player.bowling_stats
                    ]
                }
                
                # Add to vector store
                if vector_store.add_player(player.id, player_data):
                    successful += 1
            
            print(f"\n✅ Successfully added {successful}/{len(players)} players to Qdrant")
    
    except Exception as e:
        print(f"❌ Error populating Qdrant: {e}")


def test_vector_search():
    """Test vector search functionality"""
    print("\n🧪 Testing vector search...")
    
    test_queries = [
        "aggressive opener batsman",
        "death over specialist bowler",
        "all-rounder with good strike rate",
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        results = vector_store.search_similar_players(query, limit=3)
        
        if results:
            for i, player in enumerate(results, 1):
                print(f"  {i}. {player['name']} ({player['role']}) - Score: {player['similarity_score']:.3f}")
        else:
            print("  No results found")


def main():
    """Main entry point"""
    print("""
╔════════════════════════════════════════════╗
║   IPL Auction Bot - Qdrant Setup Tool    ║
╚════════════════════════════════════════════╝
""")
    
    print("Choose an option:")
    print("1. Populate Qdrant with existing players")
    print("2. Test vector search")
    print("3. Both")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == '1':
        populate_vector_store()
    elif choice == '2':
        test_vector_search()
    elif choice == '3':
        populate_vector_store()
        test_vector_search()
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    main()