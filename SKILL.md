---
name: mathprove
description: 组合式数学推导与证明技能。适用于需要拆步评估、SymPy/Lean4 路线切换、逐步校验并生成草稿与正式稿的数学问题；可选启用 subagent 路由进行并行化解释与校验。
---

# MathProve

## 目标
将数学问题拆解为最小可验证步骤（step），对每一步进行难度评估并选择 SymPy 或 Lean4 路线；校验通过后写入 `draft.md`；最终执行全量复核并生成 `Solution.md`。

## SkillMP 结构
- `SKILL.md`：技能入口与总览
- `agent.md`：XML 结构化协议（Supervisor/Prover/Verifier）
- `config.yaml`：路径/超时/开关
- `runtime/`：运行时工具（sympy/tactic/citation/workspace/watchdog）
- `scripts/`：兼容入口与执行脚本

## 快速开始
1. 环境检查（建议验证 Mathlib）  
   `python scripts/check_env.py --project "D:\MATH Studio\math_studio" --verify-mathlib`
2. 问题级路由（含 subagent 建议）  
   `python scripts/problem_router.py --text "<问题>"`
3. 步骤级路由  
   `python scripts/step_router.py --input steps.json --output steps.routed.json --explain`
4. （可选）生成子代理任务包  
   `python scripts/subagent_tasks.py --steps steps.routed.json --out-dir subagent_tasks --emit-md`
5. 草稿记录（逐步通过后写入）  
   `python scripts/draft_logger.py --draft draft.md --step-file one_step.json`
6. 最终复核与生成（可选 reverse gate）  
   `python scripts/final_audit.py --steps steps.routed.json --solution Solution.md --lean-cwd "D:\MATH Studio\math_studio" --lean-gate`
   - 可选：`--lean-ephemeral` 启用临时工作区，`--lean-watchdog-timeout` 启用无输出超时

## 核心流程（必须遵守）
1. Problem Lock：明确目标结论、变量域/类型、允许使用的已知结论、成功标准
2. Notation + Assumptions：填写符号表与假设台账（模板见 `assets/templates/`）
3. Step 拆解：每步仅包含一个可校验子目标
4. 难度评估与路由：`easy` 优先 SymPy；`medium/hard` 走 Lean4
5. 工具校验：未通过不得进入草稿
6. 草稿记录：每步补齐符号/假设/讲解版解释
7. 最终复核：`final_audit.py` 全量通过后生成 `Solution.md`

## Step 数据契约（强约束）
- step id：推荐 `S1/S2/...`，与 Lean theorem/lemma 名称对齐
- `checker.type = sympy`：
  - 使用 `checker.code` 或 `checker.code_file`
  - 必须补齐 `symbols/assumptions/explanation`
- `checker.type = lean4`：
  - 使用 `checker.cmds` 或 `checker.code`
  - 必须包含 `theorem/lemma Sx ... := by ...`，且 x 与 step id 一致

## 路径覆盖（多环境/多版本）
- SymPy 执行解释器：`final_audit.py --python` 或 `--sympy-python`
- Lean4 客户端解释器：`final_audit.py --lean-python`
- Lean/Lake 可执行路径：`step.checker.lean_path` / `step.checker.lake_path` 或 `lean_repl_client.py --lean-path/--lake-path`

## Subagent 路由（可选，建议用于难题/长链条）
适用：步骤较多、需要大量解释、需要检索 Mathlib 引理、Lean4 证明较难的场景。

分工建议：
- 主代理：拆步、确定目标与依赖、汇总回填 steps/draft/Solution
- 子代理：讲解版解释、引理检索、SymPy 片段、Lean4 证明骨架

启用方式：
- 显式：`MATHPROVE_SUBAGENT=1`（可选 `MATHPROVE_SUBAGENT_DRIVER`）
- 生成任务包：`scripts/subagent_tasks.py`

## Lean4 reverse gate（强烈推荐）
用途：将 Lean4 单步验证升级为统一门禁。

功能：
- 生成 `reverse_gate.lean`
- Lint：禁止 `sorry/admit/axiom/constant/opaque`
- `lake env lean reverse_gate.lean` 编译校验

入口：
- `python scripts/final_audit.py ... --lean-gate`
- 手动：`scripts/check_reverse_lean4.ps1 -Path <lean> -ProjectDir <lake-root> -RequireMathlib -RequireStepMap`

## 联网启发记录
仅用于启发思路；任何外部信息必须记录来源并回证。
- 记录脚本：`scripts/web_inspiration.py`
- 示例：`references/web-inspiration-example.md`

## 模板化流程（讲解友好）
`assets/templates/` 提供可复用结构：
- `draft_template.md` / `solution_template.md` / `audit_template.md`
- `notation_table.md` / `assumption_ledger.md`
- `claim_list.md` / `claim_evidence_matrix.md`
- `baseline_evidence.md` / `competing_models.md` / `red_team_review.md` / `validation_plan.md` / `sympy_checklist.md`

## 错误处理（必须执行）
- SymPy/Lean4 单步失败：先分析原因，最多重试 3 次
- 仍失败：标记 step 为 failed，停止进入最终复核
- 未通过不得写入草稿或生成正式稿

## 资源与脚本
**脚本**
- `scripts/verify_sympy.py`：执行 SymPy 校验
- `scripts/lean_repl_client.py`：Lean4（repl/file/auto）执行
- `scripts/final_audit.py`：最终复核 + 生成 `Solution.md`
- `scripts/lint_reverse_lean4.py`：reverse gate lint
- `scripts/check_reverse_lean4.ps1`：reverse gate（lint + 编译）
- `scripts/problem_router.py`：问题级路由（含 subagent 建议）
- `scripts/subagent_tasks.py`：生成子代理任务包

**关键资源**
- `assets/step_schema.json`
- `assets/lean/reverse_template_mathlib.lean`
