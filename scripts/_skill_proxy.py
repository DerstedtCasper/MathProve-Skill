"""加载并代理 `skill/scripts/<same-name>` 的实现。

要求：
- wrapper 文件名必须与目标脚本同名（例如 `scripts/final_audit.py` -> `skill/scripts/final_audit.py`）。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _target_path(wrapper_file: str) -> Path:
    wrapper = Path(wrapper_file).resolve()
    repo_root = wrapper.parents[1]
    return repo_root / "skill" / "scripts" / wrapper.name


def proxy_module(wrapper_file: str, g: dict) -> ModuleType:
    """加载目标模块并把其公共符号注入到当前 wrapper 的 globals。"""
    target = _target_path(wrapper_file)
    if not target.exists():
        raise FileNotFoundError(f"skill script not found: {target}")

    # 让目标脚本的“本地导入”（如 `import logger`）可用
    target_dir = str(target.parent)
    if target_dir not in sys.path:
        sys.path.insert(0, target_dir)

    # 以唯一模块名加载，避免污染 `scripts.*` 命名空间
    mod_name = f"_skill_scripts_{target.stem}"
    spec = importlib.util.spec_from_file_location(mod_name, target)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"cannot load module spec: {target}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    for k, v in vars(mod).items():
        if k.startswith("_"):
            continue
        g[k] = v
    g["__doc__"] = getattr(mod, "__doc__", None)
    return mod

