# SOP: SymPy 符号验证

> **加载时机**: 阶段 C 逐步循环 — MAGI APPROVED 后进入 SymPy 验证

---

## 1. 产物要求（每步必须落盘）

| 文件 | 说明 |
|------|------|
| `sympy/step_XXX_check.py` | 验证脚本 |
| `sympy/step_XXX_out.txt` | 执行输出（stdout+stderr） |
| `logs/tool_calls.log` | 命令、退出码、时间戳 |

## 2. 脚本规范（强制）

- 使用 `assert` 或显式布尔判定，失败时退出码非 0
- 避免浮点近似，优先用 `simplify`, `factor`, `cancel`, `together`, `ratsimp`
- 显式声明符号域/假设，与 `assumptions.md` 一致
- 通过时打印：`PASS: step_XXX`

### 模板

```python
# sympy/step_001_check.py
from sympy import symbols, simplify

x = symbols("x", real=True)  # 根据 assumptions.md
lhs = ...
rhs = ...

ok = simplify(lhs - rhs) == 0
assert ok, f"FAIL: step_001, simplify(lhs-rhs) != 0, got: {simplify(lhs-rhs)}"
print("PASS: step_001")
```

## 3. 执行

```bash
python sympy/step_001_check.py > sympy/step_001_out.txt 2>&1
```

退出码非 0 视为失败。

## 4. 重试策略

- 最多 **3 次**修复重跑
- 每次重试在 `logs/errors.log` 写入：失败原因 → 修复动作 → 预期改善
- 3 次仍失败：该 step 判定失败，生成 FAILURE_REPORT

## 5. 域敏感操作注意

遇到开方、对数、除法、乘以可能为 0 的量、单调性推理时：
- 必须把域条件写进 `assumptions`
- 必须在 MAGI hazards 中显式列出
- SymPy 返回 `None/Unknown` → 当作未证明，需改写目标或补充假设
