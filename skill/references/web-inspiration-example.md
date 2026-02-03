# 联网启发示例

## 示例场景
问题：证明某公式的收敛性，需先检索已知结论或提示思路。

## 示例输入
1. 通过 IDE 联网能力获取来源列表（标题/链接/摘要）
2. 将来源列表写入 JSON 文件（例如 `sources.json`）

示例 `sources.json`:
```json
[
  {
    "title": "示例文献标题",
    "url": "https://example.org/paper",
    "summary": "给出关键引理或收敛性判别条件"
  }
]
```

## 记录命令
```bash
python scripts/web_inspiration.py --query "级数收敛性证明思路" --sources-file sources.json --notes "作为启发线索" --draft draft.md
```

## 端到端示例流程（精简）
1. 使用 `scripts/problem_router.py` 判断问题路线（可选）
2. 用 `scripts/step_router.py` 生成步骤与路线
3. 通过 IDE 联网能力整理来源，写入 `sources.json`
4. 调用 `web_inspiration.py` 将来源写入草稿与日志
5. 按步骤运行 SymPy/Lean4 验证并写入草稿
6. 使用 `final_audit.py` 复核并生成 `Solution.md`

示例命令（日志写入 `logs/demo_inspiration.jsonl`）：
```bash
python scripts/problem_router.py --text "证明级数收敛性" --log logs/demo_inspiration.jsonl
python scripts/step_router.py --input steps.json --output steps_routed.json --log logs/demo_inspiration.jsonl
python scripts/web_inspiration.py --query "级数收敛性证明思路" --sources-file sources.json --notes "启发来源" --draft draft.md --log logs/demo_inspiration.jsonl
python scripts/verify_sympy.py --code "<sympy代码>" --log logs/demo_inspiration.jsonl
python scripts/lean_repl_client.py --payload-file lean_payload.json --mode auto --cwd "<lean项目>" --log logs/demo_inspiration.jsonl
python scripts/final_audit.py --steps steps_routed.json --solution Solution.md --lean-mode auto --lean-cwd "<lean项目>" --log logs/demo_inspiration.jsonl
```

日志样例见 `references/web-inspiration-log-sample.jsonl`。

## 预期结果
- 草稿追加“联网启发记录”区块
- 日志记录 `event=web_inspiration`

## 约束
- 仅作启发，必须用 SymPy/Lean4 回证后才能进入正式稿
