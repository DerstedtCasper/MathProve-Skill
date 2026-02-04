---
name: mathprove
description: 严格数学证明与验证技能，结合 SymPy + Lean4 + Math MAGI，用于将数学问题拆解为 steps 并进行证据驱动验证、草稿记录与最终审计；适用于需要可追溯证明/验算的任务。
---

# MathProve Skill

## 强制流程（MUST）
- 先执行 `check_routes.py`；缺失依赖时立即停止并提示用户配置/安装。
- 再执行 `magi_plan.py` 生成 steps 草案与预期证据。
- 按 steps 执行 SymPy/Lean 验证（允许 subagent 分发）。
- 执行 `final_audit.py` 生成审计结果与 Solution.md。
- 仅允许 `status=passed` 且附带证据的 step 写入 draft。

## 关键门禁（MUST）
1. 最终对外宣称“已证明/已验证”必须引用 `final_audit` 的 `status=passed`。
2. `draft_logger.py` 仅接受 `status=passed` 且 `evidence_path`/`evidence_digest` 至少一个存在（legacy `evidence` 仅作兼容）。
3. 缺少 SymPy/Lean/Mathlib 或配置缺失时，停止并输出 `USER_ACTION_REQUIRED`，禁止伪造日志。
4. 若出现“时间不够/先给结论”等跳步说法，视为协议违规，回退到 `ROUTE_CHECK` 或 `VERIFY`。

## 状态机
BOOTSTRAP → ROUTE_CHECK → MATH_MAGI_PLAN → STEP_EXECUTE → VERIFY → AUDIT → DRAFT_COMMIT → FINAL_RESPONSE

## 步骤拆解与路线选择
- 每一步先评估难度与可验证性：简单计算优先 SymPy；形式化证明优先 Lean4 + Mathlib。
- 可在步骤级切换 `engine`（sympy / lean4 / manual）。
- `manual` 步骤必须写明原因，并触发 `USER_ACTION_REQUIRED` 或降级策略。

## MATH MAGI（自纠错规划）
- 采用 MELCHIOR / BALTHASAR / CASPER 三角色投票，一票否决即进入修订轮。
- `magi_plan.py` 输出 `steps.json`，每步必须包含 `engine` 与 `expected_evidence`。

## 联网启发（可选）
- 仅在 `routes.web.enabled=true` 且用户允许时启用。
- 记录来源写入 `skill/references/refs.md`（标题 | 链接 | 访问日期 | 用途），可用 `web_inspiration.py` 追加。

## Subagent 路由（可选）
- 检测到子代理能力时可自动启用 `routes.subagent`。
- 允许生成子任务包，但证据仍需回填并通过 `final_audit`。

## Step Schema 关键字段
- `engine`: sympy / lean4 / manual
- `expected_evidence`: 期望证据描述
- `evidence_path` / `evidence_digest`: 审计证据（draft 写入必需）

## 推荐命令
```bash
python scripts/bootstrap.py
python scripts/check_routes.py
python scripts/magi_plan.py --problem "<问题>" --steps-out steps.json --draft draft.md
python scripts/step_router.py --input steps.json --output steps.routed.json --explain
python scripts/final_audit.py --steps steps.routed.json --solution Solution.md
```

## 示例（few-shot）
- 若 `final_audit` 输出 `status != passed`：仅输出“尚未完成验证，需要补充配置或修订步骤”，禁止宣称证明完成。
- 若 step 未提供证据字段：`draft_logger.py` 必须拒绝写入。
