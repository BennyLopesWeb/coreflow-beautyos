# @coreflow/sdk

SDK TypeScript do CoreFlow Platform (mobile/web).

## Build obrigatório

O pacote publica `main`/`types` apontando para `dist/`:

```json
"main": "dist/index.js",
"types": "dist/index.d.ts"
```

`dist/` está no `.gitignore`. Após alterar `src/` (ou ao clonar a branch), rode:

```bash
cd packages/coreflow-sdk
npm install
npm run build
```

O app Expo (`frontend/`) resolve `@coreflow/sdk` via `file:../packages/coreflow-sdk` e carrega o **`dist/`** gerado — não há path mapping para `src/`.

## Scripts

- `npm run build` — emite `dist/`
- `npm run typecheck` — `tsc --noEmit`
