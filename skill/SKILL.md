---
name: mathprove-skill
description: |
  面向复杂数学证明/推导/等价变形的"分步-工具验证-形式化门控"技能。
  强制以步骤为单位：MAGI 共识 → SymPy 验证 → Lean4 形式化 → 证据包 → 审计。
metadata:
  version: 1.0.0
  triggers: ["证明","形式化验证","Lean4","SymPy","推导","等价变形","prove","formalize"]
  tags: [math, theorem-proving, sympy, lean4, verification, magi]
---

# MathProve Skill

本技能把证明当成可执行、可复核的软件流水线。每个结论必须绑定物理证据。

---

## 0. 不可谈判硬规则（MUST）

0.1 **目录写入边界** — 只能在 `WORKSPACE/` 下读写产物。禁止在 skill 包内写入任何临时文件。

0.2 **禁止角色扮演** — 不得在主线程假装三人格。MAGI 必须通过 `scripts/magi_plan.py` 实现。

0.3 **门控写入** — 仅当 MAGI=APPROVED + SymPy 通过 + Lean4 通过 + 证据包齐全，才允许写入 draft 并标记 passed。

0.4 **终局约束** — `final_audit.py` 输出 APPROVED 之前，不得宣称"证明完成"。

0.5 **可复核** — 每次工具调用的命令、输入、输出、退出码，必须落盘 workspace。

---

## 1. 工作区结构

```
WORKSPACE/runs/<run_id>/
├── problem.md / assumptions.md / manifest.json / status.json
├── plan/        steps.json + steps_readme.md
├── magi/        step_XXX_vote.json
├── sympy/       step_XXX_check.py + step_XXX_out.txt
├── lean/        StepXXX.lean + step_XXX_lean.log
├── draft/       step_XXX.md + proof_draft.md
├── evidence/    step_XXX_evidence.json
├── audit/       audit.json + Solution.md + FAILURE_REPORT.md
└── logs/        init_check.log + tool_calls.log + errors.log
```

run_id 格式：`YYYYMMDD_HHMMSS_<short_hash>`

---

## 2. 强制流程（4 阶段）

| 阶段 | 步骤 | 详细 SOP |
|------|------|----------|
| **A. 预检** | check_routes → 创建 run 目录 → 写 problem.md + assumptions.md | — |
| **B. 规划** | magi_plan → steps.json → 结构校验 | — |
| **C. 逐步循环** | 对每个 step: proposal → MAGI → SymPy → Lean4 → evidence → draft | `sop/magi.md` `sop/sympy.md` `sop/lean.md` `sop/evidence.md` |
| **D. 审计** | final_audit → audit.json + Solution.md | `sop/audit.md` |

失败时参考 `sop/error.md`。

---

## 3. steps.json 最小 Schema

每个 step 必须原子化（一次只做一个可验证的最小推导单元），包含：

- `id`, `title`, `claim`（含 LaTeX）
- `inputs`（前置 step id 列表）
- `method`（sympy/lean/both）
- `sympy`: { required, check_goal }
- `lean`: { required, theorem_goal }
- `evidence_required`, `risks`, `accept_criteria`

---

## 4. status.json 状态机

```
phase: init → planning → step_loop → auditing → done | failed
step.status: pending → magi_approved → sympy_passed → lean_passed → passed | failed
```

使用 `ProofSearchTree` 管理，非法转移抛 ValueError。详见 `sop/runtime.md`。

---

## 5. 运行时模块（v1.0）

| 模块 | 路径 | 职责 |
|------|------|------|
| ProofSearchTree | `runtime/proof_tree.py` | 状态机管理 |
| ErrorClassifier | `runtime/error_classifier.py` | 三级错误分类 + RetryBudget |
| ParallelRunner | `runtime/parallel_runner.py` | N 分支并行竞速 |
| SafeVerify | `runtime/safe_verify.py` | Lean4 白盒审计 |
| Orchestrator | `runtime/orchestrator.py` | 一键编排入口 |

详细 API 参考 `sop/runtime.md`。

---

## 6. SOP 按需加载索引

| SOP 文件 | 加载时机 |
|----------|----------|
| `sop/magi.md` | 阶段 C — 每个 step 验证前 |
| `sop/sympy.md` | 阶段 C — MAGI 通过后 SymPy 验证 |
| `sop/lean.md` | 阶段 C — SymPy 通过后 Lean4 验证 |
| `sop/evidence.md` | 阶段 C — 验证全部通过后写证据+草稿 |
| `sop/audit.md` | 阶段 D — 终局审计 |
| `sop/error.md` | 任何验证失败时 |
| `sop/runtime.md` | 需要 Runtime API 参考时 |

---

## 7. 汇报规范

- 每次汇报含：run_id、当前 phase/step、通过/失败、证据路径
- 不贴长日志全文（最多 5~20 行关键错误行）
- 完整日志留在 workspace，指向文件路径

---

## 8. 执行清单

- [ ] check_routes 成功 + logs/init_check.log
- [ ] run 目录 + problem.md + assumptions.md + status.json
- [ ] steps.json 每步有 evidence_required + accept_criteria
- [ ] 每步：MAGI vote → SymPy PASS → Lean4 PASS → evidence → draft
- [ ] final_audit = APPROVED → 输出 Solution.md
