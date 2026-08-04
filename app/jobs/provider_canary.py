"""ProviderCanaryJob — Detecta parsers rotos (0 listings en vivo).

Task A.6: AS24 con 0 anuncios = fallo del job.
Task A.5: mobile.de con 403 anti-bot = WARN (no falla el job) si NO hay
proxy/cookies configurados. Si hay proxy/cookies (anti-bot configurado),
mobile.de pasa a ser estricto: 403 o 0 listings derriban el job (FAIL).
"""

from __future__ import annotations

from app.core.config import settings
from app.jobs.base import Job, JobContext, JobResult
from app.jobs.canary_state import set_last_canary_result
from app.providers.autoscout24 import AutoScout24Provider
from app.providers.exceptions import ProviderConnectionError, ProviderError
from app.providers.mobile_de import MobileDeProvider

AS24_SEARCH_URL = (
    "https://www.autoscout24.de/lst"
    "?atype=C&cy=D&desc=0&sortage=age&ustate=N%2CU"
)
MOBILE_SEARCH_URL = (
    "https://suchen.mobile.de/fahrzeuge/search.html"
    "?dam=false&isSearchRequest=true&ref=srp&sb=rel&vc=Car"
)


def _anti_bot_configured() -> bool:
    """True si hay proxy o cookies anti-bot configurados en settings."""
    proxy = (getattr(settings, "provider_http_proxy", None) or "").strip()
    cookies = (getattr(settings, "provider_http_cookies", None) or "").strip()
    return bool(proxy or cookies)


class ProviderCanaryJob(Job):
    @property
    def name(self) -> str:
        return "provider_canary"

    async def execute(self, context: JobContext) -> JobResult:
        logger = context.logger
        data: dict = {"autoscout24": {}, "mobile_de": {}}
        as24_ok = False
        mobile_status = "skip"

        # --- AutoScout24 (obligatorio) ---
        provider = AutoScout24Provider()
        try:
            results = await provider.search(AS24_SEARCH_URL)
            count = len(results) if results else 0
            data["autoscout24"] = {
                "count": count,
                "sample_id": results[0].external_id if results else None,
                "sample_price": results[0].price if results else None,
            }
            as24_ok = count > 0
            if as24_ok:
                logger.info("canary AS24 OK: %d listings", count)
            else:
                logger.error("canary AS24 FAIL: 0 listings (parser/DOM roto?)")
        except ProviderError as exc:
            data["autoscout24"] = {"error": str(exc)}
            logger.error("canary AS24 ERROR: %s", exc)
        except Exception as exc:  # noqa: BLE001
            data["autoscout24"] = {"error": f"{type(exc).__name__}: {exc}"}
            logger.exception("canary AS24 unexpected: %s", exc)
        finally:
            await provider.close()

        # --- mobile.de (warn si anti-bot) ---
        strict_mobile = _anti_bot_configured()
        mobile = MobileDeProvider()
        try:
            results = await mobile.search(MOBILE_SEARCH_URL)
            count = len(results) if results else 0
            data["mobile_de"] = {"count": count}
            mobile_status = "ok" if count > 0 else "empty"
            if count == 0:
                if strict_mobile:
                    logger.error(
                        "canary mobile.de FAIL: 0 listings with proxy configured"
                        " (possible selector drift)"
                    )
                else:
                    logger.warning("canary mobile.de: 0 listings")
            else:
                logger.info("canary mobile.de OK: %d listings", count)
        except ProviderConnectionError as exc:
            data["mobile_de"] = {"status": "blocked", "error": str(exc)}
            mobile_status = "blocked"
            if strict_mobile:
                logger.error(
                    "canary mobile.de FAIL: still blocked with proxy configured: %s",
                    exc,
                )
            else:
                logger.warning("canary mobile.de blocked (no proxy; WARN): %s", exc)
        except ProviderError as exc:
            data["mobile_de"] = {"error": str(exc)}
            mobile_status = "error"
            logger.error("canary mobile.de ERROR: %s", exc)
        except Exception as exc:  # noqa: BLE001
            data["mobile_de"] = {"error": f"{type(exc).__name__}: {exc}"}
            mobile_status = "error"
            logger.exception("canary mobile.de unexpected: %s", exc)
        finally:
            await mobile.close()

        data["mobile_status"] = mobile_status
        data["strict_mobile"] = strict_mobile

        if as24_ok:
            if strict_mobile and mobile_status != "ok":
                success = False
                message = (
                    "Canary FAIL: mobile.de bloqueado con proxy configurado "
                    f"(status={mobile_status})"
                )
            else:
                success = True
                message = f"Canary OK (AS24 listings>0, mobile={mobile_status})"
        else:
            success = False
            message = "Canary FAIL: AutoScout24 devolvió 0 listings o error"

        set_last_canary_result(success=success, message=message, data=data)
        return JobResult(success=success, message=message, data=data)