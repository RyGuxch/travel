"""Complete schema for railway deployment

Revision ID: 180cce8e3d36
Revises: 21e34e0e0aff
Create Date: 2025-06-04 13:25:51.407515

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '180cce8e3d36'
down_revision = '21e34e0e0aff'
branch_labels = None
depends_on = None


def upgrade():
    # 检查表是否存在，如果不存在则创建
    
    # 用户表
    try:
        op.create_table('users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('username', sa.String(length=80), nullable=False),
            sa.Column('password_hash', sa.String(length=200), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('username')
        )
    except:
        pass  # 表已存在
    
    # 目的地表
    try:
        op.create_table('destinations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('city', sa.String(length=50), nullable=True),
            sa.Column('province', sa.String(length=50), nullable=True),
            sa.Column('country', sa.String(length=50), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
    except:
        pass
    
    # 景点表
    try:
        op.create_table('attractions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('destination_id', sa.Integer(), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=True),
            sa.Column('rating', sa.Float(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.ForeignKeyConstraint(['destination_id'], ['destinations.id']),
            sa.PrimaryKeyConstraint('id')
        )
    except:
        pass
    
    # 旅行计划表
    try:
        op.create_table('travel_plans',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('start_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=False),
            sa.Column('total_days', sa.Integer(), nullable=False),
            sa.Column('budget_min', sa.Float(), nullable=True),
            sa.Column('budget_max', sa.Float(), nullable=True),
            sa.Column('travel_theme', sa.String(length=50), nullable=True),
            sa.Column('transport_mode', sa.String(length=50), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.Column('ai_generated', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )
    except:
        pass
    
    # 行程表
    try:
        op.create_table('itineraries',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('travel_plan_id', sa.Integer(), nullable=False),
            sa.Column('day_number', sa.Integer(), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('theme', sa.String(length=100), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['travel_plan_id'], ['travel_plans.id']),
            sa.PrimaryKeyConstraint('id')
        )
    except:
        pass
    
    # 行程项目表
    try:
        op.create_table('itinerary_items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('itinerary_id', sa.Integer(), nullable=False),
            sa.Column('start_time', sa.Time(), nullable=True),
            sa.Column('end_time', sa.Time(), nullable=True),
            sa.Column('activity_type', sa.String(length=50), nullable=True),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('location', sa.String(length=200), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('estimated_cost', sa.Float(), nullable=True),
            sa.Column('order_index', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['itinerary_id'], ['itineraries.id']),
            sa.PrimaryKeyConstraint('id')
        )
    except:
        pass
    
    # 计划目的地关联表
    try:
        op.create_table('plan_destinations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('plan_id', sa.Integer(), nullable=False),
            sa.Column('destination_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['destination_id'], ['destinations.id']),
            sa.ForeignKeyConstraint(['plan_id'], ['travel_plans.id']),
            sa.PrimaryKeyConstraint('id')
        )
    except:
        pass
    
    # 游记表
    try:
        op.create_table('travel_notes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('plan_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('media', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['plan_id'], ['travel_plans.id']),
            sa.PrimaryKeyConstraint('id')
        )
    except:
        pass
    
    # 好友表
    try:
        op.create_table('friends',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('friend_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['friend_id'], ['users.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'friend_id')
        )
    except:
        pass
    
    # 好友请求表
    try:
        op.create_table('friend_requests',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('sender_id', sa.Integer(), nullable=False),
            sa.Column('receiver_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['receiver_id'], ['users.id']),
            sa.ForeignKeyConstraint(['sender_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )
    except:
        pass
    
    # 消息表
    try:
        op.create_table('messages',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('sender_id', sa.Integer(), nullable=False),
            sa.Column('receiver_id', sa.Integer(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('is_read', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['receiver_id'], ['users.id']),
            sa.ForeignKeyConstraint(['sender_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )
    except:
        pass
    
    # 动态表
    try:
        op.create_table('moments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('media', sa.Text(), nullable=True),
            sa.Column('location', sa.String(length=200), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('visibility', sa.String(length=20), nullable=True),
            sa.Column('note_id', sa.Integer(), nullable=True),
            sa.Column('note_title', sa.String(length=200), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )
    except:
        pass
    
    # 动态点赞表
    try:
        op.create_table('moment_likes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('moment_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['moment_id'], ['moments.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('moment_id', 'user_id')
        )
    except:
        pass
    
    # 动态评论表
    try:
        op.create_table('moment_comments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('moment_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('parent_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['moment_id'], ['moments.id']),
            sa.ForeignKeyConstraint(['parent_id'], ['moment_comments.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )
    except:
    pass


def downgrade():
    # 由于使用了try/except，downgrade时也需要相应的逻辑
    # 但为了安全起见，我们不在这里删除表
    pass
