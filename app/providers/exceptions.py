"""Excepciones específicas del dominio de proveedores."""

from __future__ import annotations


class ProviderError(Exception):
    """Excepción base para errores de proveedores."""

    def __init__(self, message: str, provider: str | None = None) -> None:
        self.provider = provider
        super().__init__(message)


class ProviderConnectionError(ProviderError):
    """Error de conexión con el proveedor."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        self.original_error = original_error
        super().__init__(message, provider)


class ProviderTimeoutError(ProviderError):
    """Timeout al consultar el proveedor."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.timeout = timeout
        super().__init__(message, provider)


class ProviderRateLimitError(ProviderError):
    """Rate limit excedido en el proveedor."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, provider)


class ProviderAuthenticationError(ProviderError):
    """Error de autenticación con el proveedor."""

    pass


class ProviderNotFoundError(ProviderError):
    """Recurso no encontrado en el proveedor."""

    pass


class ProviderParsingError(ProviderError):
    """Error al parsear la respuesta del proveedor."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        raw_data: dict | None = None,
    ) -> None:
        self.raw_data = raw_data
        super().__init__(message, provider)


class ProviderMaxRetriesExceededError(ProviderError):
    """Se excedió el número máximo de reintentos."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        attempts: int = 0,
    ) -> None:
        self.attempts = attempts
        super().__init__(message, provider)


class ProviderResponseTooLargeError(ProviderError):
    """La respuesta del proveedor supera el límite de bytes configurado.

    Se lanza para evitar fugas de memoria al descargar cuerpos gigantes
    (TASK-010). El límite se controla leyendo la respuesta en streaming, de
    forma que nunca se llega a materializar el cuerpo completo en memoria.
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        max_bytes: int = 0,
    ) -> None:
        self.max_bytes = max_bytes
        super().__init__(message, provider)


class ProviderUnavailableError(ProviderError):
    """Proveedor no disponible temporalmente."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
    ) -> None:
        super().__init__(message, provider)