from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('system/', views.SystemView.as_view(), name='system'),
    path('system/stats/', views.SystemView.as_view(), {'action': 'get_system_stats'}, name='system_stats'),
    path('websites/', views.WebsitesView.as_view(), name='websites'),
    path('websites/add/', views.WebsitesView.as_view(), {'action': 'add'}, name='websites_add'),
    path('websites/edit/<int:website_id>/', views.WebsitesView.as_view(), {'action': 'edit'}, name='websites_edit'),
    path('websites/delete/<int:website_id>/', views.WebsitesView.as_view(), {'action': 'delete'}, name='websites_delete'),
    path('websites/toggle/<int:website_id>/', views.WebsitesView.as_view(), {'action': 'toggle'}, name='websites_toggle'),
    path('database/', views.DatabaseView.as_view(), name='database'),
    path('database/add/', views.DatabaseView.as_view(), {'action': 'add'}, name='database_add'),
    path('database/edit/<int:database_id>/', views.DatabaseView.as_view(), {'action': 'edit'}, name='database_edit'),
    path('database/delete/<int:database_id>/', views.DatabaseView.as_view(), {'action': 'delete'}, name='database_delete'),
    path('files/', views.FilesView.as_view(), name='files'),
    path('security/', views.SecurityView.as_view(), name='security'),
    path('security/add/', views.SecurityView.as_view(), {'action': 'add'}, name='security_add'),
    path('security/edit/<int:rule_id>/', views.SecurityView.as_view(), {'action': 'edit'}, name='security_edit'),
    path('security/delete/<int:rule_id>/', views.SecurityView.as_view(), {'action': 'delete'}, name='security_delete'),
    path('security/toggle/<int:rule_id>/', views.SecurityView.as_view(), {'action': 'toggle'}, name='security_toggle'),
    path('cron/', views.CronView.as_view(), name='cron'),
    path('cron/add/', views.CronView.as_view(), {'action': 'add'}, name='cron_add'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
]