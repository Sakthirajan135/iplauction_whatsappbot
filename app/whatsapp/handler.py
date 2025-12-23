"""WhatsApp message handler - orchestrates all services"""
from typing import Dict, Optional
import sys

# Import with error handling
try:
    from app.services.redis_cache import redis_cache
except Exception as e:
    print(f"⚠️ Redis cache import failed: {e}")
    redis_cache = None

try:
    from app.services.vector_store import vector_store
except Exception as e:
    print(f"⚠️ Vector store import failed: {e}")
    vector_store = None

try:
    from app.services.text_to_sql import text_to_sql
except Exception as e:
    print(f"⚠️ Text-to-SQL import failed: {e}")
    text_to_sql = None

try:
    from app.services.valuation import valuation_model
except Exception as e:
    print(f"⚠️ Valuation model import failed: {e}")
    valuation_model = None

try:
    from app.services.ai_response import ai_response
except Exception as e:
    print(f"⚠️ AI response import failed: {e}")
    ai_response = None

from app.database import get_db
from app.models import Player
from sqlalchemy import or_


class WhatsAppHandler:
    def process_message(self, message: str, sender: str) -> str:
        """Main message processing pipeline"""
        
        # Check if AI response service is available
        if not ai_response:
            return "❌ Service temporarily unavailable. Please try again later."
        
        # Detect intent
        intent_data = ai_response.detect_intent(message)
        intent = intent_data['intent']
        
        print(f"🎯 Intent detected: {intent}")
        
        # Route to appropriate handler
        if intent == 'player_stats':
            return self._handle_player_stats(message)
        elif intent == 'valuation':
            return self._handle_valuation(message)
        elif intent == 'comparison':
            return self._handle_comparison(message)
        elif intent == 'hidden_gems':
            return self._handle_hidden_gems(message)
        elif intent == 'ranking':
            return self._handle_ranking(message)
        else:
            return self._handle_general_query(message)
    
    def _handle_player_stats(self, message: str) -> str:
        """Handle player statistics request"""
        # Extract player name
        player_name = self._extract_player_name(message)
        
        if not player_name:
            return "Please specify a player name.\n\nExample: Show me Virat Kohli stats"
        
        # Track search popularity
        redis_cache.increment_search(player_name)
        
        # Search for player
        player_data = self._find_player(player_name)
        
        if not player_data:
            # Try vector search for similar players
            similar = vector_store.search_similar_players(player_name, limit=3)
            if similar:
                response = f"❌ Player '{player_name}' not found.\n\n*Did you mean:*\n"
                for p in similar:
                    response += f"• {p['name']}\n"
                return response
            return f"Player '{player_name}' not found in database."
        
        # Format response
        response = ai_response.format_whatsapp_response(
            message,
            player_data,
            response_type='player_stats'
        )
        
        # Debug: Log response length
        print(f"📝 Generated response ({len(response)} chars): {response[:100]}")
        
        # Safety check
        if not response or len(response.strip()) < 10:
            return f"📊 *{player_data['name']}*\n🏏 Role: {player_data['role']}\n🌍 Country: {player_data['country']}\n\n⚠️ Stats temporarily unavailable."
        
        return response
    
    def _handle_valuation(self, message: str) -> str:
        """Handle player valuation request"""
        player_name = self._extract_player_name(message)
        
        if not player_name:
            return "❌ Please specify a player name.\n\nExample: What's Virat Kohli's auction value?"
        
        # Find player
        player = self._find_player_by_name(player_name)
        
        if not player:
            return f"❌ Player '{player_name}' not found."
        
        # Calculate valuation using simple version (no session issues)
        try:
            from app.services.simple_valuation import simple_valuation
            valuation = simple_valuation.calculate_valuation(player.id)
        except Exception as e:
            print(f"⚠️ Simple valuation failed: {e}, trying original")
            valuation = valuation_model.calculate_valuation(player.id) if valuation_model else None
        
        if not valuation:
            return "❌ Unable to calculate valuation for this player."
        
        return ai_response.format_whatsapp_response(
            message,
            valuation,
            response_type='valuation'
        )
    
    def _handle_comparison(self, message: str) -> str:
        """Handle player comparison request"""
        # Extract player names (simplified)
        players = self._extract_multiple_players(message)
        
        if len(players) < 2:
            return "❌ Please specify at least 2 players to compare.\n\nExample: _Compare Virat Kohli and Rohit Sharma_"
        
        # Get valuations
        player_ids = []
        for name in players:
            player = self._find_player_by_name(name)
            if player:
                player_ids.append(player.id)
        
        if len(player_ids) < 2:
            return "❌ Could not find enough players to compare."
        
        valuations = valuation_model.compare_players(player_ids)
        
        return ai_response.format_whatsapp_response(
            message,
            valuations,
            response_type='comparison'
        )
    
    def _handle_hidden_gems(self, message: str) -> str:
        """Handle hidden gems discovery"""
        # Extract role if specified
        role = None
        for r in ['batsman', 'bowler', 'all-rounder', 'wicket-keeper']:
            if r in message.lower():
                role = r.title()
                break
        
        # Use vector search to find underrated players
        query = f"underrated {role or 'player'} good performance low cost"
        similar = vector_store.search_similar_players(query, limit=5)
        
        if not similar:
            return "❌ No hidden gems found at the moment."
        
        return ai_response.format_whatsapp_response(
            message,
            similar,
            response_type='similar_players'
        )
    
    def _handle_ranking(self, message: str) -> str:
        """Handle ranking/top players queries"""
        # Try simple router first (no AI needed)
        try:
            from app.services.simple_queries import simple_router
            pattern = simple_router.match_query(message)
            
            if pattern:
                print(f"📊 Using simple query pattern: {pattern}")
                result = simple_router.execute_query(pattern)
                if result and result.get('success'):
                    return ai_response.format_whatsapp_response(
                        message,
                        result,
                        response_type='query_result'
                    )
        except Exception as e:
            print(f"⚠️ Simple router failed: {e}")
        
        # Fallback to Text-to-SQL
        if text_to_sql:
            result = text_to_sql.natural_language_to_data(message)
            return ai_response.format_whatsapp_response(
                message,
                result,
                response_type='query_result'
            )
        
        return "❌ Sorry, I couldn't process that ranking query."
    
    def _handle_general_query(self, message: str) -> str:
        """Handle general queries using Text-to-SQL"""
        # Try simple router first
        try:
            from app.services.simple_queries import simple_router
            pattern = simple_router.match_query(message)
            
            if pattern:
                print(f"📊 Using simple query pattern: {pattern}")
                result = simple_router.execute_query(pattern)
                if result and result.get('success'):
                    return ai_response.format_whatsapp_response(
                        message,
                        result,
                        response_type='query_result'
                    )
        except Exception as e:
            print(f"⚠️ Simple router failed: {e}")
        
        # Try Text-to-SQL
        if text_to_sql:
            result = text_to_sql.natural_language_to_data(message)
            
            if result.get('success'):
                return ai_response.format_whatsapp_response(
                    message,
                    result,
                    response_type='query_result'
                )
        
        # Fallback to vector search
        if vector_store:
            similar = vector_store.search_similar_players(message, limit=5)
            if similar:
                return ai_response.format_whatsapp_response(
                    message,
                    similar,
                    response_type='similar_players'
                )
        
        return "Sorry, I couldn't understand that query. Try:\n\nShow me Virat Kohli stats\nWhat's Rohit Sharma's auction value?\nTop 5 batsmen by IPL runs"
    
    def _extract_player_name(self, message: str) -> Optional[str]:
        """Extract player name from message"""
        # Normalize message
        message_lower = message.lower()
        
        # Remove common query words
        stop_words = {
            'show', 'me', 'about', 'stats', 'profile', 'tell', 'value', 'worth', 
            'price', 'what', 'is', 'the', 'his', 'her', 'auction', 'find',
            'get', 'display', 'give', 'whats', "what's", 'of', 'for', 'a', 'an',
            'which', 'country', 'role', 'team'
        }
        
        # Split and clean
        words = message.split()
        
        # Try to find known players first
        known_players = ['virat kohli', 'rohit sharma', 'ms dhoni', 'jasprit bumrah', 'hardik pandya']
        for player in known_players:
            if player in message_lower:
                return player.title()
        
        # Extract capitalized words
        name_parts = []
        for word in words:
            # Skip stop words
            if word.lower() in stop_words:
                continue
            # Keep capitalized words or words with caps
            if word and (word[0].isupper() or any(c.isupper() for c in word)):
                # Clean the word
                clean_word = ''.join(c for c in word if c.isalpha())
                if len(clean_word) > 2:
                    name_parts.append(clean_word)
        
        if name_parts:
            # Return up to 3 words (first name + middle + last name)
            return ' '.join(name_parts[:3])
        
        return None
    
    def _extract_multiple_players(self, message: str) -> list:
        """Extract multiple player names from message"""
        # Split by 'and', 'vs', ','
        parts = message.replace(' and ', '|').replace(' vs ', '|').replace(',', '|').split('|')
        
        players = []
        for part in parts:
            name = self._extract_player_name(part)
            if name:
                players.append(name)
        
        return players
    
    def _find_player_by_name(self, name: str) -> Optional[Player]:
        """Find player by name in database"""
        try:
            with get_db() as db:
                player = db.query(Player).filter(
                    Player.name.ilike(f"%{name}%")
                ).first()
                return player
        except:
            return None
    
    def _find_player(self, name: str) -> Optional[Dict]:
        """Find player with full stats"""
        try:
            with get_db() as db:
                from sqlalchemy.orm import joinedload
                
                player = db.query(Player).options(
                    joinedload(Player.batting_stats),
                    joinedload(Player.bowling_stats)
                ).filter(
                    Player.name.ilike(f"%{name}%")
                ).first()
                
                if not player:
                    return None
                
                # Convert to dict
                return {
                    'id': player.id,
                    'name': player.name,
                    'role': player.role,
                    'country': player.country,
                    'batting_style': player.batting_style,
                    'bowling_style': player.bowling_style,
                    'batting_stats': [
                        {
                            'format': s.format,
                            'matches': s.matches,
                            'innings': s.innings,
                            'runs': s.runs,
                            'average': s.average,
                            'strike_rate': s.strike_rate,
                            'fifties': s.fifties,
                            'hundreds': s.hundreds,
                        } for s in player.batting_stats
                    ],
                    'bowling_stats': [
                        {
                            'format': s.format,
                            'matches': s.matches,
                            'wickets': s.wickets,
                            'average': s.average,
                            'economy': s.economy,
                            'five_wicket_haul': s.five_wicket_haul,
                        } for s in player.bowling_stats
                    ]
                }
        except Exception as e:
            print(f"❌ Error finding player: {e}")
            return None


# Singleton instance - lazy initialization to avoid import errors
_whatsapp_handler = None

def get_whatsapp_handler():
    """Get or create WhatsApp handler singleton"""
    global _whatsapp_handler
    if _whatsapp_handler is None:
        _whatsapp_handler = WhatsAppHandler()
    return _whatsapp_handler

# For backward compatibility
whatsapp_handler = get_whatsapp_handler()