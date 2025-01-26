#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 面板安装目录
INSTALL_DIR="/www/panel"
PYTHON_BIN="$INSTALL_DIR/venv/bin/python"
MANAGE_PY="$INSTALL_DIR/btpanel/manage.py"
LOG_FILE="/var/log/panel.log"
SERVICE_FILE="/etc/systemd/system/panel.service"

# 检查是否为root用户
check_root() {
    if [ $(id -u) != "0" ]; then
        echo -e "${RED}错误: 必须使用root用户运行此脚本${NC}"
        exit 1
    fi
}

# 显示菜单
show_menu() {
    echo -e "${BLUE}================ 面板管理工具 =================${NC}"
    echo -e "${GREEN}1. 安装面板"
    echo -e "2. 查看面板信息"
    echo -e "3. 启动面板服务"
    echo -e "4. 停止面板服务"
    echo -e "5. 重启面板服务"
    echo -e "6. 查看错误日志"
    echo -e "7. 重置管理员密码"
    echo -e "8. 卸载面板"
    echo -e "0. 退出${NC}"
    echo -e "${BLUE}=============================================${NC}"
}

# 安装面板
install_panel() {
    echo -e "${YELLOW}开始安装面板...${NC}"
    
    # 安装依赖
    apt update
    apt install -y python3-venv python3-pip nginx git

    # 创建安装目录
    mkdir -p $INSTALL_DIR
    cd $INSTALL_DIR

    # 克隆代码
    git clone https://github.com/yourusername/btpanel.git

    # 创建虚拟环境
    python3 -m venv venv
    source venv/bin/activate

    # 安装依赖包
    pip install -r btpanel/requirements.txt

    # 初始化数据库
    cd btpanel
    python manage.py migrate
    python manage.py init_apps
    python manage.py create_admin

    # 创建服务文件
    cat > $SERVICE_FILE << EOF
[Unit]
Description=Panel Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/btpanel
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/gunicorn btpanel.wsgi:application -b 0.0.0.0:8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    # 启动服务
    systemctl daemon-reload
    systemctl enable panel
    systemctl start panel

    echo -e "${GREEN}面板安装完成！${NC}"
    show_panel_info
}

# 显示面板信息
show_panel_info() {
    echo -e "${BLUE}================ 面板信息 =================${NC}"
    echo -e "${GREEN}面板地址: http://$(hostname -I | awk '{print $1}'):8000"
    echo -e "默认用户名: admin"
    echo -e "默认密码: admin123${NC}"
    echo -e "${YELLOW}请及时修改默认密码！${NC}"
    echo -e "${BLUE}=========================================${NC}"
}

# 启动面板服务
start_panel() {
    echo -e "${YELLOW}正在启动面板服务...${NC}"
    systemctl start panel
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}面板服务启动成功！${NC}"
    else
        echo -e "${RED}面板服务启动失败！${NC}"
    fi
}

# 停止面板服务
stop_panel() {
    echo -e "${YELLOW}正在停止面板服务...${NC}"
    systemctl stop panel
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}面板服务已停止！${NC}"
    else
        echo -e "${RED}面板服务停止失败！${NC}"
    fi
}

# 重启面板服务
restart_panel() {
    echo -e "${YELLOW}正在重启面板服务...${NC}"
    systemctl restart panel
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}面板服务重启成功！${NC}"
    else
        echo -e "${RED}面板服务重启失败！${NC}"
    fi
}

# 查看错误日志
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}最近的错误日志：${NC}"
        tail -n 100 $LOG_FILE
    else
        echo -e "${RED}日志文件不存在！${NC}"
    fi
}

# 重置管理员密码
reset_password() {
    echo -e "${YELLOW}正在重置管理员密码...${NC}"
    cd $INSTALL_DIR/btpanel
    $PYTHON_BIN $MANAGE_PY shell << EOF
from dashboard.models import AdminUser
admin = AdminUser.objects.get(username='admin')
admin.set_password('admin123')
admin.save()
EOF
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}管理员密码已重置为: admin123${NC}"
    else
        echo -e "${RED}密码重置失败！${NC}"
    fi
}

# 卸载面板
uninstall_panel() {
    echo -e "${RED}警告：此操作将删除所有面板数据！${NC}"
    read -p "确定要卸载面板吗？(y/n): " confirm
    if [ "$confirm" = "y" ]; then
        systemctl stop panel
        systemctl disable panel
        rm -f $SERVICE_FILE
        rm -rf $INSTALL_DIR
        echo -e "${GREEN}面板已卸载！${NC}"
    fi
}

# 主程序
main() {
    check_root
    while true; do
        show_menu
        read -p "请输入选项 [0-8]: " choice
        case $choice in
            1) install_panel ;;
            2) show_panel_info ;;
            3) start_panel ;;
            4) stop_panel ;;
            5) restart_panel ;;
            6) show_logs ;;
            7) reset_password ;;
            8) uninstall_panel ;;
            0) exit 0 ;;
            *) echo -e "${RED}无效的选项！${NC}" ;;
        esac
        echo
        read -p "按回车键继续..."
    done
}

# 运行主程序
main 