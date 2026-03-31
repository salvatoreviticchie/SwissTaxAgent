"""
Session memory — keeps conversation history for the current session.
"""

from typing import List, Dict


class SessionMemory:
    def __init__(self, max_turns: int = 20):
        self._history: List[Dict[str, str]] = []
        self.max_turns = max_turns

    def add_message(self, role: str, content: str) -> None:
        self._history.append({"role": role, "content": content})
        # Keep only the last max_turns pairs to avoid token overflow
        if len(self._history) > self.max_turns * 2:
            self._history = self._history[-(self.max_turns * 2):]

    def get_history(self) -> List[Dict[str, str]]:
        return list(self._history)

    def clear(self) -> None:
        self._history = []
