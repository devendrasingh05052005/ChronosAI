#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing CPU-only PyTorch to optimize build size and build time..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

echo "Installing remaining project requirements..."
pip install -r requirements.txt

echo "Collecting static assets..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

echo "Seeding the database..."
python scratch/seed_4_timetables.py

echo "Build completed successfully!"
