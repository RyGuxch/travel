import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from config import Config
from database.models import db, User, Destination, Attraction, TravelPlan, Itinerary, ItineraryItem
from datetime import date, time, datetime
from werkzeug.security import generate_password_hash
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    # 初始化Flask-Migrate
    from flask_migrate import Migrate
    migrate = Migrate(app, db)
    
    return app

def init_database():
    """初始化数据库，创建表和基础数据"""
    app = create_app()
    
    # 如果不是在Railway上运行，则使用SQLite
    if not os.environ.get('RAILWAY_DEPLOYMENT'):
        logger.info("在本地环境运行数据库初始化...")
        
        with app.app_context():
            try:
                # 本地环境直接创建表
                db.create_all()
                logger.info("数据库表创建成功")
                create_sample_data()
            except Exception as e:
                logger.error(f"本地数据库初始化失败: {str(e)}")
                raise
    else:
        logger.info("在Railway环境运行数据库初始化...")
    
    with app.app_context():
        try:
                # Railway环境先执行迁移
                from flask_migrate import upgrade
                from sqlalchemy import inspect
                
                # 检查数据库连接
                logger.info("检查数据库连接...")
                db.engine.connect()
                logger.info("✅ 数据库连接成功")
                
                # 检查是否已有表
                inspector = inspect(db.engine)
                existing_tables = inspector.get_table_names()
                logger.info(f"当前数据库表数量: {len(existing_tables)}")
                
                if len(existing_tables) == 0:
                    # 数据库为空，首次部署，直接创建所有表
                    logger.info("首次部署，创建数据库表...")
                    db.create_all()
                    logger.info("✅ 数据库表创建成功")
                else:
                    # 数据库已存在，执行迁移
                    logger.info("执行数据库迁移...")
                    try:
                        upgrade()
                        logger.info("✅ 数据库迁移完成")
                    except Exception as migrate_error:
                        logger.warning(f"迁移执行失败: {migrate_error}")
                        # 迁移失败时，尝试手动修复表结构
                        logger.info("尝试手动修复表结构...")
                        try:
                            # 手动修改User表的字段长度
                            with db.engine.connect() as conn:
                                # 检查users表是否存在且字段长度不够
                                result = conn.execute("SELECT column_name, character_maximum_length FROM information_schema.columns WHERE table_name = 'users' AND column_name IN ('username', 'password_hash', 'email')")
                                columns = dict(result.fetchall())
                                
                                # 如果password_hash字段长度不够，则修改
                                if 'password_hash' in columns and columns['password_hash'] < 512:
                                    logger.info("修复password_hash字段长度...")
                                    conn.execute("ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(512)")
                                    conn.commit()
                                
                                # 如果username字段长度不够，则修改
                                if 'username' in columns and columns['username'] < 150:
                                    logger.info("修复username字段长度...")
                                    conn.execute("ALTER TABLE users ALTER COLUMN username TYPE VARCHAR(150)")
                                    conn.commit()
                                
                                # 如果email字段长度不够，则修改
                                if 'email' in columns and columns['email'] < 255:
                                    logger.info("修复email字段长度...")
                                    conn.execute("ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(255)")
                                    conn.commit()
                                
                                logger.info("✅ 手动修复完成")
                        except Exception as fix_error:
                            logger.error(f"手动修复失败: {fix_error}")
                            # 如果手动修复也失败，记录错误但继续
                
                # 验证最终表结构
                final_tables = inspector.get_table_names()
                logger.info(f"📋 最终数据库表: {len(final_tables)}个")
                for table in sorted(final_tables):
                    logger.info(f"  - {table}")
                
                # 创建示例数据
                create_sample_data()
                
            except Exception as e:
                logger.error(f"Railway数据库初始化失败: {str(e)}")
                db.session.rollback()
                raise

def create_sample_data():
    """创建示例数据"""
    try:
            # 检查是否已有用户，如果没有则创建管理员账户
            if not User.query.filter_by(username='admin').first():
            # 使用较短的密码哈希避免长度问题
                admin = User(
                    username='admin',
                password_hash=generate_password_hash('admin123'),  # 这应该生成适当长度的哈希
                    email='admin@example.com'
                )
            
            # 验证password_hash长度
            password_hash_length = len(admin.password_hash)
            logger.info(f"生成的password_hash长度: {password_hash_length}")
            
            if password_hash_length > 512:
                logger.warning(f"密码哈希长度 {password_hash_length} 超过字段限制 512，使用简化版本")
                # 如果还是太长，使用更简单的哈希方法
                admin.password_hash = generate_password_hash('admin123', method='pbkdf2:sha256', salt_length=8)
                logger.info(f"简化后的password_hash长度: {len(admin.password_hash)}")
            
                db.session.add(admin)
                logger.info("创建管理员账户")
                
            # 添加一些示例目的地
            destinations = [
                {
                    'name': '故宫', 
                    'city': '北京',
                    'province': '北京',
                    'country': '中国',
                    'latitude': 39.9163, 
                    'longitude': 116.3972,
                    'description': '中国明清两代的皇家宫殿，是中国古代宫廷建筑之精华。'
                },
                {
                    'name': '西湖',
                    'city': '杭州',
                    'province': '浙江',
                    'country': '中国',
                    'latitude': 30.2587,
                    'longitude': 120.1315,
                    'description': '中国浙江省杭州市区西部的淡水湖，国家5A级旅游景区。'
                },
                {
                    'name': '上海迪士尼乐园',
                    'city': '上海',
                    'province': '上海',
                    'country': '中国',
                    'latitude': 31.1433,
                    'longitude': 121.6572,
                    'description': '中国第一个迪士尼主题乐园，于2016年6月16日正式开园。'
                }
            ]
            
            # 检查是否已有目的地数据
            if not Destination.query.first():
                for dest_data in destinations:
                    dest = Destination(**dest_data)
                    db.session.add(dest)
                logger.info("添加示例目的地数据")
            
            # 提交更改
            db.session.commit()
        logger.info("✅ 示例数据创建完成！")
            
        except Exception as e:
        logger.error(f"创建示例数据失败: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    init_database() 