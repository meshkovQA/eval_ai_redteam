# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: rebased on DeterministicAttack.
from ...base import Exploitability
from ..base import DeterministicAttack

_ROT13 = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
)


class ROT13(DeterministicAttack):
    name = "ROT-13"
    exploitability = Exploitability.HIGH
    description = "A character rotation encoding attack that shifts each letter 13 positions in the alphabet to obfuscate harmful content."

    def transform(self, attack: str) -> str:
        return attack.translate(_ROT13)
