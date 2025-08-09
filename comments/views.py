from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from books.models import Book
from .mongodb_utils import (
    get_book_comments, get_chapter_comments, add_comment,
    get_comment, update_comment_review_status
)
from books.ai_utils import check_content_by_ai


class BookCommentsView(LoginRequiredMixin, TemplateView):
    """作品评论页面"""
    template_name = 'comments/book_comments.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        book = get_object_or_404(Book, id=book_id)
        
        # 检查作品是否公开可见
        if not book.is_visible_to_public and book.author != self.request.user:
            messages.error(self.request, '该作品还未审核通过')
            return context
        
        comments = get_book_comments(book_id)
        # 过滤未审核通过的评论（除非是管理员）
        if not self.request.user.is_admin:
            comments = [c for c in comments if c.get('is_visible', False)]
        
        context.update({
            'book': book,
            'comments': comments,
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
        comments = get_chapter_comments(book_id, chapter_number)
        
        # 过滤未审核通过的评论（除非是管理员）
        if not self.request.user.is_admin:
            comments = [c for c in comments if c.get('is_visible', False)]
        
        context.update({
            'book': book,
            'chapter_number': chapter_number,
            'comments': comments,
        })
        return context


class AddCommentView(LoginRequiredMixin, TemplateView):
    """添加评论页面"""
    template_name = 'comments/add_comment.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = self.request.GET.get('book_id')
        chapter_number = self.request.GET.get('chapter_number')
        
        if book_id:
            book = get_object_or_404(Book, id=book_id)
            context['book'] = book
            
        if chapter_number:
            context['chapter_number'] = int(chapter_number)
        
        return context
    
    def post(self, request, *args, **kwargs):
        if not request.user.can_create_content:
            messages.error(request, '请先设置显示名称才能评论')
            return render(request, self.template_name)
        
        book_id = request.POST.get('book_id')
        chapter_number = request.POST.get('chapter_number')
        content = request.POST.get('content', '').strip()
        
        if not book_id or not content:
            messages.error(request, '请填写评论内容')
            return render(request, self.template_name)
        
        book = get_object_or_404(Book, id=book_id)
        
        # 创建评论
        comment_data = {
            'book_id': int(book_id),
            'chapter_number': int(chapter_number) if chapter_number else None,
            'author_id': request.user.id,
            'content': content,
            'content_pending': content,
            'ai_check': 'pending',
            'adm_check': None,
            'reject_reason': '',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'is_visible': False,
        }
        
        comment_id = add_comment(comment_data)
        
        # AI审核
        try:
            ai_result = check_content_by_ai(content)
            
            update_data = {
                'ai_check': 'approved' if ai_result['approved'] else 'rejected',
                'is_visible': ai_result['approved'],
                'updated_at': datetime.now(),
            }
            
            if not ai_result['approved']:
                update_data['reject_reason'] = ai_result.get('reason', 'AI审核未通过')
            else:
                # AI审核通过，更新正式内容
                update_data['content'] = content
                update_data['content_pending'] = None
            
            update_comment_review_status(comment_id, update_data)
        except Exception as e:
            pass
        
        messages.success(request, '评论提交成功，正在审核中')
        
        # 重定向到相应页面
        if chapter_number:
            return redirect('books:chapter_detail', book_id=book_id, chapter_number=chapter_number)
        else:
            return redirect('books:book_detail', book_id=book_id)


class AddCommentAPIView(LoginRequiredMixin, View):
    """添加评论API"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        if not request.user.can_create_content:
            return JsonResponse({'success': False, 'message': '请先设置显示名称才能评论'})
        
        book_id = request.POST.get('book_id')
        chapter_number = request.POST.get('chapter_number')
        content = request.POST.get('content', '').strip()
        
        if not book_id or not content:
            return JsonResponse({'success': False, 'message': '请填写评论内容'})
        
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return JsonResponse({'success': False, 'message': '作品不存在'})
        
        # 创建评论
        comment_data = {
            'book_id': int(book_id),
            'chapter_number': int(chapter_number) if chapter_number else None,
            'author_id': request.user.id,
            'content': content,
            'content_pending': content,
            'ai_check': 'pending',
            'adm_check': None,
            'reject_reason': '',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'is_visible': False,
        }
        
        comment_id = add_comment(comment_data)
        
        # AI审核
        try:
            ai_result = check_content_by_ai(content)
            
            update_data = {
                'ai_check': 'approved' if ai_result['approved'] else 'rejected',
                'is_visible': ai_result['approved'],
                'updated_at': datetime.now(),
            }
            
            if not ai_result['approved']:
                update_data['reject_reason'] = ai_result.get('reason', 'AI审核未通过')
            else:
                update_data['content'] = content
                update_data['content_pending'] = None
            
            update_comment_review_status(comment_id, update_data)
            
            return JsonResponse({
                'success': True, 
                'message': '评论提交成功' if ai_result['approved'] else '评论已提交，正在审核中',
                'approved': ai_result['approved']
            })
        except Exception as e:
            return JsonResponse({'success': True, 'message': '评论已提交，正在审核中', 'approved': False})
