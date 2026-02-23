# SOP: 错误分类与恢复

> **加载时机**: 阶段 C — 任何验证步骤失败时

---

## 1. ErrorClassifier 模块

```python
from skill.runtime.error_classifier import classify, suggest_fix, format_feedback_prompt, RetryBudget
```

### 三级分类

| 类别 | 说明 | 示例 |
|------|------|------|
| SYNTAX | 语法/编译错误 | 类型不匹配、缺少 import、括号不全 |
| LOGIC | 逻辑错误 | tactic failed、assert 失败、simplify 不收敛 |
| ENVIRONMENT | 环境错误 | 缺少依赖、命令不存在、超时 |

### 使用流程

```python
error = classify(stderr, "lean")       # → StructuredError
suggest_fix(error)                      # → 填充 error.suggestion
prompt = format_feedback_prompt(error, "S1")  # → MAGI 反馈 Prompt
```

## 2. RetryBudget

```python
budget = RetryBudget("step_001")
# 默认上限: magi=2, sympy=3, lean=5

if budget.can_retry("lean"):
    budget.consume("lean")
    # 执行修复重试
else:
    # 生成 FAILURE_REPORT，停止推进
```

当 `budget.is_exhausted()` 时，**必须**停止重试。

## 3. 错误处理行为

| 错误类别 | 处理方式 |
|----------|----------|
| SYNTAX | 基于 stderr 精确修复，保留修复痕迹 (errors.log) |
| LOGIC | 回退并修改 step claim / 拆分更小 step → 重走 MAGI |
| ENVIRONMENT | 检查依赖环境，报告用户 |

## 4. 每次重试必须记录

在 `logs/errors.log` 写入：
- 失败原因（关键 stderr 行）
- 修复动作
- 预期改善

## 5. ParallelRunner（可选加速）

当某步多次失败时，可用 ParallelRunner 尝试多个候选策略：

```python
from skill.runtime.parallel_runner import ParallelRunner, CandidateBranch

candidates = [CandidateBranch("v1", code1, "lean"), ...]
runner = ParallelRunner(max_workers=4, timeout=60)
log = runner.run_candidates("S1", candidates)  # 首胜取消其余
```

每个分支在**物理隔离**的临时目录中运行。
