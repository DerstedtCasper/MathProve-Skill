# MathProve Skill

一个“分步拆解 + 路由 + 严格复核”的数学证明组合 skill：把一个问题拆成可验证的 step，并在 SymPy（快速符号/代数校验）与 Lean4+Mathlib（形式化证明校验）之间灵活切换；每步通过后写入 `draft.md`；最终对全量步骤做一致性复核并产出 `Solution.md`（可选启用 Lean4 reverse gate）。

---

## 一句话用法（自然语言驱动）

你可以直接用自然语言把任务交给 Agent（无需先写 steps）：

示例 A（纯计算，SymPy 为主）：
```text
使用 MathProve 处理这个问题：
- 问题：计算并化简 (x+1)^2 - (x^2+2x+1)
- 输出：必须生成 Solution.md，并在 draft.md 记录每一步的符号定义与证据
```

示例 B（证明为主，Lean4 为主）：
```text
使用 MathProve 处理这个问题：
- 问题：证明对任意自然数 n，有 n + 0 = n
- Lean 工程：D:\MATH Studio\math_studio
- 输出：必须启用 lean-gate，生成 reverse_gate.lean 并通过后再写 Solution.md
```

示例 C（混合 + 子代理并行细化）：
```text
使用 MathProve 处理这个问题：
- 问题：证明并验证：对任意实数 x，有 (x+1)^2 = x^2 + 2x + 1
- Lean 工程：D:\MATH Studio\math_studio
- 启用 subagent：是（主代理拆步与汇总；子代理负责每步讲解/引理检索/Lean 骨架/SymPy 校验片段）
- 输出：draft.md 必须包含符号表、假设台账、以及每步讲解版解释（便于讲座/答辩）
```

说明：自然语言模式下，Agent 会按 `SKILL.md` 的工作链路自动生成 `steps.json` 并执行验证闭环。

---

## 配置与环境

### SymPy（Python）
- 依赖：`sympy`
- 可指定 Python：
  - 单步：在 step 的 `checker.python` 填路径
  - 最终复核：`final_audit.py --python / --sympy-python`

### Lean4 + Mathlib（推荐 Lake 工程）
- 强烈建议在“带 Mathlib 的 Lake 工程目录”中运行（例如：`D:\MATH Studio\math_studio`）
- 环境探测（推荐）：
```powershell
python scripts/check_env.py --project "D:\MATH Studio\math_studio" --verify-mathlib
```

### 超时与重试
- SymPy 默认超时：`final_audit.py --timeout <秒>`
- Lean4 默认超时：`final_audit.py --lean-timeout <秒>`
- 单步覆盖：`step.checker.timeout`
- 重试：`step.checker.retries`

### Subagent（多代理并行）开关
- 保守探测 + 显式启用：
  - `MATHPROVE_SUBAGENT=1`
  - 可选 `MATHPROVE_SUBAGENT_DRIVER=<你的 IDE/CLI 分发命令>`
- 任务包生成（用于并行分发或作为单代理自检清单）：
```powershell
python scripts/subagent_tasks.py --steps steps.routed.json --out-dir subagent_tasks --emit-md
```

---

## Skill 工作链路（从问题到正式稿）

1) Problem Lock（锁定问题与成功标准）
- 产物：`draft.md` 的 Problem Lock / Notation / Assumptions 区块（模板来自 `assets/templates/`）

2) 生成 steps（一步一证据）
- 产物：`steps.json`（结构见 `assets/step_schema.json`；**step id 建议 S1/S2/...**）

3) 路由与难度评估
- `scripts/problem_router.py`：问题级路线（sympy/lean4/hybrid）+ 执行策略（single_agent/subagent）
- `scripts/step_router.py`：逐步难度（easy/medium/hard）+ 推荐路线

4) 逐步校验 + 写草稿（必须先通过再记录）
- SymPy：`scripts/verify_sympy.py`
- Lean4：`scripts/lean_repl_client.py`（repl/file/auto 回退）
- 通过后：`scripts/draft_logger.py` 追加到 `draft.md`（含符号/假设/讲解/证据指针）

5) 最终复核 + 生成正式稿
- `scripts/final_audit.py`：逐步回放校验；全部通过后生成 `Solution.md`
- 可选但强烈推荐：`--lean-gate`
  - 自动生成 `reverse_gate.lean`
  - `scripts/lint_reverse_lean4.py` 禁止 `sorry/admit/axiom/constant/opaque`，要求 step map
  - 在 `--lean-cwd` 指定的 Lake+Mathlib 工程中执行 `lake env lean reverse_gate.lean`

---

## 快速开始（手动 CLI 方式）

### 1) 环境检查
```powershell
python scripts/check_env.py --project "D:\MATH Studio\math_studio" --verify-mathlib
```

### 2) 步骤路由
```powershell
python scripts/step_router.py --input "steps.json" --output "steps.routed.json" --explain
```

### 3) 最终复核（推荐启用 reverse gate）
```powershell
python scripts/final_audit.py --steps "steps.routed.json" --solution "Solution.md" --lean-cwd "D:\MATH Studio\math_studio" --lean-gate --lean-timeout 120
```

---

## 仓库结构

- `SKILL.md`：主指南（面向 Agent）
- `scripts/`：执行脚本（SymPy/Lean4/reverse gate/subagent/final audit）
- `assets/`：模板与 schema（讲解友好）
- `references/`：策略与示例（含联网启发示例）

## 贡献

见 `CONTRIBUTING.md`。
