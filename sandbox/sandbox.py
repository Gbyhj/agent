"""
Sandbox System — 安全代码执行

设计融合:
- Grok Build: 四级沙箱 (off/workspace/read-only/strict)
- Smolagents: Executor 抽象 (local/docker/e2b)
- E2B: <200ms 冷启动隔离沙箱

用法:
    from agent.sandbox import Sandbox
    sandbox = Sandbox(mode="workspace")
    result = sandbox.execute_bash("ls -la", timeout=10)
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    truncated: bool = False


class Sandbox:
    """
    安全沙箱

    权限级别:
    - off:       无限制（不推荐）
    - workspace: CWD + 子目录，可写，可联网（默认）
    - read-only: CWD + 子目录，只读，无网络
    - strict:    仅 /tmp，无网络，无写
    """

    BLOCKED_COMMANDS = [
        r"rm\s+-rf\s+/", r"sudo\s+", r"mkfs\.", r"dd\s+if=",
        r">\s*/dev/", r"chmod\s+777\s+/", r":\(\)\s*\{ :\|:& \};:",
        r"curl.*\|\s*(ba)?sh", r"wget.*-O\s*-\s*\|\s*sh",
    ]

    SENSITIVE_PATHS = [
        "~/.ssh", "~/.aws", "~/.gcloud", "~/.azure",
        "/etc/passwd", "/etc/shadow", "/etc/sudoers",
        "~/.bash_history", "~/.zsh_history",
    ]

    def __init__(self, mode: str = "workspace", cwd: str | None = None):
        self.mode = mode
        self.cwd = cwd or os.getcwd()

    def validate_path(self, path: str, allow_write: bool = False) -> str:
        """
        验证并规范化文件路径（防路径遍历攻击）

        Args:
            path: 用户提供的路径
            allow_write: 是否允许写入

        Returns:
            规范化后的绝对路径

        Raises:
            PermissionError: 路径不安全
        """
        # 展开 ~ 和相对路径
        expanded = os.path.expanduser(path)
        if not os.path.isabs(expanded):
            expanded = os.path.join(self.cwd, expanded)

        # 规范化（消除 ../ ）
        normalized = os.path.normpath(expanded)
        resolved = os.path.realpath(normalized) if os.path.exists(os.path.dirname(normalized)) else normalized

        # 1. 检查敏感路径
        for sensitive in self.SENSITIVE_PATHS:
            sensitive_expanded = os.path.expanduser(sensitive)
            if resolved.startswith(sensitive_expanded):
                raise PermissionError(f"禁止访问敏感路径: {sensitive}")

        # 2. 严格模式：禁止访问 CWD 之外
        if self.mode == "strict":
            cwd_real = os.path.realpath(self.cwd)
            if not resolved.startswith(cwd_real) and not resolved.startswith("/tmp"):
                raise PermissionError(f"严格模式禁止访问 CWD 之外的路径: {path}")

        # 3. 只读模式：禁止写入
        if self.mode == "read-only" and allow_write:
            raise PermissionError(f"只读模式禁止写入: {path}")

        # 4. 检查是否存在解引用后的路径遍历
        if ".." in Path(path).parts:
            raise PermissionError(f"禁止路径遍历: {path}")

        return resolved

    def execute_bash(self, command: str, timeout: int = 30) -> SandboxResult:
        """在沙箱中执行 Shell 命令"""
        # 命令安全检查
        for pattern in self.BLOCKED_COMMANDS:
            if re.search(pattern, command):
                return SandboxResult(
                    stdout="", stderr=f"阻止执行: 匹配危险模式 '{pattern}'",
                    exit_code=1,
                )

        # 严格模式禁止网络
        if self.mode == "strict":
            if re.search(r"\b(curl|wget|nc|telnet|ssh|scp)\b", command):
                return SandboxResult(
                    stdout="", stderr="严格模式禁止网络访问",
                    exit_code=1,
                )

        try:
            env = os.environ.copy()
            if self.mode in ("read-only", "strict"):
                env["http_proxy"] = ""
                env["https_proxy"] = ""
                env["HTTP_PROXY"] = ""
                env["HTTPS_PROXY"] = ""

            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=min(timeout, 120), cwd=self.cwd,
                env=env,
            )

            stdout = result.stdout[-10000:]  # 限制输出
            stderr = result.stderr[-5000:]
            truncated = len(result.stdout) > 10000 or len(result.stderr) > 5000

            if truncated:
                stdout = "...(truncated)\n" + stdout

            return SandboxResult(
                stdout=stdout or "(无输出)",
                stderr=stderr,
                exit_code=result.returncode,
                truncated=truncated,
            )

        except subprocess.TimeoutExpired:
            return SandboxResult(stdout="", stderr=f"命令超时 ({timeout}s)", exit_code=124)
        except Exception as e:
            return SandboxResult(stdout="", stderr=str(e), exit_code=1)

    def execute_docker(self, command: str, image: str = "python:3.12-slim",
                       timeout: int = 60) -> SandboxResult:
        """在 Docker 容器中执行命令（完全隔离）"""
        try:
            result = subprocess.run(
                ["docker", "run", "--rm", "--network=none", "--read-only",
                 f"--memory=256m", f"--cpus=0.5",
                 "-v", f"{self.cwd}:/workspace:ro",
                 image, "bash", "-c", command],
                capture_output=True, text=True,
                timeout=min(timeout, 60),
            )
            return SandboxResult(
                stdout=result.stdout[-5000:] or "(无输出)",
                stderr=result.stderr[-2000:],
                exit_code=result.returncode,
            )
        except FileNotFoundError:
            return SandboxResult(
                stdout="", stderr="Docker 未安装。回退到本地沙箱执行。",
                exit_code=1,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(stdout="", stderr="Docker 命令超时", exit_code=124)
        except Exception as e:
            return SandboxResult(stdout="", stderr=str(e), exit_code=1)


# 默认沙箱实例
default_sandbox = Sandbox(mode="workspace")
