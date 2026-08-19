"""Utilidades transversales."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Devuelve el instante actual en UTC, con zona horaria explicita.

    Se usa en todo el proyecto en lugar de datetime.now() porque un datetime
    sin zona horaria (naive) es ambiguo: al guardarlo y leerlo de MongoDB no
    hay forma de saber a que huso pertenecia.
    """
    return datetime.now(timezone.utc)
