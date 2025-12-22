
from typing import Optional, Dict, List
from app.database import get_db
from sqlalchemy import text


class SimpleQueryRouter:
    """Handle common queries with predefined SQL"""
    
    QUERY_PATTERNS = {
        'top_batsmen': ['top', 'batsmen', 'runs'],
        'top_bowlers': ['top', 'bowlers', 'wickets'],
        'best_strike_rate': ['strike', 'rate', 'batsmen'],
        'best_economy': ['economy', 'bowlers'],
        'all_rounders': ['all', 'rounder', 'all-rounder'],
        'list_players': ['list', 'all', 'players', 'show'],
    }
    
    def match_query(self, query: str) -> Optional[str]:
        """Match query to predefined pattern"""
        query_lower = query.lower()
        
        # Top batsmen by runs
        if any(word in query_lower for word in ['top', 'best']) and any(word in query_lower for word in ['batsmen', 'batsman', 'runs']):
            return 'top_batsmen'
        
        # Top bowlers by wickets
        if any(word in query_lower for word in ['top', 'best']) and any(word in query_lower for word in ['bowlers', 'bowler', 'wickets']):
            return 'top_bowlers'
        
        # Best strike rate
        if 'strike' in query_lower and 'rate' in query_lower:
            return 'best_strike_rate'
        
        # Best economy
        if 'economy' in query_lower:
            return 'best_economy'
        
        # All-rounders
        if 'all' in query_lower and 'round' in query_lower:
            return 'all_rounders'
        
        # List players
        if any(word in query_lower for word in ['list', 'show all', 'all players']):
            return 'list_players'
        
        return None
    
    def execute_query(self, pattern: str) -> Optional[Dict]:
        """Execute predefined query"""
        sql_map = {
            'top_batsmen': """
                SELECT p.name, b.runs, b.average, b.strike_rate, b.hundreds, b.fifties
                FROM players p
                INNER JOIN batting_stats b ON p.id = b.player_id
                WHERE b.format = 'IPL'
                ORDER BY b.runs DESC
                LIMIT 5;
            """,
            'top_bowlers': """
                SELECT p.name, bw.wickets, bw.average, bw.economy
                FROM players p
                INNER JOIN bowling_stats bw ON p.id = bw.player_id
                WHERE bw.format = 'IPL'
                ORDER BY bw.wickets DESC
                LIMIT 5;
            """,
            'best_strike_rate': """
                SELECT p.name, b.strike_rate, b.runs, b.average
                FROM players p
                INNER JOIN batting_stats b ON p.id = b.player_id
                WHERE b.format = 'IPL' AND b.matches > 10
                ORDER BY b.strike_rate DESC
                LIMIT 5;
            """,
            'best_economy': """
                SELECT p.name, bw.economy, bw.wickets, bw.average
                FROM players p
                INNER JOIN bowling_stats bw ON p.id = bw.player_id
                WHERE bw.format = 'IPL' AND bw.wickets > 10
                ORDER BY bw.economy ASC
                LIMIT 5;
            """,
            'all_rounders': """
                SELECT p.name, p.role, b.runs, bw.wickets
                FROM players p
                LEFT JOIN batting_stats b ON p.id = b.player_id AND b.format = 'IPL'
                LEFT JOIN bowling_stats bw ON p.id = bw.player_id AND bw.format = 'IPL'
                WHERE p.role = 'All-Rounder'
                LIMIT 10;
            """,
            'list_players': """
                SELECT name, role, country
                FROM players
                ORDER BY name
                LIMIT 20;
            """
        }
        
        sql = sql_map.get(pattern)
        if not sql:
            return None
        
        try:
            with get_db() as db:
                result = db.execute(text(sql))
                rows = result.fetchall()
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in rows]
                
                return {
                    'success': True,
                    'sql': sql,
                    'data': data,
                    'count': len(data)
                }
        except Exception as e:
            print(f"❌ Simple query error: {e}")
            return None


# Singleton
simple_router = SimpleQueryRouter()
