"""
BriefInput schema for optimized market brief generation.
Defines the compact data structures used in the two-stage pipeline.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Level:
    """Support/resistance level for a ticker."""
    price: float
    label: str


@dataclass
class Ticker:
    """Market ticker with price and change data."""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    levels: List[Level]


@dataclass
class Event:
    """Economic or market event."""
    time: str
    event: str
    impact: str
    why: str


@dataclass
class BriefInput:
    """Compact input structure for brief generation."""
    # Market indices
    indices: List[Ticker]
    
    # Interest rates
    rates: List[Ticker]
    
    # Economic events
    events: List[Event]
    
    # Top movers
    movers: List[Ticker]

    # Key levels
    levels: List[Level]
    
    # Market headlines
    headlines: List[str]
    
    # Additional context
    date: str
    market_session: str = "premarket"
