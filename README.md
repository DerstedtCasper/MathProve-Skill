# MathProve

**MathProve** 是一个神经符号（Neuro-Symbolic）数学验证流水线。通过集成符号计算引擎（SymPy）与交互式定理证明器（Lean 4），为大语言模型（LLM）的数学推理过程提供形式化验证与可追溯审计。

本项目聚焦于 LLM 在数学推导中的“幻觉”现象：将 Chain-of-Thought (CoT) 映射为可执行代码或形式化命题，确保最终生成的 `Solution.md` 中每一步都经过计算验证或逻辑检查。

## 核心特性

- **混合求解路由 (Hybrid Routing)**：自动分析推理步骤属性；计算类任务分发至 SymPy；逻辑证明类任务分发至 Lean 4 + Mathlib。
- **严格门禁机制 (Strict Gatekeeping)**：仅通过执行引擎校验的步骤（Step）可合并至最终解；失败步骤触发回滚或重试。
- **形式化审计 (Formal Auditing)**：支持生成完整 `.lean` 源文件并调用编译器进行全局一致性检查，杜绝滥用 `sorry` 或循环论证。
- **结构化输出**：生成包含符号定义、假设前提及验证状态的标准化 Markdown 文档。

## 架构概览

MathProve 的工作流包含以下阶段：

1. **Decomposition**：将自然语言问题拆解为原子化 `steps.json`。
2. **Routing & Execution**：
   - **CAS Track**：调用 Python/SymPy 进行代数运算、微积分求解等计算验证。
   - **ITP Track**：构造 Lean 4 命题，利用 Mathlib 策略库（tactics）完成证明。
3. **Verification**：验证每一步的返回状态、标准输出与期望结果。
4. **Synthesis**：聚合所有通过的步骤，生成最终报告（`draft.md` → `Solution.md`）。

## 环境依赖

- Python 3.8+
- Lean 4 + Lake（用于形式化验证；需可在 PATH 中调用，或显式提供可执行路径）
- Python 依赖：

```bash
python -m pip install -r requirements-dev.txt
```

## 安装

### 作为独立 CLI 工具使用

```bash
git clone https://github.com/DerstedtCasper/MathProve-Skill.git MathProve
cd MathProve
```

### 集成到 Agent/Codex（可选）

建议以软链接/目录联接方式挂载到 Codex skills 目录（Windows 默认 `%USERPROFILE%\.codex\skills\`）：

```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.codex\skills\MathProve" `
  -Target "D:\AI bot\MathProve"
```

## 快速开始

### 1) 环境自检（推荐）

在运行复杂证明前，确保 Lean 4 工程路径可用且 Mathlib 已编译：

```bash
python scripts/check_env.py --project "<path-to-lean-project>" --verify-mathlib
```

### 2) 标准工作流（CLI）

步骤 A：路由与单步验证

```bash
python scripts/step_router.py \
  --input "steps.json" \
  --output "steps.routed.json" \
  --explain
```

参数说明：

- `--explain`：在日志中输出路由决策理由（SymPy vs Lean）

步骤 B：全局审计与生成

```bash
python scripts/final_audit.py \
  --steps "steps.routed.json" \
  --solution "Solution.md" \
  --lean-cwd "<path-to-lean-project>" \
  --lean-gate
```

参数说明：

- `--lean-gate`：启用严格模式，生成 `reverse_gate.lean` 并调用 Lean 编译器验证整条推导链

## 输入数据格式示例

`steps.json` 的结构以 `assets/step_schema.json` 为准。以下示例展示常见的 SymPy 步骤与 Lean4 步骤：

```json
{
  "problem": "证明并验证：对任意实数 x，有 (x+1)^2 = x^2 + 2x + 1",
  "steps": [
    {
      "id": "S1",
      "goal": "展开 (x + 1)^2",
      "checker": {
        "type": "sympy",
        "code": "import sympy as sp\nx = sp.Symbol('x')\nexpr = (x + 1)**2\nassert sp.expand(expr) == x**2 + 2*x + 1\nprint('ok')"
      }
    },
    {
      "id": "S2",
      "goal": "形式化：Nat 加法右单位元",
      "checker": {
        "type": "lean4",
        "cmds": [
          "import Mathlib",
          "theorem S2 (n : Nat) : n + 0 = n := by simp"
        ]
      }
    }
  ]
}
```

## 高级配置

### Lean Reverse Gate（反向验证）

为防止生成“语法正确但逻辑无效”的证明（例如滥用 `axiom`、`constant` 或 `sorry`），可启用 reverse gate 进行全局门禁：

- 生成 `reverse_gate.lean` 并聚合所有 Lean step
- lint：禁止 `sorry/admit/axiom/constant/opaque` 等捷径
- 在 Lake 工程中执行 `lake env lean reverse_gate.lean` 进行编译级校验

Windows 下可直接运行：

```powershell
pwsh -File scripts/check_reverse_lean4.ps1 `
  -Path "reverse_gate.lean" `
  -ProjectDir "<path-to-lean-project>" `
  -RequireMathlib `
  -RequireStepMap
```

### Subagent 并行化

对长链推导任务，可通过环境变量开启子任务拆分模式，并生成可分发任务包：

```bash
export MATHPROVE_SUBAGENT="1"
python scripts/subagent_tasks.py --steps steps.routed.json --out-dir ./tasks
```

## 目录结构

- `scripts/`：核心逻辑脚本
  - `step_router.py`：步骤分发器（SymPy vs Lean4）
  - `final_audit.py`：最终审计与 `Solution.md` 生成
  - `check_reverse_lean4.ps1`：reverse gate（lint + 编译）
- `assets/`：schema 与模板（含 `assets/step_schema.json`、`assets/templates/`）
- `tests/`：单元测试

## License

MIT License

