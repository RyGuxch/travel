#!/usr/bin/env python3
"""
Railway数据库字段长度修复脚本
专门用于修复PostgreSQL中字符串字段长度不足的问题
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text, inspect

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_railway_database():
    """修复Railway数据库字段长度问题"""
    
    # 获取数据库连接URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("未找到DATABASE_URL环境变量")
        return False
    
    try:
        # 创建数据库连接
        engine = create_engine(database_url)
        logger.info("✅ 数据库连接成功")
        
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            
            try:
                # 检查users表是否存在
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                logger.info(f"当前数据库表: {tables}")
                
                if 'users' in tables:
                    logger.info("找到users表，开始修复字段长度...")
                    
                    # 获取当前字段信息
                    result = conn.execute(text("""
                        SELECT column_name, character_maximum_length, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = 'users' 
                        AND column_name IN ('username', 'password_hash', 'email')
                    """))
                    
                    current_fields = {row[0]: row[1] for row in result.fetchall()}
                    logger.info(f"当前字段长度: {current_fields}")
                    
                    # 修复password_hash字段
                    if 'password_hash' in current_fields:
                        current_length = current_fields['password_hash']
                        if current_length is None or current_length < 512:
                            logger.info(f"修复password_hash字段长度: {current_length} -> 512")
                            conn.execute(text("ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(512)"))
                        else:
                            logger.info(f"password_hash字段长度已足够: {current_length}")
                    
                    # 修复username字段
                    if 'username' in current_fields:
                        current_length = current_fields['username']
                        if current_length is None or current_length < 150:
                            logger.info(f"修复username字段长度: {current_length} -> 150")
                            conn.execute(text("ALTER TABLE users ALTER COLUMN username TYPE VARCHAR(150)"))
                        else:
                            logger.info(f"username字段长度已足够: {current_length}")
                    
                    # 修复email字段
                    if 'email' in current_fields:
                        current_length = current_fields['email']
                        if current_length is None or current_length < 255:
                            logger.info(f"修复email字段长度: {current_length} -> 255")
                            conn.execute(text("ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(255)"))
                        else:
                            logger.info(f"email字段长度已足够: {current_length}")
                    
                    logger.info("✅ users表字段修复完成")
                
                # 检查并修复其他重要表的字段长度
                table_field_fixes = {
                    'travel_plans': {
                        'title': 500,
                        'travel_theme': 150,
                        'transport_mode': 100
                    },
                    'itinerary_items': {
                        'title': 500,
                        'location': 500
                    },
                    'travel_notes': {
                        'title': 500
                    },
                    'expenses': {
                        'description': 500,
                        'merchant': 200,
                        'location': 500,
                        'receipt_image': 1000
                    },
                    'moments': {
                        'location': 500,
                        'note_title': 500
                    }
                }
                
                for table_name, fields in table_field_fixes.items():
                    if table_name in tables:
                        logger.info(f"修复表 {table_name} 的字段长度...")
                        
                        # 获取当前字段信息
                        result = conn.execute(text(f"""
                            SELECT column_name, character_maximum_length 
                            FROM information_schema.columns 
                            WHERE table_name = '{table_name}' 
                            AND column_name IN ({','.join([f"'{field}'" for field in fields.keys()])})
                        """))
                        
                        current_fields = {row[0]: row[1] for row in result.fetchall()}
                        
                        for field_name, target_length in fields.items():
                            if field_name in current_fields:
                                current_length = current_fields[field_name]
                                if current_length is None or current_length < target_length:
                                    logger.info(f"修复 {table_name}.{field_name}: {current_length} -> {target_length}")
                                    conn.execute(text(f"ALTER TABLE {table_name} ALTER COLUMN {field_name} TYPE VARCHAR({target_length})"))
                
                # 提交事务
                trans.commit()
                logger.info("✅ 所有字段长度修复完成")
                
                # 验证修复结果
                logger.info("验证修复结果...")
                result = conn.execute(text("""
                    SELECT column_name, character_maximum_length 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name IN ('username', 'password_hash', 'email')
                """))
                
                final_fields = {row[0]: row[1] for row in result.fetchall()}
                logger.info(f"修复后的users表字段长度: {final_fields}")
                
                return True
                
            except Exception as e:
                # 回滚事务
                trans.rollback()
                logger.error(f"修复过程中出错，已回滚: {str(e)}")
                return False
                
    except Exception as e:
        logger.error(f"数据库连接或操作失败: {str(e)}")
        return False

if __name__ == '__main__':
    logger.info("🔧 开始修复Railway数据库字段长度...")
    
    if fix_railway_database():
        logger.info("🎉 数据库字段长度修复成功！")
        sys.exit(0)
    else:
        logger.error("❌ 数据库字段长度修复失败！")
        sys.exit(1) 