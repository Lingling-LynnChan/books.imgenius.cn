"""
AI审核工具类
调用AI接口进行内容审核
"""
import requests
import json
from django.conf import settings


def check_content_by_ai(content):
    """
    调用AI接口审核内容
    
    Args:
        content (str): 要审核的内容
    
    Returns:
        dict: 审核结果
        {
            'approved': bool,  # 是否通过审核
            'reason': str,     # 拒绝原因（如果未通过）
            'confidence': float  # 置信度
        }
    """
    try:
        # 构建请求数据
        data = {
            'content': content,
            'check_type': 'text',
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {settings.AI_CHECK_API_KEY}',
        }
        
        # 发送请求到AI审核接口
        response = requests.post(
            settings.AI_CHECK_API_URL,
            data=json.dumps(data),
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                'approved': result.get('approved', False),
                'reason': result.get('reason', ''),
                'confidence': result.get('confidence', 0.0)
            }
        else:
            # API调用失败，默认不通过
            return {
                'approved': False,
                'reason': 'AI审核服务暂时不可用',
                'confidence': 0.0
            }
    
    except requests.exceptions.Timeout:
        return {
            'approved': False,
            'reason': 'AI审核服务超时',
            'confidence': 0.0
        }
    except requests.exceptions.RequestException as e:
        return {
            'approved': False,
            'reason': f'AI审核服务连接失败: {str(e)}',
            'confidence': 0.0
        }
    except Exception as e:
        return {
            'approved': False,
            'reason': f'AI审核异常: {str(e)}',
            'confidence': 0.0
        }


def batch_check_content(contents):
    """
    批量审核内容
    
    Args:
        contents (list): 要审核的内容列表
    
    Returns:
        list: 审核结果列表
    """
    results = []
    
    for content in contents:
        result = check_content_by_ai(content)
        results.append(result)
    
    return results


def simple_content_filter(content):
    """
    简单的本地内容过滤（作为AI审核的备用方案）
    
    Args:
        content (str): 要检查的内容
    
    Returns:
        dict: 审核结果
    """
    # 敏感词列表（示例）
    sensitive_words = [
        '暴力', '色情', '政治敏感', '违法', '广告',
        # 可以根据需要添加更多敏感词
    ]
    
    content_lower = content.lower()
    
    for word in sensitive_words:
        if word in content_lower:
            return {
                'approved': False,
                'reason': f'包含敏感词: {word}',
                'confidence': 0.9
            }
    
    # 检查内容长度
    if len(content.strip()) < 5:
        return {
            'approved': False,
            'reason': '内容过短',
            'confidence': 0.8
        }
    
    return {
        'approved': True,
        'reason': '',
        'confidence': 0.7
    }
