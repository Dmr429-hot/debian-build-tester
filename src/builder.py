from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import List, Mapping, Tuple

from log_drain import extract_key_log_snippet
from models import BuildPlan, BuildResult


def _nproc() -> str:
    return str(os.cpu_count() or 1)


def _fmt_cmd(cmd: list[str]) -> str:
    return " ".join(shlex.quote(x) for x in cmd)


def _append_log(logs: List[str], cmd: list[str], cwd: Path | None, out: str) -> None:
    cwd_str = str(cwd) if cwd else "."
    logs.append(f"[cwd] {cwd_str}\n$ {_fmt_cmd(cmd)}\n{out.rstrip()}\n")


def run_cmd(
    cmd: list[str],
    cwd: Path | None = None,
    timeout_s: int = 300,
    env: Mapping[str, str] | None = None,
) -> Tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_s,
            env=dict(env) if env else None,
        )
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired as e:
        output = e.stdout or ""
        if e.stderr:
            output += ("\n" if output else "") + e.stderr
        return 124, f"[TIMEOUT after {timeout_s}s]\n{output}"


def _prepare_env(plan: BuildPlan) -> dict[str, str]:
    env = os.environ.copy()
    env["CCACHE_DIR"] = str(plan.repo_dir / "ccache")

    repo_bin = str(plan.repo_dir / "bin")
    old_path = env.get("PATH", "")
    env["PATH"] = f"/usr/lib/ccache:{repo_bin}:{old_path}"

    job_name = env.get("JOB_NAME", "")
    if "/clang/" in job_name:
        env["CC"] = "clang"
        env["CXX"] = "clang++"

    return env


def _split_opts(opt_str: str) -> list[str]:
    return shlex.split(opt_str) if opt_str.strip() else []


def _source_rel_from_build(plan: BuildPlan) -> str:
    return f"../{plan.srcdir}" if plan.srcdir else ".."


def _reset_build_dir(build_dir: Path) -> None:
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)


def _make_result(status: str, stage: str, full_log: str) -> BuildResult:
    if status == "OK":
        return BuildResult(
            status="OK",
            failure_stage="NONE",
            failure_reason="NONE",
            key_log="",
            full_log=full_log,
        )

    reason, key_log = extract_key_log_snippet(
        full_log,
        failure_stage=stage,
        max_length=800,
    )
    return BuildResult(
        status="FAIL",
        failure_stage=stage,
        failure_reason=reason,
        key_log=key_log,
        full_log=full_log,
    )


def _run_aligned_test(plan: BuildPlan, env: Mapping[str, str], timeout_s: int, logs: List[str]) -> Tuple[str, str]:
    build_dir = plan.build_dir
    source_dir = plan.source_dir
    check_target = plan.check_target.strip()

    if (build_dir / "config.log").is_file():
        target = check_target or "check"
        cmd = ["make", target, "-j", _nproc()]
        code, out = run_cmd(cmd, cwd=build_dir, timeout_s=timeout_s, env=env)
        _append_log(logs, cmd, build_dir, out)
        return ("OK", "NONE") if code == 0 else ("FAIL", "TESTING")

    if (build_dir / "CMakeCache.txt").is_file():
        target = check_target or "test"
        if (build_dir / "build.ninja").is_file():
            cmd = ["ninja", target, "-j", _nproc()]
        elif (build_dir / "Makefile").is_file():
            cmd = ["make", target, "-j", _nproc()]
        else:
            logs.append("CMakeCache.txt exists, but neither build.ninja nor Makefile exists.\n")
            return "FAIL", "TESTING"
        code, out = run_cmd(cmd, cwd=build_dir, timeout_s=timeout_s, env=env)
        _append_log(logs, cmd, build_dir, out)
        return ("OK", "NONE") if code == 0 else ("FAIL", "TESTING")

    if (build_dir / "meson-info").is_dir():
        target = check_target or "test"
        cmd = ["meson", target]
        code, out = run_cmd(cmd, cwd=build_dir, timeout_s=timeout_s, env=env)
        _append_log(logs, cmd, build_dir, out)
        return ("OK", "NONE") if code == 0 else ("FAIL", "TESTING")

    if (source_dir / "Makefile").is_file():
        target = check_target or "check"
        cmd = ["make", target, "-j", _nproc()]
        code, out = run_cmd(cmd, cwd=source_dir, timeout_s=timeout_s, env=env)
        _append_log(logs, cmd, source_dir, out)
        return ("OK", "NONE") if code == 0 else ("FAIL", "TESTING")

    logs.append("No known test layout detected.\n")
    return "FAIL", "TESTING"


def run_cmake_build(plan: BuildPlan, timeout_s: int = 300) -> BuildResult:
    logs: List[str] = []
    env = _prepare_env(plan)

    _reset_build_dir(plan.build_dir)
    source_rel = _source_rel_from_build(plan)
    configure_opt = _split_opts(plan.configure_opt)

    cmd = ["cmake", source_rel, *configure_opt]
    code, out = run_cmd(cmd, cwd=plan.build_dir, timeout_s=timeout_s, env=env)
    _append_log(logs, cmd, plan.build_dir, out)
    if code != 0:
        return _make_result("FAIL", "CONFIGURATION", "\n".join(logs))

    if (plan.build_dir / "build.ninja").is_file():
        build_cmd = ["ninja", "-j", _nproc()]
    elif (plan.build_dir / "Makefile").is_file():
        build_cmd = ["make", "-j", _nproc()]
    else:
        logs.append("CMake succeeded, but no build.ninja / Makefile found.\n")
        return _make_result("FAIL", "CONFIGURATION", "\n".join(logs))

    code, out = run_cmd(build_cmd, cwd=plan.build_dir, timeout_s=timeout_s, env=env)
    _append_log(logs, build_cmd, plan.build_dir, out)
    if code != 0:
        return _make_result("FAIL", "BUILD", "\n".join(logs))

    test_status, test_stage = _run_aligned_test(plan, env, timeout_s, logs)
    if test_status != "OK":
        return _make_result("FAIL", test_stage, "\n".join(logs))

    return _make_result("OK", "NONE", "\n".join(logs))


def run_meson_build(plan: BuildPlan, timeout_s: int = 300) -> BuildResult:
    logs: List[str] = []
    env = _prepare_env(plan)

    _reset_build_dir(plan.build_dir)
    source_rel = _source_rel_from_build(plan)
    configure_opt = _split_opts(plan.configure_opt)

    cmd = ["meson", "setup", *configure_opt, source_rel]
    code, out = run_cmd(cmd, cwd=plan.build_dir, timeout_s=timeout_s, env=env)
    _append_log(logs, cmd, plan.build_dir, out)
    if code != 0:
        return _make_result("FAIL", "CONFIGURATION", "\n".join(logs))

    build_cmd = ["meson", "compile"]
    code, out = run_cmd(build_cmd, cwd=plan.build_dir, timeout_s=timeout_s, env=env)
    _append_log(logs, build_cmd, plan.build_dir, out)
    if code != 0:
        return _make_result("FAIL", "BUILD", "\n".join(logs))

    test_status, test_stage = _run_aligned_test(plan, env, timeout_s, logs)
    if test_status != "OK":
        return _make_result("FAIL", test_stage, "\n".join(logs))

    return _make_result("OK", "NONE", "\n".join(logs))


def _run_autotools_prepare(plan: BuildPlan, timeout_s: int, env: Mapping[str, str], logs: List[str]) -> None:
    source_dir = plan.source_dir
    if not (source_dir / "configure.ac").is_file():
        return

    if (source_dir / "autogen.sh").is_file():
        cmd = ["bash", "./autogen.sh"]
        code, out = run_cmd(cmd, cwd=source_dir, timeout_s=timeout_s, env=env)
        _append_log(logs, cmd, source_dir, out)

        cmd2 = ["make", "distclean"]
        _, out2 = run_cmd(cmd2, cwd=source_dir, timeout_s=timeout_s, env=env)
        _append_log(logs, cmd2, source_dir, out2)

    elif (source_dir / "bootstrap").is_file():
        cmd = ["bash", "./bootstrap"]
        code, out = run_cmd(cmd, cwd=source_dir, timeout_s=timeout_s, env=env)
        _append_log(logs, cmd, source_dir, out)

    elif (source_dir / "autogen.pl").is_file():
        cmd = ["perl", "./autogen.pl"]
        code, out = run_cmd(cmd, cwd=source_dir, timeout_s=timeout_s, env=env)
        _append_log(logs, cmd, source_dir, out)

    else:
        cmd = ["autoreconf", "-i", "-f"]
        code, out = run_cmd(cmd, cwd=source_dir, timeout_s=timeout_s, env=env)
        _append_log(logs, cmd, source_dir, out)


def run_autotools_build(plan: BuildPlan, timeout_s: int = 300) -> BuildResult:
    logs: List[str] = []
    env = _prepare_env(plan)

    _run_autotools_prepare(plan, timeout_s, env, logs)
    _reset_build_dir(plan.build_dir)

    if not (plan.source_dir / "configure").is_file():
        logs.append(f"configure not found: {plan.source_dir / 'configure'}\n")
        return _make_result("FAIL", "CONFIGURATION", "\n".join(logs))

    source_rel = _source_rel_from_build(plan)
    configure_opt = _split_opts(plan.configure_opt)

    cmd = [f"{source_rel}/configure", *configure_opt]
    code, out = run_cmd(cmd, cwd=plan.build_dir, timeout_s=timeout_s, env=env)
    _append_log(logs, cmd, plan.build_dir, out)
    if code != 0:
        return _make_result("FAIL", "CONFIGURATION", "\n".join(logs))

    build_cmd = ["make", "-j", _nproc()]
    code, out = run_cmd(build_cmd, cwd=plan.build_dir, timeout_s=timeout_s, env=env)
    _append_log(logs, build_cmd, plan.build_dir, out)
    if code != 0:
        return _make_result("FAIL", "BUILD", "\n".join(logs))

    test_status, test_stage = _run_aligned_test(plan, env, timeout_s, logs)
    if test_status != "OK":
        return _make_result("FAIL", test_stage, "\n".join(logs))

    return _make_result("OK", "NONE", "\n".join(logs))


def run_makefile_build(plan: BuildPlan, timeout_s: int = 300) -> BuildResult:
    logs: List[str] = []
    env = _prepare_env(plan)

    _reset_build_dir(plan.build_dir)

    if not (plan.source_dir / "Makefile").is_file():
        logs.append(f"Makefile not found: {plan.source_dir / 'Makefile'}\n")
        return _make_result("FAIL", "CONFIGURATION", "\n".join(logs))

    build_cmd = ["make", "-j", _nproc()]
    code, out = run_cmd(build_cmd, cwd=plan.source_dir, timeout_s=timeout_s, env=env)
    _append_log(logs, build_cmd, plan.source_dir, out)
    if code != 0:
        return _make_result("FAIL", "BUILD", "\n".join(logs))

    test_status, test_stage = _run_aligned_test(plan, env, timeout_s, logs)
    if test_status != "OK":
        return _make_result("FAIL", test_stage, "\n".join(logs))

    return _make_result("OK", "NONE", "\n".join(logs))


def execute_build_plan(plan: BuildPlan, timeout_s: int = 300) -> BuildResult:
    if plan.effective_type == "CMAKE":
        return run_cmake_build(plan, timeout_s)
    elif plan.effective_type == "MESON":
        return run_meson_build(plan, timeout_s)
    elif plan.effective_type == "AUTOTOOLS":
        return run_autotools_build(plan, timeout_s)
    elif plan.effective_type == "MAKEFILE":
        return run_makefile_build(plan, timeout_s)
    else:
        full_log = f"Unsupported build type: {plan.effective_type}"
        return _make_result("FAIL", "UNKNOWN", full_log)