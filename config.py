"""
config.py
=========
Configuration centralisée de l'application Alternax.

Tous les paramètres sont lus depuis les variables d'environnement,
avec des valeurs par défaut appropriées.
"""

import os
from functools import lru_cache

# =============================================================================
# DATABASE
# =============================================================================

DATABASE_URL = os.environ.get("DATABASE_URL", "")
"""PostgreSQL connection string. Empty = SQLite (data/offers.db)"""

# =============================================================================
# API
# =============================================================================

API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))
API_RELOAD = os.environ.get("API_RELOAD", "true").lower() == "true"
API_WORKERS = int(os.environ.get("API_WORKERS", "1"))

FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
"""Frontend URL for CORS. Empty = allow all origins"""

# =============================================================================
# CACHING
# =============================================================================

CACHE_TTL_STATS = int(os.environ.get("CACHE_TTL_STATS", "300"))
"""Cache time-to-live for /api/stats in seconds (default: 5 min)"""

CACHE_TTL_SOURCES = int(os.environ.get("CACHE_TTL_SOURCES", "600"))
"""Cache time-to-live for /api/sources in seconds (default: 10 min)"""

# =============================================================================
# SCRAPING
# =============================================================================

SCRAPER_MAX_PAGES = int(os.environ.get("SCRAPER_MAX_PAGES", "5"))
SCRAPER_DELAY_MIN = float(os.environ.get("SCRAPER_DELAY_MIN", "5.0"))
SCRAPER_DELAY_MAX = float(os.environ.get("SCRAPER_DELAY_MAX", "9.0"))
SCRAPER_MAX_RETRY = int(os.environ.get("SCRAPER_MAX_RETRY", "2"))

# =============================================================================
# RATE LIMITING
# =============================================================================

RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "false").lower() == "true"
"""Enable rate limiting on API endpoints"""

RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
"""Max requests per window"""

RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))
"""Rate limit window in seconds"""

# =============================================================================
# LOGGING
# =============================================================================

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
"""Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"""

# =============================================================================
# PAGINATION
# =============================================================================

PAGINATION_DEFAULT_PER_PAGE = 20
PAGINATION_MAX_PER_PAGE = 100
PAGINATION_MIN_PER_PAGE = 1

# =============================================================================
# FEATURE FLAGS
# =============================================================================

FEATURE_HEALTH_CHECK = os.environ.get("FEATURE_HEALTH_CHECK", "true").lower() == "true"
FEATURE_METRICS = os.environ.get("FEATURE_METRICS", "true").lower() == "true"
FEATURE_SWAGGER = os.environ.get("FEATURE_SWAGGER", "true").lower() == "true"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

@lru_cache(maxsize=1)
def get_cors_origins():
    """Retourne la liste des origines autorisées pour CORS."""
    if FRONTEND_URL:
        return [FRONTEND_URL]
    return ["*"]


def is_production():
    """Vérifie si on est en mode production."""
    return not API_RELOAD and DATABASE_URL != ""
