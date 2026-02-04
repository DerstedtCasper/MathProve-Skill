# MathProve

语言 / Language: [中文](README.md) | [English](README.en.md)

MathProve 是一个神经符号数学验证流水线，集成 SymPy 与 Lean4，为数学推理提供可审计的证据链。目标是把自然语言推导映射为可执行步骤，并将验证结果汇总为 `Solution.md`。

## 核心特性
- **混合路由**：按步骤难度在 SymPy/Lean4 间切换，支持手工覆盖。
- **MATH MAGI 规划**：三角色投票 + 一票否决，生成结构化 `steps.json`。
- **严格门禁**：仅 `status=passed` 且附带证据的 step 可写入 `draft.md`。
- **审计闭环**：`final_audit.py` 统一产出审计结果与 `Solution.md`。
- **可审计日志**：JSONL + Markdown 摘要，便于追踪。
- **可选路由**：subagent 分发与联网启发记录（refs.md）。

## 安装

### 作为独立 CLI 工具使用
```bash
git clone https://github.com/DerstedtCasper/MathProve-Skill.git MathProve
cd MathProve
```

### 挂载为 Codex/Agent Skill
建议挂载 `skill/` 目录，并保证目录名与 `SKILL.md` 中 `name: mathprove` 一致：
```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.codex\skills\mathprove" `
  -Target "D:\AI bot\MathProve\skill"
```

## 快速开始

### 1) Bootstrap（可选）
生成本地覆盖配置与 refs 模板：
```bash
python scripts/bootstrap.py
```

### 2) 路由检查（必需）
检查 SymPy/Lean4/Mathlib 是否可用：
```bash
python scripts/check_routes.py
```

### 3) MATH MAGI 规划（必需）
```bash
python scripts/magi_plan.py --problem "<问题文本>" --steps-out steps.json --draft draft.md
```

### 4) 步骤路由与执行（必需）
```bash
python scripts/step_router.py \
  --input "steps.json" \
  --output "steps.routed.json" \
  --explain
```

### 5) Final Audit（必需）
```bash
python scripts/final_audit.py \
  --steps "steps.routed.json" \
  --solution "Solution.md" \
  --lean-cwd "<path-to-lean-project>" \
  --lean-gate
```

### 6) 草稿写入（按需）
单步写入草稿示例：
```bash
python scripts/draft_logger.py --draft draft.md --step-file one_step.json
```

## 工作流状态机
BOOTSTRAP → ROUTE_CHECK → MATH_MAGI_PLAN → STEP_EXECUTE → VERIFY → AUDIT → DRAFT_COMMIT → FINAL_RESPONSE

## `steps.json` 示例
```json
{
  "problem": "证明并验证：对任意实数 x，有 (x+1)^2 = x^2 + 2x + 1",
  "steps": [
    {
      "id": "S1",
      "goal": "展开 (x + 1)^2",
      "engine": "sympy",
      "expected_evidence": "sympy output: simplify(...) == 0",
      "checker": {
        "type": "sympy",
        "code": "import sympy as sp\nx = sp.Symbol('x')\nexpr = (x + 1)**2\nassert sp.expand(expr) == x**2 + 2*x + 1\nprint('ok')"
      }
    },
    {
      "id": "S2",
      "goal": "形式化：Nat 加法右单位元",
      "engine": "lean4",
      "expected_evidence": "lean build success (no goals, no sorries)",
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

## 配置与路由

### config.yaml / config.local.yaml
- `skill/config.yaml`：默认配置。
- `skill/config.local.yaml`：本地覆盖（gitignored），由 `bootstrap.py` 生成模板。

### 路径覆盖
- SymPy 解释器：`final_audit.py --python` 或 `--sympy-python`
- Lean4 客户端：`final_audit.py --lean-python`
- Lean/Lake 可执行：`step.checker.lean_path` / `step.checker.lake_path`

### Subagent 路由
- `routes.subagent.auto_enable=true` 时可自动启用。
- 生成任务包：`python scripts/subagent_tasks.py --steps steps.routed.json --out-dir ./tasks`

## 联网启发示例
记录联网启发结果到 `skill/references/refs.md`：
```bash
python skill/scripts/web_inspiration.py \
  --query "mathlib lemma for ring simplification" \
  --sources-json "[{\"title\":\"Mathlib simp lemma\",\"url\":\"https://example.com\",\"summary\":\"用于简化环上等式\"}]" \
  --notes "用于确定可用引理"
```

## 目录结构
- `skill/`：可安装的 Skill 根目录（推荐挂载）
  - `SKILL.md`：Skill 入口与强制规则
  - `assets/`：schema 与模板
  - `references/`：外部来源记录
  - `config.yaml` / `config.local.yaml`
  - `runtime/`：运行时工具
  - `scripts/`：标准脚本入口
- `scripts/`：兼容入口（调用 `skill/scripts/`）
- `tests/`：单元测试

## License
MIT License
