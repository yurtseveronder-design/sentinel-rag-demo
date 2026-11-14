import json
import urllib.error
import urllib.request


class GuardUnavailable(RuntimeError):
    pass


class Guard:
    """Asks ai-sentinel /v1/scan whether a piece of text is safe. Fails closed."""

    def __init__(self, base_url, api_key, timeout=10):
        self.url, self.key, self.timeout = base_url.rstrip("/") + "/v1/scan", api_key, timeout

    def is_blocked(self, text):
        request = urllib.request.Request(
            self.url, data=json.dumps({"prompt": text}).encode(), method="POST",
            headers={"Content-Type": "application/json", "X-API-Key": self.key})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read()).get("action") == "BLOCK"
        except (OSError, ValueError) as exc:
            raise GuardUnavailable(str(exc)) from exc
