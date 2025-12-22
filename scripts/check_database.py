
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import get_db
from app.models import Player, BattingStats, BowlingStats
from sqlalchemy.orm import joinedload


def check_database():
    """Check what's in the database"""
    print("="*60)
    print("DATABASE DIAGNOSTIC")
    print("="*60)
    
    with get_db() as db:
        # Check players
        players = db.query(Player).all()
        print(f"\n📊 Total Players: {len(players)}")
        
        if not players:
            print("❌ No players in database!")
            return
        
        print("\nPlayers:")
        for p in players:
            print(f"  • {p.id}: {p.name} ({p.role})")
        
        # Check batting stats
        print("\n" + "="*60)
        print("BATTING STATS")
        print("="*60)
        
        batting_stats = db.query(BattingStats).all()
        print(f"\nTotal Batting Records: {len(batting_stats)}")
        
        for stat in batting_stats:
            player = db.query(Player).filter(Player.id == stat.player_id).first()
            print(f"\n{player.name} - {stat.format}:")
            print(f"  Matches: {stat.matches}")
            print(f"  Runs: {stat.runs}")
            print(f"  Average: {stat.average}")
            print(f"  Strike Rate: {stat.strike_rate}")
        
        # Check bowling stats
        print("\n" + "="*60)
        print("BOWLING STATS")
        print("="*60)
        
        bowling_stats = db.query(BowlingStats).all()
        print(f"\nTotal Bowling Records: {len(bowling_stats)}")
        
        for stat in bowling_stats:
            player = db.query(Player).filter(Player.id == stat.player_id).first()
            print(f"\n{player.name} - {stat.format}:")
            print(f"  Matches: {stat.matches}")
            print(f"  Wickets: {stat.wickets}")
            print(f"  Economy: {stat.economy}")
        
        # Test query
        print("\n" + "="*60)
        print("TEST QUERY: Top 5 Batsmen by IPL Runs")
        print("="*60)
        
        from sqlalchemy import text
        sql = """
            SELECT p.name, b.runs, b.average, b.strike_rate
            FROM players p
            INNER JOIN batting_stats b ON p.id = b.player_id
            WHERE b.format = 'IPL'
            ORDER BY b.runs DESC
            LIMIT 5;
        """
        
        result = db.execute(text(sql))
        rows = result.fetchall()
        
        if rows:
            print("\nResults:")
            for i, row in enumerate(rows, 1):
                print(f"{i}. {row[0]}: {row[1]} runs (avg: {row[2]}, SR: {row[3]})")
        else:
            print("\n❌ No results! This means batting_stats table is empty.")


if __name__ == "__main__":
    check_database()