"""
Demo application for Canary deployment strategy with Argo Rollouts.
Provides health checks, metrics, and configurable failure injection.
"""
import os
import time
import random
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app

app = Flask(__name__)

# Configuration from environment variables
VERSION = os.getenv('APP_VERSION', 'v1.0.0')
FAILURE_RATE = float(os.getenv('FAILURE_RATE', '0.0'))  # 0.0 to 1.0
LATENCY_MS = int(os.getenv('LATENCY_MS', '0'))  # Additional latency in ms
PORT = int(os.getenv('PORT', '8080'))

# Prometheus metrics
request_counter = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)
error_counter = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['endpoint', 'error_type']
)
active_requests = Gauge(
    'http_active_requests',
    'Number of active HTTP requests'
)
app_info = Gauge(
    'app_info',
    'Application information',
    ['version']
)

# Set app version metric
app_info.labels(version=VERSION).set(1)

# Application state
app_state = {
    'healthy': True,
    'ready': True,
    'start_time': time.time(),
    'request_count': 0
}


def inject_failure():
    """Simulate failures based on configured failure rate."""
    if random.random() < FAILURE_RATE:
        return True
    return False


def inject_latency():
    """Inject configured latency."""
    if LATENCY_MS > 0:
        time.sleep(LATENCY_MS / 1000.0)


@app.before_request
def before_request():
    """Track active requests."""
    active_requests.inc()
    request.start_time = time.time()


@app.after_request
def after_request(response):
    """Record metrics after each request."""
    active_requests.dec()
    
    # Record request duration
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        request_duration.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown'
        ).observe(duration)
    
    # Record request count
    request_counter.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown',
        status=response.status_code
    ).inc()
    
    app_state['request_count'] += 1
    
    return response


@app.route('/')
def index():
    """Root endpoint with version information."""
    inject_latency()
    
    if inject_failure():
        error_counter.labels(endpoint='index', error_type='injected').inc()
        return jsonify({
            'error': 'Simulated failure',
            'version': VERSION
        }), 500
    
    return jsonify({
        'message': 'Canary Demo Application',
        'version': VERSION,
        'status': 'healthy',
        'uptime_seconds': int(time.time() - app_state['start_time']),
        'total_requests': app_state['request_count']
    })


@app.route('/health')
def health():
    """Health check endpoint for liveness probe."""
    if not app_state['healthy']:
        return jsonify({
            'status': 'unhealthy',
            'version': VERSION
        }), 503
    
    return jsonify({
        'status': 'healthy',
        'version': VERSION
    })


@app.route('/ready')
def ready():
    """Readiness check endpoint."""
    if not app_state['ready']:
        return jsonify({
            'status': 'not ready',
            'version': VERSION
        }), 503
    
    return jsonify({
        'status': 'ready',
        'version': VERSION
    })


@app.route('/api/data')
def api_data():
    """Sample API endpoint with business logic."""
    inject_latency()
    
    if inject_failure():
        error_counter.labels(endpoint='api_data', error_type='injected').inc()
        return jsonify({
            'error': 'Failed to fetch data',
            'version': VERSION
        }), 500
    
    return jsonify({
        'data': [
            {'id': 1, 'name': 'Item 1', 'value': 100},
            {'id': 2, 'name': 'Item 2', 'value': 200},
            {'id': 3, 'name': 'Item 3', 'value': 300}
        ],
        'version': VERSION,
        'timestamp': int(time.time())
    })


@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/config')
def config():
    """Show current configuration."""
    return jsonify({
        'version': VERSION,
        'failure_rate': FAILURE_RATE,
        'latency_ms': LATENCY_MS,
        'port': PORT
    })


@app.route('/admin/health', methods=['POST'])
def set_health():
    """Admin endpoint to control health status."""
    data = request.get_json() or {}
    app_state['healthy'] = data.get('healthy', True)
    return jsonify({
        'healthy': app_state['healthy']
    })


@app.route('/admin/ready', methods=['POST'])
def set_ready():
    """Admin endpoint to control readiness status."""
    data = request.get_json() or {}
    app_state['ready'] = data.get('ready', True)
    return jsonify({
        'ready': app_state['ready']
    })


if __name__ == '__main__':
    print(f"Starting Canary Demo App {VERSION}")
    print(f"Failure Rate: {FAILURE_RATE}")
    print(f"Latency: {LATENCY_MS}ms")
    app.run(host='0.0.0.0', port=PORT)
