
import google.generativeai as genai
from typing import Dict, List, Any
from app.config import get_settings

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)


class AIResponseGenerator:
    def __init__(self):
        try:
            self.model = genai.GenerativeModel("gemini-1.5-flash-latest")
        except Exception as e:
            print(f"⚠️ Error initializing Gemini for responses: {e}")
            try:
                self.model = genai.GenerativeModel("gemini-pro")
            except:
                self.model = None
    
    def format_whatsapp_response(
        self,
        query: str,
        data: Any,
        response_type: str = 'general'
    ) -> str:
        """Format data into WhatsApp-friendly response"""
        
        if response_type == 'player_stats':
            return self._format_player_stats(data)
        elif response_type == 'valuation':
            return self._format_valuation(data)
        elif response_type == 'comparison':
            return self._format_comparison(data)
        elif response_type == 'query_result':
            return self._format_query_result(data, query)
        elif response_type == 'similar_players':
            return self._format_similar_players(data)
        else:
            return self._generate_dynamic_response(query, data)
    
    def _format_player_stats(self, player: Dict) -> str:
        """Format player statistics"""
        # Use simple formatting without markdown - Twilio doesn't always support it
        response = f"📊 {player.get('name', 'Unknown')}\n"
        response += f"🏏 Role: {player.get('role', 'N/A')}\n"
        response += f"🌍 Country: {player.get('country', 'N/A')}\n\n"
        
        # Batting stats
        if 'batting_stats' in player:
            ipl_batting = next((s for s in player['batting_stats'] if s.get('format') == 'IPL'), None)
            if ipl_batting:
                response += "IPL Batting:\n"
                response += f"• Matches: {ipl_batting.get('matches', 0)}\n"
                response += f"• Runs: {ipl_batting.get('runs', 0)}\n"
                response += f"• Average: {ipl_batting.get('average', 0):.2f}\n"
                response += f"• Strike Rate: {ipl_batting.get('strike_rate', 0):.2f}\n"
                response += f"• 50s/100s: {ipl_batting.get('fifties', 0)}/{ipl_batting.get('hundreds', 0)}\n\n"
        
        # Bowling stats
        if 'bowling_stats' in player:
            ipl_bowling = next((s for s in player['bowling_stats'] if s.get('format') == 'IPL'), None)
            if ipl_bowling and ipl_bowling.get('wickets', 0) > 0:
                response += "IPL Bowling:\n"
                response += f"• Wickets: {ipl_bowling.get('wickets', 0)}\n"
                response += f"• Average: {ipl_bowling.get('average', 0):.2f}\n"
                response += f"• Economy: {ipl_bowling.get('economy', 0):.2f}\n"
                response += f"• 5W: {ipl_bowling.get('five_wicket_haul', 0)}\n"
        
        return response.strip()
    
    def _format_valuation(self, valuation: Dict) -> str:
        """Format player valuation"""
        response = f"💰 Auction Valuation: {valuation.get('player_name', 'Unknown')}\n\n"
        response += f"🎯 Estimated Price: ₹{valuation.get('estimated_price_cr', 0):.2f} Cr\n\n"
        
        breakdown = valuation.get('breakdown', {})
        response += "Impact Breakdown:\n"
        response += f"🏏 Batting: {breakdown.get('batting_impact', 0)*100:.1f}%\n"
        response += f"⚡ Bowling: {breakdown.get('bowling_impact', 0)*100:.1f}%\n"
        response += f"📈 Form: {breakdown.get('recent_form', 0)*100:.1f}%\n"
        response += f"🎲 Scarcity: {breakdown.get('role_scarcity', 0)*100:.1f}%\n\n"
        
        # Key stats
        stats = valuation.get('key_stats', {})
        if stats:
            response += "Key Stats:\n"
            if 'ipl_runs' in stats:
                response += f"• Runs: {stats['ipl_runs']}\n"
                response += f"• Avg: {stats.get('batting_avg', 0):.1f}\n"
            if 'ipl_wickets' in stats:
                response += f"• Wickets: {stats['ipl_wickets']}\n"
                response += f"• Economy: {stats.get('economy', 0):.2f}\n"
        
        return response.strip()
    
    def _format_comparison(self, players: List[Dict]) -> str:
        """Format player comparison"""
        response = "⚖️ *Player Comparison*\n\n"
        
        for i, p in enumerate(players[:5], 1):
            response += f"{i}. *{p.get('player_name', 'Unknown')}*\n"
            response += f"   ₹{p.get('estimated_price_cr', 0):.2f} Cr | {p.get('role', 'N/A')}\n"
            
            stats = p.get('key_stats', {})
            stat_parts = []
            if 'ipl_runs' in stats:
                stat_parts.append(f"{stats['ipl_runs']} runs")
            if 'ipl_wickets' in stats:
                stat_parts.append(f"{stats['ipl_wickets']} wkts")
            
            if stat_parts:
                response += f"   {' | '.join(stat_parts)}\n"
            response += "\n"
        
        return response.strip()
    
    def _format_query_result(self, result: Dict, query: str) -> str:
        """Format SQL query results"""
        if not result.get('success'):
            return f"❌ Sorry, I couldn't process that query.\n\n_{result.get('error', 'Unknown error')}_"
        
        data = result.get('data', [])
        if not data:
            return "📭 No results found for your query."
        
        response = f"📊 *Results for: {query[:50]}...*\n\n"
        
        # Show top results
        for i, row in enumerate(data[:10], 1):
            response += f"{i}. "
            # Format each field
            for key, value in row.items():
                if value is not None:
                    if isinstance(value, float):
                        response += f"{key}: {value:.2f} | "
                    else:
                        response += f"{key}: {value} | "
            response = response.rstrip(" | ") + "\n"
        
        if len(data) > 10:
            response += f"\n_...and {len(data) - 10} more results_"
        
        return response.strip()
    
    def _format_similar_players(self, players: List[Dict]) -> str:
        """Format similar players search results"""
        if not players:
            return "❌ No similar players found."
        
        response = "🔍 *Similar Players:*\n\n"
        
        for i, p in enumerate(players[:5], 1):
            response += f"{i}. *{p.get('name', 'Unknown')}*\n"
            response += f"   {p.get('role', 'N/A')} | {p.get('country', 'N/A')}\n"
            response += f"   Similarity: {p.get('similarity_score', 0)*100:.1f}%\n\n"
        
        return response.strip()
    
    def _generate_dynamic_response(self, query: str, data: Any) -> str:
        """Generate dynamic response using Gemini"""
        prompt = f"""You are an IPL auction expert WhatsApp bot. 

User Query: {query}

Data: {str(data)[:1000]}

Generate a concise, friendly WhatsApp response (max 500 chars):
- Use emojis sparingly (2-3 max)
- Be direct and informative
- Format with *bold* for emphasis
- Keep it conversational

Response:"""
        
        try:
            if not self.model:
                return "✅ Here's what I found:\n\n" + str(data)[:300]
            
            response = self.model.generate_content(prompt)
            return response.text.strip()[:500]  # Limit length
        except Exception as e:
            print(f"❌ Dynamic response error: {e}")
            return "✅ Here's what I found:\n\n" + str(data)[:300]
    
    def detect_intent(self, message: str) -> Dict[str, Any]:
        """Detect user intent from message"""
        message_lower = message.lower()
        
        # Player search
        if any(word in message_lower for word in ['stats', 'profile', 'about', 'tell me']):
            return {'intent': 'player_stats', 'type': 'search'}
        
        # Valuation
        if any(word in message_lower for word in ['price', 'value', 'worth', 'cost', 'valuation']):
            return {'intent': 'valuation', 'type': 'analysis'}
        
        # Comparison
        if any(word in message_lower for word in ['compare', 'vs', 'versus', 'better']):
            return {'intent': 'comparison', 'type': 'analysis'}
        
        # Hidden gems
        if any(word in message_lower for word in ['hidden gem', 'underrated', 'bargain', 'cheap']):
            return {'intent': 'hidden_gems', 'type': 'search'}
        
        # Rankings/Lists
        if any(word in message_lower for word in ['top', 'best', 'highest', 'most', 'list']):
            return {'intent': 'ranking', 'type': 'query'}
        
        # General query
        return {'intent': 'general_query', 'type': 'query'}


# Singleton instance
ai_response = AIResponseGenerator()