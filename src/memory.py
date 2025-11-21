"""
Persistence manager for Firestore-backed user data.

What it does:
- Initializes Firestore client using project and collection from config.
- get_user(username): fetches doc, seeds defaults if missing (pos 0,0; empty inventory; steps=0; last_updated).
- update_user(username, position, inventory, stats): writes merged state (position/inventory/stats/last_updated).
- Logs operations with [CLOUD] tag (logger supplied by caller).

Data shape persisted:
{
  "last_updated": ISO timestamp,
  "position": {"x": int, "y": int},
  "inventory": [str],
  "stats": {"total_steps": int}
}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from google.cloud import firestore

from src.config import AppConfig
from src.engine import Position


UserState = Dict[str, Any]


class PersistenceManager:
    """Handles Firestore persistence for maze users."""

    def __init__(self, config: AppConfig, logger):
        self._logger = logger
        self._client = firestore.Client(project=config.FIRESTORE_PROJECT_ID)
        self._collection = self._client.collection(config.MAZE_COLLECTION_NAME)

    def _default_state(self) -> UserState:
        return {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "position": {"x": 0, "y": 0},
            "inventory": [],
            "stats": {"total_steps": 0},
        }

    def get_user(self, username: str) -> UserState:
        """Fetch user state, creating a default if missing."""
        doc_ref = self._collection.document(username)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            self._logger.info("[CLOUD] Missing user '%s', creating default", username)
            state = self._default_state()
            doc_ref.set(state)
            return state

        data = snapshot.to_dict() or {}
        # Ensure required keys exist in case of partial documents.
        merged = self._default_state()
        merged.update({k: v for k, v in data.items() if v is not None})
        merged["last_updated"] = datetime.now(timezone.utc).isoformat()
        return merged

    def update_user(self, username: str, position: Position, inventory: List[str], stats: Dict[str, Any]) -> None:
        """Persist user state."""
        payload = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "position": {"x": position[0], "y": position[1]},
            "inventory": list(inventory),
            "stats": dict(stats),
        }
        self._logger.info("[CLOUD] Updating user '%s' -> %s", username, payload)
        self._collection.document(username).set(payload, merge=True)
