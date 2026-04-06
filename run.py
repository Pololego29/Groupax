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
import sys

# Doit être défini avant tout import de uvicorn/asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
