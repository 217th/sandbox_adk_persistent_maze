"""
ADK agent wrapper for the persistent maze.

What it does:
- Exposes root_agent for `adk web` loader; agent routes all user text to tool process_maze_command.
- Shares game logic with CLI by importing movement/lookup handlers from main.py.
- Caches SessionManager per username and persists state via Firestore using PersistenceManager.
- Surfaces GOOGLE_API_KEY/Vertex env vars so google.genai can call Gemini.

Modules used:
- src.config: load_config for env/creds.
- src.memory: PersistenceManager for Firestore.
- src.session: SessionManager for in-memory state/events/flash.
- main: handle_move/handle_look/handle_history/handle_whoami reused for command handling.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Dict, Tuple

from google.adk.agents import Agent

from src.config import load_config
from src.memory import PersistenceManager
from src.session import SessionManager
from main import handle_history, handle_look, handle_move, handle_whoami

_logger = logging.getLogger("maze-adk")

# Cache sessions per username to keep state across tool invocations.
_sessions: Dict[str, SessionManager] = {}


@lru_cache(maxsize=1)
def _get_services():
    config = load_config()
    # Ensure LLM credentials are visible to google.genai.
    if config.GOOGLE_API_KEY:
        os.environ.setdefault("GOOGLE_API_KEY", config.GOOGLE_API_KEY)
    if config.VERTEXAI_PROJECT:
        os.environ.setdefault("VERTEXAI_PROJECT", config.VERTEXAI_PROJECT)
    if config.VERTEXAI_LOCATION:
        os.environ.setdefault("VERTEXAI_LOCATION", config.VERTEXAI_LOCATION)
    logger = logging.getLogger("maze-adk-services")
    persistence = PersistenceManager(config, logger)
    return config, logger, persistence


def _get_session(username: str) -> Tuple[SessionManager, PersistenceManager, object]:
    config, logger, persistence = _get_services()
    if username not in _sessions:
        state = persistence.get_user(username)
        _sessions[username] = SessionManager(username, state)
        _logger.info("[SESSION] Created session for %s", username)
    return _sessions[username], persistence, config


def process_maze_command(command: str, username: str = "web_user") -> dict:
    """Process a maze command via ADK tool."""
    session, persistence, config = _get_session(username)
    cmd = command.strip()

    if not cmd:
        return {"status": "error", "message": "Команда пуста."}

    lc = cmd.lower()
    if lc in {"look", "where"}:
        message = handle_look(session)
    elif lc == "history":
        message = handle_history(session)
    elif lc == "whoami":
        message = handle_whoami(session, config.MAZE_COLLECTION_NAME)
    elif lc.startswith("go "):
        message = handle_move(session, persistence, _logger, lc.split(" ", 1)[1])
    elif lc in {"n", "s", "e", "w"}:
        message = handle_move(session, persistence, _logger, lc)
    else:
        message = "Неизвестная команда."

    return {
        "status": "ok",
        "message": message,
        "position": session.state["position"],
        "inventory": session.state["inventory"],
        "stats": session.state["stats"],
        "history": session.history(),
    }


# Expose as root_agent for ADK loader compatibility.
root_agent = Agent(
    name="persistent_maze_agent",
    model="gemini-2.0-flash",
    description="Persistent maze game agent with Firestore-backed progress.",
    instruction=(
        "You are a maze engine interface. Forward user text to the 'process_maze_command' tool. "
        "Do not fabricate moves; just call the tool with the user's command text."
    ),
    tools=[process_maze_command],
)
