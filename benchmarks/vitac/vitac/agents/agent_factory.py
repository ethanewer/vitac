"""Dynamic agent loading from module:ClassName notation."""

from __future__ import annotations

import importlib

from vitac.agents.base_agent import CollaboratorAgent, PrimaryAgent


def load_agent_class(spec: str) -> type:
    """Load a class from a 'module.path:ClassName' string.

    Example: 'my_agents.gpt:GPTPrimary' -> imports my_agents.gpt and returns GPTPrimary
    """
    if ":" not in spec:
        raise ValueError(
            f"Agent spec must be 'module:ClassName', got: {spec!r}"
        )
    module_path, class_name = spec.rsplit(":", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls


def load_primary_agent(spec: str) -> PrimaryAgent:
    """Load and instantiate a PrimaryAgent from spec."""
    cls = load_agent_class(spec)
    if not issubclass(cls, PrimaryAgent):
        raise TypeError(f"{cls.__name__} is not a PrimaryAgent subclass")
    return cls()


def load_collaborator_agent(spec: str) -> CollaboratorAgent:
    """Load and instantiate a CollaboratorAgent from spec."""
    cls = load_agent_class(spec)
    if not issubclass(cls, CollaboratorAgent):
        raise TypeError(f"{cls.__name__} is not a CollaboratorAgent subclass")
    return cls()
