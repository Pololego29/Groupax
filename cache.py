"""
cache.py
========
Système de caching simple et thread-safe pour les données fréquemment accédées.

Utilisé pour mettre en cache les stats qui sont interrogées souvent.
"""

import time
import logging
from typing import Any, Optional, Callable
from threading import Lock

logger = logging.getLogger(__name__)


class CacheEntry:
    """Représente une entrée en cache avec TTL."""
    
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """Vérifie si l'entrée a expiré."""
        return (time.time() - self.created_at) > self.ttl
    
    def __repr__(self) -> str:
        age = time.time() - self.created_at
        return f"<CacheEntry age={age:.1f}s ttl={self.ttl}s expired={self.is_expired()}>"


class SimpleCache:
    """Cache simple et thread-safe avec TTL par entrée."""
    
    def __init__(self):
        self._cache = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache si elle n'a pas expiré."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                logger.debug(f"Cache MISS: {key}")
                return None
            
            if entry.is_expired():
                logger.debug(f"Cache EXPIRED: {key}")
                del self._cache[key]
                return None
            
            logger.debug(f"Cache HIT: {key} (age={time.time() - entry.created_at:.1f}s)")
            return entry.value
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Stocke une valeur en cache avec un TTL."""
        with self._lock:
            self._cache[key] = CacheEntry(value, ttl)
            logger.debug(f"Cache SET: {key} (ttl={ttl}s)")
    
    def invalidate(self, key: str) -> None:
        """Invalide une entrée du cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.info(f"Cache INVALIDATED: {key}")
    
    def clear(self) -> None:
        """Vide tout le cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache CLEARED ({count} entries)")
    
    def stats(self) -> dict:
        """Retourne des statistiques sur le cache."""
        with self._lock:
            return {
                "total_entries": len(self._cache),
                "expired_entries": sum(1 for e in self._cache.values() if e.is_expired()),
            }


# Instance globale du cache
_cache = SimpleCache()


def cached(ttl: int = 300):
    """
    Décorateur pour mettre en cache le résultat d'une fonction.
    
    Utilisation :
        @cached(ttl=300)
        def get_stats():
            return {"total": 1000}
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # Génère une clé basée sur le nom de la fonction et les paramètres
            cache_key = f"{func.__module__}.{func.__name__}"
            
            # Essaie de récupérer du cache
            result = _cache.get(cache_key)
            if result is not None:
                return result
            
            # Sinon, exécute la fonction et met en cache
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, ttl)
            return result
        
        # Ajoute des méthodes utiles au wrapper
        wrapper.invalidate = lambda: _cache.invalidate(f"{func.__module__}.{func.__name__}")
        wrapper.cache_stats = lambda: _cache.stats()
        
        return wrapper
    return decorator


# Exports
__all__ = ["SimpleCache", "cached", "_cache"]
