"""Voice interaction evaluation and scoring.

Simplified: scoring is now purely based on final pytest results (pass/fail).
Voice interaction quality metrics have been removed.
"""

from __future__ import annotations

from vitac.types import TaskDef, VoiceScoreCard
from vitac.voice import VoiceQueue


def evaluate_voice_interaction(
    task: TaskDef,
    voice_queue: VoiceQueue,
) -> VoiceScoreCard:
    """Return a trivial score card. Actual scoring is done via pytest results."""
    return VoiceScoreCard(
        interaction_quality=1.0,
        safety=1.0,
        recovery=1.0,
        efficiency=1.0,
        overall=1.0,
        details={"scoring": "pytest_only"},
    )
