"""运行时路径定位（兼容标准 skill 目录与仓库根目录布局）。

设计目标：
- 保持脚本可“直接运行”（`python scripts/xxx.py`）与“包内导入”两种方式都可用。
- 目录迁移后仍能定位 `assets/`、`references/` 等资源（为后续 `skill/` 标准化铺路）。

约定：
- 未来标准布局：`<repo>/skill/SKILL.md` 存在，则 `skill_root = <repo>/skill`
- 当前布局：`<repo>/SKILL.md` 存在，则 `skill_root = <repo>`
"""

from __future__ import annotations

from pathlib import Path

try:
    from ..runtime.workspace_manager import ensure_run_dir
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from runtime.workspace_manager import ensure_run_dir

def _walk_up(start: Path) -> list[Path]:
    out: list[Path] = []
    cur = start.resolve()
    while True:
        out.append(cur)
        if cur.parent == cur:
            return out
        cur = cur.parent


def skill_root() -> Path:
    """返回“Skill 根目录”（包含 SKILL.md 的目录）。"""
    # 以当前文件所在位置向上探测：脚本移动到 skill/scripts 后也仍可工作
    here = Path(__file__).resolve()
    for p in _walk_up(here.parent):
        if (p / "skill" / "SKILL.md").exists():
            return p / "skill"
        if (p / "SKILL.md").exists():
            return p
    # fallback：至少返回仓库根推测（脚本目录的上一级）
    return here.parents[1]


def repo_root() -> Path:
    """返回“仓库根目录”（包含 .git 的目录；若无 .git 则回退到 skill_root 的父级）。"""
    here = Path(__file__).resolve()
    for p in _walk_up(here.parent):
        if (p / ".git").exists():
            return p
    sr = skill_root()
    return sr.parent if sr.name == "skill" else sr


def assets_dir() -> Path:
    sr = skill_root()
    candidate = sr / "assets"
    if candidate.exists():
        return candidate
    # 兼容：某些布局下 assets 仍在 repo root
    rr = repo_root()
    return rr / "assets"


def references_dir() -> Path:
    sr = skill_root()
    candidate = sr / "references"
    if candidate.exists():
        return candidate
    rr = repo_root()
    return rr / "references"


def logs_dir() -> Path:
    run_dir = ensure_run_dir()
    return run_dir / "logs"


def subagent_tasks_dir() -> Path:
    run_dir = ensure_run_dir()
    return run_dir / "subagent_tasks"

