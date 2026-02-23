# SOP: 终局审计与失败报告

> **加载时机**: 阶段 D — 所有 step 完成后进入审计

---

## 1. 调用方式

```bash
python scripts/final_audit.py \
  --run_dir WORKSPACE/runs/<run_id> \
  --steps plan/steps.json \
  --draft draft/proof_draft.md \
  --out audit/audit.json \
  --solution audit/Solution.md
```

## 2. 审计必须检查

- [ ] steps.json 中每个 step 都有对应的 magi vote / sympy / lean / evidence 文件
- [ ] PASS marker 存在且 exit_code 正确
- [ ] Lean log 无 error（strict 默认无 sorry）
- [ ] draft 中每步都包含证据引用
- [ ] status.json 中所有 step.status == passed
- 任一项失败 → `audit.status = REJECTED`，生成 `audit/FAILURE_REPORT.md`

## 3. SafeVerify 白盒审计（v1.0 MUST）

```python
from skill.runtime.safe_verify import run_audit, scan_forbidden_tokens
```

- `scan_forbidden_tokens(source)` — 检测 sorry/admit/partial/unsafe
- `run_audit(lean_files, theorem_names, import_module)` — 完整审计流水线
- 任何 `sorryAx` 检测 → 立即判定不通过

## 4. 终局输出约束

| audit.status | 允许的输出 |
|------|------|
| APPROVED | 可向用户输出"证明完成" + 引用 Solution.md |
| REJECTED | 只能输出失败原因摘要 + 具体 step + 日志路径 |

## 5. 失败报告 FAILURE_REPORT.md

当 step 或 audit 失败时，必须生成 `audit/FAILURE_REPORT.md`，包含：

1. 失败 step_id
2. 失败阶段（MAGI / SymPy / Lean / Audit）
3. 关键错误日志路径 + 核心错误行（5~20 行）
4. 已尝试的修复动作与次数
5. 建议的下一步（需要用户补充条件？重写 step？）

## 6. 错误恢复重试预算

| 阶段 | 上限 |
|------|------|
| MAGI | 每 step 最多 2 次修订重投 |
| SymPy | 每 step 最多 3 次脚本修复 |
| Lean4 | 每 step 最多 5 次修复重编译 |

超过上限 → 必须停止推进并生成 FAILURE_REPORT。
