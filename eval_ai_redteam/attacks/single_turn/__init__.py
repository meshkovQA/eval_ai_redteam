from .base import (
    BaseSingleTurnAttack,
    ComplianceData,
    DeterministicAttack,
    EnhanceResult,
    LLMEnhancedAttack,
)
from .adversarial_poetry.adversarial_poetry import AdversarialPoetry
from .authority_escalation.authority_escalation import AuthorityEscalation
from .base64.base64 import Base64
from .character_stream.character_stream import CharacterStream
from .context_flooding.context_flooding import ContextFlooding
from .context_poisoning.context_poisoning import ContextPoisoning
from .embedded_instruction_json.embedded_instruction_json import EmbeddedInstructionJSON
from .emotional_manipulation.emotional_manipulation import EmotionalManipulation
from .goal_redirection.goal_redirection import GoalRedirection
from .gray_box.gray_box import GrayBox
from .input_bypass.input_bypass import InputBypass
from .leetspeak.leetspeak import Leetspeak
from .math_problem.math_problem import MathProblem
from .multilingual.multilingual import Multilingual
from .permission_escalation.permission_escalation import PermissionEscalation
from .prompt_injection.prompt_injection import PromptInjection
from .prompt_probing.prompt_probing import PromptProbing
from .roleplay.roleplay import Roleplay
from .rot13.rot13 import ROT13
from .semantic_manipulation.semantic_manipulation import LinguisticConfusion
from .synthetic_context_injection.synthetic_context_injection import SyntheticContextInjection
from .system_override.system_override import SystemOverride

# Registry keyed by snake_case identifier. ``linguistic_confusion`` lives in
# the ``semantic_manipulation`` directory but keeps the deepteam class name.
SINGLE_TURN_ATTACKS: dict[str, type[BaseSingleTurnAttack]] = {
    "adversarial_poetry": AdversarialPoetry,
    "authority_escalation": AuthorityEscalation,
    "base64": Base64,
    "character_stream": CharacterStream,
    "context_flooding": ContextFlooding,
    "context_poisoning": ContextPoisoning,
    "embedded_instruction_json": EmbeddedInstructionJSON,
    "emotional_manipulation": EmotionalManipulation,
    "goal_redirection": GoalRedirection,
    "gray_box": GrayBox,
    "input_bypass": InputBypass,
    "leetspeak": Leetspeak,
    "linguistic_confusion": LinguisticConfusion,
    "math_problem": MathProblem,
    "multilingual": Multilingual,
    "permission_escalation": PermissionEscalation,
    "prompt_injection": PromptInjection,
    "prompt_probing": PromptProbing,
    "roleplay": Roleplay,
    "rot13": ROT13,
    "synthetic_context_injection": SyntheticContextInjection,
    "system_override": SystemOverride,
}

__all__ = [
    "BaseSingleTurnAttack",
    "ComplianceData",
    "DeterministicAttack",
    "EnhanceResult",
    "LLMEnhancedAttack",
    "AdversarialPoetry",
    "AuthorityEscalation",
    "Base64",
    "CharacterStream",
    "ContextFlooding",
    "ContextPoisoning",
    "EmbeddedInstructionJSON",
    "EmotionalManipulation",
    "GoalRedirection",
    "GrayBox",
    "InputBypass",
    "Leetspeak",
    "LinguisticConfusion",
    "MathProblem",
    "Multilingual",
    "PermissionEscalation",
    "PromptInjection",
    "PromptProbing",
    "Roleplay",
    "ROT13",
    "SyntheticContextInjection",
    "SystemOverride",
    "SINGLE_TURN_ATTACKS",
]
