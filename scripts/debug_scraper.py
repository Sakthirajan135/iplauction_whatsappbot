
import sys
sys.path.append('.')

from app.scrapers.cricbuzz_scraper import CricbuzzScraper
import json


def debug_player(player_id: int, player_slug: str):
    """Debug scrape a single player"""
    print(f"🔍 Debugging player: {player_slug} (ID: {player_id})")
    print(f"URL: https://www.cricbuzz.com/profiles/{player_id}/{player_slug}\n")
    
    scraper = CricbuzzScraper(rate_limit_delay=0)
    
    # Fetch page
    url = f"{scraper.BASE_URL}/profiles/{player_id}/{player_slug}"
    soup = scraper._fetch_page(url)
    
    if not soup:
        print("❌ Failed to fetch page")
        return
    
    print("✅ Page fetched successfully\n")
    
    # Debug: Show title
    title = soup.find('title')
    if title:
        print(f"📄 Page Title: {title.text}\n")
    
    # Debug: Show all h1 tags
    print("=== H1 Tags ===")
    h1_tags = soup.find_all('h1')
    for i, h1 in enumerate(h1_tags, 1):
        print(f"{i}. {h1.get_text(strip=True)}")
    print()
    
    # Debug: Show player info divs
    print("=== Player Info Sections ===")
    info_divs = soup.find_all('div', class_='cb-col')
    for i, div in enumerate(info_divs[:10], 1):
        text = div.get_text(strip=True)
        if text and len(text) < 200 and ':' in text:
            print(f"{i}. {text}")
    print()
    
    # Try extracting with current scraper
    print("=== Attempting to Extract Data ===")
    player_data = scraper.extract_player_details(player_id, player_slug)
    
    if player_data:
        print("\n✅ Extraction Result:")
        print(json.dumps({
            'name': player_data.get('name'),
            'country': player_data.get('country'),
            'role': player_data.get('role'),
            'batting_style': player_data.get('batting_style'),
            'bowling_style': player_data.get('bowling_style'),
            'batting_stats_count': len(player_data.get('batting_stats', [])),
            'bowling_stats_count': len(player_data.get('bowling_stats', [])),
        }, indent=2))
        
        # Show stats details
        if player_data.get('batting_stats'):
            print("\n📊 Batting Stats:")
            for stat in player_data['batting_stats']:
                print(f"  {stat.get('format')}: {stat.get('runs')} runs, {stat.get('average')} avg")
        
        if player_data.get('bowling_stats'):
            print("\n⚡ Bowling Stats:")
            for stat in player_data['bowling_stats']:
                print(f"  {stat.get('format')}: {stat.get('wickets')} wickets, {stat.get('economy')} econ")
    else:
        print("\n❌ Failed to extract data")
        
        # Show raw HTML snippet for debugging
        print("\n=== First 1000 chars of HTML ===")
        print(str(soup)[:1000])


if __name__ == "__main__":
    # Test with Virat Kohli
    print("╔════════════════════════════════════════════╗")
    print("║        Cricbuzz Scraper Debug Tool        ║")
    print("╚════════════════════════════════════════════╝\n")
    
    # You can change these to test different players
    test_players = [
        (1413, 'virat-kohli'),
        (253802, 'rohit-sharma'),
        (4608, 'ms-dhoni'),
    ]
    
    print("Choose a player to debug:")
    for i, (pid, slug) in enumerate(test_players, 1):
        print(f"{i}. {slug} (ID: {pid})")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(test_players):
            player_id, player_slug = test_players[idx]
            print()
            debug_player(player_id, player_slug)
        else:
            print("Invalid choice")
    except ValueError:
        print("Invalid input")