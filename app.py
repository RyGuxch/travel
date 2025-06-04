from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from config import Config
from database.models import db, User, Destination, Attraction, TravelPlan, Itinerary, ItineraryItem, TravelNote, Friend, FriendRequest, Message, Expense, ExpenseBudget, ExpenseCategory, Moment, MomentLike, MomentComment
import json
from openai import OpenAI
from datetime import datetime, date, timedelta
import requests
from math import radians, cos, sin, sqrt, atan2
from werkzeug.utils import secure_filename
import os
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from flask import redirect, url_for
import threading
import uuid
import time
from flask_migrate import Migrate
from ocr_service import ocr_service

# 任务存储
tasks = {}

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 初始化扩展
    db.init_app(app)
    CORS(app, supports_credentials=True)
    
    # 初始化Flask-Migrate
    migrate = Migrate(app, db)
    
    return app

app = create_app()

# Deepseek客户端初始化
deepseek_client = OpenAI(
    api_key=app.config['DEEPSEEK_API_KEY'],
    base_url=app.config['DEEPSEEK_BASE_URL']
)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'msg': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

def login_required_page(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index', login_required=1))
        return f(*args, **kwargs)
    return decorated_function

# 后台任务处理函数
def process_plan_generation_task(task_id, user_id, data):
    """后台处理AI生成计划任务"""
    try:
        tasks[task_id]['status'] = 'processing'
        
        # 获取用户输入，优先自定义
        destinations = data.get('destinations', [])
        days = data.get('days', 3)
        budget_min = data.get('budget_min', 0)
        budget_max = data.get('budget_max', 5000)
        theme = data.get('theme', '观光')
        transport = data.get('transport', '高铁')
        start_date_str = data.get('start_date')
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = date.today() + timedelta(days=7)  # 默认一周后开始
        
        # 获取当前登录用户
        with app.app_context():
            user = User.query.get(user_id)
            if not user:
                tasks[task_id]['status'] = 'failed'
                tasks[task_id]['error'] = '用户不存在'
                return
                
            # 构建AI提示词
            system_prompt = """
你是一个专业的旅行规划师。根据用户的输入，生成详细的旅行计划。
请以JSON格式返回计划，包含以下结构：
{
    "title": "旅行计划标题",
    "summary": "行程概要",
    "days": [
        {
            "day": 1,
            "date": "2024-05-01",
            "theme": "当日主题",
            "items": [
                {
                    "time": "09:00",
                    "activity": "参观故宫",
                    "location": "故宫博物院",
                    "duration": "3小时",
                    "cost": 60,
                    "description": "详细描述",
                    "latitude": 39.9163,
                    "longitude": 116.3972
                }
            ]
        }
    ],
    "total_cost": 1200,
    "tips": ["实用建议1", "实用建议2"]
}
"""
            
            user_prompt = f"""
请为我规划一个旅行计划：
- 目的地：{', '.join(destinations)}
- 天数：{days}天
- 预算：{budget_min}-{budget_max}元
- 主题偏好：{theme}
- 交通方式：{transport}

请生成详细的每日行程安排，包括景点参观、用餐、休息等。
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            try:
                # 调用AI API生成内容
                response = deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    response_format={'type': 'json_object'}
                )
                
                ai_result = json.loads(response.choices[0].message.content)
                
                # 创建旅行计划
                travel_plan = TravelPlan(
                    title=ai_result.get('title', f"{', '.join(destinations)}{days}日游"),
                    start_date=start_date,
                    end_date=start_date + timedelta(days=days-1),
                    total_days=days,
                    budget_min=budget_min,
                    budget_max=budget_max,
                    travel_theme=theme,
                    transport_mode=transport,
                    status='draft',
                    ai_generated=True,
                    user_id=user.id
                )
                
                db.session.add(travel_plan)
                db.session.commit()
                
                # 保存每日行程
                for day_data in ai_result.get('days', []):
                    itinerary = Itinerary(
                        day_number=day_data.get('day', 1),
                        date=start_date + timedelta(days=day_data.get('day', 1) - 1),
                        theme=day_data.get('theme', ''),
                        travel_plan_id=travel_plan.id
                    )
                    db.session.add(itinerary)
                    db.session.commit()
                    
                    # 保存行程项目
                    for idx, item in enumerate(day_data.get('items', [])):
                        itinerary_item = ItineraryItem(
                            start_time=datetime.strptime(item.get('time', '09:00'), '%H:%M').time(),
                            activity_type='visit',
                            title=item.get('activity', ''),
                            description=item.get('description', ''),
                            location=item.get('location', ''),
                            latitude=item.get('latitude'),
                            longitude=item.get('longitude'),
                            estimated_cost=item.get('cost', 0),
                            order_index=idx,
                            itinerary_id=itinerary.id
                        )
                        db.session.add(itinerary_item)
                
                db.session.commit()
                
                # 更新任务状态
                tasks[task_id]['status'] = 'completed'
                tasks[task_id]['result'] = {
                    'plan_id': travel_plan.id,
                    'plan': ai_result
                }
                
            except Exception as e:
                print(f"AI生成计划失败: {str(e)}")
                tasks[task_id]['status'] = 'failed'
                tasks[task_id]['error'] = f'生成计划失败: {str(e)}'
                
    except Exception as e:
        print(f"任务处理异常: {str(e)}")
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['error'] = f'任务处理异常: {str(e)}'

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/plans')
@login_required_page
def plans():
    """计划列表页面"""
    return render_template('plans.html')

@app.route('/about')
def about():
    """关于页面"""
    return render_template('about.html')

@app.route('/plan/<int:plan_id>')
@login_required_page
def plan_detail(plan_id):
    """计划详情页面"""
    plan = TravelPlan.query.get_or_404(plan_id)
    return render_template('plan.html', plan=plan, config=app.config)

@app.route('/shared-plan/<int:plan_id>/<share_token>')
def shared_plan_detail(plan_id, share_token):
    """公开的计划分享页面，通过分享token访问"""
    try:
        plan = TravelPlan.query.get_or_404(plan_id)
        
        # 验证分享token（简单实现：基于计划ID和用户ID的hash）
        import hashlib
        expected_token = hashlib.md5(f"{plan.id}_{plan.user_id}_travel_agent_share".encode()).hexdigest()[:8]
        
        if share_token != expected_token:
            return render_template('error.html', 
                                 title='访问被拒绝',
                                 message='分享链接无效或已过期'), 403
        
        return render_template('shared_plan.html', plan=plan, config=app.config)
        
    except Exception as e:
        return render_template('error.html', 
                             title='页面不存在',
                             message='分享的计划不存在或已被删除'), 404

@app.route('/api/destinations')
@login_required
def get_destinations():
    """获取所有目的地"""
    destinations = Destination.query.all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'city': d.city,
        'province': d.province,
        'country': d.country,
        'latitude': d.latitude,
        'longitude': d.longitude,
        'description': d.description
    } for d in destinations])

@app.route('/api/generate-plan', methods=['POST'])
@login_required
def generate_plan():
    """异步生成旅行计划，返回任务ID"""
    try:
        # 创建任务ID
        task_id = str(uuid.uuid4())
        
        # 存储任务信息
        tasks[task_id] = {
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'user_id': session['user_id'],
            'data': request.json
        }
        
        # 启动后台线程处理
        thread = threading.Thread(
            target=process_plan_generation_task,
            args=(task_id, session['user_id'], request.json)
        )
        thread.daemon = True
        thread.start()
        
        # 立即返回任务ID
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '旅行计划生成任务已提交，请稍后查询结果'
        })
        
    except Exception as e:
        print(f"提交生成计划任务失败: {str(e)}")
        return jsonify({'success': False, 'error': f'提交任务失败: {str(e)}'}), 500

@app.route('/api/task/<task_id>', methods=['GET'])
@login_required
def get_task_status(task_id):
    """获取任务状态和结果"""
    if task_id not in tasks:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    
    # 检查任务所有权
    if task.get('user_id') != session['user_id']:
        return jsonify({'success': False, 'error': '无权访问此任务'}), 403
    
    result = {
        'success': True,
        'status': task['status'],
        'created_at': task['created_at']
    }
    
    # 添加错误信息（如果有）
    if task['status'] == 'failed' and 'error' in task:
        result['error'] = task['error']
    
    # 添加结果（如果已完成）
    if task['status'] == 'completed' and 'result' in task:
        result.update(task['result'])
    
    # 清理过期任务（可选）
    if task['status'] in ['completed', 'failed']:
        # 设置结果保留时间（例如1小时）
        created_time = datetime.fromisoformat(task['created_at'])
        if (datetime.now() - created_time).total_seconds() > 3600:
            tasks.pop(task_id, None)
    
    return jsonify(result)

@app.route('/api/plans')
@login_required
def get_plans():
    """获取所有旅行计划，分为已完成和未完成（根据end_date与当前日期判断）"""
    user_id = session['user_id']
    plans = TravelPlan.query.filter_by(user_id=user_id).all()
    completed = []
    future = []
    today = date.today()
    for p in plans:
        # 动态判断状态
        plan_end_date = p.end_date if isinstance(p.end_date, date) else datetime.strptime(p.end_date, '%Y-%m-%d').date()
        if plan_end_date < today:
            status = 'completed'
        else:
            status = p.status
        plan_dict = {
        'id': p.id,
        'title': p.title,
        'start_date': p.start_date.isoformat(),
        'end_date': p.end_date.isoformat(),
        'total_days': p.total_days,
        'budget_min': p.budget_min,
        'budget_max': p.budget_max,
        'travel_theme': p.travel_theme,
        'transport_mode': p.transport_mode,
            'status': status,
        'ai_generated': p.ai_generated,
        'created_at': p.created_at.isoformat()
        }
        if status == 'completed':
            completed.append(plan_dict)
        else:
            future.append(plan_dict)
    return jsonify({
        'completed': completed,
        'future': future
    })

@app.route('/api/plan/<int:plan_id>')
@login_required
def get_plan_detail(plan_id):
    """获取计划详情"""
    user_id = session['user_id']
    plan = TravelPlan.query.filter_by(id=plan_id, user_id=user_id).first_or_404()
    today = date.today()
    # 动态判断已完成
    plan_end_date = plan.end_date if isinstance(plan.end_date, date) else datetime.strptime(plan.end_date, '%Y-%m-%d').date()
    if plan_end_date < today:
        status = 'completed'
    else:
        status = plan.status
    itineraries = []
    for itinerary in plan.itineraries:
        items = []
        for item in itinerary.itinerary_items:
            items.append({
                'id': item.id,
                'start_time': item.start_time.strftime('%H:%M'),
                'end_time': item.end_time.strftime('%H:%M') if item.end_time else None,
                'activity_type': item.activity_type,
                'title': item.title,
                'description': item.description,
                'location': item.location,
                'latitude': item.latitude,
                'longitude': item.longitude,
                'estimated_cost': item.estimated_cost,
                'order_index': item.order_index
            })
        itineraries.append({
            'id': itinerary.id,
            'day_number': itinerary.day_number,
            'date': itinerary.date.isoformat(),
            'theme': itinerary.theme,
            'notes': itinerary.notes,
            'items': sorted(items, key=lambda x: x['order_index'])
        })
    return jsonify({
        'id': plan.id,
        'title': plan.title,
        'start_date': plan.start_date.isoformat(),
        'end_date': plan.end_date.isoformat(),
        'total_days': plan.total_days,
        'budget_min': plan.budget_min,
        'budget_max': plan.budget_max,
        'travel_theme': plan.travel_theme,
        'transport_mode': plan.transport_mode,
        'status': status,
        'ai_generated': plan.ai_generated,
        'itineraries': sorted(itineraries, key=lambda x: x['day_number'])
    })

@app.route('/api/geocode')
def geocode():
    """地理编码服务"""
    address = request.args.get('address')
    if not address:
        return jsonify({'error': '地址参数缺失'}), 400
    
    try:
        # 使用高德地图API进行地理编码
        url = 'https://restapi.amap.com/v3/geocode/geo'
        params = {
            'key': app.config['AMAP_API_KEY'],
            'address': address,
            'output': 'JSON'
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] == '1' and data['geocodes']:
            location = data['geocodes'][0]['location'].split(',')
            return jsonify({
                'latitude': float(location[1]),
                'longitude': float(location[0]),
                'formatted_address': data['geocodes'][0]['formatted_address']
            })
        else:
            return jsonify({'error': '地址解析失败'}), 400
            
    except Exception as e:
        return jsonify({'error': f'地理编码失败: {str(e)}'}), 500

def merge_nearby_points(points, threshold=0.1):
    # threshold单位：公里（0.1=100米）
    if not points:
        return []
    merged = [points[0]]
    for pt in points[1:]:
        last = merged[-1]
        # 计算两点距离
        d = haversine(last, pt)
        if d < threshold:
            continue  # 距离太近，合并
        merged.append(pt)
    return merged

def haversine(p1, p2):
    # 经纬度距离计算，返回公里
    lon1, lat1 = p1
    lon2, lat2 = p2
    R = 6371.0
    dlon = radians(lon2 - lon1)
    dlat = radians(lat2 - lat1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

@app.route('/api/route-planning', methods=['POST'])
def route_planning():
    """路线规划服务"""
    data = request.json
    waypoints = data.get('waypoints', [])
    if len(waypoints) < 2:
        return jsonify({'error': '至少需要2个坐标点'}), 400
    try:
        # 合并邻近点
        merged_points = merge_nearby_points(waypoints, threshold=0.1)  # 100米内合并
        # 超过16点再抽样
        if len(merged_points) > 16:
            # 保留首尾，均匀抽样中间点
            keep = [merged_points[0]]
            n = len(merged_points) - 2
            sample_count = 14
            if n > 0:
                step = max(1, n // sample_count)
                keep += merged_points[1:-1][::step][:sample_count]
            keep.append(merged_points[-1])
            merged_points = keep
        # 重新组装参数
        origin = f"{merged_points[0][0]},{merged_points[0][1]}"
        destination = f"{merged_points[-1][0]},{merged_points[-1][1]}"
        via_points = []
        if len(merged_points) > 2:
            via_points = [f"{pt[0]},{pt[1]}" for pt in merged_points[1:-1]]
        params = {
            'key': app.config['AMAP_API_KEY'],
            'origin': origin,
            'destination': destination,
            'strategy': 0,
            'extensions': 'all',
            'output': 'json'
        }
        if via_points:
            params['waypoints'] = ';'.join(via_points)
        url = 'https://restapi.amap.com/v3/direction/driving'
        response = requests.get(url, params=params)
        data = response.json()
        if data['status'] == '1' and data['route']['paths']:
            route = data['route']['paths'][0]
            distance = float(route['distance']) / 1000
            duration = int(route['duration']) // 60
            polyline = []
            for step in route['steps']:
                if 'polyline' in step:
                    step_points = step['polyline'].split(';')
                    for point_str in step_points:
                        if ',' in point_str:
                            lng, lat = point_str.split(',')
                            polyline.append([float(lng), float(lat)])
            return jsonify({
                'success': True,
                'route': {
                    'distance': round(distance, 1),
                    'duration': duration,
                    'polyline': polyline,
                    'waypoints_count': len(merged_points)
                }
            })
        else:
            error_msg = data.get('info', '路线规划失败')
            return jsonify({'error': f'路线规划失败: {error_msg}'}), 400
    except Exception as e:
        return jsonify({'error': f'路线规划服务错误: {str(e)}'}), 500

@app.route('/api/plan/<int:plan_id>', methods=['DELETE'])
@login_required
def delete_plan(plan_id):
    """删除指定ID的旅行计划"""
    try:
        user_id = session['user_id']
        
        # 检查计划是否存在且属于当前用户
        plan = TravelPlan.query.filter_by(id=plan_id, user_id=user_id).first()
        if not plan:
            return jsonify({'success': False, 'msg': '计划不存在或无权限删除'}), 404
        
        # 删除相关联的数据
        # 1. 删除所有游记
        for note in plan.notes:
            db.session.delete(note)
        
        # 2. 删除所有行程项
        for itinerary in plan.itineraries:
            for item in itinerary.itinerary_items:
                db.session.delete(item)
            db.session.delete(itinerary)
        
        # 3. 删除相关的开销记录
        expenses = Expense.query.filter_by(plan_id=plan_id, user_id=user_id).all()
        for expense in expenses:
            db.session.delete(expense)
        
        # 4. 删除关联的动态中的note_id引用（不删除动态本身，只清除关联）
        from database.models import Moment
        moments = Moment.query.filter_by(user_id=user_id).all()
        for moment in moments:
            if moment.note_id:
                # 检查这个note_id是否属于要删除的计划
                note = TravelNote.query.filter_by(id=moment.note_id, plan_id=plan_id).first()
                if note:
                    moment.note_id = None
                    moment.note_title = None
        
        # 5. 最后删除计划本身
        db.session.delete(plan)
        
        # 提交所有更改
        db.session.commit()
        
        return jsonify({'success': True, 'msg': '计划删除成功'})
        
    except Exception as e:
        # 发生错误时回滚事务
        db.session.rollback()
        print(f"删除计划时出错: {str(e)}")
        return jsonify({'success': False, 'msg': f'删除失败: {str(e)}'}), 500

@app.route('/api/plan/<int:plan_id>/confirm', methods=['POST'])
def confirm_plan(plan_id):
    """确认计划，将status从draft改为confirmed"""
    plan = TravelPlan.query.get_or_404(plan_id)
    if plan.status != 'draft':
        return jsonify({'success': False, 'message': '该计划已确认或已完成'}), 400
    plan.status = 'confirmed'
    from datetime import datetime
    plan.updated_at = datetime.utcnow()
    from database.models import db
    db.session.commit()
    return jsonify({'success': True, 'message': '计划已确认'})

@app.route('/api/plan/<int:plan_id>', methods=['PUT'])
@login_required
def update_plan(plan_id):
    """更新旅行计划"""
    user_id = session['user_id']
    plan = TravelPlan.query.filter_by(id=plan_id, user_id=user_id).first_or_404()
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'msg': '无效的请求数据'}), 400
        
        # 更新计划基本信息
        plan.title = data.get('title', plan.title)
        plan.travel_theme = data.get('travel_theme', plan.travel_theme)
        plan.transport_mode = data.get('transport_mode', plan.transport_mode)
        plan.budget_min = data.get('budget_min', plan.budget_min)
        plan.budget_max = data.get('budget_max', plan.budget_max)
        
        # 更新日期（如果提供了）
        if 'start_date' in data and data['start_date']:
            plan.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if 'end_date' in data and data['end_date']:
            plan.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        # 更新状态
        plan.status = data.get('status', plan.status)
        plan.updated_at = datetime.utcnow()
        
        # 处理行程数据
        if 'itineraries' in data:
            # 获取已有行程的映射
            existing_itineraries = {it.day_number: it for it in plan.itineraries}
            
            for itinerary_data in data['itineraries']:
                day_number = itinerary_data.get('day_number')
                
                if day_number in existing_itineraries:
                    # 更新已有行程
                    itinerary = existing_itineraries[day_number]
                    
                    # 删除原有的所有行程项
                    for item in itinerary.itinerary_items:
                        db.session.delete(item)
                    
                    # 添加新的行程项
                    for idx, item_data in enumerate(itinerary_data.get('items', [])):
                        start_time = datetime.strptime(item_data.get('start_time', '00:00'), '%H:%M').time() if item_data.get('start_time') else None
                        end_time = datetime.strptime(item_data.get('end_time', '00:00'), '%H:%M').time() if item_data.get('end_time') else None
                        
                        new_item = ItineraryItem(
                            itinerary_id=itinerary.id,
                            title=item_data.get('title', ''),
                            start_time=start_time,
                            end_time=end_time,
                            location=item_data.get('location', ''),
                            description=item_data.get('description', ''),
                            activity_type=item_data.get('activity_type', 'visit'),
                            estimated_cost=item_data.get('estimated_cost', 0),
                            latitude=item_data.get('latitude'),
                            longitude=item_data.get('longitude'),
                            order_index=idx
                        )
                        db.session.add(new_item)
        
        db.session.commit()
        return jsonify({'success': True, 'msg': '计划更新成功'})
    
    except Exception as e:
        db.session.rollback()
        print(f"更新计划时出错: {str(e)}")
        return jsonify({'success': False, 'msg': f'更新计划时出错: {str(e)}'}), 500

@app.route('/api/plan/<int:plan_id>/notes', methods=['GET'])
@login_required
def get_notes(plan_id):
    user_id = session['user_id']
    plan = TravelPlan.query.filter_by(id=plan_id, user_id=user_id).first_or_404()
    notes = plan.notes
    return jsonify([
        {
            'id': n.id,
            'title': n.title,
            'content': n.content,
            'media': json.loads(n.media) if n.media else [],
            'created_at': n.created_at.isoformat(),
            'updated_at': n.updated_at.isoformat()
        } for n in notes
    ])

@app.route('/api/plan/<int:plan_id>/notes', methods=['POST'])
@login_required
def add_note(plan_id):
    user_id = session['user_id']
    plan = TravelPlan.query.filter_by(id=plan_id, user_id=user_id).first_or_404()
    data = request.json
    note = TravelNote(
        plan_id=plan_id,
        title=data.get('title', ''),
        content=data.get('content', ''),
        media=json.dumps(data.get('media', []))
    )
    db.session.add(note)
    db.session.commit()
    return jsonify({'success': True, 'note_id': note.id})

@app.route('/api/note/<int:note_id>', methods=['PUT'])
@login_required
def edit_note(note_id):
    user_id = session['user_id']
    note = TravelNote.query.get_or_404(note_id)
    plan = TravelPlan.query.filter_by(id=note.plan_id, user_id=user_id).first()
    if not plan:
        return jsonify({'success': False, 'msg': '无权限'}), 403
    data = request.json
    note.title = data.get('title', note.title)
    note.content = data.get('content', note.content)
    note.media = json.dumps(data.get('media', []))
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/note/<int:note_id>', methods=['DELETE'])
@login_required
def delete_note(note_id):
    user_id = session['user_id']
    note = TravelNote.query.get_or_404(note_id)
    plan = TravelPlan.query.filter_by(id=note.plan_id, user_id=user_id).first()
    if not plan:
        return jsonify({'success': False, 'msg': '无权限'}), 403
    db.session.delete(note)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/note/<int:note_id>', methods=['GET'])
@login_required
def get_note(note_id):
    user_id = session['user_id']
    note = TravelNote.query.get_or_404(note_id)
    plan = TravelPlan.query.filter_by(id=note.plan_id, user_id=user_id).first()
    if not plan:
        return jsonify({'success': False, 'msg': '无权限'}), 403
    return jsonify({
        'id': note.id,
        'title': note.title,
        'content': note.content,
        'media': json.loads(note.media) if note.media else [],
        'created_at': note.created_at.isoformat(),
        'updated_at': note.updated_at.isoformat()
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({'success': False, 'msg': '未选择文件'})
        
        if file.filename == '':
            return jsonify({'success': False, 'msg': '未选择文件'})
        
        # 检查文件类型
        allowed_extensions = {
            'image': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'],
            'video': ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv', '3gp']
        }
        
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # 判断文件类型
        file_type = None
        for type_name, extensions in allowed_extensions.items():
            if file_ext in extensions:
                file_type = type_name
                break
        
        if not file_type:
            return jsonify({
                'success': False, 
                'msg': f'不支持的文件格式。支持的格式：{", ".join([ext for exts in allowed_extensions.values() for ext in exts])}'
            })
        
        # 检查文件大小（前端也会检查，这里是后端验证）
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置到文件开头
        
        # 检查大小限制
        max_size = app.config.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024)  # 默认100MB
        if file_size > max_size:
            size_mb = max_size / (1024 * 1024)
            return jsonify({
                'success': False, 
                'msg': f'文件太大，最大支持 {size_mb:.0f}MB'
            })
        
        # 生成唯一文件名
        import time
        timestamp = int(time.time())
        unique_filename = f"{timestamp}_{filename}"
        
        # 根据文件类型选择存储目录
        if file_type == 'image':
            upload_dir = os.path.join(app.root_path, 'static', 'images')
            url_prefix = '/static/images/'
        else:  # video
            upload_dir = os.path.join(app.root_path, 'static', 'videos')
            url_prefix = '/static/videos/'
        
        # 确保目录存在
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存文件
        save_path = os.path.join(upload_dir, unique_filename)
        file.save(save_path)
        
        # 返回文件信息
        url = url_prefix + unique_filename
        return jsonify({
            'success': True, 
            'url': url,
            'filename': unique_filename,
            'file_type': file_type,
            'file_size': file_size
        })
        
    except Exception as e:
        print(f"文件上传失败: {str(e)}")
        return jsonify({'success': False, 'msg': f'上传失败: {str(e)}'})

@app.route('/notes')
@login_required_page
def notes_page():
    """游记列表页面"""
    return render_template('notes.html')

@app.route('/note/<int:note_id>')
@login_required_page
def note_detail(note_id):
    """游记详情页面 - 优化权限控制"""
    try:
        current_user_id = session['user_id']
        
        # 获取游记信息
        note = TravelNote.query.get(note_id)
        if not note:
            # 游记不存在
            return render_template('note_not_found.html', 
                                 note_id=note_id, 
                                 reason='游记不存在或已被删除')
        
        # 获取关联的旅行计划
        plan = TravelPlan.query.get(note.plan_id)
        if not plan:
            # 关联的计划不存在
            return render_template('note_not_found.html', 
                                 note_id=note_id, 
                                 reason='关联的旅行计划已被删除')
        
        # 权限检查逻辑
        is_owner = plan.user_id == current_user_id
        
        # 游记主人可以直接访问
        if is_owner:
            return render_template('note_detail.html', 
                                 note=note, 
                                 plan=plan, 
                                 is_owner=True,
                                 access_type='owner')
        
        # 非主人需要检查是否有访问权限
        # 1. 检查游记是否被分享到动态中（公开分享）
        from database.models import Moment
        shared_moment = Moment.query.filter_by(note_id=note_id).first()
        
        if shared_moment:
            # 游记已被分享，根据分享的可见性判断权限
            if shared_moment.visibility == 'public':
                # 公开分享，任何人都可以查看
                return render_template('note_detail.html', 
                                     note=note, 
                                     plan=plan, 
                                     is_owner=False,
                                     access_type='public_shared',
                                     shared_by=shared_moment.user.username)
            
            elif shared_moment.visibility == 'friends':
                # 仅好友可见，检查是否是好友关系
                from database.models import Friend
                is_friend = Friend.query.filter(
                    ((Friend.user_id == current_user_id) & (Friend.friend_id == shared_moment.user_id)) |
                    ((Friend.user_id == shared_moment.user_id) & (Friend.friend_id == current_user_id))
                ).first() is not None
                
                if is_friend:
                    return render_template('note_detail.html', 
                                         note=note, 
                                         plan=plan, 
                                         is_owner=False,
                                         access_type='friend_shared',
                                         shared_by=shared_moment.user.username)
                else:
                    # 不是好友，无权访问
                    return render_template('note_not_found.html', 
                                         note_id=note_id, 
                                         reason='您没有权限查看此游记，仅限好友访问')
            
            else:  # private
                # 私密分享，仅分享者本人可以查看
                if shared_moment.user_id == current_user_id:
                    return render_template('note_detail.html', 
                                         note=note, 
                                         plan=plan, 
                                         is_owner=False,
                                         access_type='private_shared',
                                         shared_by=shared_moment.user.username)
                else:
                    return render_template('note_not_found.html', 
                                         note_id=note_id, 
                                         reason='您没有权限查看此游记，该内容为私密分享')
        
        # 2. 如果没有分享，检查是否有其他访问权限（如好友关系）
        from database.models import Friend
        is_friend_of_owner = Friend.query.filter(
            ((Friend.user_id == current_user_id) & (Friend.friend_id == plan.user_id)) |
            ((Friend.user_id == plan.user_id) & (Friend.friend_id == current_user_id))
        ).first() is not None
        
        if is_friend_of_owner:
            # 是游记主人的好友，可以查看（需要游记主人的设置允许）
            # 这里可以根据需要添加更细致的权限控制
            return render_template('note_detail.html', 
                                 note=note, 
                                 plan=plan, 
                                 is_owner=False,
                                 access_type='friend_access',
                                 owner_name=plan.user.username)
        
        # 3. 都不满足，无权访问
        return render_template('note_not_found.html', 
                             note_id=note_id, 
                             reason='您没有权限查看此游记，该游记为私人内容')
        
    except Exception as e:
        print(f"游记详情页面加载出错: {str(e)}")
        return render_template('note_not_found.html', 
                             note_id=note_id, 
                             reason='加载游记时出现系统错误，请稍后重试')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({'success': True, 'username': user.username})
    return jsonify({'success': False, 'msg': '用户名或密码错误'})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/userinfo')
def userinfo():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'username': session.get('username')})
    else:
        return jsonify({'logged_in': False})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'success': False, 'msg': '用户名和密码不能为空'})
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'msg': '用户名已存在'})
    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True})

# 任务清理函数（可选）
def cleanup_old_tasks():
    """定期清理旧任务"""
    current_time = datetime.now()
    to_remove = []
    
    for task_id, task in tasks.items():
        created_time = datetime.fromisoformat(task['created_at'])
        # 已完成或失败的任务保留1小时
        if task['status'] in ['completed', 'failed'] and (current_time - created_time).total_seconds() > 3600:
            to_remove.append(task_id)
        # 待处理或处理中但超过2小时的任务视为失败
        elif task['status'] in ['pending', 'processing'] and (current_time - created_time).total_seconds() > 7200:
            task['status'] = 'failed'
            task['error'] = '任务处理超时'
            to_remove.append(task_id)
    
    for task_id in to_remove:
        tasks.pop(task_id, None)

# 好友管理相关API
@app.route('/friends')
@login_required_page
def friends_page():
    """好友管理页面"""
    return render_template('friends.html')

@app.route('/api/friends')
@login_required
def get_friends():
    """获取当前用户的好友列表"""
    user_id = session.get('user_id')
    
    # 获取作为发起方的好友
    friends_sent = Friend.query.filter_by(user_id=user_id).all()
    friends_sent_ids = [f.friend_id for f in friends_sent]
    
    # 获取作为接收方的好友
    friends_received = Friend.query.filter_by(friend_id=user_id).all()
    friends_received_ids = [f.user_id for f in friends_received]
    
    # 合并好友ID
    friend_ids = list(set(friends_sent_ids + friends_received_ids))
    
    # 查询好友信息
    friends = User.query.filter(User.id.in_(friend_ids)).all()
    
    return jsonify({
        'success': True,
        'friends': [{
            'id': friend.id,
            'username': friend.username
        } for friend in friends]
    })

@app.route('/api/friend-requests')
@login_required
def get_friend_requests():
    """获取当前用户收到的好友请求"""
    user_id = session.get('user_id')
    
    # 获取未处理的好友请求
    requests = FriendRequest.query.filter_by(receiver_id=user_id, status='pending').all()
    
    return jsonify({
        'success': True,
        'requests': [{
            'id': req.id,
            'sender_id': req.sender_id,
            'sender_name': User.query.get(req.sender_id).username,
            'created_at': req.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for req in requests]
    })

@app.route('/api/search-users')
@login_required
def search_users():
    """搜索用户"""
    keyword = request.args.get('keyword', '')
    if not keyword or len(keyword) < 2:
        return jsonify({
            'success': False,
            'msg': '请输入至少2个字符'
        })
    
    user_id = session.get('user_id')
    
    # 查询匹配的用户
    users = User.query.filter(
        User.username.like(f'%{keyword}%'),
        User.id != user_id  # 排除自己
    ).limit(10).all()
    
    # 获取好友ID列表
    friends_sent = Friend.query.filter_by(user_id=user_id).all()
    friends_sent_ids = [f.friend_id for f in friends_sent]
    
    friends_received = Friend.query.filter_by(friend_id=user_id).all()
    friends_received_ids = [f.user_id for f in friends_received]
    
    friend_ids = set(friends_sent_ids + friends_received_ids)
    
    # 获取已发送请求的用户ID
    sent_requests = FriendRequest.query.filter_by(
        sender_id=user_id,
        status='pending'
    ).all()
    sent_request_ids = [req.receiver_id for req in sent_requests]
    
    # 获取已接收请求的用户ID
    received_requests = FriendRequest.query.filter_by(
        receiver_id=user_id,
        status='pending'
    ).all()
    received_request_ids = [req.sender_id for req in received_requests]
    
    return jsonify({
        'success': True,
        'users': [{
            'id': user.id,
            'username': user.username,
            'is_friend': user.id in friend_ids,
            'request_sent': user.id in sent_request_ids,
            'request_received': user.id in received_request_ids
        } for user in users]
    })

@app.route('/api/send-friend-request', methods=['POST'])
@login_required
def send_friend_request():
    """发送好友请求"""
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    
    if not receiver_id:
        return jsonify({
            'success': False,
            'msg': '请求参数不完整'
        })
    
    sender_id = session.get('user_id')
    
    # 检查是否已经是好友
    is_friend = Friend.query.filter(
        ((Friend.user_id == sender_id) & (Friend.friend_id == receiver_id)) |
        ((Friend.user_id == receiver_id) & (Friend.friend_id == sender_id))
    ).first()
    
    if is_friend:
        return jsonify({
            'success': False,
            'msg': '你们已经是好友了'
        })
    
    # 检查是否已经发送过请求且未处理
    existing_request = FriendRequest.query.filter_by(
        sender_id=sender_id,
        receiver_id=receiver_id,
        status='pending'
    ).first()
    
    if existing_request:
        return jsonify({
            'success': False,
            'msg': '已经发送过好友请求，请等待对方回应'
        })
    
    # 检查是否有任何状态的好友请求记录
    any_request = FriendRequest.query.filter_by(
        sender_id=sender_id,
        receiver_id=receiver_id
    ).first()
    
    try:
        if any_request:
            # 如果有任何状态的请求，更新其状态为pending
            any_request.status = 'pending'
            any_request.updated_at = datetime.utcnow()
            db.session.commit()
        else:
            # 创建新请求
            new_request = FriendRequest(
                sender_id=sender_id,
                receiver_id=receiver_id
            )
            db.session.add(new_request)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'msg': '好友请求已发送'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'msg': f'发送请求失败: {str(e)}'
        })

@app.route('/api/respond-friend-request', methods=['POST'])
@login_required
def respond_friend_request():
    """回应好友请求"""
    data = request.get_json()
    request_id = data.get('request_id')
    action = data.get('action')  # accept 或 reject
    
    if not request_id or not action:
        return jsonify({
            'success': False,
            'msg': '请求参数不完整'
        })
    
    user_id = session.get('user_id')
    
    # 查找请求
    friend_request = FriendRequest.query.filter_by(
        id=request_id,
        receiver_id=user_id,
        status='pending'
    ).first()
    
    if not friend_request:
        return jsonify({
            'success': False,
            'msg': '好友请求不存在或已处理'
        })
    
    if action == 'accept':
        # 接受请求，创建双向好友关系
        friendship1 = Friend(
            user_id=friend_request.sender_id,
            friend_id=user_id
        )
        
        # 创建反向好友关系
        friendship2 = Friend(
            user_id=user_id,
            friend_id=friend_request.sender_id
        )
        
        try:
            # 更新请求状态
            friend_request.status = 'accepted'
            db.session.add(friendship1)
            db.session.add(friendship2)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'msg': '已添加为好友'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'msg': f'添加好友失败: {str(e)}'
            })
    elif action == 'reject':
        # 拒绝请求
        friend_request.status = 'rejected'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'msg': '已拒绝好友请求'
        })
    else:
        return jsonify({
            'success': False,
            'msg': '无效的操作'
        })

@app.route('/api/delete-friend', methods=['POST'])
@login_required
def delete_friend():
    """删除好友"""
    friend_id = request.json.get('friend_id')
    if not friend_id:
        return jsonify({'success': False, 'msg': '参数错误'})
    
    # 找到双向的好友关系
    friend_relation1 = Friend.query.filter_by(user_id=session['user_id'], friend_id=friend_id).first()
    friend_relation2 = Friend.query.filter_by(user_id=friend_id, friend_id=session['user_id']).first()
    
    if not friend_relation1 or not friend_relation2:
        return jsonify({'success': False, 'msg': '好友关系不存在'})
    
    try:
        # 删除好友关系
        db.session.delete(friend_relation1)
        db.session.delete(friend_relation2)
        
        # 同时删除与该好友的聊天记录
        from database.models import Message
        messages = Message.query.filter(
            ((Message.sender_id == session['user_id']) & (Message.receiver_id == friend_id)) |
            ((Message.sender_id == friend_id) & (Message.receiver_id == session['user_id']))
        ).all()
        
        for message in messages:
            db.session.delete(message)
        
        # 将好友请求记录标记为已删除状态
        from database.models import FriendRequest
        friend_requests = FriendRequest.query.filter(
            ((FriendRequest.sender_id == session['user_id']) & (FriendRequest.receiver_id == friend_id)) |
            ((FriendRequest.sender_id == friend_id) & (FriendRequest.receiver_id == session['user_id']))
        ).all()
        
        for req in friend_requests:
            req.status = 'deleted'  # 使用特殊状态表示已删除好友
            req.updated_at = datetime.utcnow()
        
        db.session.commit()
        return jsonify({'success': True, 'msg': '好友删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': f'删除失败：{str(e)}'}), 500

# 聊天相关API
@app.route('/chat/<int:friend_id>')
@login_required_page
def chat_page(friend_id):
    """聊天页面"""
    friend = User.query.get_or_404(friend_id)
    # 检查是否是好友关系（双向检查）
    is_friend = Friend.query.filter(
        ((Friend.user_id == session['user_id']) & (Friend.friend_id == friend_id)) |
        ((Friend.user_id == friend_id) & (Friend.friend_id == session['user_id']))
    ).first() is not None
    
    if not is_friend:
        return redirect(url_for('friends_page'))
    
    return render_template('chat.html', friend=friend)

@app.route('/api/messages/<int:friend_id>')
@login_required
def get_messages(friend_id):
    """获取与指定好友的聊天记录"""
    from database.models import Message
    
    # 验证是否是好友关系（双向检查）
    is_friend = Friend.query.filter(
        ((Friend.user_id == session['user_id']) & (Friend.friend_id == friend_id)) |
        ((Friend.user_id == friend_id) & (Friend.friend_id == session['user_id']))
    ).first() is not None
    
    if not is_friend:
        return jsonify({'success': False, 'msg': '非好友关系'})
    
    # 获取与该好友的所有聊天记录（发送和接收的）
    messages = Message.query.filter(
        ((Message.sender_id == session['user_id']) & (Message.receiver_id == friend_id)) |
        ((Message.sender_id == friend_id) & (Message.receiver_id == session['user_id']))
    ).order_by(Message.created_at).all()
    
    # 将获取的消息标记为已读
    unread_messages = Message.query.filter_by(
        sender_id=friend_id, 
        receiver_id=session['user_id'], 
        is_read=False
    ).all()
    
    for msg in unread_messages:
        msg.is_read = True
    
    db.session.commit()
    
    # 格式化消息
    messages_data = [{
        'id': msg.id,
        'sender_id': msg.sender_id,
        'receiver_id': msg.receiver_id,
        'content': msg.content,
        'is_self': msg.sender_id == session['user_id'],
        'timestamp': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for msg in messages]
    
    return jsonify({
        'success': True, 
        'messages': messages_data,
        'friend': {
            'id': friend_id,
            'username': User.query.get(friend_id).username
        }
    })

@app.route('/api/send-message', methods=['POST'])
@login_required
def send_message():
    """发送消息"""
    from database.models import Message
    
    receiver_id = request.json.get('receiver_id')
    content = request.json.get('content')
    
    if not receiver_id or not content or not content.strip():
        return jsonify({'success': False, 'msg': '参数错误'})
    
    # 验证是否是好友关系（双向检查）
    is_friend = Friend.query.filter(
        ((Friend.user_id == session['user_id']) & (Friend.friend_id == receiver_id)) |
        ((Friend.user_id == receiver_id) & (Friend.friend_id == session['user_id']))
    ).first() is not None
    
    if not is_friend:
        return jsonify({'success': False, 'msg': '非好友关系'})
    
    # 创建新消息
    message = Message(
        sender_id=session['user_id'],
        receiver_id=receiver_id,
        content=content
    )
    
    try:
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'msg': '发送成功',
            'message': {
                'id': message.id,
                'sender_id': message.sender_id,
                'receiver_id': message.receiver_id,
                'content': message.content,
                'is_self': True,
                'timestamp': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': f'发送失败：{str(e)}'}), 500

@app.route('/api/unread-messages')
@login_required
def get_unread_messages_count():
    """获取未读消息数量"""
    from database.models import Message
    
    # 按发送者分组统计未读消息
    unread_counts = db.session.query(
        Message.sender_id, 
        db.func.count(Message.id).label('count')
    ).filter_by(
        receiver_id=session['user_id'], 
        is_read=False
    ).group_by(Message.sender_id).all()
    
    # 转换为前端所需格式
    result = {
        'total': sum(count for _, count in unread_counts),
        'by_sender': {sender_id: count for sender_id, count in unread_counts}
    }
    
    return jsonify({'success': True, 'unread': result})

# 动态相关路由和API
@app.route('/moments')
@login_required_page
def moments_page():
    """动态页面"""
    return render_template('moments.html')

@app.route('/api/moments', methods=['GET'])
@login_required
def get_moments():
    """获取动态列表"""
    from database.models import Moment, MomentLike, MomentComment, Friend
    
    user_id = session['user_id']
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    filter_type = request.args.get('filter', 'all')  # all, friends, mine
    
    # 获取所有好友ID
    friends_sent = Friend.query.filter_by(user_id=user_id).all()
    friends_sent_ids = [f.friend_id for f in friends_sent]
    
    friends_received = Friend.query.filter_by(friend_id=user_id).all()
    friends_received_ids = [f.user_id for f in friends_received]
    
    friend_ids = list(set(friends_sent_ids + friends_received_ids))
    
    # 根据筛选类型构建查询
    if filter_type == 'mine':
        # 只查看自己的动态
        query = Moment.query.filter_by(user_id=user_id)
    elif filter_type == 'friends':
        # 查看好友的动态（好友可见或公开）
        query = Moment.query.filter(
            Moment.user_id.in_(friend_ids),
            Moment.visibility.in_(['public', 'friends'])
        )
    else:  # all
        # 查看所有可见动态：自己的所有动态 + 好友的好友可见/公开动态 + 其他人的公开动态
        query = Moment.query.filter(
            db.or_(
                Moment.user_id == user_id,  # 自己的所有动态
                db.and_(
                    Moment.user_id.in_(friend_ids),  # 好友的动态
                    Moment.visibility.in_(['public', 'friends'])  # 可见性为公开或好友可见
                ),
                db.and_(
                    ~Moment.user_id.in_(friend_ids + [user_id]),  # 非好友且非自己的动态
                    Moment.visibility == 'public'  # 可见性为公开
                )
            )
        )
    
    # 按时间倒序排序
    query = query.order_by(Moment.created_at.desc())
    
    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    moments = pagination.items
    
    # 格式化结果
    result = []
    for moment in moments:
        # 检查当前用户是否点赞
        is_liked = MomentLike.query.filter_by(
            moment_id=moment.id,
            user_id=user_id
        ).first() is not None
        
        # 获取评论数量
        comment_count = MomentComment.query.filter_by(moment_id=moment.id).count()
        
        # 获取点赞数量
        like_count = MomentLike.query.filter_by(moment_id=moment.id).count()
        
        # 确定用户关系
        is_self = moment.user_id == user_id
        is_friend = moment.user_id in friend_ids
        
        # 格式化媒体数据
        media = json.loads(moment.media) if moment.media else []
        
        moment_data = {
            'id': moment.id,
            'user_id': moment.user_id,
            'username': moment.user.username,
            'content': moment.content,
            'media': media,
            'location': moment.location,
            'latitude': moment.latitude,
            'longitude': moment.longitude,
            'visibility': moment.visibility,
            'note_id': moment.note_id,  # 添加关联的游记ID
            'note_title': moment.note_title,  # 添加关联的游记标题
            'created_at': moment.created_at.isoformat(),
            'updated_at': moment.updated_at.isoformat(),
            'is_liked': is_liked,
            'like_count': like_count,
            'comment_count': comment_count,
            'is_self': is_self,
            'is_friend': is_friend,
            'comments': []
        }
        result.append(moment_data)
    
    # 返回分页信息
    return jsonify({
        'success': True,
        'moments': result,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })

@app.route('/api/moments', methods=['POST'])
@login_required
def create_moment():
    """创建新动态"""
    from database.models import Moment
    
    data = request.json
    if not data or 'content' not in data or not data['content'].strip():
        return jsonify({'success': False, 'msg': '动态内容不能为空'}), 400
    
    try:
        # 创建新动态
        moment = Moment(
            user_id=session['user_id'],
            content=data['content'],
            media=json.dumps(data.get('media', [])),
            location=data.get('location'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            visibility=data.get('visibility', 'public'),  # 默认公开
            note_id=data.get('note_id'),  # 添加关联的游记ID
            note_title=data.get('note_title')  # 添加关联的游记标题
        )
        
        db.session.add(moment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'msg': '动态发布成功',
            'moment_id': moment.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': f'发布动态失败：{str(e)}'}), 500

@app.route('/api/moments/<int:moment_id>', methods=['GET'])
@login_required
def get_moment_detail(moment_id):
    """获取动态详情"""
    from database.models import Moment, MomentLike, MomentComment, Friend
    
    user_id = session['user_id']
    
    # 获取动态
    moment = Moment.query.get_or_404(moment_id)
    
    # 获取好友ID列表
    friends_sent = Friend.query.filter_by(user_id=user_id).all()
    friends_sent_ids = [f.friend_id for f in friends_sent]
    
    friends_received = Friend.query.filter_by(friend_id=user_id).all()
    friends_received_ids = [f.user_id for f in friends_received]
    
    friend_ids = list(set(friends_sent_ids + friends_received_ids))
    
    # 检查权限
    if moment.user_id != user_id:
        if moment.visibility == 'private':
            return jsonify({'success': False, 'msg': '无权查看该动态'}), 403
        if moment.visibility == 'friends' and moment.user_id not in friend_ids:
            return jsonify({'success': False, 'msg': '无权查看该动态'}), 403
    
    # 检查当前用户是否点赞
    is_liked = MomentLike.query.filter_by(
        moment_id=moment.id,
        user_id=user_id
    ).first() is not None
    
    # 获取评论数量
    comment_count = MomentComment.query.filter_by(moment_id=moment.id).count()
    
    # 获取点赞数量
    like_count = MomentLike.query.filter_by(moment_id=moment.id).count()
    
    # 获取所有评论
    comments = MomentComment.query.filter_by(
        moment_id=moment.id,
        parent_id=None  # 只获取顶级评论
    ).order_by(MomentComment.created_at.asc()).all()
    
    comments_data = []
    for comment in comments:
        # 获取评论的回复
        replies = MomentComment.query.filter_by(
            parent_id=comment.id
        ).order_by(MomentComment.created_at.asc()).all()
        
        replies_data = [{
            'id': reply.id,
            'user_id': reply.user_id,
            'username': reply.user.username,
            'content': reply.content,
            'created_at': reply.created_at.isoformat()
        } for reply in replies]
        
        comments_data.append({
            'id': comment.id,
            'user_id': comment.user_id,
            'username': comment.user.username,
            'content': comment.content,
            'created_at': comment.created_at.isoformat(),
            'replies': replies_data
        })
    
    # 确定用户关系
    is_self = moment.user_id == user_id
    is_friend = moment.user_id in friend_ids
    
    # 格式化媒体数据
    media = json.loads(moment.media) if moment.media else []
    
    moment_data = {
        'id': moment.id,
        'user_id': moment.user_id,
        'username': moment.user.username,
        'content': moment.content,
        'media': media,
        'location': moment.location,
        'latitude': moment.latitude,
        'longitude': moment.longitude,
        'visibility': moment.visibility,
        'note_id': moment.note_id,  # 添加关联的游记ID
        'note_title': moment.note_title,  # 添加关联的游记标题
        'created_at': moment.created_at.isoformat(),
        'updated_at': moment.updated_at.isoformat(),
        'is_liked': is_liked,
        'like_count': like_count,
        'comment_count': comment_count,
        'is_self': is_self,
        'is_friend': is_friend,
        'comments': comments_data
    }
    
    return jsonify({
        'success': True,
        'moment': moment_data
    })

@app.route('/api/moments/<int:moment_id>', methods=['PUT'])
@login_required
def update_moment(moment_id):
    """更新动态"""
    from database.models import Moment
    
    user_id = session['user_id']
    
    # 获取动态
    moment = Moment.query.get_or_404(moment_id)
    
    # 检查权限
    if moment.user_id != user_id:
        return jsonify({'success': False, 'msg': '无权修改该动态'}), 403
    
    data = request.json
    if not data or 'content' not in data or not data['content'].strip():
        return jsonify({'success': False, 'msg': '动态内容不能为空'}), 400
    
    try:
        # 更新动态
        moment.content = data['content']
        moment.media = json.dumps(data.get('media', []))
        moment.location = data.get('location')
        moment.latitude = data.get('latitude')
        moment.longitude = data.get('longitude')
        moment.visibility = data.get('visibility', moment.visibility)
        # 保留游记关联信息，不允许通过编辑修改
        # moment.note_id 和 moment.note_title 保持不变
        moment.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'msg': '动态更新成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': f'更新动态失败：{str(e)}'}), 500

@app.route('/api/moments/<int:moment_id>', methods=['DELETE'])
@login_required
def delete_moment(moment_id):
    """删除动态"""
    from database.models import Moment
    
    user_id = session['user_id']
    
    # 获取动态
    moment = Moment.query.get_or_404(moment_id)
    
    # 检查权限
    if moment.user_id != user_id:
        return jsonify({'success': False, 'msg': '无权删除该动态'}), 403
    
    try:
        db.session.delete(moment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'msg': '动态删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': f'删除动态失败：{str(e)}'}), 500

@app.route('/api/moments/<int:moment_id>/like', methods=['POST'])
@login_required
def like_moment(moment_id):
    """点赞动态"""
    from database.models import Moment, MomentLike, Friend
    
    user_id = session['user_id']
    
    # 获取动态
    moment = Moment.query.get_or_404(moment_id)
    
    # 获取好友ID列表
    friends_sent = Friend.query.filter_by(user_id=user_id).all()
    friends_sent_ids = [f.friend_id for f in friends_sent]
    
    friends_received = Friend.query.filter_by(friend_id=user_id).all()
    friends_received_ids = [f.user_id for f in friends_received]
    
    friend_ids = list(set(friends_sent_ids + friends_received_ids))
    
    # 检查权限
    if moment.user_id != user_id:
        if moment.visibility == 'private':
            return jsonify({'success': False, 'msg': '无权操作该动态'}), 403
        if moment.visibility == 'friends' and moment.user_id not in friend_ids:
            return jsonify({'success': False, 'msg': '无权操作该动态'}), 403
    
    # 检查是否已点赞
    existing_like = MomentLike.query.filter_by(
        moment_id=moment_id,
        user_id=user_id
    ).first()
    
    if existing_like:
        return jsonify({'success': False, 'msg': '已经点赞过该动态'}), 400
    
    try:
        # 创建点赞记录
        like = MomentLike(
            moment_id=moment_id,
            user_id=user_id
        )
        
        db.session.add(like)
        db.session.commit()
        
        # 获取最新点赞数
        like_count = MomentLike.query.filter_by(moment_id=moment_id).count()
        
        return jsonify({
            'success': True,
            'msg': '点赞成功',
            'like_count': like_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': f'点赞失败：{str(e)}'}), 500

@app.route('/api/moments/<int:moment_id>/unlike', methods=['POST'])
@login_required
def unlike_moment(moment_id):
    """取消点赞动态"""
    from database.models import MomentLike
    
    user_id = session['user_id']
    
    # 检查是否已点赞
    like = MomentLike.query.filter_by(
        moment_id=moment_id,
        user_id=user_id
    ).first()
    
    if not like:
        return jsonify({'success': False, 'msg': '尚未点赞该动态'}), 400
    
    try:
        db.session.delete(like)
        db.session.commit()
        
        # 获取最新点赞数
        like_count = MomentLike.query.filter_by(moment_id=moment_id).count()
        
        return jsonify({
            'success': True,
            'msg': '取消点赞成功',
            'like_count': like_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': f'取消点赞失败：{str(e)}'}), 500

@app.route('/api/moments/<int:moment_id>/comments', methods=['POST'])
@login_required
def comment_moment(moment_id):
    """评论动态"""
    from database.models import Moment, MomentComment, Friend
    
    user_id = session['user_id']
    
    # 获取动态
    moment = Moment.query.get_or_404(moment_id)
    
    # 获取好友ID列表
    friends_sent = Friend.query.filter_by(user_id=user_id).all()
    friends_sent_ids = [f.friend_id for f in friends_sent]
    
    friends_received = Friend.query.filter_by(friend_id=user_id).all()
    friends_received_ids = [f.user_id for f in friends_received]
    
    friend_ids = list(set(friends_sent_ids + friends_received_ids))
    
    # 检查权限
    if moment.user_id != user_id:
        if moment.visibility == 'private':
            return jsonify({'success': False, 'msg': '无权操作该动态'}), 403
        if moment.visibility == 'friends' and moment.user_id not in friend_ids:
            return jsonify({'success': False, 'msg': '无权操作该动态'}), 403
    
    data = request.json
    if not data or 'content' not in data or not data['content'].strip():
        return jsonify({'success': False, 'msg': '评论内容不能为空'}), 400
    
    try:
        # 创建评论
        comment = MomentComment(
            moment_id=moment_id,
            user_id=user_id,
            content=data['content'],
            parent_id=data.get('parent_id')  # 回复评论的ID，可为空
        )
        
        db.session.add(comment)
        db.session.commit()
        
        # 格式化评论数据
        comment_data = {
            'id': comment.id,
            'user_id': comment.user_id,
            'username': comment.user.username,
            'content': comment.content,
            'created_at': comment.created_at.isoformat(),
            'replies': []
        }
        
        # 获取最新评论数
        comment_count = MomentComment.query.filter_by(moment_id=moment_id).count()
        
        return jsonify({
            'success': True,
            'msg': '评论成功',
            'comment': comment_data,
            'comment_count': comment_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': f'评论失败：{str(e)}'}), 500

@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """删除评论"""
    from database.models import MomentComment
    
    user_id = session['user_id']
    
    # 获取评论
    comment = MomentComment.query.get_or_404(comment_id)
    
    # 检查权限（只能删除自己的评论）
    if comment.user_id != user_id:
        return jsonify({'success': False, 'msg': '无权删除该评论'}), 403
    
    moment_id = comment.moment_id
    
    try:
        # 递归删除所有回复
        def delete_replies(comment_id):
            replies = MomentComment.query.filter_by(parent_id=comment_id).all()
            for reply in replies:
                delete_replies(reply.id)
                db.session.delete(reply)
        
        delete_replies(comment_id)
        db.session.delete(comment)
        db.session.commit()
        
        # 获取最新评论数
        comment_count = MomentComment.query.filter_by(moment_id=moment_id).count()
        
        return jsonify({
            'success': True,
            'msg': '评论删除成功',
            'comment_count': comment_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'msg': f'删除评论失败：{str(e)}'}), 500

# ========================= 开销管理 API =========================

@app.route('/expenses')
@login_required_page
def expenses_page():
    """开销管理页面"""
    return render_template('expenses.html')

@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses():
    """获取开销记录列表"""
    try:
        user_id = session['user_id']
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        category = request.args.get('category', '')
        plan_id = request.args.get('plan_id', '')
        
        # 构建查询
        query = Expense.query.filter_by(user_id=user_id)
        
        if category:
            query = query.filter_by(category=category)
        
        if plan_id:
            query = query.filter_by(plan_id=plan_id)
        
        # 按时间倒序排列
        query = query.order_by(Expense.expense_date.desc())
        
        # 分页
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        expenses = []
        for expense in pagination.items:
            expenses.append({
                'id': expense.id,
                'amount': expense.amount,
                'category': expense.category,
                'description': expense.description,
                'merchant': expense.merchant,
                'location': expense.location,
                'expense_date': expense.expense_date.isoformat() if expense.expense_date else None,
                'payment_method': expense.payment_method,
                'currency': expense.currency,
                'is_ai_extracted': expense.is_ai_extracted,
                'ai_confidence': expense.ai_confidence,
                'notes': expense.notes,
                'plan_id': expense.plan_id,
                'created_at': expense.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'expenses': expenses,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
            'total_pages': pagination.pages
        })
        
    except Exception as e:
        print(f"获取开销列表失败: {str(e)}")
        return jsonify({'success': False, 'msg': f'获取开销列表失败: {str(e)}'}), 500

@app.route('/api/expenses', methods=['POST'])
@login_required
def add_expense():
    """添加开销记录"""
    try:
        user_id = session['user_id']
        
        # 获取表单数据，添加空值检查
        amount_str = request.form.get('amount')
        if not amount_str or amount_str.strip() == '':
            return jsonify({'success': False, 'msg': '金额不能为空'}), 400
        
        try:
            amount = float(amount_str)
            if amount <= 0:
                return jsonify({'success': False, 'msg': '金额必须大于0'}), 400
        except ValueError:
            return jsonify({'success': False, 'msg': '金额格式不正确'}), 400
        
        category = request.form.get('category')
        if not category:
            return jsonify({'success': False, 'msg': '分类不能为空'}), 400
        
        description = request.form.get('description', '')
        merchant = request.form.get('merchant', '')
        location = request.form.get('location', '')
        expense_date_str = request.form.get('expense_date')
        payment_method = request.form.get('payment_method', '')
        plan_id = request.form.get('plan_id')
        notes = request.form.get('notes', '')
        receipt_image = request.form.get('receipt_image', '')
        is_ai_extracted = request.form.get('is_ai_extracted', 'false').lower() == 'true'
        
        ai_confidence_str = request.form.get('ai_confidence', '0')
        try:
            ai_confidence = float(ai_confidence_str) if ai_confidence_str else 0
        except ValueError:
            ai_confidence = 0
        
        # 解析日期
        if expense_date_str:
            try:
                expense_date = datetime.fromisoformat(expense_date_str)
            except ValueError:
                return jsonify({'success': False, 'msg': '日期格式不正确'}), 400
        else:
            expense_date = datetime.now()
        
        # 创建开销记录
        expense = Expense(
            user_id=user_id,
            plan_id=int(plan_id) if plan_id and plan_id.strip() else None,
            amount=amount,
            category=category,
            description=description,
            merchant=merchant,
            location=location,
            expense_date=expense_date,
            payment_method=payment_method,
            receipt_image=receipt_image,
            is_ai_extracted=is_ai_extracted,
            ai_confidence=ai_confidence,
            notes=notes
        )
        
        db.session.add(expense)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'msg': '开销记录保存成功',
            'expense_id': expense.id
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'msg': f'数据格式错误: {str(e)}'}), 400
    except Exception as e:
        print(f"保存开销记录失败: {str(e)}")
        return jsonify({'success': False, 'msg': f'保存开销记录失败: {str(e)}'}), 500

@app.route('/api/expenses/upload-receipt', methods=['POST'])
@login_required
def upload_receipt():
    """上传并识别支付截图"""
    try:
        if 'receipt' not in request.files:
            return jsonify({'success': False, 'msg': '未找到上传文件'}), 400
        
        file = request.files['receipt']
        if file.filename == '':
            return jsonify({'success': False, 'msg': '未选择文件'}), 400
        
        if file and allowed_file(file.filename):
            # 保存文件
            filename = secure_filename(file.filename)
            timestamp = int(time.time())
            filename = f"{timestamp}_{filename}"
            
            # 确保上传目录存在
            upload_dir = os.path.join(app.static_folder, 'uploads', 'receipts')
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # 获取相对路径用于存储
            relative_path = f"/static/uploads/receipts/{filename}"
            
            # 调用AI识别（这里简化处理，实际应该调用OCR服务）
            recognition_result = ocr_service.recognize_payment_receipt(file_path)
            recognition_result['receipt_image'] = relative_path
            
            return jsonify({
                'success': True,
                'msg': '上传成功',
                'data': recognition_result
            })
        else:
            return jsonify({'success': False, 'msg': '不支持的文件格式'}), 400
            
    except Exception as e:
        print(f"上传截图失败: {str(e)}")
        return jsonify({'success': False, 'msg': f'上传截图失败: {str(e)}'}), 500

@app.route('/api/expenses/stats', methods=['GET'])
@login_required
def get_expense_stats():
    """获取开销统计数据"""
    try:
        user_id = session['user_id']
        
        # 获取本月统计
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        
        monthly_expenses = db.session.query(Expense).filter(
            Expense.user_id == user_id,
            Expense.expense_date >= start_of_month
        ).all()
        
        # 计算统计数据
        monthly_total = sum(expense.amount for expense in monthly_expenses)
        monthly_count = len(monthly_expenses)
        daily_average = monthly_total / now.day if now.day > 0 else 0
        
        # 获取主要分类
        category_stats = {}
        for expense in monthly_expenses:
            category = expense.category
            if category in category_stats:
                category_stats[category] += expense.amount
            else:
                category_stats[category] = expense.amount
        
        top_category = max(category_stats.keys(), key=lambda k: category_stats[k]) if category_stats else None
        
        return jsonify({
            'success': True,
            'stats': {
                'monthly_total': round(monthly_total, 2),
                'monthly_count': monthly_count,
                'daily_average': round(daily_average, 2),
                'top_category': top_category,
                'category_breakdown': category_stats
            }
        })
        
    except Exception as e:
        print(f"获取统计数据失败: {str(e)}")
        return jsonify({'success': False, 'msg': f'获取统计数据失败: {str(e)}'}), 500

@app.route('/api/expenses/<int:expense_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def handle_expense(expense_id):
    """处理单个开销记录的获取、更新、删除操作"""
    if request.method == 'GET':
        # 获取开销详情
        try:
            user_id = session['user_id']
            expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
            
            if not expense:
                return jsonify({'success': False, 'msg': '开销记录不存在'}), 404
            
            return jsonify({
                'success': True,
                'expense': {
                    'id': expense.id,
                    'amount': expense.amount,
                    'category': expense.category,
                    'description': expense.description,
                    'merchant': expense.merchant,
                    'location': expense.location,
                    'expense_date': expense.expense_date.isoformat(),
                    'payment_method': expense.payment_method,
                    'plan_id': expense.plan_id,
                    'receipt_image': expense.receipt_image,
                    'is_ai_extracted': expense.is_ai_extracted,
                    'ai_confidence': expense.ai_confidence,
                    'notes': expense.notes,
                    'created_at': expense.created_at.isoformat(),
                    'updated_at': expense.updated_at.isoformat() if expense.updated_at else None
                }
            })
            
        except Exception as e:
            print(f"获取开销详情失败: {str(e)}")
            return jsonify({'success': False, 'msg': f'获取开销详情失败: {str(e)}'}), 500
    
    elif request.method == 'PUT':
        # 更新开销记录
        try:
            user_id = session['user_id']
            expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
            
            if not expense:
                return jsonify({'success': False, 'msg': '开销记录不存在'}), 404
            
            # 更新金额字段，添加空值检查
            amount_str = request.form.get('amount')
            if amount_str:
                try:
                    amount = float(amount_str)
                    if amount <= 0:
                        return jsonify({'success': False, 'msg': '金额必须大于0'}), 400
                    expense.amount = amount
                except ValueError:
                    return jsonify({'success': False, 'msg': '金额格式不正确'}), 400
            
            # 更新其他字段
            category = request.form.get('category')
            if category:
                expense.category = category
            
            expense.description = request.form.get('description', expense.description)
            expense.merchant = request.form.get('merchant', expense.merchant)
            expense.location = request.form.get('location', expense.location)
            expense.payment_method = request.form.get('payment_method', expense.payment_method)
            expense.notes = request.form.get('notes', expense.notes)
            
            expense_date_str = request.form.get('expense_date')
            if expense_date_str:
                try:
                    expense.expense_date = datetime.fromisoformat(expense_date_str)
                except ValueError:
                    return jsonify({'success': False, 'msg': '日期格式不正确'}), 400
            
            plan_id = request.form.get('plan_id')
            expense.plan_id = int(plan_id) if plan_id and plan_id.strip() else None
            
            expense.updated_at = datetime.now()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'msg': '开销记录更新成功'
            })
            
        except Exception as e:
            print(f"更新开销记录失败: {str(e)}")
            return jsonify({'success': False, 'msg': f'更新开销记录失败: {str(e)}'}), 500
    
    elif request.method == 'DELETE':
        # 删除开销记录
        try:
            user_id = session['user_id']
            expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
            
            if not expense:
                return jsonify({'success': False, 'msg': '开销记录不存在'}), 404
            
            # 删除关联的收据图片文件
            if expense.receipt_image:
                try:
                    file_path = os.path.join(app.static_folder, expense.receipt_image.lstrip('/static/'))
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"删除收据图片失败: {str(e)}")
            
            db.session.delete(expense)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'msg': '开销记录删除成功'
            })
            
        except Exception as e:
            print(f"删除开销记录失败: {str(e)}")
            return jsonify({'success': False, 'msg': f'删除开销记录失败: {str(e)}'}), 500

def allowed_file(filename):
    """检查文件格式是否允许"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def recognize_payment_receipt(file_path):
    """
    识别支付截图 - 这里是简化版本
    实际应用中应该调用专业的OCR服务如百度OCR、腾讯OCR或阿里云OCR
    """
    try:
        # 这里使用模拟的识别结果
        # 实际应该调用OCR API进行文字识别，然后使用AI分析支付信息
        
        # 可以根据文件名或其他方式进行简单的模拟识别
        import random
        
        # 模拟识别结果
        merchants = ['星巴克', '麦当劳', '肯德基', '华为商城', '苹果零售店', '家乐福', '沃尔玛', '7-Eleven']
        categories = ['餐饮', '购物', '交通', '娱乐']
        payment_methods = ['微信支付', '支付宝']
        
        # 随机生成一些模拟数据（实际应用中应该从图片中识别）
        result = {
            'amount': round(random.uniform(10, 500), 2),
            'merchant': random.choice(merchants),
            'category': random.choice(categories),
            'payment_method': random.choice(payment_methods),
            'expense_date': datetime.now().isoformat(),
            'confidence': random.uniform(0.7, 0.95)
        }
        
        # TODO: 这里应该调用真实的OCR和AI识别服务
        # 例如：
        # 1. 使用OCR提取图片中的文字
        # 2. 使用AI分析文字内容，提取支付信息
        # 3. 返回结构化的支付数据
        
        return result
        
    except Exception as e:
        print(f"识别支付截图失败: {str(e)}")
        # 返回空结果，让用户手动填写
        return {
            'amount': None,
            'merchant': None,
            'category': None,
            'payment_method': None,
            'expense_date': datetime.now().isoformat(),
            'confidence': 0.0
        }

# 旅行报告生成相关API
@app.route('/reports')
@login_required_page
def reports_page():
    """旅行报告页面"""
    return render_template('reports.html')

@app.route('/api/generate-travel-report', methods=['POST'])
@login_required
def generate_travel_report():
    """生成用户旅行报告"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        # 获取用户的所有历史数据
        # 1. 已完成的旅行计划
        today = date.today()
        completed_plans = TravelPlan.query.filter(
            TravelPlan.user_id == user_id,
            TravelPlan.end_date < today
        ).order_by(TravelPlan.end_date.desc()).all()
        
        # 2. 所有游记
        all_notes = []
        for plan in TravelPlan.query.filter_by(user_id=user_id).all():
            all_notes.extend(plan.notes)
        
        # 3. 开销记录
        expenses = Expense.query.filter_by(user_id=user_id).all()
        
        # 4. 动态记录
        moments = Moment.query.filter_by(user_id=user_id).all()
        
        # 如果没有足够的数据，返回提示
        if len(completed_plans) == 0 and len(all_notes) == 0:
            return jsonify({
                'success': False,
                'msg': '您还没有足够的旅行数据来生成报告，请先完成一些旅行计划并撰写游记。'
            })
        
        # 准备数据摘要
        report_data = {
            'user_info': {
                'username': user.username,
                'total_plans': len(TravelPlan.query.filter_by(user_id=user_id).all()),
                'completed_plans': len(completed_plans),
                'total_notes': len(all_notes),
                'total_expenses': len(expenses),
                'total_moments': len(moments)
            },
            'plans_summary': [],
            'notes_summary': [],
            'expense_summary': {
                'total_amount': sum(e.amount for e in expenses),
                'categories': {},
                'monthly_spending': {}
            },
            'travel_destinations': set(),
            'travel_themes': {},
            'transport_modes': {}
        }
        
        # 分析旅行计划
        for plan in completed_plans[:10]:  # 最近10个完成的计划
            plan_data = {
                'title': plan.title,
                'dates': f"{plan.start_date} 到 {plan.end_date}",
                'days': plan.total_days,
                'theme': plan.travel_theme,
                'transport': plan.transport_mode,
                'budget': f"{plan.budget_min}-{plan.budget_max}元"
            }
            report_data['plans_summary'].append(plan_data)
            
            # 统计主题和交通方式
            if plan.travel_theme:
                report_data['travel_themes'][plan.travel_theme] = report_data['travel_themes'].get(plan.travel_theme, 0) + 1
            if plan.transport_mode:
                report_data['transport_modes'][plan.transport_mode] = report_data['transport_modes'].get(plan.transport_mode, 0) + 1
        
        # 分析游记
        for note in all_notes[:10]:  # 最近10篇游记
            note_data = {
                'title': note.title,
                'content_length': len(note.content),
                'created_date': note.created_at.strftime('%Y-%m-%d')
            }
            report_data['notes_summary'].append(note_data)
        
        # 分析开销
        for expense in expenses:
            category = expense.category
            month = expense.expense_date.strftime('%Y-%m') if expense.expense_date else '未知'
            
            if category:
                report_data['expense_summary']['categories'][category] = \
                    report_data['expense_summary']['categories'].get(category, 0) + expense.amount
            
            report_data['expense_summary']['monthly_spending'][month] = \
                report_data['expense_summary']['monthly_spending'].get(month, 0) + expense.amount
        
        # 从行程中提取目的地
        for plan in TravelPlan.query.filter_by(user_id=user_id).all():
            for itinerary in plan.itineraries:
                for item in itinerary.itinerary_items:
                    if item.location:
                        report_data['travel_destinations'].add(item.location)
        
        report_data['travel_destinations'] = list(report_data['travel_destinations'])
        
        # 构建AI提示词
        system_prompt = """
你是一个专业的旅行数据分析师和报告撰写专家。请根据用户的旅行历史数据，生成一份详细、有洞察力的个人旅行履历报告。

报告应该包含以下部分，使用Markdown格式：

# 🌍 个人旅行履历报告

## 📊 旅行数据概览
- 总体统计数据

## 🗺️ 旅行足迹分析
- 主要目的地分析
- 地域偏好特点

## 🎯 个人旅行偏好画像
- 旅行主题偏好
- 交通方式习惯
- 预算水平分析

## 💰 旅行消费分析
- 开销结构分析
- 消费趋势洞察

## 📝 游记创作分析
- 记录习惯分析
- 内容特点总结

## 🚀 个人成长轨迹
- 旅行经验发展
- 能力提升体现

## 💡 未来旅行建议
- 基于历史数据的个性化推荐
- 旅行技能提升建议

请用温暖、专业、有洞察力的语调撰写，让用户感受到自己旅行经历的价值和成长。
"""

        user_prompt = f"""
请为用户 {user.username} 生成旅行履历报告，基于以下数据：

## 基础统计
- 总旅行计划数：{report_data['user_info']['total_plans']}
- 已完成计划数：{report_data['user_info']['completed_plans']}
- 游记总数：{report_data['user_info']['total_notes']}
- 开销记录数：{report_data['user_info']['total_expenses']}
- 动态发布数：{report_data['user_info']['total_moments']}

## 最近完成的旅行计划
{report_data['plans_summary']}

## 游记概况
{report_data['notes_summary']}

## 开销分析
- 总开销：{report_data['expense_summary']['total_amount']}元
- 分类开销：{report_data['expense_summary']['categories']}
- 月度开销：{report_data['expense_summary']['monthly_spending']}

## 旅行目的地
{report_data['travel_destinations']}

## 旅行主题偏好
{report_data['travel_themes']}

## 交通方式偏好
{report_data['transport_modes']}

请基于这些数据生成一份有深度、有洞察的个人旅行履历报告。
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 调用DEEPSEEK API生成报告
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            max_tokens=4000,
            temperature=0.7
        )
        
        report_content = response.choices[0].message.content
        
        # 保存报告到数据库（可选）
        # 这里可以创建一个Report模型来保存历史报告
        
        return jsonify({
            'success': True,
            'report': report_content,
            'data_summary': report_data['user_info'],
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"生成旅行报告失败: {str(e)}")
        return jsonify({
            'success': False,
            'msg': f'生成报告失败: {str(e)}'
        }), 500

@app.route('/api/travel-stats', methods=['GET'])
@login_required
def get_travel_stats():
    """获取用户旅行统计数据"""
    try:
        user_id = session['user_id']
        today = date.today()
        
        # 基础统计
        total_plans = TravelPlan.query.filter_by(user_id=user_id).count()
        completed_plans = TravelPlan.query.filter(
            TravelPlan.user_id == user_id,
            TravelPlan.end_date < today
        ).count()
        
        total_notes = db.session.query(TravelNote).join(TravelPlan).filter(
            TravelPlan.user_id == user_id
        ).count()
        
        total_expenses = Expense.query.filter_by(user_id=user_id).count()
        total_amount = db.session.query(db.func.sum(Expense.amount)).filter_by(user_id=user_id).scalar() or 0
        
        # 今年的统计
        current_year = today.year
        yearly_plans = TravelPlan.query.filter(
            TravelPlan.user_id == user_id,
            db.extract('year', TravelPlan.start_date) == current_year
        ).count()
        
        yearly_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.user_id == user_id,
            db.extract('year', Expense.expense_date) == current_year
        ).scalar() or 0
        
        # 访问过的城市数（从行程项中统计）
        visited_locations = db.session.query(ItineraryItem.location).join(Itinerary).join(TravelPlan).filter(
            TravelPlan.user_id == user_id,
            TravelPlan.end_date < today,
            ItineraryItem.location.isnot(None)
        ).distinct().count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_plans': total_plans,
                'completed_plans': completed_plans,
                'total_notes': total_notes,
                'total_expenses': total_expenses,
                'total_amount': round(total_amount, 2),
                'yearly_plans': yearly_plans,
                'yearly_expenses': round(yearly_expenses, 2),
                'visited_locations': visited_locations,
                'completion_rate': round((completed_plans / total_plans * 100) if total_plans > 0 else 0, 1)
            }
        })
        
    except Exception as e:
        print(f"获取旅行统计失败: {str(e)}")
        return jsonify({'success': False, 'msg': f'获取统计数据失败: {str(e)}'}), 500

@app.route('/api/plan/<int:plan_id>/share-link', methods=['POST'])
@login_required
def generate_share_link(plan_id):
    """生成计划分享链接"""
    try:
        user_id = session['user_id']
        plan = TravelPlan.query.filter_by(id=plan_id, user_id=user_id).first_or_404()
        
        # 生成分享token
        import hashlib
        share_token = hashlib.md5(f"{plan.id}_{plan.user_id}_travel_agent_share".encode()).hexdigest()[:8]
        
        # 构建分享链接
        from urllib.parse import urljoin
        share_url = urljoin(request.host_url, f'/shared-plan/{plan_id}/{share_token}')
        
        return jsonify({
            'success': True,
            'share_url': share_url,
            'share_token': share_token
        })
        
    except Exception as e:
        return jsonify({'success': False, 'msg': f'生成分享链接失败: {str(e)}'}), 500

@app.route('/api/shared-plan/<int:plan_id>/<share_token>')
def get_shared_plan_detail(plan_id, share_token):
    """获取公开分享的计划详情"""
    try:
        plan = TravelPlan.query.get_or_404(plan_id)
        
        # 验证分享token
        import hashlib
        expected_token = hashlib.md5(f"{plan.id}_{plan.user_id}_travel_agent_share".encode()).hexdigest()[:8]
        
        if share_token != expected_token:
            return jsonify({'success': False, 'msg': '分享链接无效'}), 403
        
        # 返回计划数据（类似于原有的get_plan_detail，但不需要登录验证）
        today = date.today()
        plan_end_date = plan.end_date if isinstance(plan.end_date, date) else datetime.strptime(plan.end_date, '%Y-%m-%d').date()
        if plan_end_date < today:
            status = 'completed'
        else:
            status = plan.status
            
        itineraries = []
        for itinerary in plan.itineraries:
            items = []
            for item in itinerary.itinerary_items:
                items.append({
                    'id': item.id,
                    'start_time': item.start_time.strftime('%H:%M'),
                    'end_time': item.end_time.strftime('%H:%M') if item.end_time else None,
                    'activity_type': item.activity_type,
                    'title': item.title,
                    'description': item.description,
                    'location': item.location,
                    'latitude': item.latitude,
                    'longitude': item.longitude,
                    'estimated_cost': item.estimated_cost,
                    'order_index': item.order_index
                })
            itineraries.append({
                'id': itinerary.id,
                'day_number': itinerary.day_number,
                'date': itinerary.date.isoformat(),
                'theme': itinerary.theme,
                'notes': itinerary.notes,
                'items': sorted(items, key=lambda x: x['order_index'])
            })
            
        return jsonify({
            'success': True,
            'id': plan.id,
            'title': plan.title,
            'start_date': plan.start_date.isoformat(),
            'end_date': plan.end_date.isoformat(),
            'total_days': plan.total_days,
            'budget_min': plan.budget_min,
            'budget_max': plan.budget_max,
            'travel_theme': plan.travel_theme,
            'transport_mode': plan.transport_mode,
            'status': status,
            'ai_generated': plan.ai_generated,
            'owner': plan.user.username,
            'itineraries': sorted(itineraries, key=lambda x: x['day_number'])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'msg': f'获取计划数据失败: {str(e)}'}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'
    
    # 在Railway环境中运行时
    if os.environ.get('RAILWAY_DEPLOYMENT'):
        print("🚀 Railway部署环境检测到")
        # 使用Flask-Migrate进行数据库迁移，而不是create_all
        try:
            from flask_migrate import upgrade
            with app.app_context():
                print("📊 开始执行数据库迁移...")
                # 检查数据库连接
                try:
                    db.engine.connect()
                    print("✅ 数据库连接成功")
                except Exception as conn_error:
                    print(f"❌ 数据库连接失败: {conn_error}")
                    raise
                
                # 执行数据库迁移到最新版本
                upgrade()
                print("✅ 数据库迁移完成")
                
                # 验证表结构
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                print(f"📋 当前数据库表: {len(tables)}个")
                for table in sorted(tables):
                    print(f"  - {table}")
                    
        except Exception as e:
            print(f"⚠️ 数据库迁移失败: {e}")
            # 如果迁移失败且没有表，则创建表（仅在首次部署时）
            try:
                with app.app_context():
                    from sqlalchemy import inspect
                    inspector = inspect(db.engine)
                    tables = inspector.get_table_names()
                    if not tables:  # 如果没有任何表，说明是首次部署
                        print("🔧 首次部署，创建数据库表...")
                        db.create_all()
                        print("✅ 数据库表创建完成")
                        
                        # 再次验证
                        final_tables = inspector.get_table_names()
                        print(f"📋 创建后的数据库表: {len(final_tables)}个")
                    else:
                        print(f"⚠️ 数据库已存在{len(tables)}个表，但迁移失败")
                        print("可能的原因：字段长度不兼容、数据类型冲突等")
                        # 重新抛出原始错误
                        raise e
            except Exception as fallback_error:
                print(f"❌ 数据库初始化彻底失败: {fallback_error}")
                raise
    else:
        print("🏠 本地开发环境")
    
    # 启动清理任务线程
    cleanup_thread = threading.Thread(target=cleanup_old_tasks)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    print(f"🌍 Travel Agent启动在 {host}:{port}")
    app.run(host=host, port=port, debug=os.environ.get('DEBUG', 'False').lower() == 'true') 
