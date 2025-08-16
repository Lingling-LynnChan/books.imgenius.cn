from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from books.models import Book, Chapter
from .models import Comment
from books.ai_utils import check_content_by_ai


class AddCommentView(LoginRequiredMixin, TemplateView):
    """添加评论页面"""
    template_name = 'comments/add_comment.html'
    login_url = '/accounts/login/'


class BookCommentsView(LoginRequiredMixin, TemplateView):
    """作品评论页面"""
    template_name = 'comments/book_comments.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        
        book = get_object_or_404(Book, id=book_id)
        
        # 检查权限：作者可以查看自己的所有评论，其他用户只能查看通过审核的公开作品的评论
        if book.author != self.request.user and not book.is_visible_to_public:
            raise Http404("作品不存在")
        
        # 获取作品评论（不包含章节评论）
        # 用户可以查看自己的所有评论（包括审核中的），其他用户只能查看已通过审核的评论
        if book.author == self.request.user:
            # 作者可以查看所有评论
            comments = Comment.objects.filter(
                book=book, 
                chapter__isnull=True
            ).order_by('-created_at')
        else:
            # 其他用户可以查看已通过审核的评论 + 自己的所有评论
            comments = Comment.objects.filter(
                book=book, 
                chapter__isnull=True
            ).filter(
                Q(is_visible=True) | Q(author=self.request.user)
            ).order_by('-created_at')
        
        # 分页
        paginator = Paginator(comments, 20)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context.update({
            'book': book,
            'page_obj': page_obj,
        })
        
        return context


class ChapterCommentsView(LoginRequiredMixin, TemplateView):
    """章节评论页面"""
    template_name = 'comments/chapter_comments.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        chapter_number = kwargs.get('chapter_number')
        
        book = get_object_or_404(Book, id=book_id)
        chapter = get_object_or_404(Chapter, book=book, chapter_number=chapter_number)
        
        # 检查权限：作者可以查看自己的所有评论，其他用户只能查看通过审核的公开作品的评论
        if book.author != self.request.user and not book.is_visible_to_public:
            raise Http404("作品不存在")
        
        # 获取章节评论
        # 用户可以查看自己的所有评论（包括审核中的），其他用户只能查看已通过审核的评论
        if book.author == self.request.user:
            # 作者可以查看所有评论
            comments = Comment.objects.filter(
                book=book,
                chapter=chapter
            ).order_by('-created_at')
        else:
            # 其他用户可以查看已通过审核的评论 + 自己的所有评论
            comments = Comment.objects.filter(
                book=book,
                chapter=chapter
            ).filter(
                Q(is_visible=True) | Q(author=self.request.user)
            ).order_by('-created_at')
        
        # 分页
        paginator = Paginator(comments, 20)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context.update({
            'book': book,
            'chapter': chapter,
            'page_obj': page_obj,
        })
        
        return context


class AddCommentAPIView(LoginRequiredMixin, TemplateView):
    """添加评论API"""
    
    def post(self, request, *args, **kwargs):
        return JsonResponse({'success': True, 'message': '评论添加成功'})


@login_required
def add_book_comment(request, book_id):
    """添加作品评论"""
    book = get_object_or_404(Book, id=book_id)
    
    # 校验用户是否可以发表评论
    can_comment, error_msg = validate_user_can_comment(request.user)
    if not can_comment:
        return JsonResponse({'success': False, 'error': error_msg})
    
    # 检查权限：作者可以对自己的作品评论，其他用户只能对通过审核的公开作品评论
    if book.author != request.user and not book.is_visible_to_public:
        return JsonResponse({'success': False, 'error': '无权限对此作品发表评论'})
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': '评论内容不能为空'})
        
        try:
            with transaction.atomic():
                # 使用AI进行内容审核
                ai_result = check_content_by_ai(content)
                ai_check_status = 'approved' if ai_result.get('approved', False) else 'rejected'
                
                comment = Comment.objects.create(
                    book=book,
                    author=request.user,
                    content_pending=content,  # 将内容放入待审核字段
                    ai_check=ai_check_status,
                    is_visible=False  # 默认不可见，需要审核通过
                )
                
                # 如果AI审核通过，直接发布
                if ai_check_status == 'approved':
                    comment.content = content
                    comment.is_visible = True
                    comment.save()
            
            if ai_check_status == 'approved':
                return JsonResponse({
                    'success': True,
                    'message': '评论发表成功',
                    'comment_id': comment.id
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': '评论已提交，正在审核中',
                    'comment_id': comment.id
                })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '无效的请求方法'})


@login_required
def add_chapter_comment(request, book_id, chapter_number):
    """添加章节评论"""
    book = get_object_or_404(Book, id=book_id)
    chapter = get_object_or_404(Chapter, book=book, chapter_number=chapter_number)
    
    # 校验用户是否可以发表评论
    can_comment, error_msg = validate_user_can_comment(request.user)
    if not can_comment:
        return JsonResponse({'success': False, 'error': error_msg})
    
    # 检查权限：作者可以对自己的作品评论，其他用户只能对通过审核的公开作品评论
    if book.author != request.user and not book.is_visible_to_public:
        return JsonResponse({'success': False, 'error': '无权限对此章节发表评论'})
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': '评论内容不能为空'})
        
        try:
            with transaction.atomic():
                # 使用AI进行内容审核
                ai_result = check_content_by_ai(content)
                ai_check_status = 'approved' if ai_result.get('approved', False) else 'rejected'
                
                comment = Comment.objects.create(
                    book=book,
                    chapter=chapter,
                    author=request.user,
                    content_pending=content,  # 将内容放入待审核字段
                    ai_check=ai_check_status,
                    is_visible=False  # 默认不可见，需要审核通过
                )
                
                # 如果AI审核通过，直接发布
                if ai_check_status == 'approved':
                    comment.content = content
                    comment.is_visible = True
                    comment.save()
            
            if ai_check_status == 'approved':
                return JsonResponse({
                    'success': True,
                    'message': '评论发表成功',
                    'comment_id': comment.id
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': '评论已提交，正在审核中',
                    'comment_id': comment.id
                })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '无效的请求方法'})


@login_required
def delete_comment(request, comment_id):
    """删除评论"""
    comment = get_object_or_404(Comment, id=comment_id)
    
    # 只能删除自己的评论
    if comment.author != request.user:
        return JsonResponse({'success': False, 'error': '无权限删除此评论'})
    
    if request.method == 'POST':
        try:
            comment.delete()
            
            return JsonResponse({
                'success': True,
                'message': '评论删除成功'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '无效的请求方法'})


def validate_user_can_comment(user):
    """
    校验用户是否可以发表评论
    必须设置显示昵称才能评论
    """
    if not user.is_authenticated:
        return False, "请先登录"
    
    if not user.display_name or not user.display_name.strip():
        return False, "请先设置显示昵称才能发表评论"
    
    return True, ""
