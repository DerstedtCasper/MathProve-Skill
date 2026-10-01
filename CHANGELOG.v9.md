# 9.1.0 — 2026-10-01

## TriviumDB 研究数据库

- 增加真实 TriviumDB 适配器及 `db-init`、`db-put`、`db-get`、`db-query`、`db-link` 命令，存储研究记录、用户向量及其关系；SQLite 保留任务、租约、会话和流程状态。
- 依赖声明使用不带版本条件的 `triviumdb`，支持当前本地源码安装；`doctor` 报告实际可用性、版本及初始化状态，不设置版本或提交锁定。
- 增加持久化重新打开、维度校验、有限 JSON、跨任务隔离、关系和 CLI 错误回归；持续集成增加 Python 3.12 原生数据库测试任务。数据库记录不自动参与证明验收。

## 本地执行规则澄清

- 明确本地执行是默认且被允许的方式，覆盖数学计算、Python 脚本和 Lean／Lake；不要求 Docker、Podman、虚拟机或容器沙盒作为前置条件。
- 缺少工具时报告具体本地依赖；旧 Docker 执行器仅在用户主动选择时使用，宿主既有权限保持不变。
- 增加三个技能入口的规则回归与含空格工作目录的真实 Python 子进程测试，模拟验证器断言仅发现 `lake`。现有 Lean 验证器、精确目标类型、实际编译结果与公理依赖检查保持不变。

## 数学研究工作台

- 以数学问题、引理探索、反例、文献复用和可恢复笔记为中心；简单任务不强制创建数据库或执行六阶段流程。
- 使用最新互相兼容的 Lean／mathlib，在实际 Lake 项目中构建并复用缓存。取消固定版本、依赖提交锁定、冷重建及重复构建授权。
- 取消文件、依赖、可执行程序、日志、研究产物和事件链的哈希验收；目标与证据改用普通修订编号和对象编号，保留旧数据库字段兼容。
- 正常编辑笔记或引理产物不再触发哈希过期阻断。数学含义变化时重新登记结论或撤回旧结论，历史记录不是对修改后证明的自动验证。
- 数学审阅不再要求额外人工签核；检查点保存失败只提示，不阻止停止或暂停。
- 保留目标与假设核对、精确 Lean 类型、实际编译、公理依赖和未解决反例；`sorryAx`、额外公理和失败编译不作为完成证明。
- 覆盖清单改用文件路径列表，CoMath 配置不再要求历史源码指纹。角色说明、模板、示例及回归测试同步调整。

验证结果见 `docs/v9/TEST-REPORT.md`。以下 RC2／RC1 条目是历史记录，其固定版本、哈希和审批流程不适用于 9.1。

---

# 9.0.0-rc2 — 2026-09-27

## Snow host integration — 2026-09-28

- Added a Snow CLI/App hook adapter for the seven v9 lifecycle events Snow exposes. It translates Snow tool/session fields and host-specific exit codes while reusing the v9 controller.
- Added an installer that merges global Snow CLI hook files and Snow App hook settings, retains unrelated rules, backs up the App database, and supports dry-run/idempotent reapplication.
- Snow hooks activate controller behavior only in an initialized `.mathprove` research workspace. Actual Snow UI/model sessions and Lean verification remain separate acceptance checks.

Source-informed follow-up to the independent RC1 overlay. CoMath is pinned to e8e0182823b383cb228802c4d70f3309bf0a698c; MathProve to e4aaf6abec8c05bc5186d635b06b56152442380b. GitHub source reads succeeded; no full clones, full upstream builds or remote changes.

## Fixed

- Selected legacy v8 helper: reject mixed-stage/duplicate candidates and invalid thresholds; normalize nonfinite scores to zero; validate closed line-map DAGs with explicitly named external prerequisites; accept only literal true termination flags. These remain structural/ranking helpers, not proof certification.
- Repository overlay now refuses divergent pinned legacy source and touched dirty Git paths before writes; unrelated local changes remain untouched.
- Only actual context-emitting startup hook handlers receive additionalContextLimit, avoiding irrelevant event configuration.
- Retired the RC1 generic CoMath adaptations, whose portable role names and contracts did not match the actual registry and durable prompt path.
- Windows test fixtures now read UTF-8 release artifacts explicitly, use native absolute paths for MCP configuration, and skip symlink cases only when the current account cannot create them. This is test-harness portability only; it does not change the v9 protocol or runtime semantics.
- Repository text checkouts now use LF through `.gitattributes`, so the content-addressed v9 overlay remains reproducible when Windows Git has `core.autocrlf` enabled.

## Added

- Shared host-neutral mathematical research method and nine source-bound CoMath profile supplements, generated alongside nine portable Codex presets.
- A source-checked configuration renderer for the EXISTING CoMath operator MCP; default read-only tool allowlist, environment-only credential names, no network/process/config mutation.
- Explicit portable versus CoMath-backed skill routing and parity/installation documentation.
- 31 additional conformance tests; selected original-source reproductions, a separate one-line CoMath signature-boundary patch and 13 standalone regression cases.
- Current source-coverage/test/review records; RC1 evidence retained only under docs/v9/archive/rc1.

## Still not provided

Live Codex/CoMath integration, real Lean execution, full Codex/Snow UI lifecycle validation, full original test suites, automatic legacy state migration, installed CoMath prompt supplements, a full replay-chain security audit, or measured mathematical speedup. The legacy JSON context writer remains single-writer only in practice; use v9 or the existing daemon for multiworker research.

---

# 9.0.0-rc1 — 2026-09-27

Independent, additive portable-controller release candidate. Not a full upstream checkout or v8 database migration.

## Added

- Standard-library SQLite/WAL research state, current statement hashes, event history and bounded checkpoints.
- Dependency-aware tasks, attempt budgets, atomic leases, heartbeats, expired-task recovery, descendant invalidation and result/artifact checks.
- Content-addressed evidence with origin freshness, non-destructive withdrawal and adverse-issue resolution.
- Six cumulative gates and snapshot-bound local operator review with explicit trust limitations.
- Explicit constrained Lean replay adapter: version/manifest checks, random exact-type audit theorem, axiom allowlist, current source/toolchain/artifact bindings. Mocked locally; real Lean smoke remains opt-in and was skipped.
- Nine shared role contracts, generated native Codex agent TOML files, draft CoMath adaptations, evidence schemas and unapproved starter templates.
- Nine native Codex command hook handlers with bounded context, checkpoints, limited guardrails and hashed event metadata. No LLM/compile in hooks.
- Non-destructive project installer, idempotent native hook merge, backup/rollback and manifest-bound repository overlay helper.
- Public deterministic conformance tests, elementary research demo, hook-overhead microbenchmark and local-test CI configuration.

## Deliberate changes from the observed old entrypoint

No fixed million-token context target; no infinite stop prevention; no independent-agent fiction; no promotion of experiments or a reviewed informal argument into a Lean certificate. No automatic tool installation, model launch, human self-signoff or legacy-state trust.

## Not included

A verified CoMath daemon adapter, Pi extension changes, authenticated host-only approvals, OS-enforced worker isolation, hermetic transitive-dependency rebuilding, model billing enforcement, novelty guarantees, a measured mathematical productivity gain, or full legacy compatibility.
