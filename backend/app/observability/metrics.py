from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter

# HTTP instrumentation
def init_metrics(app) -> None:
    if getattr(app.state, "metrics_initialized", False):
        return
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    app.state.metrics_initialized = True

# Custom Groq metrics
_groq_requests = Counter("groq_requests_total", "Total Groq requests", ["model", "agent"])
_groq_tokens   = Counter("groq_tokens_total", "Groq tokens used", ["type", "model", "agent"])
_groq_errors   = Counter("groq_errors_total", "Groq errors", ["model", "agent"])

def record_groq_usage(model: str, agent: str, prompt_tokens: int, completion_tokens: int) -> None:
    _groq_requests.labels(model=model, agent=agent).inc()
    if prompt_tokens:
        _groq_tokens.labels(type="prompt", model=model, agent=agent).inc(prompt_tokens)
    if completion_tokens:
        _groq_tokens.labels(type="completion", model=model, agent=agent).inc(completion_tokens)

def record_groq_error(model: str, agent: str) -> None:
    _groq_errors.labels(model=model, agent=agent).inc()

_webhook_requests = Counter("webhook_requests_total", "Webhook requests", ["service"])
_webhook_errors   = Counter("webhook_errors_total", "Webhook errors",   ["service"])

def record_webhook_request(service: str) -> None:
    _webhook_requests.labels(service=service).inc()

def record_webhook_error(service: str) -> None:
    _webhook_errors.labels(service=service).inc()