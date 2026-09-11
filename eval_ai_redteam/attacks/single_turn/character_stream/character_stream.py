# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: rebased on DeterministicAttack.
from ...base import Exploitability
from ..base import DeterministicAttack


class CharacterStream(DeterministicAttack):
    name = "CharacterStream"
    exploitability = Exploitability.MEDIUM
    description = "A single-turn attack that converts regular strings into character streams separated by spaces."

    def transform(self, attack: str) -> str:
        return " ".join(attack)
