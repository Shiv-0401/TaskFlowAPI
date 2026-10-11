#!/bin/sh
set -e

flask db upgrade

exec gunicorn --bind 0.0.0.0:5000 --workers 3 run:app
