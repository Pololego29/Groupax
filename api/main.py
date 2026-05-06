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


# =============================================================================
# SECTION 1 – CYCLE DE VIE
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("[api] Base de données initialisée")
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
    offers, total = get_offers(
        search=search, location=location, source=source,
        page=page, per_page=per_page,
    )
    return {
        "offers":   offers,
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    max(1, -(-total // per_page)),
    }


@app.get("/api/stats")
async def api_stats():
    return get_stats()


@app.get("/api/sources")
async def api_sources():
    return list(get_stats()["by_source"].keys())
