import json
import requests
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView, ListView
from django.views import View
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.urls import reverse

from .models import Book, BookDraft
from .mongodb_utils import (
    get_book_chapters, get_chapter, create_chapter, update_chapter,
    delete_chapter, save_chapter_draft, get_chapter_draft,
    get_pending_reviews, get_mongodb_collection
)
from .ai_utils import check_content_by_ai


class IndexView(LoginRequiredMixin, TemplateView):
    """首页 - 重定向到阅读页面"""
    login_url = '/accounts/login/'
    
    def get(self, request, *args, **kwargs):
        return redirect('books:read')


class ReadView(LoginRequiredMixin, ListView):
    """阅读板块"""
    model = Book
    template_name = 'books/read.html'
    context_object_name = 'books'
    paginate_by = settings.PAGINATION_PAGE_SIZE
    login_url = '/accounts/login/'
    
    def get_queryset(self):
        # 根据修复后的审核逻辑构建查询
        # 标题通过：管理员已审核则看管理员结果，否则看AI结果
        # 简介通过：管理员已审核则看管理员结果，否则看AI结果
        
        # 标题审核通过的条件
        title_approved = (
            # 管理员已审核且通过
            Q(adm_check_title='approved') |
            # 管理员未审核但AI通过
            (Q(adm_check_title__isnull=True) & Q(ai_check_title='approved'))
        )
        
        # 简介审核通过的条件  
        description_approved = (
            # 管理员已审核且通过
            Q(adm_check_description='approved') |
            # 管理员未审核但AI通过
            (Q(adm_check_description__isnull=True) & Q(ai_check_description='approved'))
        )
        
        queryset = Book.objects.filter(title_approved & description_approved)
        
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(author__display_name__icontains=search_query)
            )
        
        return queryset.order_by('-last_chapter_update', '-updated_at')


class BookDetailView(LoginRequiredMixin, TemplateView):
    """作品详情页面"""
    template_name = 'books/book_detail.html'
    login_url = '/accounts/login/'
    
    def get(self, request, *args, **kwargs):
        book_id = kwargs.get('book_id')
        book = get_object_or_404(Book, id=book_id)
        
        # 检查访问权限
        if not book.is_visible_to_public and book.author != request.user:
            messages.error(request, '该作品还未审核通过')
            return redirect('books:read')
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        book = get_object_or_404(Book, id=book_id)
        
        chapters = get_book_chapters(book_id)
        # 过滤未审核通过的章节（除非是作者本人）
        if book.author != self.request.user:
            chapters = [ch for ch in chapters if self._is_chapter_approved(ch)]
        
        # 计算最后一章的章节号
        last_chapter_number = None
        if chapters:
            last_chapter_number = chapters[-1].get('chapter_number')
        
        context.update({
            'book': book,
            'chapters': chapters,
            'last_chapter_number': last_chapter_number,
        })
        return context
    
    def _is_chapter_approved(self, chapter):
        """检查章节是否审核通过"""
        # 检查标题审核状态
        if chapter.get('adm_check_title') is not None:
            title_approved = chapter.get('adm_check_title') == 'approved'
        else:
            title_approved = chapter.get('ai_check_title') == 'approved'
        
        # 检查内容审核状态
        if chapter.get('adm_check_content') is not None:
            content_approved = chapter.get('adm_check_content') == 'approved'
        else:
            content_approved = chapter.get('ai_check_content') == 'approved'
        
        return title_approved and content_approved


class ChapterDetailView(LoginRequiredMixin, TemplateView):
    """章节详情页面"""
    template_name = 'books/chapter_detail.html'
    login_url = '/accounts/login/'
    
    def get(self, request, *args, **kwargs):
        book_id = kwargs.get('book_id')
        chapter_number = kwargs.get('chapter_number')
        
        book = get_object_or_404(Book, id=book_id)
        chapter = get_chapter(book_id, chapter_number)
        
        if not chapter:
            messages.error(request, '章节不存在')
            return redirect('books:book_detail', book_id=book_id)
        
        # 检查访问权限
        is_author = book.author == request.user
        if not is_author and not self._is_chapter_approved(chapter):
            messages.error(request, '该章节还未审核通过')
            return redirect('books:book_detail', book_id=book_id)
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        chapter_number = kwargs.get('chapter_number')
        
        book = get_object_or_404(Book, id=book_id)
        chapter = get_chapter(book_id, chapter_number)
        is_author = book.author == self.request.user
        
        # 获取章节列表用于导航
        chapters = get_book_chapters(book_id)
        if not is_author:
            chapters = [ch for ch in chapters if self._is_chapter_approved(ch)]
        
        # 找到当前章节在列表中的位置
        current_index = None
        for i, ch in enumerate(chapters):
            if ch.get('chapter_number') == chapter_number:
                current_index = i
                break
        
        prev_chapter = None
        next_chapter = None
        if current_index is not None:
            if current_index > 0:
                prev_chapter = chapters[current_index - 1]
            if current_index < len(chapters) - 1:
                next_chapter = chapters[current_index + 1]
        
        context.update({
            'book': book,
            'chapter': chapter,
            'is_author': is_author,
            'chapters': chapters,
            'prev_chapter': prev_chapter,
            'next_chapter': next_chapter,
        })
        return context
    
    def _is_chapter_approved(self, chapter):
        """检查章节是否审核通过"""
        # 检查标题审核状态
        if chapter.get('adm_check_title') is not None:
            title_approved = chapter.get('adm_check_title') == 'approved'
        else:
            title_approved = chapter.get('ai_check_title') == 'approved'
        
        # 检查内容审核状态
        if chapter.get('adm_check_content') is not None:
            content_approved = chapter.get('adm_check_content') == 'approved'
        else:
            content_approved = chapter.get('ai_check_content') == 'approved'
        
        return title_approved and content_approved


class CreateView(LoginRequiredMixin, ListView):
    """创作板块"""
    model = Book
    template_name = 'books/create.html'
    context_object_name = 'books'
    paginate_by = settings.PAGINATION_PAGE_SIZE
    login_url = '/accounts/login/'
    
    def get_queryset(self):
        return Book.objects.filter(author=self.request.user).order_by('-updated_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_create'] = self.request.user.can_create_content
        return context


class CreateBookView(LoginRequiredMixin, TemplateView):
    """创建新作品"""
    template_name = 'books/create_book.html'
    login_url = '/accounts/login/'
    
    def get(self, request, *args, **kwargs):
        if not request.user.can_create_content:
            messages.error(request, '请先设置显示名称才能创作')
            return redirect('accounts:profile')
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        if not request.user.can_create_content:
            messages.error(request, '请先设置显示名称才能创作')
            return redirect('accounts:profile')
        
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not title:
            messages.error(request, '请填写作品名')
            return render(request, self.template_name)
        
        # 创建作品
        book = Book.objects.create(
            author=request.user,
            title=title,
            description=description,
            title_pending=title,
            description_pending=description,
        )
        
        # AI审核
        try:
            ai_result_title = check_content_by_ai(title)
            ai_result_desc = check_content_by_ai(description)
            
            book.ai_check_title = 'approved' if ai_result_title['approved'] else 'rejected'
            book.ai_check_description = 'approved' if ai_result_desc['approved'] else 'rejected'
            
            if not ai_result_title['approved']:
                book.title_reject_reason = ai_result_title.get('reason', 'AI审核未通过')
            if not ai_result_desc['approved']:
                book.description_reject_reason = ai_result_desc.get('reason', 'AI审核未通过')
            
            book.save()
        except Exception as e:
            # AI审核失败，保持待审核状态
            pass
        
        messages.success(request, '作品创建成功')
        return redirect('books:edit_book', book_id=book.id)


class EditBookView(LoginRequiredMixin, TemplateView):
    """编辑作品信息"""
    template_name = 'books/edit_book.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        book = get_object_or_404(Book, id=book_id, author=self.request.user)
        context['book'] = book
        return context
    
    def post(self, request, *args, **kwargs):
        book_id = kwargs.get('book_id')
        book = get_object_or_404(Book, id=book_id, author=request.user)
        
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not title:
            messages.error(request, '请填写作品名')
            return render(request, self.template_name, {'book': book})
        
        # 检查内容是否真的发生了变化
        current_title = book.title_pending if book.title_pending else book.title
        current_description = book.description_pending if book.description_pending else book.description
        
        title_changed = title != current_title
        description_changed = description != current_description
        
        # 只有内容发生变化时才重新提交审核
        if title_changed or description_changed:
            # 更新待审核内容
            if title_changed:
                book.title_pending = title
                book.ai_check_title = 'pending'
                book.adm_check_title = None
                book.title_reject_reason = ''
            
            if description_changed:
                book.description_pending = description
                book.ai_check_description = 'pending'
                book.adm_check_description = None
                book.description_reject_reason = ''
            
            book.save()
            
            # AI审核
            try:
                if title_changed:
                    ai_result_title = check_content_by_ai(title)
                    book.ai_check_title = 'approved' if ai_result_title['approved'] else 'rejected'
                    if not ai_result_title['approved']:
                        book.title_reject_reason = ai_result_title.get('reason', 'AI审核未通过')
                
                if description_changed:
                    ai_result_desc = check_content_by_ai(description)
                    book.ai_check_description = 'approved' if ai_result_desc['approved'] else 'rejected'
                    if not ai_result_desc['approved']:
                        book.description_reject_reason = ai_result_desc.get('reason', 'AI审核未通过')
                
                book.save()
            except Exception as e:
                pass
            
            messages.success(request, '作品信息更新成功，已提交审核')
        else:
            messages.info(request, '作品信息没有变化')
        
        return render(request, self.template_name, {'book': book})


class ChapterListView(LoginRequiredMixin, TemplateView):
    """章节列表"""
    template_name = 'books/chapter_list.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        book = get_object_or_404(Book, id=book_id, author=self.request.user)
        chapters = get_book_chapters(book_id)
        
        # 计算最后一章的章节号
        last_chapter_number = None
        if chapters:
            last_chapter_number = chapters[-1].get('chapter_number')
        
        context.update({
            'book': book,
            'chapters': chapters,
            'last_chapter_number': last_chapter_number,
        })
        return context


class CreateChapterView(LoginRequiredMixin, TemplateView):
    """创建新章节"""
    template_name = 'books/create_chapter.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        book = get_object_or_404(Book, id=book_id, author=self.request.user)
        context['book'] = book
        return context
    
    def post(self, request, *args, **kwargs):
        book_id = kwargs.get('book_id')
        book = get_object_or_404(Book, id=book_id, author=request.user)
        
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        
        if not title:
            messages.error(request, '请填写章节名')
            return render(request, self.template_name, {'book': book})
        
        # 获取下一个章节号
        chapters = get_book_chapters(book_id)
        next_chapter_number = len(chapters) + 1
        
        # 创建章节
        chapter_data = {
            'book_id': book_id,
            'chapter_number': next_chapter_number,
            'title': title,
            'content': content,
            'title_pending': title,
            'content_pending': content,
            'ai_check_title': 'pending',
            'ai_check_content': 'pending',
            'adm_check_title': None,
            'adm_check_content': None,
            'title_reject_reason': '',
            'content_reject_reason': '',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'author_id': request.user.id,
        }
        
        create_chapter(chapter_data)
        
        # AI审核
        try:
            ai_result_title = check_content_by_ai(title)
            ai_result_content = check_content_by_ai(content)
            
            update_data = {
                'ai_check_title': 'approved' if ai_result_title['approved'] else 'rejected',
                'ai_check_content': 'approved' if ai_result_content['approved'] else 'rejected',
            }
            
            if not ai_result_title['approved']:
                update_data['title_reject_reason'] = ai_result_title.get('reason', 'AI审核未通过')
            if not ai_result_content['approved']:
                update_data['content_reject_reason'] = ai_result_content.get('reason', 'AI审核未通过')
            
            update_chapter(book_id, next_chapter_number, update_data)
        except Exception as e:
            pass
        
        # 更新作品的最后章节更新时间
        book.last_chapter_update = timezone.now()
        book.save()
        
        messages.success(request, '章节创建成功')
        return redirect('books:edit_chapter', book_id=book_id, chapter_number=next_chapter_number)


class EditChapterView(LoginRequiredMixin, TemplateView):
    """编辑章节"""
    template_name = 'books/edit_chapter.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        chapter_number = kwargs.get('chapter_number')
        
        book = get_object_or_404(Book, id=book_id, author=self.request.user)
        chapter = get_chapter(book_id, chapter_number)
        
        if not chapter:
            messages.error(self.request, '章节不存在')
            return redirect('books:chapter_list', book_id=book_id)
        
        # 获取草稿内容
        draft = get_chapter_draft(book_id, chapter_number)
        
        context.update({
            'book': book,
            'chapter': chapter,
            'draft': draft,
        })
        return context
    
    def post(self, request, *args, **kwargs):
        book_id = kwargs.get('book_id')
        chapter_number = kwargs.get('chapter_number')
        
        book = get_object_or_404(Book, id=book_id, author=request.user)
        chapter = get_chapter(book_id, chapter_number)
        
        if not chapter:
            messages.error(request, '章节不存在')
            return redirect('books:chapter_list', book_id=book_id)
        
        action = request.POST.get('action')
        
        if action == 'save_draft':
            # 保存草稿
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '').strip()
            
            save_chapter_draft(book_id, chapter_number, title, content, request.user.id)
            return JsonResponse({'success': True, 'message': '草稿保存成功'})
        
        elif action == 'publish':
            # 发布章节
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '').strip()
            
            if not title:
                messages.error(request, '请填写章节标题')
                # 获取草稿内容
                draft = get_chapter_draft(book_id, chapter_number)
                return render(request, self.template_name, {
                    'book': book,
                    'chapter': chapter,
                    'draft': draft,
                })
            
            if not content:
                messages.error(request, '请填写章节内容')
                # 获取草稿内容
                draft = get_chapter_draft(book_id, chapter_number)
                return render(request, self.template_name, {
                    'book': book,
                    'chapter': chapter,
                    'draft': draft,
                })
            
            # 更新章节
            update_data = {
                'title_pending': title,
                'content_pending': content,
                'ai_check_title': 'pending',
                'ai_check_content': 'pending',
                'adm_check_title': None,
                'adm_check_content': None,
                'title_reject_reason': '',
                'content_reject_reason': '',
                'updated_at': datetime.now(),
            }
            
            update_chapter(book_id, chapter_number, update_data)
            
            # AI审核
            try:
                ai_result_title = check_content_by_ai(title)
                ai_result_content = check_content_by_ai(content)
                
                ai_update_data = {
                    'ai_check_title': 'approved' if ai_result_title['approved'] else 'rejected',
                    'ai_check_content': 'approved' if ai_result_content['approved'] else 'rejected',
                }
                
                if not ai_result_title['approved']:
                    ai_update_data['title_reject_reason'] = ai_result_title.get('reason', 'AI审核未通过')
                if not ai_result_content['approved']:
                    ai_update_data['content_reject_reason'] = ai_result_content.get('reason', 'AI审核未通过')
                
                update_chapter(book_id, chapter_number, ai_update_data)
            except Exception as e:
                pass
            
            # 更新作品的最后章节更新时间
            book.last_chapter_update = timezone.now()
            book.save()
            
            messages.success(request, '章节发布成功')
            return redirect('books:edit_chapter', book_id=book_id, chapter_number=chapter_number)
        
        # 如果没有匹配的action，返回错误
        messages.error(request, '无效的操作')
        return redirect('books:edit_chapter', book_id=book_id, chapter_number=chapter_number)


# API视图
class SearchAPIView(View):
    """搜索API"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        search_query = request.GET.get('q', '').strip()
        page = int(request.GET.get('page', 1))
        
        if not search_query:
            return JsonResponse({'books': [], 'has_next': False})
        
        books = Book.objects.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(author__display_name__icontains=search_query),
            ai_check_title='approved',
            ai_check_description='approved'
        ).exclude(adm_check_title='rejected').exclude(adm_check_description='rejected')
        
        paginator = Paginator(books, settings.PAGINATION_PAGE_SIZE)
        page_obj = paginator.get_page(page)
        
        book_list = []
        for book in page_obj:
            book_list.append({
                'id': book.id,
                'title': book.title,
                'description': book.description,
                'author': book.author.display_name,
                'updated_at': book.updated_at.strftime('%Y-%m-%d %H:%M'),
            })
        
        return JsonResponse({
            'books': book_list,
            'has_next': page_obj.has_next(),
        })


class AutoSaveBookAPIView(LoginRequiredMixin, View):
    """作品自动保存API"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        book_id = request.POST.get('book_id')
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not book_id:
            return JsonResponse({'success': False, 'message': '缺少作品ID'})
        
        try:
            book = Book.objects.get(id=book_id, author=request.user)
            draft, created = BookDraft.objects.get_or_create(book=book)
            draft.title = title
            draft.description = description
            draft.save()
            
            return JsonResponse({'success': True, 'message': '自动保存成功'})
        except Book.DoesNotExist:
            return JsonResponse({'success': False, 'message': '作品不存在'})


class AutoSaveChapterAPIView(LoginRequiredMixin, View):
    """章节自动保存API"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        book_id = request.POST.get('book_id')
        chapter_number = request.POST.get('chapter_number')
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        
        if not book_id or not chapter_number:
            return JsonResponse({'success': False, 'message': '缺少参数'})
        
        try:
            book = Book.objects.get(id=book_id, author=request.user)
            save_chapter_draft(int(book_id), int(chapter_number), title, content, request.user.id)
            
            return JsonResponse({'success': True, 'message': '自动保存成功'})
        except Book.DoesNotExist:
            return JsonResponse({'success': False, 'message': '作品不存在'})


class PublishBookAPIView(LoginRequiredMixin, View):
    """发布作品API"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        # 实现发布作品逻辑
        return JsonResponse({'success': True, 'message': '发布成功'})


class PublishChapterAPIView(LoginRequiredMixin, View):
    """发布章节API"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        # 实现发布章节逻辑
        return JsonResponse({'success': True, 'message': '发布成功'})


# 管理员视图
class AdminPanelView(LoginRequiredMixin, TemplateView):
    """管理员后台"""
    template_name = 'books/admin_panel.html'
    login_url = '/accounts/login/'
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, '您没有管理员权限')
            return redirect('books:read')
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取待审核内容
        pending_reviews = get_pending_reviews()
        
        # 计算系统统计信息
        from accounts.models import User
        total_users = User.objects.count()
        total_books = Book.objects.count()
        
        # 计算总章节数（从MongoDB）
        chapters_collection = get_mongodb_collection('chapters')
        total_chapters = 0
        if chapters_collection is not None:
            total_chapters = chapters_collection.count_documents({})
        
        # 计算总评论数（从MongoDB）
        from comments.mongodb_utils import get_mongodb_collection as get_comments_collection
        comments_collection = get_comments_collection('comments')
        total_comments = 0
        if comments_collection is not None:
            total_comments = comments_collection.count_documents({})
        
        context.update({
            'pending_books': pending_reviews.get('books', []),
            'pending_chapters': pending_reviews.get('chapters', []),
            'total_users': total_users,
            'total_books': total_books,
            'total_chapters': total_chapters,
            'total_comments': total_comments,
        })
        return context


class AdminReviewView(LoginRequiredMixin, TemplateView):
    """管理员审核页面"""
    template_name = 'books/admin_review.html'
    login_url = '/accounts/login/'
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, '您没有管理员权限')
            return redirect('books:read')
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_id = kwargs.get('content_id')
        
        book = get_object_or_404(Book, id=content_id)
        context['book'] = book
        
        return context
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_admin:
            return JsonResponse({'success': False, 'message': '无权限'})
        
        content_id = kwargs.get('content_id')
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()
        
        book = get_object_or_404(Book, id=content_id)
        field_type = request.POST.get('field_type')  # title 或 description
        
        if action == 'approve':
            if field_type == 'title':
                book.adm_check_title = 'approved'
                if book.title_pending:
                    book.title = book.title_pending
                    book.title_pending = None  # 清空待审核内容
                    # 审核通过后清空拒绝原因
                    book.title_reject_reason = ''
            elif field_type == 'description':
                book.adm_check_description = 'approved'
                if book.description_pending:
                    book.description = book.description_pending
                    book.description_pending = None  # 清空待审核内容
                    # 审核通过后清空拒绝原因
                    book.description_reject_reason = ''
        elif action == 'reject':
            if field_type == 'title':
                book.adm_check_title = 'rejected'
                book.title_reject_reason = reason
            elif field_type == 'description':
                book.adm_check_description = 'rejected'
                book.description_reject_reason = reason
        
        book.save()
        messages.success(request, '操作成功')
        
        # 检查是否是AJAX请求
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': '操作成功'})
        else:
            # 普通表单提交，重定向回当前页面
            return redirect('books:admin_review', content_id=content_id)


class AdminChapterReviewView(LoginRequiredMixin, TemplateView):
    """管理员章节审核页面"""
    template_name = 'books/admin_chapter_review.html'
    login_url = '/accounts/login/'
    
    def get(self, request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, '您没有管理员权限')
            return redirect('books:read')
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        chapter_number = self.request.GET.get('chapter')
        
        book = get_object_or_404(Book, id=book_id)
        chapter = None
        
        if chapter_number:
            chapter = get_chapter(book_id, int(chapter_number))
        
        context.update({
            'book': book,
            'chapter': chapter,
        })
        return context
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_admin:
            return JsonResponse({'success': False, 'message': '无权限'})
        
        book_id = kwargs.get('book_id')
        chapter_number = int(request.GET.get('chapter', 0))
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()
        field_type = request.POST.get('field_type')  # title 或 content
        
        if not chapter_number:
            return JsonResponse({'success': False, 'message': '缺少章节号'})
        
        chapter = get_chapter(book_id, chapter_number)
        if not chapter:
            return JsonResponse({'success': False, 'message': '章节不存在'})
        
        update_data = {}
        
        if action == 'approve':
            if field_type == 'title':
                update_data.update({
                    'adm_check_title': 'approved',
                    'title': chapter.get('title_pending', chapter.get('title')),
                    'title_pending': None,  # 清空待审核内容
                    # 审核通过后清空拒绝原因
                    'title_reject_reason': ''
                })
            elif field_type == 'content':
                update_data.update({
                    'adm_check_content': 'approved',
                    'content': chapter.get('content_pending', chapter.get('content')),
                    'content_pending': None,  # 清空待审核内容
                    # 审核通过后清空拒绝原因
                    'content_reject_reason': ''
                })
        elif action == 'reject':
            if field_type == 'title':
                update_data.update({
                    'adm_check_title': 'rejected',
                    'title_reject_reason': reason
                })
            elif field_type == 'content':
                update_data.update({
                    'adm_check_content': 'rejected',
                    'content_reject_reason': reason
                })
        
        if update_data:
            update_chapter(book_id, chapter_number, update_data)
            messages.success(request, '操作成功')
        
        # 检查是否是AJAX请求
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': '操作成功'})
        else:
            # 普通表单提交，重定向回当前页面
            chapter_param = f"?chapter={chapter_number}"
            return redirect(f"{reverse('books:admin_chapter_review', args=[book_id])}{chapter_param}")
