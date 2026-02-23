# SOP: Lean4 形式化验证

> **加载时机**: 阶段 C 逐步循环 — SymPy 通过后进入 Lean4 验证

---

## 1. 产物要求（每步必须落盘）

| 文件 | 说明 |
|------|------|
| `lean/StepXXX.lean` | Lean 文件（lemma/theorem） |
| `lean/step_XXX_lean.log` | 编译日志（stdout+stderr） |

## 2. 文件规范（强制）

- 显式导入所需库（mathlib 习惯）
- 把 assumptions（域条件、可微性等）写成显式参数/前提
- 即使只做引理，也须写成可被后续步骤引用的 lemma

### 模板

```lean
-- lean/Step001.lean
import Mathlib

variable {x : ℝ}

theorem step_001 : (/* goal */) := by
  -- proof tactics
  sorry  -- ← strict 模式下禁止
```

## 3. sorry 策略

| 模式 | 规则 |
|------|------|
| strict（默认） | 禁止 sorry，编译成功且无 sorry 才算通过 |
| relaxed | 由 steps.json 的 `accept_criteria` 显式声明允许，审计中记录 |

## 4. 编译执行

```bash
lake env lean lean/Step001.lean > lean/step_001_lean.log 2>&1
```

## 5. 重试策略

- 最多 **5 次**修复重编译
- 每次依据 Lean 错误信息精确修复：类型、引理引用、域前提、simp lemma
- 5 次仍失败：该 step 判定失败，生成 FAILURE_REPORT

## 6. 不可逾越约束

- Lean4 无法证明时，**不得用自然语言补洞**
- 必须要么改步骤（引入合适引理/前提），要么明确失败并停止
- 不得把 `sorry` 当成通过（strict 模式）
