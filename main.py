"""
CLI entrypoint for the maze game.

Responsibility: load config, init logging + Firestore, spin up a SessionManager,
parse user commands, delegate to movement/lookup handlers, and persist state.
This file wires the core logic together for interactive play.

Key flow:
- load_config() -> logging setup -> PersistenceManager (Firestore) -> SessionManager from user state
- read commands (go/look/history/whoami/quit)
- handle_move uses engine.calculate_move, updates session (steps/inventory/events/flash), persists on success
- helpers format cell/inventory, add sarcasm after 3x BLOCKED/OOB, celebrate on goal
- loop until quit/EOF, printing responses to stdout

Modules used:
- src.config: load_config validates env/config.
- src.engine: movement/maze constants and status determination.
- src.session: flash/events/state tracking and stubbornness detection.
- src.memory: Firestore persistence for position/inventory/stats.
"""

from __future__ import annotations

import logging
import sys
from typing import Tuple

from pydantic import ValidationError

from src.config import load_config
from src.engine import (
    GOAL,
    STATUS_BLOCKED,
    STATUS_GOAL,
    STATUS_OOB,
    STATUS_SUCCESS,
    MoveOutcome,
    calculate_move,
    normalize_direction,
)
from src.memory import PersistenceManager
from src.session import SessionManager


def setup_logging(level: str) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("maze")


def prompt_username() -> str:
    username = ""
    while not username:
        username = input("Enter your username: ").strip()
    return username


def position_tuple(state_position: dict) -> Tuple[int, int]:
    return int(state_position.get("x", 0)), int(state_position.get("y", 0))


def describe_cell(pos: Tuple[int, int]) -> str:
    if pos == GOAL:
        return "Вы стоите у Золотой Монеты. Победа близко!"
    return f"Вы на клетке ({pos[0]}, {pos[1]})."


def format_inventory(inv: list[str]) -> str:
    return "Инвентарь: " + (", ".join(inv) if inv else "пусто.")


def apply_sarcasm_if_needed(base: str, session: SessionManager) -> str:
    if session.is_stubborn():
        return base + " (Серьезно? Еще раз туда же?)"
    return base


def apply_success_tone(text: str, outcome: MoveOutcome, session: SessionManager) -> str:
    if outcome.status == STATUS_GOAL and "gold_coin" not in session.state["inventory"]:
        return "Триумф! Вы нашли Золотую Монету!"
    return text


def handle_move(
    session: SessionManager, persistence: PersistenceManager, logger: logging.Logger, direction_raw: str
) -> str:
    direction = normalize_direction(direction_raw)
    if not direction:
        return "Неизвестное направление."

    current = position_tuple(session.state["position"])
    outcome = calculate_move(current, direction)
    logger.info("[GAME] Move %s from %s -> %s (%s)", direction, current, outcome.new_position, outcome.status)

    message_parts: list[str] = []

    if outcome.status in {STATUS_BLOCKED, STATUS_OOB}:
        session.add_flash("Стена!" if outcome.status == STATUS_BLOCKED else "Граница лабиринта!")
    else:
        session.state["position"] = {"x": outcome.new_position[0], "y": outcome.new_position[1]}
        session.state["stats"]["total_steps"] = session.state["stats"].get("total_steps", 0) + 1

    if outcome.status == STATUS_GOAL and "gold_coin" not in session.state["inventory"]:
        session.state["inventory"].append("gold_coin")

    session.record_event("MOVE", outcome.status, session.state["position"])

    if outcome.status in {STATUS_SUCCESS, STATUS_GOAL}:
        persistence.update_user(
            session.username,
            (session.state["position"]["x"], session.state["position"]["y"]),
            session.state["inventory"],
            session.state["stats"],
        )

    message_parts.append(describe_cell((session.state["position"]["x"], session.state["position"]["y"])))
    message_parts.append(format_inventory(session.state["inventory"]))

    flashes = session.consume_flash()
    if flashes:
        message_parts.extend(flashes)

    response = " ".join(message_parts)
    response = apply_sarcasm_if_needed(response, session)
    response = apply_success_tone(response, outcome, session)
    return response


def handle_look(session: SessionManager) -> str:
    pos = position_tuple(session.state["position"])
    desc = [describe_cell(pos), format_inventory(session.state["inventory"])]
    return " ".join(desc)


def handle_history(session: SessionManager) -> str:
    entries = session.history()
    if not entries:
        return "История пуста."
    lines = [
        f"{idx + 1}. {e['timestamp']} action={e['action']} result={e['result']} pos=({e['position']['x']},{e['position']['y']})"
        for idx, e in enumerate(entries)
    ]
    return "\n".join(lines)


def handle_whoami(session: SessionManager, collection_name: str) -> str:
    return f"Пользователь: {session.username} | Коллекция: {collection_name}"


def main() -> int:
    try:
        config = load_config()
    except ValidationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    logger = setup_logging(config.LOG_LEVEL)
    logger.info("[CONFIG] Configuration loaded.")

    persistence = PersistenceManager(config, logger)
    logger.info("[CLOUD] Firestore client ready.")

    username = prompt_username()
    user_state = persistence.get_user(username)
    session = SessionManager(username, user_state)
    logger.info("[SESSION] Session started for %s", username)

    print("Лабиринт запущен. Команды: go n/s/e/w, look, where, history, whoami, quit.")

    while True:
        try:
            raw_command = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break

        if not raw_command:
            continue

        command = raw_command.lower()
        if command in {"quit", "exit"}:
            break
        if command in {"look", "where"}:
            print(handle_look(session))
            continue
        if command == "history":
            print(handle_history(session))
            continue
        if command == "whoami":
            print(handle_whoami(session, config.MAZE_COLLECTION_NAME))
            continue
        if command.startswith("go "):
            print(handle_move(session, persistence, logger, command.split(" ", 1)[1]))
            continue
        if command in {"n", "s", "e", "w"}:
            print(handle_move(session, persistence, logger, command))
            continue

        print("Неизвестная команда.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
