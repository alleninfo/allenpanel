from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
import psutil
import datetime
from django.http import JsonResponse
import time
import platform
import json
from .models import AdminUser, Website, Database, SecurityRule, CronJob
import os
import subprocess
from django.contrib import messages
import mysql.connector
import secrets
import string
import shutil
from pathlib import Path
from django.http import HttpResponse
from django.urls import reverse
from croniter import croniter
from .utils import FileManager

class IndexView(LoginRequiredMixin, View):
    login_url = '/login/'
    
    def get(self, request):
        # 获取系统信息
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time

        # 转换内存和磁盘大小为GB
        memory_total_gb = round(memory.total / (1024 ** 3), 1)
        disk_total_gb = round(disk.total / (1024 ** 3), 1)

        context = {
            'cpu_usage': cpu_usage,
            'memory_usage': memory.percent,
            'memory_total_gb': memory_total_gb,
            'disk_usage': disk.percent,
            'disk_total_gb': disk_total_gb,
            'uptime': str(uptime).split('.')[0],
            'website_stats': [],  # 这里添加网站统计数据
            'system_logs': [],    # 这里添加系统日志数据
            'system_info': {
                'os': platform.system(),
                'cpu_count': psutil.cpu_count()
            }
        }
        return render(request, 'dashboard/index.html', context)

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        return render(request, 'dashboard/login.html')
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            user.last_login_ip = request.META.get('REMOTE_ADDR')
            user.save()
            
            # 设置默认session值
            if 'panel_name' not in request.session:
                request.session['panel_name'] = '控制面板'
            if 'panel_theme' not in request.session:
                request.session['panel_theme'] = 'light'
            if 'panel_language' not in request.session:
                request.session['panel_language'] = 'zh_CN'
            request.session.modified = True
            
            return redirect('dashboard:index')
        return render(request, 'dashboard/login.html', {'error': '用户名或密码错误'})

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('dashboard:login')

class SystemView(LoginRequiredMixin, View):
    login_url = '/login/'
    
    def get(self, request, action=None):
        if action == 'get_system_stats':
            return self.get_system_stats(request)
            
        # 获取系统基本信息
        system_info = {
            'os': platform.system(),
            'os_version': platform.version(),
            'hostname': platform.node(),
            'cpu_count': psutil.cpu_count(),
            'cpu_physical_count': psutil.cpu_count(logical=False),
            'memory_total': self.format_size(psutil.virtual_memory().total),
            'disk_total': self.format_size(psutil.disk_usage('/').total),
        }
        
        return render(request, 'dashboard/system.html', {'system_info': system_info})
    
    def get_system_stats(self, request):
        # 使用上下文管理器自动释放资源
        with psutil.Process().oneshot():
            # 获取CPU使用率，减少采样间隔
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
            
            # 获取内存信息
            memory = psutil.virtual_memory()
            memory_stats = {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percent': memory.percent,
                'total_formatted': self.format_size(memory.total),
                'used_formatted': self.format_size(memory.used),
                'available_formatted': self.format_size(memory.available),
            }
            
            # 只获取根分区的磁盘信息
            disk = psutil.disk_usage('/')
            disk_stats = {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent,
                'total_formatted': self.format_size(disk.total),
                'used_formatted': self.format_size(disk.used),
                'free_formatted': self.format_size(disk.free),
            }
            
            # 获取网络信息
            net_io = psutil.net_io_counters()
            network_stats = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
            }

        # 返回统计数据
        return JsonResponse({
            'cpu': {
                'usage': cpu_percent,
                'per_cpu': cpu_per_cpu,
            },
            'memory': memory_stats,
            'disk': disk_stats,
            'network': network_stats,
            'timestamp': time.time()
        })
    
    def format_size(self, size):
        # 转换字节大小为人类可读格式
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

class WebsitesView(LoginRequiredMixin, View):
    login_url = '/login/'
    
    def __init__(self):
        super().__init__()
        # 确保必要的目录存在
        os.makedirs(Website.BASE_WWW_PATH, exist_ok=True)
        os.makedirs(Website.BASE_LOGS_PATH, exist_ok=True)
        os.makedirs(Website.BASE_SSL_PATH, exist_ok=True)
        os.makedirs(Website.NGINX_SITES_AVAILABLE, exist_ok=True)
        os.makedirs(Website.NGINX_SITES_ENABLED, exist_ok=True)
    
    def get(self, request, action=None, website_id=None):
        if action == 'add':
            return render(request, 'dashboard/websites_add.html')
        elif action == 'edit' and website_id:
            # 只获取需要的字段
            website = get_object_or_404(
                Website.objects.only('id', 'name', 'domain', 'port', 'php_version'),
                id=website_id
            )
            return render(request, 'dashboard/websites_edit.html', {'website': website})
            
        # 分页查询
        page = int(request.GET.get('page', 1))
        per_page = 20
        start = (page - 1) * per_page
        end = start + per_page
        
        # 只获取需要的字段并分页
        websites = Website.objects.only(
            'id', 'name', 'domain', 'port', 'php_version', 
            'status', 'created_at'
        )[start:end]
        
        return render(request, 'dashboard/websites.html', {'websites': websites})
    
    def post(self, request, action=None, website_id=None):
        if action == 'add':
            return self.add_website(request)
        elif action == 'edit' and website_id:
            return self.edit_website(request, website_id)
        elif action == 'delete' and website_id:
            return self.delete_website(request, website_id)
        elif action == 'toggle' and website_id:
            return self.toggle_website(request, website_id)
    
    def add_website(self, request):
        try:
            # 创建网站记录
            website = Website.objects.create(
                name=request.POST.get('name'),
                domain=request.POST.get('domain'),
                path=os.path.join(Website.BASE_WWW_PATH, request.POST.get('domain')),  # 使用默认路径
                port=request.POST.get('port', 80),
                server_type=request.POST.get('server_type', 'nginx'),
                php_version=request.POST.get('php_version'),
            )
            
            # 创建网站相关目录
            os.makedirs(website.path, exist_ok=True)  # 网站目录
            os.makedirs(website.get_log_path(), exist_ok=True)  # 日志目录
            os.makedirs(website.get_ssl_path(), exist_ok=True)  # SSL目录
            
            # 生成并保存配置文件
            config = website.generate_nginx_config()
            config_path = website.get_config_path()
            with open(config_path, 'w') as f:
                f.write(config)
            
            # 创建符号链接
            symlink_path = os.path.join(Website.NGINX_SITES_ENABLED, f"{website.domain}.conf")
            if os.path.exists(symlink_path):
                os.remove(symlink_path)
            os.symlink(config_path, symlink_path)
            
            # 设置目录权限
            subprocess.run(['chown', '-R', 'www:www', website.path])
            subprocess.run(['chown', '-R', 'www:www', website.get_log_path()])
            subprocess.run(['chmod', '-R', '755', website.path])
            
            # 重启Nginx
            subprocess.run(['systemctl', 'reload', 'nginx'])
            
            messages.success(request, '网站创建成功！')
            return redirect('dashboard:websites')
        except Exception as e:
            messages.error(request, f'创建网站失败：{str(e)}')
            return redirect('dashboard:websites')
    
    def edit_website(self, request, website_id):
        website = get_object_or_404(Website, id=website_id)
        try:
            old_domain = website.domain
            old_path = website.path
            old_log_path = website.get_log_path()
            old_ssl_path = website.get_ssl_path()
            
            # 更新网站信息
            website.name = request.POST.get('name')
            website.domain = request.POST.get('domain')
            website.port = request.POST.get('port', 80)
            website.php_version = request.POST.get('php_version')
            
            # 如果域名改变，需要更新所有相关路径
            if old_domain != website.domain:
                # 设置新路径
                website.path = os.path.join(Website.BASE_WWW_PATH, website.domain)
                
                # 移动网站目录
                if os.path.exists(old_path):
                    os.makedirs(os.path.dirname(website.path), exist_ok=True)
                    os.rename(old_path, website.path)
                
                # 移动日志目录
                new_log_path = website.get_log_path()
                if os.path.exists(old_log_path):
                    os.makedirs(os.path.dirname(new_log_path), exist_ok=True)
                    os.rename(old_log_path, new_log_path)
                
                # 移动SSL目录
                new_ssl_path = website.get_ssl_path()
                if os.path.exists(old_ssl_path):
                    os.makedirs(os.path.dirname(new_ssl_path), exist_ok=True)
                    os.rename(old_ssl_path, new_ssl_path)
                
                # 删除旧的nginx配置
                old_config_path = os.path.join(Website.NGINX_SITES_AVAILABLE, f"{old_domain}.conf")
                if os.path.exists(old_config_path):
                    os.remove(old_config_path)
                
                # 删除旧的符号链接
                old_symlink_path = os.path.join(Website.NGINX_SITES_ENABLED, f"{old_domain}.conf")
                if os.path.exists(old_symlink_path):
                    os.remove(old_symlink_path)
            
            website.save()
            
            # 生成新的nginx配置
            config = website.generate_nginx_config()
            config_path = website.get_config_path()
            with open(config_path, 'w') as f:
                f.write(config)
            
            # 创建新的符号链接
            symlink_path = os.path.join(Website.NGINX_SITES_ENABLED, f"{website.domain}.conf")
            if os.path.exists(symlink_path):
                os.remove(symlink_path)
            os.symlink(config_path, symlink_path)
            
            # 设置目录权限
            subprocess.run(['chown', '-R', 'www-data:www-data', website.path])
            subprocess.run(['chown', '-R', 'www-data:www-data', website.get_log_path()])
            subprocess.run(['chmod', '-R', '755', website.path])
            
            # 重启Nginx
            subprocess.run(['systemctl', 'reload', 'nginx'])
            
            messages.success(request, '网站更新成功！')
            return redirect('dashboard:websites')
        except Exception as e:
            messages.error(request, f'更新网站失败：{str(e)}')
            return redirect('dashboard:websites')
    
    def delete_website(self, request, website_id):
        website = get_object_or_404(Website, id=website_id)
        try:
            # 删除网站目录
            if os.path.exists(website.path):
                subprocess.run(['rm', '-rf', website.path])
            
            # 删除日志目录
            if os.path.exists(website.get_log_path()):
                subprocess.run(['rm', '-rf', website.get_log_path()])
            
            # 删除SSL目录
            if os.path.exists(website.get_ssl_path()):
                subprocess.run(['rm', '-rf', website.get_ssl_path()])
            
            # 删除配置文件
            if os.path.exists(website.get_config_path()):
                os.remove(website.get_config_path())
            
            # 删除符号链接
            symlink_path = os.path.join(Website.NGINX_SITES_ENABLED, f"{website.domain}.conf")
            if os.path.exists(symlink_path):
                os.remove(symlink_path)
            
            # 删除网站记录
            website.delete()
            
            # 重启Nginx
            subprocess.run(['systemctl', 'reload', 'nginx'])
            
            messages.success(request, '网站删除成功！')
        except Exception as e:
            messages.error(request, f'删除网站失败：{str(e)}')
        return redirect('dashboard:websites')
    
    def toggle_website(self, request, website_id):
        website = get_object_or_404(Website, id=website_id)
        try:
            symlink_path = f"/etc/nginx/sites-enabled/{website.domain}.conf"
            if website.status == 'running':
                # 停止网站
                if os.path.exists(symlink_path):
                    os.remove(symlink_path)
                website.status = 'stopped'
            else:
                # 启动网站
                if not os.path.exists(symlink_path):
                    os.symlink(website.get_config_path(), symlink_path)
                website.status = 'running'
            
            website.save()
            subprocess.run(['systemctl', 'reload', 'nginx'])
            
            messages.success(request, f'网站{website.status == "running" and "启动" or "停止"}成功！')
        except Exception as e:
            messages.error(request, f'操作失败：{str(e)}')
        return redirect('dashboard:websites')

class SecurityView(LoginRequiredMixin, View):
    login_url = '/login/'
    
    def get(self, request, action=None):
        try:
            if action == 'add':
                print("显示添加规则表单")  # 调试输出
                return render(request, 'dashboard/security_add.html')
            elif action == 'edit':
                rule_id = request.GET.get('id')
                rule = get_object_or_404(SecurityRule, id=rule_id)
                return render(request, 'dashboard/security_edit.html', {'rule': rule})
            
            # 获取所有规则并按创建时间倒序排序
            rules = SecurityRule.objects.all().order_by('-created_at')
            
            # 添加调试输出
            print("Found rules:", rules.count())
            for rule in rules:
                print(f"Rule: {rule.name} - {rule.rule_type} - {rule.value}")
            
            return render(request, 'dashboard/security.html', {'rules': rules})
        except Exception as e:
            print(f"SecurityView.get 出错: {str(e)}")  # 调试输出
            messages.error(request, f'操作失败：{str(e)}')
            return redirect('dashboard:security')
    
    def post(self, request):
        try:
            action = request.POST.get('action') or request.GET.get('action')
            print(f"处理 POST 请求，action: {action}")  # 调试输出
            
            if action == 'add':
                return self.add_rule(request)
            elif action == 'edit':
                return self.edit_rule(request)
            elif action == 'delete':
                return self.delete_rule(request)
            elif action == 'toggle':
                return self.toggle_rule(request)
            
            messages.error(request, '无效的操作')
            return redirect('dashboard:security')
        except Exception as e:
            print(f"SecurityView.post 出错: {str(e)}")  # 调试输出
            messages.error(request, f'操作失败：{str(e)}')
            return redirect('dashboard:security')
    
    def add_rule(self, request):
        try:
            # 打印请求数据，用于调试
            print("POST data:", request.POST)
            
            # 创建规则
            rule = SecurityRule.objects.create(
                name=request.POST.get('name'),
                rule_type=request.POST.get('rule_type'),
                value=request.POST.get('value'),
                description=request.POST.get('description', '')
            )
            
            # 应用规则
            try:
                rule.apply_rule()
            except Exception as e:
                # 如果应用规则失败，删除规则记录
                rule.delete()
                raise Exception(f'应用规则失败：{str(e)}')
            
            messages.success(request, '安全规则添加成功！')
        except Exception as e:
            messages.error(request, f'添加规则失败：{str(e)}')
        return redirect('dashboard:security')
    
    def edit_rule(self, request):
        try:
            rule = get_object_or_404(SecurityRule, id=request.POST.get('rule_id'))
            old_value = rule.value
            
            rule.name = request.POST.get('name')
            rule.value = request.POST.get('value')
            rule.description = request.POST.get('description', '')
            
            if old_value != rule.value:
                # 如果规则值改变，需要重新应用规则
                rule.apply_rule()
            
            rule.save()
            messages.success(request, '安全规则更新成功！')
        except Exception as e:
            messages.error(request, f'更新规则失败：{str(e)}')
        return redirect('dashboard:security')
    
    def delete_rule(self, request):
        try:
            rule = get_object_or_404(SecurityRule, id=request.POST.get('rule_id'))
            rule.is_enabled = False
            rule.apply_rule()  # 移除规则
            rule.delete()
            messages.success(request, '安全规则删除成功！')
        except Exception as e:
            messages.error(request, f'删除规则失败：{str(e)}')
        return redirect('dashboard:security')
    
    def toggle_rule(self, request):
        try:
            rule = get_object_or_404(SecurityRule, id=request.POST.get('rule_id'))
            rule.is_enabled = not rule.is_enabled
            rule.save()
            rule.apply_rule()
            messages.success(request, f'规则已{rule.is_enabled and "启用" or "禁用"}！')
        except Exception as e:
            messages.error(request, f'操作失败：{str(e)}')
        return redirect('dashboard:security')

class CronView(LoginRequiredMixin, View):
    login_url = '/login/'
    
    def get(self, request, action=None):
        try:
            if action == 'add':
                print("显示添加任务表单")  # 调试输出
                return render(request, 'dashboard/cron_add.html')
            elif action == 'edit':
                job_id = request.GET.get('id')
                job = get_object_or_404(CronJob, id=job_id)
                return render(request, 'dashboard/cron_edit.html', {'job': job})
            
            jobs = CronJob.objects.all()
            # 更新下次执行时间
            for job in jobs:
                if job.is_enabled and job.get_cron_expression():
                    try:
                        cron = croniter(job.get_cron_expression(), datetime.datetime.now())
                        job.next_run = cron.get_next(datetime.datetime)
                        job.save()
                    except Exception as e:
                        print(f"更新任务 {job.name} 的下次执行时间失败: {str(e)}")
            
            return render(request, 'dashboard/cron.html', {'jobs': jobs})
        except Exception as e:
            print(f"CronView.get 出错: {str(e)}")  # 调试输出
            messages.error(request, f'操作失败：{str(e)}')
            return redirect('dashboard:cron')
    
    def post(self, request):
        try:
            action = request.POST.get('action') or request.GET.get('action')
            print(f"处理 POST 请求，action: {action}")  # 调试输出
            
            if action == 'add':
                return self.add_job(request)
            elif action == 'edit':
                return self.edit_job(request)
            elif action == 'delete':
                return self.delete_job(request)
            elif action == 'toggle':
                return self.toggle_job(request)
            
            messages.error(request, '无效的操作')
            return redirect('dashboard:cron')
        except Exception as e:
            print(f"CronView.post 出错: {str(e)}")  # 调试输出
            messages.error(request, f'操作失败：{str(e)}')
            return redirect('dashboard:cron')
    
    def add_job(self, request):
        try:
            # 获取表单数据
            name = request.POST.get('name')
            command = request.POST.get('command')
            interval = request.POST.get('interval')
            cron_expression = request.POST.get('cron_expression', '')
            description = request.POST.get('description', '')
            
            # 打印调试信息
            print("添加计划任务:", {
                'name': name,
                'command': command,
                'interval': interval,
                'cron_expression': cron_expression,
                'description': description
            })
            
            # 验证数据
            if not name or not command or not interval:
                raise ValueError('请填写必要的字段')
            
            if interval == 'custom' and not cron_expression:
                raise ValueError('自定义执行周期时必须填写Cron表达式')
            
            # 验证cron表达式
            if interval == 'custom':
                try:
                    croniter.croniter(cron_expression)
                except Exception as e:
                    print("Cron表达式验证失败:", str(e))
                    raise ValueError('无效的Cron表达式')
            
            # 创建任务
            job = CronJob.objects.create(
                name=name,
                command=command,
                interval=interval,
                cron_expression=cron_expression,
                description=description,
                is_enabled=True  # 默认启用
            )
            
            # 如果启用，添加到系统crontab
            try:
                print("正在更新crontab...")
                job.update_crontab()
                print("crontab更新成功")
            except Exception as e:
                print("更新crontab失败:", str(e))
                # 如果添加到crontab失败，删除任务记录
                job.delete()
                raise Exception(f'添加到系统计划任务失败：{str(e)}')
            
            messages.success(request, '计划任务添加成功！')
            return redirect('dashboard:cron')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'添加任务失败：{str(e)}')
        return redirect('dashboard:cron')
    
    def edit_job(self, request):
        try:
            job = get_object_or_404(CronJob, id=request.POST.get('job_id'))
            
            job.name = request.POST.get('name')
            job.command = request.POST.get('command')
            job.interval = request.POST.get('interval')
            job.cron_expression = request.POST.get('cron_expression', '')
            job.description = request.POST.get('description', '')
            
            job.save()
            job.update_crontab()
            
            messages.success(request, '计划任务更新成功！')
        except Exception as e:
            messages.error(request, f'更新任务失败：{str(e)}')
        return redirect('dashboard:cron')
    
    def delete_job(self, request):
        try:
            job = get_object_or_404(CronJob, id=request.POST.get('job_id'))
            job.is_enabled = False
            job.update_crontab()  # 从crontab中移除
            job.delete()
            messages.success(request, '计划任务删除成功！')
        except Exception as e:
            messages.error(request, f'删除任务失败：{str(e)}')
        return redirect('dashboard:cron')
    
    def toggle_job(self, request):
        try:
            job = get_object_or_404(CronJob, id=request.POST.get('job_id'))
            job.is_enabled = not job.is_enabled
            job.save()
            job.update_crontab()
            messages.success(request, f'任务已{job.is_enabled and "启用" or "禁用"}！')
        except Exception as e:
            messages.error(request, f'操作失败：{str(e)}')
        return redirect('dashboard:cron')

class SettingsView(LoginRequiredMixin, View):
    login_url = '/login/'
    
    def get(self, request):
        # 获取当前设置
        settings = {
            'panel_name': request.session.get('panel_name', '控制面板'),
            'panel_theme': request.session.get('panel_theme', 'light'),
            'panel_language': request.session.get('panel_language', 'zh_CN'),
            'backup_path': request.session.get('backup_path', '/www/backup'),
            'backup_retention': request.session.get('backup_retention', 7),
            'log_retention': request.session.get('log_retention', 30),
            'notification_email': request.session.get('notification_email', ''),
            'smtp_host': request.session.get('smtp_host', ''),
            'smtp_port': request.session.get('smtp_port', 587),
            'smtp_user': request.session.get('smtp_user', ''),
            'smtp_password': request.session.get('smtp_password', ''),
            'smtp_ssl': request.session.get('smtp_ssl', True),
        }
        return render(request, 'dashboard/settings.html', {'settings': settings})
    
    def post(self, request):
        try:
            # 保存基本设置
            panel_name = request.POST.get('panel_name', '控制面板')
            request.session['panel_name'] = panel_name
            request.session.modified = True  # 确保session被保存
            
            # 保存其他设置
            request.session['panel_theme'] = request.POST.get('panel_theme', 'light')
            request.session['panel_language'] = request.POST.get('panel_language', 'zh_CN')
            
            # 保存备份设置
            backup_path = request.POST.get('backup_path', '/www/backup')
            if not os.path.exists(backup_path):
                os.makedirs(backup_path, exist_ok=True)
            request.session['backup_path'] = backup_path
            request.session['backup_retention'] = int(request.POST.get('backup_retention', 7))
            
            # 保存日志设置
            request.session['log_retention'] = int(request.POST.get('log_retention', 30))
            
            # 保存邮件通知设置
            request.session['notification_email'] = request.POST.get('notification_email', '')
            request.session['smtp_host'] = request.POST.get('smtp_host', '')
            request.session['smtp_port'] = int(request.POST.get('smtp_port', 587))
            request.session['smtp_user'] = request.POST.get('smtp_user', '')
            
            # 只在提供新密码时更新密码
            smtp_password = request.POST.get('smtp_password')
            if smtp_password:
                request.session['smtp_password'] = smtp_password
            
            request.session['smtp_ssl'] = request.POST.get('smtp_ssl') == 'on'
            
            # 确保所有更改都被保存
            request.session.modified = True
            
            # 测试邮件设置
            if request.POST.get('test_email'):
                self.test_email_settings(request)
            
            # 如果是AJAX请求，返回JSON响应
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': '设置保存成功！',
                    'panel_name': panel_name
                })
            
            messages.success(request, '设置保存成功！')
        except Exception as e:
            messages.error(request, f'保存设置失败：{str(e)}')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': f'保存设置失败：{str(e)}'
                })
        return redirect('dashboard:settings')
    
    def test_email_settings(self, request):
        """测试邮件设置"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.utils import formataddr
            
            smtp_host = request.session.get('smtp_host')
            smtp_port = request.session.get('smtp_port')
            smtp_user = request.session.get('smtp_user')
            smtp_password = request.session.get('smtp_password')
            smtp_ssl = request.session.get('smtp_ssl')
            notification_email = request.session.get('notification_email')
            
            msg = MIMEText('这是一封测试邮件，如果您收到这封邮件，说明邮件设置正确。', 'plain', 'utf-8')
            msg['From'] = formataddr(['控制面板', smtp_user])
            msg['To'] = formataddr(['管理员', notification_email])
            msg['Subject'] = '控制面板邮件测试'
            
            if smtp_ssl:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
            
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, [notification_email], msg.as_string())
            server.quit()
            
            messages.success(request, '测试邮件发送成功！')
        except Exception as e:
            messages.error(request, f'发送测试邮件失败：{str(e)}')

class DatabaseView(LoginRequiredMixin, View):
    login_url = '/login/'
    
    def get(self, request, action=None, database_id=None):
        if action == 'add':
            return render(request, 'dashboard/database_add.html')
        elif action == 'edit' and database_id:
            database = get_object_or_404(Database, id=database_id)
            return render(request, 'dashboard/database_edit.html', {'database': database})
            
        databases = Database.objects.all()
        return render(request, 'dashboard/database.html', {'databases': databases})
    
    def post(self, request, action=None, database_id=None):
        if action == 'add':
            return self.add_database(request)
        elif action == 'edit' and database_id:
            return self.edit_database(request, database_id)
        elif action == 'delete' and database_id:
            return self.delete_database(request, database_id)
    
    def generate_password(self, length=16):
        """生成随机密码"""
        alphabet = string.ascii_letters + string.digits + '@#$%^&*'
        return ''.join(secrets.choice(alphabet) for i in range(length))
    
    def add_database(self, request):
        try:
            db_name = request.POST.get('name')
            db_type = request.POST.get('db_type', 'mysql')
            username = request.POST.get('username', db_name)
            password = request.POST.get('password') or self.generate_password()
            charset = request.POST.get('charset', 'utf8mb4')
            
            # 创建数据库记录
            database = Database.objects.create(
                name=db_name,
                db_type=db_type,
                username=username,
                password=password,
                charset=charset
            )
            
            # 连接MySQL并创建数据库和用户
            if db_type == 'mysql':
                conn = mysql.connector.connect(
                    host='localhost',
                    user='root',
                    password='your_mysql_root_password'  # 需要替换为实际的root密码
                )
                cursor = conn.cursor()
                
                # 创建数据库
                cursor.execute(f"CREATE DATABASE `{db_name}` CHARACTER SET {charset}")
                
                # 创建用户并授权
                cursor.execute(f"CREATE USER '{username}'@'localhost' IDENTIFIED BY '{password}'")
                cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{username}'@'localhost'")
                cursor.execute("FLUSH PRIVILEGES")
                
                cursor.close()
                conn.close()
            
            messages.success(request, '数据库创建成功！')
            return redirect('dashboard:database')
        except Exception as e:
            messages.error(request, f'创建数据库失败：{str(e)}')
            return redirect('dashboard:database')
    
    def edit_database(self, request, database_id):
        database = get_object_or_404(Database, id=database_id)
        try:
            new_password = request.POST.get('password')
            
            if new_password:
                # 更新MySQL用户密码
                if database.db_type == 'mysql':
                    conn = mysql.connector.connect(
                        host='localhost',
                        user='root',
                        password='your_mysql_root_password'
                    )
                    cursor = conn.cursor()
                    
                    cursor.execute(f"ALTER USER '{database.username}'@'localhost' IDENTIFIED BY '{new_password}'")
                    cursor.execute("FLUSH PRIVILEGES")
                    
                    cursor.close()
                    conn.close()
                
                database.password = new_password
                database.save()
            
            messages.success(request, '数据库更新成功！')
            return redirect('dashboard:database')
        except Exception as e:
            messages.error(request, f'更新数据库失败：{str(e)}')
            return redirect('dashboard:database')
    
    def delete_database(self, request, database_id):
        database = get_object_or_404(Database, id=database_id)
        try:
            # 删除MySQL数据库和用户
            if database.db_type == 'mysql':
                conn = mysql.connector.connect(
                    host='localhost',
                    user='root',
                    password='your_mysql_root_password'
                )
                cursor = conn.cursor()
                
                cursor.execute(f"DROP DATABASE IF EXISTS `{database.name}`")
                cursor.execute(f"DROP USER IF EXISTS '{database.username}'@'localhost'")
                cursor.execute("FLUSH PRIVILEGES")
                
                cursor.close()
                conn.close()
            
            # 删除数据库记录
            database.delete()
            
            messages.success(request, '数据库删除成功！')
        except Exception as e:
            messages.error(request, f'删除数据库失败：{str(e)}')
        return redirect('dashboard:database')

class FilesView(LoginRequiredMixin, View):
    login_url = '/login/'
    
    def get(self, request, action=None):
        try:
            current_path = request.GET.get('path')
            if not current_path:
                current_path = FileManager.BASE_PATH
            
            if action == 'download':
                return self.download_file(request)
            
            # 规范化路径
            current_path = os.path.abspath(current_path)
            
            # 确保路径是目录
            if not os.path.isdir(current_path):
                messages.error(request, '无效的目录路径')
                return redirect('dashboard:files')
            
            items = FileManager.list_directory(current_path)
            context = {
                'items': items,
                'current_path': current_path,
                'parent_path': os.path.dirname(current_path) if current_path != '/' else None,
                'BASE_PATH': FileManager.BASE_PATH
            }
            return render(request, 'dashboard/files.html', context)
        except Exception as e:
            messages.error(request, f'访问目录失败：{str(e)}')
            if request.GET.get('path'):
                return redirect('dashboard:files')
            return render(request, 'dashboard/files.html', {
                'items': [],
                'current_path': FileManager.BASE_PATH,
                'parent_path': None,
                'BASE_PATH': FileManager.BASE_PATH
            })
    
    def post(self, request):
        try:
            action = request.GET.get('action')
            
            if action == 'batch_delete':
                return self.batch_delete(request)
            elif action == 'move':
                return self.move_items(request)
            elif action == 'upload':
                return self.upload_file(request)
            elif action == 'remote_download':
                return self.remote_download(request)
            elif action == 'create_file':
                return self.create_file(request)
            elif action == 'create_folder':
                return self.create_folder(request)
            elif action == 'delete':
                return self.delete_item(request)
            elif action == 'rename':
                return self.rename_item(request)
            elif action == 'chmod':
                return self.chmod_item(request)
            
            messages.error(request, '无效的操作')
            return redirect(request.META.get('HTTP_REFERER') or 'dashboard:files')
        except Exception as e:
            messages.error(request, f'操作失败：{str(e)}')
            return redirect(request.META.get('HTTP_REFERER') or 'dashboard:files')
    
    def upload_file(self, request):
        try:
            current_path = request.POST.get('current_path')
            uploaded_file = request.FILES['file']
            file_path = os.path.join(current_path, uploaded_file.name)
            
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            messages.success(request, '文件上传成功！')
        except Exception as e:
            messages.error(request, f'文件上传失败：{str(e)}')
        return redirect(f"{reverse('dashboard:files')}?path={current_path}")
    
    def remote_download(self, request):
        try:
            url = request.POST.get('url')
            filename = request.POST.get('filename')
            current_path = request.POST.get('current_path')
            
            if not filename:
                filename = os.path.basename(url)
            
            file_path = os.path.join(current_path, filename)
            
            # 使用wget下载文件
            subprocess.run(['wget', '-O', file_path, url], check=True)
            
            messages.success(request, '文件下载成功！')
        except Exception as e:
            messages.error(request, f'远程下载失败：{str(e)}')
        return redirect(f"{reverse('dashboard:files')}?path={current_path}")
    
    def create_file(self, request):
        try:
            current_path = request.POST.get('current_path')
            file_name = request.POST.get('file_name')
            content = request.POST.get('content', '')
            
            # 规范化路径
            file_path = os.path.abspath(os.path.join(current_path, file_name))
            
            # 安全检查
            if not FileManager.is_safe_path(file_path):
                raise ValueError('无效的文件路径')
            
            # 创建文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 设置权限
            os.chmod(file_path, 0o644)
            
            messages.success(request, '文件创建成功！')
        except Exception as e:
            messages.error(request, f'创建文件失败：{str(e)}')
        return redirect(f"{reverse('dashboard:files')}?path={current_path}")
    
    def create_folder(self, request):
        try:
            current_path = request.POST.get('current_path')
            folder_name = request.POST.get('folder_name')
            
            # 规范化路径
            folder_path = os.path.abspath(os.path.join(current_path, folder_name))
            
            # 安全检查
            if not FileManager.is_safe_path(folder_path):
                raise ValueError('无效的目录路径')
            
            # 创建目录
            os.makedirs(folder_path, exist_ok=True)
            
            # 设置权限
            os.chmod(folder_path, 0o755)
            
            messages.success(request, '文件夹创建成功！')
        except Exception as e:
            messages.error(request, f'创建文件夹失败：{str(e)}')
        return redirect(f"{reverse('dashboard:files')}?path={current_path}")
    
    def delete_item(self, request):
        try:
            path = request.POST.get('path')
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            messages.success(request, '删除成功！')
        except Exception as e:
            messages.error(request, f'删除失败：{str(e)}')
        return redirect(request.META.get('HTTP_REFERER', reverse('dashboard:files')))
    
    def rename_item(self, request):
        try:
            old_path = request.POST.get('old_path')
            new_name = request.POST.get('new_name')
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            
            os.rename(old_path, new_path)
            messages.success(request, '重命名成功！')
        except Exception as e:
            messages.error(request, f'重命名失败：{str(e)}')
        return redirect(request.META.get('HTTP_REFERER', reverse('dashboard:files')))
    
    def chmod_item(self, request):
        try:
            path = request.POST.get('path')
            mode = int(request.POST.get('mode'), 8)
            
            os.chmod(path, mode)
            messages.success(request, '权限修改成功！')
        except Exception as e:
            messages.error(request, f'修改权限失败：{str(e)}')
        return redirect(request.META.get('HTTP_REFERER', reverse('dashboard:files')))
    
    def download_file(self, request):
        try:
            file_path = request.GET.get('path')
            if os.path.isfile(file_path):
                with open(file_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                    return response
            raise Exception('文件不存在')
        except Exception as e:
            messages.error(request, f'下载失败：{str(e)}')
            return redirect(request.META.get('HTTP_REFERER', reverse('dashboard:files')))

    def batch_delete(self, request):
        try:
            paths = json.loads(request.POST.get('paths', '[]'))
            for path in paths:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            messages.success(request, '批量删除成功！')
        except Exception as e:
            messages.error(request, f'批量删除失败：{str(e)}')
        return redirect(request.META.get('HTTP_REFERER', reverse('dashboard:files')))

    def move_items(self, request):
        try:
            source_paths = json.loads(request.POST.get('source_paths', '[]'))
            target_path = request.POST.get('target_path')
            operation = request.POST.get('operation')
            
            # 确保目标路径存在
            os.makedirs(target_path, exist_ok=True)
            
            for source_path in source_paths:
                filename = os.path.basename(source_path)
                dest_path = os.path.join(target_path, filename)
                
                if operation == 'copy':
                    if os.path.isdir(source_path):
                        shutil.copytree(source_path, dest_path)
                    else:
                        shutil.copy2(source_path, dest_path)
                else:  # move or cut
                    shutil.move(source_path, dest_path)
            
            operation_name = {
                'copy': '复制',
                'cut': '剪切',
                'move': '移动'
            }.get(operation, '操作')
            
            messages.success(request, f'{operation_name}成功！')
        except Exception as e:
            messages.error(request, f'操作失败：{str(e)}')
        return redirect(f"{reverse('dashboard:files')}?path={target_path}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['BASE_PATH'] = FileManager.BASE_PATH
        return context
