"""
E2E tests for Hierarchical Agent Teams.
Run: python tests/test_hierarchical_e2e.py --api-key <key>
"""
import argparse
import asyncio
import httpx
import sys

DEFAULT_BASE_URL = "https://api-staging.crewhubai.com"


class HierarchicalE2ETests:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        self.passed = 0
        self.failed = 0

    async def _post(self, path: str, data: dict) -> dict:
        if not path.endswith("/"):
            path += "/"
        url = f"{self.base_url}/api/v1{path}"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.post(url, json=data, headers=self.headers)
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

    async def _delete(self, path: str):
        if not path.endswith("/"):
            path += "/"
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.delete(
                f"{self.base_url}/api/v1{path}",
                headers=self.headers,
            )
            return resp.status_code

    def _report(self, name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    async def test_create_hierarchical_workflow(self):
        """Test: Create a hierarchical workflow with sub-workflow step."""
        try:
            # First create a simple "child" workflow
            child = await self._post("/workflows/", {
                "name": "E2E Child Workflow",
                "description": "Sub-workflow for hierarchical test",
                "pattern_type": "manual",
                "steps": [],
            })
            child_id = child["id"]

            # Create parent hierarchical workflow with sub-workflow step
            parent = await self._post("/workflows/", {
                "name": "E2E Hierarchical Workflow",
                "description": "Parent workflow with nested sub-workflow",
                "pattern_type": "hierarchical",
                "steps": [
                    {"sub_workflow_id": child_id, "step_group": 0, "label": "Run child pipeline"},
                ],
            })

            assert parent.get("pattern_type") == "hierarchical", f"Wrong pattern_type: {parent.get('pattern_type')}"
            assert len(parent.get("steps", [])) == 1, "Expected 1 step"
            assert parent["steps"][0].get("sub_workflow_id") == child_id, "sub_workflow_id not set"

            self._report("Create hierarchical workflow", True, f"parent={parent['id']}, child={child_id}")
            return parent, child_id
        except Exception as e:
            self._report("Create hierarchical workflow", False, str(e))
            return None, None

    async def test_cycle_detection(self):
        """Test: Circular sub-workflow reference is rejected."""
        try:
            # Create workflow A
            wf_a = await self._post("/workflows/", {
                "name": "E2E Cycle A",
                "pattern_type": "hierarchical",
                "steps": [],
            })

            # Try to make A reference itself
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.put(
                    f"{self.base_url}/api/v1/workflows/{wf_a['id']}/",
                    json={
                        "steps": [{"sub_workflow_id": wf_a["id"], "step_group": 0}],
                    },
                    headers=self.headers,
                )

            # Should be rejected (400)
            if resp.status_code == 400:
                self._report("Cycle detection (self-reference)", True, "correctly rejected")
            else:
                self._report("Cycle detection (self-reference)", False, f"status {resp.status_code}")

            # Cleanup
            await self._delete(f"/workflows/{wf_a['id']}")
        except Exception as e:
            self._report("Cycle detection (self-reference)", False, str(e))

    async def run_all(self):
        print("\n=== Hierarchical E2E Tests ===\n")
        parent, child_id = await self.test_create_hierarchical_workflow()
        await self.test_cycle_detection()

        # Cleanup
        if parent:
            await self._delete(f"/workflows/{parent['id']}")
        if child_id:
            await self._delete(f"/workflows/{child_id}")

        print(f"\n  Results: {self.passed} passed, {self.failed} failed\n")
        return self.failed == 0


async def main():
    parser = argparse.ArgumentParser(description="Hierarchical E2E Tests")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    tests = HierarchicalE2ETests(args.base_url, args.api_key)
    success = await tests.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
