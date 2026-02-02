# MathProve Skill

把数学推导变成“可验、可追溯、可讲解”的产品级流程。

MathProve 的核心想法很简单：**别让证明靠“感觉”成立**。把一个问题拆成小 step——能用 SymPy 快速算清楚的就算；需要严谨证明的就丢给 Lean4 + Mathlib 过门禁；每一步都把证据写进草稿，最后生成一份能经得起追问的 `Solution.md`。

## 你会用它来干嘛

- 把“推导一大坨”拆成可验证的 `S1/S2/...` step（每步一个小目标）
- 简单步骤用 SymPy 快速验算；关键步骤用 Lean4 + Mathlib 形式化验真
- 每一步都强制补齐：符号定义、假设、为什么成立（讲座/答辩不怕被追问）
- 最终生成：
  - `draft.md`：过程草稿（可审计、可讲解）
  - `Solution.md`：最终正式稿（只在全步通过后产出）

## 一分钟理解工作链路

1. 你用自然语言描述问题（或者先写 `steps.json`）
2. 路由器评估每个 step 难度：该走 `sympy` 还是 `lean4`
3. 每步必须“工具验证通过”才允许写入 `draft.md`
4. 终局复核：把所有 step 串起来再跑一遍（可选开启 Lean4 reverse gate），通过后生成 `Solution.md`

## 自然语言用法示范（复制就能用）

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

## 部署 / 安装方式（你选一个）

### 方式 1：当作 Codex Skill 安装（推荐）

把仓库放进你的 Codex skills 目录（Windows 默认在 `%USERPROFILE%\.codex\skills\`）：

```powershell
# 例：用 junction 做到“本地开发 = 即时生效”
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\\.codex\\skills\\MathProve" `
  -Target "D:\\AI bot\\MathProve"
```

### 方式 2：当作独立工具仓库用（也很好）

不装 skill 也能跑：直接用 `python scripts/*.py` 走完整流程（见下方“快速开始”）。

## 快速开始（CLI / Windows）

### 1) 安装 Python 依赖（最少需要 SymPy）
```powershell
python -m pip install -r requirements-dev.txt
```

### 2)（可选但强烈推荐）验证 Lean4 + Mathlib
把 `--project` 指向你的 Lake + Mathlib 工程目录（例如：`D:\MATH Studio\math_studio`）：
```powershell
python scripts/check_env.py --project "D:\MATH Studio\math_studio" --verify-mathlib
```

### 3) 路由 steps + 最终复核（推荐开门禁）
```powershell
python scripts/step_router.py --input "steps.json" --output "steps.routed.json" --explain
python scripts/final_audit.py --steps "steps.routed.json" --solution "Solution.md" --lean-cwd "D:\MATH Studio\math_studio" --lean-gate --lean-timeout 120
```

## 可选增强：子代理（subagent）并行拆活

适合：步骤很多、需要大量讲解、需要检索 Mathlib 引理、或者 Lean4 证明卡住的情况。

```powershell
$env:MATHPROVE_SUBAGENT = "1"
python scripts/subagent_tasks.py --steps steps.routed.json --out-dir subagent_tasks --emit-md
```

你可以把 `subagent_tasks/` 里的任务分发给 IDE/CLI 的 subagent 能力；如果环境不支持，也可以把它当“自检清单”逐项做完。

## 可选增强：Lean4 reverse gate（强烈推荐）

一句话：**把“看起来证明了”升级成“编译器也认账”**。

启用 `--lean-gate` 后会自动：
- 生成 `reverse_gate.lean`
- lint：禁止 `sorry/admit/axiom/constant/opaque` 等捷径
- 在你的 Lake 工程里跑 `lake env lean reverse_gate.lean`

（Windows 可直接用）：
```powershell
pwsh -File scripts/check_reverse_lean4.ps1 -Path reverse_gate.lean -ProjectDir "D:\MATH Studio\math_studio" -RequireMathlib -RequireStepMap
```

## 更多文档

- 更完整的中文说明：`README.zh-CN.md`
- Full English guide: `README.en.md`
- Agent 执行规则与脚本入口：`SKILL.md`

<details>
<summary>English</summary>

Turn math into a **step-by-step, tool-checked, talk-ready** workflow.

MathProve has one simple rule: **don’t let proofs run on vibes**. Break the problem into small steps. If a step is “just algebra”, SymPy checks it fast. If a step needs real rigor, Lean4 + Mathlib verifies it. Every passed step leaves an audit trail in the draft, and the final output is a `Solution.md` that can survive questions.

Quickstart (Windows / CLI):
```powershell
python -m pip install -r requirements-dev.txt
python scripts/check_env.py --project "D:\MATH Studio\math_studio" --verify-mathlib
python scripts/step_router.py --input steps.json --output steps.routed.json --explain
python scripts/final_audit.py --steps steps.routed.json --solution Solution.md --lean-cwd "D:\MATH Studio\math_studio" --lean-gate --lean-timeout 120
```
</details>
