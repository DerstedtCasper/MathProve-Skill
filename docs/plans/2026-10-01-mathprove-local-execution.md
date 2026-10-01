# MathProve 本地执行规则修正计划

**目标**：明确 MathProve 允许直接在本地执行数学计算、Python 脚本和 Lean／Lake 验证，不将 Docker、Podman、虚拟机或容器沙盒作为前置条件。

**实施方式**：现有 v9 验证器已经通过本地子进程调用 Lake，无需修改运行时或公共接口。本次修改技能说明、操作参考和必要回归测试，保留旧 Docker 执行器作为用户主动选择的兼容工具。

**技术栈**：Python 3.11+ 标准库、unittest、Markdown、Windows PowerShell、GitHub CLI。

**已确认范围**：用户于 2026-10-01 确认推荐方案，实施后同步当前 Snow 技能，并推送 GitHub、合并到 main。每组 Git 操作在执行前列出确切命令，通过交互工具另行确认。

## 已核实上下文

- 源仓库：`D:\MATH _Studio\MathProve-Skill`。
- 当前分支：`main`，起始提交：`18336d8`，工作区干净。
- 远端：`https://github.com/DerstedtCasper/MathProve-Skill.git`。
- 当前 Snow 技能：`C:\Users\derst\.snow\skills\mathprove-skill`，是独立目录，不是链接。
- `skill/runtime_v9/runner.py` 直接在原项目执行 `lake build` 和 `lake env lean`，复用缓存。
- `skill/scripts/docker_runner.py` 仅由旧兼容入口调用，不是当前研究流程的必需依赖。
- 本机 Python 为 3.13.7；当前 PATH 没有 Lean／Lake。

## 修改文件与职责

| 文件 | 修改内容 |
| --- | --- |
| `skill/SKILL.md` | 增加明确的本地执行规则，位于研究方法之前，覆盖计算与形式验证。 |
| `skill/agent.md` | 在环境说明中明确本地执行许可及容器非必需。 |
| `skill/references/v9/operations.md` | 说明本地 Python／Lake 命令、缺少依赖时的处理和 Docker 可选性质。 |
| `README.md` | 增加本地执行说明，避免安装时误解。 |
| `CHANGELOG.v9.md` | 记录本次规则澄清和回归覆盖。 |
| `tests_v9/test_research_workflow.py` | 回归检查技能入口、角色实践和操作参考均保留本地执行规则。 |
| `tests_v9/test_runner.py` | 验证真实本地子进程在指定工作目录执行，未查询容器工具；模拟验证器只查找本地 Lake。 |
| `docs/plans/2026-10-01-mathprove-local-execution.md` | 本计划与验收记录。 |

## Chunk 1：规则修正与回归测试

- [ ] 在现有研究工作流测试中增加技能规则回归：三个说明入口均明确包含本地执行、容器非必需和宿主权限不变。
- [ ] 在现有 runner 测试中增加真实本地 Python 子进程检查：设置含空格的工作目录，输出 `Path.cwd()`，确认实际目录一致；禁止在该测试中查询容器工具。
- [ ] 增加验证器查询检查：模拟工具发现仅接受 `lake`，拒绝任何 Docker／Podman 等工具查询；保持已有精确目标类型和公理检查。
- [ ] 先运行新增测试，确认规则回归在修改前失败，执行行为测试可反映现有本地实现。
- [ ] 为三个技能说明入口加入一致规则：直接本地执行；不要求 Docker／Podman／虚拟机／容器沙盒；缺少工具时报告具体依赖，不要求先安装容器；保持宿主既有权限。
- [ ] 同步 README 与 CHANGELOG。保留 Docker 可选入口，不更改运行时、安装器、hooks 或 Codex 只读角色配置。

## Chunk 2：验证与 Snow 同步

- [ ] 运行定向测试：`python -m unittest discover -s tests_v9 -p 'test_research_workflow.py' -v`。
- [ ] 运行 runner 测试：`python -m unittest discover -s tests_v9 -p 'test_runner.py' -v`。
- [ ] 运行完整 v9 回归：`python -m unittest discover -s tests_v9 -p 'test_*.py' -v`。
- [ ] 编译 Python 文件：`python -m compileall -q skill/runtime_v9 skill/scripts/mathprove.py tests_v9`。
- [ ] 只同步 `SKILL.md`、`agent.md`、`references/v9/operations.md` 到当前 Snow 技能目录，确认复制前没有独立修改；发现差异时暂停并说明。
- [ ] 确认同步后的三个文件与仓库内容一致，重新加载技能确认本地执行规则可读取。
- [ ] 审查最终差异，仅包含本计划列出的文件；不将模拟编译结果称为真实 Lean 验收。

## Chunk 3：GitHub 发布与 main 合并

- [ ] 取得分支与 Git 检查命令的明确确认，再创建 `fix/mathprove-local-execution` 工作分支。
- [ ] 验证通过后，仅暂存上述八个仓库文件，提交 `fix: explicitly allow local MathProve execution`。
- [ ] 推送工作分支，创建目标为 `main` 的拉取请求，正文说明变更与验证结果。
- [ ] 核实远端 CI、可合并状态和差异范围，取得合并命令确认后合并。
- [ ] 使用快进方式同步本地 main，核实远端 main 含有合并结果。

## 验收条件

1. 技能和操作文档明确允许本地执行，没有将容器或虚拟机设为前置条件。
2. 新增回归测试与完整 v9 测试通过；Python 编译检查通过。
3. 当前 Snow 技能三个相关文件与仓库一致。
4. 保留已有数学验证规则、宿主权限、历史 Docker 可选工具和用户未提交工作。
5. GitHub 拉取请求合并到 main，发布结果有实际远端证据。

## 边界与验证解释

本地执行规则阶段不安装 Lean、Lake、Docker 或新依赖，不修改生产配置或宿主授权。真实 Python 子进程检查验证本地执行能力；模拟 Lake 测试验证编排与工具发现，不是 Lean 内核证明。若远端保护规则、CI 或权限阻止合并，保留已完成修改并报告实际阻碍，不强制推送或绕过保护。

## 后续范围补充与实施记录

用户随后批准接入 TriviumDB 研究数据库，详细范围见 `2026-10-01-triviumdb-research-db.md`。因此最终提交包含该接入的必要运行时、依赖声明、安装器和测试改动，不再限定为原八个文件；SQLite 流程状态与 Lean 验证器保持原行为。

本地执行规则已完成测试先行、定向回归、真实 Python 子进程验证、独立审查及首轮 Snow 同步。最终合并前本地回归为两种 Python 环境各 229 项：Python 3.12／TriviumDB 环境 224 通过、5 跳过；Python 3.13 无扩展环境 203 通过、26 跳过。两环境编译检查通过。GitHub 发布与 main 合并由会话待办跟踪，并以实际拉取请求结果为准。
