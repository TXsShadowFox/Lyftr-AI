/* Local visual verification. Not part of the production build. */
const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");

const OUT = path.resolve(__dirname, "../../screenshots");
fs.mkdirSync(OUT, { recursive: true });

function attach(page, errors) {
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(`console: ${message.text()}`);
    }
  });
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
}

async function overflow(page) {
  return page.evaluate(() => ({
    innerWidth: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
  }));
}

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  const report = {};

  const desktop = await browser.newPage({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  attach(desktop, errors);
  await desktop.goto("http://127.0.0.1:3000/", { waitUntil: "networkidle" });
  await desktop.evaluate(() => document.fonts.ready);
  await desktop.waitForTimeout(150);
  await desktop.screenshot({ path: path.join(OUT, "desktop-empty.png") });

  const lastPrompt = await desktop
    .getByRole("button", {
      name: "Write a SQLite schema for conversation memory.",
    })
    .boundingBox();
  const composer = await desktop.getByTestId("chat-input").boundingBox();

  report.desktopEmpty = {
    title: await desktop.title(),
    testIds: await desktop
      .locator("[data-testid]")
      .evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-testid"))),
    overflow: await overflow(desktop),
    lastPromptFullyVisible:
      lastPrompt && composer
        ? lastPrompt.y + lastPrompt.height <= composer.y
        : null,
    healthText: await desktop.locator("#app-sidebar").innerText(),
  };

  await desktop.getByTestId("chat-input").fill("What is the capital of France?");
  await desktop.getByTestId("send-button").click();
  await desktop.getByTestId("assistant-message").first().waitFor();
  await desktop.waitForTimeout(350);
  await desktop.screenshot({ path: path.join(OUT, "desktop-chat-live.png") });

  report.live = {
    source: await desktop.getByTestId("meta-source").first().innerText(),
    model: await desktop.getByTestId("meta-model").first().innerText(),
    latency: await desktop.getByTestId("meta-latency").first().innerText(),
    inputTokens: await desktop.getByTestId("meta-input-tokens").first().innerText(),
    outputTokens: await desktop.getByTestId("meta-output-tokens").first().innerText(),
    assistantMessages: await desktop.getByTestId("assistant-message").count(),
    overflow: await overflow(desktop),
  };

  await desktop.getByRole("button", { name: "Start a new session" }).click();
  await desktop.getByTestId("chat-input").fill("What is the capital of France?");
  await desktop.getByTestId("send-button").click();
  await desktop.getByTestId("assistant-message").first().waitFor();
  await desktop.waitForTimeout(250);
  await desktop.screenshot({ path: path.join(OUT, "desktop-chat-cache.png") });
  report.cache = {
    source: await desktop.getByTestId("meta-source").first().innerText(),
    assistantMessages: await desktop.getByTestId("assistant-message").count(),
    sidebar: await desktop.locator("#app-sidebar").innerText(),
  };

  await desktop.route("**/chat", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "all providers unavailable" }),
    }),
  );
  await desktop.getByRole("button", { name: "Start a new session" }).click();
  await desktop.getByTestId("chat-input").fill("This should fail cleanly");
  await desktop.getByTestId("send-button").click();
  await desktop.getByRole("alert").waitFor();
  await desktop.waitForTimeout(350);
  await desktop.screenshot({ path: path.join(OUT, "desktop-error.png") });
  report.errorState = {
    alert: await desktop.getByRole("alert").innerText(),
    assistantMessages: await desktop.getByTestId("assistant-message").count(),
    inputValue: await desktop.getByTestId("chat-input").inputValue(),
  };
  await desktop.unroute("**/chat");

  const mobile = await browser.newPage({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  });
  attach(mobile, errors);
  await mobile.goto("http://127.0.0.1:3000/", { waitUntil: "networkidle" });
  await mobile.evaluate(() => document.fonts.ready);
  await mobile.screenshot({ path: path.join(OUT, "mobile-empty.png") });
  report.mobileEmpty = { overflow: await overflow(mobile) };

  await mobile.getByRole("button", { name: "Open navigation" }).click();
  await mobile.waitForTimeout(350);
  await mobile.screenshot({ path: path.join(OUT, "mobile-drawer.png") });
  report.mobileDrawer = {
    systemPromptVisible: await mobile.getByTestId("system-prompt-input").isVisible(),
    overflow: await overflow(mobile),
  };
  await mobile.getByRole("button", { name: "Close navigation", exact: true }).click();
  await mobile.waitForTimeout(250);

  await mobile
    .getByTestId("chat-input")
    .fill("Explain how automatic key failover works in one paragraph.");
  await mobile.getByTestId("send-button").click();
  await mobile.getByTestId("assistant-message").first().waitFor();
  await mobile.waitForTimeout(350);
  await mobile.screenshot({ path: path.join(OUT, "mobile-chat.png") });
  report.mobileChat = {
    source: await mobile.getByTestId("meta-source").first().innerText(),
    overflow: await overflow(mobile),
  };

  const tablet = await browser.newPage({
    viewport: { width: 768, height: 1024 },
    deviceScaleFactor: 1,
  });
  attach(tablet, errors);
  await tablet.goto("http://127.0.0.1:3000/", { waitUntil: "networkidle" });
  await tablet.evaluate(() => document.fonts.ready);
  await tablet.screenshot({ path: path.join(OUT, "tablet-empty.png") });
  report.tablet = { overflow: await overflow(tablet) };

  report.errors = errors;
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
