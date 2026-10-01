# TriviumDB 研究数据库接入计划

**目标**：将 TriviumDB 作为 MathProve 实际可用的研究数据库依赖，不锁版本或源码提交；保留 SQLite 作为任务租约、会话与流程状态存储。

**批准范围**：用户于 2026-10-01 选择真实研究数据库接入方案。数据库在本地执行，可从当前本地源码安装；允许建立 Python 3.12 虚拟环境验证，不引入容器或虚拟机。

## 核实依据

- MathProve 当前没有 TriviumDB 依赖或调用；`skill/runtime_v9/core.py` 使用 SQLite。
- `D:\MATH _Studio\TriviumDB\python\triviumdb\__init__.pyi` 提供 `TriviumDB`、`insert`、`get_payload`、`all_node_ids`、`link`、`close` 等真实接口，不提供 SQLite SQL 接口替换能力。
- TriviumDB 当前 Python 包要求 Python `<3.13`。已在 `.venv-triviumdb` 建立 Python 3.12 环境并从本地源码安装成功，未指定包版本或提交。

## 设计

### 数据职责

SQLite 保存流程状态与证明证据登记，不自动迁移或双写。TriviumDB 保存研究文档、文献、引理及记录关系，路径为 `.mathprove/research.tdb`，向量维度配置为 `.mathprove/research-db.json`。两种存储均不直接构成证明验收依据。

每条研究记录包含所属 run、登记时的目标修订编号以及用户 payload。向量必须由输入提供，长度匹配初始化维度且元素有限；不补零、不伪造嵌入。记录读取、查询和连接限于指定 run，历史修订编号保留为记录上下文。

### 命令

- `db-init --dim N`：显式初始化研究数据库；重复同维度初始化幂等，不同维度拒绝静默重建。
- `db-put RUN --record FILE`：输入 JSON 结构为 `{"vector": [...], "payload": {...}}`，返回节点编号。
- `db-get RUN NODE_ID`：读取指定研究记录，返回所属修订和 payload。
- `db-query RUN --query TEXT --limit N`：按 payload 的字面文本查询，返回同一 run 的记录，稳定按节点编号排序；不宣称语义向量检索。
- `db-link RUN SOURCE_ID TARGET_ID --label LABEL`：连接同一研究任务的记录。
- `doctor`：报告 TriviumDB 包是否可导入、实际版本、数据库是否初始化；不以固定版本作为验收条件。

`TriviumDB` 延迟导入，普通状态命令不因缺少扩展而失效；执行数据库命令时缺少依赖明确返回 JSON 错误和本地安装说明。数据库操作使用原生接口，关闭句柄后能重新打开；读取不隐式创建新库。

## 文件范围

- 新建：`skill/runtime_v9/research_db.py`、`skill/requirements-db.txt`、`tests_v9/test_research_db.py`、本计划。
- 修改：`skill/runtime_v9/cli.py` 的解析与分发、`skill/runtime_v9/install.py` 的文件选择、`.gitignore` 的本地环境排除。
- 文档：`skill/SKILL.md`、`skill/agent.md`、`skill/references/v9/operations.md`、`README.md`、`CHANGELOG.v9.md`，澄清新增数据库依赖与两种存储职责。
- 持续集成：`.github/workflows/mathprove-v9-tests.yml` 增加 Python 3.12 的真实 TriviumDB 测试任务，安装依赖不指定版本。
- Snow 同步：只更新发生修改的技能文件，包含新增适配器与依赖声明；不重新安装 hooks，不更改宿主 Python 命令配置。

## 实施与验证

- [ ] 先增加回归测试并确认接入缺失导致失败。
- [ ] 新建最小原生适配器并加入 CLI 分发，保留 core、runner、hooks 的既有行为。
- [ ] 使用不带版本条件的 `triviumdb` 依赖声明，安装器复制该声明；忽略 `.venv-triviumdb/`。
- [ ] 测试缺依赖错误、未初始化、维度和数值校验、跨任务隔离、重复初始化、持久化重新打开、查询及关系连接、CLI JSON 输出。
- [ ] 在 Python 3.12 环境执行真实 TriviumDB 测试与完整 v9 回归。
- [ ] 在现有 Python 3.13 环境执行完整回归，缺少扩展时只跳过明确标注的真实数据库测试，缺依赖行为必须通过。
- [ ] 编译 Python 文件、审查差异、同步当前 Snow 技能并确认加载入口。
- [ ] 将本地执行规则与数据库接入一并经确认提交、推送、建立拉取请求；远端检查通过后合并 main。

## 验收条件

依赖声明不锁版本、分支或提交；CLI 真实写入并持久化 TriviumDB 研究数据；读取、查询、关系连接和错误行为有测试证据；现有 SQLite 流程回归通过；当前 Snow 技能含新增接口；最终 GitHub main 包含两部分修正。

## 范围边界

不替换 SQLite 流程状态，不自动迁移旧研究工作区，不添加 embedding 服务或新检索框架，不修改 TriviumDB 项目，不扩大宿主权限，不将数据库写入或测试成功描述为数学证明成功。

## 实施记录

接入已完成测试先行与真实数据库验证。独立审查发现并修正大整数的原生数值转换损失、JSON 转义文本导致的字面查询漏检；内部 payload 以无损 JSON 文本保存，公开 API 仍返回对象。新增回归确认大整数、嵌套数据、引号、反斜杠及 Unicode 在写入／关闭／重新打开后保持正确。

最终本地完整回归：Python 3.12／真实 TriviumDB 环境运行 229 项，224 通过、5 跳过；Python 3.13 无扩展环境运行 229 项，203 通过、26 跳过。原生数据库套件 32 项全部通过；两环境 Python 编译检查通过。实际测试包为本地源码安装的 TriviumDB 0.8.8，此编号仅记录验证环境，不是依赖约束。最终发布与合并结果通过 GitHub 拉取请求核实。
