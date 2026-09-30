# MathProve-Skill 9.1 — 数学研究工作台

面向持续数学研究、定理证明、文献复用、反例搜索、符号计算和可选 Lean 形式化。工作重点是推进数学问题、保留可恢复的研究进度，而不是进行代码供应链审计。

## 本次调整

- Lean／mathlib 使用最新互相兼容的环境，不冻结特定版本或依赖提交。
- 不验收源码、依赖、二进制、日志、研究笔记或事件链的哈希。
- 直接在已有 Lake 项目编译，复用 `.lake` 缓存，支持本地路径依赖和正常元编程。
- 取消反复构建授权、哈希变动审批和强制人工快照签核；数学审阅作为普通研究记录。
- 保留真正的数学验证：精确目标类型、实际编译结果、公理依赖、假设核对与未解决反例。

旧版本报告保留为历史资料，不再作为当前研究流程的版本锁定或审批要求。数据库中的 `spec_hash` 等旧字段名仅为兼容现有工作区保留：当前目标使用修订编号，证据使用对象编号，不计算或核验内容哈希。

## 使用方式

- **直接研究**：加载 `skill/SKILL.md`，读取问题、假设与已有证明，选择下一步有价值的数学行动。简单任务不要求创建数据库或走完所有阶段。
- **Portable-local**：使用 Python 3.11+ 标准库控制器保存引理任务、研究证据与检查点。
- **CoMath-backed**：已有 CoMath 服务时使用它当前提供的工具，不为同一个研究项目另建影子数据库。入口说明见 `skill/references/v9/comath-backed.md`。

```powershell
python skill/scripts/mathprove.py --root D:/research/project doctor
python skill/scripts/mathprove.py --root D:/research/project init
python skill/scripts/mathprove.py --root D:/research/project start paper1 --spec spec.json
python skill/scripts/mathprove.py --root D:/research/project status paper1 --check
```

研究对象由 `statement`、`assumptions`、`symbols` 描述。形式化任务另需 `lean.project`、`lean.module`、`lean.declaration`、`lean.expected_type`。修改数学目标使用 `revise`；正常改进笔记和代码不因文件字节变化被阻断。

操作示例见 `skill/references/v9/operations.md`。`spec → plan → candidate → refutation → verify → release` 是可选的持续项目组织工具，不是数学真理或新颖性认证流程。

## Lean 与 mathlib

保持最新不等于强行组合互不兼容的版本：使用当前 mathlib 要求的 Lean 工具链。准备或更新项目时使用正常 Lake 流程；研究过程中复用已有依赖与缓存。Lake 自动生成的 `lean-toolchain`／`lake-manifest.json` 是正常构建元数据，不是 MathProve 的冻结或审批门禁。

```powershell
# 在形式化项目中准备或更新当前依赖，然后验证所研究的目标。
lake update
lake build
python skill/scripts/mathprove.py --root D:/research/project verify paper1 --timeout 1800
```

验证器在实际项目中执行构建，用指定声明生成精确 `expected_type` 检查并读取公理依赖。`sorry`、错误目标或额外未说明公理不会被当作完成证明。`--allow-build` 仅保留为旧调用的兼容参数，不再是必需授权步骤。未安装 Lean 时继续数学研究，并将形式验证标记为待完成。

## 安装与协作

```powershell
python scripts/install_v9.py --project D:/research/project --dry-run
python scripts/install_v9.py --project D:/research/project --upgrade
```

安装入口、角色模板和 hooks 可按需要使用；不必为普通研究同时启动所有角色。已有文件更新保留备份，不提交工作区、私有凭据或租约文件。Snow 安装见 `docs/v9/SNOW-HOOKS.md`。

`apply_v9_overlay.py` 接受文件路径列表或旧清单，比较实际内容决定是否复制，不校验旧清单哈希或旧源码提交。`comath_codex_config.py` 根据当前构建入口生成配置，不要求源文件匹配历史 Git blob。

## 验证

```powershell
python -m unittest discover -s tests_v9 -p 'test_*.py' -v
python scripts/demo_v9.py --root D:/research/demo-project
```

协议回归与模拟编译测试不等于真实 Lean 内核验收。本轮本机没有 Lean／Lake，真实证明编译未运行；测试结果和具体变更见 `CHANGELOG.v9.md`。保留原许可证及既有历史工作。
