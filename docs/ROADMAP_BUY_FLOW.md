# BUY-FLOW (POST-MVP) — NO IMPLEMENTAR TODAVÍA

Estado: **ROADMAP — NO IMPLEMENTAR**.

Este documento captura la propuesta de feature para convertir la app de detector de oportunidades a flujo completo de compra. No debe ser implementado antes de completar el MVP actual (AS24 DE → comparables ES → costes → rentabilidad → oportunidad).

## Flujo propuesto

1. **La app detecta una oportunidad**
   - Precio Alemania.
   - Costes de importación (`ImportCostProfile`).
   - Coste estimado de matriculación.
   - Viaje/transporte.
   - Beneficio esperado / margen final.
2. **Usuario pulsa: "Voy a comprar este coche"**
3. **La app genera automáticamente el viaje**
   - Aeropuerto más cercano al concesionario.
   - Vuelos disponibles para la fecha.
   - Cómo llegar desde el aeropuerto al concesionario: tren, autobús, metro, taxi/VTC si procede.
   - Horarios coordinados con la hora de llegada del vuelo.
   - Tiempo total y coste.
4. **Regreso con el coche**
   - Ruta Alemania → España.
   - Kilómetros.
   - Combustible estimado.
   - Peajes.
   - Posibles ferris si la ruta los requiere.
   - Tiempo estimado.
   - Coste total.
5. **Recalcula la rentabilidad real** con todos los costes del viaje.

Ejemplo (estimación):

```
Compra: 18.500 €
Impuestos/matriculación: 1.450 €
Vuelo: 120 €
Transporte al concesionario: 35 €
Combustible: 280 €
Peajes: 160 €
Otros: 100 €
Coste total: 20.645 €
Venta estimada España: 24.500 €
Beneficio estimado: 3.855 €
```

## Modificaciones importantes

No integrar `https://www.dieselogasolina.com/` como dependencia crítica.

- `dieselogasolina.com` puede usarse como **fuente de referencia** para matriculación.
- El sistema debe tener su propio `ImportCostCalculator` (ya existe `app/config/import_costs.py` con perfiles estáticos por país).
- Posteriormente añadir proveedores externos cuando sea necesario.

## Arquitectura propuesta para viajes

```text
TravelPlanner
    ├── FlightProvider
    ├── GroundTransportProvider
    ├── Maps/RoutingProvider
    └── Toll/CostProvider
```

## Dependencias futuras (NO IMPLEMENTAR)

- `ImportCostCalculator` propio (no atado a web externa como dependencia crítica).
- `TravelPlanner` con proveedores desacoplados (`FlightProvider`, `GroundTransportProvider`, `Maps/RoutingProvider`, `Toll/CostProvider`).
- Posible integración con API de mapas (rutas, horarios de transporte público, peajes).
- Posible integración con datos de vuelos (no implementado en MVP).

## Restricción explícita

**POST-MVP — NO IMPLEMENTAR TODAVÍA.**
Primero completar: AS24 DE → comparables ES → costes → rentabilidad → oportunidad.
