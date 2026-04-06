"""
database/db.py
==============
Gestion de la base de données SQLite.

Contient :
- La définition du schéma (table offers)
- Les fonctions CRUD utilisées par l'API et le pipeline
"""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "offers.db"


# =============================================================================
# SECTION 1 – INITIALISATION
# =============================================================================

def init_db() -> None:
    """
    Crée la base de données et la table si elles n'existent pas encore.
    Appelé au démarrage de l'API.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS offers (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                title         TEXT    NOT NULL,
                company       TEXT    DEFAULT '',
                location      TEXT    DEFAULT '',
                contract_type TEXT    DEFAULT 'Alternance',
                salary        TEXT    DEFAULT '',
                description   TEXT    DEFAULT '',
                url           TEXT    UNIQUE,       -- clé de déduplication principale
                source        TEXT    DEFAULT '',
                scraped_at    TEXT    DEFAULT '',
                created_at    TEXT    DEFAULT (datetime('now'))
            )
        """)
        # Index pour accélérer les filtres courants
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source   ON offers(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_location ON offers(location)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created  ON offers(created_at)")


# =============================================================================
# SECTION 2 – CONNEXION
# =============================================================================

@contextmanager
def get_conn():
    """
    Gestionnaire de contexte pour les connexions SQLite.
    Garantit le commit/rollback automatique et la fermeture de la connexion.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # Résultats accessibles par nom de colonne
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =============================================================================
# SECTION 3 – ÉCRITURE
# =============================================================================

def insert_offer(offer: dict) -> bool:
    """
    Insère une offre dans la base.

    Utilise INSERT OR IGNORE : si l'URL existe déjà, l'offre est silencieusement ignorée.
    C'est la première ligne de défense contre les doublons.

    Args:
        offer : Dictionnaire avec les champs de JobOffer

    Returns:
        True si l'offre a été insérée, False si elle existait déjà
    """
    with get_conn() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO offers
                (title, company, location, contract_type, salary, description, url, source, scraped_at)
            VALUES
                (:title, :company, :location, :contract_type, :salary, :description, :url, :source, :scraped_at)
        """, offer)
        return cursor.rowcount > 0


def insert_offers_bulk(offers: list[dict]) -> int:
    """
    Insère une liste d'offres en une seule transaction (plus rapide).

    Args:
        offers : Liste de dictionnaires JobOffer

    Returns:
        Nombre d'offres réellement insérées (hors doublons)
    """
    inserted = 0
    with get_conn() as conn:
        for offer in offers:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO offers
                    (title, company, location, contract_type, salary, description, url, source, scraped_at)
                VALUES
                    (:title, :company, :location, :contract_type, :salary, :description, :url, :source, :scraped_at)
            """, offer)
            inserted += cursor.rowcount
    return inserted


# =============================================================================
# SECTION 4 – LECTURE
# =============================================================================

def get_offers(
    search: str = "",
    location: str = "",
    source: str = "",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict], int]:
    """
    Récupère les offres avec filtres optionnels et pagination.

    Args:
        search   : Recherche fulltext sur titre + entreprise + description
        location : Filtre sur la ville/région (LIKE)
        source   : Filtre sur la source ("indeed", "hellowork"…)
        page     : Numéro de page (commence à 1)
        per_page : Nombre d'offres par page

    Returns:
        (liste d'offres sous forme de dict, total d'offres correspondantes)
    """
    conditions = []
    params: list = []

    if search:
        conditions.append("(title LIKE ? OR company LIKE ? OR description LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term, term])

    if location:
        conditions.append("location LIKE ?")
        params.append(f"%{location}%")

    if source:
        conditions.append("source = ?")
        params.append(source)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * per_page

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM offers {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT id, title, company, location, contract_type,
                   salary, description, url, source, scraped_at, created_at
            FROM offers {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [per_page, offset],
        ).fetchall()

    return [dict(r) for r in rows], total


def get_stats() -> dict:
    """
    Retourne des statistiques globales sur la base.

    Utilisé par le frontend pour afficher :
    - Le nombre total d'offres
    - Le nombre d'offres par source
    - La date de la dernière collecte
    """
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]

        by_source = conn.execute(
            "SELECT source, COUNT(*) as count FROM offers GROUP BY source"
        ).fetchall()

        last_scrape = conn.execute(
            "SELECT MAX(scraped_at) FROM offers"
        ).fetchone()[0]

    return {
        "total": total,
        "by_source": {row["source"]: row["count"] for row in by_source},
        "last_scrape": last_scrape or "Jamais",
    }


def url_exists(url: str) -> bool:
    """Vérifie si une URL est déjà en base (utilisé par le déduplicateur)."""
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM offers WHERE url = ?", (url,)).fetchone()
        return row is not None
