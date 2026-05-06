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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import init_db
from pipeline.deduplicator import process_and_save
from scrapers.indeed import IndeedScraper


async def main() -> None:
    print("[scraper] Initialisation de la base...")
    init_db()

    print("[scraper] Démarrage du scraping Indeed...")
    scraper = IndeedScraper(query="alternance", location="France", max_pages=5)
    offers = await scraper.run()

    inserted = process_and_save(offers)
    print(f"[scraper] Terminé : {inserted} nouvelles offres insérées")


if __name__ == "__main__":
    asyncio.run(main())
