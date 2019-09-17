from django.contrib.admin.apps import AdminConfig as ContribAdminConfig


class AdminConfig(ContribAdminConfig):
    default_site = 'admin.sites.AdminSite'
