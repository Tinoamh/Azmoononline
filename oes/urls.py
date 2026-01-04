"""
URL configuration for oes project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Use DashboardView for home page to inject dynamic context if needed, or update TemplateView logic
    # For now, let's keep it simple but point to a custom view if we want to pass context.
    # Actually, we can use a simple function view or class view in accounts/views.py for the home page.
    # But since it was TemplateView, we can switch it to our enhanced view if we move it to views.py or just use it here.
    # Let's import a home_view from accounts.views
    path('', include('accounts.home_urls')), # Delegating home to an app url or view
    path('accounts/', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
