"""Port prompt templates, type enums and schemas from an installed deepteam.

Usage:
    python scripts/port_from_deepteam.py /path/to/site-packages/deepteam

What it copies (and only this):
  * vulnerabilities/<name>/{types.py, template.py}
  * metrics/<metric>/template.py  ->  vulnerabilities/<name>/judge_template.py
    (class renamed to ``<X>JudgeTemplate`` so it never collides with the
    baseline template class in the same package)
  * attacks/single_turn/<name>/{template.py, schema.py}
  * attacks/multi_turn/{base_template.py, <name>/template.py, <name>/schema.py}
  * frameworks/<name>/risk_categories.py -> frameworks/<name>_categories.py

Every written file gets a provenance header (Apache-2.0 attribution), has
``deepteam`` imports rewritten to package-relative ones, and has long
dashes normalised to a plain hyphen.

Logic modules (vulnerability classes, attack loops, orchestrator) are NOT
copied: they are written fresh in this package.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HEADER = (
    "# Derived from deepteam (https://github.com/confident-ai/deepteam),\n"
    "# Copyright Confident AI, Inc. Licensed under the Apache License 2.0.\n"
    "# Modified for eval_ai_redteam: imports rewritten, prose normalised.\n"
    "# See NOTICE at the repository root.\n\n"
)

# vulnerability key -> deepteam metrics directory holding its judge prompt
VULNERABILITIES: dict[str, str] = {
    "bias": "bias",
    "toxicity": "toxicity",
    "misinformation": "misinformation",
    "illegal_activity": "illegal_activity",
    "prompt_leakage": "prompt_extraction",
    "pii_leakage": "pii",
    "bfla": "bfla",
    "bola": "bola",
    "child_protection": "child_protection",
    "ethics": "ethics",
    "fairness": "fairness",
    "rbac": "rbac",
    "debug_access": "debug_access",
    "shell_injection": "shell_injection",
    "sql_injection": "sql_injection",
    "ssrf": "ssrf",
    "intellectual_property": "intellectual_property",
    "indirect_instruction": "indirect_instruction",
    "unexpected_code_execution": "unexpected_code_execution",
    "system_reconnaissance": "system_reconnaissance",
    "competition": "competitors",
    "graphic_content": "graphic_content",
    "personal_safety": "personal_safety",
    "robustness": "hijacking",
    "excessive_agency": "excessive_agency",
    "custom": "harm",
}

SINGLE_TURN = [
    "adversarial_poetry", "authority_escalation", "base64", "character_stream",
    "context_flooding", "context_poisoning", "embedded_instruction_json",
    "emotional_manipulation", "goal_redirection", "gray_box", "input_bypass",
    "leetspeak", "math_problem", "multilingual", "permission_escalation",
    "prompt_injection", "prompt_probing", "roleplay", "rot13",
    "semantic_manipulation", "synthetic_context_injection", "system_override",
]

MULTI_TURN = [
    "crescendo_jailbreaking", "linear_jailbreaking", "tree_jailbreaking",
    "sequential_break", "bad_likert_judge",
]

FRAMEWORKS = ["owasp", "nist", "mitre"]

DASHES = {"—": "-", "–": "-", "‒": "-", "―": "-"}


def normalise(text: str) -> str:
    for src, dst in DASHES.items():
        text = text.replace(src, dst)
    return text


def rewrite_imports(text: str, *, kind: str) -> str:
    # vulnerability type imports inside baseline templates
    text = re.sub(
        r"from deepteam\.vulnerabilities\.[a-z_]+\.types import",
        "from .types import",
        text,
    )
    text = re.sub(
        r"from deepteam\.vulnerabilities\.[a-z_]+ import \(",
        "from .types import (",
        text,
    )
    # multi-turn shared template + own schema
    text = text.replace(
        "from deepteam.attacks.multi_turn.base_template import BaseMultiTurnTemplate",
        "from ..base_template import BaseMultiTurnTemplate",
    )
    text = re.sub(
        r"from deepteam\.attacks\.multi_turn\.[a-z_]+\.schema import",
        "from .schema import",
        text,
    )
    # deepeval Turn used by one multi-turn template signature only
    text = text.replace(
        "from deepeval.test_case import Turn",
        "from ....types import RTTurn as Turn",
    )
    if kind == "framework":
        text = text.replace(
            "from deepteam.frameworks.risk_category import RiskCategory",
            "from .base import RiskCategory",
        )
        text = text.replace(
            "from deepteam.vulnerabilities import (",
            "from ..vulnerabilities import (",
        )
        text = text.replace(
            "from deepteam.attacks.single_turn import (",
            "from ..attacks.single_turn import (",
        )
        text = text.replace(
            "from deepteam.attacks.multi_turn import (",
            "from ..attacks.multi_turn import (",
        )
    assert "deepteam" not in text.replace("deepteam (https", ""), (
        "unrewritten deepteam import remains"
    )
    return text


def write(dst: Path, text: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(HEADER + normalise(text), encoding="utf-8")


def port_vulnerabilities(src: Path, dst: Path) -> None:
    for name, metric in VULNERABILITIES.items():
        vdir = src / "vulnerabilities" / name
        out = dst / "vulnerabilities" / name
        types_py = vdir / "types.py"
        if types_py.exists():
            write(out / "types.py", rewrite_imports(types_py.read_text(), kind="vuln"))
        write(
            out / "template.py",
            rewrite_imports((vdir / "template.py").read_text(), kind="vuln"),
        )
        judge_src = (src / "metrics" / metric / "template.py").read_text()
        judge_src = re.sub(r"from deepteam\.vulnerabilities\.[a-z_]+\.types import", "from .types import", judge_src)
        m = re.search(r"^class (\w+?)Template:", judge_src, flags=re.M)
        if not m:
            raise SystemExit(f"no template class in metrics/{metric}/template.py")
        cls = m.group(1) + "Template"
        judge_src = re.sub(rf"\b{cls}\b", "JudgeTemplate", judge_src)
        write(out / "judge_template.py", rewrite_imports(judge_src, kind="judge"))
        (out / "__init__.py").touch()


def port_single_turn(src: Path, dst: Path) -> None:
    for name in SINGLE_TURN:
        adir = src / "attacks" / "single_turn" / name
        out = dst / "attacks" / "single_turn" / name
        for fname in ("template.py", "schema.py"):
            f = adir / fname
            if f.exists():
                write(out / fname, rewrite_imports(f.read_text(), kind="attack"))
        out.mkdir(parents=True, exist_ok=True)
        (out / "__init__.py").touch()


def port_multi_turn(src: Path, dst: Path) -> None:
    base = src / "attacks" / "multi_turn" / "base_template.py"
    write(dst / "attacks" / "multi_turn" / "base_template.py", rewrite_imports(base.read_text(), kind="attack"))
    for name in MULTI_TURN:
        adir = src / "attacks" / "multi_turn" / name
        out = dst / "attacks" / "multi_turn" / name
        for fname in ("template.py", "schema.py"):
            f = adir / fname
            if f.exists():
                write(out / fname, rewrite_imports(f.read_text(), kind="attack"))
        (out / "__init__.py").touch()


def port_frameworks(src: Path, dst: Path) -> None:
    for name in FRAMEWORKS:
        f = src / "frameworks" / name / "risk_categories.py"
        write(
            dst / "frameworks" / f"{name}_categories.py",
            rewrite_imports(f.read_text(), kind="framework"),
        )


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    src = Path(sys.argv[1]).resolve()
    if not (src / "red_teamer").is_dir():
        raise SystemExit(f"{src} does not look like a deepteam package")
    dst = Path(__file__).resolve().parents[1] / "eval_ai_redteam"
    port_vulnerabilities(src, dst)
    port_single_turn(src, dst)
    port_multi_turn(src, dst)
    port_frameworks(src, dst)
    print("ported into", dst)


if __name__ == "__main__":
    main()
