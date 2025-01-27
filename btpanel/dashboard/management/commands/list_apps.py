from django.core.management.base import BaseCommand
from dashboard.models import AppStore
import json

class Command(BaseCommand):
    help = '列出所有应用'

    def handle(self, *args, **kwargs):
        apps = AppStore.objects.all()
        self.stdout.write(f'总共有 {apps.count()} 个应用:')
        for app in apps:
            self.stdout.write('=' * 50)
            self.stdout.write(f'ID: {app.id}')
            self.stdout.write(f'名称: {app.name}')
            self.stdout.write(f'类型: {app.get_app_type_display()}')
            self.stdout.write(f'版本: {app.versions}')
            self.stdout.write(f'默认版本: {app.default_version}')
            self.stdout.write(f'当前版本: {app.current_version}')
            self.stdout.write(f'状态: {app.status}') 