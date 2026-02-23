# MathProve-Skill v1.0 核心实现计划

> 基线标签: `v0.5.0-baseline` (commit 40126d9)
> 全部 17 测试通过，现有 ~2,210 LOC runtime/scripts 实现完整

## 任务总览

### M1: ProofSearchTree — 证明搜索树状态机 (机制1)
- **目标**: 将 status.json 驱动的状态机固化为 Python 类
- **输出**: `skill/runtime/proof_tree.py`
- **依赖**: 无（纯新增）
- **关键类**:
  - `ProofNode`: 单个证明节点（step_id, status, children, parent, attempts, error_log）
  - `ProofSearchTree`: 树管理器（add_node, get_current, advance, backtrack, serialize/deserialize）
  - 状态枚举: PENDING → MAGI_APPROVED → SYMPY_PASSED → LEAN_PASSED → PASSED / FAILED
  - `to_status_json()` / `from_status_json()` — 与现有 status.json 格式兼容

### M2: ErrorClassifier — 结构化错误分类与自愈循环 (机制4)
- **目标**: 实现三级错误分类 + 自动重试 + Prompt重构
- **输出**: `skill/runtime/error_classifier.py`
- **依赖**: M1 (ProofSearchTree 用于回滚/改道)
- **关键类**:
  - `ErrorCategory` 枚举: SYNTAX, LOGIC, ENVIRONMENT
  - `StructuredError` dataclass: category, source(sympy/lean/magi), message, location, raw_stderr
  - `classify(stderr: str, source: str) -> StructuredError` — 正则+启发式分类
  - `suggest_fix(error: StructuredError) -> str` — 生成修复建议 Prompt 片段
  - `RetryBudget`: 跟踪每步的重试次数（magi:2, sympy:3, lean:5）

### M3: ParallelCandidateRunner — 并行候选竞速框架 (机制5)
- **目标**: N 分支并行验证 + 首胜取消 + 物理隔离
- **输出**: `skill/runtime/parallel_runner.py`
- **依赖**: M1, workspace.py (EphemeralWorkspace)
- **关键类**:
  - `CandidateBranch` dataclass: branch_id, lean_code/sympy_code, workspace_path, status
  - `ParallelRunner`:
    - `run_candidates(candidates: list[CandidateBranch], timeout) -> CandidateBranch | None`
    - 内部使用 ProcessPoolExecutor
    - 首个成功者返回，terminate 其余进程
    - 每个分支在独立 EphemeralWorkspace 中运行
  - `SearchTreeLogger`: 递归 JSON 结构记录搜索树

### M4: SafeVerify — Lean4 终极白盒审计 (机制6)
- **目标**: 纯 Lean4 原生审计模块
- **输出**:
  - `skill/runtime/safe_verify.py` (Python 编排层)
  - `skill/assets/lean/safe_verify_template.lean` (Lean4 审计模板)
- **依赖**: verify_lean.py, final_audit.py (现有)
- **关键功能**:
  - 生成独立 `final_audit.lean`（import 主定理 + #print axioms）
  - 违禁词扫描: sorry, admit, partial, unsafe, sorryAx
  - 公理溯源: 解析 #print axioms 输出
  - (可选) 零缓存重编译: lean --make in clean env

### M5: OrchestratorLoop — 顶层编排循环集成 (机制1+2+3)
- **目标**: 将 M1-M4 集成为完整的编排循环
- **输出**: `skill/runtime/orchestrator.py`
- **依赖**: M1, M2, M3, M4 + 现有 magi_plan/step_router/verify_*
- **关键功能**:
  - `run(problem: str, config: dict) -> AuditResult`
  - 阶段 A: 预检 + 工作区初始化
  - 阶段 B: MAGI 全局规划 → steps.json
  - 阶段 C: 逐步循环（MAGI决策 → SymPy → Lean4 → 证据包 → draft）
  - 阶段 D: SafeVerify + final_audit → Solution.md
  - 错误时调用 ErrorClassifier 决定重试/改道/停止
  - 复杂步骤调用 ParallelRunner 多路探索

### M6: 测试套件 — 全覆盖单元测试
- **目标**: 为 M1-M5 编写测试
- **输出**: `tests/test_proof_tree.py`, `tests/test_error_classifier.py`,
  `tests/test_parallel_runner.py`, `tests/test_safe_verify.py`, `tests/test_orchestrator.py`
- **依赖**: M1-M5

## 执行顺序与并行策略

```
        M1 (ProofSearchTree)
       / |
      /  |
    M2   M4 (ErrorClassifier / SafeVerify — 可并行)
      \  |
       \ |
        M3 (ParallelRunner — 依赖 M1)
         |
        M5 (Orchestrator — 集成全部)
         |
        M6 (Tests — 最后收尾)
```

- **Phase 1 (并行)**: M1 + M4（无依赖关系，可同时开发） ✅ DONE (commit 8fd2740)
- **Phase 2 (并行)**: M2 + M3（M2 依赖 M1，M3 依赖 M1） ✅ DONE (commit e70d5f3)
- **Phase 3**: M5（集成所有模块） ✅ DONE (commit 1263910)
- **Phase 4**: M6（测试收尾） ✅ DONE — 117 tests all passing

## 实现统计
- 新增代码: ~2,700 LOC (5 runtime modules + 5 test files)
- 总测试: 117 (17 existing + 100 new)
- 新增模块: proof_tree, error_classifier, parallel_runner, safe_verify, orchestrator
