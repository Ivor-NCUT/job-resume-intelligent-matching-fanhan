---
name: job-resume-intelligent-matching-fanhan
description: Use this skill whenever the user wants to match jobs/JDs/岗位 with resumes/候选人/作品集/个人网站/GitHub/社媒链接, including “上传简历找岗位”, “上传 JD 找候选人”, “跑岗位候选人匹配”, “飞书多维表格匹配”, or feedback like “这个匹配不准”. Candidate-to-job runs return a short copy-ready Feishu text message for forwarding to the candidate; JD-to-candidate runs classify the role, rank every same-category resume JSON, select up to five eligible candidates, and deliver concise company-facing recommendations with their original resumes.
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
4. When a JD arrives in a Feishu group, use that group as the delivery target. Otherwise require an explicit target chat before sending; matching can proceed while the destination is unresolved.
5. When an intern invokes local Codex from Feishu, treat the normal agent reply as the delivery channel. Do not send a duplicate message to the same group through `lark-cli` unless the user explicitly asks.

## Core Algorithm

Run these phases in order.

1. Normalize inputs.
   - Candidate fields: name, all parsed material text, original files, original links, skills, experience, education, location, availability, expected role, `实习 & 正职`.
   - Treat PDF, Word, HTML, ZIP/project files, personal websites, Feishu documents, GitHub repositories, social links, and email text as candidate evidence when present.
   - Match against extracted content from every material version, not only the current PDF or filename. Preserve each original file/link for delivery.
   - Job fields: title, company, JD text, must-have requirements, nice-to-have requirements, location, seniority, job type, hiring status.
   - Preserve source evidence snippets. Never invent missing facts.
2. Classify the JD and build the candidate pool.
   - Use the canonical category values in `Role Category Gate`.
   - If the JD is an existing job record, prefer its `职位分类`; otherwise infer the category from the full JD. A JD may have more than one category only when its responsibilities materially span them.
   - Load every candidate whose `候选人职位类目` intersects the JD category. Do not retrieve a cross-category semantic shortlist first.
   - For each same-category candidate, parse the resume JSON using the field precedence in `Feishu Base source`. Exclude rows without readable JSON from scoring and report their count.
3. Infer engagement type.
   - Candidate type comes first from `实习 & 正职`.
   - Job type comes from job title, JD, explicit tags, and requirements.
   - Use the compatibility matrix below before semantic ranking.
4. Hard-condition gate.
   - Check job type, location, seniority, work authorization if present, availability, language, required domain, and required technical stack.
   - Exclude explicit must-have failures from the company-facing shortlist. Show them only in a separate internal exploratory list when the user explicitly asks for broad exploration.
5. Retrieval and scoring.
   - Keyword score: exact skills, domain terms, role terms, tool names, product names.
   - Semantic score: summarize candidate and job as comparable work evidence; compare responsibilities and outcomes.
   - Rule score: hard-condition fit, engagement type fit, seniority fit, recency, portfolio strength, and requirement coverage.
   - Score every readable JSON in the same-category pool, then sort all results by final score. Use the LLM only to review the leading results and resolve close evidence-based comparisons; never let it introduce an out-of-category candidate.
6. Output and delivery.
   - Return ranked matches with `推荐等级`, `匹配理由`, `风险理由`, `证据引用`, and `下一步建议`.
   - For candidate-to-jobs, keep the recruiter-facing assessment separate from the candidate-facing copy. The latter must follow `Candidate Copy In Feishu` and be directly pasteable as one message.
   - For job-to-candidates, keep the internal assessment separate from the company-facing copy. The latter must follow `Company Copy In Feishu`.
   - When the user requests delivery, send the original file format (including HTML or ZIP) and include the original webpage, Feishu document, GitHub, or social link. A link-only candidate is valid when its extracted text supports the match.
   - Select `min(5, eligible_count)` candidates. Never pad the list with another category. If fewer than five survive, state why.
   - Freeze the selected names and order before composing or sending. The overview, candidate introductions, and resume files must remain consistent. Delivery does not imply Base writeback.

## Candidate Copy In Feishu

This section is mandatory for `candidate_to_jobs`. After the internal ranking, produce one candidate-facing plain-text message that the operator can copy in full and send to the candidate without editing.

### Feishu delivery contract

- When invoked through Feishu or a Feishu Bridge, the default visible reply is only the candidate-facing text. Do not mix in scores, completion status, database notes, or a `给实习生复制` label; the intern should be able to copy the entire message bubble.
- Preserve short paragraphs and blank lines as plain text. Do not use Markdown headings, code fences, quote blocks, rich posts, cards, tables, or buttons.
- The Bridge normally relays the agent response back to the source chat. Return the text normally; do not call `im +messages-send` to echo it into the same chat.
- If the user explicitly asks to send the copy to another Feishu chat, confirm the target and identity, then use `im +messages-send --text` so line breaks remain unchanged. Do not use `--markdown` for this copy.
- Show the internal assessment in Feishu only when explicitly requested, and keep it in a separate message from the copy-ready text.

### Content contract

- Turn every final selected JD into a short choice, not a pasted JD. Default to the top five; if more must be delivered, split them into copyable messages of at most five jobs each.
- Keep each job to at most three short lines and the whole five-job message within roughly 1,200 Chinese characters.
- For each job include only: `岗位｜公司`, confirmed location/work mode and compensation when available, one sentence on what the role mainly does, one evidence-backed sentence on why it fits this candidate, and at most one decision-critical point to confirm.
- Translate internal `风险理由` into neutral candidate language such as `需要确认：上海线下办公，想先确认您是否考虑`。Omit low-value gaps instead of making the candidate read an audit report.
- End with one low-effort action: ask the candidate to reply with job numbers; promise the full JD/company details only for the selected numbers.
- Use natural one-to-one Chinese. Use `老师` only when the existing relationship already uses it.

### Never expose in candidate copy

- Scores, ranking labels, JD IDs, retrieval counts, model names, database/writeback status, `Top5`, `风险`, or internal evidence language.
- Full responsibilities, requirements, company introduction, or application homework for every job. Those belong in the follow-up after the candidate chooses.
- `把简历发我` or any request to resend materials already received.
- Unverified salary, location, financing, company claims, or exaggerated fit.
- Markdown tables, quote blocks, nested lists, or five repeated greetings and closings.

### Copy-ready template

```text
{候选人称呼}您好，我结合您的经历筛了几个目前在招、匹配度比较高的机会，先把简版发您。您看看哪些值得进一步了解：

1）{岗位}｜{公司}｜{地点/办公方式；已确认的薪酬或职级可继续写在本行，没有就省略}
主要做：{一句人话说明核心工作}
比较适合您：{一句候选人经历与岗位的具体连接}{有关键条件时接“；需要确认：...”}

2）{岗位}｜{公司}
...

您直接回复感兴趣的编号就行，比如“1、3”。我再把对应的完整 JD 和公司信息发您；如果这几个都不合适，也可以告诉我您更看重的方向、地点或薪资，我继续帮您缩小范围。
```

The candidate text itself is the deliverable. In Feishu, return it without a wrapper label. Outside Feishu, a wrapper label may appear before the text, but recruiter-only analysis must remain outside the copy block.

## Company Copy In Feishu

This section is mandatory for `job_to_candidates` when results are delivered to a company group. Company-visible messages help the client decide whom to interview; internal scoring and execution logs stay outside the client group.

### Company-visible contract

- Send only candidates who pass the role category and explicit hard conditions. Never add a weak candidate merely to reach five; say `本轮暂无达到推荐线的候选人` when none qualify.
- For each candidate use at most three short lines: `姓名｜当前角色/年限/地点`, `值得看：` one or two verified facts, and optional `需要确认：` one decision-critical gap.
- Do not expose scores, ranking labels, JD IDs, retrieval counts, model names, database/writeback status, audit summaries, or `Top5`. Do not repeat the full JD or use the label `风险`.
- Send each candidate introduction immediately before that candidate's original resume. Use a readable filename such as `{job}-{rank}-{candidate}.{ext}`; do not send duplicate copies or hash-heavy names.
- Close once with: `如果觉得哪位候选人比较合适，可以直接 @情情，我们的实习生会帮忙联系候选人并推进约面。` Resolve and use 情情's real Feishu mention when available; do not guess an open ID.

### One JD in the group

1. Send one short header naming the role and the number of eligible candidates. State that the list was not padded when fewer than five qualify.
2. Send each concise candidate introduction followed immediately by the matching resume.
3. Send the closing action sentence once after the last resume.

```text
已按「{job_title}｜{location}」筛完候选人库。这轮有 {eligible_count} 位达到推荐线，没有为了凑满 5 人加入硬条件不符的人选。

1）{candidate_name}｜{current_role_or_years}｜{location}
值得看：{one_or_two_verified_facts}
需要确认：{one_decision_critical_gap}
```

### Multiple JDs in the group

1. Send one compact overview in the main chat: one line per JD with its eligible count; for zero results, name the main missing hard condition.
2. Send one standalone header message per JD. Put that JD's candidate introductions and resumes in the header's reply thread with `im +messages-reply --reply-in-thread`; do not dump every resume into the main chat.
3. Keep each resume in the same thread as its candidate introduction and end the overall delivery with the same `@情情` action sentence.

```text
本轮共完成 {job_count} 个岗位的候选人筛选：
1）{job_one}：{eligible_count} 位可推荐
2）{job_two}：暂无达标人选，主要缺口是 {hard_requirement}
…

下面按岗位分别发送主消息，候选人介绍和简历都放在对应回复串里，方便按岗位查看。
```

## Role Category Gate

Use the canonical matching values below; normalize the user's wording and the two tables' option aliases to these values.

| User/JD wording | Canonical category |
|---|---|
| 市场、增长、运营、用户运营、内容运营、客户运营 | `增长/运营/市场` |
| 产品经理、产品运营（以产品职责为主） | `产品` |
| 工程师、开发、前端、后端、全栈、基础设施 | `研发` |
| 算法、机器学习、LLM、NLP、CV、推荐 | `算法` |
| 数据分析、商业分析、数据科学 | `数据` |
| UI、UX、视觉、交互、产品设计 | `设计` |
| 商务、销售、BD、渠道 | `商务/销售` |
| 首席科学家、Chief Scientist | `首席科学家` |
| 无法归入以上类别 | `其它` |

Category is a pool gate, not a score. A candidate passes when `候选人职位类目` intersects the JD category set. Missing or non-intersecting categories are excluded from this run and counted in the audit summary.

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

### Feishu Base source

The default matching database is:

```text
https://twoj0037lkv.feishu.cn/base/A80Xb9jOnaexcKswFkacPBoEnAf?table=tblcprcqjXs35bdq&view=vewkVFCtes
```

Use `lark-cli` with user identity and re-resolve the URL before each run; IDs and field names below are the verified baseline, not permission to assume the live schema never changes.

- Base: `A80Xb9jOnaexcKswFkacPBoEnAf` (`泛函｜公司&职位&候选人`)
- Jobs: `tblcprcqjXs35bdq` (`岗位`), category field `职位分类`
- Candidates: `tbldGJk6awx45Chc` (`候选人`), category field `候选人职位类目`
- Candidate JSON precedence: `候选人检索字段 JSON.文本` -> `候选人检索 JSON（Agent回填）` -> JSON attachment in `候选人检索字段 JSON.附件`
- Original resume field: `简历`; engagement field: `实习 & 正职`; display name: `姓名 & 昵称`

Read only the necessary fields and continue pagination until `has_more=false`. The Object field `候选人检索字段 JSON` is currently unsupported by OpenAPI; do not treat its omission as an empty candidate library. Parse each JSON value independently, keep the source `record_id`, and report total same-category rows, readable JSON rows, excluded rows, and scored rows.

Do not silently fall back to Workbench, SQLite, CSV, or another Base. If the Base is unavailable or the category pool has no readable JSON, report the gap.

### Feishu group delivery

1. Read `lark-base`, `lark-im`, and `lark-shared` before live execution.
2. Download only the selected candidates' original attachments with `base +record-download-attachment`, using each candidate `record_id` and the `简历` file token. Keep downloads in a task-specific directory and validate returned size; validate PDF signatures when the file is PDF.
3. Follow `Company Copy In Feishu`: use the main chat for one-JD delivery; for multiple JDs, create one header per JD and use `im +messages-reply --reply-in-thread` for its candidate introductions and resume files. Use idempotency keys. Use user identity when it can write to the group; if an external-group policy returns `230027` and the bot is already a member, retry as bot.
4. Read the target group's recent messages and verify the overview/header structure, candidate-to-resume order, and every expected file. A successful upload call alone is not delivery proof.

Use bundled script for deterministic batch checks:

```bash
python scripts/run_match.py --input input.json --output matches.json --top-n 5
```

Read these references only when needed:

- `references/base-field-mapping.md`: verified Feishu Base field mapping and category aliases.
- `schemas/match-input.schema.json`: expected local input shape.
- `schemas/match-output.schema.json`: expected output shape.

## Feedback And Darwin Iteration

When the user gives feedback such as “这个结果不准”, “实习生被推荐到正职了”, or “把这个规则写进 skill”, run this loop:

1. Classify feedback.
   - Wrong engagement type, missing hard condition, weak evidence, hallucinated evidence, ranking order, output format, or tool/writeback issue.
2. Convert feedback into a failing example.
   - Add or update one eval in `evals/evals.json`.
   - Include minimal candidate/job facts and the expected corrected behavior.
3. Read `skill-evolution-darwin-runner`.
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
| JD category is unclear | classify from the full JD and state the evidence | do not search every category to manufacture results |
| same-category row has no readable JSON | exclude it from scoring and count it | do not rank on filename alone |
| fewer than five eligible candidates | send every eligible candidate | do not pad from another category |
| Feishu write fails | preserve local output JSON or CSV | report exact table, field, and record that failed |
| LLM review conflicts with hard gate | hard gate wins | include conflict in risk reason |

## Do Not

- Do not train, fine-tune, distill, or modify model weights.
- Do not let semantic similarity override `实习 & 正职` hard mismatch.
- Do not let semantic similarity override the role-category pool gate.
- Do not invent portfolio claims, GitHub activity, work dates, education, or availability.
- Do not require a PDF when readable evidence came from HTML, a webpage, a Feishu document, GitHub, or another original format.
- Do not hide missing evidence behind confident language.
- Do not rewrite database schema unless the user asks for a schema migration.
- Do not rank a partial page as if it were the complete same-category pool.
- Do not replace a missing top-five resume with a lower-ranked candidate without saying so.
- Do not expose internal matching scores or execution status in company-facing messages.
- Do not flood the main group with every resume when matching multiple JDs; use one reply thread per JD.
- Do not write back to a live table after feedback iteration without an explicit writeback authorization.

## Internal Output Template

For each match:

```markdown
### {rank}. {job_or_candidate_name}
- 推荐等级：强匹配 / 可推荐 / 备选 / 弱匹配
- 综合分：{score}/100
- 职位分类：岗位为 {job_categories}，候选人为 {candidate_categories}，类目门控为 pass
- 实习/正职判断：候选人为 {candidate_type}，岗位为 {job_type}，兼容性为 {compatibility}
- 匹配理由：{3 concise bullets}
- 风险理由：{missing or mismatch risks}
- 证据引用：{source snippets or fields}
- 下一步建议：{interview question, portfolio check, or manual review action}
```

After the list, include:

```text
候选池审计：同类候选人 {category_rows} 人；可读 JSON {readable_json_rows} 人；因 JSON 缺失/损坏排除 {excluded_rows} 人；已评分 {scored_rows} 人；已发送简历 {sent_files}/{selected_count} 份。
```
