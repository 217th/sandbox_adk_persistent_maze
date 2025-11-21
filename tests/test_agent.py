import os
import uuid

import pytest
from dotenv import load_dotenv

from src.config import AppConfig, load_config
from src.engine import STATUS_BLOCKED, STATUS_OOB, calculate_move
from src.memory import PersistenceManager


REQUIRED_ENV = ["GOOGLE_APPLICATION_CREDENTIALS", "FIRESTORE_PROJECT_ID", "MAZE_COLLECTION_NAME"]

# Load env from .env so Firestore tests use local config.
load_dotenv()


@pytest.fixture(scope="module")
def config():
    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing env vars for Firestore tests: {', '.join(missing)}")
    return load_config()


@pytest.fixture(scope="module")
def persistence(config: AppConfig):
    import logging

    logger = logging.getLogger("test-maze")
    return PersistenceManager(config, logger)


def test_engine_blocks_wall_and_oob():
    blocked = calculate_move((1, 0), "north")
    assert blocked.status == STATUS_BLOCKED

    oob = calculate_move((0, 0), "south")
    assert oob.status == STATUS_OOB


def test_firestore_default_user(persistence: PersistenceManager):
    username = f"pytest_{uuid.uuid4().hex}"
    state = persistence.get_user(username)
    assert state["position"] == {"x": 0, "y": 0}
    assert state["inventory"] == []
    assert state["stats"]["total_steps"] == 0


def test_firestore_update_and_reload(persistence: PersistenceManager):
    username = f"pytest_{uuid.uuid4().hex}"
    persistence.get_user(username)
    persistence.update_user(username, (2, 2), ["gold_coin"], {"total_steps": 3})
    reloaded = persistence.get_user(username)
    assert reloaded["position"] == {"x": 2, "y": 2}
    assert "gold_coin" in reloaded["inventory"]
    assert reloaded["stats"]["total_steps"] == 3
