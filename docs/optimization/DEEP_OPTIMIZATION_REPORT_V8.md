# MathProve Ultra v8 深度优化研究报告

## 结论

v8 的核心优化是把 MathProve 从“MAGI + SymPy + Lean 的逐步验证器”升级为“长程 proof factory”。它面向 24h+、1M+ 有效上下文、10M-20M+ 全局工作量的研究级自动形式化证明任务，通过文件化上下文湖、阶段门控、多智能体候选包、证据加权选择、MoE 专家路由、proof-memory graph 和最终审计来扩展单个 LLM 的上下文与可靠性。

## 源码审计摘要

上传源码已经包含很好的工程骨架：`runtime/orchestrator.py`、`proof_tree.py`、`parallel_runner.py`、`safe_verify.py`、`final_audit.py`、MAGI protocol、SOP 文档和测试目录。v8 没有推翻这些结构，而是在 skill 层与 runtime 辅助层上增强：

- 原有 step loop 升级为 10 个 stage gates。
- 原有 parallel runner 的“竞速”思想升级为 stage-local candidate packs + evidence-weighted gate。
- 原有 final audit 继续保留，但增加前置 theorem drift、quota、context-lake、proof-memory 和 non-skeleton sorry veto。
- 原有 MAGI 三角色不再只做阶段 C 的前置投票，而成为多专家 task-card/candidate-pack 协作框架的一部分。

## 前沿研究吸收

1. **AlphaProof / Lean RL environment**：把证明看成 Lean state 上的 sequential decision process；MathProve v8 因此把每个 gate 的候选与日志当成可回放 trajectory，而不是自然语言承诺。
2. **DeepSeek-Prover-V2**：递归子目标分解 + informal/formal reasoning 结合；v8 将其落地为 theorem variants、lemma DAG、leaf-lemma sprint、upward integration。
3. **BFS-Prover-V2**：planner-enhanced multi-agent tree search；v8 加入 stage-local parallel candidate packs、shared proof memory、quota-based anti-laziness gate。
4. **Kimina-Prover**：reasoning-driven exploration 与 verifier feedback；v8 允许深推理探索，但只把 verifier-backed artifact 晋升。
5. **AXLE/AxiomProver**：proof verification/manipulation primitives 是基础设施；v8 将 replay logs、dependency profile、audit JSON 视作 proof object 的组成部分。
6. **Gauss / Sphere Packing**：大规模自动形式化的真正难点包括 blueprint、并行、refactor、integration、maintainability；v8 因此增加 integration/refactor/golf gate 与 proof memory update gate。
7. **Tao-style formalization workflow**：先定义符号，再写 skeleton，再 line-map，再逐 lemma 证明；v8 将其变成默认形式化流程。

## v8 新增机制

### 1. Long-horizon budget contract

- frontier/research 模式默认 `local_context_target_tokens=1_000_000`。
- 全局 campaign target 可达 `20_000_000` tokens 级别。
- hard/frontier theorem 默认允许 24h+。
- 本地上下文耗尽不是终止条件，必须 externalize-and-continue。

### 2. Context lake

新增 `context_lake/index.json` 和 shards/handoff capsules。每个阶段把关键上下文写入文件，用短 summary 保持可检索性，用 stable ID 维持跨 agent 续跑。

### 3. MoE expert router

默认按 stage 激活相关专家；frontier/research/repeated-failure/high-uncertainty 激活 full panel：Formalizer、Skeletonist、LineMapper、TacticSprinter、WholeProofProposer、Librarian、AlgebraicVerifier、Refuter、Repairer、Integrator、Auditor、DomainExpert。

### 4. Evidence-weighted promotion

候选不是按多数票晋升，而是按：

- kernel/tool verification
- dependency closure
- refutation coverage
- evidence completeness
- maintainability
- restartability
- novelty
- cost sanity

并受 hard veto 约束。

### 5. Frontier quota veto

在 research/frontier 模式下，候选需要满足当前 stage 的最小工作量记录，例如 lemma_sprint 至少要有 candidate pack；否则会触发 `quota_not_met`，防止 agent 快速给出漂亮但偷懒的结论。

### 6. Theorem statement drift guard

每个候选可带 `expected_statement_hash` 与 `theorem_statement_hash`。如果证明过程中悄悄改了定理陈述而没有记录，直接 veto。

### 7. Proof memory graph

用 `defines / uses / proves / fails_by / repairs / generalizes / specializes / refutes / renames / supersedes / depends_on` 记录可复用知识，而不是堆积聊天记录。

## 伪测试结果

`mathprove_v8_pseudotest.py` 共 9 项全部通过：

1. evidence-weighted selection: 有 Lean 日志的候选胜过漂亮无证据草稿。
2. statement drift veto: 定理陈述 hash 不一致会被拒绝。
3. skeleton sorry only: skeleton 可含 sorry，final audit 禁止。
4. line map guard: 检测缺失 obligation 与 self dependency。
5. budget contract frontier: 验证 1M/20M/24h 合同存在。
6. no premature termination: local context exhausted 不是终止条件。
7. MoE full-panel escalation: frontier 模式激活全专家面板。
8. context lake and memory roundtrip: shard + proof memory 可写可读。
9. frontier quota veto: 未满足 stage quota 会被拒绝。

## 与 v7 相比的提升

- v7 已经有 stage gates 与 proof factory；v8 增加了更明确的 frontier budget contract、termination gate、context-lake shard API、theorem drift hash、quota veto 和 full MoE router。
- v7 更像“强协议”；v8 更像“可长跑的证明工程系统”。
- v8 对“无 token/time 上限”的解释更严格：不是无限思维链，而是无限可恢复工作单元。

## 建议落地顺序

1. 先安装 `mathprove_ultra_v8_skill.zip` 做 skill 层替换。
2. 再将 `MathProve-Skill-ultra-v8-source.zip` 合并到 GitHub 仓库分支。
3. 运行 `skill/scripts/mathprove_v8_pseudotest.py`。
4. 再跑原仓库 pytest；若环境中 Lean 不可用，先保留 blocked-by-environment 日志。
5. 用一个小 Lean 定理做端到端演练：notation -> skeleton -> line_map -> lemma_sprint -> final_audit。
6. 再迁移到你自己的 braid/YBE/representation theory 研究命题。
