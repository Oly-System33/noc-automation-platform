# NOC Dashboard Frontend

Base técnica del frontend independiente del Dashboard NOC. El dashboard visual
completo todavía no se implementó en esta parte.

## Instalación

```bash
npm install
```

## Desarrollo

```bash
npm run dev
```

La aplicación queda disponible en `http://localhost:5173` y espera que FastAPI
esté disponible en `http://localhost:8000`.

## Compilación

```bash
npm run build
```

## Tests

```bash
npm run test:run
```

## Variables

- `VITE_API_BASE_URL`: URL base del backend FastAPI.
- `VITE_POLL_INTERVAL_MS`: intervalo base de actualización en milisegundos.

Usar `.env.example` como referencia. Las variables se leen exclusivamente a
través de `src/config/env.ts`.

## Referencias visuales

- `docs/ui/dashboard-main-reference.png`
- `docs/ui/noc-logo-reference.png`

Estas referencias son obligatorias para las siguientes etapas. Esta base no
intenta reproducir todavía el diseño final del dashboard.
