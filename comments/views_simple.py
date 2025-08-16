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
import json

from books.models import Book, Chapter
from .models import Comment
from books.ai_utils import check_content_by_ai


class BookCommentsView(LoginRequiredMixin, TemplateView):
    """作品评论页面"""
    template_name = 'comments/book_comments.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        
        book = get_object_or_404(Book, id=book_id)
        
        # 获取作品评论（不包含章节评论）
        comments = Comment.objects.filter(
            book=book, 
            chapter__isnull=True,
            is_visible=True
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
        
        # 获取章节评论
        comments = Comment.objects.filter(
            book=book,
            chapter=chapter,
            is_visible=True
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


@login_required
def add_book_comment(request, book_id):
    """添加作品评论"""
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': '评论内容不能为空'})
        
        try:
            with transaction.atomic():
                comment = Comment.objects.create(
                    book=book,
                    author=request.user,
                    content=content,
                    ai_check='approved',  # 简化版本直接通过
                    is_visible=True
                )
            
            return JsonResponse({
                'success': True,
                'message': '评论添加成功',
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
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': '评论内容不能为空'})
        
        try:
            with transaction.atomic():
                comment = Comment.objects.create(
                    book=book,
                    chapter=chapter,
                    author=request.user,
                    content=content,
                    ai_check='approved',  # 简化版本直接通过
                    is_visible=True
                )
            
            return JsonResponse({
                'success': True,
                'message': '评论添加成功',
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
