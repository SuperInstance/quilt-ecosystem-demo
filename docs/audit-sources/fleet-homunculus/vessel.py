"""Fleet homunculus implementation."""

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from enum import Enum


class PainLevel(Enum):
    """Severity of pain signals."""
    NONE = 0
    MILD = 1
    MODERATE = 2
    SEVERE = 3
    CRITICAL = 4


@dataclass
class PainSignal:
    """A pain signal from a vessel."""
    vessel_id: str
    message: str
    level: PainLevel
    timestamp: float = field(default_factory=time.time)

    def is_critical(self) -> bool:
        return self.level == PainLevel.CRITICAL

    def is_severe_or_worse(self) -> bool:
        return self.level.value >= PainLevel.SEVERE.value


@dataclass
class Vessel:
    """A vessel in the fleet with health tracking."""
    vessel_id: str
    name: str
    max_health: float = 100.0
    current_health: float = 100.0
    status: str = "active"

    def take_damage(self, amount: float) -> Optional[PainSignal]:
        """Take damage and generate pain signal if significant."""
        if amount <= 0:
            return None

        old_health = self.current_health
        self.current_health = max(0, self.current_health - amount)

        # Status reflects remaining health (bands aligned with heal())
        health_percent = self.current_health / self.max_health
        if health_percent <= 0:
            self.status = "destroyed"
        elif health_percent < 0.25:
            self.status = "critical"
        elif health_percent < 0.75:
            self.status = "damaged"
        else:
            self.status = "active"

        # Pain level reflects hit severity
        if health_percent <= 0:
            level = PainLevel.CRITICAL
        elif amount > 50:
            level = PainLevel.SEVERE
        elif amount > 10:
            level = PainLevel.MILD
        else:
            return None  # Minor damage, no signal

        return PainSignal(
            vessel_id=self.vessel_id,
            message=f" Took {amount:.1f} damage. Health: {self.current_health:.1f}/{self.max_health}",
            level=level
        )

    def heal(self, amount: float) -> None:
        """Heal the vessel."""
        self.current_health = min(self.max_health, self.current_health + amount)
        if self.current_health > self.max_health * 0.75:
            self.status = "active"
        elif self.current_health > self.max_health * 0.5:
            self.status = "damaged"

    def is_alive(self) -> bool:
        return self.current_health > 0

    def health_percent(self) -> float:
        return self.current_health / self.max_health


@dataclass
class ReflexArc:
    """An automatic response to pain signals."""
    name: str
    trigger_level: PainLevel
    action: Callable[[PainSignal], None]
    cooldown: float = 5.0  # seconds
    _last_triggered: float = 0.0

    def should_trigger(self, signal: PainSignal) -> bool:
        """Check if reflex should trigger."""
        if signal.level.value < self.trigger_level.value:
            return False

        now = time.time()
        if now - self._last_triggered < self.cooldown:
            return False

        return True

    def trigger(self, signal: PainSignal) -> bool:
        """Trigger the reflex if conditions met."""
        if not self.should_trigger(signal):
            return False

        self.action(signal)
        self._last_triggered = time.time()
        return True


class FleetBody:
    """The fleet body managing all vessels and reflexes."""

    def __init__(self, fleet_id: str):
        self.fleet_id = fleet_id
        self._vessels: Dict[str, Vessel] = {}
        self._reflexes: List[ReflexArc] = []
        self._pain_history: List[PainSignal] = []
        self._max_history = 100

    def add_vessel(self, vessel: Vessel) -> None:
        """Add a vessel to the fleet."""
        self._vessels[vessel.vessel_id] = vessel

    def get_vessel(self, vessel_id: str) -> Optional[Vessel]:
        """Get a vessel by ID."""
        return self._vessels.get(vessel_id)

    def get_all_vessels(self) -> List[Vessel]:
        """Get all vessels."""
        return list(self._vessels.values())

    def add_reflex(self, reflex: ReflexArc) -> None:
        """Add a reflex arc."""
        self._reflexes.append(reflex)

    def damage_vessel(self, vessel_id: str, amount: float) -> Optional[PainSignal]:
        """Damage a vessel and process pain signals."""
        vessel = self._vessels.get(vessel_id)
        if not vessel:
            return None

        signal = vessel.take_damage(amount)
        if signal:
            self._process_pain(signal)
        return signal

    def heal_vessel(self, vessel_id: str, amount: float) -> bool:
        """Heal a vessel."""
        vessel = self._vessels.get(vessel_id)
        if not vessel:
            return False
        vessel.heal(amount)
        return True

    def _process_pain(self, signal: PainSignal) -> None:
        """Process a pain signal through reflex arcs."""
        self._pain_history.append(signal)

        # Trim history
        if len(self._pain_history) > self._max_history:
            self._pain_history = self._pain_history[-self._max_history:]

        # Trigger reflexes
        for reflex in self._reflexes:
            reflex.trigger(signal)

    def get_pain_history(self, vessel_id: Optional[str] = None) -> List[PainSignal]:
        """Get pain history, optionally filtered by vessel."""
        if vessel_id is None:
            return list(self._pain_history)
        return [s for s in self._pain_history if s.vessel_id == vessel_id]

    def get_fleet_health(self) -> float:
        """Get average fleet health percentage."""
        if not self._vessels:
            return 0.0
        return sum(v.health_percent() for v in self._vessels.values()) / len(self._vessels)

    def get_critical_vessels(self) -> List[Vessel]:
        """Get all vessels in critical or worse state."""
        return [v for v in self._vessels.values() if v.health_percent() < 0.25]

    def count_by_status(self) -> Dict[str, int]:
        """Count vessels by status."""
        counts = {}
        for vessel in self._vessels.values():
            counts[vessel.status] = counts.get(vessel.status, 0) + 1
        return counts
