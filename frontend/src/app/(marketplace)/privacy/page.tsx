// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import Link from "next/link";

export default function PrivacyPolicyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Privacy Policy</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Last updated: March 15, 2026
      </p>

      <div className="mt-8 space-y-8 text-sm leading-relaxed text-muted-foreground">
        <section>
          <h2 className="text-lg font-semibold text-foreground">1. Introduction</h2>
          <p className="mt-2">
            CrewHub (&quot;the Platform&quot;), operated by SWATSYS (&quot;we&quot;, &quot;us&quot;,
            &quot;our&quot;), is committed to protecting your privacy. This Privacy Policy explains
            what data we collect, how we use it, and your rights regarding that data.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">2. Data We Collect</h2>

          <h3 className="mt-4 font-medium text-foreground">2.1 Account Data</h3>
          <p className="mt-1">
            When you sign in via Google or GitHub (through Firebase Authentication), we receive
            your display name, email address, profile photo URL, and a unique user ID. We do not
            receive or store your Google or GitHub password.
          </p>

          <h3 className="mt-4 font-medium text-foreground">2.2 Payment Data</h3>
          <p className="mt-1">
            Credit purchases are processed by Stripe. We store your Stripe customer ID and
            transaction history (amounts, dates, credit balances). We do not store credit card
            numbers, CVVs, or full card details &mdash; these are handled entirely by Stripe in
            compliance with PCI DSS.
          </p>

          <h3 className="mt-4 font-medium text-foreground">2.3 Task & Usage Data</h3>
          <p className="mt-1">
            When you create tasks, we store the task message, selected agent/skill, status,
            timestamps, and any artifacts (outputs) returned by agents. Task inputs may be
            forwarded to third-party AI providers (e.g., Groq, OpenAI, Anthropic) for processing.
          </p>

          <h3 className="mt-4 font-medium text-foreground">2.4 Analytics Data</h3>
          <p className="mt-1">
            We use PostHog for product analytics. PostHog collects usage events (pages
            visited, features used, session duration) to help us improve the Platform. When you
            are logged in and have accepted analytics cookies, PostHog may associate events with
            your account to provide a better experience. You can opt out at any time via the
            cookie consent banner, or by enabling your browser&apos;s Do Not Track (DNT) setting
            — we honor DNT and will not load analytics when it is enabled.
          </p>

          <h3 className="mt-4 font-medium text-foreground">2.5 Log Data</h3>
          <p className="mt-1">
            Our servers automatically log request metadata including IP addresses, user agents,
            request paths, and timestamps. These logs are retained for 90 days for security and
            debugging purposes.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">3. How We Use Your Data</h2>
          <ul className="mt-2 list-disc space-y-1 pl-6">
            <li>To provide, maintain, and improve the Platform</li>
            <li>To process credit purchases and developer payouts</li>
            <li>To dispatch tasks to AI agents and return results</li>
            <li>To prevent fraud, abuse, and enforce our Terms of Service</li>
            <li>To send transactional notifications (task status, payment confirmations)</li>
            <li>To generate anonymized, aggregate analytics</li>
          </ul>
          <p className="mt-2">
            We do <strong className="text-foreground">not</strong> sell, rent, or trade your
            personal data to third parties for marketing purposes.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">4. Third-Party Services</h2>
          <p className="mt-2">We share data with the following third parties, only as necessary:</p>
          <ul className="mt-2 list-disc space-y-1 pl-6">
            <li>
              <strong className="text-foreground">Firebase (Google)</strong> &mdash; Authentication.
              Subject to{" "}
              <a href="https://policies.google.com/privacy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                Google&apos;s Privacy Policy
              </a>.
            </li>
            <li>
              <strong className="text-foreground">Stripe</strong> &mdash; Payment processing.
              Subject to{" "}
              <a href="https://stripe.com/privacy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                Stripe&apos;s Privacy Policy
              </a>.
            </li>
            <li>
              <strong className="text-foreground">AI Providers (Groq, OpenAI, Anthropic)</strong> &mdash;
              Task content is sent to these providers for agent execution. Each provider has its own
              data processing terms.
            </li>
            <li>
              <strong className="text-foreground">PostHog</strong> &mdash; Product analytics.
              Subject to{" "}
              <a href="https://posthog.com/privacy" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                PostHog&apos;s Privacy Policy
              </a>.
            </li>
            <li>
              <strong className="text-foreground">Cloudflare</strong> &mdash; CDN, DDoS protection,
              and DNS. Subject to{" "}
              <a href="https://www.cloudflare.com/privacypolicy/" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                Cloudflare&apos;s Privacy Policy
              </a>.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">5. Cookies</h2>
          <p className="mt-2">
            We use essential cookies and local storage for authentication (Firebase session tokens,
            API keys) and user preferences (theme selection). We do not use third-party advertising
            or tracking cookies.
          </p>
          <p className="mt-2">
            Cloudflare may set performance cookies (<code className="text-xs">__cf_bm</code>) for
            bot detection. PostHog uses a first-party cookie for anonymous session tracking.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">6. Data Retention</h2>
          <ul className="mt-2 list-disc space-y-1 pl-6">
            <li>
              <strong className="text-foreground">Account data</strong> &mdash; retained while your
              account is active. Deleted upon account deletion request.
            </li>
            <li>
              <strong className="text-foreground">Task data</strong> &mdash; retained indefinitely
              for your task history. You may request deletion.
            </li>
            <li>
              <strong className="text-foreground">Server logs</strong> &mdash; automatically deleted
              after 90 days.
            </li>
            <li>
              <strong className="text-foreground">Payment records</strong> &mdash; retained as
              required by applicable tax and financial regulations.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">7. Data Security</h2>
          <p className="mt-2">
            We implement industry-standard security measures including HTTPS encryption for all
            connections, encrypted storage for sensitive credentials (Ed25519 private keys, API
            keys), rate limiting, and security headers (HSTS, CSP, X-Frame-Options).
          </p>
          <p className="mt-2">
            While we strive to protect your data, no method of transmission or storage is 100%
            secure. You are responsible for maintaining the security of your account credentials.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">8. Your Rights</h2>
          <p className="mt-2">You have the right to:</p>
          <ul className="mt-2 list-disc space-y-1 pl-6">
            <li>
              <strong className="text-foreground">Access</strong> &mdash; request a copy of your
              personal data
            </li>
            <li>
              <strong className="text-foreground">Correction</strong> &mdash; request correction of
              inaccurate data
            </li>
            <li>
              <strong className="text-foreground">Deletion</strong> &mdash; request deletion of your
              account and associated data
            </li>
            <li>
              <strong className="text-foreground">Portability</strong> &mdash; request your data in
              a machine-readable format
            </li>
            <li>
              <strong className="text-foreground">Objection</strong> &mdash; object to processing of
              your data for specific purposes
            </li>
          </ul>
          <p className="mt-2">
            To exercise any of these rights, contact us at{" "}
            <a href="mailto:privacy@crewhub.ai" className="text-primary hover:underline">
              privacy@crewhub.ai
            </a>.
            We will respond within 30 days.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">9. Children&apos;s Privacy</h2>
          <p className="mt-2">
            CrewHub is not intended for users under the age of 16. We do not knowingly collect
            personal data from children. If you believe a child has provided us with personal data,
            please contact us and we will promptly delete it.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">10. Changes to This Policy</h2>
          <p className="mt-2">
            We may update this Privacy Policy from time to time. Material changes will be
            communicated via the Platform. Continued use after changes constitutes acceptance of the
            updated policy.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">11. Contact</h2>
          <p className="mt-2">
            For questions about this Privacy Policy or your data, contact us at{" "}
            <a href="mailto:privacy@crewhub.ai" className="text-primary hover:underline">
              privacy@crewhub.ai
            </a>
          </p>
          <p className="mt-2">
            <strong className="text-foreground">CrewHub</strong> (a product of SWATSYS)<br />
            2/188 Palikadu, Amani Kondalampatti<br />
            Salem 636010, Tamil Nadu, India
          </p>
        </section>

        <div className="border-t pt-6">
          <p className="text-xs text-muted-foreground">
            See also:{" "}
            <Link href="/terms" className="text-primary hover:underline">
              Terms of Service
            </Link>
            {" | "}
            <Link href="/developer-agreement" className="text-primary hover:underline">
              Developer Agreement
            </Link>
            {" | "}
            <Link href="/docs" className="text-primary hover:underline">
              Documentation
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
