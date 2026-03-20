"""
Canary Analysis Demo App
App con métricas Prometheus para validación automática via AnalysisTemplate.
Soporta inyección de fallos para simular escenarios de rollback.
"""
import os
import time
import random
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

APP_VERSION = os.getenv("APP_VERSION", "v1.0.0")
FAILURE_RATE = float(os.getenv("FAILURE_RATE", "0.0"))
LATENCY_MS = int(os.getenv("LATENCY_MS", "0"))

# Métricas Prometheus
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status", "version"]
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "version"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

def should_fail():
    return random.random() < FAILURE_RATE

def add_latency():
    if LATENCY_MS > 0:
        time.sleep(LATENCY_MS / 1000.0)

@app.route("/")
def index():
    start = time.time()
    add_latency()
    if should_fail():
        REQUEST_COUNT.labels("GET", "/", "500", APP_VERSION).inc()
        REQUEST_DURATION.labels("GET", "/", APP_VERSION).observe(time.time() - start)
        return jsonify({"error": "simulated failure", "version": APP_VERSION}), 500
    REQUEST_COUNT.labels("GET", "/", "200", APP_VERSION).inc()
    REQUEST_DURATION.labels("GET", "/", APP_VERSION).observe(time.time() - start)
    return jsonify({
        "app": "canary-analysis",
        "version": APP_VERSION,
        "status": "ok"
    })

@app.route("/api/data")
def api_data():
    start = time.time()
    add_latency()
    if should_fail():
        REQUEST_COUNT.labels("GET", "/api/data", "500", APP_VERSION).inc()
        REQUEST_DURATION.labels("GET", "/api/data", APP_VERSION).observe(time.time() - start)
        return jsonify({"error": "simulated failure"}), 500
    REQUEST_COUNT.labels("GET", "/api/data", "200", APP_VERSION).inc()
    REQUEST_DURATION.labels("GET", "/api/data", APP_VERSION).observe(time.time() - start)
    return jsonify({"data": [1, 2, 3], "version": APP_VERSION})

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "version": APP_VERSION})

@app.route("/ready")
def ready():
    return jsonify({"status": "ready", "version": APP_VERSION})

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

@app.route("/config")
def config():
    """Endpoint para ver/cambiar failure rate y latency en runtime."""
    if request.method == "GET":
        return jsonify({
            "version": APP_VERSION,
            "failure_rate": FAILURE_RATE,
            "latency_ms": LATENCY_MS
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
