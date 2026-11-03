/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Absolute backend origin, e.g. http://127.0.0.1:8000. Leave unset to use the dev proxy. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
