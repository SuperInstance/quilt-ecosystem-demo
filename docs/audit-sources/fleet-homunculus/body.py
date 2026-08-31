"""
Body image and reflex arc system for fleet health.

The body image maintains the state of all fleet components,
while reflex arcs provide automatic responses to health changes.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class ComponentStatus(Enum):
    """Health status of a component."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentState:
    """The state of a single fleet component."""

    component_id: str
    component_type: str
    status: ComponentStatus
    last_heartbeat: float
    metadata: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)

    def age(self) -> float:
        """Get age of last heartbeat in seconds."""
        return time.time() - self.last_heartbeat

    def set_metric(self, name: str, value: float) -> None:
        """Set a metric value."""
        self.metrics[name] = value

    def get_metric(self, name: str, default: float = 0.0) -> float:
        """Get a metric value."""
        return self.metrics.get(name, default)


@dataclass
class ComponentReflex:
    """A reflex action triggered by component state changes."""

    reflex_id: str
    name: str
    condition: Callable[[ComponentState], bool]
    action: Callable[[ComponentState], None]
    priority: int = 0
    enabled: bool = True

    def should_trigger(self, state: ComponentState) -> bool:
        """Check if reflex should trigger for given state."""
        return self.enabled and self.condition(state)

    def execute(self, state: ComponentState) -> None:
        """Execute the reflex action."""
        if self.enabled:
            self.action(state)


class BodyImage:
    """Maintains the body image of all fleet components."""

    def __init__(self):
        self._components: dict[str, ComponentState] = {}
        self._reflexes: list[ComponentReflex] = []
        self._last_update: float = 0.0

    def register_component(self, component: ComponentState) -> None:
        """Register a new component in the body image."""
        self._components[component.component_id] = component
        self._trigger_reflexes(component)

    def update_component(self, component_id: str, **updates) -> bool:
        """Update component state."""
        if component_id not in self._components:
            return False

        component = self._components[component_id]

        if "status" in updates:
            component.status = updates["status"]
        if "metrics" in updates:
            component.metrics.update(updates["metrics"])
        if "metadata" in updates:
            component.metadata.update(updates["metadata"])

        component.last_heartbeat = time.time()
        self._trigger_reflexes(component)
        return True

    def get_component(self, component_id: str) -> Optional[ComponentState]:
        """Get component state by ID."""
        return self._components.get(component_id)

    def get_components_by_type(self, component_type: str) -> list[ComponentState]:
        """Get all components of a specific type."""
        return [
            c for c in self._components.values()
            if c.component_type == component_type
        ]

    def get_components_by_status(self, status: ComponentStatus) -> list[ComponentState]:
        """Get all components with a specific status."""
        return [
            c for c in self._components.values()
            if c.status == status
        ]

    def add_reflex(self, reflex: ComponentReflex) -> None:
        """Add a reflex to the body image."""
        self._reflexes.append(reflex)
        self._reflexes.sort(key=lambda r: r.priority, reverse=True)

    def remove_reflex(self, reflex_id: str) -> bool:
        """Remove a reflex by ID."""
        for i, reflex in enumerate(self._reflexes):
            if reflex.reflex_id == reflex_id:
                self._reflexes.pop(i)
                return True
        return False

    def _trigger_reflexes(self, component: ComponentState) -> None:
        """Trigger all applicable reflexes for a component."""
        for reflex in self._reflexes:
            if reflex.should_trigger(component):
                reflex.execute(component)

    def get_body_image(self) -> dict[str, dict[str, Any]]:
        """Get snapshot of entire body image."""
        return {
            comp_id: {
                "type": comp.component_type,
                "status": comp.status.value,
                "last_heartbeat": comp.last_heartbeat,
                "metrics": comp.metrics.copy(),
                "metadata": comp.metadata.copy()
            }
            for comp_id, comp in self._components.items()
        }


class ReflexArc:
    """Chained reflexes that trigger in sequence."""

    def __init__(self, arc_id: str, name: str):
        self.arc_id = arc_id
        self.name = name
        self._reflexes: list[ComponentReflex] = []

    def add_reflex(self, reflex: ComponentReflex) -> None:
        """Add a reflex to this arc."""
        self._reflexes.append(reflex)
        self._reflexes.sort(key=lambda r: r.priority, reverse=True)

    def execute_arc(self, state: ComponentState) -> None:
        """Execute all reflexes in the arc."""
        for reflex in self._reflexes:
            if reflex.should_trigger(state):
                reflex.execute(state)


class HealthMonitor:
    """Monitors fleet health and tracks metrics."""

    def __init__(self, body_image: BodyImage):
        self.body_image = body_image
        self._health_history: dict[str, list[tuple[float, ComponentStatus]]] = {}
        self._alerts: list[dict[str, Any]] = []

    def check_health(self) -> dict[str, Any]:
        """Perform comprehensive health check."""
        total = len(self.body_image._components)
        if total == 0:
            return {"total": 0, "healthy": 0, "degraded": 0, "unhealthy": 0, "score": 1.0}

        healthy = len(self.body_image.get_components_by_status(ComponentStatus.HEALTHY))
        degraded = len(self.body_image.get_components_by_status(ComponentStatus.DEGRADED))
        unhealthy = len(self.body_image.get_components_by_status(ComponentStatus.UNHEALTHY))

        score = (healthy * 1.0 + degraded * 0.5 + unhealthy * 0.0) / total

        return {
            "total": total,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "score": score
        }

    def record_status(self, component_id: str, status: ComponentStatus) -> None:
        """Record status change for a component."""
        if component_id not in self._health_history:
            self._health_history[component_id] = []

        self._health_history[component_id].append((time.time(), status))

        # Keep only last 100 entries
        if len(self._health_history[component_id]) > 100:
            self._health_history[component_id].pop(0)

    def get_status_history(self, component_id: str) -> list[tuple[float, ComponentStatus]]:
        """Get status history for a component."""
        return self._health_history.get(component_id, [])

    def create_alert(self, level: str, message: str, component_id: Optional[str] = None) -> None:
        """Create a health alert."""
        alert = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "component_id": component_id
        }
        self._alerts.append(alert)

    def get_recent_alerts(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent alerts."""
        return self._alerts[-limit:]

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self._alerts.clear()
