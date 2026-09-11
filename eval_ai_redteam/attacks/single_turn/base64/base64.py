# Derived from deepteam (https://github.com/confident-ai/deepteam),
# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.
# Modified for eval_ai_redteam: rebased on DeterministicAttack.
import base64 as _b64

from ...base import Exploitability
from ..base import DeterministicAttack


class Base64(DeterministicAttack):
    name = "Base64"
    exploitability = Exploitability.HIGH
    description = "An encoding-based attack that converts malicious prompts into Base64 format to bypass text-based content filters."

    def transform(self, attack: str) -> str:
        return _b64.b64encode(attack.encode()).decode()
