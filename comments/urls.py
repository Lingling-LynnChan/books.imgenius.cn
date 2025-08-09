from django.urls import path
from . import views

app_name = 'comments'

urlpatterns = [
    path('add/', views.AddCommentView.as_view(), name='add_comment'),
    path('book/<int:book_id>/', views.BookCommentsView.as_view(), name='book_comments'),
    path('chapter/<int:book_id>/<int:chapter_number>/', views.ChapterCommentsView.as_view(), name='chapter_comments'),
    path('api/add/', views.AddCommentAPIView.as_view(), name='api_add_comment'),
]
