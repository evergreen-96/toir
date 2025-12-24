import threading

_local = threading.local()


def get_request_context():
    return getattr(_local, "context", None)


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        source = "admin" if request.path.startswith("/admin/") else "ui"

        _local.context = {
            "source": source,
            "path": request.path,
            "method": request.method,
        }

        try:
            return self.get_response(request)
        finally:
            _local.context = None
