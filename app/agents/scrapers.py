import logging
import random
from playwright.async_api import Page
from sqlalchemy.orm import Session
from app.models.job import JobListing
from app.automation.stealth import gaussian_wait, natural_scroll

logger = logging.getLogger(__name__)

async def scrape_linkedin_jobs(page: Page, db: Session, keywords: str, location: str):
    """
    Scrape jobs from LinkedIn.
    This runs inside a persistent stealth context.
    """
    logger.info(f"Scraping LinkedIn for {keywords} in {location}")
    url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}"
    await page.goto(url)
    await gaussian_wait(3.0, 1.0)
    
    await natural_scroll(page)
    
    # Simple placeholder parsing logic
    job_cards = await page.query_selector_all(".job-card-container")
    logger.info(f"Found {len(job_cards)} jobs on first page.")
    
    new_jobs = 0
    for card in job_cards:
        try:
            title_el = await card.query_selector(".job-card-list__title")
            company_el = await card.query_selector(".job-card-container__company-name")
            link_el = await card.query_selector("a.job-card-list__title")
            
            if not title_el or not link_el:
                continue
                
            title = await title_el.inner_text()
            company = await company_el.inner_text() if company_el else "Unknown"
            url = await link_el.get_attribute("href")
            
            # Simple URL hash/deduplication
            clean_url = url.split("?")[0]
            existing = db.query(JobListing).filter(JobListing.url == clean_url).first()
            if existing:
                continue
                
            job = JobListing(
                source="linkedin",
                title=title.strip(),
                company_name=company.strip(),
                url=clean_url
            )
            db.add(job)
            new_jobs += 1
        except Exception as e:
            logger.error(f"Error parsing job card: {e}")
            
    db.commit()
    logger.info(f"Saved {new_jobs} new LinkedIn jobs to database.")
    return new_jobs
