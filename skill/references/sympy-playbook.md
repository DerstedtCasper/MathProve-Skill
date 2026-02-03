# SymPy 验证流程提示

## 常见模式
- 恒等式验证：`simplify(lhs - rhs) == 0`
- 求导：`diff(f, x, n)`
- 积分：`integrate(f, x)`
- 解方程：`solve(eq, x)`
- 化简：`simplify(expr)`

## 输出建议
使用 `emit({...})` 输出 JSON，便于脚本解析与复核。

## 注意事项
- 明确符号域与假设（必要时用 `symbols(..., real=True)`）
- 避免 SymPy 无法解析的自定义记号
