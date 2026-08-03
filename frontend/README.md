# NOC Dashboard Frontend

Frontend independiente del Dashboard NOC.

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

Estas referencias son obligatorias para las siguientes etapas.

## Dashboard principal estático

El Dashboard principal fue implementado en F2 a partir de la referencia visual
aprobada. Utiliza datos estáticos tipados y todavía no consume FastAPI. Los
controles de aprobación, pausa, reanudación y reintento son exclusivamente
visuales y no ejecutan operaciones reales.
