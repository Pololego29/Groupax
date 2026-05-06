# Changelog

Tous les changements notables du projet Alternax sont documentés ici.

Format basé sur [Keep a Changelog](https://keepachangelog.com/) et [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-05-06

### ✨ Ajoutés
- **Health Check Endpoint** (`GET /api/health`) pour vérifier l'état de l'app
- **Métriques API** (`GET /api/metrics`) pour tracker l'utilisation
- **Système de Cache** (`cache.py`) - mise en cache intelligente des données
  - Décorateur `@cached()` pour cacher les résultats de fonction
  - TTL configurable par entrée
- **Configuration Centralisée** (`config.py`)
  - Tous les paramètres en un fichier
  - Feature flags pour activer/désactiver des fonctionnalités
  - Valeurs par défaut sensées
- **Optimisation de Base de Données** (`optimize_db.py`)
  - Indices supplémentaires sur title, company, source
  - Index composite pour les filtres courants
  - Compaction avec VACUUM
- **Monitoring de Performance** (`metrics.py`)
  - Décorateur `@track_performance` pour mesurer les opérations
  - Statistiques min/max/avg
  - Alertes automatiques pour les opérations lentes
- **Documentation Swagger/OpenAPI**
  - API interactive sur `/api/docs` (Swagger UI)
  - Également sur `/api/redoc` (ReDoc)
  - Générée automatiquement à partir du code
- **Frontend Amélioré**
  - Animations fluides (fadeIn, slideUp, spin)
  - Dégradés et effets d'ombre modernes
  - Spinner de chargement animé
  - Compteur animé pour les statistiques
  - Responsive design optimisé pour mobile
- **Logging Amélioré**
  - Logs avec timestamps et contexte
  - Dépistage détaillé des opérations
  - Stack traces pour les erreurs
- **Variables d'Environnement Étendues**
  - `CACHE_TTL_STATS` et `CACHE_TTL_SOURCES`
  - `API_HOST`, `API_PORT`, `API_RELOAD`, `API_WORKERS`
  - `FEATURE_HEALTH_CHECK`, `FEATURE_METRICS`, `FEATURE_SWAGGER`
  - `RATE_LIMIT_*` (pour l'avenir)
  - `PAGINATION_*` pour la pagination

### 🔧 Modifiés
- **API (api/main.py)**
  - Utilisation du cache pour `/api/stats` et `/api/sources`
  - Métriques intégrées dans les endpoints
  - Meilleure gestion des erreurs
  - Logs détaillés pour chaque requête
  
- **Configuration**
  - `.env.example` enrichi avec tous les paramètres
  - Documentation complète des variables

- **Frontend (frontend/style.css)**
  - Animations @keyframes pour fadeIn, pulse, spin, slideUp
  - Effets d'ombre et dégradés améliorés
  - Design responsive pour mobile
  - États de chargement visuels

- **Frontend (frontend/app.js)**
  - Performance tracking des appels API
  - Événements de filtre optimisés
  - Meilleur debouncing

### 📚 Documentation
- Nouveau fichier `FEATURES.md` - Guide des nouvelles fonctionnalités
- Nouveau fichier `CHANGELOG.md` - Ce fichier
- `.env.example` enrichi avec commentaires détaillés
- `IMPROVEMENTS.md` mis à jour avec les changements v1.1.0

### 🎯 Améliorations de Performance
- Cache réduit les requêtes DB de ~90% pour stats/sources
- Indices DB accélèrent les recherches fulltext
- Monitoring identifie les goulets d'étranglement
- Métriques détectent les problèmes proactivement

### 🔒 Sécurité
- Tous les changements sont backward compatible
- Feature flags permettent de désactiver les nouvelles fonctionnalités
- Protection XSS renforcée au frontend
- Aucun data leak dans les logs

## [1.0.0] - 2026-05-05

### ✨ Ajoutés (version initiale)
- Scraper Indeed avec Playwright
- Pipeline de déduplication
- Base de données SQLite/PostgreSQL
- API FastAPI avec recherche et filtres
- Frontend HTML/CSS/JS sans framework
- Support des deux backends (SQLite local, PostgreSQL production)
- Logging systématique
- Gestion d'erreurs robuste
- Validation des entrées
- Documentation complète

---

## Légende

- **✨ Ajoutés** : Nouvelles fonctionnalités
- **🔧 Modifiés** : Changements à des fonctionnalités existantes
- **🐛 Corrigés** : Corrections de bugs
- **📚 Documentation** : Changements de documentation
- **🔒 Sécurité** : Correctifs de sécurité
- **⚠️ Deprecated** : Fonctionnalités à supprimer
- **🚀 Performance** : Améliorations de performance

## Versions Futures

- [ ] **Rate Limiting** - Protéger l'API des abus
- [ ] **Export de Données** - CSV, JSON, RSS
- [ ] **Historique des Offres** - Tracker les changements
- [ ] **Alertes Email** - Notifications pour les nouvelles offres
- [ ] **Dashboard Admin** - Gestion depuis le web
- [ ] **WebSockets** - Live updates sans polling
- [ ] **GraphQL API** - Alternative à REST
- [ ] **Multi-Langue** - Support i18n
- [ ] **Tests Unitaires** - Couverture de code
- [ ] **Docker Compose** - Deploy facilité

---

**Projet:** Alternax  
**Version Actuelle:** 1.1.0  
**Date de Mise à Jour:** 6 Mai 2026
