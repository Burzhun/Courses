import os

from django.contrib.admin import AdminSite as ContribAdminSite
from django.conf import settings
from django.conf.urls.static import serve
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path, re_path
from django.template.response import TemplateResponse


site_name = settings.SITE_NAME or 'Django'


class AdminSite(ContribAdminSite):
    site_header = '{} администрирование'.format(site_name)

    def get_urls(self):
        urlpatterns = super().get_urls()
        urlpatterns += [
            path('docs/', self.admin_view(self.docs), name='docs'),
            re_path(r'^docs/(?P<path>.*)$', view=staff_member_required(serve), kwargs={
                'document_root': os.path.join(settings.BASE_DIR, 'docs/_build/html')
            })
        ]
        return urlpatterns

    def docs(self, request):
        """Рендерит страницу с документацией"""
        context = dict(
            # Include common variables for rendering the admin template.
            self.each_context(request),
        )
        return TemplateResponse(request, 'admin/docs.html', context)
