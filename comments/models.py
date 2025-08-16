from django.db import models
from django.utils import timezone
from accounts.models import User
from books.models import Book, Chapter


class Comment(models.Model):
    """评论模型 - 存储在SQLite中"""
    REVIEW_STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '审核通过'),
        ('rejected', '审核不通过'),
    ]
    
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='comments', verbose_name='所属作品')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='comments', 
                               verbose_name='所属章节', blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', verbose_name='评论者')
    content = models.TextField('评论内容')
    
    # 审核相关字段
    content_pending = models.TextField('待审核内容', blank=True, null=True)
    ai_check = models.CharField('AI审核状态', max_length=20, choices=REVIEW_STATUS_CHOICES, default='pending')
    adm_check = models.CharField('管理员审核状态', max_length=20, choices=REVIEW_STATUS_CHOICES, blank=True, null=True)
    reject_reason = models.TextField('拒绝原因', blank=True)
    
    is_visible = models.BooleanField('是否可见', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'comments'
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['-created_at']
    
    def __str__(self):
        comment_type = "章节评论" if self.chapter else "作品评论"
        return f"{self.author.username} 对 {self.book.title} 的{comment_type}"
    
    @property
    def display_content(self):
        """显示内容（优先显示待审核内容，否则显示已发布内容）"""
        return self.content_pending or self.content
    
    @property
    def is_approved(self):
        """是否已审核通过"""
        if self.adm_check is not None:
            return self.adm_check == 'approved'
        return self.ai_check == 'approved'
    
    def save(self, *args, **kwargs):
        """保存时自动更新可见性"""
        self.is_visible = self.is_approved
        super().save(*args, **kwargs)
