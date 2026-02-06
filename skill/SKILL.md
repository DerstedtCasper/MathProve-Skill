---
name: mathprove-skill
description: |
  面向复杂数学证明/推导/等价变形的“分步-工具验证-形式化门控”技能。强制以步骤为单位执行：
  (1) 每个 step 先触发 MAGI 并行共识决策（讨论方案与风险）；
  (2) 再进入 SymPy 与 Lean4 的函数级验证；
  (3) 只有当 MAGI=APPROVED 且 SymPy&Lean4 均通过并附带可复核证据时，才允许把该 step 写入草稿并进入下一个 step；
  (4) 最终通过 final_audit 生成审计报告与 Solution.md。
metadata:
  version: 0.5.0
  triggers:
    - "证明"
    - "形式化验证"
    - "Lean4"
    - "SymPy"
    - "推导"
    - "等价变形"
    - "prove"
    - "formalize"
  tags:
    - math
    - theorem-proving
    - sympy
    - lean4
    - verification
    - magi
---

# MathProve Skill

本技能不是“回答数学题”，而是“把证明当成一个可执行、可复核的软件流水线”。你必须把每个结论绑定到可复核的物理证据（脚本输出、编译日志、投票结果）。

你必须假设：LLM 会偷懒、会跳步、会把“我想对了”当成“我证明了”。因此，本技能用硬性工序约束你：先决策、后验证、再落盘、最后审计。

---

## 0. 非谈判硬规则（MUST）

0.1 目录写入边界  
- 你只能在 `WORKSPACE/` 下读写本次运行的产物。  
- 严禁在 skill 包目录内写入任何 logs、draft、临时文件（避免上下文污染与路径误判）。  
- “logs 目录”必须在 workspace 内：`WORKSPACE/logs/...`。

0.2 不得“角色扮演”实现多智能体  
- 你不得在主线程里假装自己分别是 Melchior / Balthasar / Casper。  
- MAGI 的并行与隔离必须通过脚本 `scripts/magi_plan.py` 实现；你只负责调用脚本并解析其结构化输出。

0.3 只有“通过且带证据”的 step 才能写入草稿  
- 写入草稿（draft）是一个显式文件写入动作，不是“脑内认为写了”。  
- 只有当以下条件同时满足，`step.status` 才能标为 `passed`，且才允许落盘进入 draft：  
  (A) `magi.status == APPROVED`（该 step 的方案共识已通过，且无致命风险未处理）  
  (B) SymPy 验证通过（脚本退出码=0，且输出满足本技能规定的 PASS 标记/断言）  
  (C) Lean4 验证通过（编译/检查退出码=0，且日志中无 error）  
  (D) 证据包齐全（见“证据包 Evidence Pack”小节）

0.4 不得输出“已证明/证毕”式结论，除非 final_audit 通过  
- 在 `final_audit.py` 输出 `APPROVED` 之前，你对用户只能说“当前进度/尚在验证/某步失败原因”，不得宣称完整证明成立。

0.5 所有动作必须可复核  
- 每一次工具调用（SymPy、Lean4、MAGI）都必须把：命令、输入文件、输出日志、退出码，写入 workspace 下的可追踪文件。

---

## 1. 工作区契约（Workspace Contract）

你每次执行该技能，必须创建一个独立 run 目录，避免不同任务互相污染。

推荐结构（可执行、可审计、可扩展）：

WORKSPACE/
  runs/
    <run_id>/
      problem.md
      assumptions.md
      manifest.json
      status.json
      plan/
        steps.json
        steps_readme.md
      magi/
        plan_vote.json
        step_001_vote.json
        step_001_revision_01_vote.json
        ...
      sympy/
        step_001_check.py
        step_001_out.txt
        ...
      lean/
        Step001.lean
        step_001_lean.log
        ...
      draft/
        proof_draft.md
        step_001.md
        step_002.md
        ...
      evidence/
        step_001_evidence.json
        step_002_evidence.json
        ...
      audit/
        audit.json
        Solution.md
        FAILURE_REPORT.md
      logs/
        init_check.log
        tool_calls.log
        errors.log

run_id 建议：`YYYYMMDD_HHMMSS_<short_hash>`。

---

## 2. 强制流程总览（MUST Pipeline）

你必须严格按顺序执行，任何缺失都视为失败。

阶段 A：预检与初始化  
1) 执行 `scripts/check_routes.py`  
2) 创建 run 工作区结构与初始 `manifest.json / status.json`  
3) 写入 `problem.md`（完整复刻用户命题）与 `assumptions.md`（默认假设与符号约定）

阶段 B：全局规划（仅做步骤草案，不做证明）  
4) 调用 `scripts/magi_plan.py` 生成 `plan/steps.json`（步骤草案 + 每步预期证据）  
5) 对 `steps.json` 做结构校验（字段齐全、步骤可执行、证据可产生）

阶段 C：逐步循环（核心）  
对每个 step i，按以下顺序循环执行：  
6) Step i 方案拟定（proposal）  
7) 触发 MAGI：对 Step i 的方案进行并行讨论与共识决策（必须在验证之前）  
8) 若 MAGI=APPROVED：进入函数级验证（SymPy -> Lean4）  
9) 若 SymPy&Lean4 都通过：生成证据包并写入 `draft/step_i.md`，再 append 到 `draft/proof_draft.md`  
10) 更新 `status.json`，进入下一步  
11) 若任何环节失败：按错误恢复协议处理（可重试，但不得跳过）

阶段 D：终局审计与输出  
12) 执行 `scripts/final_audit.py` 生成 `audit/audit.json` 与 `audit/Solution.md`  
13) 只有当 audit=APPROVED 才允许向用户输出最终证明摘要

---

## 3. 输入/输出与文件格式（你必须遵守）

### 3.1 problem.md（必须写入）
内容必须包含：  
- 原始命题（最好含 LaTeX）  
- 已知条件、变量域、目标结论  
- 任何用户隐含约束（如“在实数域”“x>0”）

### 3.2 assumptions.md（必须写入）
当用户未明确说明时，你必须写出默认假设，并在后续验证中严格使用：  
- 变量类型与域（ℝ/ℂ/ℕ/有序域/度量空间等）  
- 函数可微/连续等正则性假设  
- 分母非零、对数自变量正等域限制  
- 你选择的证明风格（代数化简/构造/归纳/反证/微积分/线性代数等）

### 3.3 plan/steps.json（必须由 magi_plan 生成并被你校验）
每个 step 必须是“原子化、可验证”的最小单元。禁止“大跃迁”。

最小 schema（必须有这些字段）：
- id: "step_001"
- title: 简述
- claim: 本步要证明/推出的陈述（可含 LaTeX）
- inputs: 依赖的前置结论（step id 列表）
- method: 计划采用的验证方式（sympy/lean/both）
- sympy:
    required: true/false
    check_goal: 需要验证的等式/化简/求导/积分/解方程等目标描述
- lean:
    required: true/false
    theorem_goal: 形式化要点（自然语言即可，但必须足够精确）
- evidence_required: 该步落盘必须具备的证据列表（例如：sympy_out, lean_log, magi_vote）
- risks: 潜在陷阱（域限制、可逆性、隐含条件等）
- accept_criteria: 明确的“通过判据”（字符串列表）

你必须在 `plan/steps_readme.md` 里写明：该 steps.json 的整体证明策略与为何这样拆分。

---

## 4. MAGI：每步决策机制（必须在验证之前触发）

### 4.1 何时触发（MUST）
- 在进入每个 step 的 SymPy/Lean 验证前，必须触发 MAGI：讨论该 step 是否合理、是否缺少域条件、是否有更稳健的推导方式、该 step 的可验证性是否足够。

### 4.2 输入（你需要准备）
对 Step i 的 MAGI 输入必须包含：  
- step.claim（本步要得到什么）  
- step.inputs（依赖了哪些前置步骤）  
- 你拟定的“本步证明思路”（proposal，必须写入文件）  
- step.risks（如果steps.json里有）  
- 当前 assumptions.md 的相关约束

将这些内容写入：`draft/step_XXX_proposal.md`（或同等路径），然后把该路径传给 MAGI 脚本。

### 4.3 调用方式（示例，具体参数以脚本实现为准）
```bash
python scripts/magi_plan.py \
  --mode step_decide \
  --run_dir WORKSPACE/runs/<run_id> \
  --step_id step_001 \
  --proposal draft/step_001_proposal.md \
  --assumptions assumptions.md \
  --steps plan/steps.json \
  --out magi/step_001_vote.json
```

### 4.4 输出要求（你必须解析并执行）

`magi/step_001_vote.json` 最少包含：

* status: "APPROVED" | "REJECTED"
* votes:
  melchior: { vote: PASS/FAIL, reasons: [...] }
  balthasar: { vote: PASS/FAIL, reasons: [...] }
  casper: { vote: PASS/FAIL, reasons: [...] }
* required_changes: 若 REJECTED，列出必须修改的点（结构化列表）
* hazards: 本步的关键风险清单（域、等价变形条件、不可逆操作等）
* acceptance: 明确说明“什么条件下可进入工具验证”

### 4.5 你必须遵守的行为

* 若 `status == REJECTED`：不得进入 SymPy/Lean 验证。你必须修改 proposal 并重新触发 MAGI（最多 2 次修订；超过则判定该 step 方案不收敛，进入失败报告）。
* 若 `status == APPROVED`：你必须把 hazards 显式写入该步的草稿文件（后续写 draft 时），并在验证脚本里体现域条件（例如 sympy 的 assumptions 或在 Lean 里显式声明）。

---

## 5. SymPy 验证（函数级、可复核）

### 5.1 产物要求（每步必须落盘）

对 step_001：

* `sympy/step_001_check.py`：验证脚本
* `sympy/step_001_out.txt`：执行输出（stdout+stderr 汇总）
* `logs/tool_calls.log`：记录命令、退出码、时间戳

### 5.2 脚本规范（强制）

* 必须使用 `assert` 或显式的布尔判定，保证失败时退出码非 0 或打印 FAIL 并退出非 0。
* 必须避免浮点近似，优先用 `simplify`, `factor`, `cancel`, `together`, `ratsimp` 等精确变换。
* 必须显式声明符号域/假设（例如 `symbols('x', real=True, positive=True)`），并与 assumptions.md 一致。
* 通过时必须打印一行：`PASS: step_001`（便于 final_audit 解析）。

SymPy 脚本模板（示例）：

```python
# sympy/step_001_check.py
from sympy import symbols, simplify

x = symbols("x", real=True)  # 根据 assumptions.md 调整
lhs = ...
rhs = ...

ok = simplify(lhs - rhs) == 0
assert ok, f"FAIL: step_001, simplify(lhs-rhs) != 0, got: {simplify(lhs-rhs)}"
print("PASS: step_001")
```

### 5.3 执行规范（示例）

```bash
python sympy/step_001_check.py > sympy/step_001_out.txt 2>&1
```

你必须在日志中记录退出码；退出码非 0 视为失败。

### 5.4 重试策略（有上限）

* SymPy 脚本生成/修复最多 3 次。
* 每次重试必须在 `logs/errors.log` 写入“失败原因 → 修复动作 → 预期改善”。
* 3 次仍失败：该 step 判定失败，进入 Failure Report（不得硬写 draft）。

---

## 6. Lean4 验证（形式化门控）

### 6.1 产物要求（每步必须落盘）

对 step_001：

* `lean/Step001.lean`：本步对应的 Lean 文件（可包含 lemma/theorem）
* `lean/step_001_lean.log`：Lean 编译日志（stdout+stderr）

### 6.2 Lean 文件规范（强制）

* 你必须显式导入所需库（以 mathlib 习惯为准）。
* 你必须把 assumptions（域条件、可微性等）写成显式参数/前提。
* 若本步只做引理，你仍必须写成可被后续步骤引用的 lemma。

Lean 模板（示例，按你的环境调整 import）：

```lean
-- lean/Step001.lean
import Mathlib

-- 根据 assumptions.md 声明变量域与前提
variable {x : ℝ}

-- 示例：写成 lemma / theorem
theorem step_001 : (/* goal */) := by
  -- proof
  sorry
```

注意：你不能把 `sorry` 当成通过。只有编译成功且无 sorry（若策略要求零 sorry）才算通过。是否允许 sorry 由 steps.json 的 accept_criteria 决定；默认 strict 模式：禁止 sorry。

### 6.3 编译执行（示例）

```bash
lake env lean lean/Step001.lean > lean/step_001_lean.log 2>&1
```

### 6.4 重试策略（有上限）

* Lean 修复最多 5 次。
* 每次必须依据 Lean 错误信息精确修复：类型、引理引用、域前提、simp lemma 等。
* 5 次仍失败：该 step 判定失败，进入 Failure Report（不得硬写 draft）。

---

## 7. 证据包 Evidence Pack（必须生成，final_audit 依赖它）

每个通过的 step 必须生成：`evidence/step_001_evidence.json`

最小 schema（必须包含）：

* step_id
* magi:
  vote_file: "magi/step_001_vote.json"
  status: "APPROVED"
* sympy:
  script: "sympy/step_001_check.py"
  output: "sympy/step_001_out.txt"
  exit_code: 0
  pass_marker_found: true
* lean:
  file: "lean/Step001.lean"
  log: "lean/step_001_lean.log"
  exit_code: 0
  error_found: false
* artifacts_exist: true/false（由你在生成时检查）
* timestamp

如果任何字段缺失或 artifacts_exist=false，则该 step 不允许标记 passed。

---

## 8. 草稿写入 Draft Writing（这是“产物”，不是“描述”）

### 8.1 必须写入的文件

* `draft/step_001.md`：该步的可读解释 + 证据引用
* `draft/proof_draft.md`：按顺序拼接每个 step 的索引文档（可 include/链接 step_xxx.md）

### 8.2 step_001.md 的格式（强制）

必须包含以下区块（用标题即可）：

1. Step Claim（本步结论，含 LaTeX）
2. Dependencies（引用前置 steps）
3. Proposal Summary（MAGI 通过的方案摘要，含 hazards 与前提）
4. SymPy Verification（说明脚本路径、关键表达式、输出 PASS 行引用）
5. Lean4 Verification（说明文件路径、目标 lemma/theorem 名、编译成功证据）
6. Evidence Pack（指向 evidence json）
7. Status（必须写：`passed`）

禁止只写“通过了”。你必须写“怎么通过的 + 证据在哪”。

### 8.3 写入时机（再次强调）

* 只有在 MAGI=APPROVED 且 SymPy&Lean4 均通过且 evidence pack 齐全时，才允许写入 step_001.md 并 append proof_draft.md。

---

## 9. status.json 与流程状态机（必须维护）

`status.json`（run 级别）必须包含：

* run_id
* phase: "init" | "planning" | "step_loop" | "auditing" | "done" | "failed"
* current_step_id
* steps:

  * step_id
    status: "pending" | "magi_rejected" | "magi_approved" | "sympy_passed" | "lean_passed" | "passed" | "failed"
    attempts: { magi: n, sympy: n, lean: n }
    last_error: "..."
* updated_at

你必须在每一步关键节点更新 status.json。final_audit 会以此判断你是否跳步或偷懒。

---

## 10. final_audit（终局审计与 Solution.md 生成）

### 10.1 调用（示例）

```bash
python scripts/final_audit.py \
  --run_dir WORKSPACE/runs/<run_id> \
  --steps plan/steps.json \
  --draft draft/proof_draft.md \
  --out audit/audit.json \
  --solution audit/Solution.md
```

### 10.2 审计必须检查的内容（你必须确保可通过）

* steps.json 中每个 step 都有对应的 magi vote / sympy / lean / evidence 文件
* PASS marker 存在且 exit_code 正确
* Lean log 无 error，且（默认 strict）无 sorry
* draft 中每步都包含证据引用
* status.json 中所有 step.status == passed
* 若任一项失败：audit.status 必须为 REJECTED，并生成 `audit/FAILURE_REPORT.md`

### 10.3 你对用户的最终输出约束

* 仅当 `audit.status == APPROVED`，你才可以对用户给出“证明完成”的自然语言摘要，并引用 Solution.md 的结构。
* 若 REJECTED：你必须给出失败原因摘要（指向具体 step 与日志路径），不得“强行总结成正确结论”。

---

## 11. 失败报告 Failure Report（必须可读、可定位）

当任一 step 或 final_audit 失败并终止时，必须生成：`audit/FAILURE_REPORT.md`

必须包含：

* 失败 step_id
* 失败发生在 MAGI / SymPy / Lean / Audit 哪个阶段
* 关键错误日志的路径与核心错误行（只摘录少量关键行，避免把整份日志塞进对话上下文）
* 已尝试的修复动作与次数
* 建议的下一步（需要用户补充条件？还是需要重写 step？）

---

## 12. 最低质量门槛（防止 LLM 偷懒）

* 每个 step 必须“原子化”：一次只做一个等价变形、一个引理、一个推导点。禁止“由此显然得证”。
* 每个 step 必须同时满足“可执行验证”和“可形式化表达”，否则 steps.json 就不合格，必须回到规划阶段重拆。
* 在 SymPy 中遇到域敏感操作（开方、对数、除法、乘以可能为0的量、单调性推理等），必须把域条件写进 assumptions，并在 MAGI hazards 中显式列出。
* Lean4 无法证明时，不得用自然语言补洞：必须要么改步骤（引入合适引理/前提），要么明确失败并停止。

---

## 13. 常用命令速查（示例）

初始化与预检：

```bash
python scripts/check_routes.py --workspace WORKSPACE
```

全局规划：

```bash
python scripts/magi_plan.py --mode plan --run_dir WORKSPACE/runs/<run_id> --out plan/steps.json
```

Step 决策：

```bash
python scripts/magi_plan.py --mode step_decide --run_dir WORKSPACE/runs/<run_id> --step_id step_001 --proposal draft/step_001_proposal.md --out magi/step_001_vote.json
```

SymPy：

```bash
python sympy/step_001_check.py > sympy/step_001_out.txt 2>&1
```

Lean：

```bash
lake env lean lean/Step001.lean > lean/step_001_lean.log 2>&1
```

终局审计：

```bash
python scripts/final_audit.py --run_dir WORKSPACE/runs/<run_id> --out audit/audit.json --solution audit/Solution.md
```

---

## 14. 你在对话中的“汇报方式”（建议但强烈推荐）

为了不污染上下文：

* 对用户只汇报：当前 phase、当前 step、通过/失败、关键证据路径。
* 不要把长日志全文粘贴进对话。只摘录 5~20 行关键错误即可，其余留在 workspace 文件中。
* 用户要看细节时，指向 `audit/Solution.md` 或 `audit/FAILURE_REPORT.md`。

---

## 15. 执行清单（你必须逐项打钩）

* [ ] 运行 check_routes.py 成功，且 logs/init_check.log 已写入
* [ ] run 目录创建完成，problem.md / assumptions.md / manifest.json / status.json 存在
* [ ] magi_plan 生成 steps.json，且每步都有 evidence_required 与 accept_criteria
* [ ] 每个 step：proposal.md 存在
* [ ] 每个 step：MAGI vote.json 存在且 APPROVED 才进入验证
* [ ] 每个 step：SymPy 脚本与输出存在，PASS marker 存在，exit_code=0
* [ ] 每个 step：Lean 文件与日志存在，exit_code=0，无 error（strict 默认无 sorry）
* [ ] 每个 step：evidence json 完整
* [ ] 每个 step：step_i.md 写入 + proof_draft.md append
* [ ] final_audit 生成 audit.json 与 Solution.md，且 audit=APPROVED 才输出最终结论

