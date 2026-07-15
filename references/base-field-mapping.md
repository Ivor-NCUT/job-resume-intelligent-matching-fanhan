# 字段映射

## 候选人表

最小字段：

- `姓名`: 候选人姓名。
- `实习 & 正职`: 候选人当前寻找实习、正职，或两者都可。
- `简历`: 简历附件或文本链接。
- `作品集`: 作品集附件或链接。
- `补充材料`: 个人网站、GitHub、社媒账号、项目链接、补充说明。
- `候选人结构化画像`: Agent 解析后的结构化 JSON。
- `候选人检索文本`: 用于关键词和语义检索的扁平文本。
- `候选人匹配摘要`: 给匹配结果使用的短摘要。

## 职位表

最小字段：

- `岗位名称`: 岗位名称；用于推断实习或正职。
- `岗位描述`: 原始 JD。
- `岗位要求`: 必须条件和加分项。
- `岗位结构化画像`: Agent 解析后的结构化 JSON。
- `岗位评分规则`: 岗位特有权重或硬条件。
- `岗位检索文本`: 用于关键词和语义检索的扁平文本。
- `岗位匹配摘要`: 给候选人输出使用的短摘要。

## 匹配结果表

最小字段：

- `匹配批次ID`
- `候选人`
- `岗位`
- `最终排名`
- `推荐等级`
- `硬条件结果`
- `关键词分数`
- `语义分数`
- `规则分数`
- `LLM排序`
- `匹配理由`
- `风险理由`
- `证据引用`
- `人工决策`
- `算法版本`

## SQLite MVP

Use three tables first:

- `candidates`
- `jobs`
- `match_results`

Keep column names close to the Feishu fields. Store structured profile JSON in text columns during MVP; migrate to JSONB or dedicated tables later only when query needs prove it.
