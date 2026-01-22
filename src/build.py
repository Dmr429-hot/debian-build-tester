import subprocess
from pathlib import Path
from typing import Tuple


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout_s: int = 300) -> Tuple[int, str]:
    """
    运行命令并捕获输出
    :param cmd: 命令行列表
    :param cwd: 工作目录
    :param timeout_s: 超时设置
    :return: 返回执行代码和输出日志
    """
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_s,
    )
    return p.returncode, p.stdout


def build_project(repo_dir: Path, build_type: str, timeout_s: int = 300) -> Tuple[str, str, str]:
    """
    执行构建命令，返回构建状态、日志和失败阶段
    :param repo_dir: 仓库路径
    :param build_type: 构建类型(CMake / Meson 等)
    :param timeout_s: 超时设置
    :return: 构建状态(成功/失败)、构建日志、失败阶段
    """
    build_status, build_log = "FAIL", ""
    failure_stage = "UNKNOWN"  # 默认值，未确定失败阶段

    if build_type == "MESON":
        build_status, build_log, failure_stage = run_meson_build(repo_dir, timeout_s)
    elif build_type == "CMAKE":
        build_status, build_log, failure_stage = run_cmake_build(repo_dir, timeout_s)
    else:
        return "FAIL", f"Unsupported build type: {build_type}", failure_stage

    # 记录错误日志并返回
    if build_status == "FAIL":
        print(f"Build failed for {repo_dir}. Stage: {failure_stage}. Log: {build_log}")

    # 删除构建的仓库
    if repo_dir.exists():
        subprocess.run(["rm", "-rf", str(repo_dir)], check=True)

    return build_status, build_log, failure_stage



def run_meson_build(repo_dir: Path, timeout_s: int) -> Tuple[str, str, str]:
    """
    使用 Meson 构建项目，并记录失败阶段
    :param repo_dir: 仓库路径
    :param timeout_s: 超时设置
    :return: 构建状态、构建日志、失败阶段
    """
    build_dir = repo_dir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    # 配置命令
    meson_cmd = ["meson", "setup", str(build_dir)]
    code, out = run_cmd(meson_cmd, cwd=repo_dir, timeout_s=timeout_s)
    if code != 0:
        return "FAIL", out, "CONFIGURATION"

    # 执行构建
    build_cmd = ["ninja"]
    code, out = run_cmd(build_cmd, cwd=build_dir, timeout_s=timeout_s)
    if code != 0:
        return "FAIL", out, "BUILD"

    # 执行测试
    test_cmd = ["ninja", "test"]
    code, out = run_cmd(test_cmd, cwd=build_dir, timeout_s=timeout_s)
    if code != 0:
        return "FAIL", out, "TESTING"

    return "OK", out, "NONE"  # 成功时返回“没有失败”

def run_cmake_build(repo_dir: Path, timeout_s: int) -> Tuple[str, str, str]:
    """
    使用 CMake 构建项目，并记录失败阶段
    :param repo_dir: 仓库路径
    :param timeout_s: 超时设置
    :return: 构建状态、构建日志、失败阶段
    """
    build_dir = repo_dir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    # 配置命令
    cmake_cmd = ["cmake", ".."]
    code, out = run_cmd(cmake_cmd, cwd=build_dir, timeout_s=timeout_s)
    if code != 0:
        return "FAIL", out, "CONFIGURATION"

    # 执行构建
    build_cmd = ["make", "-j", str(min(4, os.cpu_count()))]  # 使用 4 核，最多
    code, out = run_cmd(build_cmd, cwd=build_dir, timeout_s=timeout_s)
    if code != 0:
        return "FAIL", out, "BUILD"

    # 执行测试
    test_cmd = ["make", "test"]
    code, out = run_cmd(test_cmd, cwd=build_dir, timeout_s=timeout_s)
    if code != 0:
        return "FAIL", out, "TESTING"

    return "OK", out, "NONE"  # 成功时返回“没有失败”


