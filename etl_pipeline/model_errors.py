"""Provider-independent failures safe to report without upstream bodies or secrets."""


class ModelUnavailable(RuntimeError):
    pass


class ModelTimeout(RuntimeError):
    pass


class ModelInvalidResponse(RuntimeError):
    pass


class ModelInputError(ValueError):
    pass


class ModelRateLimited(RuntimeError):
    def __init__(self, provider: str, retry_after: int = 60):
        self.retry_after = max(1, min(300, retry_after))
        super().__init__(f"{provider} quota reached; retry in {self.retry_after}s")


def retry_after_seconds(value: str) -> int:
    try:
        return max(1, min(300, int(value)))
    except ValueError:
        return 60
