"""Capa de IA opcional y degradable del producto.

Reglas duras heredadas de `CLAUDE.md` que esta capa NUNCA rompe:

- CERO datos inventados. La IA solo (a) traduce lenguaje natural a los filtros
  ya soportados por el contrato de convocatorias y deja que Postgres traiga los
  resultados REALES; (b) resume texto que YA existe en la BD; (c) responde
  dudas de uso con el manual real como contexto.
- Si el proveedor de IA no está disponible, se degrada con gracia: nunca se
  inventa ni se rompe la app. La búsqueda cae a un filtro `q=` de texto plano;
  resumen y soporte devuelven un mensaje claro de "servicio no disponible".

El contrato de estos endpoints vive en `docs/ai-contract.md` (nuevo y aparte;
el contrato de convocatorias/fuentes/stats sigue congelado).
"""
