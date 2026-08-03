"""ProviderCanaryJob — Detecta parsers rotos (0 listings en vivo).

Task A.6: AS24 con 0 anuncios = fallo del job.
mobile.de con 403 anti-bot = WARN (no falla el job hasta tener proxy).
"""

from __future__ import annotations

from app.jobs.base import Job, JobContext, JobResult
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
        mobile = MobileDeProvider()
        try:
            results = await mobile.search(MOBILE_SEARCH_URL)
            count = len(results) if results else 0
            data["mobile_de"] = {"count": count}
            mobile_status = "ok" if count > 0 else "empty"
            if count == 0:
                logger.warning("canary mobile.de: 0 listings")
            else:
                logger.info("canary mobile.de OK: %d listings", count)
        except ProviderConnectionError as exc:
            data["mobile_de"] = {"status": "blocked", "error": str(exc)}
            mobile_status = "blocked"
            logger.warning("canary mobile.de WARN (anti-bot): %s", exc)
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

        if as24_ok:
            return JobResult(
                success=True,
                message=f"Canary OK (AS24 listings>0, mobile={mobile_status})",
                data=data,
            )

        return JobResult(
            success=False,
            message="Canary FAIL: AutoScout24 devolvió 0 listings o error",
            data=data,
        )