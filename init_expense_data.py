#!/usr/bin/env python
"""
初始化开销管理数据脚本
为现有用户创建默认的开销分类
"""

from app import app, db
from database.models import User, ExpenseCategory

def init_default_categories_for_all_users():
    """为所有现有用户初始化默认分类"""
    with app.app_context():
        try:
            default_categories = [
                {'name': '交通', 'icon': '🚗', 'color': '#007AFF'},
                {'name': '住宿', 'icon': '🏨', 'color': '#FF9500'},
                {'name': '餐饮', 'icon': '🍽️', 'color': '#FF3B30'},
                {'name': '门票', 'icon': '🎫', 'color': '#34C759'},
                {'name': '购物', 'icon': '🛍️', 'color': '#AF52DE'},
                {'name': '娱乐', 'icon': '🎮', 'color': '#FF2D92'},
                {'name': '其他', 'icon': '📝', 'color': '#8E8E93'}
            ]
            
            # 获取所有用户
            users = User.query.all()
            print(f"找到 {len(users)} 个用户")
            
            for user in users:
                print(f"为用户 {user.username} (ID: {user.id}) 初始化默认分类...")
                
                for cat_data in default_categories:
                    # 检查是否已存在
                    existing = ExpenseCategory.query.filter_by(
                        user_id=user.id,
                        name=cat_data['name']
                    ).first()
                    
                    if not existing:
                        category = ExpenseCategory(
                            user_id=user.id,
                            name=cat_data['name'],
                            icon=cat_data['icon'],
                            color=cat_data['color'],
                            is_default=True
                        )
                        db.session.add(category)
                        print(f"  - 添加分类: {cat_data['name']}")
                    else:
                        print(f"  - 分类已存在: {cat_data['name']}")
            
            db.session.commit()
            print("✅ 所有用户的默认分类初始化完成！")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 初始化失败: {str(e)}")

def init_single_user_categories(user_id):
    """为单个用户初始化默认分类"""
    with app.app_context():
        try:
            user = User.query.get(user_id)
            if not user:
                print(f"❌ 用户 ID {user_id} 不存在")
                return
            
            default_categories = [
                {'name': '交通', 'icon': '🚗', 'color': '#007AFF'},
                {'name': '住宿', 'icon': '🏨', 'color': '#FF9500'},
                {'name': '餐饮', 'icon': '🍽️', 'color': '#FF3B30'},
                {'name': '门票', 'icon': '🎫', 'color': '#34C759'},
                {'name': '购物', 'icon': '🛍️', 'color': '#AF52DE'},
                {'name': '娱乐', 'icon': '🎮', 'color': '#FF2D92'},
                {'name': '其他', 'icon': '📝', 'color': '#8E8E93'}
            ]
            
            print(f"为用户 {user.username} (ID: {user.id}) 初始化默认分类...")
            
            for cat_data in default_categories:
                # 检查是否已存在
                existing = ExpenseCategory.query.filter_by(
                    user_id=user.id,
                    name=cat_data['name']
                ).first()
                
                if not existing:
                    category = ExpenseCategory(
                        user_id=user.id,
                        name=cat_data['name'],
                        icon=cat_data['icon'],
                        color=cat_data['color'],
                        is_default=True
                    )
                    db.session.add(category)
                    print(f"  - 添加分类: {cat_data['name']}")
                else:
                    print(f"  - 分类已存在: {cat_data['name']}")
            
            db.session.commit()
            print(f"✅ 用户 {user.username} 的默认分类初始化完成！")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ 初始化失败: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 如果提供了用户ID参数，只为该用户初始化
        try:
            user_id = int(sys.argv[1])
            init_single_user_categories(user_id)
        except ValueError:
            print("❌ 无效的用户ID")
    else:
        # 否则为所有用户初始化
        init_default_categories_for_all_users() 