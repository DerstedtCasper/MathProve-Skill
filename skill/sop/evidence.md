# SOP: 证据包与草稿写入

> **加载时机**: 阶段 C 逐步循环 — SymPy & Lean4 均通过后

---

## 1. 证据包 Evidence Pack

每个通过的 step 必须生成：`evidence/step_XXX_evidence.json`

### 最小 Schema

```json
{
  "step_id": "step_001",
  "magi": {
    "vote_file": "magi/step_001_vote.json",
    "status": "APPROVED"
  },
  "sympy": {
    "script": "sympy/step_001_check.py",
    "output": "sympy/step_001_out.txt",
    "exit_code": 0,
    "pass_marker_found": true
  },
  "lean": {
    "file": "lean/Step001.lean",
    "log": "lean/step_001_lean.log",
    "exit_code": 0,
    "error_found": false
  },
  "artifacts_exist": true,
  "timestamp": "2025-01-01T00:00:00Z"
}
```

任何字段缺失或 `artifacts_exist=false` → 该 step 不允许标记 passed。

## 2. 草稿写入

### 必须写入的文件

| 文件 | 说明 |
|------|------|
| `draft/step_XXX.md` | 该步的可读解释 + 证据引用 |
| `draft/proof_draft.md` | 按顺序拼接所有 step 的索引 |

### step_XXX.md 格式（强制区块）

1. **Step Claim** — 本步结论（含 LaTeX）
2. **Dependencies** — 引用前置 steps
3. **Proposal Summary** — MAGI 通过的方案摘要 + hazards + 前提
4. **SymPy Verification** — 脚本路径、关键表达式、PASS 行引用
5. **Lean4 Verification** — 文件路径、lemma/theorem 名、编译证据
6. **Evidence Pack** — 指向 evidence json
7. **Status** — `passed`

### 写入时机（再次强调）

仅当以下条件**全部满足**才允许写入：
- MAGI = APPROVED
- SymPy 通过（exit_code=0 + PASS marker）
- Lean4 通过（exit_code=0 + 无 error + strict 无 sorry）
- Evidence Pack 齐全（artifacts_exist=true）
