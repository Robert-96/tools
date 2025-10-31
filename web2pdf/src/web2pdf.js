const puppeteer = require('puppeteer');

(async () => {
    // Launch a headless browser
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    await page.goto('http://archive.org/');

    // Generate PDF from the page
    const outputPath = './page.pdf';
    await page.pdf({
        path: outputPath,
    });

    console.log("PDF generated successfully at: " + outputPath);

    await browser.close();
})();
