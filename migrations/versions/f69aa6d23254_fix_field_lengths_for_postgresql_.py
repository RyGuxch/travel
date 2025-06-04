"""Fix field lengths for PostgreSQL compatibility

Revision ID: f69aa6d23254
Revises: 180cce8e3d36
Create Date: 2025-01-04 14:06:36.461052

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f69aa6d23254'
down_revision = '180cce8e3d36'
branch_labels = None
depends_on = None


def upgrade():
    # 修复PostgreSQL字段长度兼容性问题
    try:
        # 修改users表的password_hash字段长度
        op.alter_column('users', 'password_hash',
                       existing_type=sa.String(256),
                       type_=sa.String(512),  # 增加到512字符
                       existing_nullable=False)
    except:
        pass  # 如果字段已经是正确长度或表不存在，忽略错误
    
    try:
        # 确保其他可能有长度问题的字段也有足够的长度
        op.alter_column('users', 'username',
                       existing_type=sa.String(80),
                       type_=sa.String(150),  # 增加用户名长度限制
                       existing_nullable=False,
                       existing_unique=True)
    except:
        pass
    
    try:
        # 修改email字段长度
        op.alter_column('users', 'email',
                       existing_type=sa.String(120),
                       type_=sa.String(255),  # 标准email长度
                       existing_nullable=True,
                       existing_unique=True)
    except:
        pass
    
    try:
        # 修改travel_plans表的title字段
        op.alter_column('travel_plans', 'title',
                       existing_type=sa.String(200),
                       type_=sa.String(500),  # 增加标题长度
                       existing_nullable=False)
    except:
        pass
    
    try:
        # 修改travel_theme和transport_mode字段
        op.alter_column('travel_plans', 'travel_theme',
                       existing_type=sa.String(100),
                       type_=sa.String(150),
                       existing_nullable=True)
    except:
        pass
    
    try:
        op.alter_column('travel_plans', 'transport_mode',
                       existing_type=sa.String(50),
                       type_=sa.String(100),
                       existing_nullable=True)
    except:
        pass
    
    try:
        # 修改itinerary_items表的字段
        op.alter_column('itinerary_items', 'title',
                       existing_type=sa.String(200),
                       type_=sa.String(500),
                       existing_nullable=False)
    except:
        pass
    
    try:
        op.alter_column('itinerary_items', 'location',
                       existing_type=sa.String(200),
                       type_=sa.String(500),
                       existing_nullable=True)
    except:
        pass
    
    try:
        # 修改expenses表的字段
        op.alter_column('expenses', 'description',
                       existing_type=sa.String(200),
                       type_=sa.String(500),
                       existing_nullable=True)
    except:
        pass
    
    try:
        op.alter_column('expenses', 'merchant',
                       existing_type=sa.String(100),
                       type_=sa.String(200),
                       existing_nullable=True)
    except:
        pass
    
    try:
        op.alter_column('expenses', 'location',
                       existing_type=sa.String(200),
                       type_=sa.String(500),
                       existing_nullable=True)
    except:
        pass
    
    try:
        op.alter_column('expenses', 'receipt_image',
                       existing_type=sa.String(500),
                       type_=sa.String(1000),  # 增加图片路径长度
                       existing_nullable=True)
    except:
        pass


def downgrade():
    # 这里不执行降级操作，因为缩短字段长度可能导致数据丢失
    pass
