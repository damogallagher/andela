import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || "http://localhost:8000";

function devRootRedirectPlugin() {
  return {
    name: "dev-root-redirect",
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        if (request.url === "/" || request.url === "") {
          response.statusCode = 302;
          response.setHeader("Location", "/static/frontend/");
          response.end();
          return;
        }
        next();
      });
    },
  };
}

export default defineConfig({
  base: "/static/frontend/",
  build: {
    outDir: "../app/static/frontend",
    emptyOutDir: true,
  },
  plugins: [devRootRedirectPlugin(), react()],
  server: {
    watch: {
      usePolling: process.env.CHOKIDAR_USEPOLLING === "true",
    },
    proxy: {
      "/api": apiProxyTarget,
      "/docs": apiProxyTarget,
      "/health": apiProxyTarget,
      "/openapi.json": apiProxyTarget,
    },
  },
});
