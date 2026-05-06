const fs = require("fs");

const apiUrl = process.env.API_URL || "http://localhost:8000/api";

fs.writeFileSync(
  "frontend/config.js",
  `// Généré au build — ne pas modifier manuellement\nconst API_URL = "${apiUrl}";\n`
);

console.log("[build] config.js généré → API_URL =", apiUrl);
