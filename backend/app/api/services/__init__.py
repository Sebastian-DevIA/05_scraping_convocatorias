"""Servicios de la API: TODA la lógica de consulta vive aquí.

Los routers (`app.api.routers`) solo orquestan (request -> service -> response);
estos módulos construyen las queries SQLAlchemy y mapean los modelos ORM a los
schemas Response congelados en `docs/api-contract.md`.
"""
