from django.contrib.auth.models import AbstractUser
from django.db import models
import os
import datetime
import subprocess
import tempfile
from django.utils import timezone
import paramiko
from django.http import JsonResponse
import secrets
import string
import shutil

# Create your models here.

class AdminUser(AbstractUser):
    phone = models.CharField(max_length=11, null=True, blank=True, verbose_name='手机号')
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='最后登录IP')
    last_login_time = models.DateTimeField(null=True, blank=True, verbose_name='最后登录时间')
    
    class Meta:
        verbose_name = '管理员'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username

class Website(models.Model):
    STATUS_CHOICES = (
        ('running', '运行中'),
        ('stopped', '已停止'),
    )
    
    # 定义基础路径
    BASE_WWW_PATH = '/wwwroot/sites'
    BASE_LOGS_PATH = '/wwwroot/wwwlogs'
    BASE_SSL_PATH = '/wwwroot/ssl'
    NGINX_SITES_AVAILABLE = '/etc/nginx/sites-available'
    NGINX_SITES_ENABLED = '/etc/nginx/sites-enabled'
    
    name = models.CharField('网站名称', max_length=100)
    domain = models.CharField('域名', max_length=100)
    path = models.CharField('网站目录', max_length=200)
    port = models.IntegerField('端口', default=80)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='stopped')
    server_type = models.CharField('服务器类型', max_length=20, default='nginx')
    php_version = models.CharField('PHP版本', max_length=20, null=True, blank=True)
    ssl_enabled = models.BooleanField('启用SSL', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '网站'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_config_path(self):
        """获取配置文件路径"""
        if self.server_type == 'nginx':
            return os.path.join(self.NGINX_SITES_AVAILABLE, f"{self.domain}.conf")
        return ""

    def get_web_path(self):
        """获取网站目录"""
        return os.path.join(self.BASE_WWW_PATH, self.domain)

    def get_log_path(self):
        """获取日志目录"""
        return os.path.join(self.BASE_LOGS_PATH, self.domain)

    def get_ssl_path(self):
        """获取SSL证书目录"""
        return os.path.join(self.BASE_SSL_PATH, self.domain)

    def generate_nginx_config(self):
        """生成Nginx配置"""
        config = f"""server {{
    listen {self.port};
    server_name {self.domain};
    root {self.path};
    index index.html index.htm index.php;

    access_log {self.get_log_path()}/access.log;
    error_log {self.get_log_path()}/error.log;

    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}
"""
        if self.php_version:
            config += f"""
    location ~ \.php$ {{
        fastcgi_pass unix:/run/php/php{self.php_version}-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }}
"""
        config += "}\n"
        return config

class Database(models.Model):
    DB_TYPE_CHOICES = (
        ('mysql', 'MySQL'),
        ('postgresql', 'PostgreSQL'),
    )
    
    name = models.CharField('数据库名', max_length=100)
    db_type = models.CharField('数据库类型', max_length=20, choices=DB_TYPE_CHOICES, default='mysql')
    username = models.CharField('用户名', max_length=100)
    password = models.CharField('密码', max_length=100)
    charset = models.CharField('字符集', max_length=20, default='utf8mb4')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '数据库'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class FileManager:
    BASE_PATH = '/wwwroot/sites'  # 基础目录路径
    
    @staticmethod
    def list_directory(path=None):
        """列出目录内容"""
        if path is None:
            path = FileManager.BASE_PATH
        
        items = []
        for item in os.scandir(path):
            stats = item.stat()
            items.append({
                'name': item.name,
                'path': item.path,
                'is_dir': item.is_dir(),
                'size': FileManager.format_size(stats.st_size),
                'modified': datetime.datetime.fromtimestamp(stats.st_mtime),
                'mode': oct(stats.st_mode)[-4:],  # 权限模式
            })
        return sorted(items, key=lambda x: (not x['is_dir'], x['name']))
    
    @staticmethod
    def format_size(size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

class SecurityRule(models.Model):
    RULE_TYPES = (
        ('ip', 'IP封禁'),
        ('port', '端口限制'),
        ('url', 'URL拦截'),
    )
    
    name = models.CharField('规则名称', max_length=100)
    rule_type = models.CharField('规则类型', max_length=10, choices=RULE_TYPES)
    value = models.CharField('规则值', max_length=200)
    description = models.TextField('描述', blank=True, null=True)
    is_enabled = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '安全规则'
        verbose_name_plural = '安全规则'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class CronJob(models.Model):
    INTERVAL_CHOICES = (
        ('minute', '每分钟'),
        ('hour', '每小时'),
        ('day', '每天'),
        ('week', '每周'),
        ('month', '每月'),
        ('custom', '自定义'),
    )
    
    name = models.CharField('任务名称', max_length=100)
    command = models.TextField('执行命令')
    interval = models.CharField('执行间隔', max_length=20, choices=INTERVAL_CHOICES)
    cron_expression = models.CharField('Cron表达式', max_length=100, blank=True)
    description = models.TextField('描述', blank=True)
    is_enabled = models.BooleanField('是否启用', default=True)
    last_run = models.DateTimeField('上次执行', null=True, blank=True)
    next_run = models.DateTimeField('下次执行', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '计划任务'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_cron_expression(self):
        """根据间隔获取cron表达式"""
        if self.interval == 'custom':
            return self.cron_expression
        elif self.interval == 'minute':
            return '* * * * *'
        elif self.interval == 'hour':
            return '0 * * * *'
        elif self.interval == 'day':
            return '0 0 * * *'
        elif self.interval == 'week':
            return '0 0 * * 0'
        elif self.interval == 'month':
            return '0 0 1 * *'
        return ''

    def update_crontab(self):
        """更新系统crontab"""
        try:
            print(f"更新任务 {self.name} 的crontab配置")
            
            # 获取当前的crontab内容
            try:
                current_crontab = subprocess.check_output(['crontab', '-l']).decode()
                print("当前crontab内容:", current_crontab)
            except subprocess.CalledProcessError:
                current_crontab = ''
                print("当前crontab为空")
            
            # 准备新的crontab内容
            new_crontab = [line for line in current_crontab.splitlines() if line.strip()]
            
            # 移除旧的任务（如果存在）
            new_crontab = [line for line in new_crontab if self.command not in line]
            
            # 如果任务启用，添加新任务
            if self.is_enabled:
                expression = self.get_cron_expression()
                if expression:
                    new_job = f'{expression} {self.command}'
                    print("添加新任务:", new_job)
                    new_crontab.append(new_job)
            
            # 写入新的crontab
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
                content = '\n'.join(new_crontab)
                if content and not content.endswith('\n'):
                    content += '\n'
                temp.write(content)
                print("新crontab内容:", content)
            
            try:
                subprocess.run(['crontab', temp.name], check=True)
                print("crontab更新成功")
            except subprocess.CalledProcessError as e:
                print("crontab更新失败:", str(e))
                raise
            finally:
                os.unlink(temp.name)
            
        except Exception as e:
            print("更新crontab时出错:", str(e))
            raise

def get_os_type(request):
    """获取操作系统类型的API"""
    try:
        # 假设目标服务器的信息已经存储在session中
        target_server = request.session.get('target_server')
        
        # 通过SSH连接到目标服务器
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(target_server['host'], 
                   username=target_server['username'],
                   password=target_server['password'])
        
        # 执行命令检测操作系统
        stdin, stdout, stderr = ssh.exec_command('cat /etc/os-release')
        os_info = stdout.read().decode().lower()
        
        if 'ubuntu' in os_info:
            os_type = 'ubuntu'
        elif 'centos' in os_info:
            os_type = 'centos'
        else:
            os_type = 'unknown'
            
        ssh.close()
        return JsonResponse({'os_type': os_type})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
