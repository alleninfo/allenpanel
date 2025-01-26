import os
import datetime

class FileManager:
    # 修改基础目录路径为根目录
    BASE_PATH = '/'  # 系统根目录
    
    @staticmethod
    def list_directory(path=None, page=1, per_page=50):
        """分页列出目录内容"""
        if path is None:
            path = FileManager.BASE_PATH
        
        try:
            # 使用生成器获取目录内容
            items = []
            start = (page - 1) * per_page
            end = start + per_page
            count = 0
            
            for entry in os.scandir(path):
                if count >= end:
                    break
                    
                if count >= start:
                    try:
                        stats = entry.stat()
                        items.append({
                            'name': entry.name,
                            'path': entry.path,
                            'is_dir': entry.is_dir(),
                            'size': FileManager.format_size(stats.st_size),
                            'modified': datetime.datetime.fromtimestamp(stats.st_mtime),
                            'mode': oct(stats.st_mode)[-4:],  # 权限模式
                            'owner': FileManager.get_owner_info(stats.st_uid, stats.st_gid)
                        })
                    except (OSError, PermissionError):
                        continue  # 跳过无法访问的文件
                count += 1
            
            return items
        except Exception as e:
            raise ValueError(f'无法访问目录：{str(e)}')
    
    @staticmethod
    def format_size(size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    @staticmethod
    def get_owner_info(uid, gid):
        """获取文件所有者信息"""
        try:
            import pwd, grp
            user = pwd.getpwuid(uid).pw_name
            group = grp.getgrgid(gid).gr_name
            return f"{user}:{group}"
        except:
            return f"{uid}:{gid}"

    @staticmethod
    def is_safe_path(path):
        """检查路径是否安全"""
        try:
            # 规范化路径
            real_path = os.path.abspath(path)
            # 检查路径是否包含特殊字符
            if any(c in real_path for c in ['..', '~', '$', '`', '|', '&', ';', ' ']):
                return False
            # 检查路径是否存在
            return os.path.exists(os.path.dirname(real_path))
        except:
            return False