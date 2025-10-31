const puppeteer = require('puppeteer');

(async () => {
    // Launch a headless browser
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    // Set the HTML content
    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
          <title>Sample PDF</title>
      </head>
      <body>
          <h1>Hello, PDF!</h1>
          <p>This PDF was generated from HTML content.</p>
      </body>
      </html>
    `;

    await page.setContent(htmlContent);

    // Generate PDF from the HTML content
    const outputPath = './page.pdf';
    await page.pdf({
        path: outputPath,
    });

    console.log("PDF generated successfully at: " + outputPath);

    await browser.close();
})()
