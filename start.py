#!/usr/bin/env python3
"""
EcoMetrics Backend 启动脚本
"""

import os
import sys
import uvicorn
import logging
from datetime import datetime
from config import settings

def setup_logging():
    """设置启动日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 获取配置信息
    config_info = settings.get_config_info()
    warnings = settings.validate_config()
    
    print(f"📋 环境: {config_info['environment']}")
    print(f"🐛 调试模式: {config_info['debug']}")
    print(f"📊 日志级别: {config_info['log_level']}")
    print(f"🗄️ 数据库主机: {config_info['database']['host']}:{config_info['database']['port']}")
    print(f"👤 数据库用户: {config_info['database']['user']}")
    print(f"💾 数据库名称: {config_info['database']['database']}")
    print(f"🔐 密码已设置: {config_info['database']['password_set']}")
    print(f"🌐 前端URL: {config_info['application']['frontend_url']}")
    print(f"🚢 Railway环境: {config_info['railway']['is_railway']}")
    
    if warnings:
        print("⚠️ 配置警告:")
        for warning in warnings:
            print(f"   - {warning}")
    else:
        print("✅ 配置验证通过")
    
    return len(warnings) == 0

def test_database():
    """测试数据库连接"""
    print("\n🔗 测试数据库连接...")
    
    try:
        from database import test_database_connection
        
        connection_info = test_database_connection()
        print(f"✅ 数据库连接成功")
        print(f"   - 版本: {connection_info.get('database_version', 'Unknown')}")
        print(f"   - 数据库存在: {connection_info.get('database_exists', False)}")
        print(f"   - 连接池状态: {connection_info.get('pool_status', {})}")
        
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def main():
    """启动FastAPI应用"""
    print("=" * 60)
    print("🚀 EcoMetrics Backend API 启动中...")
    print(f"⏰ 启动时间: {datetime.now()}")
    print("=" * 60)
    
    setup_logging()
    
    # 检查环境配置
    config_ok = check_environment()
    
    # 测试数据库连接
    db_ok = test_database()
    
    if not config_ok:
        print("\n⚠️ 配置有问题，但继续启动...")
    
    if not db_ok:
        print("\n⚠️ 数据库连接有问题，但继续启动...")
    
    print("\n" + "=" * 60)
    print("🎯 启动信息:")
    print(f"📍 端口: {settings.PORT}")
    print(f"🔗 数据库: {settings.DATABASE_URL.replace(settings.MYSQL_PASSWORD, '***') if settings.MYSQL_PASSWORD else settings.DATABASE_URL}")
    print(f"🌐 前端URL: {settings.FRONTEND_URL}")
    print(f"📋 API文档: http://localhost:{settings.PORT}/docs")
    print(f"🩺 健康检查: http://localhost:{settings.PORT}/health")
    print(f"🔧 数据库调试: http://localhost:{settings.PORT}/debug/database")
    print("=" * 60)
    
    try:
        # 根据环境设置不同的配置
        reload_enabled = settings.ENVIRONMENT == "development"
        log_level = settings.LOG_LEVEL.lower()
        
        print(f"🔄 热重载: {reload_enabled}")
        print(f"📊 日志级别: {log_level}")
        print("\n🚀 启动服务器...")
        
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=settings.PORT,
            reload=reload_enabled,
            reload_dirs=["./"] if reload_enabled else None,
            log_level=log_level,
            access_log=True,
            use_colors=True
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 