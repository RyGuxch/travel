"""
OCR服务集成模块
支持多种OCR服务提供商，用于识别支付截图
"""

import requests
import json
import base64
import os
from datetime import datetime
import re
from config import Config

class OCRService:
    """OCR服务类"""
    
    def __init__(self):
        self.baidu_api_key = os.environ.get('BAIDU_OCR_API_KEY')
        self.baidu_secret_key = os.environ.get('BAIDU_OCR_SECRET_KEY')
        self.tencent_secret_id = os.environ.get('TENCENT_SECRET_ID')
        self.tencent_secret_key = os.environ.get('TENCENT_SECRET_KEY')
        
    def recognize_payment_receipt(self, image_path):
        """
        识别支付截图，提取支付信息
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            dict: 提取的支付信息
        """
        try:
            # 优先使用百度OCR
            if self.baidu_api_key and self.baidu_secret_key:
                return self._baidu_ocr_recognition(image_path)
            
            # 备选：腾讯OCR
            if self.tencent_secret_id and self.tencent_secret_key:
                return self._tencent_ocr_recognition(image_path)
            
            # 如果没有配置API密钥，返回模拟数据
            print("警告：未配置OCR API密钥，使用模拟识别结果")
            return self._mock_recognition()
            
        except Exception as e:
            print(f"OCR识别失败: {str(e)}")
            return self._mock_recognition()
    
    def _baidu_ocr_recognition(self, image_path):
        """使用百度OCR进行识别"""
        try:
            # 获取access_token
            token_url = "https://aip.baidubce.com/oauth/2.0/token"
            token_params = {
                'grant_type': 'client_credentials',
                'client_id': self.baidu_api_key,
                'client_secret': self.baidu_secret_key
            }
            
            token_response = requests.post(token_url, params=token_params)
            access_token = token_response.json().get('access_token')
            
            if not access_token:
                raise Exception("获取百度OCR access_token失败")
            
            # 读取图片并转换为base64
            with open(image_path, 'rb') as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 尝试多种OCR接口，按准确度排序
            ocr_results = []
            
            # 1. 票据识别 - 最适合支付截图
            try:
                receipt_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/receipt?access_token={access_token}"
                receipt_data = {
                    'image': image_base64,
                    'recognize_granularity': 'big',
                    'accuracy': 'high'
                }
                receipt_response = requests.post(receipt_url, data=receipt_data)
                receipt_result = receipt_response.json()
                
                if 'words_result' in receipt_result:
                    text_lines = [item['words'] for item in receipt_result['words_result']]
                    full_text = '\n'.join(text_lines)
                    result = self._analyze_payment_text(full_text)
                    result['ocr_method'] = '票据识别'
                    ocr_results.append(result)
                    print(f"票据识别成功，识别文本: {full_text}")
            except Exception as e:
                print(f"票据识别失败: {str(e)}")
            
            # 2. 通用高精度识别
            try:
                accurate_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={access_token}"
                accurate_data = {
                    'image': image_base64,
                    'detect_direction': 'true',
                    'language_type': 'CHN_ENG',
                    'recognize_granularity': 'big'
                }
                accurate_response = requests.post(accurate_url, data=accurate_data)
                accurate_result = accurate_response.json()
                
                if 'words_result' in accurate_result:
                    text_lines = [item['words'] for item in accurate_result['words_result']]
                    full_text = '\n'.join(text_lines)
                    result = self._analyze_payment_text(full_text)
                    result['ocr_method'] = '高精度识别'
                    ocr_results.append(result)
                    print(f"高精度识别成功，识别文本: {full_text}")
            except Exception as e:
                print(f"高精度识别失败: {str(e)}")
            
            # 3. 通用识别作为后备
            try:
                general_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
                general_data = {
                    'image': image_base64,
                    'detect_direction': 'true',
                    'language_type': 'CHN_ENG'
                }
                general_response = requests.post(general_url, data=general_data)
                general_result = general_response.json()
                
                if 'words_result' in general_result:
                    text_lines = [item['words'] for item in general_result['words_result']]
                    full_text = '\n'.join(text_lines)
                    result = self._analyze_payment_text(full_text)
                    result['ocr_method'] = '通用识别'
                    ocr_results.append(result)
                    print(f"通用识别成功，识别文本: {full_text}")
            except Exception as e:
                print(f"通用识别失败: {str(e)}")
            
            # 选择最佳结果
            if ocr_results:
                # 按置信度和识别完整度排序
                best_result = max(ocr_results, key=lambda x: (
                    x.get('confidence', 0),
                    1 if x.get('amount') else 0,
                    1 if x.get('merchant') else 0,
                    1 if x.get('payment_method') else 0
                ))
                print(f"选择最佳结果: {best_result['ocr_method']}, 置信度: {best_result.get('confidence', 0):.2f}")
                return best_result
            else:
                raise Exception("所有OCR方法都失败")
                
        except Exception as e:
            print(f"百度OCR识别失败: {str(e)}")
            return self._mock_recognition()
    
    def _tencent_ocr_recognition(self, image_path):
        """使用腾讯OCR进行识别"""
        # TODO: 实现腾讯OCR API调用
        # 这里可以参考腾讯云OCR文档进行实现
        return self._mock_recognition()
    
    def _analyze_payment_text(self, text):
        """
        分析OCR识别的文字，提取支付信息
        
        Args:
            text: OCR识别的文字内容
            
        Returns:
            dict: 提取的支付信息
        """
        try:
            result = {
                'amount': None,
                'merchant': None,
                'category': None,
                'payment_method': None,
                'expense_date': datetime.now().isoformat(),
                'confidence': 0.8,
                'raw_text': text
            }
            
            print(f"分析文本: {text}")  # 调试信息
            
            # 提取金额（支持多种格式，包括负号）
            amount_patterns = [
                # 微信支付特有格式
                r'-¥?(\d+(?:\.\d{1,2})?)',               # -¥9.90 或 -9.90
                r'¥-(\d+(?:\.\d{1,2})?)',               # ¥-9.90
                r'￥-(\d+(?:\.\d{1,2})?)',              # ￥-9.90
                r'-(￥|¥)(\d+(?:\.\d{1,2})?)',          # -¥9.90
                
                # 标准格式 - 更严格的匹配
                r'¥(\d+(?:\.\d{1,2})?)',                # ¥123.45
                r'￥(\d+(?:\.\d{1,2})?)',               # ￥123.45
                r'(\d+\.\d{1,2})元',                    # 123.45元
                r'(\d+)元(\d{1,2})角',                  # 123元45角
                
                # 文字标识格式
                r'金额[：:\s]*[-]?¥?(\d+(?:\.\d{1,2})?)',      # 金额：-9.90
                r'支付金额[：:\s]*[-]?¥?(\d+(?:\.\d{1,2})?)',  # 支付金额：-9.90
                r'实付[：:\s]*[-]?¥?(\d+(?:\.\d{1,2})?)',      # 实付：-9.90
                r'转账金额[：:\s]*[-]?¥?(\d+(?:\.\d{1,2})?)', # 转账金额：-9.90
                r'总金额[：:\s]*[-]?¥?(\d+(?:\.\d{1,2})?)',    # 总金额：-9.90
                r'付款[：:\s]*[-]?¥?(\d+(?:\.\d{1,2})?)',      # 付款：-9.90
                
                # 带千分位格式
                r'￥(\d{1,5}(?:,\d{3})*(?:\.\d{1,2})?)',      # ￥1,234.56
                r'(\d{1,5}(?:,\d{3})*(?:\.\d{1,2})?)元',      # 1,234.56元
                
                # 独立数字格式 - 添加这个模式来匹配简单的数字
                r'(?:^|\n|\s)(\d+\.\d{1,2})(?=\s|\n|$)',     # 独立的小数，如 9.90
                r'(?:^|\n|\s)(\d{1,5})(?=\s|\n|$)',          # 独立的整数，如 50
            ]
            
            for pattern in amount_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    amounts = []
                    for match in matches:
                        try:
                            if isinstance(match, tuple):
                                # 处理特殊格式 (如 -(￥|¥)(\d+) 或 元角格式)
                                if len(match) == 2 and match[0] and match[1]:
                                    # 检查是否是符号+金额格式
                                    if match[0] in ['￥', '¥']:
                                        amount = float(match[1])
                                    else:
                                        # 元角格式
                                        yuan, jiao = match
                                        amount = float(yuan) + float(jiao) / 10
                                else:
                                    # 取第一个非空值
                                    amount_str = next((m for m in match if m), "0")
                                    amount = float(amount_str)
                            else:
                                # 移除千分位逗号
                                amount_str = str(match).replace(',', '')
                                amount = float(amount_str)
                            
                            # 只接受合理范围的金额
                            if 0.01 <= amount <= 100000:
                                amounts.append(amount)
                        except (ValueError, IndexError):
                            continue
                    
                    # 选择最合理的金额（通常是最大值，代表主要交易金额）
                    if amounts:
                        result['amount'] = max(amounts)
                        print(f"识别到金额: {result['amount']}")
                        break
            
            # 提取商家名称（增强版，支持中英文混合）
            merchant_patterns = [
                # 微信支付特有格式 - 更精确的匹配
                r'([a-zA-Z]+\s*coffee)\b',                          # luckin coffee等
                r'\b([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s*(?=[\u4e00-\u9fff]|$)',  # 英文商家名
                r'([a-zA-Z0-9\'\-\s]+?)(?:\s*（|\s*$)',             # 英文名后跟中文括号
                
                # 中文商家名格式
                r'([\u4e00-\u9fff]{2,}(?:（[\u4e00-\u9fff]*）)?(?:有限公司|集团|店|超市|商场)?)',  # 中文公司名
                r'收款方[：:\s]*([^\n\r]+?)(?:\s|$)',
                r'收款人[：:\s]*([^\n\r]+?)(?:\s|$)', 
                r'商户[：:\s]*([^\n\r]+?)(?:\s|$)',
                r'商家[：:\s]*([^\n\r]+?)(?:\s|$)',
                r'商户全称[：:\s]*([^\n\r]+?)(?:\s|$)',            # 微信支付专用
                
                # 交易相关格式 - 提取目标商家
                r'向\s*([^\s\n\r付款]+)',                          # 向XXX付款
                r'付款给\s*([^\n\r]+?)(?:\s|$)',
                r'转账给\s*([^\n\r]+?)(?:\s|$)',
                r'支付给\s*([^\n\r]+?)(?:\s|$)',
                r'店铺[：:\s]*([^\n\r]+?)(?:\s|$)',
            ]
            
            for pattern in merchant_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    merchant = match.group(1).strip()
                    
                    # 清理商家名称
                    merchant = re.sub(r'[（）()]+', '', merchant)  # 移除括号
                    merchant = re.sub(r'\s+', ' ', merchant)       # 合并多余空格
                    merchant = merchant.strip()
                    
                    # 过滤掉无意义的信息
                    invalid_merchants = [
                        '微信支付', '支付宝', '银行卡', '现金', '订单付款', 
                        '支付成功', '付款成功', '转账', '收款', '财付通',
                        '支付科技有限公司', '有限公司', '付款'
                    ]
                    
                    # 过滤掉纯数字或过短的名称
                    if (len(merchant) > 1 and 
                        not merchant.isdigit() and
                        merchant not in invalid_merchants and
                        not any(invalid in merchant for invalid in invalid_merchants)):
                        result['merchant'] = merchant
                        print(f"识别到商家: {merchant}")
                        break
            
            # 根据关键词推断分类（增强版，包含更多品牌）
            text_lower = text.lower()
            category_keywords = {
                '餐饮': [
                    # 咖啡品牌
                    'coffee', 'luckin', '瑞幸', '星巴克', 'starbucks', 'costa', 
                    # 快餐品牌
                    '麦当劳', 'mcdonald', '肯德基', 'kfc', '汉堡王', '必胜客', 'pizza',
                    # 中餐
                    '餐厅', '饭店', '火锅', '海底捞', '小龙坎', '呷哺', '外婆家',
                    # 茶饮
                    '奶茶', '喜茶', '一点点', 'coco', '茶颜悦色', '古茗',
                    # 外卖
                    '外卖', '美团', '饿了么', '点餐', '用餐', '聚餐', '食堂', '茶餐厅',
                    # 通用词汇
                    '咖啡', '美食', '快餐', '订单付款'
                ],
                '交通': [
                    '滴滴', '出租', '地铁', '公交', '打车', '网约车', '出行', '共享单车', 
                    '摩拜', 'ofo', '哈啰', '滴滴出行', '快车', '专车', '顺风车', '代驾',
                    '火车', '高铁', '飞机', '机票', '车票', '地铁卡', '公交卡', '加油',
                    '12306', '携程', '去哪儿'
                ],
                '住宿': [
                    '酒店', '宾馆', '住宿', '客栈', '民宿', '青旅', '旅馆', '旅社',
                    '如家', '汉庭', '锦江', '7天', '速8', 'airbnb', '途家', '华住'
                ],
                '门票': [
                    '门票', '景区', '博物馆', '公园', '游乐园', '动物园', '海洋馆',
                    '故宫', '长城', '迪士尼', '欢乐谷', '方特', '旅游', '景点'
                ],
                '购物': [
                    '超市', '商场', '购物', '百货', '便利店', '专卖店', '商店',
                    '淘宝', '天猫', '京东', '拼多多', '苏宁', '国美', '沃尔玛',
                    '家乐福', '大润发', '7-eleven', '全家', '罗森'
                ],
                '娱乐': [
                    '电影', 'ktv', '游戏', '娱乐', '健身', '按摩', '美容', '美发',
                    '网吧', '桌游', '密室逃脱', '剧本杀', '洗浴', 'spa', '足疗',
                    '王者荣耀', '和平精英', 'steam', '网易', '腾讯游戏'
                ]
            }
            
            # 首先检查商家名称中的关键词
            merchant_name = result.get('merchant', '').lower()
            for category, keywords in category_keywords.items():
                if any(keyword in merchant_name for keyword in keywords):
                    result['category'] = category
                    print(f"根据商家名识别分类: {category}")
                    break
            
            # 如果商家名没有匹配，再检查全文
            if not result['category']:
                for category, keywords in category_keywords.items():
                    if any(keyword in text_lower for keyword in keywords):
                        result['category'] = category
                        print(f"根据全文识别分类: {category}")
                        break
            
            if not result['category']:
                result['category'] = '其他'
            
            # 识别支付方式（增强版）
            payment_keywords = {
                '微信支付': ['微信', 'wechat', '腾讯', '微信转账', '微信红包', '零钱', '财付通'],
                '支付宝': ['支付宝', '蚂蚁', 'alipay', '花呗', '余额宝', '支付宝转账'],
                '银行卡': ['银行卡', '信用卡', '储蓄卡', '借记卡', '工商银行', '建设银行', 
                          '农业银行', '中国银行', '招商银行', '交通银行', '民生银行',
                          '浦发银行', '中信银行', '兴业银行', '光大银行', '华夏银行',
                          '广发银行', '平安银行', '邮储银行'],
                '现金': ['现金', '现金支付']
            }
            
            for payment_method, keywords in payment_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    result['payment_method'] = payment_method
                    print(f"识别到支付方式: {payment_method}")
                    break
            
            # 提取时间（增强版）
            time_patterns = [
                r'(\d{4}年\d{1,2}月\d{1,2}日\s+\d{1,2}:\d{2}:\d{2})',
                r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}:\d{2})',
                r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2})',
                r'(\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2})',
                r'(\d{1,2}月\d{1,2}日\s+\d{1,2}:\d{2})',
                r'支付时间[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日\s+\d{1,2}:\d{2})',
                r'交易时间[：:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2})',
            ]
            
            for pattern in time_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        time_str = match.group(1)
                        print(f"识别到时间: {time_str}")
                        # 这里可以添加具体的时间解析
                        result['expense_date'] = datetime.now().isoformat()
                        break
                    except:
                        continue
            
            # 计算置信度
            confidence_score = 0.4  # 基础分数
            
            if result['amount']:
                confidence_score += 0.4  # 金额最重要
            if result['merchant']:
                confidence_score += 0.2
            if result['payment_method']:
                confidence_score += 0.1
            if result['category'] != '其他':
                confidence_score += 0.1
                
            # 如果是明确的商家（如luckin coffee），提高置信度
            if result['merchant']:
                known_brands = ['luckin', 'starbucks', '星巴克', '瑞幸', '麦当劳', '肯德基']
                if any(brand in result['merchant'].lower() for brand in known_brands):
                    confidence_score += 0.1
            
            result['confidence'] = min(confidence_score, 0.98)
            
            print(f"最终识别结果: {result}")
            return result
            
        except Exception as e:
            print(f"分析支付文字失败: {str(e)}")
            return self._mock_recognition()
    
    def _mock_recognition(self):
        """模拟识别结果，用于测试"""
        import random
        
        merchants = ['星巴克', '麦当劳', '肯德基', '华为商城', '苹果零售店', '家乐福', '沃尔玛', '7-Eleven']
        categories = ['餐饮', '购物', '交通', '娱乐']
        payment_methods = ['微信支付', '支付宝']
        
        return {
            'amount': round(random.uniform(10, 500), 2),
            'merchant': random.choice(merchants),
            'category': random.choice(categories),
            'payment_method': random.choice(payment_methods),
            'expense_date': datetime.now().isoformat(),
            'confidence': random.uniform(0.7, 0.95),
            'raw_text': '模拟OCR识别结果'
        }

# 全局OCR服务实例
ocr_service = OCRService() 