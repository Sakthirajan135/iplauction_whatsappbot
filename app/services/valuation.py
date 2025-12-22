
from typing import Dict, Optional
from app.database import get_db
from app.models import Player, BattingStats, BowlingStats
from sqlalchemy.orm import joinedload


class PlayerValuationModel:
    # Base prices by role (in INR Crores)
    BASE_PRICES = {
        'Batsman': 2.0,
        'Bowler': 2.0,
        'All-Rounder': 3.0,
        'Wicket-Keeper': 2.5,
    }
    
    # Weights for different factors
    WEIGHTS = {
        'batting_impact': 0.35,
        'bowling_impact': 0.35,
        'recent_form': 0.15,
        'role_scarcity': 0.10,
        'international_status': 0.05
    }
    
    def calculate_valuation(self, player_id: int) -> Optional[Dict]:
        """Calculate comprehensive player valuation"""
        try:
            with get_db() as db:
                player = db.query(Player).options(
                    joinedload(Player.batting_stats),
                    joinedload(Player.bowling_stats)
                ).filter(Player.id == player_id).first()
                
                if not player:
                    return None
                
                # Get IPL stats and convert to dicts
                ipl_batting = None
                ipl_bowling = None
                
                for stat in player.batting_stats:
                    if stat.format == 'IPL':
                        ipl_batting = {
                            'matches': stat.matches,
                            'runs': stat.runs,
                            'average': stat.average,
                            'strike_rate': stat.strike_rate,
                            'fifties': stat.fifties,
                            'hundreds': stat.hundreds,
                            'fours': stat.fours,
                            'sixes': stat.sixes
                        }
                        break
                
                for stat in player.bowling_stats:
                    if stat.format == 'IPL':
                        ipl_bowling = {
                            'matches': stat.matches,
                            'wickets': stat.wickets,
                            'average': stat.average,
                            'economy': stat.economy,
                            'five_wicket_haul': stat.five_wicket_haul
                        }
                        break
                
                # Calculate components using dict data
                batting_score = self._calculate_batting_impact_dict(ipl_batting)
                bowling_score = self._calculate_bowling_impact_dict(ipl_bowling)
                form_score = self._calculate_recent_form(player)
                scarcity_score = self._calculate_role_scarcity(player.role)
                international_score = self._calculate_international_status_dict(player)
                
                # Weighted total
                total_score = (
                    batting_score * self.WEIGHTS['batting_impact'] +
                    bowling_score * self.WEIGHTS['bowling_impact'] +
                    form_score * self.WEIGHTS['recent_form'] +
                    scarcity_score * self.WEIGHTS['role_scarcity'] +
                    international_score * self.WEIGHTS['international_status']
                )
                
                # Calculate price
                base_price = self.BASE_PRICES.get(player.role, 2.0)
                estimated_price = base_price * (1 + total_score)
                
                # Cap maximum price at 20 crores
                estimated_price = min(estimated_price, 20.0)
                
                return {
                    'player_id': player.id,
                    'player_name': player.name,
                    'role': player.role,
                    'estimated_price_cr': round(estimated_price, 2),
                    'breakdown': {
                        'batting_impact': round(batting_score, 3),
                        'bowling_impact': round(bowling_score, 3),
                        'recent_form': round(form_score, 3),
                        'role_scarcity': round(scarcity_score, 3),
                        'international_status': round(international_score, 3),
                        'total_score': round(total_score, 3)
                    },
                    'key_stats': self._get_key_stats_dict(ipl_batting, ipl_bowling)
                }
        except Exception as e:
            print(f"❌ Valuation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _calculate_batting_impact_dict(self, stats: Optional[Dict]) -> float:
        """Calculate batting impact score from dict"""
        if not stats or stats.get('matches', 0) < 5:
            return 0.0
        
        runs_score = min(stats.get('runs', 0) / 5000, 1.0)
        avg_score = min(stats.get('average', 0) / 50, 1.0)
        sr = stats.get('strike_rate', 0)
        sr_score = min((sr - 100) / 100, 1.0) if sr > 100 else 0.0
        
        boundaries = (stats.get('fours', 0) + stats.get('sixes', 0) * 2)
        boundary_score = min(boundaries / 1000, 1.0)
        
        impact = (
            runs_score * 0.4 +
            avg_score * 0.25 +
            sr_score * 0.25 +
            boundary_score * 0.10
        )
        
        return impact
    
    def _calculate_bowling_impact_dict(self, stats: Optional[Dict]) -> float:
        """Calculate bowling impact score from dict"""
        if not stats or stats.get('matches', 0) < 5:
            return 0.0
        
        wickets_score = min(stats.get('wickets', 0) / 200, 1.0)
        
        economy = stats.get('economy', 0)
        if economy > 0:
            economy_score = max(1 - (economy - 6) / 4, 0.0)
        else:
            economy_score = 0.0
        
        fifers_score = min(stats.get('five_wicket_haul', 0) / 5, 1.0)
        
        impact = (
            wickets_score * 0.5 +
            economy_score * 0.4 +
            fifers_score * 0.1
        )
        
        return impact
    
    def _calculate_international_status_dict(self, player: Player) -> float:
        """Calculate international status score"""
        # Simplified version - check if player has stats in other formats
        score = 0.0
        
        # This is a simple heuristic
        if player.country == 'India':
            score = 0.8
        
        return score
    
    def _get_key_stats_dict(self, batting: Optional[Dict], bowling: Optional[Dict]) -> Dict:
        """Extract key statistics from dicts"""
        stats = {}
        
        if batting and batting.get('matches', 0) > 0:
            stats['ipl_matches'] = batting['matches']
            stats['ipl_runs'] = batting['runs']
            stats['batting_avg'] = batting['average']
            stats['strike_rate'] = batting['strike_rate']
            stats['fifties'] = batting['fifties']
            stats['hundreds'] = batting['hundreds']
        
        if bowling and bowling.get('matches', 0) > 0:
            stats['ipl_wickets'] = bowling['wickets']
            stats['bowling_avg'] = bowling['average']
            stats['economy'] = bowling['economy']
            stats['five_wickets'] = bowling['five_wicket_haul']
        
        return stats
    
    def _calculate_batting_impact(self, stats: Optional[BattingStats]) -> float:
        """Calculate batting impact score (0-1)"""
        if not stats or stats.matches < 5:
            return 0.0
        
        # Normalize metrics
        runs_score = min(stats.runs / 5000, 1.0)  # 5000 runs = max
        avg_score = min(stats.average / 50, 1.0)  # 50 avg = max
        sr_score = min((stats.strike_rate - 100) / 100, 1.0) if stats.strike_rate > 100 else 0.0
        
        # Boundary hitting ability
        boundaries = (stats.fours + stats.sixes * 2)
        boundary_score = min(boundaries / 1000, 1.0)
        
        # Weighted average
        impact = (
            runs_score * 0.4 +
            avg_score * 0.25 +
            sr_score * 0.25 +
            boundary_score * 0.10
        )
        
        return impact
    
    def _calculate_bowling_impact(self, stats: Optional[BowlingStats]) -> float:
        """Calculate bowling impact score (0-1)"""
        if not stats or stats.matches < 5:
            return 0.0
        
        # Normalize metrics
        wickets_score = min(stats.wickets / 200, 1.0)  # 200 wickets = max
        
        # Economy - lower is better (IPL avg ~8)
        if stats.economy > 0:
            economy_score = max(1 - (stats.economy - 6) / 4, 0.0)
        else:
            economy_score = 0.0
        
        # Strike rate - lower is better
        if stats.strike_rate > 0:
            sr_score = max(1 - (stats.strike_rate - 15) / 15, 0.0)
        else:
            sr_score = 0.0
        
        # 5-wicket hauls bonus
        fifers_score = min(stats.five_wicket_haul / 5, 1.0)
        
        # Weighted average
        impact = (
            wickets_score * 0.4 +
            economy_score * 0.3 +
            sr_score * 0.2 +
            fifers_score * 0.1
        )
        
        return impact
    
    def _calculate_recent_form(self, player: Player) -> float:
        """Calculate recent form score (simplified - would need recent match data)"""
        # This is a placeholder - in production, analyze last 10 matches
        # For now, return moderate score
        return 0.5
    
    def _calculate_role_scarcity(self, role: str) -> float:
        """Calculate role scarcity multiplier"""
        scarcity_map = {
            'All-Rounder': 1.0,      # Most scarce
            'Wicket-Keeper': 0.8,
            'Bowler': 0.5,
            'Batsman': 0.3,
        }
        return scarcity_map.get(role, 0.5)
    
    def _calculate_international_status(self, player: Player) -> float:
        """Calculate international status score"""
        # Check if player has international stats
        with get_db() as db:
            has_test = any(s.format == 'TEST' and s.matches > 0 for s in player.batting_stats)
            has_odi = any(s.format == 'ODI' and s.matches > 0 for s in player.batting_stats)
            has_t20i = any(s.format == 'T20' and s.matches > 0 for s in player.batting_stats)
        
        score = 0.0
        if has_test:
            score += 0.4
        if has_odi:
            score += 0.3
        if has_t20i:
            score += 0.3
        
        return min(score, 1.0)
    
    def _get_key_stats(self, batting: Optional[BattingStats], bowling: Optional[BowlingStats]) -> Dict:
        """Extract key statistics"""
        stats = {}
        
        if batting and batting.matches > 0:
            stats['ipl_matches'] = batting.matches
            stats['ipl_runs'] = batting.runs
            stats['batting_avg'] = batting.average
            stats['strike_rate'] = batting.strike_rate
            stats['fifties'] = batting.fifties
            stats['hundreds'] = batting.hundreds
        
        if bowling and bowling.matches > 0:
            stats['ipl_wickets'] = bowling.wickets
            stats['bowling_avg'] = bowling.average
            stats['economy'] = bowling.economy
            stats['five_wickets'] = bowling.five_wicket_haul
        
        return stats
    
    def compare_players(self, player_ids: list) -> list:
        """Compare valuations of multiple players"""
        valuations = []
        for pid in player_ids:
            val = self.calculate_valuation(pid)
            if val:
                valuations.append(val)
        
        # Sort by estimated price
        valuations.sort(key=lambda x: x['estimated_price_cr'], reverse=True)
        return valuations


# Singleton instance
valuation_model = PlayerValuationModel()