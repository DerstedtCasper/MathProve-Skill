# 安装、合并与回退

## 1. 区分两个动作

**合并源码**是把本包送进你的 MathProve-Skill Git 仓库；**安装 skill**是把受审版本部署到一个具体研究项目。两者不要混为一谈，研究数据库不属于 skill 源码。

本包未取得完整 upstream tree。`README.md`、`skill/SKILL.md`、`skill/agent.md` 等已存在的同名文件可能被替换；未知旧文件原样保留。因此这是“带备份的覆盖文件集”，不是自动三方合并，也不能保证旧安装器/启动器已经重定向到 v9。

## 2. 建立本地分支，预览覆盖范围

先在你自己的克隆中确认工作区状态，提交或妥善保存既有修改。下面解压目录名按 ZIP 顶层目录设置，目标路径自行替换：

```sh
cd /path/to/MathProve-Skill
# 先审查当前状态；不要让新覆盖掩盖未保存修改。
git status --short
git switch -c review/mathprove-v9

python /path/to/MathProve-Skill-v9/scripts/apply_v9_overlay.py --target /path/to/MathProve-Skill --dry-run
python /path/to/MathProve-Skill-v9/scripts/apply_v9_overlay.py --target /path/to/MathProve-Skill --apply
```

覆盖脚本先校验 `RELEASE-MANIFEST.json` 中全部文件的 SHA-256，再写目标。不会删除旧文件、不会处理旧数据库、不会自动提交或推送。同名旧内容备份到 `.mathprove-v9-overlay-backups/<id>/`；发生写入错误时尝试回滚此次已写文件。哈希防止包损坏，不是作者签名；先确认 ZIP 来源。

接着审阅 tracked diff 与新文件。`git diff` 不会显示未跟踪的新文件正文，应同时检查 `git status --short` 和 manifest。把 `gitignore.v9.snippet` 中的规则合并进现有 `.gitignore`，不要覆盖原规则。只暂存确认过的源码、模板和文档，不要提交备份或研究状态。

```sh
python -m unittest discover -s tests_v9 -p 'test_*.py' -v
git diff --check
git diff --stat
git status --short
```

旧测试、旧安装器和打包逻辑仍需你在真实完整仓库里运行并审阅。新增测试通过不代表旧 125 项或其他私有测试已经通过。本包不更改原 LICENSE；不要将 CoMath 原文件一起重新标为 MIT。

## 3. 安装到研究根目录

```sh
python scripts/install_v9.py --project /absolute/research/project --dry-run
python scripts/install_v9.py --project /absolute/research/project
```

只复制白名单 v9 文件到 `.agents/skills/mathprove-skill/`。不会把保留的旧 v8 scripts/runtime 偷渡到新安装。存在不同的受管理内容时，审查后使用 `--upgrade`；差异备份到 `.mathprove-install-backups/<id>/`。重复安装相同版本不会无谓改写 hooks 或使信任哈希变化。

安装器合并 `.codex/hooks.json`，同一个 matcher group 里的第三方 handler 也会保留。其他 hooks 来源（用户级、inline、插件）可能仍并行运行；请在 `/hooks` 中检查重复触发。它不编辑 `.codex/config.toml`、全局文件、permission 或 trust。`integrations/codex/config.snippet.toml` 仅供你手动选择并发设置。

旧版本若安装在 `.codex/skills/...`、另一个 `.agents/skills` 目录或插件中，请先查明宿主实际发现了哪些入口，再手动停用旧副本，避免两套协议同时生效；脚本不会擅自删除它们。不要同时用原生安装和另一个打包插件重复加载相同 hooks。

## 4. 启动与迁移研究内容

新建 `.mathprove` 控制器状态；不要把 v8 数据库文件改名冒充 v9。旧成果先作为普通候选/文献/实验材料引入，记录原始来源。新 spec 经审阅锁定后，重新走相应门禁，形式化目标重新验证。旧“成功”标签不自动保留。

安装完成后运行 `doctor`，缺少 Lean/lake 时研究模式仍可工作；形式模式不能改用 LLM 输出顶替验证。Lean 示例锁定 v4.19.0 仅为固定演示输入，不表示建议升级/降级你的现有数学项目；实际项目保留其已经审阅的兼容工具链与 mathlib commit。

## 5. 操作者授权与工作区安全

本地 `review --human-ack` 是你在终端上明确执行的步骤，不应让 agent 自行调用。它不能认证物理操作者；真正 host-only 的授权应在未来同内核档位复用原服务边界。陌生 Lake/依赖代码先审阅，在受控隔离环境里运行；`--allow-build` 不是安全沙箱。

SQLite 状态应放在本地盘。备份需要在线 SQLite backup API，或停止所有写入后连同所需文件一致性备份，不能只复制一个活动数据库漏掉 WAL。公开 ZIP 导出前检查未发表研究与评审备注。

## 6. 回退

合并源码前创建分支、保存现有修改，是最清晰的回退边界。发生兼容问题时，先停止使用 v9 入口，利用 Git 对已提交源码进行受控回退；逐项检查 `.mathprove-v9-overlay-backups` 恢复被覆盖旧文件。不要用不加区分的 clean/reset 删除用户研究数据。

部署层回退使用 `.mathprove-install-backups` 和已审查的宿主配置。卸载本包 handler 时只移除 `statusMessage` 为 `MathProve v9: ...` 且命令指向相应 `mathprove_hook.py` 的条目，保留第三方 hooks。恢复后重新审查 `/hooks`。本 RC 没有自动卸载或旧数据库逆向迁移功能。
