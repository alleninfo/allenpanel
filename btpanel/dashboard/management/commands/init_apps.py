from django.core.management.base import BaseCommand
from dashboard.models import AppStore

class Command(BaseCommand):
    help = '初始化应用商店数据'

    def handle(self, *args, **kwargs):
        # 预定义应用数据
        apps_data = [
            {
                'name': 'MySQL',
                'type': 'database',
                'description': 'MySQL是世界上最流行的开源数据库',
                'icon': 'bi-database',
                'versions': ['5.7', '8.0'],
                'default_version': '8.0',
                'install_commands': {
                    'ubuntu': {
                        '5.7': '''apt update && 
                                 apt install -y mysql-server-5.7 &&
                                 systemctl enable mysql &&
                                 systemctl start mysql''',
                        '8.0': '''apt update && 
                                 apt install -y mysql-server &&
                                 systemctl enable mysql &&
                                 systemctl start mysql'''
                    },
                    'centos': {
                        '5.7': '''yum install -y https://dev.mysql.com/get/mysql57-community-release-el7-11.noarch.rpm &&
                                 yum install -y mysql-community-server &&
                                 systemctl enable mysqld &&
                                 systemctl start mysqld''',
                        '8.0': '''yum install -y https://dev.mysql.com/get/mysql80-community-release-el7-3.noarch.rpm &&
                                 yum install -y mysql-community-server &&
                                 systemctl enable mysqld &&
                                 systemctl start mysqld'''
                    }
                },
                'uninstall_command': '''systemctl stop mysql || systemctl stop mysqld &&
                                      systemctl disable mysql || systemctl disable mysqld &&
                                      apt remove -y mysql* || yum remove -y mysql*'''
            },
            {
                'name': 'PostgreSQL',
                'type': 'database',
                'description': '功能强大的开源对象关系数据库',
                'icon': 'bi-database-fill',
                'versions': ['12', '13', '14', '15'],
                'default_version': '15',
                'install_commands': {
                    'ubuntu': {
                        '12': '''apt update && 
                                apt install -y postgresql-12 &&
                                systemctl enable postgresql &&
                                systemctl start postgresql''',
                        '13': '''apt update && 
                                apt install -y postgresql-13 &&
                                systemctl enable postgresql &&
                                systemctl start postgresql''',
                        '14': '''apt update && 
                                apt install -y postgresql-14 &&
                                systemctl enable postgresql &&
                                systemctl start postgresql''',
                        '15': '''apt update && 
                                apt install -y postgresql-15 &&
                                systemctl enable postgresql &&
                                systemctl start postgresql'''
                    },
                    'centos': {
                        '12': '''yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm &&
                                yum install -y postgresql12-server &&
                                /usr/pgsql-12/bin/postgresql-12-setup initdb &&
                                systemctl enable postgresql-12 &&
                                systemctl start postgresql-12''',
                        '13': '''yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm &&
                                yum install -y postgresql13-server &&
                                /usr/pgsql-13/bin/postgresql-13-setup initdb &&
                                systemctl enable postgresql-13 &&
                                systemctl start postgresql-13''',
                        '14': '''yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm &&
                                yum install -y postgresql14-server &&
                                /usr/pgsql-14/bin/postgresql-14-setup initdb &&
                                systemctl enable postgresql-14 &&
                                systemctl start postgresql-14''',
                        '15': '''yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm &&
                                yum install -y postgresql15-server &&
                                /usr/pgsql-15/bin/postgresql-15-setup initdb &&
                                systemctl enable postgresql-15 &&
                                systemctl start postgresql-15'''
                    }
                },
                'uninstall_command': '''systemctl stop postgresql* &&
                                      systemctl disable postgresql* &&
                                      apt remove -y postgresql* || yum remove -y postgresql*'''
            },
            {
                'name': 'Redis',
                'type': 'database',
                'description': '高性能的内存数据库和缓存服务器',
                'icon': 'bi-lightning',
                'versions': ['6.0', '6.2', '7.0'],
                'default_version': '7.0',
                'install_commands': {
                    'ubuntu': {
                        '6.0': '''add-apt-repository -y ppa:redislabs/redis &&
                                 apt update &&
                                 apt install -y redis-server=6:6.0.* &&
                                 systemctl enable redis-server &&
                                 systemctl start redis-server''',
                        '6.2': '''add-apt-repository -y ppa:redislabs/redis &&
                                 apt update &&
                                 apt install -y redis-server=6:6.2.* &&
                                 systemctl enable redis-server &&
                                 systemctl start redis-server''',
                        '7.0': '''add-apt-repository -y ppa:redislabs/redis &&
                                 apt update &&
                                 apt install -y redis-server &&
                                 systemctl enable redis-server &&
                                 systemctl start redis-server'''
                    },
                    'centos': {
                        '6.0': '''yum install -y epel-release &&
                                 yum install -y redis-6.0.* &&
                                 systemctl enable redis &&
                                 systemctl start redis''',
                        '6.2': '''yum install -y epel-release &&
                                 yum install -y redis-6.2.* &&
                                 systemctl enable redis &&
                                 systemctl start redis''',
                        '7.0': '''yum install -y epel-release &&
                                 yum install -y redis &&
                                 systemctl enable redis &&
                                 systemctl start redis'''
                    }
                },
                'uninstall_command': '''systemctl stop redis* &&
                                      systemctl disable redis* &&
                                      apt remove -y redis* || yum remove -y redis*'''
            }
        ]

        # 创建应用记录
        for app_data in apps_data:
            app, created = AppStore.objects.get_or_create(
                name=app_data['name'],
                defaults={
                    'app_type': app_data['type'],
                    'description': app_data['description'],
                    'icon': app_data['icon'],
                    'versions': app_data['versions'],
                    'default_version': app_data['default_version'],
                    'install_commands': app_data['install_commands'],
                    'uninstall_command': app_data['uninstall_command']
                }
            )
            
            if created:
                self.stdout.write(f'创建应用: {app.name}')
            else:
                # 更新应用信息
                for key, value in app_data.items():
                    if key != 'name':
                        setattr(app, key, value)
                app.save()
                self.stdout.write(f'更新应用: {app.name}')

        self.stdout.write(self.style.SUCCESS('应用商店数据初始化完成')) 