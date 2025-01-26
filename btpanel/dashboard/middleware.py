import gc
import psutil
from django.conf import settings

class MemoryManagementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.memory_threshold = getattr(settings, 'MEMORY_THRESHOLD', 80)  # 内存阈值
        
    def __call__(self, request):
        # 检查内存使用
        memory = psutil.virtual_memory()
        if memory.percent > self.memory_threshold:
            # 强制进行垃圾回收
            gc.collect()
            
        response = self.get_response(request)
        return response 