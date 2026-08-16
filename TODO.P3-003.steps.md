# TODO.P3-003.steps.md — ARCH-003: SOLID ligero en providers / orchestrator

Backlog: P3-003 (cierra backlog original P0→P3).

## Pasos

- [x] 1. Crear `app/providers/parsers/__init__.py`
- [x] 2. Crear `app/providers/parsers/autoscout24_parser.py`
      (helpers puros + parse `__NEXT_DATA__` + `listing_dict_to_result`)
- [x] 3. Adelgazar `app/providers/autoscout24.py`: delegar en parser, conservando
      la API de métodos que usan los tests (`_parse_search_results`,
      `_parse_listings_from_next_data`, `_listing_dict_to_result`, helpers puros).
- [x] 4. Crear `app/services/search_result_analyzer.py`
      (`SearchResultAnalyzer.analyze` + `build_negotiation_input` + `run_negotiation`)
- [x] 5. `app/services/search_orchestrator.py`: `_analyze_vehicle` como wrapper fino
      que delega en `SearchResultAnalyzer`.
- [x] 6. `app/providers/base.py`: docstring de responsabilidades
      (HTTP cross-cutting → ProviderHttpClient; parse → subclass/parser).
- [x] 7. No se tocó config (no aplica).
- [x] 8. Verificación completada:
      - Módulos tocados (AS24 + orchestrator + profile + mobile_de + http_client): **198 passed**
      - Suite `tests/unit` global: **1075 passed**
      - `ruff check` en archivos tocados: **All checks passed!**

## Resultado

Refactor SOLID ligero completado sin cambio de comportamiento ni de API pública.
Cierra el backlog original P0→P3.
