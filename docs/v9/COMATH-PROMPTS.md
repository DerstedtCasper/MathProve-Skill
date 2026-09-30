# 共用研究方法，不混用宿主协议

本次已读取 CoMath `e8e0182823b383cb228802c4d70f3309bf0a698c` 的 `agent-profiles.ts`、`role-templates.ts`、`context-service.ts`、`codex-app-server-adapter.ts` 及 Pi formalization 模板。RC1 的便携角色到 CoMath 的机械替换已停用。

## 两层来源

`skill/assets/v9/research-method.md` 保存可跨宿主复用的数学方法：固定问题接口、最小区分实验、来源核验、失败复用、独立性说明、显式预算和证据分级。

Portable-local 的职责和任务协议来自 `skill/assets/v9/roles/`。CoMath 的专属职责和宿主不变量来自 `skill/runtime_v9/comath_adapter.py`，注册表绑定写在 `integrations/comath/profile-bindings.json`。不要把可移植研究方法与 `.mathprove` 的 CLI/JSON 协议混为一谈。

```sh
python scripts/generate_agents_v9.py
python -m unittest discover -s tests_v9 -p 'test_*.py' -v
```

生成器输出九个 Codex `mp_*` 配置、九个 CoMath profile 补充模板。`integrations/comath/prompts/` 中的旧文件只保留退役提示，避免增量覆盖留下看似可用的旧草稿。

## 源码中的真实九个 CoMath profile

| 注册 ID | role 枚举 | 补充职责重点 |
|---|---|---|
| coordinator | coordinator | 关键路径、预算、幂等 command ID、阶段状态分别报告 |
| librarian | librarian | 原文/定理定位、假设匹配、最近先行研究对照和检索缺口 |
| computation | computation | 特征/维数/域/精度、可重演计算、有限验证边界 |
| proof-route | proof_route | 少量不同方法、精确引理 DAG、失败重试条件 |
| formalization | formalization | 量词/类型/空真、锁定接口、正确 formal_candidate 回执 |
| reviewer | reviewer | 区分审稿/盲复现/翻译审核，保留反对意见及解决条件 |
| graph-builder | graph_builder | 边的含义、闭包/环、接口变更传播，GraphPatch 仅为提案 |
| security-auditor | security_auditor | 授权/路径/进程边界，复现与假设分别陈述 |
| math-integrity-auditor | math_integrity_auditor | 原题—形式命题—回放目标对应，公理/过期证据检查 |

这些不是 portable 九种角色的一一重命名。所有补充模板保持 `proof_authority=none`、`may_mutate_trusted_state=false`。记录的 legacy specialist tool 名仅用于来源追踪，实际 worker 只能使用服务供应的 `allowed_tools`。

## 必须接入实际执行链

Pi 子代理模板与持久化研究 worker 不是同一条 prompt 加载路径。已读 durable 路径是 `daemon-runtime → contextService.buildPrompt → Codex app-server adapter`；`buildPrompt` 不直接读 `.pi/agents/*.md`，而是组合经服务校验的 context pack。因此只修改 Pi 文件不能保证后台 worker 获得新方法。

建议的最小接入是：通过服务当前的上下文配置加载相应 `tool_instructions`，保留实际职责、可见范围和研究预算，不新增源码锁定、内容哈希验收或重复审批。模板若包含原证明或失败线索，不能标记为 blind-safe。使用普通修订编号区分提示词调整。

`role_template`、tool policy、write scope 仍由原服务约束。Pi 的 `child_agent_report`、durable 的 checkpoint/research_result 与 formal_candidate 使用各自 schema，不能复制 portable outcome 字段代替。对普通突破结果仍遵循“非终止候选 + 另行最终结果”；formal_candidate 按其专属回执结束。

**本包没有在 CoMath 实际安装这些补充，也没有改动其 context policy 或 registry。** 这一步必须在完整仓库中与原工具权限测试一起验收，不能只对 Markdown 做快照测试。

## 提示词验收

用一个短 formalization 任务检查实际 prompt 含正确的研究方法、目标陈述及 allowed tools；让 blind reviewer 验证看不到原证明和失败材料；验证报告符合其真实 schema。对新旧模板在相同问题、模型、预算下做配对对照，记录首个有效结果耗时、接口漂移次数、错误接受和人工修补量。更多角色不作为成功指标。
