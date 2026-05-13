"""
scrapers/run_scraper.py
=======================
Point d'entrée standalone pour le scraping multi-sources.

Utilisé par GitHub Actions (voir .github/workflows/scrape.yml).
Peut aussi être lancé manuellement : python -m scrapers.run_scraper

Variables d'environnement :
    DATABASE_URL          : URL PostgreSQL (SQLite local si absent)
    SCRAPER_SOURCES       : Sources activées, séparées par virgule (défaut : indeed,hellowork)
    SCRAPER_EXPORT_FORMATS: Formats d'export optionnels (ex: csv,json)
    SCRAPER_LOG_FILE      : 1/true pour activer les logs fichiers
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import init_db
from pipeline.deduplicator import process_and_save
from scrapers.indeed import IndeedScraper
from scrapers.hellowork import HelloWorkScraper
from utils.logger import get_logger, log_session_summary
from utils.exporters import auto_export
from utils.validators import validate_and_normalize


log = get_logger("run_scraper")

# Sources disponibles : nom → classe scraper
_SCRAPERS = {
    "indeed":    IndeedScraper,
    "hellowork": HelloWorkScraper,
}

def _get_active_sources() -> list[str]:
    """Lit SCRAPER_SOURCES et retourne les sources activées."""
    env = os.getenv("SCRAPER_SOURCES", "indeed,hellowork")
    sources = [s.strip().lower() for s in env.split(",") if s.strip()]
    unknown = [s for s in sources if s not in _SCRAPERS]
    if unknown:
        log.warning(f"Sources inconnues ignorées : {unknown}")
    return [s for s in sources if s in _SCRAPERS]


async def run_scraper(name: str, scraper_cls) -> list:
    """Lance un scraper individuel et retourne ses offres normalisées."""
    log.info(f"Démarrage : {name}")
    try:
        scraper = scraper_cls()
        offers  = await scraper.run()
        clean   = validate_and_normalize(offers)
        log_session_summary(log, scraper.stats)
        return clean
    except Exception as e:
        log.error(f"Erreur fatale dans {name} : {e}", exc_info=True)
        return []


async def main() -> None:
    log.info("=== Alternax Scraper démarrage ===")
    log.info("Initialisation de la base de données...")
    init_db()

    sources = _get_active_sources()
    if not sources:
        log.error("Aucune source active — vérifiez SCRAPER_SOURCES")
        return

    log.info(f"Sources actives : {', '.join(sources)}")

    # Lancement séquentiel (évite la surcharge réseau et les bans)
    all_offers = []
    for source_name in sources:
        offers = await run_scraper(source_name, _SCRAPERS[source_name])
        all_offers.extend(offers)

    log.info(f"Total toutes sources : {len(all_offers)} offres normalisées")

    # Insertion en base
    inserted = process_and_save(all_offers)
    log.info(f"Insertion terminée : {inserted} nouvelles offres en base")

    # Export optionnel selon SCRAPER_EXPORT_FORMATS
    exported = auto_export(all_offers)
    if exported:
        log.info(f"Exports créés : {exported}")

    log.info("=== Alternax Scraper terminé ===")


if __name__ == "__main__":
    asyncio.run(main())
