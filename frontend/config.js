// config.js — URL de l'API
// -------------------------------------------------------
// En local      : laisser http://localhost:8000/api
// Sur Vercel    : remplacer par votre URL Railway
//                 Exemple : https://alternax.up.railway.app/api
// -------------------------------------------------------
const API_URL = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? "http://localhost:8000/api"
  : "https://REMPLACER_PAR_URL_RAILWAY/api";
