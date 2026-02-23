# SOP: MAGI 并行共识决策

> **加载时机**: 阶段 C 逐步循环 — 每个 step 进入验证前

---

## 1. 触发时机（MUST）

对每个 step：在进入 SymPy/Lean 函数级验证**之前**，必须触发 MAGI 做方案决策。

## 2. 输入准备

对 Step i 的 MAGI 输入必须包含：
- `step.claim`（本步要得到什么）
- `step.inputs`（依赖的前置步骤 id 列表）
- 本步证明思路 proposal（写入 `draft/step_XXX_proposal.md`）
- `step.risks`（如 steps.json 中有）
- `assumptions.md` 的相关约束

## 3. 调用方式

```bash
python scripts/magi_plan.py \
  --mode step_decide \
  --run_dir WORKSPACE/runs/<run_id> \
  --step_id step_001 \
  --proposal draft/step_001_proposal.md \
  --assumptions assumptions.md \
  --steps plan/steps.json \
  --out magi/step_001_vote.json
```

## 4. 输出格式

`magi/step_XXX_vote.json` 最少包含：
- `status`: "APPROVED" | "REJECTED"
- `votes`: { melchior, balthasar, casper } 各含 vote + reasons
- `required_changes`: REJECTED 时的必修改项
- `hazards`: 关键风险（域、等价变形条件、不可逆操作）
- `acceptance`: 进入工具验证的条件

## 5. 门控行为（MUST）

| status | 行为 |
|--------|------|
| REJECTED | 禁止进入验证。修改 proposal 重投（最多 2 次修订） |
| APPROVED | 把 hazards 写入草稿，在验证脚本中体现域条件 |

超过 2 次修订仍 REJECTED → 该 step 方案不收敛，生成 FAILURE_REPORT。

## 6. 会话隔离（No Context Bleeding）

- 三个子人格互不可见、不共享输出
- 只能看到当前 step 的 proposal + 必要依赖摘要 + assumptions
- 不得看到主线程长推理或未审计草稿

## 7. 落盘要求

每次调用写入 `magi/<step>_vote.json` 并记录 `logs/tool_calls.log`（命令、输入、输出、退出码）。
