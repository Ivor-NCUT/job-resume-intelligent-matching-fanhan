---
name: job-resume-intelligent-matching-fanhan
description: Use this skill whenever the user wants to match jobs/JDs/岗位 with resumes/候选人/作品集/个人网站/GitHub/社媒链接, including “上传简历找岗位”, “上传 JD 找候选人”, “跑岗位候选人匹配”, “飞书多维表格匹配”, or feedback like “这个匹配不准”. This skill performs no model training; it uses Agent tools, structured extraction, retrieval, hard-condition checks, the candidate `实习 & 正职` field, evidence-based scoring, LLM review, and Darwin-style feedback iteration.
---

# 职位 & 简历智能匹配

Use this skill to run bidirectional recruiting matching without changing model weights. The skill turns candidate materials and job descriptions into structured profiles, applies hard-condition gates, ranks with evidence, and records why each match is recommended or risky.

## When Triggered

1. Confirm the direction:
   - Candidate to jobs: user uploads resume, portfolio, personal website, GitHub, social links, or extra notes and wants several matching jobs.
   - Job to candidates: user uploads a JD and wants candidate resumes, portfolios, and supporting materials.
   - Batch: user gives a Feishu Base, SQLite database, CSV, or JSON set of candidates and jobs.
   - Feedback: user says a recommendation is wrong, asks the skill to improve, or points out a recurring mismatch.
2. If the user already provided enough data and asked to run, execute directly. Do not ask for repeated confirmation.
3. If writing back to a live database, show the affected table/field list once before the first write unless the user has explicitly authorized the write in the same turn.

## Core Algorithm

Run these phases in order.

1. Normalize inputs.
   - Candidate fields: name, resume text, portfolio text, links, skills, experience, education, location, availability, expected role, `实习 & 正职`.
   - Job fields: title, company, JD text, must-have requirements, nice-to-have requirements, location, seniority, job type, hiring status.
   - Preserve source evidence snippets. Never invent missing facts.
2. Infer engagement type.
   - Candidate type comes first from `实习 & 正职`.
   - Job type comes from job title, JD, explicit tags, and requirements.
   - Use the compatibility matrix below before semantic ranking.
3. Hard-condition gate.
   - Check job type, location, seniority, work authorization if present, availability, language, required domain, and required technical stack.
   - A failed hard condition can still be shown only as “备选/风险较高” when the user asks for broad exploration.
4. Retrieval and scoring.
   - Keyword score: exact skills, domain terms, role terms, tool names, product names.
   - Semantic score: summarize candidate and job as comparable work evidence; compare responsibilities and outcomes.
   - Rule score: hard-condition fit, engagement type fit, seniority fit, recency, portfolio strength, and requirement coverage.
   - LLM review: ask the model to compare the top candidates/jobs only, with evidence and risks.
5. Output.
   - Return ranked matches with `推荐等级`, `匹配理由`, `风险理由`, `证据引用`, and `下一步建议`.
   - For Feishu Base or SQLite, write the same fields into the match result table when authorized.

## Engagement Type Gate

Candidate `实习 & 正职` is not a soft preference. It is a first-order matching gate.

### Candidate Type Normalization

| Raw value | Normalized |
|---|---|
| `实习`, `实习生`, `找实习`, `intern` | `internship` |
| `正职`, `全职`, `正式`, `社招`, `full-time` | `full_time` |
| contains both internship and full-time signals | `both` |
| blank, unknown, unclear | `unknown` |

### Job Type Inference

| Job signal | Normalized |
|---|---|
| title/JD contains `实习`, `实习生`, `校招实习`, `intern` | `internship` |
| title/JD contains `正职`, `全职`, `正式`, `社招`, `full-time` | `full_time` |
| title/JD contains both signals | `both` |
| title contains `负责人`, `主管`, `经理`, `总监`, `Head`, `Lead`, `合伙人` and no internship signal | `full_time` |
| no useful signal | `unknown` |

### Compatibility Matrix

| Candidate | Job | Action |
|---|---|---|
| `internship` | `internship` or `both` | pass |
| `full_time` | `full_time` or `both` | pass |
| `both` | any known type | pass |
| known type | `unknown` | pass with risk note |
| `unknown` | known type | pass with risk note and lower confidence |
| `internship` | `full_time` | hard mismatch; cap recommendation at `弱匹配` unless user explicitly asks broad search |
| `full_time` | `internship` | hard mismatch; normally exclude from top results |

Always include the engagement decision in the match explanation:

```text
实习/正职判断：候选人为 {candidate_type}，岗位为 {job_type}，兼容性为 {pass|risk|mismatch}。
```

## Score Formula

Default weights:

```text
final_score =
  0.25 * keyword_score +
  0.30 * semantic_score +
  0.25 * rule_score +
  0.20 * llm_review_score
```

Apply these caps after scoring:

- Engagement hard mismatch: cap at 45/100 and mark `弱匹配`.
- Missing candidate `实习 & 正职`: cap at 78/100 and add risk.
- Missing job type signal: cap at 82/100 and add risk.
- Any explicit must-have failure: cap at 60/100 unless the user asks for exploratory longlist.

## Tooling

### Database selection

When the task uses the local `opportunity_matcher` SQLite database, resolve the database before reading candidates or jobs:

1. If `OPPORTUNITY_MATCHER_DB_FILE` is set, use that exact path.
2. Otherwise use the current CLI project's `data/opportunity_matcher.db`.
3. Report the selected path once in the result.

Do not silently fall back to a different empty database when the configured database exists. Before matching, verify candidate count, total/open job count, and match-result count. If the selected database has no open jobs, report the data gap instead of fabricating matches.

Use bundled script for deterministic batch checks:

```bash
python scripts/run_match.py --input input.json --output matches.json --top-n 5
```

Read these references only when needed:

- `references/base-field-mapping.md`: Feishu Base and SQLite field mapping.
- `schemas/match-input.schema.json`: expected local input shape.
- `schemas/match-output.schema.json`: expected output shape.

## Feedback And Darwin Iteration

When the user gives feedback such as “这个结果不准”, “实习生被推荐到正职了”, or “把这个规则写进 skill”, run this loop:

1. Classify feedback.
   - Wrong engagement type, missing hard condition, weak evidence, hallucinated evidence, ranking order, output format, or tool/writeback issue.
2. Convert feedback into a failing example.
   - Add or update one eval in `evals/evals.json`.
   - Include minimal candidate/job facts and the expected corrected behavior.
3. Read `/Users/fanhan/.codex/skills/达尔文skill/SKILL.md`.
4. Apply Darwin-style improvement:
   - Evaluate current instructions against failure modes, actionability, checkpoints, and反例清单.
   - Change the smallest useful part of this skill.
   - Run deterministic script tests and any relevant eval prompts.
5. 🔴 CHECKPOINT · Stop before live database writeback or publishing the updated skill package.
   - If the user already authorized this exact update in the same turn, proceed.
   - Otherwise summarize the diff and ask for confirmation.

## Failure Handling

| Trigger | First response | Fallback |
|---|---|---|
| candidate `实习 & 正职` is empty | mark candidate type `unknown`; lower confidence | ask for clarification only if top result depends on it |
| JD type cannot be inferred | mark job type `unknown`; lower confidence | inspect job title, requirements, tags, and company notes |
| resume or portfolio cannot be parsed | use available text and metadata | mark evidence gaps in risk reason |
| Feishu write fails | preserve local output JSON or CSV | report exact table, field, and record that failed |
| LLM review conflicts with hard gate | hard gate wins | include conflict in risk reason |

## Do Not

- Do not train, fine-tune, distill, or modify model weights.
- Do not let semantic similarity override `实习 & 正职` hard mismatch.
- Do not invent portfolio claims, GitHub activity, work dates, education, or availability.
- Do not hide missing evidence behind confident language.
- Do not rewrite database schema unless the user asks for a schema migration.
- Do not write back to a live table after feedback iteration without an explicit writeback authorization.

## Output Template

For each match:

```markdown
### {rank}. {job_or_candidate_name}
- 推荐等级：强匹配 / 可推荐 / 备选 / 弱匹配
- 综合分：{score}/100
- 实习/正职判断：候选人为 {candidate_type}，岗位为 {job_type}，兼容性为 {compatibility}
- 匹配理由：{3 concise bullets}
- 风险理由：{missing or mismatch risks}
- 证据引用：{source snippets or fields}
- 下一步建议：{interview question, portfolio check, or manual review action}
```
