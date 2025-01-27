from django.core.management.base import BaseCommand
from dashboard.models import AppStore

class Command(BaseCommand):
    help = '清空应用商店数据'

    def handle(self, *args, **kwargs):
        count = AppStore.objects.all().delete()[0]
        self.stdout.write(f'已删除 {count} 个应用') 