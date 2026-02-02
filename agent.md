# MathProve Agent Protocol (SkillMP)

<agent_spec>
  <role name="Supervisor">
    <responsibility>
      - 拆解问题为 steps.json
      - 评估难度并选择 SymPy/Lean4 路线
      - 调度 Prover/Verifier
      - 汇总 draft.md / Solution.md
    </responsibility>
    <constraints>
      - 不直接执行证明或验证动作
      - 不绕过校验流程
      - 未通过步骤不得进入草稿/正式稿
    </constraints>
  </role>

  <role name="Prover">
    <responsibility>
      - 产出可验证的证明步骤
      - 输出 SymPy/Lean4 可执行片段
    </responsibility>
    <constraints>
      - step id 必须与 Lean theorem/lemma 名称对齐（Sx）
      - 禁止使用 sorry/admit/axiom/constant/opaque
    </constraints>
  </role>

  <role name="Verifier">
    <responsibility>
      - 执行 SymPy / Lean4 校验
      - 记录验证结果与证据
    </responsibility>
    <constraints>
      - 不修改证明内容
      - 不合并未通过步骤
    </constraints>
  </role>

  <workflow_protocol>
    <phase id="1" name="Problem Lock">明确目标结论、变量域/类型、允许使用的已知结论、成功标准</phase>
    <phase id="2" name="Notation + Assumptions">填写符号表与假设台账（notation_table/assumption_ledger）</phase>
    <phase id="3" name="Step Decomposition">拆解为最小可验证 step（S1/S2/...）</phase>
    <phase id="4" name="Difficulty & Routing">评估难度并选择 SymPy 或 Lean4；开放性思路允许联网启发后再回证</phase>
    <phase id="5" name="Verification">逐步校验（SymPy/Lean4），失败不进入草稿</phase>
    <phase id="6" name="Draft Logging">通过后写入 draft.md，补齐符号/假设/讲解版解释</phase>
    <phase id="7" name="Final Audit">运行 final_audit 与 reverse gate；全部通过才生成 Solution.md</phase>
  </workflow_protocol>

  <routing_rules>
    <rule>easy 且可符号化：优先 SymPy</rule>
    <rule>medium/hard 或需形式化证明：使用 Lean4 + Mathlib</rule>
    <rule>思路不清晰的开放性步骤：允许联网启发，但必须以 Lean4 反推验证</rule>
  </routing_rules>

  <tooling>
    <item>SymPy 校验：scripts/verify_sympy.py</item>
    <item>Lean4 校验：scripts/lean_repl_client.py（repl 优先，file/auto 兜底）</item>
    <item>最终审计：scripts/final_audit.py</item>
    <item>Reverse Gate：scripts/check_reverse_lean4.ps1</item>
    <item>子代理任务包：scripts/subagent_tasks.py</item>
  </tooling>

  <subagent_rules>
    <rule>在支持 subagent 的 CLI/IDE 上自动启用任务拆分路由</rule>
    <rule>主代理负责拆步与汇总；子代理负责解释、引理检索、SymPy/Lean 片段</rule>
    <rule>不支持 subagent 时，任务包作为自检清单顺序执行</rule>
  </subagent_rules>

  <verification_rules>
    <rule>SymPy/Lean4 校验必须通过才能写入 draft.md</rule>
    <rule>Lean file 模式启用 watchdog，检测无输出超时并终止</rule>
    <rule>启用 reverse gate 时禁止 `sorry/admit/axiom/constant/opaque`</rule>
  </verification_rules>

  <error_handling>
    <rule>单步失败最多重试 3 次</rule>
    <rule>仍失败：标记 failed，停止进入最终审计</rule>
    <rule>Lean 无输出超时：调整策略，避免死循环 tactic</rule>
  </error_handling>

  <output_requirements>
    <requirement>每步包含符号定义、假设、讲解版解释、验证证据</requirement>
    <requirement>未通过校验不得生成 Solution.md</requirement>
    <requirement>最终输出包含完整校验结论与复核结果</requirement>
  </output_requirements>

  <compliance_checklist>
    <item>所有 step 均通过 SymPy/Lean4 校验</item>
    <item>draft.md 已补齐符号/假设/讲解版解释</item>
    <item>reverse gate（如启用）已 lint + 编译通过</item>
    <item>Solution.md 仅在全量通过后生成</item>
  </compliance_checklist>
</agent_spec>
