from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    # 主页和阅读页面
    path('', views.IndexView.as_view(), name='index'),
    path('read/', views.ReadView.as_view(), name='read'),
    path('book/<int:book_id>/', views.BookDetailView.as_view(), name='book_detail'),
    path('book/<int:book_id>/chapter/<int:chapter_number>/', views.ChapterDetailView.as_view(), name='chapter_detail'),
    
    # 创作页面
    path('create/', views.CreateView.as_view(), name='create'),
    path('create/new-book/', views.CreateBookView.as_view(), name='create_book'),
    path('create/book/<int:book_id>/', views.EditBookView.as_view(), name='edit_book'),
    path('create/book/<int:book_id>/chapters/', views.ChapterListView.as_view(), name='chapter_list'),
    path('create/book/<int:book_id>/chapter/new/', views.CreateChapterView.as_view(), name='create_chapter'),
    path('create/book/<int:book_id>/chapter/<int:chapter_number>/', views.EditChapterView.as_view(), name='edit_chapter'),
    
    # API接口
    path('api/search/', views.SearchAPIView.as_view(), name='api_search'),
    path('api/auto-save-book/', views.AutoSaveBookAPIView.as_view(), name='api_auto_save_book'),
    path('api/auto-save-chapter/', views.AutoSaveChapterAPIView.as_view(), name='api_auto_save_chapter'),
    path('api/publish-book/', views.PublishBookAPIView.as_view(), name='api_publish_book'),
    path('api/publish-chapter/', views.PublishChapterAPIView.as_view(), name='api_publish_chapter'),
    
    # 管理员页面
    path('admin-panel/', views.AdminPanelView.as_view(), name='admin_panel'),
    path('admin-panel/review/book/<int:content_id>/', views.AdminReviewView.as_view(), name='admin_review'),
    path('admin-panel/review/chapter/<int:book_id>/', views.AdminChapterReviewView.as_view(), name='admin_chapter_review'),
]
