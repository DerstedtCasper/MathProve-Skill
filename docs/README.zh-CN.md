# MathProve-Skill

语言 / Language: [English](README.en.md) | **中文**

MathProve-Skill 是一个面向研究级数学形式化与证明工程的 Agent Skill。它将 Lean4、SymPy、阶段化 agent 编排、证据加权候选选择与最终审计门控结合起来，把非形式化数学推导推进为可恢复、可检查、可审计、部分可机器验证的证明工件。

本项目的目标不是生成流畅的证明文本，而是在长期研究任务中维持严格的证据纪律：先锁定定理陈述与假设，再分解为候选路线、lemma DAG、proof skeleton、line map、工具日志、候选包和最终审计结果。未经证据门控晋升的自然语言推断不被视为数学证明。

## 研究定位

MathProve 适用于以下工作：

- 从研究笔记、论文草稿或自然语言命题中抽取形式化定理陈述；
- 构造 theorem variants、lemma DAG、proof skeleton 与 line map；
- 对代数、分析、组合、表示论、braid/YBE、量子群与数学物理推导进行路线探索；
- 在显式假设下执行 SymPy 精确符号验证；
- 使用 Lean4/Mathlib 做可回放的形式化尝试与静态安全检查；
- 记录反例搜索、失败边界、环境阻塞与可复用 proof memory；
- 将长程证明活动拆成可交接的 context shards、candidate packs 和 handoff capsules。

MathProve 明确区分探索信号与证明证据。Agent 投票、启发式路线、类比和草稿可以引导搜索，但不能认证定理。可晋升结论必须绑定 kernel evidence、可回放符号计算、显式反例搜索或最终审计通过的证据包。

## Ultra v8 架构

v8 将早期的 MAGI + SymPy + Lean 工作流升级为长程 proof factory。

核心机制包括：

- **阶段门控**：problem lock、knowledge pack、notation gate、skeleton gate、line-map gate、lemma sprint、refutation、integration、final audit、proof-memory update。
- **证据加权晋升**：按 tool verification、dependency closure、refutation coverage、evidence completeness、maintainability、restartability、novelty、cost sanity 评分。
- **硬否决规则**：未定义符号、未声明定义域、定理陈述漂移、过期日志、缺失证据、非 skeleton `sorry`、Lean/SymPy 失败、以浮点计算冒充精确证明、未经审计的最终结论，均 fail closed。
- **Context lake**：长任务将上下文外部化为 index、shards、handoff capsules、candidate packs、logs 与 proof-memory events。
- **MoE 专家路由**：frontier/research/repeated-failure 模式会激活 formalizer、skeletonist、line mapper、librarian、tactic sprinter、algebraic verifier、refuter、repairer、integrator、auditor、domain expert 等角色。
- **禁止过早收束**：局部上下文耗尽不是终止条件。任务必须以 gate decision、counterexample、用户可见的 theorem repair 或可回放环境阻塞结束。

## 安装

```bash
git clone https://github.com/DerstedtCasper/MathProve-Skill.git MathProve-Skill
cd MathProve-Skill
python -m pip install -r requirements-dev.txt
```

挂载为 Codex/Agent Skill：

```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.codex\skills\mathprove" `
  -Target "D:\AI_studio\MathProve-Skill\skill"
```

Skill 元数据名为 `mathprove-skill`；若本地 agent 运行时采用 `mathprove` 作为挂载目录名，也可以保持该目录约定。

## 快速开始

### 1. 检查本地路由

```bash
python scripts/check_routes.py
```

### 2. 生成 MAGI 规划

```bash
python scripts/magi_plan.py \
  --problem "证明并验证：对任意实数 x，有 (x+1)^2 = x^2 + 2*x + 1" \
  --steps-out steps.json \
  --draft draft.md
```

### 3. 路由并执行证明步骤

```bash
python scripts/step_router.py \
  --input steps.json \
  --output steps.routed.json \
  --explain
```

### 4. 执行最终审计

```bash
python scripts/final_audit.py \
  --steps steps.routed.json \
  --solution Solution.md \
  --lean-cwd "<path-to-lean-project>" \
  --lean-gate
```

### 5. 运行 v8 协议伪测试

```bash
python skill/scripts/mathprove_v8_pseudotest.py
python scripts/mathprove_v8_pseudotest.py
```

## 运行产物

运行产物默认写入 skill 包外部。典型结构如下：

```text
mathprove_workspace/runs/<run_id>/
├── problem.md
├── problem_lock.md
├── assumptions.md
├── manifest.json
├── status.json
├── context_lake/
├── knowledge/
├── plan/
├── candidates/
├── magi/
├── sympy/
├── lean/
├── memory/
├── draft/
├── audit/
└── logs/
```

证明运行期间不应修改 skill 包本体。临时产物、日志、候选包和交接 capsule 应写入 workspace。

## 验证纪律

MathProve 将数学结论的支持强度分为四类：

1. Lean 或其他证明助手的 kernel-checked artifact；
2. 带显式假设的可回放精确符号计算；
3. 带记录范围的有界或穷举反例搜索；
4. 与可审计工件绑定的人类可读证明步骤。

只有这些层级可以支撑晋升结论。头脑风暴、多数投票、类比和隐藏推理只属于探索信号，不是证明证书。

## 开发验证

推荐检查：

```bash
python -m py_compile skill/runtime/proof_factory_v8.py skill/runtime/context_lake_v8.py skill/runtime/moe_router_v8.py
python skill/scripts/mathprove_v8_pseudotest.py
python scripts/mathprove_v8_pseudotest.py
python -m pytest -q
```

v8 合并后的最近一次本地验证：

```text
125 passed
```

## 文档

- [English README](README.en.md)
- [v8 deep optimization report](optimization/DEEP_OPTIMIZATION_REPORT_V8.md)
- [v8 patch notes](optimization/PATCH_NOTES_V8.md)
- [v8 pseudotest report](optimization/PSEUDOTEST_REPORT_V8.json)

## License

MIT License
