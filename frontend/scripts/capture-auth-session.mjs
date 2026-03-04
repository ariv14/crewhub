#!/usr/bin/env node
/**
 * Opens a visible Chromium browser on the staging login page.
 * After you sign in with Google, it captures localStorage + cookies
 * and saves them to .playwright-auth/session.json for reuse in tests.
 */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'fs';
import { resolve } from 'path';

const STAGING_URL = 'https://crewhub-marketplace-staging.pages.dev';
const SESSION_DIR = resolve(import.meta.dirname, '..', '.playwright-auth');
const SESSION_FILE = resolve(SESSION_DIR, 'session.json');

async function main() {
  console.log('Opening browser... Sign in with Google on the staging site.');
  console.log('After you see the dashboard, press Enter in this terminal.\n');

  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto(`${STAGING_URL}/login/`);

  // Wait for user to press Enter after signing in
  await new Promise((resolve) => {
    process.stdin.setRawMode?.(false);
    process.stdin.resume();
    process.stdin.once('data', resolve);
  });

  // Capture auth state
  const localStorage = await page.evaluate(() => {
    const data = {};
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      data[key] = window.localStorage.getItem(key);
    }
    return data;
  });

  const cookies = await context.cookies();

  // Check if auth token exists
  const token = localStorage['auth_token'];
  if (!token) {
    console.error('ERROR: No auth_token found in localStorage. Did you sign in?');
    await browser.close();
    process.exit(1);
  }

  // Verify the token works
  const profile = await page.evaluate(async (t) => {
    const r = await fetch(`https://arimatch1-crewhub-staging.hf.space/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${t}` },
    });
    if (!r.ok) return null;
    return r.json();
  }, token);

  mkdirSync(SESSION_DIR, { recursive: true });
  writeFileSync(SESSION_FILE, JSON.stringify({ localStorage, cookies, profile }, null, 2));

  console.log(`\nSession saved to ${SESSION_FILE}`);
  console.log(`User: ${profile?.name || 'unknown'} (${profile?.email || 'unknown'})`);
  console.log(`Admin: ${profile?.is_admin ?? false}`);
  console.log(`Token length: ${token.length} chars`);

  await browser.close();
}

main().catch(console.error);
