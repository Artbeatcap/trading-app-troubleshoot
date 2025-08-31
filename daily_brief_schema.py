from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# New data model for AH & Premarket movers
class MoveItem(BaseModel):
    """Represents an individual after-hours or pre-market mover."""

    ticker: str = Field(..., description="Stock ticker symbol")
    move: str = Field(..., description="Percent move string, e.g. '+5.2% AH' or '-3.4% pre'")
    why: str = Field(..., description="Concise reason for the move (earnings/guide/M&A/etc.)")
    source_url: Optional[str] = Field(default=None, description="Source headline URL")

class EarningsItem(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    note: str = Field(..., description="Earnings note/analysis")

class MorningBrief(BaseModel):
    subject_theme: str = Field(..., description="Theme for the subject line")
    date: str = Field(..., description="Date in readable format (e.g., 'August 20, 2025')")
    preheader: str = Field(..., description="Preheader text for email clients")
    logo_url: str = Field(default="", description="URL to logo image (optional)")
    market_overview: str = Field(..., description="Market overview section")
    macro_data: str = Field(..., description="Macro/Data section")
    # New movers lists
    ah_moves: List[MoveItem] = Field(default_factory=list, description="After-hours movers list")
    premarket_moves: List[MoveItem] = Field(default_factory=list, description="Premarket movers list")

    earnings: List[EarningsItem] = Field(default_factory=list, description="List of earnings items")
    sectors: Optional[str] = Field(default="", description="Sectors section (optional)")
    spy_s1: str = Field(..., description="SPY support level 1")
    spy_s2: str = Field(..., description="SPY support level 2")
    spy_r1: str = Field(..., description="SPY resistance level 1")
    spy_r2: str = Field(..., description="SPY resistance level 2")
    spy_r3: str = Field(..., description="SPY resistance level 3")
    extra_levels: Optional[str] = Field(default="", description="Additional levels (optional)")
    day_plan: List[str] = Field(..., description="List of day plan items")
    swing_plan: List[str] = Field(..., description="List of swing plan items")
    on_deck: Optional[str] = Field(default="", description="On deck section (optional)")
    cta_url: str = Field(..., description="Call-to-action URL")

    class Config:
        json_schema_extra = {
            "example": {
                "subject_theme": "Range vibes, retail on deck",
                "date": "August 20, 2025",
                "preheader": "Indexes flat, housing starts beat, Home Depot miss w/ upbeat tone; SPY levels to watch inside.",
                "logo_url": "",
                "market_overview": "Indexes are flat after yesterday's tight range; with light news flow, expect range trading unless levels break.",
                "macro_data": "Housing Starts surprised to the upside (1.43M vs 1.29M expected). Rate-cut expectations make housing-sensitive names a focal point.",
                "ah_moves": [
                    {"ticker": "PANW", "move": "+6% AH", "why": "Revenue/EPS beat; margin strength", "source_url": "https://example.com"}
                ],
                "premarket_moves": [
                    {"ticker": "HD", "move": "-3.1% pre", "why": "Earnings miss", "source_url": "https://example.com"}
                ],
                "earnings": [
                    {
                        "ticker": "HD",
                        "note": "Small miss on rev/EPS ($45.3B vs $45.41B; $4.68 vs $4.72) but reiterated FY; momentum in smaller projects; retail sympathy with TGT tomorrow."
                    },
                    {
                        "ticker": "PANW",
                        "note": "+6% AH on revenue/EPS beat ($2.54B vs $2.50B; $0.95 vs $0.89); margin strength; watch cyber basket for continuation."
                    }
                ],
                "sectors": "",
                "spy_s1": "642.13",
                "spy_s2": "641.34/640",
                "spy_r1": "643.95",
                "spy_r2": "644.70",
                "spy_r3": "645.50+",
                "extra_levels": "",
                "day_plan": [
                    "Fade extremes of the range until it breaks; size down in chop.",
                    "Track HD for retail read-through and position into TGT tomorrow.",
                    "Cybersecurity leaders (PANW) for trend continuation on pullbacks."
                ],
                "swing_plan": [
                    "Housing-linked names if data strength + rate-cut narrative persists; look for bases resolving higher.",
                    "If SPY reclaims 644.70/645.50 and holds, consider adding to strength; lose 640 with momentum and tighten risk."
                ],
                "on_deck": "Target (TGT) earnings tomorrow; monitor retail read-through.",
                "cta_url": "https://optionsplunge.com"
            }
        }


