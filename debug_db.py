#!/usr/bin/env python3
"""
数据库调试脚本
用于测试数据库连接和配置
"""

import sys
import os
import logging
import traceback
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )

def test_imports():
    """测试导入"""
    print("=== 测试导入 ===")
    try:
        from config import settings
        print("✓ 配置模块导入成功")
        
        from database import engine, test_database_connection, get_db_info
        print("✓ 数据库模块导入成功")
        
        from models import User, EcoRecord, OperationLog
        print("✓ 模型模块导入成功")
        
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        traceback.print_exc()
        return False

def test_config():
    """测试配置"""
    print("\n=== 测试配置 ===")
    try:
        from config import settings
        
        print(f"环境: {settings.ENVIRONMENT}")
        print(f"调试模式: {settings.DEBUG}")
        print(f"日志级别: {settings.LOG_LEVEL}")
        print(f"数据库主机: {settings.MYSQL_HOST}")
        print(f"数据库端口: {settings.MYSQL_PORT}")
        print(f"数据库用户: {settings.MYSQL_USER}")
        print(f"数据库名称: {settings.MYSQL_DATABASE}")
        print(f"密码已设置: {bool(settings.MYSQL_PASSWORD)}")
        
        # 获取配置信息
        config_info = settings.get_config_info()
        print(f"配置信息: {config_info}")
        
        # 验证配置
        warnings = settings.validate_config()
        if warnings:
            print(f"配置警告: {warnings}")
        else:
            print("✓ 配置验证通过")
            
        return True
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        traceback.print_exc()
        return False

def test_database_connection():
    """测试数据库连接"""
    print("\n=== 测试数据库连接 ===")
    try:
        from database import test_database_connection
        
        connection_info = test_database_connection()
        print("✓ 数据库连接成功")
        print(f"连接信息: {connection_info}")
        
        return True
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        traceback.print_exc()
        return False

def test_database_info():
    """测试数据库信息"""
    print("\n=== 测试数据库信息 ===")
    try:
        from database import get_db_info
        
        db_info = get_db_info()
        print("✓ 数据库信息获取成功")
        print(f"数据库信息: {db_info}")
        
        return True
    except Exception as e:
        print(f"✗ 数据库信息获取失败: {e}")
        traceback.print_exc()
        return False

def test_models():
    """测试模型"""
    print("\n=== 测试模型 ===")
    try:
        from database import SessionLocal
        from models import User, EcoRecord, OperationLog
        
        # 创建数据库会话
        db = SessionLocal()
        
        try:
            # 测试用户查询
            user_count = db.query(User).count()
            print(f"✓ 用户表查询成功，共 {user_count} 个用户")
            
            # 测试记录查询
            record_count = db.query(EcoRecord).count()
            print(f"✓ 记录表查询成功，共 {record_count} 条记录")
            
            # 测试日志查询
            log_count = db.query(OperationLog).count()
            print(f"✓ 日志表查询成功，共 {log_count} 条日志")
            
            return True
        finally:
            db.close()
            
    except Exception as e:
        print(f"✗ 模型测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=== 数据库调试脚本 ===")
    print(f"开始时间: {datetime.now()}")
    
    setup_logging()
    
    # 运行所有测试
    tests = [
        ("导入测试", test_imports),
        ("配置测试", test_config),
        ("数据库连接测试", test_database_connection),
        ("数据库信息测试", test_database_info),
        ("模型测试", test_models),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name}异常: {e}")
            results.append((test_name, False))
    
    # 打印总结
    print("\n=== 测试总结 ===")
    passed = 0
    failed = 0
    
    for test_name, result in results:
        if result:
            print(f"✓ {test_name}: 通过")
            passed += 1
        else:
            print(f"✗ {test_name}: 失败")
            failed += 1
    
    print(f"\n总计: {passed} 个测试通过, {failed} 个测试失败")
    print(f"结束时间: {datetime.now()}")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n🎉 所有测试通过！")

if __name__ == "__main__":
    main() 