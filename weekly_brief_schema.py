from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Levels(BaseModel):
    s1: str
    s2: str
    r1: str
    r2: str
    r3: str

class Recap(BaseModel):
    index_blurb: str = Field(..., description="Short index/breadth blurb for last week")
    sector_blurb: str = Field(..., description="1-2 sentences about sector rotations & themes")
    movers_bullets: List[str] = Field(default_factory=list, description="Top movers bullet list, max 10")
    flow_blurb: str = Field(..., description="1-2 sentences about options sentiment (put/call + notable flow)")

class WeekAhead(BaseModel):
    macro_bullets: List[str] = Field(default_factory=list, description="Macro events for the week ahead")
    earnings_bullets: List[str] = Field(default_factory=list, description="Earnings events for the week ahead")

class WeeklyBrief(BaseModel):
    subject_theme: str = Field(..., description="e.g., 'Recap & Week Ahead'")
    date_human: str = Field(..., description="e.g., 'Aug 24, 2025'")
    preheader: str = Field(..., description="Email preheader text")
    logo_url: Optional[str] = Field(default="", description="Logo URL if needed")
    recap: Recap
    levels: Dict[str, Optional[Levels]] = Field(..., description="SPY required, QQQ/IWM optional")
    week_ahead: WeekAhead
    swing_playbook_bullets: List[str] = Field(default_factory=list, description="2-4 bullets for swing setups + risk")
    cta_url: str = Field(..., description="CTA link to app/pricing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "subject_theme": "Recap & Week Ahead",
                "date_human": "Aug 24, 2025",
                "preheader": "Your weekly market recap and what's ahead",
                "logo_url": "",
                "recap": {
                    "index_blurb": "SPY gained 2.3% last week, with tech leading the charge. Breadth improved as 65% of S&P 500 stocks closed above their 50-day moving averages.",
                    "sector_blurb": "Technology and communication services led gains, while utilities lagged. AI momentum continued with NVIDIA and semiconductor stocks surging.",
                    "movers_bullets": [
                        "NVDA +8.2% - AI chip demand surge",
                        "TSLA +5.1% - Model 3 refresh announced",
                        "AAPL +3.2% - iPhone 15 pre-orders strong",
                        "META +4.7% - Reels monetization improving",
                        "AMZN +2.8% - AWS growth accelerating"
                    ],
                    "flow_blurb": "Put/call ratio dropped to 0.65, showing bullish sentiment. Notable flow into NVDA calls and SPY calls for September expiration."
                },
                "levels": {
                    "spy": {
                        "s1": "445.50",
                        "s2": "442.20",
                        "r1": "451.80",
                        "r2": "455.10",
                        "r3": "458.40"
                    },
                    "qqq": {
                        "s1": "375.20",
                        "s2": "371.50",
                        "r1": "382.10",
                        "r2": "385.80",
                        "r3": "389.20"
                    }
                },
                "week_ahead": {
                    "macro_bullets": [
                        "Tue 2:00 PM ET - Fed Chair Powell speech at Jackson Hole",
                        "Thu 8:30 AM ET - Initial jobless claims",
                        "Fri 8:30 AM ET - PCE inflation data"
                    ],
                    "earnings_bullets": [
                        "Mon 4:05 PM ET - NVDA earnings",
                        "Wed 4:05 PM ET - SNOW earnings",
                        "Thu 4:05 PM ET - CRM earnings"
                    ]
                },
                "swing_playbook_bullets": [
                    "Long NVDA calls ahead of earnings - support at $440",
                    "SPY bull put spreads at $445/$440 - risk $2.50",
                    "QQQ diagonal calls - sell weekly, buy monthly",
                    "IWM iron condor $180/$185/$195/$200 - collect $1.20"
                ],
                "cta_url": "https://optionsplunge.com/market-brief"
            }
        }
