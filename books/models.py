from django.db import models
from django.utils import timezone
from accounts.models import User


class Book(models.Model):
    """作品模型 - 存储在MySQL中"""
    REVIEW_STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '审核通过'),
        ('rejected', '审核不通过'),
    ]
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='books', verbose_name='作者')
    title = models.CharField('作品名', max_length=200)
    description = models.TextField('简介', blank=True)
    
    # 审核相关字段
    title_pending = models.CharField('待审核作品名', max_length=200, blank=True, null=True)
    description_pending = models.TextField('待审核简介', blank=True, null=True)
    
    ai_check_title = models.CharField('标题AI审核状态', max_length=20, choices=REVIEW_STATUS_CHOICES, default='pending')
    ai_check_description = models.CharField('简介AI审核状态', max_length=20, choices=REVIEW_STATUS_CHOICES, default='pending')
    adm_check_title = models.CharField('标题管理员审核状态', max_length=20, choices=REVIEW_STATUS_CHOICES, blank=True, null=True)
    adm_check_description = models.CharField('简介管理员审核状态', max_length=20, choices=REVIEW_STATUS_CHOICES, blank=True, null=True)
    
    # 拒绝原因
    title_reject_reason = models.TextField('标题拒绝原因', blank=True)
    description_reject_reason = models.TextField('简介拒绝原因', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    last_chapter_update = models.DateTimeField('最后章节更新时间', blank=True, null=True)
    
    # MongoDB中的文档ID（存储章节内容）
    mongodb_id = models.CharField('MongoDB文档ID', max_length=50, blank=True, null=True)
    
    class Meta:
        db_table = 'books'
        verbose_name = '作品'
        verbose_name_plural = '作品'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.title
    
    @property
    def display_title(self):
        """显示标题（包含审核状态）"""
        if self.title_pending and self.author:
            if self.adm_check_title == 'rejected':
                return f"{self.title_pending} (审核不通过)"
            elif (self.ai_check_title == 'pending' or 
                  (self.adm_check_title != 'approved' and self.adm_check_title is not None)):
                return f"{self.title_pending} (审核中)"
        return self.title
    
    @property
    def display_description(self):
        """显示简介（包含审核状态）"""
        if self.description_pending and self.author:
            if self.adm_check_description == 'rejected':
                return f"{self.description_pending} (审核不通过)"
            elif (self.ai_check_description == 'pending' or 
                  (self.adm_check_description != 'approved' and self.adm_check_description is not None)):
                return f"{self.description_pending} (审核中)"
        return self.description
    
    @property
    def is_title_approved(self):
        """标题是否已审核通过"""
        # 如果管理员已审核，以管理员结果为准
        if self.adm_check_title is not None:
            return self.adm_check_title == 'approved'
        # 否则以AI审核结果为准
        return self.ai_check_title == 'approved'
    
    @property
    def is_description_approved(self):
        """简介是否已审核通过"""
        # 如果管理员已审核，以管理员结果为准
        if self.adm_check_description is not None:
            return self.adm_check_description == 'approved'
        # 否则以AI审核结果为准
        return self.ai_check_description == 'approved'
    
    @property
    def is_visible_to_public(self):
        """是否对公众可见"""
        return self.is_title_approved and self.is_description_approved


class BookDraft(models.Model):
    """作品草稿 - 用于自动保存"""
    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name='draft')
    title = models.CharField('草稿标题', max_length=200, blank=True)
    description = models.TextField('草稿简介', blank=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'book_drafts'
        verbose_name = '作品草稿'
        verbose_name_plural = '作品草稿'


# MongoDB中的章节内容模型（用于参考，实际存储在MongoDB中）
"""
Chapter 文档结构（存储在MongoDB中）:
{
    "_id": ObjectId,
    "book_id": int,  # 对应MySQL中的Book.id
    "chapter_number": int,  # 章节序号
    "title": str,  # 章节标题
    "content": str,  # 章节内容
    "title_pending": str,  # 待审核标题
    "content_pending": str,  # 待审核内容
    "ai_check_title": str,  # AI审核状态 pending/approved/rejected
    "ai_check_content": str,  # AI审核状态
    "adm_check_title": str,  # 管理员审核状态
    "adm_check_content": str,  # 管理员审核状态
    "title_reject_reason": str,  # 标题拒绝原因
    "content_reject_reason": str,  # 内容拒绝原因
    "created_at": datetime,
    "updated_at": datetime,
    "author_id": int,  # 作者ID
}

ChapterDraft 文档结构（存储在MongoDB中，用于自动保存）:
{
    "_id": ObjectId,
    "book_id": int,
    "chapter_number": int,
    "title": str,
    "content": str,
    "updated_at": datetime,
    "author_id": int,
}
"""
