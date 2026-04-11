from __future__ import annotations
from pathlib import Path
from typing import Dict, List

from models import BuildPlan


def _read_build_conf(repo_dir: Path) -> Dict[str, str]:
    conf: Dict[str, str] = {}
    conf_path = repo_dir / "build.conf"
    if not conf_path.is_file():
        return conf

    for line in conf_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        conf[key.strip()] = value.strip().strip('"').strip("'")
    return conf


def detect_build_plan(repo_dir: Path) -> BuildPlan:
    evidence: List[str] = []
    conf = _read_build_conf(repo_dir)

    build_system = conf.get("BUILD_SYSTEM", "").strip()
    srcdir = conf.get("SRCDIR", "").strip()
    configure_opt = conf.get("CONFIGURE_OPT", "").strip()
    check_target = conf.get("CHECK_TARGET", "").strip()

    source_dir = repo_dir / srcdir if srcdir else repo_dir
    build_dir = repo_dir / "build-rvci"

    if (repo_dir / "build.conf").is_file():
        evidence.append("build.conf")

    def exists_in_source(name: str) -> bool:
        return (source_dir / name).exists()

    def add(name: str) -> None:
        evidence.append(f"{srcdir}/{name}" if srcdir else name)

    detected_type = "OTHER"
    detection_source = "auto_detect"

    # 先按老师 shell 的主顺序识别
    if exists_in_source("CMakeLists.txt"):
        add("CMakeLists.txt")
        detected_type = "CMAKE"
    elif exists_in_source("meson.build"):
        add("meson.build")
        if exists_in_source("meson_options.txt"):
            add("meson_options.txt")
        detected_type = "MESON"
    elif exists_in_source("configure"):
        add("configure")
        if exists_in_source("configure.ac"):
            add("configure.ac")
        if exists_in_source("configure.in"):
            add("configure.in")
        detected_type = "AUTOTOOLS"
    elif any(exists_in_source(x) for x in ["configure.ac", "configure.in", "autogen.sh", "bootstrap", "autogen.pl"]):
        for x in ["configure.ac", "configure.in", "autogen.sh", "bootstrap", "autogen.pl"]:
            if exists_in_source(x):
                add(x)
        detected_type = "AUTOTOOLS"
    elif exists_in_source("Makefile"):
        add("Makefile")
        detected_type = "MAKEFILE"
    # 下面是补充识别，只用于分类展示，不是当前主执行重点
    elif exists_in_source("pyproject.toml") or exists_in_source("setup.py") or exists_in_source("setup.cfg"):
        for x in ["pyproject.toml", "setup.py", "setup.cfg"]:
            if exists_in_source(x):
                add(x)
        detected_type = "PYTHON"
        detection_source = "extended_detect"
    elif exists_in_source("pom.xml") or exists_in_source("build.gradle") or exists_in_source("build.gradle.kts") or exists_in_source("build.xml"):
        for x in ["pom.xml", "build.gradle", "build.gradle.kts", "build.xml"]:
            if exists_in_source(x):
                add(x)
        detected_type = "JAVA"
        detection_source = "extended_detect"
    else:
        pro_files = list(source_dir.glob("*.pro"))
        if pro_files:
            add(pro_files[0].name)
            detected_type = "QMAKE"
            detection_source = "extended_detect"

    forced_map = {
        "cmake": "CMAKE",
        "meson": "MESON",
        "autotools": "AUTOTOOLS",
        "makefile": "MAKEFILE",
        "Makefile": "MAKEFILE",
    }

    if build_system in forced_map:
        effective_type = forced_map[build_system]
        detection_source = "build_conf"
    else:
        effective_type = detected_type

    return BuildPlan(
        repo_dir=repo_dir,
        source_dir=source_dir,
        build_dir=build_dir,
        detected_type=detected_type,
        effective_type=effective_type,
        evidence_files=evidence,
        build_system_from_conf=build_system,
        srcdir=srcdir,
        configure_opt=configure_opt,
        check_target=check_target,
        used_build_conf=(build_system in forced_map),
        detection_source=detection_source,
    )