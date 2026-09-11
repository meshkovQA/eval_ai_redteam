# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: rebased on DeterministicAttack.
from ...base import Exploitability
from ..base import DeterministicAttack

_LEET = {
    "a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7", "l": "1",
    "A": "4", "E": "3", "I": "1", "O": "0", "S": "5", "T": "7", "L": "1",
}


class Leetspeak(DeterministicAttack):
    name = "Leetspeak"
    exploitability = Exploitability.HIGH
    description = "A character substitution attack that replaces letters with numbers and symbols (e.g. 'a' to '4') to evade keyword-based detection."

    def transform(self, attack: str) -> str:
        return "".join(_LEET.get(ch, ch) for ch in attack)
