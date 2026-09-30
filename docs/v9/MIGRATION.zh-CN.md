# MathProve 9.1 安装与研究记录

## 使用原则

这是数学研究工作台，不是源码审计或发布审批系统。当前规范以仓库 README、`skill/SKILL.md` 和 `skill/references/v9/` 为准。RC1／RC2 报告仅保留历史信息，其中的固定版本、源码指纹、哈希验收和重复审批不适用于 9.1。

## 安装或更新技能

在源码仓库中运行以下命令，将技能部署至已有研究目录：

```powershell
python scripts/install_v9.py --project D:/research/project --dry-run
python scripts/install_v9.py --project D:/research/project --upgrade
```

安装器复制 v9 入口、角色、模板和运行时，保留被替换内容的备份，不删除未知文件或研究数据库。可使用 `--no-hooks`／`--no-agents` 只安装需要的部分；普通数学问题不要求数据库、全部角色或完整阶段流程。

更新全局技能时，将源码 `skill/` 中的 `SKILL.md`、`agent.md`、`agents/openai.yaml`、v9 运行时、v9 资料与实际使用的 `scripts/mathprove*.py` 同步到宿主发现的技能目录。不要把保留的旧 `skill/runtime/` 当成新入口复制。保留本地定制、其他技能及宿主已有配置；无需为更新说明重新安装全局 Hooks。

Snow Hook 使用方式见 `SNOW-HOOKS.md`。技能文件更新后，下次扫描或调用会加载新内容；已加载的会话上下文不会被追溯改写。

## 源码文件集覆盖

`apply_v9_overlay.py` 可预览并应用已有仓库的文件集覆盖：

```powershell
python scripts/apply_v9_overlay.py --target D:/research/MathProve-Skill --dry-run
python scripts/apply_v9_overlay.py --target D:/research/MathProve-Skill --apply
```

`RELEASE-MANIFEST.json` 使用文件路径列表，不包含哈希或旧源码提交前置条件。覆盖器比较实际内容判断是否需要复制，保留旧内容备份和目标未提交改动，不删除未知文件，不自动提交或推送。

## 数学研究与 Lean 验证

持续项目可通过 `doctor`、`init`、`status` 恢复记录，具体命令见 `skill/references/v9/operations.md`。目标修订使用 `revise`；工作笔记可正常编辑。注册证据是历史副本，结论的数学含义变化时重新登记或撤回，不把旧回执当成新证明。

使用最新互相兼容的 Lean／mathlib。mathlib 项目跟随当前 mathlib 要求的工具链，不独立强推不兼容的 Lean。正常 Lake 元数据和缓存可以保留，不要求固定依赖提交、冷重建或哈希检查。示例的 `stable` 只用于没有 mathlib 的基础项目。

`verify` 在实际项目执行 `lake build` 和精确目标类型检查，并读取公理依赖，不需要额外 `--allow-build`。数学审阅可直接记为普通 review，不要求 `--human-ack`。检查点失败只提示，不阻止停止。

实际编译未执行或失败、目标类型不匹配、存在 `sorryAx` 或未说明额外公理时，不标记为完成证明。Lean 未安装时继续数学研究，并记录形式验证待完成。旧 v8 状态不自动冒充新验证结果；已有 v9 SQLite 字段保留兼容，不清空研究进度。

## CoMath-backed

已有 CoMath 服务时使用它当前提供的工具，不为同一项目另建数据库。`comath_codex_config.py` 检查当前编译入口是否存在，不要求源码匹配历史 Git blob。角色补充和服务接入见 `COMATH-PROMPTS.md`、`skill/references/v9/comath-backed.md`。技能不修改外部服务本身的权限或配置。
