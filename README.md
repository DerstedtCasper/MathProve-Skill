# MathProve-Skill

语言 / Language: [中文](README.md) | [English](docs/README.en.md)

MathProve 是一个神经符号数学验证流水线，集成 SymPy 与 Lean4，为数学推理提供可审计的证据链。目标是把自然语言推导映射为可执行步骤，并将验证结果汇总为 `Solution.md`。

## 核心特性

- **证明搜索树 (ProofSearchTree)**：基于状态机的证明步骤生命周期管理，支持回滚与序列化
- **MATH MAGI 规划**：三角色投票 + 一票否决，生成结构化 `steps.json`
- **三级错误分类 (ErrorClassifier)**：SYNTAX / LOGIC / ENVIRONMENT，自动重试与 Prompt 重构
- **并行候选竞速 (ParallelRunner)**：N 分支并行验证，首胜取消，物理隔离
- **SafeVerify 白盒审计**：Lean4 违禁词扫描 + `#print axioms` 公理溯源 + 可选环境重放
- **Orchestrator 编排循环**：集成上述所有模块的一键编排入口
- **严格门禁**：仅 `status=passed` 且附带证据的 step 可写入 `draft.md`
- **审计闭环**：`final_audit.py` 统一产出审计结果与 `Solution.md`

## 安装

### 作为独立 CLI 工具使用
```bash
git clone https://github.com/DerstedtCasper/MathProve-Skill.git MathProve
cd MathProve
```

### 挂载为 Codex/Agent Skill
建议挂载 `skill/` 目录，并保证目录名与 `SKILL.md` 中 `name: mathprove-skill` 一致：
```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.codex\skills\mathprove" `
  -Target "<repo_root>\skill"
```

## 快速开始

### 1) 路由检查（必需）
```bash
python scripts/check_routes.py
```

### 2) MATH MAGI 规划（必需）
```bash
python scripts/magi_plan.py --problem "<问题文本>" --steps-out steps.json --draft draft.md
```

### 3) 步骤路由与执行（必需）
```bash
python scripts/step_router.py --input "steps.json" --output "steps.routed.json" --explain
```

### 4) Final Audit（必需）
```bash
python scripts/final_audit.py \
  --steps "steps.routed.json" \
  --solution "Solution.md" \
  --lean-cwd "<path-to-lean-project>" \
  --lean-gate
```

### 5) 使用 Orchestrator（可选，一键编排）
```python
from skill.runtime.orchestrator import Orchestrator, OrchestratorConfig

orch = Orchestrator(OrchestratorConfig(enable_safe_verify=True))
result = orch.run("证明: 对任意实数 x，(x+1)^2 = x^2+2x+1", steps)
print(result.summary)
```

## 工作区与 run_dir
- 运行产物默认写入 `../mathprove_workspace/`（相对 `skill/`），并自动创建 `run_YYYYMMDD_HHMMSS_xxx/` 子目录
- 可在 `skill/config.yaml` 中设置 `workspace_dir` 覆盖默认值
- `run_dir` 内含 `logs/`、`draft/`、`evidence/`、`audit/`、`magi/`、`sympy/`、`lean/`、`plan/` 等子目录

## 工作流状态机
```
INIT → PLANNING → STEP_LOOP → AUDITING → DONE
                      ↕                     ↕
                   FAILED ←←←←←←←←←←←← FAILED
```

## 项目结构

```
MathProve-Skill/
├── README.md                    # 本文件
├── LICENSE                      # MIT License
├── requirements-dev.txt         # 开发依赖
├── skill/                       # ★ Skill 根目录（挂载入口）
│   ├── SKILL.md                 # Skill 契约与 SOP
│   ├── agent.md                 # Agent 顶级约束宪章
│   ├── config.yaml              # 默认配置
│   ├── runtime/                 # 运行时核心模块
│   │   ├── proof_tree.py        # 证明搜索树状态机
│   │   ├── error_classifier.py  # 三级错误分类器
│   │   ├── parallel_runner.py   # 并行候选竞速框架
│   │   ├── safe_verify.py       # Lean4 白盒审计
│   │   ├── orchestrator.py      # 顶层编排循环
│   │   ├── config_loader.py     # 配置加载
│   │   ├── workspace_manager.py # 工作区管理
│   │   ├── magi/                # MAGI 三角色协议
│   │   └── ...
│   ├── scripts/                 # CLI 脚本入口
│   ├── assets/                  # 静态资源（模板、Schema、提示词）
│   └── references/              # 参考资料
├── scripts/                     # 兼容入口（代理到 skill/scripts/）
├── tests/                       # 单元测试（117 tests）
├── docs/                        # 文档
│   ├── IMPL_PLAN.md             # 实现计划与进度
│   ├── CONTRIBUTING.md          # 贡献指南
│   └── design/                  # 设计文档
├── docker/                      # Docker 配置
└── runtime/                     # 兼容 shim（re-export skill.runtime）
```

## 测试
```bash
python -m pytest --tb=short -q
# 117 passed
```

## License
MIT License
