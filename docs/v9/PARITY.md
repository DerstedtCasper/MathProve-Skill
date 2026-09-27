# 两种非 Pi 部署的能力边界

依据固定提交的实际源码读取，而不是把 README 描述视为运行验证。CoMath：`e8e0182823b383cb228802c4d70f3309bf0a698c`；MathProve：`e4aaf6abec8c05bc5186d635b06b56152442380b`。完整审计覆盖见 `SOURCE-COVERAGE.json`。

| 能力 | Portable-local（本包） | CoMath-backed（现有服务 + operator MCP） |
|---|---|---|
| 共用研究状态 | 本地 SQLite/WAL 与内容对象 | 复用同一 CoMath campaign、检查点、artifact 和事件，不做镜像 |
| 任务与失效 | v9 租约、依赖、产物哈希、保守后继失效 | 原服务的 generation、grant、调度、预算、回收逻辑 |
| 阶段门禁 | 六道累计本地门禁，独立 schema | 原服务的研究/正式 intake 和 proof-kernel 流程；不是本地六阶段枚举 |
| 人工批准 | cooperative `--human-ack`，不能认证操作者 | 原有 host-only 确认通道；operator 只能请求批准 |
| Worker 权限 | 依赖宿主 sandbox 与合作式目录约定 | 已读源码会校验 scope/generation/lease；实际隔离依赖部署，尚未实测 |
| 最终形式结果 | 实现了受限 Lean 适配器，但本环境只做 mock 测试 | 沿用服务-owned manifest / provenance / replay；未完成其整链审计或运行 |
| 角色模板 | 九个便携职责，已生成 Codex TOML | 九个真实 registry profile 补充模板；尚未接入实际 prompt composition |
| Hook | 项目原生 Codex hooks，子进程协议测试 | hooks 不替代服务状态；本模式不要初始化影子 SQLite |
| 安装体验 | 项目安装器和独立 CLI | 新增源指纹校验的 MCP 配置生成器；服务部署仍使用 CoMath 本身 |
| 强保证与性能 | 不等价于 daemon；无数学生产率对照数据 | 复用同一实现有助减少分叉，但尚未完成端到端等价验收 |

## 不应相互转换的东西

本地 `reviewed_formal_local` 不等于 CoMath 正式状态；服务的候选验证也不等于数学新颖性。跨模式导入只作为带来源的候选材料，再由目标模式重新验证。MCP tool 返回成功、模型回合结束、artifact 上传成功和证明成立是不同事件。

## 现在推荐的产品关系

Portable-local 是轻量降配档，不是另一个 `comathd` 的宣称等价实现。CoMath-backed 是非 Pi 环境追求同一服务标准的首选接入路线；仓库已实现 `createResearchOperatorMcp` 和 stdio 启动，不需要再造一层拥有证明状态的代理。本次仅生成配置并做静态/单元契约验证，不宣称已经连通真实服务。

不要为获得“统一界面”让模型拿到 host ticket 或 worker lease。统一的是用户概念、任务内容和可追踪来源，不是抹去不同层级的授权边界。
