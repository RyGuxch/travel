# Travel Agent - 智能旅行助手

一个基于AI的智能旅行规划和管理系统，集成了旅行计划生成、地图可视化、开销管理、游记记录和社交功能。

## ✨ 主要功能

### 🤖 AI旅行规划
- **智能路线规划**: 基于Deepseek AI的个性化旅行建议
- **实时地图可视化**: 集成高德地图显示景点和路线
- **多样化计划**: 支持不同预算、时长和兴趣的旅行方案

### 💰 智能开销管理
- **AI截图识别**: 上传微信/支付宝支付截图，自动识别金额、商家、分类
- **实时统计分析**: 月度开销、分类统计、预算跟踪
- **多种记录方式**: 支持手动录入和AI识别两种方式
- **旅行计划关联**: 开销可关联到具体的旅行计划

### 📝 游记与社交
- **富文本游记**: Markdown编辑器，支持图片和格式化内容
- **社交互动**: 朋友圈动态、好友系统、实时聊天
- **内容分享**: 分享旅行经历和美好瞬间

### 🗺️ 地图集成
- **交互式地图**: 显示旅行路线和景点标记
- **实时定位**: 基于高德地图的精准定位服务
- **路线规划**: 自动生成最优旅行路线

## 🚀 技术栈

- **后端**: Python Flask + SQLAlchemy
- **前端**: HTML5 + CSS3 + JavaScript (原生)
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **AI服务**: Deepseek API
- **地图服务**: 高德地图 API
- **OCR服务**: 百度OCR / 腾讯OCR
- **部署**: Railway (生产环境)

## 📦 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd Travel-Agent

# 安装依赖
pip install -r requirements.txt
```

### 2. 环境变量配置

创建 `.env` 文件：

```bash
# Flask配置
SECRET_KEY=your-secret-key-here

# Deepseek AI API配置
DEEPSEEK_API_KEY=your-deepseek-api-key

# 高德地图API配置
AMAP_API_KEY=your-amap-api-key
AMAP_WEB_KEY=your-amap-web-key

# 百度OCR API配置（开销管理功能）
BAIDU_OCR_API_KEY=your-baidu-ocr-api-key
BAIDU_OCR_SECRET_KEY=your-baidu-ocr-secret-key

# 文件上传配置
UPLOAD_FOLDER=static/uploads
```

### 3. 数据库初始化

```bash
# 初始化数据库迁移
export FLASK_APP=app.py
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# 初始化开销分类数据
python init_expense_data.py
```

### 4. 运行应用

```bash
python app.py
```

访问 `http://127.0.0.1:5000` 即可使用应用。

## 🔧 配置指南

### API密钥获取

1. **Deepseek AI**: [获取API密钥](https://platform.deepseek.com/api_keys)
2. **高德地图**: [申请开发者账号](https://console.amap.com/dev/key/app)
3. **百度OCR**: [申请OCR服务](https://console.bce.baidu.com/ai/#/ai/ocr/overview/index)

### 详细配置文档

- [数据库迁移指南](DATABASE_MIGRATION.md)
- [OCR服务配置](OCR_SETUP.md)

## 📱 功能详情

### 开销管理
- 📸 **支付截图识别**: 支持微信、支付宝截图自动识别
- 📊 **统计分析**: 月度、分类、趋势分析
- 🏷️ **智能分类**: 7大分类自动识别 (交通、住宿、餐饮、门票、购物、娱乐、其他)
- 💳 **支付方式**: 微信支付、支付宝、银行卡、现金
- 🎯 **计划关联**: 开销可关联到具体旅行计划

### AI识别能力
- **金额识别**: ¥123.45、123.45元、123元45角等多种格式
- **商家识别**: 收款方、商户、店铺名称自动提取
- **时间提取**: 支付时间自动识别
- **分类推断**: 基于关键词智能推断消费类型
- **置信度评估**: AI识别结果的可信度评分

## 🎨 界面特色

- **Apple风格设计**: 现代化、简洁的用户界面
- **响应式布局**: 完美适配桌面和移动设备
- **流畅动画**: 丰富的交互动画效果
- **深色模式**: 支持系统主题自动切换

## 📄 数据库结构

### 核心表
- `users`: 用户信息
- `travel_plans`: 旅行计划
- `travel_notes`: 游记内容
- `moments`: 朋友圈动态
- `friends`: 好友关系

### 开销管理表
- `expenses`: 开销记录
- `expense_categories`: 开销分类
- `expense_budgets`: 预算管理

## 🧪 测试

```bash
# 测试OCR功能
python test_ocr.py

# 测试数据库连接
python -c "from app import app, db; print('Database connected successfully')"
```

## 🚀 部署

### Railway部署

1. 连接GitHub仓库到Railway
2. 配置环境变量
3. 自动部署

### 环境变量 (生产环境)

```bash
DATABASE_URL=postgresql://...
SECRET_KEY=production-secret-key
DEEPSEEK_API_KEY=your-production-key
AMAP_API_KEY=your-production-key
AMAP_WEB_KEY=your-production-key
BAIDU_OCR_API_KEY=your-production-key
BAIDU_OCR_SECRET_KEY=your-production-key
```

## 📝 更新日志

### v2.0.0 (2025-06-04)
- ✨ 新增智能开销管理功能
- 🤖 集成百度OCR支付截图识别
- 📊 开销统计和分析面板
- 🗄️ 使用Flask-Migrate管理数据库迁移
- 🎨 优化Apple风格界面设计

### v1.0.0
- 🚀 基础旅行规划功能
- 🗺️ 高德地图集成
- 📝 游记和社交功能
- 👥 用户系统和好友功能

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目！

## 📄 许可证

MIT License

## 🙏 致谢

- [Deepseek AI](https://www.deepseek.com/) - AI智能规划
- [高德地图](https://lbs.amap.com/) - 地图服务
- [百度智能云](https://cloud.baidu.com/) - OCR识别
- [Flask](https://flask.palletsprojects.com/) - Web框架 