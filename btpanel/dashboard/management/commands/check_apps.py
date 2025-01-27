from django.core.management.base import BaseCommand
from dashboard.models import AppStore

class Command(BaseCommand):
    help = '检查应用商店数据'

    def handle(self, *args, **kwargs):
        apps = AppStore.objects.all()
        self.stdout.write(f'总共有 {apps.count()} 个应用:')
        for app in apps:
            self.stdout.write(f'ID: {app.id}, 名称: {app.name}, 类型: {app.app_type}')
            self.stdout.write(f'  版本: {app.versions}')
            self.stdout.write(f'  状态: {app.status}')
            self.stdout.write('---') 