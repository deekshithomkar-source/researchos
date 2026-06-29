import { defineConfig } from "vite";
import { tmpdir } from "node:os";
import { join } from "node:path";

export default defineConfig({
  cacheDir: process.env.VITE_CACHE_DIR || join(tmpdir(), "researchos-vite-cache"),
  build: {
    emptyOutDir: false,
  },
});
