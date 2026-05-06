"""
api/main.py
===========
API FastAPI pour Alternax — sert les offres d'alternance.

Le scraping est géré par GitHub Actions (.github/workflows/scrape.yml).
L'API ne fait que lire/écrire en base et servir le frontend.

Endpoints :
    GET /api/offres     Liste paginée avec filtres
    GET /api/stats      Statistiques globales
    GET /api/sources    Sources disponibles

Démarrage local :
    uvicorn api.main:app --reload --port 8000

Variables d'environnement :
    DATABASE_URL  : PostgreSQL en prod (absent = SQLite local)
    FRONTEND_URL  : Restreint le CORS à cette origine (absent = ouvert)
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import init_db, get_offers, get_stats

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# SECTION 1 – CYCLE DE VIE
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise
    yield


# =============================================================================
# SECTION 2 – APPLICATION
# =============================================================================

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

_frontend_url = os.environ.get("FRONTEND_URL", "")
_cors_origins  = [_frontend_url] if _frontend_url else ["*"]

app = FastAPI(
    title="Alternax – API Alternances",
    description="Offres d'alternance collectées automatiquement",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

logger.info(f"CORS origins: {_cors_origins}")


# =============================================================================
# SECTION 3 – ENDPOINTS
# =============================================================================

@app.get("/")
async def serve_frontend():
    """Sert la page d'accueil en local (en prod, le frontend est sur Vercel)."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/offres")
async def list_offres(
    search:   str = Query("", description="Recherche titre, entreprise, description"),
    location: str = Query("", description="Filtre par ville/région"),
    source:   str = Query("", description="Filtre par source"),
    page:     int = Query(1,  ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Liste les offres avec filtres et pagination."""
    try:
        # Validate and sanitize inputs
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20
        
        search = search.strip() if search else ""
        location = location.strip() if location else ""
        source = source.strip() if source else ""
        
        logger.info(f"Query: search='{search}', location='{location}', source='{source}', page={page}, per_page={per_page}")
        
        offers, total = get_offers(
            search=search, location=location, source=source,
            page=page, per_page=per_page,
        )
        
        logger.info(f"Returned {len(offers)} offers (total: {total})")
        
        return {
            "offers":   offers,
            "total":    total,
            "page":     page,
            "per_page": per_page,
            "pages":    max(1, -(-total // per_page)),
        }
    except Exception as e:
        logger.error(f"Error in list_offres: {e}", exc_info=True)
        return {
            "offers": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "pages": 0,
            "error": "Failed to fetch offers"
        }


@app.get("/api/stats")
async def api_stats():
    """Retourne les statistiques globales."""
    try:
        stats = get_stats()
        logger.info(f"Stats: {stats['total']} total offers, {len(stats['by_source'])} sources")
        return stats
    except Exception as e:
        logger.error(f"Error in api_stats: {e}", exc_info=True)
        return {
            "total": 0,
            "by_source": {},
            "last_scrape": "Jamais",
            "error": "Failed to fetch statistics"
        }


@app.get("/api/sources")
async def api_sources():
    """Retourne la liste des sources disponibles."""
    try:
        stats = get_stats()
        sources = list(stats["by_source"].keys())
        logger.info(f"Available sources: {sources}")
        return sources
    except Exception as e:
        logger.error(f"Error in api_sources: {e}", exc_info=True)
        return []
