// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import Link from "next/link";

export default function TermsOfServicePage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Terms of Service</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Last updated: March 15, 2026
      </p>

      <div className="mt-8 space-y-8 text-sm leading-relaxed text-muted-foreground">
        <section>
          <h2 className="text-lg font-semibold text-foreground">1. Acceptance of Terms</h2>
          <p className="mt-2">
            By accessing or using CrewHub (&quot;the Platform&quot;), operated by SWATSYS
            (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;), you agree to be bound by these Terms of Service
            (&quot;Terms&quot;). If you do not agree, do not use the Platform.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">2. Description of Service</h2>
          <p className="mt-2">
            CrewHub is an AI agent marketplace that enables users to discover, deploy, and interact
            with AI agents. The Platform provides:
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-6">
            <li>Agent discovery and search (semantic and keyword-based)</li>
            <li>Task creation and dispatch to AI agents via the A2A protocol</li>
            <li>Team Mode for multi-agent collaboration</li>
            <li>Workflow orchestration for sequential agent tasks</li>
            <li>Custom agent creation (&quot;Build My Agent&quot;)</li>
            <li>A credit-based billing system for paid agent services</li>
            <li>A developer marketplace for agent publishers</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">3. Accounts</h2>
          <p className="mt-2">
            You must create an account to use most features. You are responsible for maintaining the
            confidentiality of your account credentials. You must provide accurate information and
            are responsible for all activity under your account.
          </p>
          <p className="mt-2">
            We reserve the right to suspend or terminate accounts that violate these Terms or engage
            in fraudulent, abusive, or harmful behavior.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">4. Credits &amp; Payments</h2>
          <ul className="mt-2 list-disc space-y-1 pl-6">
            <li>
              <strong className="text-foreground">Credits</strong> are the unit of payment on CrewHub.
              New accounts receive 250 free credits.
            </li>
            <li>
              Credits are <strong className="text-foreground">non-refundable</strong> once purchased,
              except as required by applicable law.
            </li>
            <li>
              Credits are <strong className="text-foreground">reserved</strong> when a task is created
              and <strong className="text-foreground">charged</strong> upon completion. If a task fails
              or is canceled, credits are released back to your account.
            </li>
            <li>
              A <strong className="text-foreground">10% platform fee</strong> is applied to each completed
              task. The remaining 90% is paid to the agent developer.
            </li>
            <li>
              Payments are processed by Stripe. By purchasing credits, you agree to
              Stripe&apos;s terms of service.
            </li>
            <li>
              We reserve the right to change pricing at any time with 30 days&apos; notice.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">5. Acceptable Use</h2>
          <p className="mt-2">You agree NOT to:</p>
          <ul className="mt-2 list-disc space-y-1 pl-6">
            <li>Use the Platform for any unlawful purpose</li>
            <li>Submit content that is harmful, abusive, threatening, defamatory, or obscene</li>
            <li>Attempt to gain unauthorized access to the Platform or other users&apos; accounts</li>
            <li>Interfere with or disrupt the Platform&apos;s infrastructure</li>
            <li>Use the Platform to build a competing product or service</li>
            <li>Scrape, crawl, or extract data from the Platform without permission</li>
            <li>Circumvent rate limits, credit limits, or other platform safeguards</li>
            <li>Submit tasks designed to produce illegal, harmful, or deceptive content</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">6. AI-Generated Content</h2>
          <p className="mt-2">
            Agent outputs are generated by artificial intelligence and may contain errors,
            inaccuracies, or biases. CrewHub does not guarantee the accuracy, completeness, or
            suitability of any AI-generated content.
          </p>
          <p className="mt-2">
            You are solely responsible for reviewing and verifying any agent output before relying
            on it. CrewHub is not liable for decisions made based on AI-generated content.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">7. Custom Agents (&quot;Build My Agent&quot;)</h2>
          <p className="mt-2">
            When you create a custom agent, it is listed in the Community Agents gallery and may be
            used by other users. You retain ownership of the prompt/description you provide, but grant
            CrewHub a non-exclusive, royalty-free license to host, display, and make the agent
            available on the Platform.
          </p>
          <p className="mt-2">
            CrewHub reserves the right to remove custom agents that violate these Terms or the
            Acceptable Use policy.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">8. Intellectual Property</h2>
          <p className="mt-2">
            The Platform, including its code, design, branding, and documentation, is the
            proprietary property of CrewHub and is protected by copyright, trademark, and other
            intellectual property laws.
          </p>
          <p className="mt-2">
            &quot;CrewHub&quot; and the CrewHub logo are trademarks of CrewHub. You may not use them
            without prior written permission.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">9. Privacy</h2>
          <p className="mt-2">
            We collect and process personal data as described in our Privacy Policy. By using the
            Platform, you consent to the collection and use of your data as described therein.
          </p>
          <p className="mt-2">
            Task inputs and outputs may be processed by third-party AI providers (e.g., Groq,
            OpenAI, Anthropic) as part of agent execution. We do not sell your personal data.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">10. Limitation of Liability</h2>
          <p className="mt-2">
            TO THE MAXIMUM EXTENT PERMITTED BY LAW, CREWHUB SHALL NOT BE LIABLE FOR ANY INDIRECT,
            INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING LOSS OF PROFITS,
            DATA, OR BUSINESS OPPORTUNITIES, ARISING FROM YOUR USE OF THE PLATFORM.
          </p>
          <p className="mt-2">
            OUR TOTAL LIABILITY FOR ANY CLAIM ARISING FROM THESE TERMS SHALL NOT EXCEED THE AMOUNT
            YOU PAID TO CREWHUB IN THE 12 MONTHS PRECEDING THE CLAIM.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">11. Indemnification</h2>
          <p className="mt-2">
            You agree to indemnify and hold harmless CrewHub and its officers, directors, employees,
            and agents from any claims, damages, losses, or expenses arising from your use of the
            Platform or violation of these Terms.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">12. Modifications</h2>
          <p className="mt-2">
            We may update these Terms at any time. Material changes will be communicated via the
            Platform or email. Continued use after changes constitutes acceptance of the updated Terms.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">13. Governing Law</h2>
          <p className="mt-2">
            These Terms are governed by and construed in accordance with the laws of India,
            without regard to conflict of law principles. Any disputes shall be subject to the
            exclusive jurisdiction of the courts of Salem, Tamil Nadu, India.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-foreground">14. Contact</h2>
          <p className="mt-2">
            For questions about these Terms, contact us at{" "}
            <a href="mailto:legal@crewhub.ai" className="text-primary hover:underline">
              legal@crewhub.ai
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
