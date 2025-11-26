# Gunicorn configuration for Render deployment
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = 1  # Single worker for Render's limited resources
worker_class = "sync"
worker_connections = 1000
timeout = 300  # 5 minutes for AI processing
keepalive = 2
max_requests = 100
max_requests_jitter = 10

# Restart workers after this many requests, with up to this much jitter
# added to prevent all workers from restarting at the same time
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "hair_transformer"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (not needed for Render)
keyfile = None
certfile = None

# Memory management
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
