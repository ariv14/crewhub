"""
E2E tests for Supervisor Agent Pattern.
Run: python tests/test_supervisor_e2e.py --api-key <key>
"""
import argparse
import asyncio
import httpx
import sys

DEFAULT_BASE_URL = "https://api-staging.crewhubai.com"


class SupervisorE2ETests:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        self.passed = 0
        self.failed = 0

    async def _post(self, path: str, data: dict) -> dict:
        if not path.endswith("/"):
            path += "/"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1{path}",
                json=data,
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def _get(self, path: str) -> dict:
        if not path.endswith("/"):
            path += "/"
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1{path}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def _report(self, name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    async def test_generate_plan(self):
        """Test: Goal -> plan with valid steps."""
        try:
            plan = await self._post("/workflows/supervisor/plan", {
                "goal": "Summarize a technical document and translate the summary to Spanish"
            })
            assert "plan_id" in plan, "Missing plan_id"
            assert len(plan.get("steps", [])) > 0, "No steps in plan"
            assert plan.get("total_estimated_credits", 0) > 0, "No cost estimate"
            self._report("Generate plan from goal", True, f"{len(plan['steps'])} steps, {plan['total_estimated_credits']} credits")
            return plan
        except Exception as e:
            self._report("Generate plan from goal", False, str(e))
            return None

    async def test_approve_and_save(self, plan: dict):
        """Test: Approve plan -> creates saved workflow."""
        if not plan:
            self._report("Approve plan -> saved workflow", False, "skipped (no plan)")
            return None
        try:
            workflow = await self._post("/workflows/supervisor/approve", {
                "plan_id": plan["plan_id"],
                "workflow_name": "E2E Test Supervisor Workflow",
            })
            assert workflow.get("pattern_type") == "supervisor", f"Wrong pattern_type: {workflow.get('pattern_type')}"
            assert workflow.get("id"), "Missing workflow ID"
            self._report("Approve plan -> saved workflow", True, f"workflow {workflow['id']}")
            return workflow
        except Exception as e:
            self._report("Approve plan -> saved workflow", False, str(e))
            return None

    async def test_workflow_in_list(self, workflow: dict):
        """Test: Saved supervisor workflow appears in list with filter."""
        if not workflow:
            self._report("Workflow in filtered list", False, "skipped (no workflow)")
            return
        try:
            result = await self._get("/workflows/?pattern_type=supervisor")
            items = result.get("items", result) if isinstance(result, dict) else result
            ids = [w["id"] for w in (items if isinstance(items, list) else [])]
            assert workflow["id"] in ids, "Workflow not found in supervisor-filtered list"
            self._report("Workflow in filtered list", True)
        except Exception as e:
            self._report("Workflow in filtered list", False, str(e))

    async def test_replan(self, plan: dict):
        """Test: Replan with feedback produces different plan."""
        if not plan:
            self._report("Replan with feedback", False, "skipped (no plan)")
            return
        try:
            # Generate a fresh plan first (previous was approved)
            fresh = await self._post("/workflows/supervisor/plan", {
                "goal": "Write a blog post about AI agents and proofread it"
            })
            new_plan = await self._post("/workflows/supervisor/replan", {
                "goal": "Write a blog post about AI agents and proofread it",
                "feedback": "Add a step for SEO optimization before publishing",
                "previous_plan_id": fresh["plan_id"],
            })
            assert new_plan.get("plan_id") != fresh["plan_id"], "Same plan_id returned"
            assert len(new_plan.get("steps", [])) > 0, "No steps in replanned workflow"
            self._report("Replan with feedback", True, f"{len(new_plan['steps'])} steps")
        except Exception as e:
            self._report("Replan with feedback", False, str(e))

    async def run_all(self):
        print("\n=== Supervisor E2E Tests ===\n")
        plan = await self.test_generate_plan()
        workflow = await self.test_approve_and_save(plan)
        await self.test_workflow_in_list(workflow)
        await self.test_replan(plan)

        print(f"\n  Results: {self.passed} passed, {self.failed} failed\n")
        return self.failed == 0


async def main():
    parser = argparse.ArgumentParser(description="Supervisor E2E Tests")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    tests = SupervisorE2ETests(args.base_url, args.api_key)
    success = await tests.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
