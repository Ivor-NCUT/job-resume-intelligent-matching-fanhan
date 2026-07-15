# 职位 & 简历智能匹配

这个能力包用于无训练的岗位和简历双向匹配：上传候选人材料找岗位，或上传岗位描述找候选人。

核心规则：

- 不训练、不微调、不蒸馏模型。
- 候选人表的 `实习 & 正职` 是一等门控字段。
- 岗位类型从岗位名称和岗位要求推断。
- 输出必须包含推荐等级、匹配理由、风险理由和证据引用。
- 用户反馈会被转成评测样例，再按达尔文式流程迭代能力包。

## 本地批量匹配

```bash
python scripts/run_match.py --input input.json --output matches.json --top-n 5
```

输入结构见 `schemas/match-input.schema.json`，输出结构见 `schemas/match-output.schema.json`。

## 目录

- `SKILL.md`: Agent 使用说明。
- `scripts/run_match.py`: 可重复执行的轻量匹配脚本。
- `references/base-field-mapping.md`: 飞书多维表格和 SQLite 字段映射。
- `schemas/`: 输入输出结构说明。
- `evals/evals.json`: 初始评测用例。
