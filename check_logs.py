#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database import get_db
from models import OperationLog, User, EcoRecord
from sqlalchemy.orm import Session

def check_logs():
    """检查数据库中的操作日志"""
    try:
        # 获取数据库会话
        db = next(get_db())
        
        # 查看最近的操作日志
        logs = db.query(OperationLog).order_by(OperationLog.created_at.desc()).limit(10).all()
        print('=== 最近的操作日志 ===')
        if logs:
            for log in logs:
                user = db.query(User).filter(User.id == log.user_id).first()
                username = user.username if user else 'Unknown'
                print(f'ID: {log.id}, User: {username}({log.user_id}), Action: {log.action}, Table: {log.table_name}, Record: {log.record_id}, Time: {log.created_at}')
        else:
            print('没有找到操作日志')
        
        # 查看用户表
        users = db.query(User).all()
        print('\n=== 用户列表 ===')
        for user in users:
            print(f'ID: {user.id}, Username: {user.username}, Role: {user.role}')
        
        # 查看最近的数据记录
        records = db.query(EcoRecord).order_by(EcoRecord.created_at.desc()).limit(5).all()
        print('\n=== 最近的数据记录 ===')
        for record in records:
            creator = db.query(User).filter(User.id == record.created_by).first()
            creator_name = creator.username if creator else 'Unknown'
            print(f'ID: {record.id}, Date: {record.date}, Creator: {creator_name}({record.created_by}), Created: {record.created_at}')
        
        db.close()
        
    except Exception as e:
        print(f'检查日志时出错: {e}')

if __name__ == '__main__':
    check_logs() 