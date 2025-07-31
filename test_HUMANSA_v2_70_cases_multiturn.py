#!/usr/bin/env python3
"""HUMANSA V2 Extended Test Suite - 70 Test Cases with Multi-turn Conversations"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
import time
import sys
from typing import List, Dict, Any, Optional

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '6001')
BASE_URL = f"http://localhost:{TEST_PORT}"

# Colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    MAGENTA = '\033[35m'

def print_colored(text, color=Colors.ENDC):
    """Print text with color"""
    print(f"{color}{text}{Colors.ENDC}")

def print_section(title):
    """Print a section header"""
    print_colored(f"\n{'='*80}", Colors.BLUE)
    print_colored(f"  {title}", Colors.BOLD + Colors.BLUE)
    print_colored(f"{'='*80}", Colors.BLUE)

# Original 40 test cases
SINGLE_TURN_TEST_CASES = [
    # Identity & Introduction (1-5)
    {
        "id": 1,
        "name": "Basic Identity Query",
        "query": "你是谁？",
        "expected_keywords": ["诺亚新舟", "小诺", "健康医疗助理", "AI健康管家"],
        "category": "Identity"
    },
    {
        "id": 2,
        "name": "Company Background",
        "query": "介绍一下诺亚新舟",
        "expected_keywords": ["以爱行舟", "亲近相守", "500多位", "三甲主任级"],
        "category": "Identity"
    },
    {
        "id": 3,
        "name": "Service Capabilities",
        "query": "你能做什么？",
        "expected_keywords": ["健康咨询", "实时预约", "检查项目", "诊所导航", "体检报告"],
        "category": "Identity"
    },
    {
        "id": 4,
        "name": "Brand Slogan",
        "query": "诺亚新舟的口号是什么？",
        "expected_keywords": ["以爱行舟", "亲近相守"],
        "category": "Identity"
    },
    {
        "id": 5,
        "name": "English Identity Query",
        "query": "Who are you?",
        "expected_keywords": ["Humansa", "health", "assistant", "medical"],
        "category": "Identity"
    },
    
    # Doctor Search (6-10)
    {
        "id": 6,
        "name": "Find Cardiologist",
        "query": "我想找一个心脏科医生",
        "expected_keywords": ["心", "科", "医生"],
        "category": "Doctor Search"
    },
    {
        "id": 7,
        "name": "Find Doctors by City",
        "query": "上海有哪些医生？",
        "expected_keywords": ["上海", "医生"],
        "category": "Doctor Search"
    },
    {
        "id": 8,
        "name": "Doctor by Name",
        "query": "张医生在吗？",
        "expected_keywords": ["张", "医生"],
        "category": "Doctor Search"
    },
    {
        "id": 9,
        "name": "Doctor Availability",
        "query": "哪个医生现在有号？",
        "expected_keywords": ["医生", "号", "时间"],
        "category": "Doctor Search"
    },
    {
        "id": 10,
        "name": "Specialist Search",
        "query": "有神经内科的专家吗？",
        "expected_keywords": ["神经", "专家"],
        "category": "Doctor Search"
    },
    
    # Appointment Booking (11-15)
    {
        "id": 11,
        "name": "Book Appointment",
        "query": "我想预约明天上午的骨科",
        "expected_keywords": ["预约", "骨科", "明天"],
        "category": "Appointment"
    },
    {
        "id": 12,
        "name": "Check Availability",
        "query": "查看下周的可预约时间",
        "expected_keywords": ["下周", "时间", "预约"],
        "category": "Appointment"
    },
    {
        "id": 13,
        "name": "Cancel Appointment",
        "query": "取消我的预约",
        "expected_keywords": ["取消", "预约"],
        "category": "Appointment"
    },
    {
        "id": 14,
        "name": "Reschedule",
        "query": "改约到下周三",
        "expected_keywords": ["改", "下周三"],
        "category": "Appointment"
    },
    {
        "id": 15,
        "name": "Emergency Appointment",
        "query": "能加急预约吗？",
        "expected_keywords": ["加急", "预约"],
        "category": "Appointment"
    },
    
    # Clinic & Service (16-20)
    {
        "id": 16,
        "name": "Nearest Clinic",
        "query": "离我最近的诊所在哪？",
        "expected_keywords": ["诊所", "近", "地址"],
        "category": "Clinic"
    },
    {
        "id": 17,
        "name": "Service Price",
        "query": "血常规多少钱？",
        "expected_keywords": ["血常规", "钱", "价格"],
        "category": "Service"
    },
    {
        "id": 18,
        "name": "Health Packages",
        "query": "体检套餐有哪些？",
        "expected_keywords": ["体检", "套餐"],
        "category": "Service"
    },
    {
        "id": 19,
        "name": "Clinic Hours",
        "query": "诊所几点开门？",
        "expected_keywords": ["诊所", "时间", "营业"],
        "category": "Clinic"
    },
    {
        "id": 20,
        "name": "Contact Info",
        "query": "上海诊所的电话是多少？",
        "expected_keywords": ["上海", "电话", "联系"],
        "category": "Clinic"
    },
    
    # Medical Consultation (21-25)
    {
        "id": 21,
        "name": "Sleep Issues",
        "query": "我最近总是失眠怎么办？",
        "expected_keywords": ["失眠", "睡眠", "建议"],
        "category": "Medical"
    },
    {
        "id": 22,
        "name": "Child Fever",
        "query": "孩子发烧39度该怎么处理？",
        "expected_keywords": ["发烧", "39", "处理", "孩子"],
        "category": "Medical"
    },
    {
        "id": 23,
        "name": "Emergency Symptoms",
        "query": "胸口疼痛呼吸困难",
        "expected_keywords": ["120", "急救", "立即"],
        "category": "Medical"
    },
    {
        "id": 24,
        "name": "Medication Query",
        "query": "高血压能吃什么药？",
        "expected_keywords": ["高血压", "药", "医生"],
        "category": "Medical"
    },
    {
        "id": 25,
        "name": "Test Results",
        "query": "体检报告显示血糖偏高",
        "expected_keywords": ["血糖", "控制", "饮食"],
        "category": "Medical"
    },
    
    # Product Recommendation (26-30)
    {
        "id": 26,
        "name": "Health Products",
        "query": "你们有什么保健品推荐吗？",
        "expected_keywords": ["保健品", "推荐", "健康"],
        "category": "Product"
    },
    {
        "id": 27,
        "name": "Vitamins",
        "query": "我想买维生素D，有什么推荐？",
        "expected_keywords": ["维生素D", "推荐"],
        "category": "Product"
    },
    {
        "id": 28,
        "name": "Medical Equipment",
        "query": "家里老人需要血压计，推荐一款",
        "expected_keywords": ["血压计", "推荐"],
        "category": "Product"
    },
    {
        "id": 29,
        "name": "Sleep Aid Products",
        "query": "有什么产品可以帮助睡眠？",
        "expected_keywords": ["睡眠", "产品", "帮助"],
        "category": "Product"
    },
    {
        "id": 30,
        "name": "Purchase Guidance",
        "query": "怎么购买这些产品？",
        "expected_keywords": ["购买", "小程序", "商城"],
        "category": "Product"
    },
    
    # Memory & Context (31-40)
    {
        "id": 31,
        "name": "Store Personal Info",
        "query": "我叫李明，45岁，有高血压",
        "expected_keywords": ["记录", "信息"],
        "category": "Memory"
    },
    {
        "id": 32,
        "name": "Store Allergies",
        "query": "我对青霉素过敏",
        "expected_keywords": ["过敏", "记录", "注意"],
        "category": "Memory"
    },
    {
        "id": 33,
        "name": "Recall Info",
        "query": "你记得我的基本信息吗？",
        "expected_keywords": ["李明", "45", "高血压"],
        "category": "Memory",
        "requires_context": True
    },
    {
        "id": 34,
        "name": "Medical History",
        "query": "我有什么过敏史？",
        "expected_keywords": ["青霉素", "过敏"],
        "category": "Memory",
        "requires_context": True
    },
    {
        "id": 35,
        "name": "Family Member",
        "query": "我女儿5岁，经常感冒",
        "expected_keywords": ["记录", "女儿", "感冒"],
        "category": "Memory"
    },
    {
        "id": 36,
        "name": "Medication Tracking",
        "query": "我在吃阿司匹林和二甲双胍",
        "expected_keywords": ["记录", "药物"],
        "category": "Memory"
    },
    {
        "id": 37,
        "name": "Doctor Preference",
        "query": "我喜欢找李医生看病",
        "expected_keywords": ["记录", "偏好", "李医生"],
        "category": "Memory"
    },
    {
        "id": 38,
        "name": "Health Goals",
        "query": "我想减重10公斤",
        "expected_keywords": ["目标", "减重", "10公斤"],
        "category": "Memory"
    },
    {
        "id": 39,
        "name": "Insurance Info",
        "query": "我有平安保险的高端医疗险",
        "expected_keywords": ["保险", "记录"],
        "category": "Memory"
    },
    {
        "id": 40,
        "name": "Complex Context",
        "query": "基于我的情况，需要做哪些检查？",
        "expected_keywords": ["高血压", "检查", "建议"],
        "category": "Memory",
        "requires_context": True
    }
]

# Multi-turn conversation test cases (41-70)
MULTI_TURN_TEST_CASES = [
    # Basic Multi-turn (41-45)
    {
        "id": 41,
        "name": "Basic Greeting + Doctor Search",
        "turns": [
            {"query": "你好", "expected": ["你好", "帮助"]},
            {"query": "我住在北京", "expected": ["北京", "需求"]},
            {"query": "帮我找个骨科医生", "expected": ["骨科", "医生", "北京"]}
        ],
        "category": "Multi-turn Basic"
    },
    {
        "id": 42,
        "name": "Symptom Description + Recommendation",
        "turns": [
            {"query": "我最近头痛", "expected": ["头痛", "症状"]},
            {"query": "已经3天了", "expected": ["3天", "持续"]},
            {"query": "还伴有恶心", "expected": ["恶心", "建议", "医生"]}
        ],
        "category": "Multi-turn Medical"
    },
    {
        "id": 43,
        "name": "Appointment Booking Flow",
        "turns": [
            {"query": "我想看医生", "expected": ["医生", "预约"]},
            {"query": "骨科的", "expected": ["骨科"]},
            {"query": "这周五下午可以吗", "expected": ["周五", "下午", "时间"]}
        ],
        "category": "Multi-turn Appointment"
    },
    {
        "id": 44,
        "name": "Product Inquiry + Purchase",
        "turns": [
            {"query": "有什么助眠产品吗", "expected": ["助眠", "产品"]},
            {"query": "价格怎么样", "expected": ["价格", "元"]},
            {"query": "怎么购买", "expected": ["购买", "小程序", "商城"]}
        ],
        "category": "Multi-turn Product"
    },
    {
        "id": 45,
        "name": "Emergency Triage",
        "turns": [
            {"query": "我不太舒服", "expected": ["不舒服", "症状"]},
            {"query": "胸口有点闷", "expected": ["胸口", "闷"]},
            {"query": "还有点喘不上气", "expected": ["120", "急救", "立即"]}
        ],
        "category": "Multi-turn Emergency"
    },
    
    # Complex Medical Consultation (46-50)
    {
        "id": 46,
        "name": "Diabetes Management",
        "turns": [
            {"query": "我有糖尿病", "expected": ["糖尿病"]},
            {"query": "血糖最近控制不好", "expected": ["血糖", "控制"]},
            {"query": "空腹血糖8.5", "expected": ["8.5", "偏高", "建议"]},
            {"query": "需要调整药物吗", "expected": ["药物", "医生", "调整"]}
        ],
        "category": "Multi-turn Chronic"
    },
    {
        "id": 47,
        "name": "Child Health Consultation",
        "turns": [
            {"query": "我孩子6岁", "expected": ["孩子", "6岁"]},
            {"query": "最近不爱吃饭", "expected": ["吃饭", "食欲"]},
            {"query": "还经常说累", "expected": ["累", "疲劳"]},
            {"query": "需要做什么检查", "expected": ["检查", "建议", "儿科"]}
        ],
        "category": "Multi-turn Pediatric"
    },
    {
        "id": 48,
        "name": "Medication Interaction Check",
        "turns": [
            {"query": "我在吃降压药", "expected": ["降压药"]},
            {"query": "医生又开了抗生素", "expected": ["抗生素"]},
            {"query": "这两种药能一起吃吗", "expected": ["药物", "相互作用", "注意"]}
        ],
        "category": "Multi-turn Medication"
    },
    {
        "id": 49,
        "name": "Post-Surgery Follow-up",
        "turns": [
            {"query": "我上周做了膝盖手术", "expected": ["膝盖", "手术"]},
            {"query": "现在还有点肿", "expected": ["肿", "术后"]},
            {"query": "这正常吗", "expected": ["正常", "恢复", "注意"]}
        ],
        "category": "Multi-turn Follow-up"
    },
    {
        "id": 50,
        "name": "Health Check Planning",
        "turns": [
            {"query": "我想做个全面体检", "expected": ["体检", "全面"]},
            {"query": "有什么套餐推荐", "expected": ["套餐", "推荐"]},
            {"query": "大概多少钱", "expected": ["价格", "费用"]},
            {"query": "需要预约吗", "expected": ["预约", "时间"]}
        ],
        "category": "Multi-turn Health Check"
    },
    
    # Memory-based Multi-turn (51-55)
    {
        "id": 51,
        "name": "Personal Info + Recommendation",
        "turns": [
            {"query": "我叫王芳，52岁", "expected": ["记录", "信息"]},
            {"query": "有高血压和糖尿病", "expected": ["高血压", "糖尿病", "记录"]},
            {"query": "推荐个适合我的医生", "expected": ["王芳", "高血压", "糖尿病", "医生"]}
        ],
        "category": "Multi-turn Memory"
    },
    {
        "id": 52,
        "name": "Allergy Info + Product Check",
        "turns": [
            {"query": "我对花生过敏", "expected": ["花生", "过敏", "记录"]},
            {"query": "这个保健品含花生吗", "expected": ["花生", "过敏", "注意", "成分"]}
        ],
        "category": "Multi-turn Allergy"
    },
    {
        "id": 53,
        "name": "Location + Clinic Search",
        "turns": [
            {"query": "我住在浦东新区", "expected": ["浦东", "记录"]},
            {"query": "附近有诊所吗", "expected": ["浦东", "附近", "诊所"]}
        ],
        "category": "Multi-turn Location"
    },
    {
        "id": 54,
        "name": "Previous Condition + Update",
        "turns": [
            {"query": "上次说的失眠问题", "expected": ["失眠"]},
            {"query": "按你的建议调整作息了", "expected": ["建议", "调整"]},
            {"query": "现在好多了", "expected": ["好转", "继续"]}
        ],
        "category": "Multi-turn Progress"
    },
    {
        "id": 55,
        "name": "Family Health Management",
        "turns": [
            {"query": "我们全家都在你们这看病", "expected": ["全家", "记录"]},
            {"query": "我老公需要看心脏科", "expected": ["心脏科", "预约"]},
            {"query": "孩子要打疫苗", "expected": ["疫苗", "儿科"]}
        ],
        "category": "Multi-turn Family"
    },
    
    # Complex Scenarios (56-60)
    {
        "id": 56,
        "name": "Chronic Disease Management",
        "turns": [
            {"query": "我的高血压控制得怎么样", "expected": ["高血压", "控制"]},
            {"query": "上个月测的是150/95", "expected": ["150/95", "偏高"]},
            {"query": "需要增加药量吗", "expected": ["药量", "调整", "医生"]},
            {"query": "饮食上要注意什么", "expected": ["饮食", "低盐", "建议"]}
        ],
        "category": "Multi-turn Chronic Care"
    },
    {
        "id": 57,
        "name": "Pregnancy Consultation",
        "turns": [
            {"query": "我怀孕3个月了", "expected": ["怀孕", "3个月"]},
            {"query": "最近总是恶心", "expected": ["恶心", "孕吐", "正常"]},
            {"query": "需要补充什么营养", "expected": ["营养", "叶酸", "维生素"]},
            {"query": "下次产检什么时候", "expected": ["产检", "时间", "预约"]}
        ],
        "category": "Multi-turn Pregnancy"
    },
    {
        "id": 58,
        "name": "Mental Health Support",
        "turns": [
            {"query": "最近压力很大", "expected": ["压力", "情绪"]},
            {"query": "晚上睡不好", "expected": ["睡眠", "失眠"]},
            {"query": "白天没精神", "expected": ["疲劳", "状态"]},
            {"query": "需要看心理医生吗", "expected": ["心理", "医生", "建议"]}
        ],
        "category": "Multi-turn Mental Health"
    },
    {
        "id": 59,
        "name": "Vaccination Schedule",
        "turns": [
            {"query": "宝宝6个月大", "expected": ["宝宝", "6个月"]},
            {"query": "该打什么疫苗", "expected": ["疫苗", "接种"]},
            {"query": "有什么注意事项", "expected": ["注意", "反应", "发烧"]},
            {"query": "下一针什么时候", "expected": ["下次", "时间", "安排"]}
        ],
        "category": "Multi-turn Vaccination"
    },
    {
        "id": 60,
        "name": "Elder Care Consultation",
        "turns": [
            {"query": "我父亲75岁", "expected": ["父亲", "75岁"]},
            {"query": "最近记忆力下降", "expected": ["记忆", "下降"]},
            {"query": "有时候会忘事", "expected": ["忘事", "症状"]},
            {"query": "需要做什么检查", "expected": ["检查", "记忆", "评估", "老年"]}
        ],
        "category": "Multi-turn Elder Care"
    },
    
    # Advanced Multi-turn with Context (61-70)
    {
        "id": 61,
        "name": "Complete Health Journey",
        "turns": [
            {"query": "我想全面管理健康", "expected": ["健康", "管理"]},
            {"query": "先从体检开始吧", "expected": ["体检", "开始"]},
            {"query": "有高端体检套餐吗", "expected": ["高端", "套餐"]},
            {"query": "包含哪些项目", "expected": ["项目", "检查"]},
            {"query": "可以这周安排吗", "expected": ["本周", "安排", "预约"]}
        ],
        "category": "Multi-turn Journey"
    },
    {
        "id": 62,
        "name": "Treatment Plan Discussion",
        "turns": [
            {"query": "医生建议我做手术", "expected": ["手术", "建议"]},
            {"query": "我有点担心风险", "expected": ["风险", "担心"]},
            {"query": "有其他治疗方案吗", "expected": ["方案", "选择", "治疗"]},
            {"query": "哪种效果更好", "expected": ["效果", "比较", "建议"]},
            {"query": "我需要时间考虑", "expected": ["考虑", "理解", "支持"]}
        ],
        "category": "Multi-turn Decision"
    },
    {
        "id": 63,
        "name": "Rehabilitation Progress",
        "turns": [
            {"query": "我在做康复训练", "expected": ["康复", "训练"]},
            {"query": "腿部力量恢复慢", "expected": ["腿部", "力量", "恢复"]},
            {"query": "有什么加强练习吗", "expected": ["练习", "加强", "建议"]},
            {"query": "多久能正常走路", "expected": ["时间", "恢复", "预期"]}
        ],
        "category": "Multi-turn Rehab"
    },
    {
        "id": 64,
        "name": "Lifestyle Modification",
        "turns": [
            {"query": "医生说我要改变生活方式", "expected": ["生活方式", "改变"]},
            {"query": "具体怎么做呢", "expected": ["具体", "建议"]},
            {"query": "饮食方面呢", "expected": ["饮食", "健康", "建议"]},
            {"query": "运动要注意什么", "expected": ["运动", "注意", "适度"]},
            {"query": "能推荐营养师吗", "expected": ["营养师", "推荐", "专业"]}
        ],
        "category": "Multi-turn Lifestyle"
    },
    {
        "id": 65,
        "name": "Insurance Coverage Check",
        "turns": [
            {"query": "我有医保", "expected": ["医保", "保险"]},
            {"query": "还有商业保险", "expected": ["商业保险", "补充"]},
            {"query": "看病能报销多少", "expected": ["报销", "比例", "费用"]},
            {"query": "需要什么手续", "expected": ["手续", "材料", "流程"]}
        ],
        "category": "Multi-turn Insurance"
    },
    {
        "id": 66,
        "name": "Second Opinion Request",
        "turns": [
            {"query": "我想听听其他医生意见", "expected": ["意见", "其他医生"]},
            {"query": "之前诊断是胃炎", "expected": ["胃炎", "诊断"]},
            {"query": "但吃药效果不好", "expected": ["效果", "不好", "药物"]},
            {"query": "能约其他专家吗", "expected": ["专家", "预约", "第二"]}
        ],
        "category": "Multi-turn Second Opinion"
    },
    {
        "id": 67,
        "name": "Travel Health Prep",
        "turns": [
            {"query": "下个月要出国", "expected": ["出国", "旅行"]},
            {"query": "去非洲", "expected": ["非洲", "目的地"]},
            {"query": "需要打什么疫苗", "expected": ["疫苗", "预防", "旅行"]},
            {"query": "要准备什么药品", "expected": ["药品", "准备", "常备"]}
        ],
        "category": "Multi-turn Travel"
    },
    {
        "id": 68,
        "name": "Pain Management",
        "turns": [
            {"query": "我有慢性疼痛", "expected": ["慢性", "疼痛"]},
            {"query": "主要是腰部", "expected": ["腰部", "位置"]},
            {"query": "已经半年了", "expected": ["半年", "持续"]},
            {"query": "止痛药效果有限", "expected": ["止痛药", "效果", "有限"]},
            {"query": "有其他办法吗", "expected": ["办法", "治疗", "方案"]}
        ],
        "category": "Multi-turn Pain"
    },
    {
        "id": 69,
        "name": "Preventive Care Plan",
        "turns": [
            {"query": "我想做预防保健", "expected": ["预防", "保健"]},
            {"query": "家族有心脏病史", "expected": ["家族", "心脏病", "风险"]},
            {"query": "应该注意什么", "expected": ["注意", "预防", "建议"]},
            {"query": "多久检查一次", "expected": ["检查", "频率", "定期"]},
            {"query": "生活上怎么预防", "expected": ["生活", "预防", "方式"]}
        ],
        "category": "Multi-turn Prevention"
    },
    {
        "id": 70,
        "name": "Comprehensive Care Coordination",
        "turns": [
            {"query": "我需要看多个科室", "expected": ["多个", "科室"]},
            {"query": "内科、骨科和眼科", "expected": ["内科", "骨科", "眼科"]},
            {"query": "能统一安排吗", "expected": ["统一", "安排", "协调"]},
            {"query": "最好是同一天", "expected": ["同一天", "时间", "方便"]},
            {"query": "费用大概多少", "expected": ["费用", "总计", "预估"]}
        ],
        "category": "Multi-turn Coordination"
    }
]

# Global tracking
debug_events = []
tool_calls = []
thinking_steps = []

async def test_response_api(session, test_data, response_id=None):
    """Test using Response API with streaming"""
    try:
        # Prepare request
        user_id = test_data.get('user_id', f"test_user_{test_data['id']}")
        
        request_data = {
            "model": "gpt-4-turbo",
            "input": test_data['query'],
            "user_id": str(user_id),
            "metadata": {"test_id": test_data['id']}
        }
        
        if response_id:
            request_data["previous_response_id"] = response_id
        
        # Make streaming request
        start_time = time.time()
        full_response = ""
        new_response_id = None
        tools_used = []
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/responses/stream",
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            
            if response.status != 200:
                error_text = await response.text()
                return {
                    "success": False,
                    "error": f"HTTP {response.status}: {error_text}",
                    "response_time": time.time() - start_time
                }
            
            # Process streaming response
            async for line in response.content:
                if line:
                    decoded = line.decode('utf-8').strip()
                    
                    if decoded.startswith('data: '):
                        data_str = decoded[6:]
                        
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            data = json.loads(data_str)
                            event_type = data.get('event', '')
                            event_data = data.get('data', {})
                            
                            if event_type == 'response.created':
                                new_response_id = event_data.get('id')
                            
                            elif event_type == 'response.output_item.done':
                                item = event_data.get('item', {})
                                item_type = item.get('type', '')
                                
                                if item_type == 'text':
                                    text = item.get('text', '')
                                    if not ('思考' in text or 'Thought' in text):
                                        # Concatenate responses instead of overwriting
                                        if full_response and text:
                                            full_response += "\n" + text
                                        elif text:
                                            full_response = text
                                
                                elif item_type == 'tool_use':
                                    tool_info = item.get('tool_use', {})
                                    tool_name = tool_info.get('name', '')
                                    if tool_name:
                                        tools_used.append(tool_name)
                        
                        except json.JSONDecodeError:
                            pass
            
            elapsed_time = time.time() - start_time
            
            return {
                "success": True,
                "response": full_response,
                "response_id": new_response_id,
                "response_time": elapsed_time,
                "tools_used": tools_used
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response_time": 0
        }

async def test_single_turn_case(session, test_case):
    """Test a single-turn conversation"""
    print_colored(f"\n🔹 Test #{test_case['id']}: {test_case['name']}", Colors.CYAN)
    print(f"   Query: {test_case['query']}")
    
    result = await test_response_api(session, test_case)
    
    if result['success']:
        response = result['response']
        print_colored(f"   Response: {response[:150]}...", Colors.GREEN)
        
        # Check keywords
        found_keywords = []
        missing_keywords = []
        for keyword in test_case.get('expected_keywords', []):
            if keyword.lower() in response.lower():
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        passed = len(missing_keywords) == 0
        
        if passed:
            print_colored(f"   ✅ PASSED ({result['response_time']:.2f}s)", Colors.GREEN)
        else:
            print_colored(f"   ❌ FAILED - Missing: {missing_keywords}", Colors.RED)
        
        if result['tools_used']:
            print(f"   🔧 Tools used: {', '.join(result['tools_used'])}")
        
        return {
            "test_id": test_case['id'],
            "test_name": test_case['name'],
            "passed": passed,
            "response_time": result['response_time'],
            "response": response,
            "found_keywords": found_keywords,
            "missing_keywords": missing_keywords,
            "tools_used": result['tools_used']
        }
    else:
        print_colored(f"   ❌ ERROR: {result['error']}", Colors.RED)
        return {
            "test_id": test_case['id'],
            "test_name": test_case['name'],
            "passed": False,
            "error": result['error'],
            "response_time": result['response_time']
        }

async def test_multi_turn_case(session, test_case):
    """Test a multi-turn conversation"""
    print_colored(f"\n🔸 Test #{test_case['id']}: {test_case['name']}", Colors.MAGENTA)
    
    results = []
    response_id = None
    all_passed = True
    total_time = 0
    
    for i, turn in enumerate(test_case['turns'], 1):
        print(f"\n   Turn {i}: {turn['query']}")
        
        test_data = {
            "id": f"{test_case['id']}_turn_{i}",
            "query": turn['query'],
            "user_id": f"mt_test_{test_case['id']}"
        }
        
        result = await test_response_api(session, test_data, response_id)
        
        if result['success']:
            response = result['response']
            response_id = result.get('response_id')  # Use for next turn
            print_colored(f"   Response: {response[:150]}...", Colors.GREEN)
            
            # Check expected keywords for this turn
            found = []
            missing = []
            for keyword in turn.get('expected', []):
                if keyword.lower() in response.lower():
                    found.append(keyword)
                else:
                    missing.append(keyword)
            
            turn_passed = len(missing) == 0
            all_passed = all_passed and turn_passed
            
            if turn_passed:
                print_colored(f"   ✅ Turn {i} passed", Colors.GREEN)
            else:
                print_colored(f"   ❌ Turn {i} failed - Missing: {missing}", Colors.RED)
            
            if result['tools_used']:
                print(f"   🔧 Tools: {', '.join(result['tools_used'])}")
            
            total_time += result['response_time']
            
            results.append({
                "turn": i,
                "query": turn['query'],
                "response": response,
                "passed": turn_passed,
                "found_keywords": found,
                "missing_keywords": missing,
                "tools_used": result['tools_used'],
                "response_time": result['response_time']
            })
        else:
            print_colored(f"   ❌ ERROR: {result['error']}", Colors.RED)
            all_passed = False
            results.append({
                "turn": i,
                "query": turn['query'],
                "passed": False,
                "error": result['error']
            })
            break
    
    return {
        "test_id": test_case['id'],
        "test_name": test_case['name'],
        "passed": all_passed,
        "total_turns": len(test_case['turns']),
        "successful_turns": len([r for r in results if r.get('passed', False)]),
        "total_time": total_time,
        "turn_results": results
    }

async def setup_memory_context(session, user_id, messages):
    """Setup memory context for a user"""
    try:
        setup_data = {
            "user_id": str(user_id),
            "messages": messages
        }
        
        async with session.post(f"{BASE_URL}/v2/humansa/memory/add", json=setup_data) as resp:
            if resp.status == 200:
                print_colored(f"   ✅ Memory context setup for user {user_id}", Colors.GREEN)
                return True
            else:
                print_colored(f"   ❌ Failed to setup memory: {resp.status}", Colors.RED)
                return False
    except Exception as e:
        print_colored(f"   ❌ Memory setup error: {e}", Colors.RED)
        return False

async def run_all_tests():
    """Run all 70 test cases"""
    print_section("HUMANSA V2 Extended Test Suite - 70 Test Cases")
    print(f"Total test cases: 70")
    print(f"- Single-turn tests: 40")
    print(f"- Multi-turn tests: 30")
    print_colored("Using Response API with full tool transparency", Colors.CYAN)
    
    async with aiohttp.ClientSession() as session:
        # Check health
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
                if resp.status == 200:
                    print_colored(f"\n✅ V2 Health Check Passed", Colors.GREEN)
                else:
                    print_colored(f"❌ V2 Health Check Failed: {resp.status}", Colors.RED)
                    return
        except Exception as e:
            print_colored(f"❌ Cannot connect to server: {e}", Colors.RED)
            return
        
        all_results = []
        
        # Setup memory context for tests that need it
        print_section("Setting up Memory Context")
        
        # For test cases 33-34 (need context from 31-32)
        await setup_memory_context(session, "test_user_31", [
            {"role": "user", "content": "我叫李明，45岁，有高血压"},
            {"role": "assistant", "content": "好的，我已经记录了您的信息"}
        ])
        
        await setup_memory_context(session, "test_user_32", [
            {"role": "user", "content": "我对青霉素过敏"},
            {"role": "assistant", "content": "已记录您对青霉素过敏"}
        ])
        
        # Copy context for recall tests
        await setup_memory_context(session, "test_user_33", [
            {"role": "user", "content": "我叫李明，45岁，有高血压"},
            {"role": "assistant", "content": "好的，我已经记录了您的信息"}
        ])
        
        await setup_memory_context(session, "test_user_34", [
            {"role": "user", "content": "我对青霉素过敏"},
            {"role": "assistant", "content": "已记录您对青霉素过敏"}
        ])
        
        # Run single-turn tests (1-40)
        print_section("Running Single-Turn Tests (1-40)")
        single_turn_passed = 0
        
        for test_case in SINGLE_TURN_TEST_CASES:
            # Handle special cases that need context
            if test_case.get('requires_context'):
                if test_case['id'] == 33:
                    test_case['user_id'] = 'test_user_33'
                elif test_case['id'] == 34:
                    test_case['user_id'] = 'test_user_34'
                elif test_case['id'] == 40:
                    # Setup context for complex query
                    test_case['user_id'] = 'test_user_40'
                    await setup_memory_context(session, "test_user_40", [
                        {"role": "user", "content": "我45岁，有高血压"},
                        {"role": "assistant", "content": "已记录您的健康信息"}
                    ])
            
            result = await test_single_turn_case(session, test_case)
            all_results.append(result)
            if result.get('passed', False):
                single_turn_passed += 1
            
            await asyncio.sleep(0.5)  # Small delay between tests
        
        # Run multi-turn tests (41-70)
        print_section("Running Multi-Turn Tests (41-70)")
        multi_turn_passed = 0
        
        for test_case in MULTI_TURN_TEST_CASES:
            result = await test_multi_turn_case(session, test_case)
            all_results.append(result)
            if result.get('passed', False):
                multi_turn_passed += 1
            
            await asyncio.sleep(1)  # Longer delay between multi-turn tests
        
        # Summary
        print_section("TEST SUMMARY")
        total_passed = single_turn_passed + multi_turn_passed
        
        print(f"Total tests: 70")
        print_colored(f"Passed: {total_passed}", Colors.GREEN)
        print_colored(f"Failed: {70 - total_passed}", Colors.RED)
        print(f"\nBreakdown:")
        print(f"  Single-turn: {single_turn_passed}/40 passed")
        print(f"  Multi-turn: {multi_turn_passed}/30 passed")
        print(f"  Overall success rate: {(total_passed/70*100):.1f}%")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"HUMANSA_v2_70cases_results_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "total_tests": 70,
                "passed": total_passed,
                "failed": 70 - total_passed,
                "single_turn_passed": single_turn_passed,
                "multi_turn_passed": multi_turn_passed,
                "success_rate": total_passed/70,
                "results": all_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\nDetailed results saved to: {results_file}")
        
        # Show failed tests
        if total_passed < 70:
            print_section("FAILED TESTS")
            for result in all_results:
                if not result.get('passed', False):
                    print_colored(f"\nTest {result['test_id']}: {result.get('test_name', 'N/A')}", Colors.RED)
                    if 'error' in result:
                        print(f"  Error: {result['error']}")
                    elif 'missing_keywords' in result:
                        print(f"  Missing: {result['missing_keywords']}")
                    elif 'turn_results' in result:
                        # Multi-turn failure
                        for turn in result['turn_results']:
                            if not turn.get('passed', False):
                                print(f"  Turn {turn['turn']} failed - Missing: {turn.get('missing_keywords', [])}")

if __name__ == "__main__":
    # Enable colored output on Windows
    if sys.platform == "win32":
        os.system("color")
    
    asyncio.run(run_all_tests())