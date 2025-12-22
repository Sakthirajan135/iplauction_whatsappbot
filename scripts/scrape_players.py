
import sys
sys.path.append('.')

from app.scrapers.cricbuzz_scraper import CricbuzzScraper, POPULAR_PLAYERS
from app.database import get_db
from app.models import Player, BattingStats, BowlingStats
from app.services.vector_store import vector_store
from app.services.redis_cache import redis_cache
import time


def save_player_to_db(player_data: dict):
    """Save scraped player data to PostgreSQL"""
    try:
        with get_db() as db:
            # Check if player exists
            existing_player = db.query(Player).filter(
                Player.cricbuzz_id == player_data['cricbuzz_id']
            ).first()
            
            if existing_player:
                print(f"⚠️ Player already exists: {player_data['name']}")
                player = existing_player
            else:
                # Create new player
                player = Player(
                    cricbuzz_id=player_data['cricbuzz_id'],
                    name=player_data.get('name', 'Unknown'),
                    country=player_data.get('country'),
                    role=player_data.get('role'),
                    batting_style=player_data.get('batting_style'),
                    bowling_style=player_data.get('bowling_style'),
                    profile_url=player_data.get('profile_url')
                )
                db.add(player)
                db.flush()  # Get player.id
                print(f"✅ Created player: {player.name}")
            
            # Save batting stats
            for stat in player_data.get('batting_stats', []):
                # Check if stat already exists
                existing_stat = db.query(BattingStats).filter(
                    BattingStats.player_id == player.id,
                    BattingStats.format == stat['format']
                ).first()
                
                if existing_stat:
                    # Update existing
                    for key, value in stat.items():
                        setattr(existing_stat, key, value)
                else:
                    # Create new
                    batting_stat = BattingStats(
                        player_id=player.id,
                        **stat
                    )
                    db.add(batting_stat)
            
            # Save bowling stats
            for stat in player_data.get('bowling_stats', []):
                # Check if stat already exists
                existing_stat = db.query(BowlingStats).filter(
                    BowlingStats.player_id == player.id,
                    BowlingStats.format == stat['format']
                ).first()
                
                if existing_stat:
                    # Update existing
                    for key, value in stat.items():
                        setattr(existing_stat, key, value)
                else:
                    # Create new
                    bowling_stat = BowlingStats(
                        player_id=player.id,
                        **stat
                    )
                    db.add(bowling_stat)
            
            db.commit()
            
            # Cache player data
            redis_cache.cache_player(player.id, player_data)
            
            # Add to vector store
            vector_store.add_player(player.id, player_data)
            
            return player.id
    
    except Exception as e:
        print(f"❌ Error saving player: {e}")
        return None


def scrape_and_ingest(player_list: list, rate_limit: float = 3.0):
    """Main scraping and ingestion pipeline"""
    scraper = CricbuzzScraper(rate_limit_delay=rate_limit)
    
    successful = 0
    failed = 0
    
    print(f"🚀 Starting to scrape {len(player_list)} players...")
    print(f"⏱️ Rate limit: {rate_limit}s between requests\n")
    
    for i, player_info in enumerate(player_list, 1):
        # Handle both tuple (id, slug) and int formats
        if isinstance(player_info, tuple):
            player_id, player_slug = player_info
            print(f"\n[{i}/{len(player_list)}] Scraping player: {player_slug} (ID: {player_id})")
        else:
            player_id = player_info
            player_slug = None
            print(f"\n[{i}/{len(player_list)}] Scraping player ID: {player_id}")
        
        # Scrape player data
        player_data = scraper.extract_player_details(player_id, player_slug)
        
        if player_data:
            # Save to database
            saved_id = save_player_to_db(player_data)
            
            if saved_id:
                successful += 1
                player_name = player_data.get('name', 'Unknown')
                print(f"✅ Successfully saved: {player_name}")
            else:
                failed += 1
        else:
            failed += 1
            print(f"❌ Failed to scrape player {player_id}")
        
        # Progress update
        if i % 5 == 0:
            print(f"\n📊 Progress: {successful} successful, {failed} failed\n")
    
    # Final summary
    print(f"\n{'='*50}")
    print(f"🎉 Scraping Complete!")
    print(f"{'='*50}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {(successful/(successful+failed)*100):.1f}%")
    print(f"{'='*50}\n")


def scrape_custom_players():
    """Scrape custom list of players"""
    print("Enter player information in format: ID,slug (one per line)")
    print("Examples:")
    print("  1413,virat-kohli")
    print("  253802,rohit-sharma")
    print("\nOr just IDs (comma-separated): 1413,253802,4608")
    print("Press Enter twice when done.\n")
    
    player_list = []
    
    # Try to read multiple lines
    print("Enter player info:")
    while True:
        line = input().strip()
        if not line:
            break
        
        # Check if it's the old format (just numbers)
        if ',' in line and not any(c.isalpha() for c in line):
            # Old format: comma-separated IDs
            try:
                ids = [int(x.strip()) for x in line.split(',') if x.strip()]
                # Convert to new format with None slugs
                player_list.extend([(id, None) for id in ids])
                break
            except ValueError:
                print("❌ Invalid format. Try again.")
                continue
        
        # New format: ID,slug
        if ',' in line:
            parts = line.split(',', 1)
            try:
                player_id = int(parts[0].strip())
                player_slug = parts[1].strip() if len(parts) > 1 else None
                player_list.append((player_id, player_slug))
            except ValueError:
                print("❌ Invalid format. Try again.")
        else:
            print("❌ Use format: ID,slug or just comma-separated IDs")
    
    if not player_list:
        print("❌ No valid players provided")
        return
    
    scrape_and_ingest(player_list)


def main():
    """Main entry point"""
    print("""
╔════════════════════════════════════════════╗
║   IPL Auction Bot - Data Ingestion Tool   ║
╚════════════════════════════════════════════╝
""")
    
    print("Choose an option:")
    print("1. Scrape popular players (predefined list)")
    print("2. Scrape custom players (enter IDs)")
    print("3. Quick test (first 3 popular players)")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == '1':
        print(f"\n📋 Will scrape {len(POPULAR_PLAYERS)} popular players")
        confirm = input("Continue? (y/n): ")
        if confirm.lower() == 'y':
            scrape_and_ingest(POPULAR_PLAYERS, rate_limit=3.0)
    
    elif choice == '2':
        scrape_custom_players()
    
    elif choice == '3':
        print("\n🧪 Test mode: Scraping first 3 players")
        scrape_and_ingest(POPULAR_PLAYERS[:3], rate_limit=2.0)
    
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    main()