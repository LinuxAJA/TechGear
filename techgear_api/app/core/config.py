"""Configuracion central de la aplicacion.

Sigue el principio 12-Factor: toda la configuracion llega por variables de
entorno y se valida al arrancar. Si falta MONGODB_URL, la aplicacion falla de
inmediato con un mensaje claro en vez de romperse a mitad de una peticion.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores de configuracion leidos desde el archivo .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Metadatos de la aplicacion ────────────────────────
    app_name: str = "TechGear API"
    app_version: str = "1.0.0"
    debug: bool = False

    # ── MongoDB Atlas ─────────────────────────────────────
    # Sin valor por defecto a proposito: es obligatoria.
    mongodb_url: str
    mongodb_db: str = "techgear_db"
    mongodb_test_db: str = "techgear_test"

    # ── API ───────────────────────────────────────────────
    api_v1_prefix: str = "/api/v1"

    # Se recibe como texto separado por comas para que el .env sea legible;
    # pydantic-settings exigiria formato JSON si se declarara como list[str].
    cors_origins: str = "http://localhost:8000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte 'a,b' en ['a', 'b'] para el middleware de CORS."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuracion en cache.

    El decorador @lru_cache evita releer y revalidar el archivo .env en cada
    peticion: se construye una sola instancia durante toda la vida del proceso.
    """
    return Settings()
