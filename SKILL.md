---
name: mathprove
description: 组合式数学推导与证明技能。适用于需要分步拆解、难度评估、在 SymPy 与 Lean4+Mathlib 间灵活切换、逐步验证并生成可审计草稿与正式稿的数学问题；可选启用 subagent 路由进行并行化解释/引理检索/证明骨架构建。
---

# MathProve（分步验证 + 路由 + 子代理 + 严格复核）

## 目标
把数学问题拆成最小可验证步骤（step），对每一步进行难度评估并选择 SymPy 或 Lean4 路线；每一步通过后写入 `draft.md`；最终对所有步骤做一致性复核（可选启用 Lean4 reverse gate）并生成 `Solution.md`。

## 快速开始
1. 环境检查（推荐验证 Mathlib）：
   - `python scripts/check_env.py --project "D:\MATH Studio\math_studio" --verify-mathlib`
2. 生成步骤清单（JSON）：
   - 结构见 `assets/step_schema.json`
   - **step id 强烈推荐使用 `S1/S2/...`**（与 Lean theorem/lemma 名称对齐）
3. 问题级路由（含 subagent 建议）：
   - `python scripts/problem_router.py --text "<问题>"`
4. 步骤级路由（难度与路线建议）：
   - `python scripts/step_router.py --input steps.json --output steps.routed.json --explain`
5. （可选）生成子代理任务包（并行解释/引理检索/证明骨架）：
   - `python scripts/subagent_tasks.py --steps steps.routed.json --out-dir subagent_tasks --emit-md`
6. 每步验证通过后写入草稿：
   - `python scripts/draft_logger.py --draft draft.md --step-file one_step.json`
7. 最终复核并生成正式稿（可选启用 Lean4 reverse gate）：
   - `python scripts/final_audit.py --steps steps.routed.json --solution Solution.md --lean-cwd "D:\MATH Studio\math_studio" --lean-gate`

## 核心流程（必须遵守）
1. Problem Lock（问题锁定）
   - 在推导前写清：目标结论、变量域/类型、允许使用的已知结果、成功标准。
2. Notation + Assumptions（符号与假设）
   - 先写 `符号表/假设台账`（模板见 `assets/templates/notation_table.md`、`assets/templates/assumption_ledger.md`）。
3. Step 拆解
   - 每个 step 只做一个可校验的“子目标”。
4. 难度评估与路线选择
   - `easy` 且可符号化：优先 SymPy。
   - `medium/hard` 或需要形式化保证：Lean4+Mathlib。
   - 思路不清晰/开放性：允许联网启发（只取灵感），再用 Lean4 反推验证。
5. 工具校验（必须通过才可写入草稿）
   - SymPy：`scripts/verify_sympy.py`
   - Lean4：`scripts/lean_repl_client.py`（优先 repl；无 repl 时用 file/auto）
6. 草稿记录（演讲友好）
   - 每步写入 `draft.md` 时，必须补齐：符号/假设/讲解版解释（否则答辩/讲座容易被打断）。
7. 最终复核（禁止口头保证）
   - `scripts/final_audit.py` 会逐步回放校验结果，全部通过才生成 `Solution.md`。

## Step 数据契约（强约束，提升可校验性）
- step id：推荐 `S1/S2/...`（用于映射 Lean theorem/lemma 名称）。
- 对于 `checker.type = sympy`：
  - 使用 `checker.code` 或 `checker.code_file`，并写清 `symbols/assumptions/explanation`。
- 对于 `checker.type = lean4`：
  - 使用 `checker.cmds`（或 `checker.code` 作为逐行片段）。
  - **必须包含 `theorem/lemma Sx ... := by ...`，且 x 与 step id 一致。**

## Subagent 路由（可选，推荐用于难题/长证明）
适用：步骤较多、需要大量讲解、需要检索 Mathlib 引理、或 Lean4 证明较难时。

角色分工建议：
- 主 agent：拆步、确定目标与依赖、汇总回填 steps.json/draft/Solution。
- 子代理：逐 step 输出
  - 讲解版解释（符号定义/关键不变量/逻辑跳跃）
  - Mathlib lemma 候选与使用方式（可直接 apply/have）
  - SymPy 验证片段（最小可运行 + 期望结果）
  - Lean4 证明骨架（避免 sorry/admit）

启用方式（保守探测 + 显式开关）：
- 显式：设置 `MATHPROVE_SUBAGENT=1`（可选 `MATHPROVE_SUBAGENT_DRIVER`）
- 生成任务包：`scripts/subagent_tasks.py`

如果运行环境不支持 subagent：任务包仍可当作“自检清单”顺序执行（流程不变）。

## Lean4 reverse gate（强烈推荐）
用途：把 Lean4 证明从“单步运行 OK”升级为“统一严格门禁”：
- 自动生成 `reverse_gate.lean`
- 运行 lint：禁止 `sorry/admit/axiom/constant/opaque`，要求 step map
- 用 `lake env lean` 编译通过（默认要求 Mathlib/Lake 工程；除非显式 `--lean-gate-no-mathlib`）

入口：
- `python scripts/final_audit.py ... --lean-gate`
- 也可手动：`scripts/check_reverse_lean4.ps1 -Path <lean> -ProjectDir <lake-root> -RequireMathlib -RequireStepMap`

## 联网启发记录
联网检索只用于启发思路；任何外部信息必须记录来源摘要并再回证：
- 记录脚本：`scripts/web_inspiration.py`
- 示例：`references/web-inspiration-example.md`

## 模板化流程（讲解友好）
`assets/templates/` 提供可复用结构，建议在草稿/正式稿中保持一致：
- `draft_template.md` / `solution_template.md` / `audit_template.md`
- `notation_table.md` / `assumption_ledger.md`
- `claim_list.md` / `claim_evidence_matrix.md`
- （可选深度）`baseline_evidence.md` / `competing_models.md` / `red_team_review.md` / `validation_plan.md` / `sympy_checklist.md`

## 错误处理（必须执行）
- SymPy/Lean4 单步失败：先分析错误原因，再有限重试（不超过 3 次）。
- 若仍失败：将 step 标记为失败，停止进入最终复核（不得生成正式稿）。
- 禁止在未验证通过的情况下写入草稿或生成正式稿。

## 资源与参考
**脚本**
- `scripts/verify_sympy.py`：执行 SymPy 校验
- `scripts/lean_repl_client.py`：Lean4（repl/file/auto）执行
- `scripts/final_audit.py`：最终复核 + 生成 `Solution.md`
- `scripts/lint_reverse_lean4.py`：Lean4 reverse gate lint
- `scripts/check_reverse_lean4.ps1`：Lean4 reverse gate（lint + 编译）
- `scripts/subagent_tasks.py`：生成子代理任务包

**关键资源**
- `assets/step_schema.json`
- `assets/lean/reverse_template_mathlib.lean`

