# RC2 验证报告

日期：2026-09-27（Australia/Brisbane）。环境：Linux / Python 3.13.5 / Node 22；真实 Lean/lake 与 Codex 宿主不可用。版本：MathProve-Skill 9.0.0-rc2。

## Windows 本仓库补充验收（post-RC2）

在 Windows / Python 3.13.7、默认 CP936（非 UTF-8）环境重跑 `python -m unittest discover -s tests_v9 -p 'test_*.py' -v`：**152 项，147 通过，5 跳过，0 失败**。测试夹具改为显式读取 UTF-8 发布文件，并使用 Windows 原生绝对路径验证 MCP 配置；这不改变 v9 协议或运行时行为。

`test_native_windows_hook` 在该环境实际通过。4 个 symlink 拒绝测试因当前账户无创建 symlink 特权而明确跳过，未把无法建立夹具误报为产品失败；`test_live_lean_opt_in` 仍因没有 `lake` 且未设置显式 opt-in 而跳过。此结果不等于 Codex/Snow UI 生命周期、真实 Lean kernel 或 CoMath 服务已经验收。

## 实际执行与范围

| 执行 | 结果 | 证据范围 |
|---|---|---|
| 原 RC1 测试重跑 | 121 项，119 通过，2 跳过，0 失败 | 先建立旧包基线，不是上游测试 |
| RC2 全部 tests_v9 | **152 项，150 通过，2 跳过，0 失败** | 便携运行时、hooks 子进程、安装/覆盖、模板及新增源回归 |
| 原始 v8 对应选定上游测试 | 4 通过 | 仅 `tests/test_proof_factory_v8.py` |
| 修补 v8 对应同四测试 | 4 通过 | 未覆盖其他旧模块/安装入口 |
| 原源码四文件 Git blob 核对 | 全部相符 | 核心、MoE、四测试、CoMath signature parser；非整仓 clone |
| v8 原函数确定性复现 | 输出已留存 | 混合 stage、环/悬空依赖、NaN、字符串 false、索引丢写、合成证据排序 |
| CoMath 签名补丁独立严格 TS 编译 | 通过 | 单文件，不依赖完整 daemon 构建 |
| CoMath 签名补丁 Node 回归 | 13/13 通过 | 文本解析输入，不是 Lean 编译/证明回放 |
| 生成 TOML / profile JSON / Python 编译检查 | 通过 | 静态与生成一致性，不是宿主执行 |
| Git diff 空白检查 | 通过 | 本地 RC1 到 RC2 工作副本；不是 upstream 完整 diff |
| 最终 ZIP 清洁解压后测试 | 同样 152 项，150 通过，2 跳过，0 失败 | 测试的是解压交付物，不依赖开发目录缓存 |
| ZIP / manifest 与覆盖夹具 | 完整性及逐文件哈希核对；预览、应用、备份、保留无关文件 | 夹具含精确原 v8 文件，**不是两个完整仓库上的集成合并** |

没有把几类测试相加称作一个完整系统通过多少项：152 项中已包含部分源回归和配置测试；4 个上游用例与 13 个 CoMath 用例是另外的执行边界。

## 新增 31 项测试主要覆盖

混合阶段/重复候选、合法同阶段选择、非有限分数/非法阈值、循环/悬空/大图及显式外部依赖、布尔值终止；真实 profile ID/role 枚举和宿主独立性、CoMath MCP 工具清单/TOML、安全默认、hook context 参数；覆盖前旧源码指纹、幂等已修补文件、分叉或缺失文件拒绝；真正临时 Git 仓库中的 staged/unstaged/untracked 覆盖保护与无关脏文件保留。

旧 v8 的 JSON context index 双写问题有确定性原函数复现，**并没有在本次把该 writer 改造成多写安全**。合成 `lean_passed` 的评分问题也没有“修成真证明”：评分器的信任边界被明确保留为建议排序，实际正式检查另走验证器。

## 两项跳过

`test_live_lean_opt_in`：没有 Lean/lake，也没有执行受审实际构建，不能宣称 kernel 成功。

`test_native_windows_hook`：交付环境是 Linux；Windows argv/编码分支有生成测试，但不等于真实 Windows PowerShell/Codex 生命周期已跑通。

## 无法从本报告推出的结论

CoMath 全部 proof-kernel / manifest / clean-replay 逻辑可靠；私有 QA 或完整上游构建通过；MCP 已连通真实服务；新 profile 已在 durable worker 中生效；旧 v8 全部调用者兼容；Codex 对生成 hooks 的实际事件触发、信任/权限或 Windows 行为已验收；数学研究速度或成果质量提高某个倍数。这些都需要各自的运行证据。

## 复现命令

在解压的 MathProve 包中：

```sh
python -m unittest discover -s tests_v9 -p 'test_*.py' -v
python scripts/generate_agents_v9.py
python -m compileall -q skill/runtime_v9 skill/runtime/proof_factory_v8.py scripts tests_v9
```

在独立原 MathProve 检出上运行已固定字节的观察脚本：

```sh
python /path/to/MathProve-Skill-v9/review/reproductions/mathprove_v8_observations.py /path/to/original/skill/runtime/proof_factory_v8.py
```

该脚本拒绝被修补后的 v8 文件，防止把不同实现标成原始证据。在完整 CoMath 上单独补丁和行为验收命令见 MIGRATION.zh-CN.md；本次已执行的单文件步骤是 `tsc --target ES2022 --module commonjs --strict` 后，将编译文件路径传给 `review/comath-signature-regression.cjs`。

## 测试材料

`test-output.txt` 是 RC2 开发目录最终代码测试日志；清洁解压重跑日志随交付另附。`test-results.json` 为结构化结果；原源码观察位于 `review/reproductions/`。历史 RC1 日志与微基准只在 `archive/rc1/` 中保留，不作为本轮 CoMath 或数学提速测量。
