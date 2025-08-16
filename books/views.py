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
from accounts.models import User
from comments.models import Comment


class IndexView(LoginRequiredMixin, TemplateView):
    """首页 - 重定向到阅读页面"""
    login_url = '/accounts/login/'
    
    def get(self, request, *args, **kwargs):
        return redirect('books:read')


class ReadView(LoginRequiredMixin, TemplateView):
    """阅读页面 - 显示所有通过审核的公开作品"""
    template_name = 'books/read.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取所有通过审核的公开作品
        # 使用模型中定义的is_visible_to_public属性进行过滤
        all_books = Book.objects.all().order_by('-updated_at')
        books = [book for book in all_books if book.is_visible_to_public]
        
        # 搜索功能
        search_query = self.request.GET.get('search', '')
        if search_query:
            books = [book for book in books if 
                    search_query.lower() in book.title.lower() or 
                    search_query.lower() in (book.description or '').lower()]
        
        # 手动分页（因为我们使用了Python过滤）
        paginator = Paginator(books, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context.update({
            'page_obj': page_obj,
            'books': page_obj.object_list,  # 添加books变量供模板使用
            'search_query': search_query,
            'is_paginated': page_obj.has_other_pages(),  # 添加分页标志
            'paginator': page_obj.paginator,  # 添加分页器
        })
        
        return context


class CreateView(LoginRequiredMixin, TemplateView):
    """创建作品页面"""
    template_name = 'books/create.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 检查用户是否设置了显示名称
        can_create = bool(self.request.user.display_name and self.request.user.display_name.strip())
        
        # 获取用户的作品
        books = Book.objects.filter(author=self.request.user).order_by('-updated_at')
        
        context.update({
            'can_create': can_create,
            'books': books,
        })
        
        return context


class BookDetailView(LoginRequiredMixin, TemplateView):
    """作品详情页面"""
    template_name = 'books/book_detail.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        
        book = get_object_or_404(Book, id=book_id)
        
        # 检查权限：作者可以查看自己的所有作品，其他用户只能查看通过审核的公开作品
        if book.author != self.request.user and not book.is_visible_to_public:
            raise Http404("作品不存在")
        
        # 获取章节列表
        chapters = Chapter.objects.filter(book=book).order_by('chapter_number')
        
        context.update({
            'book': book,
            'chapters': chapters,
        })
        
        return context


class ChapterDetailView(LoginRequiredMixin, TemplateView):
    """章节详情页面"""
    template_name = 'books/chapter_detail.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        chapter_number = kwargs.get('chapter_number')
        
        book = get_object_or_404(Book, id=book_id)
        chapter = get_object_or_404(Chapter, book=book, chapter_number=chapter_number)
        
        # 检查权限
        if book.author != self.request.user:
            raise Http404("作品不存在")
        
        context.update({
            'book': book,
            'chapter': chapter,
        })
        
        return context


class CreateBookView(LoginRequiredMixin, TemplateView):
    """创建新作品页面"""
    template_name = 'books/create_book.html'
    login_url = '/accounts/login/'
    
    def post(self, request, *args, **kwargs):
        """处理创建作品的POST请求"""
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not title:
            return JsonResponse({'success': False, 'error': '作品标题不能为空'})
        
        try:
            with transaction.atomic():
                # AI审核标题和描述
                try:
                    title_ai_result = check_content_by_ai(title)
                except Exception as e:
                    title_ai_result = {'approved': False, 'reason': f'AI审核服务不可用: {str(e)}'}
                
                try:
                    description_ai_result = check_content_by_ai(description) if description else {'approved': True, 'reason': ''}
                except Exception as e:
                    description_ai_result = {'approved': False, 'reason': f'AI审核服务不可用: {str(e)}'}
                
                # 确定审核状态和pending字段
                ai_title_status = 'approved' if title_ai_result['approved'] else 'pending'
                ai_desc_status = 'approved' if description_ai_result['approved'] else 'pending'
                
                book = Book.objects.create(
                    author=request.user,
                    title=title if title_ai_result['approved'] else '',
                    description=description if description_ai_result['approved'] else '',
                    title_pending=title if not title_ai_result['approved'] else None,
                    description_pending=description if not description_ai_result['approved'] else None,
                    ai_check_title=ai_title_status,
                    ai_check_description=ai_desc_status,
                    title_reject_reason=title_ai_result.get('reason', ''),
                    description_reject_reason=description_ai_result.get('reason', '')
                )
                
                # 创建草稿
                BookDraft.objects.create(
                    book=book,
                    title=title,
                    description=description
                )
            
            # 构建响应消息
            messages = []
            if title_ai_result['approved'] and description_ai_result['approved']:
                messages.append('✅ 作品创建成功，AI审核通过')
            else:
                messages.append('📝 作品创建成功')
                if not title_ai_result['approved']:
                    messages.append(f'❌ AI审核标题不通过：{title_ai_result.get("reason", "未知原因")}')
                if not description_ai_result['approved']:
                    messages.append(f'❌ AI审核简介不通过：{description_ai_result.get("reason", "未知原因")}')
                if not title_ai_result['approved'] or not description_ai_result['approved']:
                    messages.append('⏳ 请等待管理员审核')
            
            return JsonResponse({
                'success': True,
                'message': '\n'.join(messages),
                'book_id': book.id,
                'ai_check_status': {
                    'title': book.ai_check_title,
                    'description': book.ai_check_description,
                    'title_reason': title_ai_result.get('reason', ''),
                    'description_reason': description_ai_result.get('reason', '')
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': '创建失败，请稍后重试'
            })


class EditBookView(LoginRequiredMixin, TemplateView):
    """编辑作品页面"""
    template_name = 'books/edit_book.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        
        book = get_object_or_404(Book, id=book_id)
        
        # 检查权限
        if book.author != self.request.user:
            raise Http404("作品不存在")
        
        context.update({
            'book': book,
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """处理编辑作品的POST请求"""
        book_id = kwargs.get('book_id')
        book = get_object_or_404(Book, id=book_id)
        
        # 检查权限
        if book.author != request.user:
            return JsonResponse({'success': False, 'error': '权限不足'})
        
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not title:
            return JsonResponse({'success': False, 'error': '作品标题不能为空'})
        
        try:
            with transaction.atomic():
                # 检查是否有实际修改
                title_changed = title != book.title
                description_changed = description != book.description
                
                if title_changed or description_changed:
                    # 如果有修改，进行AI审核
                    if title_changed:
                        title_ai_result = check_content_by_ai(title)
                        book.title_pending = title
                        book.ai_check_title = 'approved' if title_ai_result['approved'] else 'rejected'
                        book.title_reject_reason = title_ai_result.get('reason', '')
                        book.adm_check_title = None  # 重置管理员审核
                        
                        # 如果AI审核通过，直接更新正式字段
                        if title_ai_result['approved']:
                            book.title = title
                    
                    if description_changed:
                        description_ai_result = check_content_by_ai(description) if description else {'approved': True, 'reason': ''}
                        book.description_pending = description
                        book.ai_check_description = 'approved' if description_ai_result['approved'] else 'rejected'
                        book.description_reject_reason = description_ai_result.get('reason', '')
                        book.adm_check_description = None  # 重置管理员审核
                        
                        # 如果AI审核通过，直接更新正式字段
                        if description_ai_result['approved']:
                            book.description = description
                    
                    book.save()
                    
                    # 更新草稿
                    draft, created = BookDraft.objects.get_or_create(book=book)
                    draft.title = title
                    draft.description = description
                    draft.save()
                    
                    # 构建响应消息
                    messages = []
                    if title_changed or description_changed:
                        # 检查AI审核状态
                        title_ai_approved = not title_changed or book.ai_check_title == 'approved'
                        desc_ai_approved = not description_changed or book.ai_check_description == 'approved'
                        
                        if title_ai_approved and desc_ai_approved:
                            messages.append('✅ 作品修改成功，AI审核通过')
                        else:
                            messages.append('📝 作品修改成功')
                            if title_changed and book.ai_check_title == 'pending':
                                title_reason = getattr(book, 'title_reject_reason', '')
                                if title_reason:
                                    messages.append(f'⚠️ AI审核标题不通过：{title_reason}')
                            if description_changed and book.ai_check_description == 'pending':
                                desc_reason = getattr(book, 'description_reject_reason', '')
                                if desc_reason:
                                    messages.append(f'⚠️ AI审核简介不通过：{desc_reason}')
                            if not (title_ai_approved and desc_ai_approved):
                                messages.append('⏳ 请等待管理员审核')
                    else:
                        messages.append('ℹ️ 没有检测到修改')
                    
                    message = '\n'.join(messages)
            
            return JsonResponse({
                'success': True,
                'message': message,
                'ai_check_status': {
                    'title': book.ai_check_title,
                    'description': book.ai_check_description
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': '修改失败，请稍后重试'
            })


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


class CreateChapterView(LoginRequiredMixin, TemplateView):
    """创建章节页面"""
    template_name = 'books/create_chapter.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        
        book = get_object_or_404(Book, id=book_id)
        
        # 检查权限
        if book.author != self.request.user:
            raise Http404("作品不存在")
        
        context.update({
            'book': book,
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """处理创建章节的POST请求"""
        book_id = kwargs.get('book_id')
        book = get_object_or_404(Book, id=book_id)
        
        # 检查权限
        if book.author != request.user:
            return JsonResponse({'success': False, 'error': '权限不足'})
        
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
                
                # AI审核标题和内容
                title_ai_result = check_content_by_ai(title)
                content_ai_result = check_content_by_ai(content)
                
                chapter = Chapter.objects.create(
                    book=book,
                    author=request.user,
                    chapter_number=chapter_number,
                    title=title,
                    content=content,
                    ai_check_title='approved' if title_ai_result['approved'] else 'rejected',
                    ai_check_content='approved' if content_ai_result['approved'] else 'rejected',
                    title_reject_reason=title_ai_result.get('reason', ''),
                    content_reject_reason=content_ai_result.get('reason', '')
                )
                
                # 创建草稿
                ChapterDraft.objects.create(
                    book=book,
                    author=request.user,
                    chapter_number=chapter_number,
                    title=title,
                    content=content
                )
                
                # 更新作品的最后章节更新时间
                book.last_chapter_update = timezone.now()
                book.save()
            
            # 构建响应消息
            if title_ai_result['approved'] and content_ai_result['approved']:
                message = '章节创建成功，AI审核通过'
            else:
                message = '章节创建成功，但AI审核未通过，请等待管理员审核'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'chapter_number': chapter_number,
                'ai_check_status': {
                    'title': chapter.ai_check_title,
                    'content': chapter.ai_check_content
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': '创建失败，请稍后重试'
            })


class EditChapterView(LoginRequiredMixin, TemplateView):
    """编辑章节页面"""
    template_name = 'books/edit_chapter.html'
    login_url = '/accounts/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book_id = kwargs.get('book_id')
        chapter_number = kwargs.get('chapter_number')
        
        book = get_object_or_404(Book, id=book_id)
        chapter = get_object_or_404(Chapter, book=book, chapter_number=chapter_number)
        
        # 检查权限
        if book.author != self.request.user:
            raise Http404("作品不存在")
        
        context.update({
            'book': book,
            'chapter': chapter,
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """处理编辑章节的POST请求"""
        book_id = kwargs.get('book_id')
        chapter_number = kwargs.get('chapter_number')
        
        book = get_object_or_404(Book, id=book_id)
        chapter = get_object_or_404(Chapter, book=book, chapter_number=chapter_number)
        
        # 检查权限
        if book.author != request.user:
            return JsonResponse({'success': False, 'error': '权限不足'})
        
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        
        if not title:
            return JsonResponse({'success': False, 'error': '章节标题不能为空'})
        
        if not content:
            return JsonResponse({'success': False, 'error': '章节内容不能为空'})
        
        try:
            with transaction.atomic():
                # 检查是否有实际修改
                title_changed = title != chapter.title
                content_changed = content != chapter.content
                
                if title_changed or content_changed:
                    # 如果有修改，进行AI审核
                    if title_changed:
                        title_ai_result = check_content_by_ai(title)
                        chapter.title_pending = title
                        chapter.ai_check_title = 'approved' if title_ai_result['approved'] else 'rejected'
                        chapter.title_reject_reason = title_ai_result.get('reason', '')
                        chapter.adm_check_title = None  # 重置管理员审核
                        
                        # 如果AI审核通过，直接更新正式字段
                        if title_ai_result['approved']:
                            chapter.title = title
                    
                    if content_changed:
                        content_ai_result = check_content_by_ai(content)
                        chapter.content_pending = content
                        chapter.ai_check_content = 'approved' if content_ai_result['approved'] else 'rejected'
                        chapter.content_reject_reason = content_ai_result.get('reason', '')
                        chapter.adm_check_content = None  # 重置管理员审核
                        
                        # 如果AI审核通过，直接更新正式字段
                        if content_ai_result['approved']:
                            chapter.content = content
                    
                    chapter.save()
                    
                    # 更新草稿
                    draft, created = ChapterDraft.objects.get_or_create(
                        book=book, 
                        chapter_number=chapter_number,
                        defaults={'author': request.user}
                    )
                    draft.title = title
                    draft.content = content
                    draft.save()
                    
                    # 更新作品的最后章节更新时间
                    book.last_chapter_update = timezone.now()
                    book.save()
                    
                    # 构建响应消息
                    ai_passed = True
                    if title_changed and chapter.ai_check_title == 'rejected':
                        ai_passed = False
                    if content_changed and chapter.ai_check_content == 'rejected':
                        ai_passed = False
                    
                    if ai_passed:
                        message = '章节修改成功，AI审核通过'
                    else:
                        message = '章节修改成功，但AI审核未通过，请等待管理员审核'
                else:
                    message = '没有检测到修改'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'ai_check_status': {
                    'title': chapter.ai_check_title,
                    'content': chapter.ai_check_content
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'修改失败: {str(e)}'
            })


# API 视图类
class SearchAPIView(LoginRequiredMixin, TemplateView):
    """搜索API"""
    
    def get(self, request, *args, **kwargs):
        return JsonResponse({'success': True, 'results': []})


class AutoSaveBookAPIView(LoginRequiredMixin, TemplateView):
    """自动保存作品API"""
    
    def post(self, request, *args, **kwargs):
        return JsonResponse({'success': True, 'message': '保存成功'})


class AutoSaveChapterAPIView(LoginRequiredMixin, TemplateView):
    """自动保存章节API"""
    
    def post(self, request, *args, **kwargs):
        return JsonResponse({'success': True, 'message': '保存成功'})


class PublishBookAPIView(LoginRequiredMixin, TemplateView):
    """发布作品API"""
    
    def post(self, request, *args, **kwargs):
        return JsonResponse({'success': True, 'message': '发布成功'})


class PublishChapterAPIView(LoginRequiredMixin, TemplateView):
    """发布章节API"""
    
    def post(self, request, *args, **kwargs):
        return JsonResponse({'success': True, 'message': '发布成功'})


class AdminPanelView(LoginRequiredMixin, TemplateView):
    """管理员面板"""
    template_name = 'books/admin_panel.html'
    login_url = '/accounts/login/'
    
    def dispatch(self, request, *args, **kwargs):
        # 检查管理员权限
        if not getattr(request.user, 'is_admin', False):
            raise Http404("页面不存在")
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取需要管理员审核的作品
        # 1. AI审核为pending的
        # 2. AI审核为rejected但管理员尚未审核的
        pending_books = Book.objects.filter(
            Q(ai_check_title='pending') | 
            Q(ai_check_description='pending') |
            Q(ai_check_title='rejected', adm_check_title__isnull=True) |
            Q(ai_check_description='rejected', adm_check_description__isnull=True)
        ).order_by('-updated_at')
        
        # 获取需要管理员审核的章节
        # 1. AI审核为pending的
        # 2. AI审核为rejected但管理员尚未审核的
        pending_chapters = Chapter.objects.filter(
            Q(ai_check_title='pending') | 
            Q(ai_check_content='pending') |
            Q(ai_check_title='rejected', adm_check_title__isnull=True) |
            Q(ai_check_content='rejected', adm_check_content__isnull=True)
        ).order_by('-updated_at')
        
        context.update({
            'pending_books': pending_books,
            'pending_chapters': pending_chapters,
            'pending_books_count': pending_books.count(),
            'pending_chapters_count': pending_chapters.count(),
            # 添加统计数据
            'total_users': User.objects.count(),
            'total_books': Book.objects.count(),
            'total_chapters': Chapter.objects.count(),
            'total_comments': Comment.objects.count(),
        })
        
        return context


class AdminReviewView(LoginRequiredMixin, TemplateView):
    """管理员审核页面"""
    template_name = 'books/admin_review.html'
    login_url = '/accounts/login/'
    
    def dispatch(self, request, *args, **kwargs):
        # 检查管理员权限
        if not getattr(request.user, 'is_admin', False):
            raise Http404("页面不存在")
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_id = kwargs.get('content_id')
        
        try:
            book = get_object_or_404(Book, id=content_id)
            context['book'] = book
            
            # 检查是否需要审核
            needs_title_review = book.ai_check_title == 'rejected' and book.adm_check_title is None
            needs_description_review = book.ai_check_description == 'rejected' and book.adm_check_description is None
            
            context.update({
                'needs_title_review': needs_title_review,
                'needs_description_review': needs_description_review,
                'has_pending_review': needs_title_review or needs_description_review
            })
            
        except Book.DoesNotExist:
            context['book'] = None
            context['error'] = '作品不存在'
        
        return context
    
    def post(self, request, *args, **kwargs):
        """处理审核结果提交"""
        print(f"收到POST请求: {request.POST}")  # 调试信息
        print(f"用户: {request.user}, is_admin: {getattr(request.user, 'is_admin', False)}")  # 调试信息
        
        if not getattr(request.user, 'is_admin', False):
            return JsonResponse({'success': False, 'error': '权限不足'})
        
        content_id = kwargs.get('content_id')
        print(f"content_id: {content_id}")  # 调试信息
        
        try:
            book = get_object_or_404(Book, id=content_id)
            print(f"找到作品: {book.display_title}")  # 调试信息
            
            # 获取审核结果
            title_action = request.POST.get('title_action')  # approve/reject
            description_action = request.POST.get('description_action')  # approve/reject
            title_reason = request.POST.get('title_reason', '')
            description_reason = request.POST.get('description_reason', '')
            
            print(f"审核参数: title_action={title_action}, description_action={description_action}")  # 调试信息
            
            messages = []
            
            # 处理标题审核
            if title_action in ['approve', 'reject']:
                if title_action == 'approve':
                    book.adm_check_title = 'approved'
                    book.title_reject_reason = ''
                    if book.title_pending:
                        book.title = book.title_pending
                        book.title_pending = ''
                    messages.append('✅ 标题审核通过')
                else:
                    book.adm_check_title = 'rejected'
                    book.title_reject_reason = title_reason or '不符合社区规范'
                    messages.append('❌ 标题审核不通过')
            
            # 处理简介审核
            if description_action in ['approve', 'reject']:
                if description_action == 'approve':
                    book.adm_check_description = 'approved'
                    book.description_reject_reason = ''
                    if book.description_pending:
                        book.description = book.description_pending
                        book.description_pending = ''
                    messages.append('✅ 简介审核通过')
                else:
                    book.adm_check_description = 'rejected'
                    book.description_reject_reason = description_reason or '不符合社区规范'
                    messages.append('❌ 简介审核不通过')
            
            book.save()
            print(f"保存成功，消息: {messages}")  # 调试信息
            
            return JsonResponse({
                'success': True,
                'message': '\n'.join(messages)
            })
            
        except Book.DoesNotExist:
            print("作品不存在")  # 调试信息
            return JsonResponse({'success': False, 'error': '作品不存在'})
        except Exception as e:
            print(f"异常: {e}")  # 调试信息
            return JsonResponse({'success': False, 'error': '审核失败，请稍后重试'})


class AdminChapterReviewView(LoginRequiredMixin, TemplateView):
    """管理员章节审核页面"""
    template_name = 'books/admin_chapter_review.html'
    login_url = '/accounts/login/'


# 函数视图
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
