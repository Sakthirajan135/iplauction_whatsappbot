
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
from app.config import get_settings
import numpy as np

settings = get_settings()


class VectorStore:
    COLLECTION_NAME = "ipl_players"
    VECTOR_SIZE = 384  # all-MiniLM-L6-v2 embedding size
    
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=30
        )
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.COLLECTION_NAME not in collection_names:
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Created Qdrant collection: {self.COLLECTION_NAME}")
            else:
                print(f"✅ Qdrant collection exists: {self.COLLECTION_NAME}")
        except Exception as e:
            print(f"❌ Error ensuring collection: {e}")
    
    def create_player_text(self, player_data: Dict) -> str:
        """Create searchable text representation of player"""
        parts = [
            player_data.get('name', ''),
            player_data.get('role', ''),
            player_data.get('country', ''),
            player_data.get('batting_style', ''),
            player_data.get('bowling_style', ''),
        ]
        
        # Add batting stats summary
        if 'batting_stats' in player_data:
            for stat in player_data['batting_stats']:
                if stat.get('format') == 'IPL':
                    parts.append(f"IPL runs: {stat.get('runs', 0)}")
                    parts.append(f"Average: {stat.get('average', 0)}")
                    parts.append(f"Strike rate: {stat.get('strike_rate', 0)}")
        
        # Add bowling stats summary
        if 'bowling_stats' in player_data:
            for stat in player_data['bowling_stats']:
                if stat.get('format') == 'IPL':
                    parts.append(f"IPL wickets: {stat.get('wickets', 0)}")
                    parts.append(f"Economy: {stat.get('economy', 0)}")
        
        return " ".join([str(p) for p in parts if p])
    
    def add_player(self, player_id: int, player_data: Dict) -> bool:
        """Add or update player in vector store"""
        try:
            # Create text representation
            text = self.create_player_text(player_data)
            
            # Generate embedding
            embedding = self.encoder.encode(text).tolist()
            
            # Create point
            point = PointStruct(
                id=player_id,
                vector=embedding,
                payload={
                    'player_id': player_id,
                    'name': player_data.get('name', ''),
                    'role': player_data.get('role', ''),
                    'country': player_data.get('country', ''),
                    'text': text
                }
            )
            
            # Upsert to Qdrant
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[point]
            )
            
            print(f"✅ Added to Qdrant: {player_data.get('name', 'Unknown')}")
            return True
        except Exception as e:
            print(f"❌ Error adding to Qdrant: {e}")
            return False
    
    def search_similar_players(
        self, 
        query: str, 
        limit: int = 5,
        score_threshold: float = 0.5
    ) -> List[Dict]:
        """Search for similar players using semantic search"""
        try:
            # Generate query embedding
            query_vector = self.encoder.encode(query).tolist()
            
            # Search Qdrant
            results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Format results
            players = []
            for hit in results:
                players.append({
                    'player_id': hit.payload['player_id'],
                    'name': hit.payload['name'],
                    'role': hit.payload['role'],
                    'country': hit.payload['country'],
                    'similarity_score': hit.score
                })
            
            return players
        except Exception as e:
            print(f"❌ Error searching Qdrant: {e}")
            return []
    
    def find_hidden_gems(
        self,
        role: str,
        min_matches: int = 20,
        limit: int = 10
    ) -> List[Dict]:
        """Find underrated players (high performance, low popularity)"""
        try:
            # This would need additional filtering logic
            # For now, return similar players to the role
            return self.search_similar_players(role, limit=limit)
        except Exception as e:
            print(f"❌ Error finding hidden gems: {e}")
            return []
    
    def bulk_add_players(self, players: List[Dict]) -> int:
        """Bulk add multiple players"""
        success_count = 0
        for player in players:
            player_id = player.get('cricbuzz_id') or player.get('id')
            if player_id and self.add_player(player_id, player):
                success_count += 1
        return success_count
    
    def health_check(self) -> bool:
        """Check Qdrant connection"""
        try:
            self.client.get_collections()
            return True
        except:
            return False


# Singleton instance
vector_store = VectorStore()