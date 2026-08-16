"""Parsers específicos de providers de vehículos.

Cada provider concentra su lógica de parseo en un módulo dedicado
(``autoscout24_parser``, etc.) con funciones puras y sin dependencia
directa de HTTP o de ``self``. Los providers delegan en estos parsers
pero conservan su API pública estable (``search``, ``get_vehicle``).
"""
