
import google.generativeai as genai
from sqlalchemy import text
from typing import Optional, Dict, List, Any
from app.config import get_settings
from app.database import get_db
from app.services.redis_cache import redis_cache
import re

settings = get_settings()

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)


class TextToSQL:
    FORBIDDEN_KEYWORDS = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
    
    SCHEMA_CONTEXT = """
Database Schema:

Table: players
- id (int, primary key)
- cricbuzz_id (int, unique)
- name (varchar)
- country (varchar)
- role (varchar) - Values: 'Batsman', 'Bowler', 'All-Rounder', 'Wicket-Keeper'
- batting_style (varchar)
- bowling_style (varchar)

Table: batting_stats
- id (int, primary key)
- player_id (int, foreign key to players.id)
- format (varchar) - Values: 'TEST', 'ODI', 'T20', 'IPL'
- matches (int)
- innings (int)
- runs (int)
- highest (varchar)
- average (float)
- strike_rate (float)
- fifties (int)
- hundreds (int)
- fours (int)
- sixes (int)

Table: bowling_stats
- id (int, primary key)
- player_id (int, foreign key to players.id)
- format (varchar) - Values: 'TEST', 'ODI', 'T20', 'IPL'
- matches (int)
- innings (int)
- wickets (int)
- average (float)
- economy (float)
- strike_rate (float)
- five_wicket_haul (int)
- ten_wicket_haul (int)

IMPORTANT RULES:
1. ALWAYS use table aliases (p for players, b for batting_stats, bw for bowling_stats)
2. ALWAYS specify format = 'IPL' when filtering IPL stats
3. For IPL runs, use: WHERE b.format = 'IPL'
4. Use INNER JOIN when stats are required
5. Use LEFT JOIN when player data is primary
6. Always LIMIT results to 20 or less

Examples:

1. "Top 5 batsmen by IPL runs"
SELECT p.name, b.runs, b.average, b.strike_rate
FROM players p
INNER JOIN batting_stats b ON p.id = b.player_id
WHERE b.format = 'IPL'
ORDER BY b.runs DESC
LIMIT 5;

2. "Best economy bowlers in IPL"
SELECT p.name, bw.economy, bw.wickets
FROM players p
INNER JOIN bowling_stats bw ON p.id = bw.player_id
WHERE bw.format = 'IPL' AND bw.wickets > 10
ORDER BY bw.economy ASC
LIMIT 10;

3. "All-rounders with 1000+ runs and 50+ wickets in IPL"
SELECT p.name, b.runs, bw.wickets
FROM players p
INNER JOIN batting_stats b ON p.id = b.player_id
INNER JOIN bowling_stats bw ON p.id = bw.player_id
WHERE p.role = 'All-Rounder'
AND b.format = 'IPL' AND b.runs > 1000
AND bw.format = 'IPL' AND bw.wickets > 50;

4. "Show all batsmen"
SELECT name, country, batting_style
FROM players
WHERE role = 'Batsman'
LIMIT 20;

5. "Batsmen with strike rate above 130"
SELECT p.name, b.strike_rate, b.runs
FROM players p
INNER JOIN batting_stats b ON p.id = b.player_id
WHERE b.format = 'IPL' AND b.strike_rate > 130
ORDER BY b.strike_rate DESC
LIMIT 20;
"""
    
    def __init__(self):
        # Use configured model with safe fallbacks
        configured = getattr(settings, 'GEMINI_MODEL', None) or 'gemini-1.5-flash'
        candidates = [configured, configured + '-latest', 'gemini-pro', 'text-bison@001']
        self.model = None
        for m in candidates:
            if not m:
                continue
            try:
                self.model = genai.GenerativeModel(m)
                print(f"✅ TextToSQL using model: {m}")
                break
            except Exception as e:
                print(f"⚠️ Model init failed for '{m}': {e}")
                self.model = None
    
    def generate_sql(self, user_query: str) -> Optional[str]:
        """Convert natural language to SQL query"""
        
        # Check cache first
        cached = redis_cache.get_query_result(f"sql:{user_query}")
        if cached:
            print("✅ Using cached SQL query")
            return cached
        
        prompt = f"""You are a SQL expert. Convert the following natural language question into a valid PostgreSQL SELECT query.

{self.SCHEMA_CONTEXT}

User Question: {user_query}

CRITICAL RULES:
1. Generate ONLY SELECT queries (no INSERT, UPDATE, DELETE, DROP)
2. Use proper INNER JOIN or LEFT JOIN syntax
3. ALWAYS use table aliases (p, b, bw)
4. For IPL statistics, ALWAYS include: WHERE format = 'IPL'
5. Limit results to maximum 20 rows
6. Use single quotes for string literals
7. Return ONLY the SQL query, no explanations or markdown
8. Do not include any text before or after the SQL query
9. The query must be a single valid SQL statement ending with semicolon

SQL Query:"""
        
        try:
            if not self.model:
                print("❌ Gemini model not initialized")
                return None
            
            response = self.model.generate_content(prompt)
            sql_query = response.text.strip()
            
            # Clean the SQL query
            sql_query = self._clean_sql(sql_query)
            
            # Validate safety
            if not self._is_safe_query(sql_query):
                print("❌ Unsafe SQL query blocked")
                return None
            
            # Cache the result
            redis_cache.set(f"sql:{user_query}", sql_query, ttl=3600)
            
            print(f"✅ Generated SQL: {sql_query[:100]}...")
            return sql_query
        except Exception as e:
            print(f"❌ Error generating SQL: {e}")
            return None
    
    def _clean_sql(self, sql: str) -> str:
        """Clean and normalize SQL query"""
        # Remove markdown code blocks
        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)
        
        # Remove extra whitespace
        sql = ' '.join(sql.split())
        
        # Ensure semicolon at end
        if not sql.endswith(';'):
            sql += ';'
        
        return sql.strip()
    
    def _is_safe_query(self, sql: str) -> bool:
        """Check if SQL query is safe to execute"""
        sql_upper = sql.upper()
        
        # Check for forbidden keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in sql_upper:
                return False
        
        # Must be a SELECT query
        if not sql_upper.strip().startswith('SELECT'):
            return False
        
        return True
    
    def execute_query(self, sql: str) -> Optional[List[Dict[str, Any]]]:
        """Execute SQL query and return results"""
        if not self._is_safe_query(sql):
            return None
        
        try:
            with get_db() as db:
                result = db.execute(text(sql))
                rows = result.fetchall()
                
                # Convert to list of dicts
                columns = result.keys()
                data = [dict(zip(columns, row)) for row in rows]
                
                print(f"✅ Query executed: {len(data)} rows returned")
                return data
        except Exception as e:
            print(f"❌ Query execution error: {e}")
            return None
    
    def natural_language_to_data(self, user_query: str) -> Optional[Dict]:
        """Complete pipeline: NL → SQL → Execute → Results"""
        # Generate SQL
        sql = self.generate_sql(user_query)
        if not sql:
            return {
                'success': False,
                'error': 'Could not generate valid SQL query'
            }
        
        # Execute query
        data = self.execute_query(sql)
        if data is None:
            return {
                'success': False,
                'error': 'Query execution failed',
                'sql': sql
            }
        
        return {
            'success': True,
            'sql': sql,
            'data': data,
            'count': len(data)
        }


# Singleton instance
text_to_sql = TextToSQL()