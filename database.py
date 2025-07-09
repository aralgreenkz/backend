from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from config import settings
import logging
import traceback
from datetime import datetime

# 获取日志记录器
logger = logging.getLogger('ecometrics.database')

# 创建数据库引擎 - MySQL配置
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 连接前检查连接是否有效
    pool_recycle=3600,   # 连接回收时间（秒）
    pool_size=10,        # 连接池大小
    max_overflow=20,     # 最大溢出连接数
    echo=True,           # 打印SQL语句用于调试
    echo_pool=True,      # 打印连接池信息
    connect_args={
        "charset": "utf8mb4",
        "connect_timeout": 60,
        "read_timeout": 30,
        "write_timeout": 30,
    }
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

def test_database_connection():
    """测试数据库连接并返回连接信息"""
    try:
        logger.info("Testing database connection...")
        
        # 测试基本连接
        with engine.connect() as connection:
            # 执行简单查询
            result = connection.execute(text("SELECT 1 as test"))
            test_result = result.fetchone()
            
            # 获取数据库版本
            version_result = connection.execute(text("SELECT VERSION() as version"))
            db_version = version_result.fetchone()
            
            # 获取当前时间
            time_result = connection.execute(text("SELECT NOW() as db_time"))
            db_time = time_result.fetchone()
            
            # 检查数据库和表是否存在
            db_check = connection.execute(text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{settings.MYSQL_DATABASE}'"))
            db_exists = db_check.fetchone() is not None
            
            # 获取连接池状态
            pool_status = {
                "size": engine.pool.size(),
                "checked_in": engine.pool.checkedin(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow()
            }
            
            connection_info = {
                "status": "connected",
                "test_query": test_result[0] if test_result else None,
                "database_version": db_version[0] if db_version else None,
                "database_time": str(db_time[0]) if db_time else None,
                "database_exists": db_exists,
                "database_name": settings.MYSQL_DATABASE,
                "host": settings.MYSQL_HOST,
                "port": settings.MYSQL_PORT,
                "pool_status": pool_status,
                "connection_url": settings.DATABASE_URL.replace(settings.MYSQL_PASSWORD, '***') if settings.MYSQL_PASSWORD else settings.DATABASE_URL,
                "test_time": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Database connection successful: {connection_info}")
            return connection_info
            
    except SQLAlchemyError as e:
        error_info = {
            "status": "error",
            "error_type": "SQLAlchemyError",
            "error_message": str(e),
            "error_details": traceback.format_exc(),
            "database_url": settings.DATABASE_URL.replace(settings.MYSQL_PASSWORD, '***') if settings.MYSQL_PASSWORD else settings.DATABASE_URL,
            "test_time": datetime.utcnow().isoformat()
        }
        logger.error(f"Database connection failed: {error_info}")
        raise Exception(f"Database connection failed: {str(e)}")
        
    except Exception as e:
        error_info = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "error_details": traceback.format_exc(),
            "database_url": settings.DATABASE_URL.replace(settings.MYSQL_PASSWORD, '***') if settings.MYSQL_PASSWORD else settings.DATABASE_URL,
            "test_time": datetime.utcnow().isoformat()
        }
        logger.error(f"Unexpected database error: {error_info}")
        raise Exception(f"Unexpected database error: {str(e)}")

# 依赖注入：获取数据库会话
def get_db():
    """获取数据库会话，包含详细的错误处理"""
    db = None
    try:
        logger.debug("Creating database session...")
        db = SessionLocal()
        
        # 测试连接
        db.execute(text("SELECT 1"))
        logger.debug("Database session created successfully")
        
        yield db
        
    except SQLAlchemyError as e:
        logger.error(f"Database session error: {str(e)}")
        logger.error(f"Database session error details: {traceback.format_exc()}")
        if db:
            db.rollback()
        raise Exception(f"Database session error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected database session error: {str(e)}")
        logger.error(f"Unexpected database session error details: {traceback.format_exc()}")
        if db:
            db.rollback()
        raise Exception(f"Unexpected database session error: {str(e)}")
        
    finally:
        if db:
            try:
                db.close()
                logger.debug("Database session closed")
            except Exception as e:
                logger.error(f"Error closing database session: {str(e)}")

def get_db_info():
    """获取数据库详细信息"""
    try:
        with engine.connect() as connection:
            # 获取数据库基本信息
            queries = {
                "version": "SELECT VERSION() as version",
                "db_time": "SELECT NOW() as db_time",
                "database_name": f"SELECT DATABASE() as database_name",
                "connection_id": "SELECT CONNECTION_ID() as connection_id",
                "user": "SELECT USER() as user",
                "charset": "SELECT @@character_set_database as charset",
                "collation": "SELECT @@collation_database as collation"
            }
            
            info = {}
            for key, query in queries.items():
                try:
                    result = connection.execute(text(query))
                    row = result.fetchone()
                    info[key] = row[0] if row else None
                except Exception as e:
                    info[key] = f"Error: {str(e)}"
            
            # 获取表信息
            try:
                tables_result = connection.execute(text(f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{settings.MYSQL_DATABASE}'"))
                info["tables"] = [row[0] for row in tables_result.fetchall()]
            except Exception as e:
                info["tables"] = f"Error: {str(e)}"
            
            return info
            
    except Exception as e:
        logger.error(f"Error getting database info: {str(e)}")
        return {"error": str(e)} 