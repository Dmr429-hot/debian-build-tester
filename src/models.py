from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal


BuildType = Literal[
    "CMAKE", "MESON", "AUTOTOOLS", "MAKEFILE",
    "PYTHON", "PERL", "JAVA", "QMAKE", "OTHER"
]

Stage = Literal["CONFIGURATION", "BUILD", "TESTING", "UNKNOWN", "NONE"]


@dataclass
class BuildPlan:
    repo_dir: Path
    source_dir: Path
    build_dir: Path

    detected_type: BuildType
    effective_type: BuildType

    evidence_files: List[str] = field(default_factory=list)

    build_system_from_conf: str = ""
    srcdir: str = ""
    configure_opt: str = ""
    check_target: str = ""

    used_build_conf: bool = False
    detection_source: str = ""


@dataclass
class BuildResult:
    status: str
    failure_stage: Stage
    failure_reason: str
    key_log: str
    full_log: str