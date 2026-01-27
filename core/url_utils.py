"""
URL utilities for Amazon links
"""
from urllib.parse import urlparse, urlunparse
import re

ASIN_REGEXES = [
    re.compile(r"/dp/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/gp/product/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/gp/aw/d/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/product/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/[^/]+/dp/([A-Z0-9]{10})", re.IGNORECASE),
]


def canonicalize_amazon_url(url: str) -> str:
    """
    Convert various Amazon product URL formats into a canonical form:
    https://<host>/dp/<ASIN>

    If ASIN cannot be extracted, returns the original URL with query/fragment removed.
    """
    try:
        parsed = urlparse(url)
        path = parsed.path or ""
        asin = None
        for rx in ASIN_REGEXES:
            m = rx.search(path)
            if m:
                asin = m.group(1).upper()
                break
        # If no ASIN, return original without query/fragment
        if not asin:
            return urlunparse((parsed.scheme or 'https', parsed.netloc, parsed.path, '', '', ''))
        # Build canonical path and URL
        canonical_path = f"/dp/{asin}"
        host = parsed.netloc or "www.amazon.com"
        scheme = parsed.scheme or "https"
        return urlunparse((scheme, host, canonical_path, '', '', ''))
    except Exception:
        # On any error, fall back to the original URL
        return url
