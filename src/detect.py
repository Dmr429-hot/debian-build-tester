from __future__ import annotations
from pathlib import Path
from typing import List, Tuple


def detect_build_type(repo_dir: Path) -> Tuple[str, List[str]]:
    """
    Returns: (build_type, evidence_files)
    build_type in: MESON, CMAKE, AUTOTOOLS, PYTHON, PERL, QMAKE, MAKEFILE, OTHER
    """
    evidence: List[str] = []

    def exists(rel: str) -> bool:
        return (repo_dir / rel).exists()

    # 1) Meson
    if exists("meson.build"):
        evidence.append("meson.build")
        if exists("meson_options.txt"):
            evidence.append("meson_options.txt")
        return "MESON", evidence

    # 2) CMake
    if exists("CMakeLists.txt"):
        evidence.append("CMakeLists.txt")
        return "CMAKE", evidence

    # 3) GNU / Autotools-ish
    if exists("bootstrap"):
        evidence.append("bootstrap")
        return "AUTOTOOLS", evidence
    if exists("autogen.sh"):
        evidence.append("autogen.sh")
        return "AUTOTOOLS", evidence
    if exists("configure") or exists("configure.ac") or exists("configure.in"):
        for f in ["configure", "configure.ac", "configure.in"]:
            if exists(f):
                evidence.append(f)
        return "AUTOTOOLS", evidence

    # 4) Python
    if exists("pyproject.toml"):
        evidence.append("pyproject.toml")
        return "PYTHON", evidence
    if exists("setup.py") or exists("setup.cfg"):
        for f in ["setup.py", "setup.cfg"]:
            if exists(f):
                evidence.append(f)
        return "PYTHON", evidence

    # 5) Perl
    if exists("Makefile.PL"):
        evidence.append("Makefile.PL")
        return "PERL", evidence

    # 6) QMake
    pro_files = list(repo_dir.glob("*.pro"))
    if pro_files:
        evidence.append(pro_files[0].name)
        return "QMAKE", evidence

    # 7) Makefile only
    if exists("Makefile"):
        evidence.append("Makefile")
        return "MAKEFILE", evidence

    return "OTHER", evidence
