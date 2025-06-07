from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Text

db = SQLAlchemy()

class User(db.Model):
    """用户表 - 存储用户基本信息"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    travel_plans = db.relationship('TravelPlan', backref='user', lazy=True)
    # 好友关系
    friends_sent = db.relationship('Friend', 
                                foreign_keys='Friend.user_id',
                                backref='user_sent', 
                                lazy='dynamic')
    friends_received = db.relationship('Friend', 
                                     foreign_keys='Friend.friend_id',
                                     backref='user_received', 
                                     lazy='dynamic')
    # 好友请求
    friend_requests_sent = db.relationship('FriendRequest', 
                                        foreign_keys='FriendRequest.sender_id',
                                        backref='sender', 
                                        lazy='dynamic')
    friend_requests_received = db.relationship('FriendRequest', 
                                            foreign_keys='FriendRequest.receiver_id',
                                            backref='receiver', 
                                            lazy='dynamic')

class Friend(db.Model):
    """好友关系表"""
    __tablename__ = 'friends'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),)

class FriendRequest(db.Model):
    """好友请求表"""
    __tablename__ = 'friend_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('sender_id', 'receiver_id', name='unique_request'),)

class Destination(db.Model):
    """目的地表 - 存储目的地基本信息"""
    __tablename__ = 'destinations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    province = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # 关系
    attractions = db.relationship('Attraction', backref='destination', lazy=True)

class Attraction(db.Model):
    """景点表 - 存储具体景点信息"""
    __tablename__ = 'attractions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 景点类型：文化、自然、娱乐等
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    rating = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    visit_duration = db.Column(db.Integer, nullable=True)  # 建议游览时长（分钟）
    ticket_price = db.Column(db.Float, nullable=True)
    
    # 外键
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id'), nullable=False)

class TravelPlan(db.Model):
    """旅行计划表 - 存储用户的旅行计划"""
    __tablename__ = 'travel_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Integer, nullable=False)
    budget_min = db.Column(db.Float, nullable=True)
    budget_max = db.Column(db.Float, nullable=True)
    travel_theme = db.Column(db.String(150), nullable=True)
    transport_mode = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='draft')  # 状态：draft, confirmed, completed
    ai_generated = db.Column(db.Boolean, default=False)  # 是否AI生成
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 关系
    itineraries = db.relationship('Itinerary', backref='travel_plan', lazy=True, cascade='all, delete-orphan')

class Itinerary(db.Model):
    """日程表 - 存储每日行程"""
    __tablename__ = 'itineraries'
    
    id = db.Column(db.Integer, primary_key=True)
    day_number = db.Column(db.Integer, nullable=False)  # 第几天
    date = db.Column(db.Date, nullable=False)
    theme = db.Column(db.String(100), nullable=True)  # 当日主题
    notes = db.Column(db.Text, nullable=True)
    
    # 外键
    travel_plan_id = db.Column(db.Integer, db.ForeignKey('travel_plans.id'), nullable=False)
    
    # 关系
    itinerary_items = db.relationship('ItineraryItem', backref='itinerary', lazy=True, cascade='all, delete-orphan')

class ItineraryItem(db.Model):
    """日程项目表 - 存储具体的行程项目"""
    __tablename__ = 'itinerary_items'
    
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=True)
    activity_type = db.Column(db.String(50), nullable=False)  # 活动类型：visit, meal, transport, rest
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(500), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    estimated_cost = db.Column(db.Float, nullable=True)
    order_index = db.Column(db.Integer, nullable=False)  # 当日顺序
    
    # 外键
    itinerary_id = db.Column(db.Integer, db.ForeignKey('itineraries.id'), nullable=False)
    attraction_id = db.Column(db.Integer, db.ForeignKey('attractions.id'), nullable=True)  # 可选关联景点

# 多对多关系：旅行计划包含的目的地
plan_destinations = db.Table('plan_destinations',
    db.Column('travel_plan_id', db.Integer, db.ForeignKey('travel_plans.id'), primary_key=True),
    db.Column('destination_id', db.Integer, db.ForeignKey('destinations.id'), primary_key=True)
)

class TravelNote(db.Model):
    __tablename__ = 'travel_notes'
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('travel_plans.id'), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    content = db.Column(Text, nullable=True)  # 富文本HTML
    media = db.Column(Text, nullable=True)    # JSON字符串，存储图片/视频URL列表
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    plan = db.relationship('TravelPlan', backref=db.backref('notes', lazy=True)) 

class Message(db.Model):
    """聊天消息表 - 存储好友之间的聊天记录"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)  # 消息内容
    is_read = db.Column(db.Boolean, default=False)  # 是否已读
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 建立与用户的关系
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy='dynamic'))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy='dynamic'))

class Moment(db.Model):
    """动态表 - 存储用户发布的动态"""
    __tablename__ = 'moments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)  # 动态内容
    media = db.Column(db.Text, nullable=True)  # JSON字符串，存储图片/视频URL列表
    location = db.Column(db.String(500), nullable=True)  # 增加到500
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    visibility = db.Column(db.String(20), default='public')  # 可见性：public（公开）, private（仅自己可见）, friends（好友可见）
    note_id = db.Column(db.Integer, nullable=True)  # 关联的游记ID，用于游记分享
    note_title = db.Column(db.String(500), nullable=True)  # 增加到500
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 建立与用户的关系
    user = db.relationship('User', backref=db.backref('moments', lazy='dynamic'))
    
    # 建立与点赞的关系
    likes = db.relationship('MomentLike', backref='moment', lazy='dynamic', cascade='all, delete-orphan')
    
    # 建立与评论的关系
    comments = db.relationship('MomentComment', backref='moment', lazy='dynamic', cascade='all, delete-orphan')

class MomentLike(db.Model):
    """动态点赞表"""
    __tablename__ = 'moment_likes'
    
    id = db.Column(db.Integer, primary_key=True)
    moment_id = db.Column(db.Integer, db.ForeignKey('moments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 确保一个用户只能给一个动态点赞一次
    __table_args__ = (db.UniqueConstraint('moment_id', 'user_id', name='unique_moment_like'),)
    
    # 建立与用户的关系
    user = db.relationship('User', backref=db.backref('moment_likes', lazy='dynamic'))

class MomentComment(db.Model):
    """动态评论表"""
    __tablename__ = 'moment_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    moment_id = db.Column(db.Integer, db.ForeignKey('moments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)  # 评论内容
    parent_id = db.Column(db.Integer, db.ForeignKey('moment_comments.id'), nullable=True)  # 回复的评论ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 建立与用户的关系
    user = db.relationship('User', backref=db.backref('moment_comments', lazy='dynamic'))
    
    # 自引用关系，用于回复评论
    replies = db.relationship('MomentComment', backref=db.backref('parent', remote_side=[id]), lazy='dynamic') 

class Expense(db.Model):
    """开销记录表 - 存储用户的消费记录"""
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('travel_plans.id'), nullable=True)  # 可选关联旅行计划
    amount = db.Column(db.Float, nullable=False)  # 金额
    category = db.Column(db.String(50), nullable=False)  # 分类：交通、住宿、餐饮、门票、购物、其他
    description = db.Column(db.String(500), nullable=True)  # 增加到500
    merchant = db.Column(db.String(200), nullable=True)  # 增加到200
    location = db.Column(db.String(500), nullable=True)  # 增加到500
    expense_date = db.Column(db.DateTime, nullable=False)  # 消费时间
    payment_method = db.Column(db.String(50), nullable=True)  # 支付方式：微信、支付宝、现金、信用卡等
    currency = db.Column(db.String(10), default='CNY')  # 货币
    receipt_image = db.Column(db.String(1000), nullable=True)  # 增加到1000
    is_ai_extracted = db.Column(db.Boolean, default=False)  # 是否AI提取
    ai_confidence = db.Column(db.Float, nullable=True)  # AI识别置信度
    tags = db.Column(db.Text, nullable=True)  # 自定义标签，JSON格式
    notes = db.Column(db.Text, nullable=True)  # 备注
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 建立关系
    user = db.relationship('User', backref=db.backref('expenses', lazy='dynamic'))
    plan = db.relationship('TravelPlan', backref=db.backref('expenses', lazy='dynamic'))

class ExpenseBudget(db.Model):
    """预算管理表 - 存储用户的预算设置"""
    __tablename__ = 'expense_budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('travel_plans.id'), nullable=True)  # 可选关联旅行计划
    category = db.Column(db.String(50), nullable=False)  # 预算分类
    budget_amount = db.Column(db.Float, nullable=False)  # 预算金额
    spent_amount = db.Column(db.Float, default=0.0)  # 已花费金额
    period_type = db.Column(db.String(20), default='trip')  # 时间周期：trip（整个行程）、daily、monthly
    start_date = db.Column(db.Date, nullable=True)  # 开始日期
    end_date = db.Column(db.Date, nullable=True)  # 结束日期
    alert_threshold = db.Column(db.Float, default=80.0)  # 预警阈值（百分比）
    is_active = db.Column(db.Boolean, default=True)  # 是否激活
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 建立关系
    user = db.relationship('User', backref=db.backref('budgets', lazy='dynamic'))
    plan = db.relationship('TravelPlan', backref=db.backref('budgets', lazy='dynamic'))

class ExpenseCategory(db.Model):
    """开销分类管理表 - 存储用户自定义的分类"""
    __tablename__ = 'expense_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)  # 分类名称
    icon = db.Column(db.String(50), nullable=True)  # 图标
    color = db.Column(db.String(7), nullable=True)  # 颜色代码
    is_default = db.Column(db.Boolean, default=False)  # 是否默认分类
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 建立关系
    user = db.relationship('User', backref=db.backref('expense_categories', lazy='dynamic'))
    
    # 唯一约束：同一用户不能有重复的分类名
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='unique_user_category'),) 

class PushSubscription(db.Model):
    """推送订阅表 - 存储用户的Web推送订阅信息"""
    __tablename__ = 'push_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    endpoint = db.Column(db.String(500), nullable=False)  # 推送服务端点
    p256dh = db.Column(db.String(200), nullable=False)  # 公钥
    auth = db.Column(db.String(50), nullable=False)  # 认证密钥
    user_agent = db.Column(db.String(500), nullable=True)  # 用户代理字符串
    is_active = db.Column(db.Boolean, default=True)  # 是否激活
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 建立关系
    user = db.relationship('User', backref=db.backref('push_subscriptions', lazy='dynamic'))
    
    # 唯一约束：同一用户同一端点只能有一个订阅
    __table_args__ = (db.UniqueConstraint('user_id', 'endpoint', name='unique_user_subscription'),) 
