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

## Integración F3

El Dashboard principal consume mediante TanStack Query:

- `GET /health` para los indicadores de FastAPI y PostgreSQL.
- `GET /api/dashboard/summary` para las ocho tarjetas KPI.
- `GET /api/incidents?limit=6` para incidentes recientes.

Las consultas se actualizan automáticamente según `VITE_POLL_INTERVAL_MS` y
pueden refrescarse en conjunto desde el control superior. Durante un refresco se
conservan los últimos datos válidos. La interfaz incluye estados compactos de
carga, lista vacía y error, sin reemplazar datos fallidos por valores mock.

Operaciones, aprobaciones e intervención manual continúan usando datos estáticos
de F2. Sus botones siguen siendo exclusivamente visuales. Las líneas de tendencia
de los KPI también continúan siendo decorativas y no representan series reales.

## Integración F4

Operaciones, aprobaciones e intervenciones se obtienen desde `/api/operations`,
`/api/approvals` y `/api/interventions`. Pausa, reanudación, aprobación y rechazo
usan las transiciones persistidas de scheduled actions. Las mutations invalidan
solo resumen, incidentes y listas operativas afectadas.

El runbook se consulta al abrir el diálogo mediante una vista segura y
estructurada; no se descarga Excel ni se exponen contactos. El backend actual no
puede reintentar efectos externos de forma idempotente, por lo que retry responde
`409 retry_not_safe` y la interfaz informa la limitación sin simular éxito.

Cada panel conserva datos anteriores durante polling y presenta estados propios
de carga, vacío y error. Los conflictos `404/409` se traducen a mensajes
controlados sin mostrar bodies internos.
