import { defineConfig, loadEnv } from "vite";
import { tmpdir } from "node:os";
import { join } from "node:path";

export default defineConfig(({ command, mode }) => {
  if (command === "build" && process.env.VERCEL_ENV === "production") {
    const { VITE_API_URL } = loadEnv(mode, process.cwd(), "VITE_API_URL");
    if (!URL.canParse(VITE_API_URL) || new URL(VITE_API_URL).protocol !== "https:") {
      throw new Error("Set VITE_API_URL to the public HTTPS FastAPI URL in Vercel Production settings before deploying.");
    }
  }

  return {
    cacheDir: process.env.VITE_CACHE_DIR || join(tmpdir(), "researchos-vite-cache"),
    build: {
      emptyOutDir: false,
    },
  };
});
