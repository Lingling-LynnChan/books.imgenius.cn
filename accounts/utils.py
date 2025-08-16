import secrets
import string
import random
from django.conf import settings

def generate_verification_code(length=6):
    """生成邮箱验证码"""
    if settings.DEBUG == True:
        return '9999'
    return ''.join(random.choices(string.digits, k=length))


def generate_token(length=64):
    """生成用户令牌"""
    return secrets.token_urlsafe(length)
