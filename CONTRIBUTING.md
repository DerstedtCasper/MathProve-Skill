# 贡献指南（MathProve）

欢迎提交改进：更严格的校验、更清晰的讲解结构、更强的 Lean4/Mathlib 证明能力、更好的子代理分发方案等。

## 开发环境

- Python 3.11+（建议 3.12/3.13）
- 依赖：`sympy`、`pytest`
- 可选：Lean4 + Mathlib（推荐用 Lake 工程，如 `D:\MATH Studio\math_studio`）

安装（示例）：

```powershell
python -m pip install -r requirements-dev.txt
```

## 运行测试

```powershell
python -m pytest "MathProve/tests"
```

说明：当前 CI 默认只跑 Python 单元测试。Lean4 Gate 由于环境差异大，保持为本地可选验证（欢迎补充更稳健的 CI 方案）。

## 提交规范

- 修改脚本后：请同时更新 `SKILL.md` / `assets/` 模板（如有影响）。
- 新增严格性约束：请补充单元测试，避免误伤正常用例。
- 尽量保持“可回退”：无 Lean/无 Mathlib/无 subagent 的环境也能跑通（只是严格度降级）。

## 报告问题

请提供：
- 复现命令（含 `--lean-cwd`/`--python` 等参数）
- `MathProve/logs/*.jsonl`（如有）
- 相关 steps JSON（可脱敏后）

