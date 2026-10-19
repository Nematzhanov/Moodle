// Снимки настоящего сайта CodeCheck для ролика (тёмная тема, 2x), в реальном времени —
// анимации сайта (отсчёт, появление блоков) успевают доиграть до снимка.
// Запуск: node scripts/shoot_site.mjs <путь к puppeteer-core>   (сервер сайта на :8000)
const puppeteer = (await import(process.argv[2] + "/lib/puppeteer/puppeteer-core.js")).default;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await puppeteer.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true, args: ["--hide-scrollbars"],
});
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "dark" }]);
await page.goto("http://127.0.0.1:8000/", { waitUntil: "networkidle0" });
const out = new URL("../assets/site/", import.meta.url).pathname;

await sleep(4800);                                   // демо на первом экране доходит до 91%
await page.screenshot({ path: out + "top.png" });

// раздел проверки: вставляем код, жмём «Проверить», ждём настоящий результат модели
const code = `#include <vector>
#include <algorithm>

// Returns the k largest elements in descending order.
std::vector<int> topK(const std::vector<int>& nums, int k) {
    std::vector<int> result(nums.begin(), nums.end());
    std::sort(result.begin(), result.end(), std::greater<int>());
    // Ensure k does not exceed the vector size.
    if (k > static_cast<int>(result.size())) {
        k = result.size();
    }
    result.resize(k);
    return result;
}`;
await page.evaluate(() => { document.documentElement.style.scrollBehavior = "auto"; });
await page.evaluate((c) => { const t = document.querySelector("#code"); t.value = c; t.dispatchEvent(new Event("input")); }, code);
await page.evaluate(() => window.scrollTo(0, document.querySelector("#check").offsetTop - 60));
await sleep(1200);
await page.screenshot({ path: out + "check.png" });
await page.click("#check-btn");
await sleep(3800);
await page.evaluate(() => window.scrollTo(0, document.querySelector("#result").offsetTop - 120));
await sleep(900);
await page.screenshot({ path: out + "result.png" });

for (const id of ["how", "quality", "team"]) {
  await page.evaluate((i) => window.scrollTo(0, document.querySelector("#" + i).offsetTop - 40), id);
  await sleep(2200);
  await page.screenshot({ path: out + id + ".png" });
}
await browser.close();
console.log("✓ снимки в", out);
