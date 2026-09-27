# 本地验证报告

日期：2026-09-27，Australia/Brisbane。版本：9.0.0-rc1。

## 实际执行

```sh
python -m unittest discover -s tests_v9 -p 'test_*.py' -v
```

**121 项，119 项通过，2 项跳过，0 failures / 0 errors。** 最后一次完整运行报告耗时 10.930 秒。环境为 Linux、Python 3.13.5、SQLite 3.46.1。完整输出见 `test-output.txt`（仅清理终端控制字符与无关 TERM 提示），结构化结果见 `test-results.json`。

这是新实现的测试，不是旧仓库 README 所述测试的重跑。CI 文件提供 Python 3.11/3.12/3.13 矩阵，但本次没有远程执行该矩阵，不能将其当成已经通过的平台。

## 覆盖范围

状态/门禁测试包括：实际多线程竞争领取、并发上限、任务依赖、过期与错误 token、预算、命题变更、任务后继失效、产物变化、证据撤回、反对意见、累计门禁、快照签核失效、检查点截断标记、哈希事件一致性和 JSON 输入边界。

Hooks 测试包括：真实脚本子进程、协议 JSON、无初始化/多 run 情况、有限直接写入拒绝、中性 PreToolUse 不授权、重复事件去重、哈希日志、不无限阻止 Stop，以及压缩/停止检查点。测试事件是 fixture，不是由真正 Codex 生命周期发送。

安装/交付测试包括：第三方 hook 合并、同 group 保留、重复安装幂等、差异备份与回滚、agent TOML 解析、共享模板一致性、带空格子目录启动、覆盖包清单哈希错误/路径越界/符号链接拒绝、旧文件保留和 CLI 错误返回。

Lean 适配器测试包括：目标类型 wrapper、版本/依赖固定、公理输出解析、失败/超时拒绝、源码/日志/二进制/编译物失效、验证器指纹变更，以及最新失败不得沿用旧成功。**这些编译调用使用 mock；通过不等于运行了 Lean kernel。** 另对普通本地进程做了真实超时清理测试。

额外手动 smoke：在临时空格路径创建非形式化演示，五道研究门禁通过；未人工确认时 release 被拒绝；安装后从子目录启动实际 SessionStart handler，返回合法协议 JSON。未创建人工签核，也未声称形式证明成立。

## 两个明确跳过项

`test_native_windows_hook`：没有原生 Windows 环境。`commandWindows` 的编码与转义有静态测试，但宿主和实际 PowerShell 行为未验收。

`test_live_lean_opt_in`：没有 Lean/lake。具备受审环境后可显式执行：

```sh
MATHPROVE_RUN_LEAN_SMOKE=1 python -m unittest discover -s tests_v9 -p 'test_runner.py' -v
```

该开关允许 fixture 执行真实构建，必须由操作者审阅后设置。它不会自动安装 Lean；在缺工具时仍跳过。独立完成该 smoke 后，仍需要在真实锁定 mathlib 项目上做全套端到端验收。

## Hook 微基准

`benchmark-local.json` 来自 `python scripts/benchmark_v9.py --samples 5`，每类事件 5 次冷启动子进程，共四类。中位数约 663–719 ms，样本 p95 约 694–786 ms。这里 p95 在如此小的样本中近似该组最大值；不应外推为服务指标。

这只是本环境脚本/SQLite/进程开销，不是 CoMath/Pi 的对照，不是数学问题完成速度或 token 节省测量。前后工具事件都会触发时有双重开销，实际宿主应继续测量并按需缩小匹配范围。

## RC 尚未关闭的验收项

真实 Codex 发现、信任与事件发送；原生 Windows；真实 Lean/mathlib 回放；完整旧仓库测试及入口迁移；CoMath schema/daemon/host-only 合同；受控环境与传递依赖构建策略；配对数学研究效率基准。这些没有被本地 green tests 代替。
