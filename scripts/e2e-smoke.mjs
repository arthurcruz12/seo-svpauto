import { spawn } from "node:child_process";
import { chromium } from "@playwright/test";

const baseURL = "http://127.0.0.1:4173";
const vite = spawn(
  process.execPath,
  ["node_modules/vite/bin/vite.js", "preview", "--configLoader", "runner", "--host", "127.0.0.1", "--port", "4173"],
  { cwd: process.cwd(), stdio: "ignore", windowsHide: true },
);

async function waitForServer() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(baseURL);
      if (response.ok) return;
    } catch {
      // Server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("A interface não iniciou para o teste E2E.");
}

let exitCode = 1;
try {
  await waitForServer();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(baseURL, { waitUntil: "domcontentloaded" });

  const result = await page.evaluate(() => {
    const heading = document.querySelector("h1");
    const buttons = [...document.querySelectorAll("button")].map((button) => button.textContent?.trim() ?? "");
    const style = heading ? getComputedStyle(heading) : null;
    return {
      title: document.title,
      hasHeading: Boolean(heading),
      hasLogin: buttons.includes("Entrar"),
      hasTrial: buttons.includes("Experimentar grátis"),
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      headingFontSize: style ? Number.parseFloat(style.fontSize) : 0,
    };
  });

  if (!/SEO/i.test(result.title) || !result.hasHeading || !result.hasLogin || !result.hasTrial) {
    throw new Error(`Elementos essenciais ausentes: ${JSON.stringify(result)}`);
  }
  if (result.horizontalOverflow || result.headingFontSize <= 30) {
    throw new Error(`Regressão visual detetada: ${JSON.stringify(result)}`);
  }
  console.log("E2E visual aprovado:", result);
  exitCode = 0;
} catch (error) {
  console.error(error);
} finally {
  vite.kill();
  setTimeout(() => process.exit(exitCode), 100);
}
