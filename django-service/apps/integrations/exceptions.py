class IntegrationError(Exception):
    """
    Raised when a downstream service (FastAPI/Flask) call fails - network
    error, timeout, or a non-2xx response. Deliberately a single generic
    exception type rather than one per service/failure mode: every caller
    in the views needs to handle this the same way (show the user a clear
    "try again" message, don't crash), so there's no value in forcing
    callers to distinguish "FastAPI timed out" from "Flask returned 500"
    at the view layer.
    """

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code
