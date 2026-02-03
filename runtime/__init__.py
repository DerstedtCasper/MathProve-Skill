"""运行时兼容层（repo root）。

目的：
- 标准 Skill 形态下，真实实现位于 `skill/runtime/`（作为 Skill 的一部分）。
- 仓库根目录仍保留 `import runtime.*` 形式的导入路径（用于 tests / 独立 CLI）。

实现方式：
- 在导入时把 `skill/runtime` 追加到当前包的 `__path__`，让 `runtime.workspace` 等子模块从
  `skill/runtime` 被发现并加载。
"""

from __future__ import annotations

from pathlib import Path

# `runtime` 是一个普通包；将实现目录加入搜索路径，避免重复拷贝代码。
_SKILL_RUNTIME = Path(__file__).resolve().parents[1] / "skill" / "runtime"
if _SKILL_RUNTIME.exists():
    __path__.append(str(_SKILL_RUNTIME))  # type: ignore[name-defined]

