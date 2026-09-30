# Snow CLI / Snow App Hook 适配

本适配复用 MathProve v9 控制器，映射 Snow 的 `onSessionStart`、`beforeToolCall`、`afterToolCall`、`beforeCompress`、`beforeSubAgentStart`、`onSubAgentComplete`、`onStop`。Snow 没有对应的 `PostCompact` / `SessionEnd` 事件，因此不伪造这两个回调。Hook 只在当前目录或祖先目录存在 `.mathprove/state.sqlite3` 时处理研究状态；子目录调用可找到同一个研究根。

Snow 的 `toolName/args` 转为控制器的工具输入。CLI 的 `beforeToolCall` 以退出码 1 拒绝直接破坏控制器存储的写入，并让会话继续；Snow App 以退出码 2 阻断。普通笔记修改和数学审阅不需要额外签核；检查点保存失败只提示，不阻止停止。无拦截时返回 0，不授予工具权限。会话上下文只返回有界状态摘要，不注入研究正文。Hook 不运行模型、编译或自动安装依赖。

安装器分别维护 `~/.snow/hooks/<event>.json` 与 Snow App 数据库中的 `hooks_global`，通过描述标记只更新本技能规则。它保留其他规则，写入前通过 SQLite backup API 保存数据库。Snow App 中非空项目规则会覆盖同类全局规则；如项目已设置同类 Hook，需在该项目的 Hooks 设置中确认实际生效规则。

Windows 示例（先将 `skill/runtime_v9/snow_hooks.py` 与 `skill/scripts/mathprove_snow_hook.py` 部署至 `~/.snow/skills/mathprove-skill`）：

```powershell
python scripts/install_snow_hooks.py --cli-dir "$env:USERPROFILE\.snow\hooks" --app-db "$env:USERPROFILE\.snowapp\snowapp.db" --skill-root "$env:USERPROFILE\.snow\skills\mathprove-skill" --backup-dir "$env:USERPROFILE\.snow\hook-backups\mathprove-v9" --python "C:\Python313\python.exe"
python scripts/install_snow_hooks.py --cli-dir "$env:USERPROFILE\.snow\hooks" --app-db "$env:USERPROFILE\.snowapp\snowapp.db" --skill-root "$env:USERPROFILE\.snow\skills\mathprove-skill" --backup-dir "$env:USERPROFILE\.snow\hook-backups\mathprove-v9" --python "C:\Python313\python.exe" --apply
```

请按本机 Python 路径替换示例的 `--python`。安装后检查七个 CLI JSON 与 App `hooks_global`；用显式绑定的临时研究 run 验证会话摘要、工具拒绝和检查点。CLI 手工修改 Hook 文件后需启动新会话；App 数据库规则由运行时读取。单独的命令冒烟不等于真实 Snow 会话中的触发验收。
