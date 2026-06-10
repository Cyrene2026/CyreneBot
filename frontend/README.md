# CyreneBot Console

Vue 3 + TypeScript + Vite frontend for the CyreneBot server API.

## Development

```bash
npm install
npm run dev -- --host 127.0.0.1
```

The Vite dev server listens on `http://127.0.0.1:5173/`.

By default, dev proxy rules forward CyreneBot API paths such as `/health`,
`/providers`, `/chat`, `/agents`, and `/plugins` to `http://127.0.0.1:8000`.
Start the Python server on that port before using API-backed panels.

For a different backend origin, set:

```bash
VITE_CYRENE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1
```

## Build

```bash
npm run build
```

The build runs `vue-tsc` before producing the Vite `dist/` output.
