#!/usr/bin/env python3
"""Lightweight no-training job/resume matcher."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

INTERN_PATTERNS = [r"实习", r"实习生", r"找实习", r"\bintern(ship)?\b"]
FULL_TIME_PATTERNS = [r"正职", r"全职", r"正式", r"社招", r"\bfull[- ]?time\b"]
SENIOR_TITLE_PATTERNS = [r"负责人", r"主管", r"经理", r"总监", r"合伙人", r"\bhead\b", r"\blead\b", r"\bmanager\b", r"\bdirector\b"]
SKILL_TERMS = ["ai", "agent", "llm", "rag", "python", "typescript", "react", "node", "sql", "数据", "增长", "运营", "销售", "产品", "客户成功", "内容", "小红书", "飞书", "自动化", "mcp", "prompt"]
CATEGORY_ALIASES = {"数据分析": "数据", "无匹配标签": "其它"}
CATEGORY_PATTERNS = {
    "增长/运营/市场": [r"增长", r"市场", r"(?<!产品)运营", r"growth", r"marketing"],
    "产品": [r"产品经理", r"产品运营", r"product manager", r"\bpm\b"],
    "算法": [r"算法", r"机器学习", r"深度学习", r"\bllm\b", r"\bnlp\b", r"\bcv\b", r"推荐系统"],
    "数据": [r"数据分析", r"商业分析", r"数据科学", r"data analyst", r"data scientist"],
    "设计": [r"设计", r"\bui\b", r"\bux\b"],
    "商务/销售": [r"商务", r"销售", r"\bbd\b", r"渠道"],
    "首席科学家": [r"首席科学家", r"chief scientist"],
}
ENGINEERING_PATTERNS = [r"前端", r"后端", r"全栈", r"软件工程", r"开发工程", r"基础设施", r"devops", r"\bsre\b", r"客户端", r"服务端"]


@dataclass
class EngagementDecision:
    candidate_type: str
    job_type: str
    compatibility: str
    cap: int | None
    risk: str


def has_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def normalize_categories(raw: Any) -> list[str]:
    values = raw if isinstance(raw, list) else [raw]
    return list(dict.fromkeys(CATEGORY_ALIASES.get(str(value).strip(), str(value).strip()) for value in values if value))


def infer_role_categories(text: str) -> list[str]:
    categories = [name for name, patterns in CATEGORY_PATTERNS.items() if has_any(patterns, text)]
    if has_any(ENGINEERING_PATTERNS, text) or (not categories and has_any([r"工程师", r"研发", r"开发"], text)):
        categories.append("研发")
    return categories or ["其它"]


def candidate_categories(candidate: dict[str, Any]) -> list[str]:
    return normalize_categories(candidate.get("role_categories") or candidate.get("候选人职位类目"))


def job_categories(job: dict[str, Any]) -> list[str]:
    explicit = normalize_categories(job.get("role_categories") or job.get("role_category") or job.get("职位分类"))
    return explicit or infer_role_categories(build_job_text(job))


def resume_json_value(candidate: dict[str, Any]) -> Any:
    return candidate.get("resume_json") or candidate.get("候选人检索字段 JSON.文本") or candidate.get("候选人检索 JSON（Agent回填）")


def has_readable_resume_json(candidate: dict[str, Any]) -> bool:
    value = resume_json_value(candidate)
    if isinstance(value, dict):
        return True
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        return isinstance(json.loads(value), dict)
    except json.JSONDecodeError:
        return False


def normalize_candidate_type(raw: str | None) -> str:
    text = (raw or "").strip().lower()
    has_intern = has_any(INTERN_PATTERNS, text)
    has_full = has_any(FULL_TIME_PATTERNS, text)
    if has_intern and has_full:
        return "both"
    if has_intern:
        return "internship"
    if has_full:
        return "full_time"
    return "unknown"


def infer_job_type(title: str | None, description: str | None, attrs: dict[str, Any] | None = None) -> str:
    parts = [title or "", description or ""]
    if attrs:
        parts.extend(str(v) for v in attrs.values() if v is not None)
    text = " ".join(parts).lower()
    has_intern = has_any(INTERN_PATTERNS, text)
    has_full = has_any(FULL_TIME_PATTERNS, text)
    if has_intern and has_full:
        return "both"
    if has_intern:
        return "internship"
    if has_full or has_any(SENIOR_TITLE_PATTERNS, text):
        return "full_time"
    return "unknown"


def engagement_decision(candidate_type: str, job_type: str) -> EngagementDecision:
    if candidate_type == "both" and job_type != "unknown":
        return EngagementDecision(candidate_type, job_type, "pass", None, "")
    if job_type == "both" and candidate_type != "unknown":
        return EngagementDecision(candidate_type, job_type, "pass", None, "")
    if candidate_type == job_type and candidate_type != "unknown":
        return EngagementDecision(candidate_type, job_type, "pass", None, "")
    if candidate_type == "unknown" and job_type != "unknown":
        return EngagementDecision(candidate_type, job_type, "risk", 78, "候选人【实习 & 正职】为空或不明确")
    if job_type == "unknown" and candidate_type != "unknown":
        return EngagementDecision(candidate_type, job_type, "risk", 82, "岗位类型无法从名称或要求中明确推断")
    if candidate_type == "internship" and job_type == "full_time":
        return EngagementDecision(candidate_type, job_type, "mismatch", 45, "候选人在找实习，但岗位推断为正职")
    if candidate_type == "full_time" and job_type == "internship":
        return EngagementDecision(candidate_type, job_type, "mismatch", 35, "候选人在找正职，但岗位推断为实习")
    return EngagementDecision(candidate_type, job_type, "risk", 75, "候选人与岗位类型兼容性不确定")


def tokenize(text: str) -> set[str]:
    lowered = text.lower()
    latin = set(re.findall(r"[a-z0-9][a-z0-9+#.-]{1,}", lowered))
    chinese_terms = {term for term in SKILL_TERMS if term in lowered}
    return latin | chinese_terms


def keyword_score(candidate_text: str, job_text: str) -> tuple[int, list[str]]:
    c_terms = tokenize(candidate_text)
    j_terms = tokenize(job_text)
    overlap = sorted((c_terms & j_terms), key=str.lower)
    if not j_terms:
        return 0, []
    score = min(100, round(100 * len(overlap) / max(4, min(len(j_terms), 16))))
    return score, overlap[:10]


def rule_score(decision: EngagementDecision, overlap: list[str], candidate: dict[str, Any], job: dict[str, Any]) -> int:
    score = 50
    if decision.compatibility == "pass":
        score += 25
    elif decision.compatibility == "risk":
        score += 8
    else:
        score -= 25
    score += min(20, len(overlap) * 4)
    if candidate.get("portfolio_text") or candidate.get("links"):
        score += 5
    if job.get("must_have") and overlap:
        score += 5
    return max(0, min(100, score))


def semantic_proxy_score(candidate_text: str, job_text: str, overlap: list[str]) -> int:
    base = min(80, 35 + len(overlap) * 8)
    if len(candidate_text) > 200 and len(job_text) > 120:
        base += 10
    return max(0, min(100, base))


def recommendation_level(score: int, decision: EngagementDecision) -> str:
    if decision.compatibility == "mismatch":
        return "弱匹配"
    if score >= 82:
        return "强匹配"
    if score >= 68:
        return "可推荐"
    if score >= 50:
        return "备选"
    return "弱匹配"


def build_candidate_text(candidate: dict[str, Any]) -> str:
    links = candidate.get("links", []) or []
    if isinstance(links, str):
        links = [links]
    fields = [
        candidate.get("profile_text"),
        candidate.get("resume_text"),
        candidate.get("portfolio_text"),
        candidate.get("summary"),
        " ".join(candidate.get("skills", []) or []),
        " ".join(links),
        json.dumps(resume_json_value(candidate), ensure_ascii=False) if isinstance(resume_json_value(candidate), dict) else resume_json_value(candidate),
    ]
    return " ".join(str(v) for v in fields if v)


def build_job_text(job: dict[str, Any]) -> str:
    fields = [job.get("title"), job.get("description"), job.get("requirements"), job.get("must_have"), job.get("nice_to_have"), " ".join(job.get("skills", []) or [])]
    return " ".join(str(v) for v in fields if v)


def match_one(candidate: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    candidate_type = normalize_candidate_type(candidate.get("engagement") or candidate.get("实习 & 正职"))
    job_type = infer_job_type(job.get("title") or job.get("岗位名称"), build_job_text(job), job.get("attributes"))
    decision = engagement_decision(candidate_type, job_type)
    candidate_text = build_candidate_text(candidate)
    job_text = build_job_text(job)
    kw, overlap = keyword_score(candidate_text, job_text)
    semantic = semantic_proxy_score(candidate_text, job_text, overlap)
    rules = rule_score(decision, overlap, candidate, job)
    llm_placeholder = round((semantic + rules) / 2)
    raw_score = round(0.25 * kw + 0.30 * semantic + 0.25 * rules + 0.20 * llm_placeholder)
    score = min(raw_score, decision.cap) if decision.cap is not None else raw_score
    risks = [decision.risk] if decision.risk else []
    if not overlap:
        risks.append("候选人与岗位关键词重合较少，需要人工复核")
    return {
        "candidate_id": candidate.get("id"),
        "candidate_name": candidate.get("name") or candidate.get("姓名"),
        "job_id": job.get("id"),
        "job_title": job.get("title") or job.get("岗位名称"),
        "score": score,
        "recommendation_level": recommendation_level(score, decision),
        "candidate_type": decision.candidate_type,
        "job_type": decision.job_type,
        "compatibility": decision.compatibility,
        "candidate_categories": candidate_categories(candidate),
        "job_categories": job_categories(job),
        "keyword_score": kw,
        "semantic_score": semantic,
        "rule_score": rules,
        "llm_review_score": llm_placeholder,
        "matched_terms": overlap,
        "match_reason": [
            f"共同能力或领域词：{', '.join(overlap[:6])}" if overlap else "缺少明显共同关键词",
            f"实习/正职判断：候选人为 {decision.candidate_type}，岗位为 {decision.job_type}，兼容性为 {decision.compatibility}",
        ],
        "risk_reason": risks,
    }


def run(data: dict[str, Any]) -> dict[str, Any]:
    top_n = int(data.get("top_n") or 5)
    direction = data.get("direction") or "candidate_to_jobs"
    rows = []
    audits = []
    if direction == "job_to_candidates":
        for job in data.get("jobs", []):
            wanted = set(job_categories(job))
            category_pool = [candidate for candidate in data.get("candidates", []) if wanted.intersection(candidate_categories(candidate))]
            readable = [candidate for candidate in category_pool if has_readable_resume_json(candidate)]
            matches = [match_one(candidate, job) for candidate in readable]
            eligible = [match for match in matches if match["compatibility"] != "mismatch"]
            eligible.sort(key=lambda item: (-item["score"], str(item.get("candidate_id") or "")))
            for rank, match in enumerate(eligible[:top_n], 1):
                match["rank"] = rank
                rows.append(match)
            audits.append({
                "job_id": job.get("id"),
                "job_categories": sorted(wanted),
                "category_rows": len(category_pool),
                "readable_json_rows": len(readable),
                "json_excluded_rows": len(category_pool) - len(readable),
                "hard_gate_excluded_rows": len(matches) - len(eligible),
                "scored_rows": len(matches),
                "selected_count": min(top_n, len(eligible)),
            })
        return {"algorithm_version": "agentic-matching-lite-v0.3-category-gate", "direction": direction, "top_n": top_n, "pool_audit": audits, "matches": rows}

    for candidate in data.get("candidates", []):
        matches = [match_one(candidate, job) for job in data.get("jobs", [])]
        matches.sort(key=lambda item: item["score"], reverse=True)
        for rank, match in enumerate(matches[:top_n], 1):
            match["rank"] = rank
            rows.append(match)
    return {"algorithm_version": "agentic-matching-lite-v0.3-category-gate", "direction": direction, "top_n": top_n, "pool_audit": audits, "matches": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--top-n", type=int)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if args.top_n is not None:
        data["top_n"] = args.top_n
    result = run(data)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
