"""
scrapers/run_scraper.py
=======================
Point d'entrée standalone pour le scraping.

Utilisé par GitHub Actions (voir .github/workflows/scrape.yml).
Peut aussi être lancé manuellement : python -m scrapers.run_scraper

Nécessite DATABASE_URL en variable d'environnement pour écrire
dans la base de production. En local sans DATABASE_URL, écrit dans SQLite.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import init_db
from pipeline.deduplicator import process_and_save
from scrapers.indeed import IndeedScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        logger.info("Initializing database...")
        init_db()

        logger.info("Starting Indeed scraper...")
        scraper = IndeedScraper(query="alternance", location="France", max_pages=5)
        offers = await scraper.run()
        
        if not offers:
            logger.warning("No offers scraped")
            return

        logger.info(f"Scraped {len(offers)} offers")
        inserted = process_and_save(offers)
        logger.info(f"Completed: {inserted} new offers inserted")
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
