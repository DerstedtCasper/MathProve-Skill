# MathProve

语言 / Language: [中文](README.md) | [English](README.en.md)

**MathProve** 是一个神经符号（Neuro-Symbolic）数学验证流水线。通过集成符号计算引擎（SymPy）与交互式定理证明器（Lean 4），为 LLM 的数学推理过程提供形式化验证与可追溯审计。  
项目聚焦于数学推导中的“幻觉”问题：将 Chain-of-Thought 映射为可执行代码或形式化命题，确保 `Solution.md` 中每一步都经过计算验证或逻辑检查。

## 核心特性
- **混合路由（Hybrid Routing）**：自动分析步骤属性；计算类任务交给 SymPy；证明类任务交给 Lean 4 + Mathlib。
- **严格门禁（Strict Gatekeeping）**：只有执行后通过的 step 才能进入最终解；失败步骤触发回滚或重试。
- **形式化审计（Formal Auditing）**：生成完整 `.lean` 文件并编译校验全局一致性，避免 `sorry` 或循环论证。
- **结构化输出**：输出包含符号定义、假设、验证状态的标准化 Markdown。
- **反污染与看门狗**：Lean 可在临时工作区执行，并提供无输出超时守护。

## 架构概览
MathProve 工作流包含以下阶段：
1. **Decomposition**：将自然语言问题拆解为原子化 `steps.json`。
2. **Routing & Execution**：
   - **CAS Track**：调用 Python/SymPy 执行代数、微积分与等式验证。
   - **ITP Track**：构造 Lean 4 命题，借助 Mathlib tactics 完成证明。
3. **Verification**：逐步验证返回状态、输出与期望结果。
4. **Synthesis**：聚合通过的步骤，生成最终报告（`draft.md` → `Solution.md`）。

## 环境依赖
- Python 3.8+
- Lean 4 + Lake（用于形式化验证；可在 PATH 中调用或显式提供路径）
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
  -Target "D:\AI bot\MathProve\skill"
```

## 快速开始

### 1) 环境自检（建议）
运行复杂证明前，先确认 Lean 4 工程路径可用且 Mathlib 已编译：
```bash
python scripts/check_env.py --project "<path-to-lean-project>" --verify-mathlib
```

### 2) 标准流程（CLI）
步骤 A：路由与单步验证
```bash
python scripts/step_router.py \
  --input "steps.json" \
  --output "steps.routed.json" \
  --explain
```

参数说明：
- `--explain`：日志中输出路由决策理由（SymPy vs Lean）

步骤 B：全局审计与生成
```bash
python scripts/final_audit.py \
  --steps "steps.routed.json" \
  --solution "Solution.md" \
  --lean-cwd "<path-to-lean-project>" \
  --lean-gate
```

参数说明：
- `--lean-gate`：启用严格模式，生成 `reverse_gate.lean` 并编译整条证明链
- `--lean-ephemeral`：Lean 在临时工作区执行
- `--lean-watchdog-timeout`：Lean 文件模式无输出超时（秒）

### 临时工作区与看门狗
```bash
python scripts/final_audit.py \
  --steps "steps.routed.json" \
  --solution "Solution.md" \
  --lean-cwd "<path-to-lean-project>" \
  --lean-ephemeral \
  --lean-watchdog-timeout 20
```

## 输入数据格式示例
`steps.json` 结构以 `assets/step_schema.json` 为准（仓库内路径为 `skill/assets/step_schema.json`；挂载/安装为 Skill 后路径为 `assets/step_schema.json`）。以下示例包含 SymPy 步骤与 Lean4 步骤：
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

### config.yaml（可选）
`skill/config.yaml`（挂载/安装为 Skill 后路径为 `config.yaml`）用于集中记录推荐的路径/超时/开关；当前 Python 脚本**不会自动读取**它。你可以按需把其中字段映射到 CLI 参数，例如：
- `timeouts.sympy_seconds` → `final_audit.py --timeout` / `verify_sympy.py --timeout`
- `timeouts.lean_seconds` → `final_audit.py --lean-timeout`
- `timeouts.watchdog_no_output_seconds` → `final_audit.py --lean-watchdog-timeout`
- `timeouts.reverse_gate_seconds` → `final_audit.py --lean-gate-timeout`

### 路径覆盖（多环境/多版本）
- SymPy 执行解释器：`final_audit.py --python` 或 `--sympy-python`
- Lean4 客户端解释器：`final_audit.py --lean-python`
- Lean/Lake 可执行路径：`step.checker.lean_path` / `step.checker.lake_path` 或 `lean_repl_client.py --lean-path/--lake-path`

### Lean Reverse Gate（反向验证）
为避免“语法正确但逻辑无效”的证明（如滥用 `axiom`、`constant`、`sorry`），启用 reverse gate：
- 生成 `reverse_gate.lean`，聚合全部 Lean step
- Lint：禁止 `sorry/admit/axiom/constant/opaque`
- 在 Lake 工程内执行 `lake env lean reverse_gate.lean`

Windows 示例：
```powershell
pwsh -File scripts/check_reverse_lean4.ps1 `
  -Path "reverse_gate.lean" `
  -ProjectDir "<path-to-lean-project>" `
  -RequireMathlib `
  -RequireStepMap
```

### Subagent 并行化
针对长证明链，启用任务拆分并生成可分发任务包：
```bash
export MATHPROVE_SUBAGENT="1"
python scripts/subagent_tasks.py --steps steps.routed.json --out-dir ./tasks
```

### Ephemeral Workspace & Watchdog
Lean 在临时工作区运行，并提供无输出超时守护：
```bash
python scripts/final_audit.py \
  --steps "steps.routed.json" \
  --solution "Solution.md" \
  --lean-cwd "<path-to-lean-project>" \
  --lean-ephemeral \
  --lean-watchdog-timeout 20
```

## 目录结构
- `skill/`：可安装的 Skill 根目录（建议把该目录挂载到 Codex skills）
  - `SKILL.md`：Skill 入口与总览
  - `assets/`：schema 与模板（`assets/step_schema.json`、`assets/templates/`）
  - `references/`：参考资料
  - `agent.md`：参考用 agent 提示词/协议模板（不被脚本自动加载）
  - `config.yaml`：可选配置参考（当前脚本不自动读取；用于集中记录路径/超时/开关，按需映射到 CLI 参数）
  - `runtime/`：运行时工具（sympy/tactic/citation/workspace/watchdog）
  - `scripts/`：Skill 内脚本入口（标准形态）
- `runtime/`：兼容 shim（保留 `import runtime.*` 导入路径；实际实现位于 `skill/runtime/`）
- `scripts/`：兼容入口（保留 `python scripts/<name>.py` 与 `import scripts.<name>`；实际实现位于 `skill/scripts/`）
  - `ci_smoke.py`：CI/本地 smoke gate
  - `step_router.py`：步骤路由（SymPy vs Lean4）
  - `final_audit.py`：最终审计与 `Solution.md` 生成
  - `check_reverse_lean4.ps1`：reverse gate（lint + 编译）
- `tests/`：单元测试

## License
MIT License
