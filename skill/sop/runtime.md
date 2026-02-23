# SOP: v1.0 运行时模块指南

> **加载时机**: 需要了解 Runtime 模块 API 或使用 Orchestrator 时

---

## 1. ProofSearchTree (`skill/runtime/proof_tree.py`)

证明搜索树状态机，管理所有 step 的生命周期。

```python
from skill.runtime.proof_tree import ProofSearchTree, NodeStatus, Phase
```

### NodeStatus 状态转移

```
PENDING → MAGI_APPROVED → SYMPY_PASSED → LEAN_PASSED → PASSED
    ↘          ↘              ↘              ↘          ↗
     → → → → FAILED ← ← ← ← ← ← ← ← ← ← ← ← ← ←
```

（也可 PENDING → MAGI_REJECTED → PENDING 重投）

### 核心 API

| 方法 | 说明 |
|------|------|
| `add_node(step_id, parent_id?)` | 添加节点 |
| `advance(step_id, new_status)` | 推进状态（非法转移抛 ValueError） |
| `backtrack(step_id)` | 回滚：递归标记后代 FAILED，重置为 PENDING |
| `save(path)` / `load(path)` | 持久化 / 反序列化 |
| `to_status_json()` | 与 status.json 兼容的字典输出 |

## 2. ErrorClassifier (`skill/runtime/error_classifier.py`)

→ 详见 `sop/error.md`

## 3. ParallelRunner (`skill/runtime/parallel_runner.py`)

→ 详见 `sop/error.md` §5

## 4. SafeVerify (`skill/runtime/safe_verify.py`)

→ 详见 `sop/audit.md` §3

### 完整 API

```python
from skill.runtime.safe_verify import (
    run_audit,             # 完整审计流水线
    scan_forbidden_tokens, # 违禁词扫描
    generate_audit_lean,   # 生成 audit.lean
    parse_axioms_output,   # 解析 #print axioms
    strip_lean_comments,   # 剥离注释
)
```

## 5. Orchestrator (`skill/runtime/orchestrator.py`)

一键编排入口，集成上述所有模块。

```python
from skill.runtime.orchestrator import Orchestrator, OrchestratorConfig

orch = Orchestrator(OrchestratorConfig(enable_safe_verify=True))
result = orch.run("证明: ...", steps)
print(result.summary)
```

### 编排阶段

| 阶段 | 模块 |
|------|------|
| A. 初始化 | ProofSearchTree + RetryBudget |
| B. 逐步执行 | subprocess 物理隔离 |
| C. 失败处理 | classify → suggest → retry/backtrack |
| D. 审计 | SafeVerify 白盒审计 |

## 6. 工作区管理

```python
from skill.runtime.workspace_manager import WorkspaceManager
from skill.runtime.config_loader import load_config
```

- `WorkspaceManager` 创建 run 目录结构
- `load_config()` 加载 config.yaml + config.local.yaml 覆盖
