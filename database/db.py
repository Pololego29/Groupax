"""
database/db.py
==============
Accès à la base de données.

Backends supportés (détecté automatiquement via DATABASE_URL) :
- SQLite    : local, aucune configuration requise
- PostgreSQL : production, nécessite DATABASE_URL dans l'environnement

En local : laisser DATABASE_URL vide → SQLite dans data/offers.db
En prod  : définir DATABASE_URL=postgresql://user:pass@host/db
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL", "")
DB_PATH      = Path(__file__).parent.parent / "data" / "offers.db"
_USE_PG      = bool(DATABASE_URL)


# =============================================================================
# SECTION 1 – CONNEXION (abstraction SQLite / PostgreSQL)
# =============================================================================

class _Conn:
    """
    Normalise sqlite3 et psycopg2 derrière une interface commune.
    Adapte les placeholders (? pour SQLite, %s pour PostgreSQL).
    """
    __slots__ = ("_raw", "_pg")

    def __init__(self, raw, use_pg: bool):
        self._raw = raw
        self._pg  = use_pg

    def execute(self, sql: str, params=None):
        if self._pg:
            sql = sql.replace("?", "%s")
        cur = self._raw.cursor()
        cur.execute(sql, params or [])
        return cur

    def commit(self):   self._raw.commit()
    def rollback(self): self._raw.rollback()
    def close(self):    self._raw.close()


@contextmanager
def get_conn():
    """Retourne une connexion normalisée vers SQLite ou PostgreSQL."""
    if _USE_PG:
        import psycopg2
        from psycopg2.extras import DictCursor
        raw = psycopg2.connect(DATABASE_URL)
        raw.cursor_factory = DictCursor
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        raw = sqlite3.connect(str(DB_PATH))
        raw.row_factory = sqlite3.Row

    conn = _Conn(raw, use_pg=_USE_PG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =============================================================================
# SECTION 2 – INITIALISATION
# =============================================================================

_SCHEMA_PK = "SERIAL PRIMARY KEY"      if _USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
_SCHEMA_TS = "TIMESTAMP DEFAULT NOW()" if _USE_PG else "TEXT DEFAULT (datetime('now'))"


def init_db() -> None:
    """Crée la table offers et ses index si nécessaire."""
    with get_conn() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS offers (
                id            {_SCHEMA_PK},
                title         TEXT      NOT NULL,
                company       TEXT      DEFAULT '',
                location      TEXT      DEFAULT '',
                contract_type TEXT      DEFAULT 'Alternance',
                salary        TEXT      DEFAULT '',
                description   TEXT      DEFAULT '',
                url           TEXT      UNIQUE,
                source        TEXT      DEFAULT '',
                scraped_at    TEXT      DEFAULT '',
                created_at    {_SCHEMA_TS}
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source   ON offers(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_location ON offers(location)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created  ON offers(created_at)")


# =============================================================================
# SECTION 3 – ÉCRITURE
# =============================================================================

# INSERT OR IGNORE (SQLite) vs ON CONFLICT DO NOTHING (PostgreSQL)
_INSERT_SQL = (
    """INSERT INTO offers
           (title, company, location, contract_type, salary, description, url, source, scraped_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT (url) DO NOTHING"""
    if _USE_PG else
    """INSERT OR IGNORE INTO offers
           (title, company, location, contract_type, salary, description, url, source, scraped_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
)


def _params(offer: dict) -> list:
    return [
        offer.get("title", ""),
        offer.get("company", ""),
        offer.get("location", ""),
        offer.get("contract_type", "Alternance"),
        offer.get("salary", ""),
        offer.get("description", ""),
        offer.get("url", ""),
        offer.get("source", ""),
        offer.get("scraped_at", ""),
    ]


def insert_offer(offer: dict) -> bool:
    """Insère une offre. Retourne True si insérée, False si déjà existante."""
    with get_conn() as conn:
        cur = conn.execute(_INSERT_SQL, _params(offer))
        return cur.rowcount > 0


def insert_offers_bulk(offers: list[dict]) -> int:
    """Insère plusieurs offres en une transaction. Retourne le nombre inséré."""
    inserted = 0
    with get_conn() as conn:
        for offer in offers:
            cur = conn.execute(_INSERT_SQL, _params(offer))
            inserted += cur.rowcount
    return inserted


# =============================================================================
# SECTION 4 – LECTURE
# =============================================================================

_LIKE = "ILIKE" if _USE_PG else "LIKE"  # ILIKE = insensible à la casse en PostgreSQL


def get_offers(
    search: str = "",
    location: str = "",
    source: str = "",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict], int]:
    """Récupère les offres avec filtres et pagination."""
    conditions: list[str] = []
    params:     list      = []

    if search:
        conditions.append(
            f"(title {_LIKE} ? OR company {_LIKE} ? OR description {_LIKE} ?)"
        )
        term = f"%{search}%"
        params.extend([term, term, term])

    if location:
        conditions.append(f"location {_LIKE} ?")
        params.append(f"%{location}%")

    if source:
        conditions.append("source = ?")
        params.append(source)

    where  = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * per_page

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM offers {where}", params
        ).fetchone()["n"]

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
    """Statistiques globales : total, par source, dernière collecte."""
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM offers"
        ).fetchone()["n"]

        by_source = conn.execute(
            "SELECT source, COUNT(*) AS count FROM offers GROUP BY source"
        ).fetchall()

        last_scrape = conn.execute(
            "SELECT MAX(scraped_at) AS last FROM offers"
        ).fetchone()["last"]

    return {
        "total": total,
        "by_source": {row["source"]: row["count"] for row in by_source},
        "last_scrape": last_scrape or "Jamais",
    }


def url_exists(url: str) -> bool:
    """Vérifie si une URL est déjà en base."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM offers WHERE url = ?", [url]
        ).fetchone()
        return row is not None
