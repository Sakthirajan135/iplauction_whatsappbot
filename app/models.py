
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Player(Base):
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cricbuzz_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)
    country = Column(String(100))
    role = Column(String(100))  # Batsman, Bowler, All-Rounder, Wicket-Keeper
    batting_style = Column(String(100))
    bowling_style = Column(String(100))
    profile_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    batting_stats = relationship("BattingStats", back_populates="player", cascade="all, delete-orphan")
    bowling_stats = relationship("BowlingStats", back_populates="player", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_player_name', 'name'),
        Index('idx_player_role', 'role'),
    )


class BattingStats(Base):
    __tablename__ = "batting_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), nullable=False)  # TEST, ODI, T20, IPL
    matches = Column(Integer, default=0)
    innings = Column(Integer, default=0)
    runs = Column(Integer, default=0)
    highest = Column(String(20))  # Can be "156*"
    average = Column(Float, default=0.0)
    strike_rate = Column(Float, default=0.0)
    fifties = Column(Integer, default=0)
    hundreds = Column(Integer, default=0)
    fours = Column(Integer, default=0)
    sixes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    player = relationship("Player", back_populates="batting_stats")
    
    __table_args__ = (
        Index('idx_batting_player_format', 'player_id', 'format'),
    )


class BowlingStats(Base):
    __tablename__ = "bowling_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), nullable=False)  # TEST, ODI, T20, IPL
    matches = Column(Integer, default=0)
    innings = Column(Integer, default=0)
    wickets = Column(Integer, default=0)
    average = Column(Float, default=0.0)
    economy = Column(Float, default=0.0)
    strike_rate = Column(Float, default=0.0)
    five_wicket_haul = Column(Integer, default=0)
    ten_wicket_haul = Column(Integer, default=0)
    best_figures = Column(String(20))  # "5/23"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    player = relationship("Player", back_populates="bowling_stats")
    
    __table_args__ = (
        Index('idx_bowling_player_format', 'player_id', 'format'),
    )


class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    short_name = Column(String(10))
    budget_remaining = Column(Float, default=0.0)
    squad_strength = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)