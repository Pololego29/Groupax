"""
scrapers/run_scraper.py
=======================
Point d'entrée standalone pour le scraping.

Utilisé par GitHub Actions (voir .github/workflows/scrape.yml).
Peut aussi être lancé manuellement : python -m scrapers.run_scraper

Nécessite DATABASE_URL en variable d'environnement pour écrire
dans la base de production. En local sans DATABASE_URL, écrit dans SQLite.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import init_db
from pipeline.deduplicator import process_and_save
from scrapers.indeed import IndeedScraper


async def main(query: str = "alternance", location: str = "France", max_pages: int = 5) -> None:
    try:
        logger.info("Initialisation de la base de données...")
        init_db()

        logger.info("Démarrage du scraping Indeed...")
        scraper = IndeedScraper(query=query, location=location, max_pages=max_pages)
        offers = await scraper.run()

        if not offers:
            logger.warning("Aucune offre trouvée.")
            return

        inserted = process_and_save(offers)
        logger.info(f"Terminé : {inserted} nouvelles offres insérées sur {len(offers)} offres traitées.")

    except Exception as e:
        logger.error(f"Erreur lors du scraping : {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper d'offres d'alternance")
    parser.add_argument("--query", default="alternance", help="Requête de recherche (défaut: alternance)")
    parser.add_argument("--location", default="France", help="Localisation (défaut: France)")
    parser.add_argument("--max-pages", type=int, default=5, help="Nombre maximum de pages (défaut: 5)")

    args = parser.parse_args()
    asyncio.run(main(query=args.query, location=args.location, max_pages=args.max_pages))
