# Default backend is httpcloak. On some Windows setups it fails with a
# permission error during session init. If you hit that, switch to
# curl_cffi by changing the line below.

USE_CURL_CFFI = False  # set True if httpcloak throws a permission error


def build_session():
    if USE_CURL_CFFI:
        from curl_cffi import requests
        return requests.Session(impersonate="chrome124", timeout=30)

    try:
        import httpcloak
        return httpcloak.Session(preset="chrome-latest", timeout=30)
    except (ImportError, Exception):
        try:
            from curl_cffi import requests as cffi_requests
            return cffi_requests.Session(impersonate="chrome124", timeout=30)
        except (ImportError, Exception):
            import requests
            s = requests.Session()
            s.headers.update({
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            })
            return s