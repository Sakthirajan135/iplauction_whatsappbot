
import sys
sys.path.append('.')

from app.database import get_db
from app.models import Player, BattingStats, BowlingStats
from app.services.vector_store import vector_store
from app.services.redis_cache import redis_cache


SAMPLE_PLAYERS = [
    {
        'cricbuzz_id': 1413,
        'name': 'Virat Kohli',
        'country': 'India',
        'role': 'Batsman',
        'batting_style': 'Right-hand Bat',
        'bowling_style': 'Right-arm Medium',
        'profile_url': 'https://www.cricbuzz.com/profiles/1413/virat-kohli',
        'batting_stats': [
            {
                'format': 'IPL',
                'matches': 237,
                'innings': 227,
                'runs': 7263,
                'highest': '113',
                'average': 36.50,
                'strike_rate': 130.02,
                'fifties': 50,
                'hundreds': 7,
                'fours': 674,
                'sixes': 235
            }
        ],
        'bowling_stats': []
    },
    {
        'cricbuzz_id': 253802,
        'name': 'Rohit Sharma',
        'country': 'India',
        'role': 'Batsman',
        'batting_style': 'Right-hand Bat',
        'bowling_style': 'Right-arm Offbreak',
        'profile_url': 'https://www.cricbuzz.com/profiles/253802/rohit-sharma',
        'batting_stats': [
            {
                'format': 'IPL',
                'matches': 243,
                'innings': 240,
                'runs': 6211,
                'highest': '109*',
                'average': 30.35,
                'strike_rate': 130.61,
                'fifties': 42,
                'hundreds': 2,
                'fours': 543,
                'sixes': 264
            }
        ],
        'bowling_stats': []
    },
    {
        'cricbuzz_id': 4608,
        'name': 'MS Dhoni',
        'country': 'India',
        'role': 'Wicket-Keeper',
        'batting_style': 'Right-hand Bat',
        'bowling_style': 'Right-arm Medium',
        'profile_url': 'https://www.cricbuzz.com/profiles/4608/ms-dhoni',
        'batting_stats': [
            {
                'format': 'IPL',
                'matches': 250,
                'innings': 235,
                'runs': 5243,
                'highest': '84*',
                'average': 39.12,
                'strike_rate': 135.92,
                'fifties': 24,
                'hundreds': 0,
                'fours': 329,
                'sixes': 229
            }
        ],
        'bowling_stats': []
    },
    {
        'cricbuzz_id': 4898,
        'name': 'Jasprit Bumrah',
        'country': 'India',
        'role': 'Bowler',
        'batting_style': 'Right-hand Bat',
        'bowling_style': 'Right-arm Fast',
        'profile_url': 'https://www.cricbuzz.com/profiles/4898/jasprit-bumrah',
        'batting_stats': [],
        'bowling_stats': [
            {
                'format': 'IPL',
                'matches': 133,
                'innings': 133,
                'wickets': 165,
                'average': 22.87,
                'economy': 7.18,
                'strike_rate': 19.1,
                'five_wicket_haul': 1,
                'ten_wicket_haul': 0
            }
        ]
    },
    {
        'cricbuzz_id': 4972,
        'name': 'Hardik Pandya',
        'country': 'India',
        'role': 'All-Rounder',
        'batting_style': 'Right-hand Bat',
        'bowling_style': 'Right-arm Fast-medium',
        'profile_url': 'https://www.cricbuzz.com/profiles/4972/hardik-pandya',
        'batting_stats': [
            {
                'format': 'IPL',
                'matches': 143,
                'innings': 128,
                'runs': 2644,
                'highest': '91',
                'average': 27.52,
                'strike_rate': 145.64,
                'fifties': 15,
                'hundreds': 0,
                'fours': 202,
                'sixes': 146
            }
        ],
        'bowling_stats': [
            {
                'format': 'IPL',
                'matches': 143,
                'innings': 126,
                'wickets': 63,
                'average': 35.65,
                'economy': 9.06,
                'strike_rate': 23.6,
                'five_wicket_haul': 0,
                'ten_wicket_haul': 0
            }
        ]
    },
]


def insert_sample_data():
    """Insert sample player data into database"""
    print("🔧 Inserting sample player data...\n")
    
    successful = 0
    
    for player_data in SAMPLE_PLAYERS:
        try:
            with get_db() as db:
                # Check if player exists
                existing = db.query(Player).filter(
                    Player.cricbuzz_id == player_data['cricbuzz_id']
                ).first()
                
                if existing:
                    print(f"⚠️  {player_data['name']} already exists, skipping...")
                    continue
                
                # Create player
                player = Player(
                    cricbuzz_id=player_data['cricbuzz_id'],
                    name=player_data['name'],
                    country=player_data['country'],
                    role=player_data['role'],
                    batting_style=player_data['batting_style'],
                    bowling_style=player_data['bowling_style'],
                    profile_url=player_data['profile_url']
                )
                db.add(player)
                db.flush()
                
                # Add batting stats
                for stat in player_data.get('batting_stats', []):
                    batting = BattingStats(player_id=player.id, **stat)
                    db.add(batting)
                
                # Add bowling stats
                for stat in player_data.get('bowling_stats', []):
                    bowling = BowlingStats(player_id=player.id, **stat)
                    db.add(bowling)
                
                db.commit()
                
                # Cache player
                redis_cache.cache_player(player.id, player_data)
                
                # Add to vector store
                vector_store.add_player(player.id, player_data)
                
                print(f"✅ {player_data['name']} inserted successfully")
                successful += 1
        
        except Exception as e:
            print(f"❌ Error inserting {player_data['name']}: {e}")
    
    print(f"\n{'='*50}")
    print(f"✅ Successfully inserted {successful}/{len(SAMPLE_PLAYERS)} players")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    print("╔════════════════════════════════════════════╗")
    print("║   Insert Sample Player Data (Testing)     ║")
    print("╚════════════════════════════════════════════╝\n")
    
    print("This will insert 5 sample players:")
    for p in SAMPLE_PLAYERS:
        print(f"  • {p['name']} ({p['role']})")
    
    confirm = input("\nContinue? (y/n): ")
    
    if confirm.lower() == 'y':
        insert_sample_data()
        
        print("\n✅ Data inserted! You can now:")
        print("1. Start the application: uvicorn app.main:app --reload")
        print("2. Test on WhatsApp")
        print("\nSample queries to try:")
        print("  • Show me Virat Kohli stats")
        print("  • What's Rohit Sharma's auction value?")
        print("  • Compare Virat Kohli and MS Dhoni")
    else:
        print("❌ Cancelled")