
import requests
from bs4 import BeautifulSoup
import time


def search_player_on_cricbuzz(player_name: str):
    """Search for a player on Cricbuzz and get their profile URL"""
    search_url = f"https://www.cricbuzz.com/api/html/search?q={player_name.replace(' ', '+')}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find player links
        links = soup.find_all('a', href=True)
        
        player_links = []
        for link in links:
            href = link.get('href', '')
            if '/profiles/' in href and href.startswith('/'):
                full_url = f"https://www.cricbuzz.com{href}"
                text = link.get_text(strip=True)
                player_links.append((text, full_url, href))
        
        return player_links
    
    except Exception as e:
        print(f"❌ Error searching: {e}")
        return []


def extract_id_and_slug(url: str):
    """Extract player ID and slug from URL"""
    # URL format: /profiles/1413/virat-kohli
    parts = url.strip('/').split('/')
    if len(parts) >= 3 and parts[0] == 'profiles':
        player_id = parts[1]
        player_slug = parts[2] if len(parts) > 2 else None
        return player_id, player_slug
    return None, None


def main():
    print("╔════════════════════════════════════════════╗")
    print("║   Cricbuzz Player URL Finder             ║")
    print("╚════════════════════════════════════════════╝\n")
    
    while True:
        player_name = input("\nEnter player name (or 'quit' to exit): ").strip()
        
        if player_name.lower() in ['quit', 'exit', 'q']:
            break
        
        if not player_name:
            continue
        
        print(f"\n🔍 Searching for: {player_name}...")
        results = search_player_on_cricbuzz(player_name)
        
        if not results:
            print("❌ No results found")
            continue
        
        print(f"\n✅ Found {len(results)} results:\n")
        
        for i, (name, full_url, rel_url) in enumerate(results[:10], 1):
            player_id, player_slug = extract_id_and_slug(rel_url)
            print(f"{i}. {name}")
            print(f"   URL: {full_url}")
            if player_id and player_slug:
                print(f"   For scraper: ({player_id}, '{player_slug}')")
            print()
        
        time.sleep(1)  # Rate limiting


if __name__ == "__main__":
    main()