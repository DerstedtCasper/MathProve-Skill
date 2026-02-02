# Lean4 证明流程提示

## 建议流程
1. 使用 `assets/lean_preamble.lean` 作为导入模板
2. 先写定理声明与证明骨架（允许 `by` + `sorry`）
3. 逐步替换 `sorry`，每次只攻克一个子目标

## 常用策略（示例）
- `simp`：简化常见表达式
- `aesop`：自动搜索（适合中小目标）
- `rfl`：反射性等式
- `rw`：重写
- `linarith`：线性算术
- `ring`：环等式
- `induction`：归纳

## 交互模式建议
优先使用 REPL 逐步执行，失败时观察错误信息并调整策略；避免长串一次性策略。

## 无 REPL 的替代方案
若 `lake exe repl` 不可用，可使用 `lean_repl_client.py --mode file` 通过 `lake env lean` 执行整段证明；也可使用 `--mode auto` 自动回退。

## 路径注入
可使用 `--lean-path` 或 `--lake-path` 指定可执行文件路径，适配多套 Lean 安装。

## REPL 命令约定（示例）
```json
{"cmd": "import Mathlib\\n theorem t (n: Nat) : n + 0 = n := by"}
```
```json
{"tactic": "simp", "proofState": 0}
```

如本地 REPL 命令不同，请在 `scripts/lean_repl_client.py` 中调整执行命令。

## Reverse Gate（强烈推荐）
当你的证明需要“可复核、可开源、可审计”时，建议在最终阶段开启 reverse gate：
- Step id 推荐统一为 `S1/S2/...`，并在 Lean 中对应写作：`theorem/lemma S1 ... := by ...`
- `python scripts/final_audit.py --lean-gate` 会：
  1) 生成统一的 `reverse_gate.lean`
  2) 运行 `scripts/lint_reverse_lean4.py`（禁止 `sorry/admit/axiom/constant/opaque`，要求 step map）
  3) 在 `--lean-cwd` 指定的 Lake+Mathlib 工程中运行 `lake env lean reverse_gate.lean`

### import 行处理
- 单步 file-mode 校验时，允许在 step 里写 `import ...`
- 进入 reverse gate 时，`final_audit.py` 会自动把这些 `import ...` 提升到文件头部（避免 “import 必须在文件开头” 的错误）

### 超时建议
- Mathlib 工程首次编译可能较慢：建议使用 `--lean-timeout 120`，或在 step 里填 `checker.timeout`。
