from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
import os
import subprocess
import re

class Website(models.Model):
    SERVER_TYPES = (
        ('nginx', 'Nginx'),
        ('apache', 'Apache'),
    )
    
    def get_php_versions():
        """获取系统中已安装的PHP版本"""
        php_versions = [('none', '不使用')]
        try:
            # 运行命令获取PHP版本
            result = subprocess.run(['php', '-v'], capture_output=True, text=True)
            if result.returncode == 0:
                # 使用正则表达式提取版本号
                version_match = re.search(r'PHP (\d+\.\d+\.\d+)', result.stdout)
                if version_match:
                    version = version_match.group(1)
                    major_minor = '.'.join(version.split('.')[:2])  # 只取主版本号和次版本号
                    php_versions.append((major_minor, f'PHP {major_minor}'))
        except Exception:
            pass
        
        # 如果没有找到任何PHP版本，返回默认选项
        if len(php_versions) == 1:
            php_versions.extend([
                ('7.4', 'PHP 7.4'),
                ('8.0', 'PHP 8.0'),
                ('8.1', 'PHP 8.1'),
                ('8.2', 'PHP 8.2'),
            ])
        return php_versions

    name = models.CharField(_('网站名称'), max_length=100)
    domain = models.CharField(
        _('主域名'),
        max_length=255,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9][a-zA-Z0-9-_.]+[a-zA-Z0-9]$',
                message='域名格式不正确'
            )
        ]
    )
    server_type = models.CharField(
        _('服务器类型'),
        max_length=10,
        choices=SERVER_TYPES,
        default='nginx'
    )
    php_version = models.CharField(
        _('PHP版本'),
        max_length=10,
        choices=get_php_versions(),
        default='none'
    )
    status = models.BooleanField(_('运行状态'), default=False)
    ssl_enabled = models.BooleanField(_('SSL状态'), default=False)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    port = models.IntegerField(default=80)

    @property
    def path(self):
        """根据域名自动生成网站目录路径"""
        return os.path.join('/www/wwwroot/', self.domain)

    @property
    def database_name(self):
        """获取数据库名称"""
        return self.domain.replace('.', '_')

    class Meta:
        verbose_name = _('网站')
        verbose_name_plural = _('网站')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class AdditionalDomain(models.Model):
    website = models.ForeignKey(
        Website,
        on_delete=models.CASCADE,
        related_name='additional_domains',
        verbose_name=_('网站')
    )
    domain = models.CharField(
        _('域名'),
        max_length=255,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9][a-zA-Z0-9-_.]+[a-zA-Z0-9]$',
                message='域名格式不正确'
            )
        ]
    )
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)

    class Meta:
        verbose_name = _('附加域名')
        verbose_name_plural = _('附加域名')
        ordering = ['-created_at']

    def __str__(self):
        return self.domain
