# ADR-003: Métricas de negocio prometheus-style en proceso

- Estado: Aceptado
- Fecha: 2026-08-15
- Área: Observabilidad

## Contexto

Se necesitan métricas de negocio (peticiones de búsqueda por proveedor,
oportunidades generadas, duración de órdenes) visibles en `/admin/metrics`,
sin añadir dependencias pesadas.

## Decisión

`app/services/metrics_service.py`: registry in-memory thread-safe (singleton)
con `Counter`/`Histogram`, expuesto en formato Prometheus text/plain vía
`GET /admin/metrics` (protegido por `require_admin`). Inyección mínima en el
pipeline de búsqueda: `search_requests_total{provider}`, `opportunities_
generated_total` y `search_order_duration_seconds` (histograma) en el job.

## Justificación

- Solo stdlib: sin `prometheus-client`, alineado al constraint de dependencias.
- Text exposition compatible con prometheus/grafana cuando se use `--profile obs`.
- Infraestructura de prometheus ya documentada en `.env.example`.

## Consecuencias

- Las métricas se pierden al reiniciar el proceso (in-memory).
- El endpoint es admin-only; en el futuro puede scrapearse desde prometheus.

## Alternativas

- `prometheus-client`: más completo pero añade dependencia.
- Stack exporter separado: sobrecarga para el despliegue personal actual.