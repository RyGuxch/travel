import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from config import Config
from database.models import db, User, Destination, Attraction, TravelPlan, Itinerary, ItineraryItem
from datetime import date, time, datetime

def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app

def create_tables():
    """仅创建不存在的数据库表"""
    app = create_app()
    
    with app.app_context():
        # 创建不存在的表
        db.create_all()
        print("数据库表创建/更新成功")

def init_database():
    """初始化数据库"""
    app = create_app()
    
    with app.app_context():
        # 删除现有表并重新创建
        db.drop_all()
        db.create_all()
        
        # 插入示例数据
        insert_sample_data()
        
        print("数据库初始化完成！")

def insert_sample_data():
    """插入示例数据"""
    
    # 1. 创建示例用户
    user = User(
        username='demo_user',
        email='demo@example.com'
    )
    db.session.add(user)
    
    # 2. 创建目的地
    destinations = [
        Destination(
            name='北京',
            city='北京',
            province='北京市',
            country='中国',
            latitude=39.9042,
            longitude=116.4074,
            description='中国首都，历史文化名城'
        ),
        Destination(
            name='上海',
            city='上海',
            province='上海市',
            country='中国',
            latitude=31.2304,
            longitude=121.4737,
            description='国际大都市，经济中心'
        ),
        Destination(
            name='西安',
            city='西安',
            province='陕西省',
            country='中国',
            latitude=34.3416,
            longitude=108.9398,
            description='古丝绸之路起点，十三朝古都'
        )
    ]
    
    for dest in destinations:
        db.session.add(dest)
    
    db.session.commit()  # 提交以获取ID
    
    # 3. 创建景点
    attractions = [
        # 北京景点
        Attraction(
            name='故宫博物院',
            type='文化',
            latitude=39.9163,
            longitude=116.3972,
            rating=4.8,
            description='明清两代皇宫，世界文化遗产',
            visit_duration=180,
            ticket_price=60.0,
            destination_id=destinations[0].id
        ),
        Attraction(
            name='天安门广场',
            type='文化',
            latitude=39.9055,
            longitude=116.3976,
            rating=4.7,
            description='世界最大的城市广场',
            visit_duration=60,
            ticket_price=0.0,
            destination_id=destinations[0].id
        ),
        Attraction(
            name='长城（八达岭）',
            type='文化',
            latitude=40.3587,
            longitude=116.0154,
            rating=4.6,
            description='万里长城最著名段落',
            visit_duration=240,
            ticket_price=45.0,
            destination_id=destinations[0].id
        ),
        # 上海景点
        Attraction(
            name='外滩',
            type='观光',
            latitude=31.2365,
            longitude=121.4907,
            rating=4.5,
            description='上海标志性景观，万国建筑博览群',
            visit_duration=120,
            ticket_price=0.0,
            destination_id=destinations[1].id
        ),
        Attraction(
            name='东方明珠',
            type='观光',
            latitude=31.2397,
            longitude=121.4994,
            rating=4.3,
            description='上海地标性建筑',
            visit_duration=90,
            ticket_price=180.0,
            destination_id=destinations[1].id
        ),
        # 西安景点
        Attraction(
            name='兵马俑',
            type='文化',
            latitude=34.3848,
            longitude=109.2734,
            rating=4.7,
            description='世界第八大奇迹',
            visit_duration=180,
            ticket_price=120.0,
            destination_id=destinations[2].id
        ),
        Attraction(
            name='西安城墙',
            type='文化',
            latitude=34.2658,
            longitude=108.9530,
            rating=4.5,
            description='中国现存最完整的古代城垣建筑',
            visit_duration=120,
            ticket_price=54.0,
            destination_id=destinations[2].id
        )
    ]
    
    for attraction in attractions:
        db.session.add(attraction)
    
    # 4. 创建示例旅行计划
    travel_plan = TravelPlan(
        title='北京3日游',
        start_date=date(2024, 5, 1),
        end_date=date(2024, 5, 3),
        total_days=3,
        budget_min=1000.0,
        budget_max=2000.0,
        travel_theme='历史文化',
        transport_mode='高铁',
        status='draft',
        ai_generated=True,
        user_id=user.id
    )
    db.session.add(travel_plan)
    
    db.session.commit()
    
    print("示例数据插入完成！")

if __name__ == '__main__':
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == 'create':
        # 仅创建表
        create_tables()
    else:
        # 完全初始化（删除并重建）
    init_database() 