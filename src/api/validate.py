# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""A2A compliance validation endpoint — checks agent protocol compliance."""

import logging
import uuid

import httpx
from fastapi import APIRouter, Depends

from src.core.rate_limiter import rate_limit_by_ip
from src.core.url_validator import validate_public_url
from src.schemas.validate import ValidateRequest, ValidationCheck, ValidateResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/validate", response_model=ValidateResponse, dependencies=[Depends(rate_limit_by_ip)])
async def validate_agent(data: ValidateRequest) -> ValidateResponse:
    """Validate an agent's A2A protocol compliance.

    Runs a series of checks and returns detailed pass/fail results.
    """

    validate_public_url(data.url)
    base_url = data.url.rstrip("/")
    card_url = base_url + "/.well-known/agent-card.json"
    checks: list[ValidationCheck] = []
    suggestions: list[str] = []
    agent_name: str | None = None
    skills_count = 0
    card: dict | None = None
    first_skill_id: str | None = None

    # --- Check 1: agent_card_reachable ---
    resp = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(card_url)
        if resp.status_code == 200:
            checks.append(ValidationCheck(
                name="agent_card_reachable",
                passed=True,
                message=f"Agent card fetched successfully from {card_url}",
                severity="error",
            ))
        else:
            checks.append(ValidationCheck(
                name="agent_card_reachable",
                passed=False,
                message=f"Agent card returned HTTP {resp.status_code}",
                severity="error",
            ))
    except httpx.TimeoutException:
        checks.append(ValidationCheck(
            name="agent_card_reachable",
            passed=False,
            message="Agent card request timed out (10s)",
            severity="error",
        ))
    except (httpx.ConnectError, httpx.HTTPError) as exc:
        checks.append(ValidationCheck(
            name="agent_card_reachable",
            passed=False,
            message=f"Could not reach agent card endpoint: {exc}",
            severity="error",
        ))

    if not resp or resp.status_code != 200:
        # Can't proceed without a card — return early
        return ValidateResponse(
            url=base_url,
            valid=False,
            checks=checks,
            agent_name=None,
            skills_count=0,
            suggestions=["Ensure your agent serves /.well-known/agent-card.json"],
        )

    # --- Check 2: agent_card_valid_json ---
    try:
        card = resp.json()
        if not isinstance(card, dict):
            raise ValueError("Not a JSON object")
        checks.append(ValidationCheck(
            name="agent_card_valid_json",
            passed=True,
            message="Agent card is valid JSON",
            severity="error",
        ))
    except Exception:
        checks.append(ValidationCheck(
            name="agent_card_valid_json",
            passed=False,
            message="Agent card response is not valid JSON",
            severity="error",
        ))
        return ValidateResponse(
            url=base_url,
            valid=False,
            checks=checks,
            agent_name=None,
            skills_count=0,
            suggestions=["Agent card must return a valid JSON object"],
        )

    # --- Check 3: required_fields ---
    name = card.get("name")
    url_field = card.get("url")
    skills_raw = card.get("skills")
    missing = []
    if not name:
        missing.append("name")
    if not url_field:
        missing.append("url")
    if not isinstance(skills_raw, list):
        missing.append("skills (array)")

    if missing:
        checks.append(ValidationCheck(
            name="required_fields",
            passed=False,
            message=f"Missing required fields: {', '.join(missing)}",
            severity="error",
        ))
    else:
        checks.append(ValidationCheck(
            name="required_fields",
            passed=True,
            message="All required fields present (name, url, skills)",
            severity="error",
        ))

    agent_name = name if isinstance(name, str) else None
    skills_list = skills_raw if isinstance(skills_raw, list) else []

    # --- Check 4: has_description ---
    description = card.get("description", "")
    if description and isinstance(description, str) and description.strip():
        checks.append(ValidationCheck(
            name="has_description",
            passed=True,
            message="Agent has a description",
            severity="warning",
        ))
    else:
        checks.append(ValidationCheck(
            name="has_description",
            passed=False,
            message="Agent card is missing a description",
            severity="warning",
        ))
        suggestions.append("Add a description to your agent card")

    # --- Check 5: has_version ---
    version = card.get("version")
    if version:
        checks.append(ValidationCheck(
            name="has_version",
            passed=True,
            message=f"Version: {version}",
            severity="warning",
        ))
    else:
        checks.append(ValidationCheck(
            name="has_version",
            passed=False,
            message="Agent card is missing a version field",
            severity="warning",
        ))

    # --- Check 6: skills_valid ---
    valid_skills = 0
    invalid_skills = []
    for i, s in enumerate(skills_list):
        if not isinstance(s, dict):
            invalid_skills.append(f"Skill {i}: not a JSON object")
            continue
        s_id = s.get("id", s.get("skill_key", ""))
        s_name = s.get("name", "")
        s_desc = s.get("description", "")
        s_missing = []
        if not s_id:
            s_missing.append("id")
        if not s_name:
            s_missing.append("name")
        if not s_desc:
            s_missing.append("description")
        if s_missing:
            invalid_skills.append(
                f"Skill '{s_id or s_name or i}': missing {', '.join(s_missing)}"
            )
        else:
            valid_skills += 1
            if first_skill_id is None:
                first_skill_id = s_id

    skills_count = valid_skills
    if invalid_skills:
        checks.append(ValidationCheck(
            name="skills_valid",
            passed=False,
            message=f"{len(invalid_skills)} skill(s) invalid: {'; '.join(invalid_skills[:3])}",
            severity="error",
        ))
    elif valid_skills == 0:
        checks.append(ValidationCheck(
            name="skills_valid",
            passed=False,
            message="No valid skills found",
            severity="error",
        ))
    else:
        checks.append(ValidationCheck(
            name="skills_valid",
            passed=True,
            message=f"{valid_skills} skill(s) valid",
            severity="error",
        ))

    # --- Check 7: skills_have_examples ---
    has_examples = any(
        isinstance(s, dict) and s.get("examples")
        for s in skills_list
    )
    if has_examples:
        checks.append(ValidationCheck(
            name="skills_have_examples",
            passed=True,
            message="At least one skill has examples",
            severity="info",
        ))
    else:
        checks.append(ValidationCheck(
            name="skills_have_examples",
            passed=False,
            message="No skills have examples",
            severity="info",
        ))
        suggestions.append(
            "Add examples to your skills \u2014 they improve discoverability "
            "and help users understand your agent"
        )

    # --- Check 8: has_pricing ---
    pricing = card.get("pricing")
    if pricing:
        checks.append(ValidationCheck(
            name="has_pricing",
            passed=True,
            message="Pricing info present",
            severity="warning",
        ))
    else:
        checks.append(ValidationCheck(
            name="has_pricing",
            passed=False,
            message="No pricing information in agent card",
            severity="warning",
        ))
        suggestions.append("Add pricing info so users know the cost upfront")

    # --- Check 9: jsonrpc_reachable ---
    # Only attempt if we found at least one valid skill
    rpc_resp = None
    rpc_data = None
    if first_skill_id:
        rpc_payload = {
            "jsonrpc": "2.0",
            "id": "validation-test",
            "method": "tasks/send",
            "params": {
                "id": f"validate-{uuid.uuid4().hex[:12]}",
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "content": "Hello, this is a validation test."}],
                },
                "metadata": {"skill_id": first_skill_id},
            },
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                rpc_resp = await client.post(base_url, json=rpc_payload)
            if rpc_resp.status_code == 200:
                checks.append(ValidationCheck(
                    name="jsonrpc_reachable",
                    passed=True,
                    message="JSON-RPC endpoint responded successfully",
                    severity="error",
                ))
            else:
                checks.append(ValidationCheck(
                    name="jsonrpc_reachable",
                    passed=False,
                    message=f"JSON-RPC endpoint returned HTTP {rpc_resp.status_code}",
                    severity="error",
                ))
        except httpx.TimeoutException:
            checks.append(ValidationCheck(
                name="jsonrpc_reachable",
                passed=False,
                message="JSON-RPC request timed out (30s)",
                severity="error",
            ))
        except (httpx.ConnectError, httpx.HTTPError) as exc:
            checks.append(ValidationCheck(
                name="jsonrpc_reachable",
                passed=False,
                message=f"Could not reach JSON-RPC endpoint: {exc}",
                severity="error",
            ))
    else:
        checks.append(ValidationCheck(
            name="jsonrpc_reachable",
            passed=False,
            message="Skipped — no valid skills found to test",
            severity="error",
        ))

    # --- Check 10: jsonrpc_response_format ---
    if rpc_resp and rpc_resp.status_code == 200:
        try:
            rpc_data = rpc_resp.json()
            has_jsonrpc = rpc_data.get("jsonrpc") == "2.0"
            has_id = "id" in rpc_data
            has_result_or_error = "result" in rpc_data or "error" in rpc_data
            if has_jsonrpc and has_id and has_result_or_error:
                checks.append(ValidationCheck(
                    name="jsonrpc_response_format",
                    passed=True,
                    message="Response follows JSON-RPC 2.0 format",
                    severity="error",
                ))
            else:
                fmt_missing = []
                if not has_jsonrpc:
                    fmt_missing.append("jsonrpc: '2.0'")
                if not has_id:
                    fmt_missing.append("id")
                if not has_result_or_error:
                    fmt_missing.append("result or error")
                checks.append(ValidationCheck(
                    name="jsonrpc_response_format",
                    passed=False,
                    message=f"Response missing: {', '.join(fmt_missing)}",
                    severity="error",
                ))
        except Exception:
            checks.append(ValidationCheck(
                name="jsonrpc_response_format",
                passed=False,
                message="JSON-RPC response is not valid JSON",
                severity="error",
            ))
    else:
        checks.append(ValidationCheck(
            name="jsonrpc_response_format",
            passed=False,
            message="Skipped — JSON-RPC endpoint not reachable",
            severity="error",
        ))

    # --- Check 11: task_completed ---
    task_state = None
    if rpc_data and "result" in rpc_data:
        result = rpc_data["result"]
        status = result.get("status", {}) if isinstance(result, dict) else {}
        task_state = status.get("state") if isinstance(status, dict) else None
        if task_state == "completed":
            checks.append(ValidationCheck(
                name="task_completed",
                passed=True,
                message="Test task completed successfully",
                severity="warning",
            ))
        else:
            checks.append(ValidationCheck(
                name="task_completed",
                passed=False,
                message=f"Task state: {task_state or 'unknown'} (expected 'completed')",
                severity="warning",
            ))
            suggestions.append(
                "Your agent returned a failed status. "
                "Check your LLM API key and error handling"
            )
    else:
        checks.append(ValidationCheck(
            name="task_completed",
            passed=False,
            message="Skipped — no valid JSON-RPC result",
            severity="warning",
        ))

    # --- Check 12: has_artifacts ---
    if rpc_data and "result" in rpc_data:
        result = rpc_data["result"]
        artifacts = result.get("artifacts", []) if isinstance(result, dict) else []
        if artifacts and isinstance(artifacts, list) and len(artifacts) > 0:
            checks.append(ValidationCheck(
                name="has_artifacts",
                passed=True,
                message=f"Task returned {len(artifacts)} artifact(s)",
                severity="warning",
            ))
        else:
            checks.append(ValidationCheck(
                name="has_artifacts",
                passed=False,
                message="Task did not return any artifacts",
                severity="warning",
            ))
            suggestions.append(
                "Successful tasks should include at least one artifact with the result"
            )
    else:
        checks.append(ValidationCheck(
            name="has_artifacts",
            passed=False,
            message="Skipped — no valid JSON-RPC result",
            severity="warning",
        ))

    # Determine overall validity: all error-severity checks must pass
    valid = all(c.passed for c in checks if c.severity == "error")

    return ValidateResponse(
        url=base_url,
        valid=valid,
        checks=checks,
        agent_name=agent_name,
        skills_count=skills_count,
        suggestions=suggestions,
    )
