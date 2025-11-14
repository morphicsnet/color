import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Allow overriding base path at deploy time (e.g., GitHub Pages subpath)
  base: process.env.BASE_PATH ?? "/"
});
