// Inbound CPH deck → PDF renderer.
// Renders a keyboard-navigated single-file HTML deck to a clean, static,
// 16:9 widescreen PDF — one page per slide, UI chrome stripped.
//
// Usage:
//   node render-pdf.js <deck.html> <out.pdf> <slideCount>
//
// Requires: puppeteer-core (npm i puppeteer-core), Google Chrome, pdfunite (poppler).
// See ../DESIGN.md → "Rendering pipeline".

const puppeteer = require('puppeteer-core');
const { execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

(async () => {
  const src = path.resolve(process.argv[2]);
  const out = path.resolve(process.argv[3]);
  const totalSlides = parseInt(process.argv[4] || '0', 10);

  if (!src || !out || !totalSlides) {
    console.error('Usage: node render-pdf.js <deck.html> <out.pdf> <slideCount>');
    process.exit(1);
  }

  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: 'new',
    args: ['--no-sandbox', '--font-render-hinting=none'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });

  const slidePdfs = [];
  for (let i = 1; i <= totalSlides; i++) {
    await page.goto('file://' + src + '#' + i, { waitUntil: 'networkidle0' });
    // Force the target slide active and strip UI chrome that does not belong in a PDF.
    await page.evaluate((n) => {
      const slides = document.querySelectorAll('.slide');
      slides.forEach((s, idx) => s.classList.toggle('active', idx === n - 1));
      const bar = document.getElementById('progressBar');
      if (bar) bar.remove();
      document.querySelectorAll('.nav-hint').forEach((el) => el.remove());
    }, i);
    await page.evaluateHandle('document.fonts.ready');
    await new Promise((r) => setTimeout(r, 200));

    const buf = await page.pdf({
      width: '13.333in',
      height: '7.5in',
      printBackground: true,
      margin: { top: 0, right: 0, bottom: 0, left: 0 },
      preferCSSPageSize: false,
    });
    const slidePath = path.join(path.dirname(out), `_slide-${String(i).padStart(2, '0')}.pdf`);
    fs.writeFileSync(slidePath, buf);
    slidePdfs.push(slidePath);
    process.stdout.write(`${i} `);
  }
  process.stdout.write('\n');
  await browser.close();

  // Merge all single-slide PDFs into the final deck, then clean up.
  execFileSync('pdfunite', [...slidePdfs, out]);
  slidePdfs.forEach((p) => fs.unlinkSync(p));
  console.log(`Done: ${out} (${totalSlides} pages, 13.333in x 7.5in)`);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
