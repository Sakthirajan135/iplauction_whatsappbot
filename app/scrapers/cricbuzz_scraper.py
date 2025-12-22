"""Cricbuzz player data scraper"""
import requests
from bs4 import BeautifulSoup
import time
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import re


class CricbuzzScraper:
    BASE_URL = "https://www.cricbuzz.com"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    def __init__(self, rate_limit_delay: float = 2.0):
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch page with retry logic"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)  # Rate limiting
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
            return None
    
    def extract_player_details(self, cricbuzz_id: int, player_name_slug: str = None) -> Optional[Dict]:
        """Extract complete player details from Cricbuzz profile"""
        # Try with player name slug first if provided
        if player_name_slug:
            url = f"{self.BASE_URL}/profiles/{cricbuzz_id}/{player_name_slug}"
        else:
            url = f"{self.BASE_URL}/profiles/{cricbuzz_id}"
        
        soup = self._fetch_page(url)
        
        if not soup:
            return None
        
        try:
            player_data = {
                'cricbuzz_id': cricbuzz_id,
                'profile_url': url
            }
            
            # Extract basic info
            player_data.update(self._extract_bio(soup))
            
            # Debug: Print extracted name
            print(f"   Extracted name: {player_data.get('name', 'NOT FOUND')}")
            
            # Extract batting stats
            batting_stats = self._extract_batting_stats(soup)
            player_data['batting_stats'] = batting_stats
            print(f"   Batting stats: {len(batting_stats)} formats found")
            
            # Extract bowling stats
            bowling_stats = self._extract_bowling_stats(soup)
            player_data['bowling_stats'] = bowling_stats
            print(f"   Bowling stats: {len(bowling_stats)} formats found")
            
            print(f"✅ Scraped: {player_data.get('name', 'Unknown')}")
            return player_data
            
        except Exception as e:
            print(f"❌ Error parsing player {cricbuzz_id}: {e}")
            return None
    
    def _extract_bio(self, soup: BeautifulSoup) -> Dict:
        """Extract player bio information"""
        bio = {}
        
        # Try multiple methods to find player name
        # Method 1: Look for h1 with player name
        name_elem = soup.find('h1', class_='cb-font-40')
        if not name_elem:
            name_elem = soup.find('h1')
        if not name_elem:
            # Method 2: Look in title tag
            title = soup.find('title')
            if title:
                bio['name'] = title.text.split('|')[0].strip()
        
        if name_elem:
            bio['name'] = name_elem.text.strip()
        
        # Fallback: extract from URL or use Unknown
        if 'name' not in bio or not bio['name']:
            bio['name'] = 'Unknown Player'
        
        # Try to find player info in various div structures
        # Method 1: Standard info section
        info_section = soup.find('div', class_='cb-col cb-col-40')
        if info_section:
            text_items = info_section.find_all('div', class_='cb-col cb-col-100')
            for item in text_items:
                text = item.text.strip()
                if ':' in text:
                    key, value = text.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if 'born' in key or 'birth' in key:
                        # Extract country from birth info
                        parts = value.split(',')
                        if len(parts) >= 2:
                            bio['country'] = parts[-1].strip()
                    elif 'role' in key:
                        bio['role'] = value
                    elif 'batting' in key and 'style' in key:
                        bio['batting_style'] = value
                    elif 'bowling' in key and 'style' in key:
                        bio['bowling_style'] = value
        
        # Method 2: Look for text containing keywords
        all_text = soup.get_text()
        
        # Try to find role if not found
        if 'role' not in bio:
            if 'Batsman' in all_text or 'Batter' in all_text:
                bio['role'] = 'Batsman'
            elif 'Bowler' in all_text:
                bio['role'] = 'Bowler'
            elif 'All-Rounder' in all_text or 'Allrounder' in all_text:
                bio['role'] = 'All-Rounder'
            elif 'Wicket-Keeper' in all_text or 'Wicketkeeper' in all_text:
                bio['role'] = 'Wicket-Keeper'
        
        # Set defaults for missing fields
        if 'country' not in bio:
            bio['country'] = 'Unknown'
        if 'role' not in bio:
            bio['role'] = 'Unknown'
        if 'batting_style' not in bio:
            bio['batting_style'] = 'Unknown'
        if 'bowling_style' not in bio:
            bio['bowling_style'] = 'Unknown'
        
        return bio
    
    def _extract_batting_stats(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract batting statistics for all formats"""
        stats = []
        
        # Find batting table
        batting_section = soup.find('div', text=re.compile(r'Batting.*Career Summary'))
        if not batting_section:
            return stats
        
        table = batting_section.find_next('table', class_='cb-col-100')
        if not table:
            return stats
        
        # Parse table rows
        rows = table.find_all('tr')[1:]  # Skip header
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 8:
                continue
            
            try:
                stat = {
                    'format': cols[0].text.strip().upper(),
                    'matches': self._safe_int(cols[1].text.strip()),
                    'innings': self._safe_int(cols[2].text.strip()),
                    'runs': self._safe_int(cols[4].text.strip()),
                    'highest': cols[5].text.strip(),
                    'average': self._safe_float(cols[6].text.strip()),
                    'strike_rate': self._safe_float(cols[8].text.strip()) if len(cols) > 8 else 0.0,
                    'hundreds': self._safe_int(cols[9].text.strip()) if len(cols) > 9 else 0,
                    'fifties': self._safe_int(cols[10].text.strip()) if len(cols) > 10 else 0,
                    'fours': self._safe_int(cols[11].text.strip()) if len(cols) > 11 else 0,
                    'sixes': self._safe_int(cols[12].text.strip()) if len(cols) > 12 else 0,
                }
                stats.append(stat)
            except Exception as e:
                print(f"⚠️ Error parsing batting row: {e}")
                continue
        
        return stats
    
    def _extract_bowling_stats(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract bowling statistics for all formats"""
        stats = []
        
        # Find bowling table
        bowling_section = soup.find('div', text=re.compile(r'Bowling.*Career Summary'))
        if not bowling_section:
            return stats
        
        table = bowling_section.find_next('table', class_='cb-col-100')
        if not table:
            return stats
        
        # Parse table rows
        rows = table.find_all('tr')[1:]  # Skip header
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 7:
                continue
            
            try:
                stat = {
                    'format': cols[0].text.strip().upper(),
                    'matches': self._safe_int(cols[1].text.strip()),
                    'innings': self._safe_int(cols[2].text.strip()),
                    'wickets': self._safe_int(cols[4].text.strip()),
                    'average': self._safe_float(cols[6].text.strip()),
                    'economy': self._safe_float(cols[7].text.strip()) if len(cols) > 7 else 0.0,
                    'strike_rate': self._safe_float(cols[8].text.strip()) if len(cols) > 8 else 0.0,
                    'five_wicket_haul': self._safe_int(cols[10].text.strip()) if len(cols) > 10 else 0,
                    'ten_wicket_haul': self._safe_int(cols[11].text.strip()) if len(cols) > 11 else 0,
                }
                stats.append(stat)
            except Exception as e:
                print(f"⚠️ Error parsing bowling row: {e}")
                continue
        
        return stats
    
    @staticmethod
    def _safe_int(value: str) -> int:
        """Safely convert string to int"""
        try:
            return int(value.replace(',', '').replace('-', '0'))
        except:
            return 0
    
    @staticmethod
    def _safe_float(value: str) -> float:
        """Safely convert string to float"""
        try:
            return float(value.replace(',', '').replace('-', '0'))
        except:
            return 0.0


# Popular player IDs with name slugs (ID, slug) format
POPULAR_PLAYERS = [
    (1413, 'virat-kohli'),
    (253802, 'rohit-sharma'),
    (4608, 'ms-dhoni'),
    (4898, 'jasprit-bumrah'),
    (6900, 'kl-rahul'),
    (4972, 'hardik-pandya'),
    (8733, 'rishabh-pant'),
    (5792, 'ravindra-jadeja'),
    (253977, 'shubman-gill'),
    (5971, 'mohammed-shami'),
    (8272, 'suryakumar-yadav'),
    (9062, 'yuzvendra-chahal'),
    (6525, 'shreyas-iyer'),
    (30045, 'ishan-kishan'),
    (9441, 'washington-sundar'),
]