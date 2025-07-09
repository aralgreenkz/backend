from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import json

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)  # 明文存储
    role = Column(String(20), default="user", nullable=False)  # user, admin
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime)
    
    # 关联关系
    created_records = relationship("EcoRecord", foreign_keys="EcoRecord.created_by", back_populates="creator")
    updated_records = relationship("EcoRecord", foreign_keys="EcoRecord.updated_by", back_populates="updater")
    operation_logs = relationship("OperationLog", back_populates="user")

class EcoRecord(Base):
    __tablename__ = "eco_records"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False, index=True)  # 每天只能有一条记录
    power_consumption = Column(Numeric(10, 2), nullable=False)  # 电量消耗 kWh
    drinking_water = Column(Numeric(10, 2), nullable=False)  # 饮用水消耗 L
    irrigation_water = Column(Numeric(10, 2), nullable=False)  # 灌溉水消耗 L
    electricity_price = Column(Numeric(10, 2), nullable=False)  # 电价 KZT/kWh
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    updated_by = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关联关系
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_records")
    updater = relationship("User", foreign_keys=[updated_by], back_populates="updated_records")

class OperationLog(Base):
    __tablename__ = "operation_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(20), nullable=False, index=True)  # CREATE, UPDATE, DELETE
    table_name = Column(String(50), nullable=False)
    record_id = Column(Integer, index=True)
    old_data = Column(JSON)  # 修改前数据
    new_data = Column(JSON)  # 修改后数据
    description = Column(Text)
    ip_address = Column(String(45))  # 支持IPv6
    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    # 关联关系
    user = relationship("User", back_populates="operation_logs") 