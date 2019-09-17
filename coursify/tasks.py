from celery import shared_task
from django.core.files.storage import default_storage

from .dash import DashVideoManager


@shared_task
def generate_dash_manifest(file_name):
    dash = DashVideoManager(file_name, default_storage)
    dash.generate()
