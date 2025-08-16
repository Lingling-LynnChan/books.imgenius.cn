from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, TemplateView
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.utils import timezone
import json

from .models import Book, BookDraft, Chapter, ChapterDraft
from .ai_utils import check_content_by_ai


class IndexView(LoginRequiredMixin, TemplateView):
    """首页 - 重定向到阅读页面"""
    login_url = '/accounts/login/'
    
    def get(self, request, *args, **kwargs):
        return redirect('books:read')


class ReadView(LoginRequiredMixin, TemplateView):
    """阅读页面 - 显示用户的作品列表"""
    template_name = 'books/read.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取用户的作品
        books = Book.objects.filter(author=self.request.user).order_by('-updated_at')
        
        # 搜索功能
        search_query = self.request.GET.get('search', '')
        if search_query:
            books = books.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        # 分页
        paginator = Paginator(books, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context.update({
            'page_obj': page_obj,
            'search_query': search_query,
        })
        
        return context


class CreateView(LoginRequiredMixin, TemplateView):
    """创建作品页面"""
    template_name = 'books/create.html'
    login_url = '/accounts/login/'


@login_required
def create_book(request):
    """创建新作品"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not title:
            return JsonResponse({'success': False, 'error': '作品标题不能为空'})
        
        try:
            with transaction.atomic():
                book = Book.objects.create(
                    author=request.user,
                    title=title,
                    description=description
                )
                
                # 创建草稿
                BookDraft.objects.create(
                    book=book,
                    title=title,
                    description=description
                )
            
            return JsonResponse({
                'success': True,
                'message': '作品创建成功',
                'book_id': book.id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '无效的请求方法'})


class BookDetailView(LoginRequiredMixin, TemplateView):
    """作品详情页面"""
    template_name = 'books/book_detail.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        
        book = get_object_or_404(Book, id=book_id)
        
        # 检查权限
        if book.author != self.request.user:
            raise Http404("作品不存在")
        
        # 获取章节列表
        chapters = Chapter.objects.filter(book=book).order_by('chapter_number')
        
        context.update({
            'book': book,
            'chapters': chapters,
        })
        
        return context


class ChapterListView(LoginRequiredMixin, TemplateView):
    """章节列表页面"""
    template_name = 'books/chapter_list.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        
        book = get_object_or_404(Book, id=book_id)
        
        # 检查权限
        if book.author != self.request.user:
            raise Http404("作品不存在")
        
        chapters = Chapter.objects.filter(book=book).order_by('chapter_number')
        
        context.update({
            'book': book,
            'chapters': chapters,
        })
        
        return context


@login_required
def create_chapter(request, book_id):
    """创建新章节"""
    book = get_object_or_404(Book, id=book_id)
    
    # 检查权限
    if book.author != request.user:
        raise Http404("作品不存在")
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        
        if not title:
            return JsonResponse({'success': False, 'error': '章节标题不能为空'})
        
        if not content:
            return JsonResponse({'success': False, 'error': '章节内容不能为空'})
        
        try:
            with transaction.atomic():
                # 获取下一个章节号
                last_chapter = Chapter.objects.filter(book=book).order_by('-chapter_number').first()
                chapter_number = (last_chapter.chapter_number + 1) if last_chapter else 1
                
                chapter = Chapter.objects.create(
                    book=book,
                    author=request.user,
                    chapter_number=chapter_number,
                    title=title,
                    content=content
                )
                
                # 创建草稿
                ChapterDraft.objects.create(
                    book=book,
                    author=request.user,
                    chapter_number=chapter_number,
                    title=title,
                    content=content
                )
                
                # 更新作品的最后更新时间
                book.last_chapter_update = timezone.now()
                book.save()
            
            return JsonResponse({
                'success': True,
                'message': '章节创建成功',
                'chapter_number': chapter_number
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '无效的请求方法'})


@login_required
def edit_chapter(request, book_id, chapter_number):
    """编辑章节"""
    book = get_object_or_404(Book, id=book_id)
    chapter = get_object_or_404(Chapter, book=book, chapter_number=chapter_number)
    
    # 检查权限
    if book.author != request.user:
        raise Http404("作品不存在")
    
    if request.method == 'GET':
        return render(request, 'books/edit_chapter.html', {
            'book': book,
            'chapter': chapter,
        })
    
    elif request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        
        if not title:
            return JsonResponse({'success': False, 'error': '章节标题不能为空'})
        
        if not content:
            return JsonResponse({'success': False, 'error': '章节内容不能为空'})
        
        try:
            with transaction.atomic():
                chapter.title = title
                chapter.content = content
                chapter.save()
                
                # 更新或创建草稿
                draft, created = ChapterDraft.objects.get_or_create(
                    book=book,
                    chapter_number=chapter_number,
                    defaults={
                        'author': request.user,
                        'title': title,
                        'content': content
                    }
                )
                if not created:
                    draft.title = title
                    draft.content = content
                    draft.save()
                
                # 更新作品的最后更新时间
                book.last_chapter_update = timezone.now()
                book.save()
            
            return JsonResponse({
                'success': True,
                'message': '章节更新成功'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '无效的请求方法'})


@login_required
def delete_chapter(request, book_id, chapter_number):
    """删除章节"""
    book = get_object_or_404(Book, id=book_id)
    chapter = get_object_or_404(Chapter, book=book, chapter_number=chapter_number)
    
    # 检查权限
    if book.author != request.user:
        raise Http404("作品不存在")
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 删除章节和相关草稿
                ChapterDraft.objects.filter(book=book, chapter_number=chapter_number).delete()
                chapter.delete()
                
                # 重新排序后续章节
                later_chapters = Chapter.objects.filter(
                    book=book, 
                    chapter_number__gt=chapter_number
                ).order_by('chapter_number')
                
                for i, later_chapter in enumerate(later_chapters, start=chapter_number):
                    later_chapter.chapter_number = i
                    later_chapter.save()
                
                # 更新作品的最后更新时间
                book.last_chapter_update = timezone.now()
                book.save()
            
            return JsonResponse({
                'success': True,
                'message': '章节删除成功'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '无效的请求方法'})


# 其他视图功能的简化版本...
