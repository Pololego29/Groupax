"""
api/main.py
===========
API FastAPI pour Alternax — sert les offres d'alternance.

Le scraping est géré par GitHub Actions (.github/workflows/scrape.yml).
L'API ne fait que lire/écrire en base et servir le frontend.

Endpoints :
    GET /                   Page d'accueil
    GET /api/offres         Liste paginée avec filtres
    GET /api/stats          Statistiques globales (cachées)
    GET /api/sources        Sources disponibles (cachées)
    GET /api/health         Health check
    GET /api/metrics        Métriques (optionnel)

Démarrage local :
    uvicorn api.main:app --reload --port 8000

Variables d'environnement :
    DATABASE_URL  : PostgreSQL en prod (absent = SQLite local)
    FRONTEND_URL  : Restreint le CORS à cette origine (absent = ouvert)
    CACHE_TTL_STATS : Cache time-to-live pour stats (défaut: 300s)
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from collections import defaultdict

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import init_db, get_offers, get_stats
from config import (
    get_cors_origins, API_HOST, API_PORT, CACHE_TTL_STATS, CACHE_TTL_SOURCES,
    FEATURE_HEALTH_CHECK, FEATURE_METRICS, FEATURE_SWAGGER
)
from cache import cached

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# METRICS
# =============================================================================

class MetricsCollector:
    """Collecte les métriques d'utilisation de l'API."""
    
    def __init__(self):
        self.requests_total = 0
        self.requests_by_endpoint = defaultdict(int)
        self.cache_hits = 0
        self.cache_misses = 0
        self.start_time = time.time()
    
    def record_request(self, endpoint: str):
        self.requests_total += 1
        self.requests_by_endpoint[endpoint] += 1
    
    def record_cache_hit(self):
        self.cache_hits += 1
    
    def record_cache_miss(self):
        self.cache_misses += 1
    
    def get_stats(self) -> dict:
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": uptime,
            "total_requests": self.requests_total,
            "requests_by_endpoint": dict(self.requests_by_endpoint),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": (
                self.cache_hits / (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0 else 0
            ),
        }


metrics = MetricsCollector()


# =============================================================================
# CACHED FUNCTIONS
# =============================================================================

@cached(ttl=CACHE_TTL_STATS)
def get_cached_stats():
    """Récupère les stats avec mise en cache."""
    metrics.record_cache_miss()
    return get_stats()


@cached(ttl=CACHE_TTL_SOURCES)
def get_cached_sources():
    """Récupère les sources avec mise en cache."""
    metrics.record_cache_miss()
    return list(get_stats()["by_source"].keys())


# =============================================================================
# CYCLE DE VIE
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
# APPLICATION
# =============================================================================

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(
    title="Alternax – API Alternances",
    description="Offres d'alternance collectées automatiquement",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if FEATURE_SWAGGER else None,
    redoc_url="/api/redoc" if FEATURE_SWAGGER else None,
)

cors_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

logger.info(f"CORS origins: {cors_origins}")
logger.info(f"Features: health_check={FEATURE_HEALTH_CHECK}, metrics={FEATURE_METRICS}, swagger={FEATURE_SWAGGER}")


# =============================================================================
# HEALTH & METRICS ENDPOINTS
# =============================================================================

if FEATURE_HEALTH_CHECK:
    @app.get("/api/health")
    async def health_check():
        """Vérification de l'état de l'application."""
        try:
            # Teste la connexion à la base
            stats = get_stats()
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "database": "connected",
                "offers_count": stats.get("total", 0)
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time()
                }
            )


if FEATURE_METRICS:
    @app.get("/api/metrics")
    async def get_api_metrics():
        """Retourne les métriques de l'API."""
        return metrics.get_stats()


# =============================================================================
# MAIN ENDPOINTS
# =============================================================================

@app.get("/")
async def serve_frontend():
    """Sert la page d'accueil en local."""
    metrics.record_request("frontend")
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
    metrics.record_request("offres")
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
    """Retourne les statistiques globales (cachées)."""
    metrics.record_request("stats")
    try:
        # Utilise le cache pour éviter les requêtes fréquentes
        stats = get_cached_stats()
        metrics.record_cache_hit()
        logger.info(f"Stats: {stats['total']} total offers")
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
    """Retourne la liste des sources disponibles (cachées)."""
    metrics.record_request("sources")
    try:
        sources = get_cached_sources()
        metrics.record_cache_hit()
        logger.info(f"Available sources: {sources}")
        return sources
    except Exception as e:
        logger.error(f"Error in api_sources: {e}", exc_info=True)
        return []
