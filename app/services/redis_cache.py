
import redis
import json
from typing import Optional, Any
from app.config import get_settings

settings = get_settings()


class RedisCache:
    def __init__(self):
        self.client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        self.default_ttl = 3600  # 1 hour
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"❌ Redis GET error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"❌ Redis SET error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"❌ Redis DELETE error: {e}")
            return False
    
    def cache_player(self, player_id: int, player_data: dict, ttl: int = 7200):
        """Cache player data (2 hour TTL)"""
        key = f"player:{player_id}"
        return self.set(key, player_data, ttl)
    
    def get_player(self, player_id: int) -> Optional[dict]:
        """Get cached player data"""
        key = f"player:{player_id}"
        return self.get(key)
    
    def cache_query_result(self, query: str, result: Any, ttl: int = 1800):
        """Cache SQL query results (30 min TTL)"""
        key = f"query:{hash(query)}"
        return self.set(key, result, ttl)
    
    def get_query_result(self, query: str) -> Optional[Any]:
        """Get cached query result"""
        key = f"query:{hash(query)}"
        return self.get(key)
    
    def increment_search(self, player_name: str) -> int:
        """Track player search popularity"""
        key = f"search_count:{player_name.lower()}"
        try:
            count = self.client.incr(key)
            self.client.expire(key, 86400 * 30)  # 30 days
            return count
        except Exception as e:
            print(f"❌ Redis INCR error: {e}")
            return 0
    
    def get_popular_players(self, limit: int = 10) -> list:
        """Get most searched players"""
        try:
            pattern = "search_count:*"
            keys = self.client.keys(pattern)
            
            players = []
            for key in keys:
                count = int(self.client.get(key) or 0)
                player_name = key.replace("search_count:", "")
                players.append((player_name, count))
            
            # Sort by count and return top N
            players.sort(key=lambda x: x[1], reverse=True)
            return players[:limit]
        except Exception as e:
            print(f"❌ Redis popular players error: {e}")
            return []
    
    def health_check(self) -> bool:
        """Check Redis connection"""
        try:
            return self.client.ping()
        except:
            return False


# Singleton instance
redis_cache = RedisCache()