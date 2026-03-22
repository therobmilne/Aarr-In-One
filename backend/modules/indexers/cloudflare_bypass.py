"""Cloudflare bypass engine — headless browser to solve JS challenges.

Uses Playwright (preferred) or falls back to basic cookie-based approach.
Replaces FlareSolverr as a built-in feature.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from backend.logging_config import get_logger

logger = get_logger("cloudflare_bypass")

try:
    from playwright.async_api import async_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.info("playwright_not_available", msg="Install playwright for Cloudflare bypass")


@dataclass
class BypassResult:
    success: bool
    url: str
    status_code: int = 0
    body: str = ""
    cookies: dict = field(default_factory=dict)
    user_agent: str = ""
    error: str = ""
    elapsed_ms: float = 0


# Cache solved sessions (cookies + user agent) per domain
_session_cache: dict[str, dict] = {}

# Rotating user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]
_ua_index = 0


def _get_next_ua() -> str:
    global _ua_index
    ua = USER_AGENTS[_ua_index % len(USER_AGENTS)]
    _ua_index += 1
    return ua


def _get_domain(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).netloc


async def bypass_cloudflare(url: str, timeout_ms: int = 30000) -> BypassResult:
    """Attempt to bypass Cloudflare protection on a URL.

    Strategy:
    1. Check session cache for existing solved cookies
    2. Try direct request with rotating user-agent
    3. If blocked, use Playwright headless browser to solve challenge
    4. Cache the resulting cookies for future requests
    """
    domain = _get_domain(url)
    start = time.monotonic()

    # 1. Try cached session
    cached = _session_cache.get(domain)
    if cached:
        result = await _try_with_cookies(url, cached["cookies"], cached["user_agent"])
        if result.success:
            result.elapsed_ms = (time.monotonic() - start) * 1000
            return result
        # Cache expired, remove it
        del _session_cache[domain]

    # 2. Try direct request with rotating UA
    ua = _get_next_ua()
    result = await _try_direct(url, ua)
    if result.success:
        result.elapsed_ms = (time.monotonic() - start) * 1000
        return result

    # 3. Try Playwright if available
    if HAS_PLAYWRIGHT:
        result = await _solve_with_playwright(url, timeout_ms)
        if result.success:
            _session_cache[domain] = {
                "cookies": result.cookies,
                "user_agent": result.user_agent,
                "solved_at": time.time(),
            }
        result.elapsed_ms = (time.monotonic() - start) * 1000
        return result

    # 4. No bypass available
    return BypassResult(
        success=False,
        url=url,
        error="Cloudflare bypass unavailable. Install playwright: pip install playwright && playwright install chromium",
        elapsed_ms=(time.monotonic() - start) * 1000,
    )


async def _try_direct(url: str, user_agent: str) -> BypassResult:
    """Try a direct request without solving challenges."""
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": user_agent},
        ) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and "cf-browser-verification" not in resp.text.lower():
                return BypassResult(
                    success=True,
                    url=url,
                    status_code=resp.status_code,
                    body=resp.text,
                    user_agent=user_agent,
                )
            return BypassResult(
                success=False,
                url=url,
                status_code=resp.status_code,
                error=f"Cloudflare challenge detected (HTTP {resp.status_code})",
            )
    except Exception as e:
        return BypassResult(success=False, url=url, error=str(e))


async def _try_with_cookies(url: str, cookies: dict, user_agent: str) -> BypassResult:
    """Try a request using previously solved cookies."""
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            cookies=cookies,
            headers={"User-Agent": user_agent},
        ) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return BypassResult(
                    success=True,
                    url=url,
                    status_code=200,
                    body=resp.text,
                    cookies=cookies,
                    user_agent=user_agent,
                )
    except Exception:
        pass
    return BypassResult(success=False, url=url)


async def _solve_with_playwright(url: str, timeout_ms: int = 30000) -> BypassResult:
    """Use Playwright headless browser to solve Cloudflare JS challenges."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                user_agent=_get_next_ua(),
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            # Navigate and wait for challenge to resolve
            response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            # Wait for Cloudflare challenge to complete (up to timeout)
            try:
                await page.wait_for_function(
                    """() => {
                        return !document.querySelector('#challenge-running') &&
                               !document.querySelector('.cf-browser-verification') &&
                               !document.title.includes('Just a moment');
                    }""",
                    timeout=timeout_ms,
                )
            except Exception:
                pass  # Timeout waiting for challenge, try anyway

            # Small delay for any final redirects
            await asyncio.sleep(2)

            # Get the page content and cookies
            body = await page.content()
            browser_cookies = await context.cookies()
            ua = await page.evaluate("() => navigator.userAgent")

            cookies = {}
            for c in browser_cookies:
                if c["domain"] in url or _get_domain(url) in c.get("domain", ""):
                    cookies[c["name"]] = c["value"]

            status = response.status if response else 0

            await browser.close()

            if status == 200 or "cf_clearance" in cookies:
                logger.info("cloudflare_solved", url=url, cookies=len(cookies))
                return BypassResult(
                    success=True,
                    url=url,
                    status_code=status,
                    body=body,
                    cookies=cookies,
                    user_agent=ua,
                )
            else:
                return BypassResult(
                    success=False,
                    url=url,
                    status_code=status,
                    error=f"Challenge not solved (HTTP {status})",
                )

    except Exception as e:
        logger.error("playwright_bypass_failed", url=url, error=str(e))
        return BypassResult(success=False, url=url, error=f"Playwright error: {e}")


def clear_session_cache() -> None:
    """Clear all cached bypass sessions."""
    _session_cache.clear()


def get_cache_status() -> dict:
    """Get bypass session cache info."""
    return {
        "cached_domains": list(_session_cache.keys()),
        "playwright_available": HAS_PLAYWRIGHT,
    }
