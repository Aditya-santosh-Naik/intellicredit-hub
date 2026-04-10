import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    os.makedirs('docs/images', exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})
        
        # Dashboard
        print("Capturing Dashboard...")
        await page.goto('http://localhost:5000/')
        await page.wait_for_timeout(2000)
        await page.screenshot(path='docs/images/dashboard.png', full_page=True)
        
        # New Case Creation
        print("Capturing New Case...")
        await page.goto('http://localhost:5000/cases/new')
        await page.wait_for_timeout(2000)
        await page.screenshot(path='docs/images/new_case.png', full_page=True)
        
        # Recent Cases List
        print("Capturing Cases List...")
        await page.goto('http://localhost:5000/cases')
        await page.wait_for_timeout(2000)
        await page.screenshot(path='docs/images/cases_list.png', full_page=True)
        
        # Reports
        print("Capturing Reports...")
        await page.goto('http://localhost:5000/reports')
        await page.wait_for_timeout(2000)
        await page.screenshot(path='docs/images/reports.png', full_page=True)

        await browser.close()
        print("Screenshots captured successfully.")

if __name__ == '__main__':
    asyncio.run(main())
