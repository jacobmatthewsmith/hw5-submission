import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend's CORS allows this origin (see backend/main.py).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
