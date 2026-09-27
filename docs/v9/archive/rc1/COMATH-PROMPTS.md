# 共源角色模板如何用于两个系统

`skill/assets/v9/roles/` 是唯一编辑源；`scripts/generate_agents_v9.py` 生成 `integrations/codex/agents/` 和 `integrations/comath/prompts/`。修改公共契约或角色后重新生成，运行模板一致性测试，避免两个宿主的提示词逐步漂移。

## 九个职责与必要交付物

| 角色 | 优化目标 | 必须留下的产物 |
|---|---|---|
| coordinator | 选择下一项最高价值工作，控制预算与依赖 | 任务卡、阻塞原因、下一动作、诚实的阶段状态 |
| formalizer | 防止量词/假设/对象漂移与空真 | 形式化对照、假设表、边界实例、反向翻译 |
| strategist | 比较不同路线，拆出可复用引理 | 有精确接口的引理 DAG、关键瓶颈、退出条件 |
| librarian | 先复用而不是先重证，区分来源与猜测 | 查验过的来源、定理/页码/适用假设、检索缺口 |
| prover | 完成一个固定接口，不改题赢门禁 | 候选证明或局部 Lean 产物、剩余义务、失败路径 |
| experimenter | 用最便宜的可重复试验区分路线 | 代码、输入、种子、版本、精确/浮点/有限搜索标签 |
| refuter | 主动打破候选或发现适用域问题 | 可复现反例线索、边界测试、未解决反对意见 |
| integrator | 维护唯一规范成果，发现组合缝隙 | 集成 patch、依赖一致性与回归记录 |
| auditor | 检查声明、证据和未覆盖范围 | 独立性说明、快照审查、不能签核的事项 |

模板刻意不规定模型品牌、固定人格、无限工作量或“必须找到证明”。已有反例应升级为问题，而非改写原命题后保持原签核。没有真正子代理时允许顺序 pass，但不能称为独立共识。Codex 中 coordinator 通常由父会话承担，不再额外派一个 coordinator。

## 对 CoMath 的适配边界

`integrations/comath/prompts/*.md` 是**待审核的人工移植草稿**，不是已经安装或通过 Pi registry 校验的预设。本次没有取得 CoMath 真实 agent 注册表、prompt composition、工具 schema、schema enum 或测试，因此没有编造对应注册 ID 或自动 patch。

保留 CoMath 原有系统级约束和原生工具契约，逐项映射角色名称。公共规范中的任务/门禁/证据概念只能映射到实际存在的 daemon 操作；不能把 `.mathprove` 的 SQLite 实现塞进 `.comath`，不能允许模型直接写 `.comath`，不能把本地 `--human-ack` 替代 host-only 操作。公共模板不应覆盖现有 proof-kernel、StatementDiffGate、不可越权的宿主指令。

推荐先移植 formalizer/refuter/integrator 三个窄职责模板，用已有真实回归任务比较其输出合同，再扩展所有角色。将角色的“可以做什么”交给实际工具权限，将“应该怎样报告”交给提示词。read-only/盲审需要宿主执行，提示词本身不是隔离。

## 建议统一但尚未实现的跨宿主合同

后续可将 `task / result / evidence / review-request` 建成版本化中立 schema，由两个宿主适配。必须包含 run、task、spec hash、接口版本、证据类型、产物引用、未决义务和信任档位。不同 trust profile 的证据只能降级导入，不能直接相互转换最终成功状态。等真实 CoMath schema 可审阅后再写迁移器和双向契约测试。
