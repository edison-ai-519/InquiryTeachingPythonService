import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire('C:/Users/14011/AppData/Local/OpenAI/Codex/runtimes/cua_node/b474a88d5d105afa/bin/node_modules/__runtime__.cjs');
const { chromium } = require('playwright-core');
const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args: ['--allow-file-access-from-files'],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
const errors = [];
page.on('console', (message) => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });
page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
const htmlPath = 'D:/javacode/InquiryTeachingPythonService/outputs/AI探究式教学助手成果展示_交互预览.html';
await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'load' });
await page.waitForTimeout(350);
const outputDir = 'D:/javacode/InquiryTeachingPythonService/.codex_artifacts/build_ai_inquiry_html/screens';
await fs.mkdir(outputDir, { recursive: true });
const report = [];
for (let i = 0; i < 13; i += 1) {
  const state = await page.evaluate(() => {
    const active = document.querySelector('.slide.active');
    const deck = document.getElementById('deck').getBoundingClientRect();
    const counter = document.getElementById('counter').textContent;
    return {
      title: active?.querySelector('h1,h2')?.textContent?.replace(/\s+/g, ' ').trim() || '',
      activeCount: document.querySelectorAll('.slide.active').length,
      counter,
      deck: { left: deck.left, top: deck.top, right: deck.right, bottom: deck.bottom },
      imageLoaded: [...active.querySelectorAll('img')].every((img) => img.complete && img.naturalWidth > 0),
      bodyOverflow: document.documentElement.scrollWidth > innerWidth || document.documentElement.scrollHeight > innerHeight,
    };
  });
  if (state.activeCount !== 1) throw new Error(`第${i + 1}页 active 数量异常`);
  if (state.counter !== `${String(i + 1).padStart(2, '0')} / 13`) throw new Error(`第${i + 1}页计数器异常：${state.counter}`);
  if (!state.imageLoaded) throw new Error(`第${i + 1}页图片加载失败`);
  if (state.bodyOverflow) throw new Error(`第${i + 1}页浏览器产生滚动溢出`);
  if (state.deck.left < -1 || state.deck.top < -1 || state.deck.right > 1601 || state.deck.bottom > 1001) throw new Error(`第${i + 1}页画布超出视口`);
  report.push(state);
  await page.screenshot({ path: path.join(outputDir, `slide-${String(i + 1).padStart(2, '0')}.png`), fullPage: false });
  if (i < 12) { await page.keyboard.press('ArrowRight'); await page.waitForTimeout(650); }
}
await page.keyboard.press('n');
const notesOpen = await page.locator('#notes').evaluate((el) => el.classList.contains('open') && el.textContent.includes('演讲提示'));
if (!notesOpen) throw new Error('演讲备注快捷键未生效');
await page.keyboard.press('Home');
if ((await page.locator('#counter').textContent()) !== '01 / 13') throw new Error('Home 快捷键未返回首页');
if (errors.length) throw new Error(errors.join('\n'));
await fs.writeFile(path.join(outputDir, 'verification.json'), JSON.stringify({ slides: report, notesOpen, errors }, null, 2), 'utf8');
await browser.close();
console.log(JSON.stringify({ slideCount: report.length, notesOpen, consoleErrors: errors.length, screenshots: outputDir }, null, 2));
