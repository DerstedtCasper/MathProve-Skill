# MathProve-Skill v9.0.0-rc2

**非 Pi 环境的可恢复数学研究协议：共享工作区、任务依赖、证据门禁、Codex hooks 与角色模板。** Python 3.11+；便携控制器仅依赖标准库。它不自行调用模型、管理 API key 或认证数学新颖性。

本版本基于对固定源码版本的重点审阅：CoMath `e8e0182823b383cb228802c4d70f3309bf0a698c`；MathProve `e4aaf6abec8c05bc5186d635b06b56152442380b`。GitHub 插件读取成功，四个用于复现的原始文件已核对 Git blob SHA；**不是两个仓库的完整 clone，也不是整仓审计或完整上游回归**。本包是保留旧文件的增量覆盖包，没有修改远端。证据范围见 `docs/v9/SOURCE-COVERAGE.json`。

## 选择一种运行方式

| 方式 | 使用对象 | 状态与授权由谁维护 |
|---|---|---|
| Portable-local | 不用 Pi，也不部署 CoMath 服务 | 本包 SQLite/WAL、任务租约和本地审阅记录；合作式单用户协议 |
| CoMath-backed | 不用 Pi，但愿意运行现有 `comathd` | **原 CoMath 服务**；Codex 通过仓库现有 operator MCP 操作，不另建影子数据库 |

第二种方式更适合追求与 CoMath 同一运行标准，但本次只核对了接口与配置生成，没有完成真实 daemon/Codex 验收。两种模式不能把成功标签或人工审批互相转换。详见 `docs/v9/PARITY.md`。

## RC2 相比 RC1 的实质更新

修复旧 `proof_factory_v8.py` 的混合阶段候选、重复 ID、非法阈值、非有限评分、依赖环/悬空依赖、字符串假值终止问题。这个旧模块仍是研究评分工具，**不因修补而变成证明验证器**；旧 context-lake 多写索引竞争未就地重构，新并发研究应使用 v9 或 CoMath。

CoMath 提示词不再把便携角色名称硬套进其注册表。新增九个与实际 profile ID 对应的补充模板，并标明 Pi 与 durable-worker 的不同接入点。新增 `comath_codex_config.py`：校验已审源码后生成现有 operator MCP 的 TOML，默认只开放读取工具，不读取密钥、不启动服务、不改全局信任。覆盖器新增上游文件指纹和相关 Git 未提交改动检查。

Codex hooks 保留九类原生事件；只在本实现确实返回上下文的启动事件配置 `additionalContextLimit`。不在 hook 内编译、调用模型或自动安装依赖，也不因为问题未解决而无限阻止退出。**152 项测试：150 通过，2 跳过；真实 Lean 和原生 Windows 未运行。** 另有 4 项所选旧测试及 13 个 CoMath 独立签名解析回归；不等于完整上游回归。

## 先在空目录演示便携模式

```sh
python -m unittest discover -s tests_v9 -p 'test_*.py' -v
mkdir demo-project
python scripts/demo_v9.py --root demo-project
python skill/scripts/mathprove.py --root demo-project status demo --human --check
```

演示是非形式化流程测试，不是模型能力评测；不调用 Lean、不伪造独立审阅、不自动执行人工签核。默认 2 个并发租约、每任务 3 次尝试、每轮 32 次尝试，可显式调整；**这些不是 token 或费用上限**。六道累计门禁为 `spec → plan → candidate → refutation → verify → release`。

## 安装到 Codex 研究项目（Portable-local）

```sh
python scripts/install_v9.py --project /absolute/research/project --dry-run
python scripts/install_v9.py --project /absolute/research/project
```

安装至 `.agents/skills/mathprove-skill/`、`.codex/hooks.json`、`.codex/agents/mp_*.toml`。目标目录须存在。已有不同受管理内容时，先查看 dry-run，再使用 `--upgrade` 进行带备份更新。操作者仍需在宿主中审阅项目及 `/hooks` 的信任；更改 hooks 后重新审阅。移动目录或 Python 后重装。`--no-hooks` / `--no-agents` 是本次跳过，不是卸载旧配置。

便携角色是 coordinator、formalizer、strategist、librarian、prover、experimenter、refuter、integrator、auditor；九种职责并非同时启动九个模型。无真实子代理能力时必须记录为顺序检查。

```sh
python skill/scripts/mathprove.py --root /absolute/research/project init
python skill/scripts/mathprove.py --root /absolute/research/project doctor
python skill/scripts/mathprove.py --root /absolute/research/project start paper1 --spec spec.json
python skill/scripts/mathprove.py --root /absolute/research/project status paper1 --human --check
```

`spec.json` 在研究根目录内；示例见 `examples/v9/`。命令详见 `skill/references/v9/operations.md`。只有在操作者审查 Lake/依赖构建行为后，才显式执行 `verify paper1 --allow-build`。真实 Lean 验收尚未运行；新回放目录不是沙箱，也不保证全部传递依赖从源码重建。

## 不用 Pi，但复用原 CoMath 服务（CoMath-backed）

在你已审阅并构建好的 CoMath 检出上生成配置：

```sh
python scripts/comath_codex_config.py --comath-root /absolute/path/to/comath-pi-lab
# 需要明确授权的任务操作时，再选择 --access operator。
```

手工合并输出到研究项目的 `.codex/config.toml`，不要用 shell 重定向覆盖已有配置。通过环境提供 `COMATH_OPERATOR_BASE_URL` 和 `COMATH_OPERATOR_TOKEN`，不要把凭据提交到仓库。服务的 operator token 不得换成 host/worker 凭据。配置器检查源文件指纹及已构建入口存在，**不认证构建产物与源码一致性**；操作者需构建所审版本。

本模式不执行本地 `init/start/review` 来镜像同一 campaign；不把 `mp_*` 的便携任务 JSON 当作 CoMath worker 协议。使用已有 `research_capabilities_get` 先发现实际能力。见 `skill/references/v9/comath-backed.md`。

## 合并到你的 MathProve-Skill 仓库

在本地审阅分支中，用包内覆盖器预览和应用，而不是删除旧仓库：

```sh
python scripts/apply_v9_overlay.py --target /path/to/MathProve-Skill --dry-run
python scripts/apply_v9_overlay.py --target /path/to/MathProve-Skill --apply
```

目标须包含已审的原 v8 核心文件，或本包相同修补版本。上游文件指纹不符、计划覆盖的 Git 路径有未提交改动时，脚本拒绝写入；没有 Git 时报告无法做 Git 状态检查。字节级检查也可能拒绝 CRLF 转换后的副本，此时人工合并 `review/patches/mathprove-v8-validation.patch`，不要绕过检查覆盖自己的改动。覆盖不是三方合并，旧数据库不迁移，旧启动器不自动切换。

`review/patches/comath-statement-signature.patch` 是单独供 CoMath 审阅的候选补丁，**不由本安装器应用**。合并及回退见 `docs/v9/MIGRATION.zh-CN.md`。

## 审阅与交接

`docs/v9/AUDIT.zh-CN.md` 给出源码发现及优先级；`TEST-REPORT.md` 给出实测与未覆盖项；`COMATH-PROMPTS.md` 说明角色真实接入路径；`HANDOFF.md` 记录后续验收。旧 RC1 报告仅作为历史记录保存在 `docs/v9/archive/rc1/`。

不要提交 `.mathprove/`、私有租约文件、研究工作区或备份。先把 `gitignore.v9.snippet` 合并进现有规则，再按路径选择提交，避免 `git add .`。保留原许可证；独立新增内容见 `LICENSE.v9`，修改的旧模块和 CoMath 补丁来源见 `review/UPSTREAM-NOTICES.md`。
