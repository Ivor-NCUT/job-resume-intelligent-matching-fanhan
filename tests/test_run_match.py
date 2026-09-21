import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "run_match.py"
SPEC = importlib.util.spec_from_file_location("run_match", MODULE_PATH)
run_match = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = run_match
SPEC.loader.exec_module(run_match)


class CategoryGateTest(unittest.TestCase):
    def test_job_to_candidates_ranks_only_complete_same_category_json(self):
        data = {
            "direction": "job_to_candidates",
            "jobs": [{"id": "j1", "title": "算法工程师", "description": "LLM RAG Python", "attributes": {"type": "全职"}}],
            "candidates": [
                {"id": "a", "name": "算法一", "候选人职位类目": ["算法"], "实习 & 正职": "正职", "候选人检索字段 JSON.文本": '{"skills":"LLM RAG Python"}'},
                {"id": "b", "name": "算法二", "候选人职位类目": ["算法"], "实习 & 正职": "正职", "resume_json": "not-json"},
                {"id": "c", "name": "研发一", "候选人职位类目": ["研发"], "实习 & 正职": "正职", "resume_json": {"skills": "LLM RAG Python"}},
            ],
        }

        result = run_match.run(data)

        self.assertEqual([row["candidate_id"] for row in result["matches"]], ["a"])
        self.assertEqual(result["pool_audit"][0]["job_categories"], ["算法"])
        self.assertEqual(result["pool_audit"][0]["category_rows"], 2)
        self.assertEqual(result["pool_audit"][0]["json_excluded_rows"], 1)


if __name__ == "__main__":
    unittest.main()
