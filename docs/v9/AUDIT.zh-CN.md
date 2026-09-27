# CoMath / MathProve 源码重点审阅与 RC2 改进报告

2026-09-27 · Australia/Brisbane

## 1. 结论与证据边界

**GitHub 插件已能读取真实源码。本轮结论不再只依赖 README。** CoMath 固定到 `e8e0182823b383cb228802c4d70f3309bf0a698c`，MathProve 固定到 `e4aaf6abec8c05bc5186d635b06b56152442380b`。读取了项目贡献约定、长期研究架构、实际角色注册表、上下文组成路径、operator MCP、部分 worker/证明证据边界，以及旧 v8 核心和部分审计入口。详细逐文件范围在 `SOURCE-COVERAGE.json`；目录树里出现的文件不算已读源码。

容器直接 Git clone 仍因 DNS 失败。因此没有两个完整检出；四个用于复现的原文件通过插件内容落盘，逐字节验证其 Git blob SHA 后才执行。这四个文件是 v8 核心、MoE 路由、其四项测试、CoMath 签名解析器。其他已读源码通过插件审阅，部分大文件只读了明确区间。没有完整私有 QA、完整 Git 历史、完整 proof-kernel 调用链，也没有真实 Lean/Codex/daemon 执行。

判断应分成三层：**确认的局部实现错误**有可重演输入和输出；**集成设计问题**由实际调用链支持但未做宿主端到端运行；**效率优化建议**是待测方案，不能宣称已经提速。RC2 修改了选定 MathProve 文件和适配材料，CoMath 只附单独候选补丁，没有修改远端。

### 对 RC1 的必要修正

第一，不能再把持久化任务、检查点、失败记忆、受控上下文、盲审资料隔离概括成“CoMath 缺少、应新增”。现有设计和源码已经包含这些机制，应该审查和优化其实际消费链。[长期研究架构][C02]、[上下文构建器][C05]、[worker 执行边界][C07] 支持这一判断。

第二，不用 Pi 的同服务方案不是等待重新设计的 HTTP 设想。仓库已经实现可直接复用的 stdio operator MCP，且区分 operator 请求与 host 审批。正确方向是复用它，不是再建立一个拥有证明状态的“兼容服务”。[operator facade][C09]

第三，RC1 的九种 portable 职责不能当作 CoMath 的九个注册 ID。更重要的是，修改 `.pi/agents/*.md` 不会自动改变已读的 durable Codex worker 提示词路径。本轮已替换为真实 profile 绑定和明确接入说明。[注册表][C03]、[context service][C06]、[adapter][C08]

## 2. CoMath 已实现、应保留的关键设计

### 2.1 研究进展与证明权威分离

已读 `worker-execution-host.ts` 不把 provider completed/result_available 当成数学结果接受。它核对 attempt、generation、租约哈希、期限、permit 和 service-owned handle；收尾还关注工具终止及 usage 是否完整。比“模型输出 done 就释放任务”更可靠。此判断来自所读函数，不代表全部 crash/recovery 路径已经运行验证。[C07]

`service-owned-lean-evidence.ts` 的所读部分检查 manifest schema、campaign/claim/candidate、runner、退出码和 authority，并调用 provenance/index/registry/binary-hash 等下游核验。应保留这样的独立证据链，不能为 portable parity 降成布尔值 `lean_passed`。但下游检查器未全部读完，不能由这些调用名推出整链安全性。[C13]

### 2.2 上下文是经校验的任务输入，不是任意聊天记录

`buildContextPack` 要求 formal task 的指定 lock/ledger 引用，核验注册 artifact 的字节哈希和 UTF-8，mandatory 材料超预算时拒绝而不是剪掉假设；blind 模式限制来源类型并去掉普通 charter/失败路线。`buildPrompt` 再确认已提交 materialization、作用域/generation、路径和当前工具集合。这个基础比只写“请阅读共享 Markdown”强得多。[C05] [C06]

因此下一步不是扩大默认上下文，而是减少重复物化成本、改进选材和任务拆分，并对资料独立性做实际宿主测试。

### 2.3 公开快照和完整内部工程不是一回事

`CONTRIBUTING.md` 及 service package 明确说明内部 QA 不在公开产品快照。公开 `test` 脚本只是输出该说明；成功退出不代表跑过任何行为断言。不能断言项目“没有测试”，也不能把它当作用户可复现的回归保障。[C01] [C15]

建议公开一个小型、去私有数据的 conformance 集：命题标识、过期结果、并发更新、取消/进程终止、blind source policy、manifest 绑定和 MCP schema。保留私有研究样本没有问题，但运行协议的关键不变量应能在外部复验。

## 3. CoMath 的确认问题及优先级

### C-P1：签名解析器使用 JavaScript 单词边界，不能正确划定 Lean 名称

定位：`services/comathd/src/proof-kernel/lean/statement-signature.ts:24–27`，`signaturePattern`。[C10]

原逻辑在转义后的名称后拼接 `\b`。独立编译原 TypeScript 模块后，观察如下：

| 查询 theorem_name | 输入输出文本 | 原结果 | 期望 |
|---|---|---|---|
| `t'` | `t' : True` | missing | ok |
| `α` | `α : True` | missing | ok |
| `t₀` | `t₀ : True` | missing | ok |
| `t` | `t' : True` | ok | missing |
| `t` | `t.other : True` | ok | missing |

这些是文本解析测试，没有声称已运行 Lean 编译这些声明。命名习惯会触发误拒，名称前缀还会误认目标；其结果被 statement-equivalence 模块消费，因此值得优先修复。[C11]

补丁改用明确空白/冒号边界，保留可选 universe 后缀，并增加普通、撇号、Unicode、下标、限定名、同名前缀、universe、重复和歧义输入共 13 个回归。独立严格 TypeScript 编译与 Node 用例均通过。**没有证明这是最终 proof-kernel 可绕过漏洞；最终输出还经过别的条件，整链未验证。** 补丁只是修复这个解析辅助层，不替代 Lean elaboration 之后的结构化目标检查。

交付：`review/patches/comath-statement-signature.patch`、`review/comath-signature-regression.cjs`。只供 CoMath 审阅，不自动安装。

### C-P1：角色预设的优化必须作用于真实 worker prompt 路径

定位：`context-service.ts::buildPrompt` → `codex-app-server-adapter.ts::start`；另有 `.pi/agents/formalization.md` 与 `role-templates.ts`。[C04] [C06] [C08] [C14]

已读 durable 路径由 service 组装通用工作指令和经核验 JSON pack，不直接读取 `.pi/agents/*.md` 或调用 `getRoleTemplate` 来拼接其文本。不能据此说“角色完全无效”，因为 context policy 可以供应指令材料；能确认的是：**不存在本次所期望的“改 Pi 模板即自动影响 durable worker”的直接加载关系。**

最小充分改进：共用一份宿主无关研究方法；分别生成适配各 schema 的角色补充；由 host policy 注册版本化 `tool_instructions` artifact，把模板哈希纳入上下文材料与回放来源。盲审版本只能包含获准的通用说明，不能混入原证明或失败路径。接入后验收实际发给模型的 prompt，而不是仅比较 Markdown 文件。

RC2 已实现公共方法、真实九 profile 映射及生成器；**未修改 CoMath context policy、未安装补充模板、未验证其线上效果**。这比把 portable `finish` JSON 或 `.mathprove` 规则直接替换成 `.comath` 更可靠。

### C-P2：已验证上下文的 I/O 与选择策略值得测量优化

`context-pack-builder.ts` 对材料使用注册引用查找、读取、哈希；可选项在判定最终能否装入前已读，lazy 引用也会验证实际内容。该行为有完整性价值，不应简单删除。可见优化点是避免跨上下文反复做相同线性查找与同一不可变 blob 的重复 I/O。[C05]

建议先测冷/热缓存情况下的构建时间、读取字节数、重复校验比例、mandatory overflow 和所选材料命中率。若重复读取占主导，采用请求内 artifact-id/hash 索引及有明确不可变性/失效边界的缓存；保留授权和当次源绑定，不能拿 mtime 代替安全哈希。`byte_cap` 是明确的字节限制，不是精确 token 数；可增加模型 tokenizer 校准，但不要因此放宽 mandatory 假设的保留规则。

这部分是静态源码驱动的性能假设，不是已测出的热点。本次未运行 CoMath 性能基准。

## 4. 旧 MathProve v8：可重演的具体缺口

所有下表观察来自与 Git blob `6f362d40efd0cd2a183f2ceb70889b84d46f7f97` 完全相同的文件。脚本与原始 JSON 位于 `review/reproductions/`；不调用 Lean、不操作用户项目。[M01]

| 问题 | 原始定位 | 最小观察 | RC2 处理 |
|---|---|---|---|
| 混合阶段候选 | `select_candidate`, 303–315 | final_audit 的首候选被 veto，但另一个 skeleton 被选中，decision 仍写 final_audit 并推进 memory_update | 同批必须同 stage、ID 唯一；不合法显式报错 |
| 非法评分输入 | `clamp01`, 200–205 | NaN 被夹成 1.0 | 非有限值返回 0；阈值必须有限且在 [0,1] |
| 依赖图不是 DAG | `validate_line_map`, 403–423 | A→B→A 和未知依赖均返回通过 | 迭代环检测、引用闭包、显式外部依赖、输入形状检查 |
| 字符串假值被当作真 | `termination_allowed`, 432–442 | `"final_audit_approved": "false"` 允许终止 | 只接受字面布尔 true |
| 并行 context 索引丢写 | `write_context_shard`, 333–349 | 受控两次读取在写入前完成：2 个 shard 文件，但只有 1 个索引记录 | 留下确定性复现；未给旧 writer 加新锁协议，改用 v9/daemon |
| 评分材料没有独立证明来源 | `candidate_hard_vetoes`, 253–270 | 不存在的 artifact/log 路径配合布尔字段，也可让评分器选中 | 明确限定为排序建议；不冒充已修成证明 authority |

这里尤其要防止过度推论：旧 `skill/scripts/final_audit.py` 另有真实工具调用，v8 CLI 包装器主要暴露 demo、静态检查、预算和终止辅助。**本次没有复现完整最终发布入口的绕过。** 能确认的是评分器与状态契约不应承担最终证明门禁，名字叫 `GateDecision.accepted` 也不会改变其信任来源。[M04] [M05]

此外，旧 `moe_router_v8.activate` 对 hard/frontier/research、uncertainty 或 repeated_failure 都返回全部 12 个专家，测试还要求百万级本地上下文、两千万级 campaign 目标和至少 24 小时。它们是配置/测试规定，不是实际观测到的花费，更不是困难数学必须满足的规律。RC2 保留旧路径以免破坏未知入口，新 v9 不再采用这些默认要求；旧路由和旧 budget helper 没有一起重构。[M02] [M03]

## 5. 对研究效率真正有价值的改进

### 5.1 先减少重证与重复失败，再增加并行数

OpenAI 的科研案例说明专家负责问题定义、批判与验证，模型能帮助文献连接、候选证明和计算，同时可能错引来源或沿无效路径前进。它们不是针对本工作台的随机对照提速证明。[W04] 因而建议把 librarian 分成“已知定理复用”和“最近先行研究对照”两种工作，不要求每次都开独立 agent。

每个候选路线先给出最小引理接口、缺失前提、已查来源和可以否定该路线的便宜实验。失败记录至少绑定 scope/假设、路线指纹、失败位置、已做检查和重试条件。相同路线再次出队时，必须说明什么变了。这里不是新增另一个 memory store，而是检查 CoMath 已有失败材料是否真正影响调度与 prompt。

### 5.2 并行的单位是不同方法或独立引理，不是人格数量

Anthropic 的研究系统经验强调明确委派、边界和方法选择；这种经验支持对可分解任务并行，但不能把某个 web research 成绩直接换算成数学提速。[W05] Aletheia 的公开摘要描述自然语言生成—验证—修订循环，也不能等同于 Lean kernel 验证。[W07]

对于一个固定接口，可尝试一条结构性证明路线、一条精确低维/边界计算、一条定理复用路线。只有当输出能够相互区分、彼此没有写同一规范文件时才并行。对于强依赖的长证明，优先降低关键路径与集成成本。生成器与反对者分工应有资料可见性差异；同一会话换角色不构成独立复现。

默认少量分支不是研究能力上限。预算足、独立引理多时可以扩展；但扩展理由应是预期新增证据，而不是“frontier 必须 full panel”。

### 5.3 用接口变更驱动失效，而不是用聊天轮次判断进度

未来值得实现一个可测试的 lemma contract：目标命题、导出假设、依赖接口、proof artifact 和证据档位。将接口哈希与证明实现哈希分开；假设或结论变化使下游失效，纯证明实现变化至少重验自身并检查必要依赖绑定。若 Lean 环境里符号/实例改变也影响语义，必须计入环境指纹，不能把文本相同当作语义相同。

这是提出的优化方向，不是本次已对 CoMath 做完的功能。RC2 便携档维持保守失效，不冒进引入未经验证的语义缓存。

### 5.4 让研究者只审批有决策意义的节点

长期 agent 的工程经验强调跨会话可恢复产物和增量工作，而不只是 compaction。[W06] 对你的使用方式，建议把人工节点聚焦在初始研究问题/假设锁、重要 statement repair、候选方向升格与最终结果，而不是每段文字都要求批准。

每个面向人的检查点只展示当前锁定目标、最近新增的可验证进展、最强反对意见、预算/关键路径和下一项需要决定的动作。原始过程留在 artifact/event 中。已有 dashboard/operator API 可承担这个摘要入口，不必再造第二个监控状态库。[C09]

### 5.5 把“正确、忠实、新颖、独立”分开显示

Lean 检查的是指定形式目标在环境内的推导；它不自动证明该目标忠实表达原问题，也不证明未发表过。独立性还依赖实际上下文与人机贡献记录。界面和导出包应分别展示这些状态，不用单个绿色“完成”覆盖全部含义。研究方法模板已按这些边界更新；完整 UI 变化未实施。

## 6. 非 Pi 架构的具体选择

**主建议：保留 Portable-local 与 CoMath-backed 两档，但不要维护两套声称等价的证明权威。**

Portable-local 继续服务零 Pi、零 daemon 的个人项目，依靠本地 SQLite、证据对象和合作式 coordinator。它实现有用的流程纪律，但不能抵抗相同 OS 权限的直接改写，也没有 host-only 身份认证。

CoMath-backed 使用源码已存在的 `createResearchOperatorMcp`。编译入口由原 `tsconfig` 的 src→dist 路径确定，环境变量已在入口实际读取；RC2 的配置生成器校验相应原文件 Git blob 及编译入口存在，只打印符合当前 Codex MCP 文档的配置，默认只开放读取工具。它不创建新服务，不读取令牌，不授予 host ticket，不将本地状态导入 CoMath。[C09] [C16] [W02]

操作者选 `--access operator` 后仍需宿主与服务授权。`research_intake_request_approval` 只能请求审阅，不能自行批准。配置器不保证已有 dist 是刚从该源码构建的，故必须先构建所审检出。真实启动/发现/读写/超时恢复与批准隔离仍为未完成验收。

这条路线提供最接近“一致使用标准”的基础；但“复用同服务”与“本次已测得相同效率、所有宿主行为一致”不同。

## 7. RC2 实施清单与验证

主要修改包含：选定 v8 核心的最小结构修复；v9 版本与 hooks 配置修正；共享数学方法和两套宿主角色生成；真实 CoMath operator 配置器；模式路由；覆盖前旧源码指纹和 Git 未提交路径保护；新回归、复现、源覆盖、迁移及交接文档。正式 Lean runner 和 v9 数据库 schema 未因本轮重构。

Codex hooks 只在实际返回 additional context 的启动事件设置该上限，避免其他事件配置告警；其信任、生命周期和执行仍由宿主负责，本地子进程测试不冒充真实 Codex 验收。[W01]

| 验证对象 | 结果 | 不涵盖 |
|---|---|---|
| 原 RC1 便携测试重跑 | 121 运行，119 通过，2 跳过 | 上游整仓 |
| RC2 测试 | 152 运行，150 通过，2 跳过 | 真实 Lean、原生 Windows、真实 Codex |
| 选定旧 v8 测试 | 原始和修补模块均 4 通过 | 所有旧版本测试/入口兼容 |
| 原始源码问题复现 | 输出保存在 review/reproductions | 最终 audit/kernel 绕过 |
| CoMath 签名补丁 | 独立严格 TS 编译，13 个 Node 回归通过 | 完整 CoMath 构建、真实 Lean 输出 |

测试记录与发布包解压/清单检查以 `TEST-REPORT.md` 为准。没有进行新的数学任务评测；历史 hook 微基准只保存在 archive，不能当作 RC2 加速数据。

## 8. 下一轮验收的最小路线

首先在完整 MathProve 仓库合并这组带指纹的补丁，跑全部旧测试及旧安装/启动路由，排除“双入口、双协议”。随后在完整 CoMath 分支应用单独 parser 补丁，并把 profile 补充接入实际 host context policy；做真实 worker prompt、blind 资料和 result-schema 回归。第三步运行真实 Lean、Codex hooks、operator MCP 与 host 批准链，确认没有把测试夹具的成功误当成部署成功。

完成行为验收后再做效率消融。建议用固定的已知引理、含错误假设的反例题、小型新方向探索三组任务；每组固定模型版本、问题输入和 token/tool/wall-clock 预算，比较原工作流、只改角色方法、只改上下文选择、两者组合。记录首个有效结果耗时、可复用引理数、重复失败占比、人工修补分钟、错误接受率、停止/恢复可靠性和总费用。样本及重复次数应按成本设定，不用一两个成功案例宣布普遍提速。

最终优先级是：**先让真实执行路径的语义和证据可靠，再减少重复计算与人工集成成本，最后才提高并行上限。**

---

## 来源定位

正文引用指向固定提交或一手资料。完整读取区间、原文件哈希及未覆盖项见 `SOURCE-COVERAGE.json` / `SOURCES.md`。技术建议是本次审阅的推论，不是这些机构对本仓库的认证。

[C01]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/CONTRIBUTING.md
[C02]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/docs/architecture/durable-research-orchestration.md
[C03]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/agent-profiles.ts
[C04]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/role-templates.ts
[C05]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/research/context-pack-builder.ts
[C06]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/research/context-service.ts
[C07]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/runtime/worker-execution-host.ts
[C08]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/runtime/codex-app-server-adapter.ts
[C09]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/control/research-mcp-facade.ts
[C10]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/proof-kernel/lean/statement-signature.ts
[C11]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/proof-kernel/lean/statement-equivalence.ts
[C12]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/proof-kernel/lean/statement-diff-gate.ts
[C13]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/proof-kernel/ensemble/service-owned-lean-evidence.ts
[C14]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/.pi/agents/formalization.md
[C15]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/package.json
[C16]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/tsconfig.json
[C17]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/agent-run-scheduler.ts
[C18]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/runtime/codex-api-adapter.ts
[C19]: https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/errors.ts
[M01]: https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/skill/runtime/proof_factory_v8.py
[M02]: https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/skill/runtime/moe_router_v8.py
[M03]: https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/tests/test_proof_factory_v8.py
[M04]: https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/skill/scripts/proof_factory_v8.py
[M05]: https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/skill/scripts/final_audit.py
[M06]: https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/LICENSE
[M07]: https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/MATHPROVE_V7_PATCH_NOTES.md
[W01]: https://developers.openai.com/codex/hooks
[W02]: https://developers.openai.com/codex/mcp
[W03]: https://developers.openai.com/codex/subagents
[W04]: https://openai.com/index/accelerating-science-gpt-5/
[W05]: https://www.anthropic.com/engineering/multi-agent-research-system
[W06]: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
[W07]: https://arxiv.org/abs/2602.10177
