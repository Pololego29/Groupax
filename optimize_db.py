"""
optimize_db.py
==============
Script pour optimiser la base de données (indices supplémentaires, vacuum, etc).

À exécuter après un scraping important ou périodiquement en production.

Utilisation:
    python optimize_db.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database.db import get_conn

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def optimize_db():
    """Optimise la base de données avec indices et nettoyage."""
    
    try:
        with get_conn() as conn:
            logger.info("Starting database optimization...")
            
            # Ajouter des indices supplémentaires pour les recherches
            logger.info("Creating additional indices...")
            
            # Index sur title pour les recherches fulltext
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_title 
                ON offers(title COLLATE NOCASE)
            """)
            
            # Index sur company
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_company 
                ON offers(company COLLATE NOCASE)
            """)
            
            # Index composite pour les filtres courants
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_location 
                ON offers(source, location)
            """)
            
            # Index sur la date pour les tris
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at_desc 
                ON offers(created_at DESC)
            """)
            
            # Analyze pour les statistiques de requête (PostgreSQL uniquement)
            try:
                conn.execute("ANALYZE offers")
                logger.info("Query statistics updated")
            except Exception:
                # SQLite n'a pas ANALYZE dans le même format
                pass
            
            # Vacuum pour compacter la base (SQLite uniquement)
            try:
                conn.execute("VACUUM")
                logger.info("Database compacted with VACUUM")
            except Exception:
                # PostgreSQL n'a pas besoin de VACUUM dans ce contexte
                pass
            
            logger.info("Database optimization completed successfully!")
            
    except Exception as e:
        logger.error(f"Database optimization failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    optimize_db()
