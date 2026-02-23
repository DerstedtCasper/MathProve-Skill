# MathProve-Skill 重构为标准 Skill 形式：执行计划（Plan）

> 目标：将仓库整理为“标准 Skill 目录结构”（`assets/`、`references/`、`scripts/`、`SKILL.md`）同时保留现有独立 CLI/脚本可运行能力。  
> 原则：每一步都必须可跑通（本地 + CI），否则不进入下一步；PR 说明必须足够详细让 maintainer 明晰意图与风险。  
> 注意：本文件仅用于跟踪，不涉及 `git push`。

## 当前进度（滚动更新）

- [x] 基线 `pytest` 通过（作为后续门禁基础）
- [x] 增加兼容导入 `MathProve.scripts.*` -> `scripts.*`（修复测试导入路径）
- [x] 增加 smoke gate：`scripts/ci_smoke.py`（CI/本地一致验证）
- [x] CI 增加 smoke 步骤（`.github/workflows/ci.yml`）
- [x] 引入路径定位工具：`scripts/runtime_paths.py`，并在关键脚本中使用（迁移前置）
- [x] 迁移为标准 Skill 目录：`skill/`（包含 `SKILL.md`、`assets/`、`references/`、`scripts/`、`runtime/`、`agent.md`、`config.yaml`）
- [x] 保留仓库根兼容入口：`scripts/`（wrapper + `ci_smoke.py`），`runtime/`（import shim）
- [x] 迁移后回归：`python -m pytest` + `python "scripts/ci_smoke.py"` 均通过
- [x] 落实门禁约束：`draft_logger` 默认拒绝未验证 step（要求 `status=passed` 且 `evidence` 非空）；`final_audit` 增加 Lean4 静态预检（禁止 `axiom/constant/opaque/sorry/admit`，并强制 `theorem/lemma Sx` 可追溯映射）

## 协作策略（已确认）

- 采用 **叠加式（stacked）多分支** 推进多个 PR：
  - `pr1` 基于 `main`
  - `pr2` 基于 `pr1`
  - `pr3` 基于 `pr2`
- 合并策略：按顺序合并 PR1 → PR2 → PR3；每个 PR 必须先通过门禁（见下文）。
- 主线目标：以“重构成标准 Skill 形态 + 每一步可跑通”为第一优先级；避免无需求的重写（KISS/YAGNI）。

## 叠加式 PR 拆分（本地整理用）

> 目标：每个 PR 都可独立通过门禁；后续 PR 基于前序 PR（stacked），降低冲突并便于 review。

### PR1：标准 Skill 目录落地 + 兼容入口（功能不变）
- 内容：
  - 引入 `skill/`（SKILL/assets/references/scripts/runtime/config/agent）
  - 仓库根保留兼容入口：
    - `scripts/`：wrapper（`python scripts/<name>.py` / `import scripts.<name>`）
    - `runtime/`：import shim（`import runtime.*` 仍可用）
    - `MathProve/`：兼容测试导入（`MathProve.scripts.*`）
  - `.gitignore`：忽略 `skill/logs/`、`skill/subagent_tasks/`
- 门禁：
  - `python -m pytest`
  -（建议）`python scripts/problem_router.py --text "证明并计算 (x+1)^2"`、`python scripts/final_audit.py --help`

### PR2：门禁增强（CI + Smoke Gate）
- 内容：
  - 新增 `scripts/ci_smoke.py`（同时验证 repo `scripts/` 与 `skill/scripts/` 两套入口）
  - CI 增加 smoke step（`.github/workflows/ci.yml`）
  - CONTRIBUTING 更新：统一 `pytest + smoke` 验证命令
- 门禁：
  - `python -m pytest`
  - `python scripts/ci_smoke.py`

### PR3：文档澄清（可安装路径、agent/config 说明）
- 内容：
  - README 三语：明确推荐挂载 `skill/`；解释 `agent.md` 为参考模板；说明 `config.yaml` 当前不自动读取（并给出 CLI 映射示例）
  - `skill/SKILL.md`：同步对 `agent.md` / `config.yaml` 的定位说明
- 门禁：
  - `python -m pytest`
  - `python scripts/ci_smoke.py`

## 0. 术语与约束

- **标准 Skill 目录**：最终可拷贝/安装到 `$CODEX_HOME/skills/<skill-name>/` 的最小闭包目录，拟命名为 `skill/`（仓库内）。
- **工程仓库根**：用于开发/测试/CI 的工作区，保留 `tests/`、`.github/` 等。
- **门禁（Hard Gate）**：每个阶段完成后必须通过的验证集合（见每阶段“验收”）。
- **兼容性**：旧用法（例如 `python "scripts/final_audit.py" ...`）在明确允许移除前必须持续可用。

## 1. 总体目标与非目标

### 1.1 目标
- 输出 `skill/` 目录，包含 Skill 所需文件与资源，并可独立运行其 `scripts/`。
- 保留仓库根的独立运行能力（最少通过“兼容层 wrapper”实现）。
- PR 可审查：单一职责、可回滚、说明清晰、验证完备。

### 1.2 非目标（第一轮不做）
- 不引入大规模架构重写/过度抽象（避免违反 KISS/YAGNI）。
- 不强制把一切改成包发布（`pip install`/`pyproject.toml`）除非确有必要且验收明确。
- 不在没有明确确认的情况下做潜在破坏性清理（删除旧入口、批量移动/重命名等）。

## 2. 当前风险点（迁移前必须控制）

- 脚本内存在基于 `__file__`/`parents[1]` 的路径假设（例如定位 `assets/templates/...`）。目录迁移会导致路径断裂。
- tests 可能通过硬编码路径调用脚本（例如 `tests/...` 拼 `scripts/*.py`），目录结构变化会引发用例失败。
- IDE 中出现 `scripts/runtime_paths.py`（当前仓库未检索到该文件），需要确认它是否为未提交/本地变更或误引用；否则需提供新的路径解析模块替代。

## 3. 执行阶段（按 PR 拆分）

> 每一阶段建议对应一个 PR，且 PR 内保持单一职责。下面的“PR#”为建议编号。

### PR#0（可选但推荐）：建立统一 Smoke Gate（不改目录结构）

**目的**
- 用一组稳定、可重复的命令验证“关键脚本链路可跑”，让后续目录迁移有明确回归检测。

**工作项**
- 新增一个 smoke 入口（建议：`scripts/ci_smoke.py`）：
  - 以最小输入跑通关键脚本（至少 `--help` 可运行；能跑的做最小功能验证）。
  - 避免依赖 Lean 环境（CI 默认不具备 mathlib 工程）。
- CI（`.github/workflows/ci.yml`）新增一步运行 smoke（只要不过度拉长耗时即可）。

**验收（必须全部通过）**
- `python -m pytest`
- `python "scripts/ci_smoke.py"`
- GitHub Actions `ci` 工作流通过（PR 上自动检查）

**PR 描述必须包含**
- smoke 覆盖脚本列表 + 每条命令的预期目标（例如“确保脚本可启动并解析参数”）。

---

### PR#1：引入“布局无关”的路径解析层（先解决迁移最大风险）

**目的**
- 让代码同时支持“当前根目录布局”和“未来 `skill/` 标准布局”，迁移目录时不破。

**工作项**
- 新增模块（建议：`runtime/paths.py` 或 `runtime/pathing.py`）提供：
  - `repo_root()` / `skill_root()`（自动探测：优先找 `skill/SKILL.md`，否则回落到仓库根 `SKILL.md`）
  - `assets_dir()`、`templates_dir()`、`references_dir()`、`scripts_dir()`
- 逐步替换脚本内硬编码 `parents[1]/assets` 之类定位方式（行为不变，仅定位策略变化）。
- 若确有 `scripts/runtime_paths.py` 本地文件：要么纳入并迁移其职责，要么替换并删除（需明确确认）。

**验收（必须全部通过）**
- `python -m pytest`
- `python "scripts/ci_smoke.py"`（若 PR#0 未做，则本 PR 同时引入）

**PR 描述必须包含**
- 路径探测规则（优先级、回退逻辑、失败时错误信息）。

---

### PR#2：迁移资源到 `skill/`（先搬资源，后搬入口）

**目的**
- 把标准 Skill 需要的资源目录搬到 `skill/`，同时依靠 PR#1 的路径解析保证“还能跑”。

**工作项**
- `git mv`（批量移动，属于高风险操作：执行前需明确确认）：
  - `assets/` -> `skill/assets/`
  - `references/` -> `skill/references/`
  - `SKILL.md` -> `skill/SKILL.md`
  - 视运行依赖：`agent.md`、`config.yaml`、`runtime/` 是否也需迁入 `skill/`
- 更新 README/CONTRIBUTING 等文档中的路径引用。

**验收（必须全部通过）**
- `python -m pytest`
- `python "scripts/ci_smoke.py"`
- 至少一次直接从新位置读取模板/schema 的实际运行验证（例如运行能触达 `assets/templates/...` 的脚本）

**PR 描述必须包含**
- 目录迁移清单（from -> to），以及“为何这些属于 Skill 最小闭包”。

---

### PR#3：迁移 `scripts/` 到 `skill/scripts/` + 根目录兼容层

**目的**
- `skill/scripts/` 成为“标准 Skill 入口”，仓库根仍保留旧命令用法（wrapper 代理）。

**工作项**
- `git mv`：`scripts/` -> `skill/scripts/`（高风险：执行前需明确确认）
- 在仓库根重建 `scripts/`，其中每个脚本是薄 wrapper：
  - 原样转发参数到 `skill/scripts/<same_name>.py`
  - 保持 `python "scripts/foo.py"` 仍可用
- 修正 tests 中对脚本路径的引用（优先保留不改 tests 的前提，通过 wrapper 保持兼容）。

**验收（必须全部通过）**
- `python -m pytest`
- `python "scripts/ci_smoke.py"`
- 同时验证两条入口：
  - `python "skill/scripts/final_audit.py" --help`
  - `python "scripts/final_audit.py" --help`

**PR 描述必须包含**
- 兼容层策略（为什么保留、保留多久、未来移除条件）。

---

### PR#4（可选）：收尾清理与稳定（需你明确确认）

**目的**
- 在确认不再需要旧入口/旧路径后，做最小清理，降低维护成本。

**可能工作项**
- 移除过期 wrapper / 旧文档引用 / 重复资源
- 把仅工程需要的内容留在根目录，把 Skill 运行需要的内容收敛到 `skill/`

**验收**
- 同前，且增加“无旧入口依赖”的验证（如果决定移除兼容层）

## 4. 统一验证命令（本地）

> 下面命令将作为每个阶段 PR 的“验证证据”写入 PR 描述。

```powershell
python -m pytest
python "scripts/ci_smoke.py"
python "scripts/final_audit.py" --help
python "scripts/verify_sympy.py" --help
```

（后续迁移后会补充 `skill/scripts/...` 的同等命令）

## 5. PR 文档模板（中文为主）

```markdown
## 背景
- 现状：
- 目标：

## 改动内容
- 新增：
- 调整：
- 删除：

## 行为与兼容性
- 行为变化：
- 兼容策略：
- 迁移说明（如需）：

## 验证
- 本地：`python -m pytest`
- Smoke：`python "scripts/ci_smoke.py"`
- 关键路径：`python ".../xxx.py" --help`（必要时给最小样例）

## 风险 & 回滚
- 风险点：
- 回滚方式：

## 不在本 PR 范围
- ...
```

## 6. 下一步（开始前需要确认的问题）

1) CI smoke 需要覆盖哪些脚本视为“每一个环节”？（默认：`verify_sympy.py`、`draft_logger.py`、`step_router.py`、`problem_router.py`、`final_audit.py` 的最小可运行验证）
2) 是否强制保留旧入口 `python "scripts/xxx.py"` 至至少一个发布周期？（默认：是）
3) `runtime/`、`config.yaml`、`agent.md` 是否属于 Skill 最小闭包并迁入 `skill/`？（默认：是，除非你指定拆分）
