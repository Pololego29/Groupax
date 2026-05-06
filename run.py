"""
run.py — Point d'entrée du serveur sur Windows.

Problème : uvicorn utilise SelectorEventLoop par défaut sur Windows,
qui ne supporte pas asyncio.create_subprocess_exec (nécessaire pour Playwright).

Solution : forcer ProactorEventLoop AVANT que uvicorn crée sa boucle,
puis lancer uvicorn programmatiquement.

Utilisation :
    python run.py
"""

import asyncio
import logging
import sys

# Configure logging before importing anything else
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Doit être défini avant tout import de uvicorn/asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    logger.info("Windows ProactorEventLoop policy set")

import uvicorn

if __name__ == "__main__":
    try:
        logger.info("Starting Alternax API server...")
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
