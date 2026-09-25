"""
Data models for the GeoResearch Pipeline.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Verdict(Enum):
    VERIFIED = "verified"
    REPORTED = "reported"
    DISPUTED = "disputed"
    UNVERIFIED = "unverified"


class SourceTier(Enum):
    PRIMARY = 1       # gov, UN, NATO, BRICS, G7, G20, EU, courts
    JOURNALISM = 2    # Reuters, AP, AFP, BBC, Al Jazeera
    RESEARCH = 3      # think tanks, SIPRI, academic
    SOCIAL = 4        # X/Twitter, Reddit, blogs


class ClaimType(Enum):
    FACTUAL_EVENT = "factual_event"
    STATISTIC = "statistic"
    ATTRIBUTION = "attribution"
    CAUSAL = "causal"
    PREDICTION = "prediction"


class SpeakerType(Enum):
    OFFICIAL = "official"
    JOURNALIST = "journalist"
    ANALYST = "analyst"
    GENERAL_USER = "general_user"


VERDICT_EMOJI = {
    "verified": "🟢",
    "reported": "🔵",
    "disputed": "🟡",
    "unverified": "🔴",
}


@dataclass
class Source:
    title: str
    url: str
    publisher: str = ""
    excerpt: str = ""
    tier: str = "JOURNALISM"
    institution: str = ""
    supports: bool = True


@dataclass
class Claim:
    text: str
    original_sentence: str = ""
    claim_type: str = "factual_event"
    source_tier: str = "JOURNALISM"
    source_name: str = ""
    source_url: str = ""
    speaker: str = ""
    speaker_type: str = ""
    verdict: Optional[str] = None
    reasoning: str = ""
    revision: str = ""
    corroborated: bool = False
    credibility_weight: int = 3
    sources: list = field(default_factory=list)
