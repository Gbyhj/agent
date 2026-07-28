# Production Deployment
# Gunicorn + Nginx + HTTPS

# 启动:
#   gunicorn -c gunicorn_config.py agent.server:app

bind = "127.0.0.1:5000"
workers = 4
worker_class = "sync"
timeout = 120
max_requests = 1000
max_requests_jitter = 100
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = "info"
