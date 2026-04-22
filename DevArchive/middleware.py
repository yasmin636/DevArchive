"""
Middleware de développement : tunnel ngrok et CSRF.

En DEBUG uniquement, ajoute dynamiquement l’origine HTTPS du tunnel ngrok à
CSRF_TRUSTED_ORIGINS pour éviter les 403 sur les formulaires (connexion, etc.).
"""
from django.conf import settings

_NGROK_SUFFIXES = (".ngrok-free.dev", ".ngrok-free.app", ".ngrok.io")


class AppendNgrokCsrfTrustedOriginMiddleware:
    """Ajoute https://<host> aux origines CSRF lorsque l’hôte est un domaine ngrok."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            host = request.get_host().split(":")[0]
            if any(host.endswith(suffix) for suffix in _NGROK_SUFFIXES):
                origin = f"https://{host}"
                trusted = list(settings.CSRF_TRUSTED_ORIGINS)
                if origin not in trusted:
                    trusted.append(origin)
                    settings.CSRF_TRUSTED_ORIGINS = trusted
        return self.get_response(request)
