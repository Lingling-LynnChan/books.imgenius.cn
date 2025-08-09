import random
import string
import secrets
from datetime import datetime, timedelta
from io import BytesIO
import base64

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.views.generic import TemplateView
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import IntegrityError
from PIL import Image, ImageDraw, ImageFont

from .models import User, UserToken
from .utils import generate_verification_code, generate_token


class LoginView(TemplateView):
    template_name = 'accounts/login.html'
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('books:index')
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', '').strip()
        captcha_code = request.POST.get('captcha_code', '').strip()
        email_code = request.POST.get('email_code', '').strip()
        remember_me = request.POST.get('remember_me') == 'on'
        step = request.POST.get('step', '1')
        
        if step == '1':
            # 第一步：验证邮箱和图片验证码
            if not email or not captcha_code:
                messages.error(request, '请填写邮箱和验证码')
                return render(request, self.template_name)
            
            # 验证图片验证码
            session_captcha = request.session.get('captcha_code', '')
            print(f"用户输入: {captcha_code}, Session中存储: {session_captcha}")
            if captcha_code.upper() != session_captcha.upper():
                messages.error(request, '图片验证码错误')
                return render(request, self.template_name)
            
            # 发送邮件验证码
            verification_code = generate_verification_code()
            cache_key = f'email_verification_{email}'
            cache.set(cache_key, verification_code, 3600)  # 1小时过期
            
            try:
                # 在开发环境下直接跳过邮件发送
                if settings.DEBUG:
                    print(f"[开发模式] 发送到 {email} 的验证码是: {verification_code}")
                    messages.success(request, f'验证码已发送到您的邮箱 (开发模式)')
                else:
                    send_mail(
                        subject='阅读网站登录验证码',
                        message=f'您的验证码是：{verification_code}，有效期1小时。',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    messages.success(request, '验证码已发送到您的邮箱')
                
                return render(request, self.template_name, {
                    'step': '2',
                    'email': email,
                    'remember_me': remember_me
                })
            except Exception as e:
                print(f"邮件发送失败: {e}")
                messages.error(request, f'邮件发送失败，验证码是: {verification_code} (开发用)')
                return render(request, self.template_name, {
                    'step': '2',
                    'email': email,
                    'remember_me': remember_me
                })

        elif step == '2':
            # 第二步：验证邮件验证码
            email = request.POST.get('email', '').strip()
            if not email or not email_code:
                messages.error(request, '请填写邮箱验证码')
                return render(request, self.template_name, {
                    'step': '2',
                    'email': email,
                    'remember_me': remember_me
                })
            
            # 验证邮件验证码
            cache_key = f'email_verification_{email}'
            cached_code = cache.get(cache_key)
            
            if not cached_code or email_code != cached_code:
                messages.error(request, '邮件验证码错误或已过期')
                return render(request, self.template_name, {
                    'step': '2',
                    'email': email,
                    'remember_me': remember_me
                })
            
            # 删除验证码（一次性使用）
            cache.delete(cache_key)
            
            # 获取或创建用户
            user, created = User.objects.get_or_create(email=email)
            
            # 生成令牌
            token = generate_token()
            expires_at = timezone.now() + timedelta(days=30 if remember_me else 7)
            
            UserToken.objects.create(
                user=user,
                token=token,
                expires_at=expires_at,
                is_remember_me=remember_me
            )
            
            # 登录用户
            login(request, user)
            request.session['user_token'] = token
            
            messages.success(request, '登录成功')
            return redirect('books:index')
        
        return render(request, self.template_name)


class ProfileView(TemplateView):
    template_name = 'accounts/profile.html'
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        action = request.POST.get('action')
        
        if action == 'update_display_name':
            display_name = request.POST.get('display_name', '').strip()
            if display_name:
                try:
                    request.user.display_name = display_name
                    request.user.save()
                    messages.success(request, '显示名称更新成功')
                except IntegrityError:
                    messages.error(request, '该显示名称已被其他用户使用，请选择其他名称')
            else:
                messages.error(request, '显示名称不能为空')
        
        elif action == 'update_email':
            new_email = request.POST.get('new_email', '').strip()
            verification_code = request.POST.get('verification_code', '').strip()
            
            if not new_email or not verification_code:
                messages.error(request, '请填写新邮箱和验证码')
                return render(request, self.template_name)
            
            # 验证邮件验证码
            cache_key = f'email_verification_{new_email}'
            cached_code = cache.get(cache_key)
            
            if not cached_code or verification_code != cached_code:
                messages.error(request, '验证码错误或已过期')
                return render(request, self.template_name)
            
            # 检查邮箱是否已被使用
            if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                messages.error(request, '该邮箱已被其他用户使用')
                return render(request, self.template_name)
            
            # 删除验证码
            cache.delete(cache_key)
            
            # 更新邮箱
            request.user.email = new_email
            request.user.save()
            messages.success(request, '邮箱更新成功')
        
        return render(request, self.template_name)


def logout_view(request):
    """用户退出登录"""
    # 删除用户令牌
    user_token = request.session.get('user_token')
    if user_token:
        UserToken.objects.filter(token=user_token).delete()
    
    logout(request)
    messages.success(request, '已退出登录')
    return redirect('accounts:login')


@csrf_exempt
def verify_email(request):
    """发送邮箱验证码"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            return JsonResponse({'success': False, 'message': '请填写邮箱地址'})
        
        verification_code = generate_verification_code()
        cache_key = f'email_verification_{email}'
        cache.set(cache_key, verification_code, 3600)  # 1小时过期
        
        try:
            send_mail(
                subject='阅读网站邮箱验证码',
                message=f'您的验证码是：{verification_code}，有效期1小时。',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            return JsonResponse({'success': True, 'message': '验证码已发送'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': '发送失败，请稍后重试'})
    
    return JsonResponse({'success': False, 'message': '请求方法错误'})


@csrf_exempt
def send_verification_code(request):
    """发送邮箱验证码API"""
    return verify_email(request)


@csrf_exempt
def verify_captcha(request):
    """验证图片验证码"""
    if request.method == 'POST':
        captcha_code = request.POST.get('captcha_code', '').strip()
        session_captcha = request.session.get('captcha_code', '')
        
        print(f"AJAX验证 - 用户输入: {captcha_code}, Session存储: {session_captcha}")
        
        if captcha_code.upper() == session_captcha.upper():
            return JsonResponse({'success': True, 'message': '验证码正确'})
        else:
            return JsonResponse({'success': False, 'message': '验证码错误'})
    
    return JsonResponse({'success': False, 'message': '请求方法错误'})


def generate_captcha(request):
    """生成图片验证码"""
    # 生成随机验证码
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    request.session['captcha_code'] = code  # 存储原始大小写
    
    # 添加调试信息
    print(f"生成验证码: {code}, 存储到session: {request.session['captcha_code']}")
    
    # 创建图片
    width, height = 120, 50
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # 添加验证码文字
    try:
        # 尝试使用系统字体
        font = ImageFont.load_default()
    except:
        font = None
    
    # 绘制验证码
    text_width = 80
    text_height = 30
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.text((x, y), code, fill='black', font=font)
    
    # 添加干扰线
    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill='gray', width=1)
    
    # 保存图片到内存
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    
    return HttpResponse(buffer.getvalue(), content_type='image/png')


class CheckDisplayNameView(View):
    """检查显示名称是否可用"""
    
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'available': False, 'message': '请先登录'})
        
        display_name = request.POST.get('display_name', '').strip()
        
        if not display_name:
            return JsonResponse({'available': False, 'message': '显示名称不能为空'})
        
        # 检查是否与当前用户的显示名称相同
        if request.user.display_name == display_name:
            return JsonResponse({'available': True, 'message': '这是您当前的显示名称'})
        
        # 检查是否有其他用户使用了这个显示名称
        if User.objects.filter(display_name=display_name).exists():
            return JsonResponse({'available': False, 'message': '该显示名称已被其他用户使用'})
        
        return JsonResponse({'available': True, 'message': '显示名称可以使用'})
