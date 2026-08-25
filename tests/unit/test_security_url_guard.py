"""Tests de seguridad SEC.SSRF.1 — app.core.url_guard."""

from __future__ import annotations

import pytest

import app.core.url_guard as guard
from app.core.url_guard import UnsafeURLError, ensure_public_http_url


class TestSchemes:
    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "data:image/png;base64,AAAA",
            "ftp://example.com/pub",
            "gopher://127.0.0.1:70/",
        ],
    )
    def test_rechaza_esquemas_no_http(self, url: str) -> None:
        with pytest.raises(UnsafeURLError):
            ensure_public_http_url(url)

    def test_acepta_http_y_https(self) -> None:
        assert ensure_public_http_url("https://www.mobile.de/") == "https://www.mobile.de/"
        assert (
            ensure_public_http_url("http://www.autoscout24.es/anuncio/123")
            == "http://www.autoscout24.es/anuncio/123"
        )


class TestIPLiterales:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8000/admin",
            "http://localhost/x",
            "http://LOCALHOST:3000/",
            "http://[::1]:9000/",
            "http://10.0.0.5/internal",
            "http://172.16.0.1/db",
            "http://192.168.1.10/router",
            "http://169.254.169.254/latest/meta-data/",
            "http://0.0.0.0/",
        ],
    )
    def test_bloquea_ips_internas(self, url: str) -> None:
        with pytest.raises(UnsafeURLError):
            ensure_public_http_url(url)

    def test_bloquea_credenciales_embebidas(self) -> None:
        with pytest.raises(UnsafeURLError):
            ensure_public_http_url("http://user:pass@8.8.8.8/")


class TestHostnames:
    def test_hostname_docker_interno_bloqueado(self) -> None:
        guard._DNS_CACHE["db"] = (True, float("inf"))
        try:
            with pytest.raises(UnsafeURLError):
                ensure_public_http_url("http://db:5432/")
        finally:
            guard._DNS_CACHE.pop("db", None)

    def test_hostname_publico_permitido(self) -> None:
        guard._DNS_CACHE["www.mobile.de"] = (False, float("inf"))
        try:
            assert (
                ensure_public_http_url("https://www.mobile.de/x")
                == "https://www.mobile.de/x"
            )
        finally:
            guard._DNS_CACHE.pop("www.mobile.de", None)

    def test_dns_roto_permite_pasar(self) -> None:
        guard._DNS_CACHE["no-existe.invalid"] = (False, float("inf"))
        try:
            assert ensure_public_http_url("https://no-existe.invalid/a")
        finally:
            guard._DNS_CACHE.pop("no-existe.invalid", None)


class TestURLMalformadas:
    def test_sin_hostname(self) -> None:
        with pytest.raises(UnsafeURLError):
            ensure_public_http_url("https://")

    def test_vacia(self) -> None:
        with pytest.raises((UnsafeURLError, ValueError)):
            ensure_public_http_url("")
