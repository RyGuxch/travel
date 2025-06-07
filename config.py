import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # 数据库配置
    # 检查是否在Railway上运行，如果是则使用PostgreSQL，否则使用SQLite
    if os.environ.get('RAILWAY_DEPLOYMENT') and os.environ.get('DATABASE_URL'):
        # 确保使用正确的PostgreSQL URI格式
        db_url = os.environ.get('DATABASE_URL')
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://')
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///travel_agent.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Deepseek API配置
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY') or 'your-deepseek-api-key'
    DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
    
    # 高德地图API配置
    AMAP_API_KEY = os.environ.get('AMAP_API_KEY') or 'your-amap-api-key'
    AMAP_WEB_KEY = os.environ.get('AMAP_WEB_KEY') or 'your-amap-web-key'
    
    # OCR服务配置
    # 百度OCR API配置
    BAIDU_OCR_API_KEY = os.environ.get('BAIDU_OCR_API_KEY')
    BAIDU_OCR_SECRET_KEY = os.environ.get('BAIDU_OCR_SECRET_KEY')
    
    # 腾讯OCR API配置
    TENCENT_SECRET_ID = os.environ.get('TENCENT_SECRET_ID')
    TENCENT_SECRET_KEY = os.environ.get('TENCENT_SECRET_KEY')
    
    # 文件上传配置
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'static/uploads'
    MAX_CONTENT_LENGTH = 256 * 1024 * 1024  # 100MB最大文件大小，支持视频和GIF上传 
    
    # Web推送通知配置 (VAPID)
    # 这些是有效的VAPID密钥对，用于Web推送通知
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY') or 'JQGdBtLpUJiGgcnTY6BDU9vnQMEz3VpkcRoQF_79SpU'
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY') or 'BMlbrHxiYertjOpPiejcdrvO8OmWuZ6Ys9nxDw_cKfB5zc8mAX-WjsqntI1TbvOEtYbkiy6KeTbahNJzFIWvS4M'
    VAPID_SUBJECT = os.environ.get('VAPID_SUBJECT') or 'mailto:admin@travel-agent.com' 