from django.apps import AppConfig


class BulkImportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bulk_import"
    label = "bulk_import"
