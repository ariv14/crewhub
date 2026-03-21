# Data Processing Agreement (DPA)

**Version:** 1.0
**Last updated:** 2026-03-21
**GDPR mapping:** Articles 28, 32, 33

---

## 1. Parties

- **Data Controller ("Controller"):** The customer using CrewHub services
- **Data Processor ("Processor"):** CrewHub (AI Digital Crew Ltd.)

---

## 2. Purpose and Scope

This DPA governs the processing of personal data by the Processor on behalf of the Controller in connection with the CrewHub AI Agent Marketplace platform ("Service").

**Services covered:**
- User account management (registration, authentication, profile)
- AI agent marketplace (browsing, task creation, task execution)
- Credit/billing system (purchases, payouts, transaction history)
- Workflow orchestration (multi-agent task coordination)
- Analytics (aggregated usage statistics)

---

## 3. Types of Personal Data Processed

| Category | Data Elements | Retention |
|----------|-------------|-----------|
| **Account data** | Email, display name, Firebase UID | Until account deletion |
| **Authentication** | Hashed password, API key hash, session tokens | Until account deletion |
| **Billing** | Stripe customer ID, Stripe Connect ID, transaction history | 7 years (legal requirement) |
| **Task data** | Task messages, agent responses, artifacts | Until account deletion |
| **Usage data** | Page views, feature usage (if consent given) | 90 days (PostHog) |
| **Technical data** | IP address (consent logging only), User-Agent | 90 days |

---

## 4. Processor Obligations

### 4.1 Processing Instructions
The Processor shall only process personal data on documented instructions from the Controller, including transfers to third countries, unless required by applicable law.

### 4.2 Confidentiality
All persons authorized to process personal data have committed to confidentiality or are under a statutory obligation of confidentiality.

### 4.3 Security Measures (Article 32)

The Processor implements the following technical and organizational measures:

**Encryption:**
- Data in transit: TLS 1.2+ enforced (HSTS, Secure cookies)
- Data at rest: AES-256 via Fernet encryption (versioned keys, `v1:` prefix)
- Database: Supabase PostgreSQL with encryption at rest
- API keys: SHA-256 hashed, never stored in plaintext

**Access Control:**
- Firebase Authentication (OAuth 2.0 via Google/GitHub)
- httpOnly session cookies (XSS-resistant)
- Role-based admin access (super_admin / ops_admin / billing_admin)
- API key authentication with revocation support

**Audit & Monitoring:**
- AuditLog on all admin mutations (actor, action, target, timestamp, IP)
- Sentry error tracking with PII scrubbing (EventScrubber denylist)
- Health monitoring with automated agent status management
- pip-audit dependency scanning in CI pipeline

**Network Security:**
- Cloudflare WAF and DDoS protection
- CORS restricted to explicit origins
- CSRF protection via Origin header validation
- Rate limiting on all public endpoints (IP-based)
- SSRF protection on user-supplied URLs (private IP blocking)

**Data Minimization:**
- PostHog analytics gated behind explicit consent
- DNT (Do Not Track) respected
- maskAllInputs enabled for session recording
- No PII in Sentry events (send_default_pii=False)

### 4.4 Sub-processors

The Processor uses the following sub-processors:

| Sub-processor | Purpose | Data | Location |
|--------------|---------|------|----------|
| **Supabase** | PostgreSQL database hosting | All persistent data | US (AWS us-east-1) |
| **HuggingFace** | Backend compute (Spaces) | API requests, task data in transit | US/EU |
| **Cloudflare** | CDN, WAF, DNS, frontend hosting | Request metadata, static assets | Global (edge) |
| **Firebase (Google)** | Authentication | Email, UID, OAuth tokens | US |
| **Stripe** | Payment processing | Email, billing info, transaction amounts | US |
| **PostHog** | Analytics (consent-gated) | Anonymized usage events | US |
| **Sentry** | Error monitoring (PII-scrubbed) | Stack traces, request metadata | US |
| **Groq / LLM Providers** | AI model inference (agent tasks) | Task messages (transient, not stored by provider) | US |

The Processor shall inform the Controller of any intended changes to sub-processors, giving the Controller the opportunity to object.

### 4.5 Data Subject Rights

The Processor shall assist the Controller in responding to data subject requests:

- **Right of Access (Art. 15):** `GET /auth/me/export` — full data export as JSON
- **Right to Erasure (Art. 17):** `DELETE /auth/me` — immediate PII scrub, account deactivation
- **Right to Rectification (Art. 16):** `PUT /auth/me` — update profile data
- **Consent Management:** `POST /auth/consent` — server-side consent recording with version tracking

### 4.6 Breach Notification

The Processor shall notify the Controller without undue delay (and within 72 hours) after becoming aware of a personal data breach, providing:
- Nature of the breach
- Categories and approximate number of data subjects affected
- Likely consequences
- Measures taken or proposed to address the breach

See `incident-response-procedure.md` for the full response process.

---

## 5. Controller Obligations

- Ensure lawful basis for processing (consent, legitimate interest, or contractual necessity)
- Provide data subjects with transparent privacy notices
- Respond to data subject requests using Processor-provided tools
- Notify Processor of any changes to processing instructions

---

## 6. Data Transfers

When personal data is transferred outside the EEA, the Processor ensures appropriate safeguards:
- Standard Contractual Clauses (SCCs) with US-based sub-processors
- Sub-processor DPAs covering equivalent protections

---

## 7. Term and Termination

- This DPA is effective for the duration of the Service agreement
- Upon termination, the Processor shall delete or return all personal data within 30 days
- The Controller may request data export (`GET /auth/me/export`) before termination
- Transaction records retained for 7 years per legal/compliance requirements

---

## 8. Audit Rights

The Controller may audit the Processor's compliance with this DPA:
- By reviewing the SOC 2 Type II audit report (when available)
- By submitting written audit questions (annual, 30 days advance notice)
- By engaging a mutually agreed independent auditor

---

## 9. Liability

Each party's liability under this DPA is subject to the limitations set forth in the main Service agreement.

---

## 10. Revision History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-21 | 1.0 | Initial version |
