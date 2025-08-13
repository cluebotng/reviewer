web: gunicorn --bind=0.0.0.0:8000 --workers=4 --forwarded-allow-ips=* --timeout=3600 cbng_reviewer.wsgi:application
run-celery: celery -A cbng_reviewer worker -l INFO
run-flower: celery -A cbng_reviewer flower