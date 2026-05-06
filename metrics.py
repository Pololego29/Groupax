"""
metrics.py
==========
Collecte et gestion des métriques de performance de l'application.

Inclut:
- Métriques de temps de réponse
- Compteurs d'utilisation
- Alertes de performance
"""

import time
import logging
from typing import Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Représente une métrique de performance."""
    name: str
    value: float
    unit: str = "ms"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self):
        return f"{self.name}: {self.value:.2f}{self.unit}"


class PerformanceMonitor:
    """Moniteur de performance pour tracker les métriques."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_times = {}
    
    def start(self, operation: str) -> str:
        """Démarre le chrono d'une opération."""
        operation_id = f"{operation}_{id(self)}"
        self.start_times[operation_id] = time.time()
        return operation_id
    
    def end(self, operation_id: str, operation: str = None) -> float:
        """Termine le chrono et enregistre la métrique."""
        if operation_id not in self.start_times:
            logger.warning(f"Operation {operation_id} not found in start_times")
            return 0.0
        
        elapsed_ms = (time.time() - self.start_times[operation_id]) * 1000
        del self.start_times[operation_id]
        
        if operation:
            metric = PerformanceMetric(operation, elapsed_ms)
            self.metrics[operation].append(metric)
            
            # Log si > 1 seconde
            if elapsed_ms > 1000:
                logger.warning(f"Slow operation: {metric}")
        
        return elapsed_ms
    
    def get_stats(self, operation: str) -> Optional[dict]:
        """Récupère les statistiques pour une opération."""
        metrics = self.metrics.get(operation, [])
        if not metrics:
            return None
        
        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "last": values[-1],
        }
    
    def get_all_stats(self) -> dict:
        """Récupère les statistiques de toutes les opérations."""
        return {
            operation: self.get_stats(operation)
            for operation in self.metrics.keys()
        }
    
    def clear(self, older_than_minutes: int = 60) -> int:
        """Nettoie les anciennes métriques."""
        cutoff_time = datetime.now() - timedelta(minutes=older_than_minutes)
        removed = 0
        
        for operation in list(self.metrics.keys()):
            metrics = self.metrics[operation]
            self.metrics[operation] = [
                m for m in metrics if m.timestamp > cutoff_time
            ]
            removed += len(metrics) - len(self.metrics[operation])
        
        return removed


# Instance globale
performance_monitor = PerformanceMonitor()


def track_performance(operation: str):
    """
    Décorateur pour tracker la performance d'une fonction.
    
    Utilisation:
        @track_performance("database_query")
        def get_offers():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_id = performance_monitor.start(operation)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                performance_monitor.end(op_id, operation)
        return wrapper
    return decorator


__all__ = ["PerformanceMonitor", "PerformanceMetric", "performance_monitor", "track_performance"]
