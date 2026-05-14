import asyncio
from playwright.async_api import async_playwright
from app.automation.stealth import create_stealth_context
from app.agents.scrapers import scrape_linkedin_jobs
from app.core.db import SessionLocal

async def main():
    print("Starting visible Playwright session...")
    async with async_playwright() as p:
        # Launch in headless=False so you can see it!
        context = await create_stealth_context(p, user_data_dir="./playwright_data", headless=False)
        page = await context.new_page()
        
        db = SessionLocal()
        try:
            print("Bot is navigating to LinkedIn and applying stealth behaviors (scrolling, etc)...")
            await scrape_linkedin_jobs(page, db, keywords="Backend Developer", location="Remote")
            print("Finished scraping.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            db.close()
            # Keep browser open for a few seconds so you can see the result
            await asyncio.sleep(5)
            await context.close()

if __name__ == "__main__":
    asyncio.run(main())
