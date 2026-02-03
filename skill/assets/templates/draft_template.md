# MathProve 草稿（draft）

> 规则：每个 step 通过（SymPy/Lean4）后再写入；每步必须写清符号与假设，保证“可讲解、可追问”。

## Problem Lock（问题锁定）

- 原问题：
- 目标结论（要证明/要计算）：
- 范围/前提（默认域、变量类型、是否允许使用已知定理等）：
- 成功标准（何谓“证明完成”）：

## Notation Table（符号表）

| 符号 | 含义 | 类型/域 | 备注 |
|---|---|---|---|
|  |  |  |  |

## Assumption Ledger（假设台账）

| 编号 | 假设 | 用途 | 来源（题面/已知/引入） |
|---|---|---|---|
| A1 |  |  |  |

## Claim List（主张清单）

| 编号 | Claim（主张） | 状态 | 依赖 |
|---|---|---|---|
| C1 |  | pending |  |

## Claim → Evidence Matrix（主张-证据矩阵）

| Claim | Evidence（SymPy/Lean4/引理/引用/推导） | Notes |
|---|---|---|
| C1 |  |  |

## Step Log（逐步推导）

> `scripts/draft_logger.py` 会把每个 step 以 S1/S2/... 的形式追加到这里。

