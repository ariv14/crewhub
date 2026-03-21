# CrewHub Incident Response Procedure

**Version:** 1.0
**Last updated:** 2026-03-21
**Owner:** Engineering Lead
**Review cadence:** Quarterly
**SOC 2 mapping:** CC7.3, CC7.4, CC7.5

---

## 1. Purpose

This document defines how CrewHub detects, responds to, mitigates, and recovers from security incidents. It covers data breaches, service outages, unauthorized access, and vulnerability exploitation.

---

## 2. Definitions

| Term | Definition |
|------|-----------|
| **Security Incident** | Any event that compromises the confidentiality, integrity, or availability of CrewHub systems or user data |
| **Data Breach** | Unauthorized access to or disclosure of personal data (GDPR Article 4(12)) |
| **Severity P0** | Data breach, credential leak, or complete service outage |
| **Severity P1** | Partial service degradation, unauthorized access attempt (no data exfiltrated) |
| **Severity P2** | Vulnerability discovered (not yet exploited), minor service anomaly |
| **Incident Commander (IC)** | Person responsible for coordinating the response |

---

## 3. Incident Response Team

| Role | Responsibility |
|------|---------------|
| **Incident Commander** | Coordinates response, makes escalation decisions, owns communications |
| **Engineering Lead** | Investigates root cause, implements technical mitigations |
| **Operations** | Manages infrastructure, executes rollbacks, monitors recovery |
| **Communications** | Drafts user notifications, regulatory filings, status page updates |

---

## 4. Detection Sources

- **Sentry** — application errors, unhandled exceptions, PII leak alerts
- **Health Monitor** — automated agent endpoint checks (every 2-10 min adaptive)
- **Discord Alerts** — health check failures, feedback anomalies
- **GitHub Actions CI** — pip-audit vulnerability scans, test failures
- **Cloudflare WAF** — DDoS, bot traffic, suspicious request patterns
- **Stripe Webhooks** — payment anomalies, dispute spikes
- **User Reports** — feedback widget, Discord community, email

---

## 5. Response Phases

### Phase 1: Identification (0-15 min)

1. **Acknowledge** — First responder confirms the alert is a real incident (not false positive)
2. **Classify severity** — P0 / P1 / P2 based on definitions above
3. **Assign Incident Commander** — IC takes ownership and creates incident channel
4. **Log the incident** — Create entry in `AuditLog` via admin endpoint:
   - Action: `incident.opened`
   - Details: description, severity, detection source, initial scope

### Phase 2: Containment (15-60 min)

**Immediate actions by severity:**

| Severity | Actions |
|----------|---------|
| P0 | Rotate compromised credentials, revoke API keys, disable affected endpoints, activate CF WAF block rules |
| P1 | Rate limit affected endpoints, block suspicious IPs via CF WAF, disable affected feature flags |
| P2 | Document vulnerability, assess exploitability, schedule fix in next deploy |

**Technical containment toolkit:**
- **Credential rotation:** Rotate `SECRET_KEY`, `ENCRYPTION_KEY`, `STRIPE_SECRET_KEY` via HF Space secrets
- **API key revocation:** `POST /admin/users/{id}/revoke-key` or direct DB update
- **Agent isolation:** `POST /admin/agents/{id}/status` → set to `suspended` or `banned`
- **User suspension:** `POST /admin/users/{id}/status` → set `is_active=false`
- **WAF rules:** Cloudflare dashboard → Security → WAF → add block rule
- **Service kill switch:** `api.restart_space("arimatch1/crewhub")` (soft restart, no rebuild)

### Phase 3: Eradication (1-24 hours)

1. **Root cause analysis** — trace the attack vector through logs (Sentry, CF, application)
2. **Fix the vulnerability** — code change, dependency update, configuration fix
3. **Deploy fix** — push to staging, verify, promote to production via GitHub Actions
4. **Verify containment** — confirm the attack vector is closed
5. **Scan for lateral movement** — check audit logs for other affected accounts/agents

### Phase 4: Recovery (1-48 hours)

1. **Restore service** — re-enable disabled features, remove temporary WAF rules
2. **Re-enable affected accounts** — bulk reactivate via admin endpoints
3. **Data integrity check** — verify no unauthorized modifications to agents, tasks, transactions
4. **Monitor closely** — increase health check frequency for 72 hours

### Phase 5: Post-Incident Review (within 5 business days)

1. **Write post-mortem** — timeline, root cause, impact, what went well, what didn't
2. **Store in** `docs/compliance/post-mortems/YYYY-MM-DD-title.md`
3. **Identify improvements** — file tasks for prevention measures
4. **Update this procedure** — if gaps were identified during response
5. **Audit log entry** — `incident.closed` with resolution summary

---

## 6. Data Breach Notification (GDPR Article 33/34)

**Supervisory Authority (within 72 hours of awareness):**
- Required when breach likely results in risk to individuals' rights
- File with relevant DPA (Data Protection Authority)
- Include: nature of breach, categories of data, approximate number of records, consequences, mitigation measures

**Affected Users (without undue delay):**
- Required when breach likely results in HIGH risk to individuals
- Communication must be in clear, plain language
- Include: nature of breach, contact details for DPO/privacy team, likely consequences, measures taken
- Channel: email to affected users + in-app notification banner

**Documentation (always, regardless of notification):**
- Record in AuditLog: breach details, effects, remedial actions
- Retain for minimum 5 years for SOC 2 audit evidence

---

## 7. Communication Templates

### User Notification (Data Breach)

> Subject: Security Notice — Action Required
>
> We identified unauthorized access to [specific data] on [date]. We've secured the affected systems and [describe fix]. [Number] accounts were affected.
>
> What happened: [brief description]
> What data was involved: [categories — email, name, etc.]
> What we've done: [containment and fix actions]
> What you should do: [rotate password / review activity / no action needed]
>
> Questions? Contact privacy@crewhubai.com

### Status Page Update

> **[Date] — Investigating [P0/P1] Incident**
> We're aware of [issue description] and are actively investigating.
> Updates will be posted every [30 min / 1 hour].
>
> **[Date] — Resolved**
> The issue has been resolved. Root cause: [brief]. No user data was compromised.

---

## 8. Escalation Matrix

| Severity | Response Time | Notification | Escalation |
|----------|--------------|-------------|------------|
| P0 | 15 min | Immediate: all team + users if data breach | External: legal counsel, DPA if required |
| P1 | 1 hour | Engineering team + affected users if needed | Internal: engineering lead review |
| P2 | 24 hours | Engineering team only | Internal: prioritize in next sprint |

---

## 9. Testing

- **Tabletop exercise:** Quarterly — walk through a hypothetical P0 scenario
- **Credential rotation drill:** Semi-annually — practice rotating all production secrets
- **Recovery drill:** Semi-annually — practice restoring from backup / redeploying

---

## 10. Revision History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-21 | 1.0 | Initial version |
