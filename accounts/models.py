from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, display_name=None, **extra_fields):
        if not email:
            raise ValueError('用户必须有邮箱地址')
        
        email = self.normalize_email(email)
        user = self.model(email=email, display_name=display_name, **extra_fields)
        user.set_password(password)  # 正确处理密码哈希
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, display_name=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('超级用户必须有 is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('超级用户必须有 is_superuser=True.')
            
        return self.create_user(email, password, display_name, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField('邮箱', unique=True)
    display_name = models.CharField('显示名称', max_length=50, blank=True, null=True, unique=True)
    is_active = models.BooleanField('是否激活', default=True)
    is_staff = models.BooleanField('是否员工', default=False)
    is_admin = models.BooleanField('是否管理员', default=False)
    date_joined = models.DateTimeField('注册时间', default=timezone.now)
    last_login = models.DateTimeField('最后登录', blank=True, null=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'
    
    def __str__(self):
        return self.email
    
    def has_perm(self, perm, obj=None):
        return self.is_admin
    
    def has_module_perms(self, app_label):
        return self.is_admin
    
    @property
    def can_create_content(self):
        """检查用户是否可以创作内容（需要设置显示名称）"""
        return bool(self.display_name and self.display_name.strip())


class UserToken(models.Model):
    """用户令牌表，存储在MySQL中"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
    token = models.CharField('令牌', max_length=255, unique=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    expires_at = models.DateTimeField('过期时间')
    is_remember_me = models.BooleanField('记住我', default=False)
    
    class Meta:
        db_table = 'user_tokens'
        verbose_name = '用户令牌'
        verbose_name_plural = '用户令牌'
    
    def __str__(self):
        return f'{self.user.email} - {self.token[:20]}...'
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
