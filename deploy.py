#!/usr/bin/env python3
"""
Railway部署脚本
用于在部署时正确处理数据库迁移和初始化
"""

import os
import sys
from flask import Flask
from flask_migrate import upgrade, init, migrate
from database.models import db


def setup_railway_deployment():
    """设置Railway部署环境"""
    
    # 设置Railway环境变量
    os.environ['RAILWAY_DEPLOYMENT'] = 'true'
    
    print("🚀 开始Railway部署设置...")
    
    # 导入应用
    from app import app
    
    with app.app_context():
        try:
            # 检查数据库连接
            print("📊 检查数据库连接...")
            db.engine.connect()
            print("✅ 数据库连接成功")
            
            # 检查alembic_version表是否存在
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'alembic_version' not in tables:
                print("🔧 首次部署，初始化迁移系统...")
                # 如果没有alembic_version表，说明是首次部署
                # 创建所有表
                db.create_all()
                print("✅ 数据库表创建完成")
                
                # 标记为最新版本
                try:
                    upgrade()
                    print("✅ 迁移系统初始化完成")
                except Exception as e:
                    print(f"⚠️  迁移系统初始化失败，但表已创建: {e}")
            else:
                print("🔄 执行数据库迁移...")
                # 执行迁移到最新版本
                upgrade()
                print("✅ 数据库迁移完成")
            
            # 验证表结构
            final_tables = inspector.get_table_names()
            print(f"📋 当前数据库表: {len(final_tables)}个")
            for table in sorted(final_tables):
                print(f"  - {table}")
            
            print("🎉 Railway部署设置完成!")
            return True
            
        except Exception as e:
            print(f"❌ 部署设置失败: {e}")
            return False


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--setup':
        success = setup_railway_deployment()
        sys.exit(0 if success else 1)
    else:
        print("使用方法: python deploy.py --setup")
        sys.exit(1)


if __name__ == '__main__':
    main() 