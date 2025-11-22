# Gunicorn Configuration File for Secret Santa Application
# This file configures Gunicorn for production deployment with high user loads
#
# Usage: gunicorn -c gunicorn_config.py app:app

import multiprocessing
import os

# =============================================================================
# SERVER SOCKET
# =============================================================================

# The socket to bind
bind = os.environ.get('BIND_ADDRESS', '0.0.0.0:8000')

# Backlog - The maximum number of pending connections
# This should be tuned based on expected load
backlog = 2048


# =============================================================================
# WORKER PROCESSES
# =============================================================================

# Number of worker processes for handling requests
# Formula: (2 × CPU cores) + 1
# Can be overridden with GUNICORN_WORKERS environment variable
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# The type of workers to use
# Use 'eventlet' for async support and WebSocket (SocketIO) compatibility
worker_class = 'eventlet'

# The maximum number of simultaneous clients per worker
# Each worker can handle this many concurrent connections
worker_connections = int(os.environ.get('WORKER_CONNECTIONS', 1000))

# Maximum number of requests a worker will process before restarting
# This helps prevent memory leaks
max_requests = int(os.environ.get('MAX_REQUESTS', 1000))

# Randomize max_requests to avoid all workers restarting at the same time
max_requests_jitter = int(os.environ.get('MAX_REQUESTS_JITTER', 50))


# =============================================================================
# TIMEOUT SETTINGS
# =============================================================================

# Workers silent for more than this many seconds are killed and restarted
# Increase this if you have long-running requests (e.g., file uploads)
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))

# The number of seconds to wait for requests on a Keep-Alive connection
keepalive = int(os.environ.get('KEEPALIVE', 5))

# Timeout for graceful workers restart
# After receiving a restart signal, workers have this much time to finish
# serving requests. After the timeout, they are force killed.
graceful_timeout = int(os.environ.get('GRACEFUL_TIMEOUT', 30))


# =============================================================================
# LOGGING
# =============================================================================

# The access log file to write to
# '-' means log to stdout
accesslog = os.environ.get('ACCESS_LOG', '-')

# The error log file to write to
# '-' means log to stderr
errorlog = os.environ.get('ERROR_LOG', '-')

# The granularity of Error log outputs
# Valid log levels: debug, info, warning, error, critical
loglevel = os.environ.get('LOG_LEVEL', 'info')

# Access log format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'


# =============================================================================
# PROCESS NAMING
# =============================================================================

# A base to use with setproctitle for process naming
proc_name = 'secret-santa'


# =============================================================================
# SERVER MECHANICS
# =============================================================================

# Daemonize the Gunicorn process
# Set to True if you want it to run in background (not recommended for containers)
daemon = False

# A filename to use for the PID file
pidfile = None

# Switch worker processes to run as this user
user = None

# Switch worker process to run as this group
group = None

# A bit mask for the file mode on files written by Gunicorn
umask = 0

# A directory to use for the worker heartbeat temporary file
tmp_upload_dir = None


# =============================================================================
# APPLICATION LOADING
# =============================================================================

# Load application code before the worker processes are forked
# This can save RAM and improve startup time, but may cause issues
# with some applications. Test thoroughly before enabling in production.
preload_app = True

# Restart workers when code changes (development only)
reload = os.environ.get('RELOAD', 'False').lower() in ('true', '1', 'yes')


# =============================================================================
# SSL/HTTPS (if terminating SSL at application level)
# Usually SSL is terminated at load balancer/reverse proxy level
# =============================================================================

# SSL key file
keyfile = os.environ.get('SSL_KEYFILE', None)

# SSL certificate file
certfile = os.environ.get('SSL_CERTFILE', None)


# =============================================================================
# SECURITY
# =============================================================================

# Limit the allowed size of an HTTP request header field
# This helps prevent DDOS attacks
limit_request_field_size = 8190

# Limit the number of HTTP headers fields in a request
limit_request_fields = 100

# Limit the allowed size of the HTTP request line
limit_request_line = 4094


# =============================================================================
# HOOKS
# =============================================================================

def on_starting(server):
    """
    Called just before the master process is initialized.
    """
    server.log.info("Starting Secret Santa application")


def on_reload(server):
    """
    Called to recycle workers during a reload via SIGHUP.
    """
    server.log.info("Reloading Secret Santa application")


def when_ready(server):
    """
    Called just after the server is started.
    """
    server.log.info("Secret Santa server is ready. Spawning workers")


def worker_int(worker):
    """
    Called just after a worker exited on SIGINT or SIGQUIT.
    """
    worker.log.info("Worker received INT or QUIT signal")


def worker_abort(worker):
    """
    Called when a worker receives the SIGABRT signal.
    This call generally happens on timeout.
    """
    worker.log.info("Worker received SIGABRT signal")


# =============================================================================
# DEPLOYMENT NOTES
# =============================================================================

# Azure App Service:
# - Set startup command in portal: gunicorn -c gunicorn_config.py app:app
# - Set environment variables in Application Settings
# - Enable Web Sockets in General Settings
#
# Docker:
# - CMD ["gunicorn", "-c", "gunicorn_config.py", "app:app"]
#
# Recommended Environment Variables:
# - GUNICORN_WORKERS=4 (adjust based on your instance size)
# - WORKER_CONNECTIONS=1000
# - GUNICORN_TIMEOUT=120
# - LOG_LEVEL=info (use debug for troubleshooting)
#
# Monitoring:
# - Monitor worker count with: ps aux | grep gunicorn
# - Check worker restarts in logs
# - Monitor memory usage per worker
# - Set up alerts for worker failures
#
# Performance Tuning:
# - Increase workers if CPU usage is low but response time is high
# - Increase worker_connections if you have many concurrent WebSocket connections
# - Increase timeout if you have long-running requests
# - Use max_requests to prevent memory leaks (restart workers periodically)
