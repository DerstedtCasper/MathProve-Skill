# MathProve Skill

把数学推导变成“可验、可追溯、可讲解”的产品级流程。

MathProve 的核心想法很简单：**别让模型靠“感觉”写证明**。把一个问题拆成小 step——能用 SymPy 快速算清楚的就算；需要严谨证明的就丢给 Lean4+Mathlib 过门禁；每一步都把证据写进草稿，最后再生成一份能经得起追问的正式稿。

---

## 你会得到什么

- **一步一证据**：每个 step 都要么 SymPy 验算通过，要么 Lean4 形式化通过。
- **讲解友好**：每步强制写清“符号/假设/为什么成立”，适合讲座、答辩、组会。
- **可审计闭环**：`draft.md`（草稿）→ `final_audit.py`（最终复核）→ `Solution.md`（正式稿）。
- **硬核反作弊（可选）**：Lean4 reverse gate 禁止 `sorry/admit/axiom/constant/opaque` 走捷径。
- **可并行（可选）**：支持 subagent 路由，把“讲解、引理检索、Lean 骨架、SymPy 校验”拆给多个助手。

---

## 自然语言上手（复制就能用）

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

---

## 3 分钟跑通（CLI）

### 1) 安装依赖（最少需要 SymPy）
```powershell
python -m pip install -r requirements-dev.txt
```

### 2) 检查 Lean4 + Mathlib（推荐）
把 `--project` 指向你的 Lake+Mathlib 工程目录（例如你本机是 `D:\MATH Studio\math_studio`）：
```powershell
python scripts/check_env.py --project "D:\MATH Studio\math_studio" --verify-mathlib
```

### 3) 路由与最终复核（推荐开门禁）
```powershell
python scripts/step_router.py --input "steps.json" --output "steps.routed.json" --explain
python scripts/final_audit.py --steps "steps.routed.json" --solution "Solution.md" --lean-cwd "D:\MATH Studio\math_studio" --lean-gate --lean-timeout 120
```

---

## 配置与开关（你最常用的那几个）

### 超时与重试
- SymPy 默认超时：`final_audit.py --timeout <秒>`
- Lean4 默认超时：`final_audit.py --lean-timeout <秒>`
- 单步覆盖：`step.checker.timeout`
- 重试：`step.checker.retries`

### Subagent（多代理并行）
- 显式启用：`MATHPROVE_SUBAGENT=1`
- 可选：`MATHPROVE_SUBAGENT_DRIVER=<你的 IDE/CLI 分发命令>`
- 生成任务包（并行分发 / 单代理自检清单都行）：
```powershell
python scripts/subagent_tasks.py --steps steps.routed.json --out-dir subagent_tasks --emit-md
```

### 路径覆盖（多环境/多 Python/多 Lean）
- SymPy：`final_audit.py --python / --sympy-python` 或在 step 里填 `checker.python`
- Lean4：在 step 里填 `checker.lean_path / checker.lake_path`，或用 `lean_repl_client.py --lean-path/--lake-path`

---

## Lean4 reverse gate 是啥（为什么值得开）

一句话：**把“看起来证明了”升级成“机器也认账”**。

启用 `--lean-gate` 后，会自动：
- 生成 `reverse_gate.lean`（把所有 Lean step 收拢成一个文件）
- 运行 lint（禁止 `sorry/admit/axiom/constant/opaque`，要求 step map）
- 在 `--lean-cwd` 指定的 Lake+Mathlib 工程里编译：`lake env lean reverse_gate.lean`

> Windows 下可直接用 `scripts/check_reverse_lean4.ps1`；其它系统可用 `scripts/lint_reverse_lean4.py` + `lake env lean` 手动跑同等校验。

---

## 仓库结构

- `SKILL.md`：给 Agent 的总指南（建议从这里开始读）
- `scripts/`：工具脚本（SymPy/Lean4/reverse gate/subagent/final audit）
- `assets/`：模板与 schema（讲解友好）
- `references/`：策略与示例（含联网启发示例）

## 贡献

想一起把它做得更“像科研基础设施”，欢迎来：
- 看 `CONTRIBUTING.md`
- 提 PR：更强的 Mathlib 引理检索策略、更稳的 gate、更好的讲解模板、更好的多代理分发格式等

