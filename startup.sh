#!/bin/bash
# Azure App Service startup script
# Azure sets the PORT environment variable (usually 8080)
gunicorn run:app --bind=0.0.0.0:${PORT:-8000} --timeout 600 --workers 1 --threads 2 --preload
