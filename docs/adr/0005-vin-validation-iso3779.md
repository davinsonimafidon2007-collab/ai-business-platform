# ADR-005: Validación de VIN ISO 3779 en el dominio

- Estado: Aceptado
- Fecha: 2026-08-15
- Área: Calidad de datos / Búsqueda por VIN

## Contexto

Se ofrece búsqueda de un vehículo por VIN (`GET /vehicles/vin/{vin}`). El VIN
almacenado (`Vehicle.vin`) puede venir sin verificar de anuncios/proveedores, y
muchos no incluyen dígito de control fiable.

## Decisión

`app/utils/vin_validator.py`:
- Valida estructura ISO 3779: 17 caracteres alfanuméricos sin I/O/Q.
- Normaliza a mayúsculas al buscar (repo compara `vin` en mayúsculas).
- Dígito de control (posición 9, NHTSA/SAE J853) es **opcional**: solo se
  verifica si el cliente lo pide explícitamente (`check_digit=True`).
- El endpoint devuelve 422 si el formato es inválido y 404 si no existe.

## Justificación

- El análisis es barato y sin dependencias; el check digit usa transliteración
  + pesos módulo 11 estándar.
- Como los proveedores no garantizan check digits reales, la validación por
  defecto es de forma (no de check) para no descartar anuncios legítimos.

## Consecuencias

- Búsqueda de VIN acotada al usuario y case-insensitive.
- Posibles VIN con check digit incorrecto se aceptan (solo forma).

## Alternativas

- Validación estricta con check digit siempre: descartaría VINs válidos en
  la práctica porque muchos orígenes no calculan el dígito correctamente.
- Sin validación: permitiría garbage en el campo y búsquedas sin sentido.