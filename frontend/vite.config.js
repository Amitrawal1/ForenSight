import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // File watching through Docker bind mounts on macOS needs polling
    watch: { usePolling: true },
  },
});
