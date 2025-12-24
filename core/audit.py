from core.middleware import get_request_context


def build_change_reason(extra: str | None = None):
    ctx = get_request_context()

    if not ctx:
        base = "system"
    else:
        base = f"{ctx['source']}:{ctx['path']}"

    if extra:
        return f"{base} — {extra}"

    return base