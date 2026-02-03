"""兼容导入：`MathProve.scripts.*` -> `scripts.*`。

说明：
- 仓库根目录的 `scripts/` 是当前脚本的真实实现。
- `MathProve/scripts/` 仅作为兼容层，保持旧的 import 路径可用。
"""

from . import problem_router, step_router

__all__ = [
    "problem_router",
    "step_router",
]

