"""
Books应用的MongoDB操作工具类
"""
from datetime import datetime
from django.conf import settings
from django.db import models
import pymongo

# 全局MongoDB连接
_mongo_client = None
_mongodb = None

def get_mongodb_connection():
    """获取MongoDB连接"""
    global _mongo_client, _mongodb
    
    if _mongodb is None:
        try:
            _mongo_client = pymongo.MongoClient(settings.MONGODB_URI)
            _mongodb = _mongo_client[settings.MONGODB_NAME]
        except Exception as e:
            print(f"MongoDB connection error: {e}")
            _mongodb = None
    
    return _mongodb


def get_mongodb_collection(collection_name):
    """获取MongoDB集合"""
    mongodb = get_mongodb_connection()
    if mongodb is not None:
        return mongodb[collection_name]
    return None


def get_book_chapters(book_id):
    """获取作品的所有章节"""
    collection = get_mongodb_collection('chapters')
    if collection is None:
        return []
    
    chapters = collection.find(
        {'book_id': book_id}
    ).sort('chapter_number', 1)
    
    return list(chapters)


def get_chapter(book_id, chapter_number):
    """获取指定章节"""
    collection = get_mongodb_collection('chapters')
    if collection is None:
        return None
    
    return collection.find_one({
        'book_id': book_id,
        'chapter_number': chapter_number
    })


def create_chapter(chapter_data):
    """创建新章节"""
    collection = get_mongodb_collection('chapters')
    if collection is None:
        return None
    
    return collection.insert_one(chapter_data)


def update_chapter(book_id, chapter_number, update_data):
    """更新章节"""
    collection = get_mongodb_collection('chapters')
    if collection is None:
        return None
    
    update_data['updated_at'] = datetime.now()
    
    return collection.update_one(
        {'book_id': book_id, 'chapter_number': chapter_number},
        {'$set': update_data}
    )


def delete_chapter(book_id, chapter_number):
    """删除章节"""
    collection = get_mongodb_collection('chapters')
    if collection is None:
        return None
    
    return collection.delete_one({
        'book_id': book_id,
        'chapter_number': chapter_number
    })


def save_chapter_draft(book_id, chapter_number, title, content, author_id):
    """保存章节草稿"""
    collection = get_mongodb_collection('chapter_drafts')
    if collection is None:
        return None
    
    draft_data = {
        'book_id': book_id,
        'chapter_number': chapter_number,
        'title': title,
        'content': content,
        'updated_at': datetime.now(),
        'author_id': author_id,
    }
    
    return collection.replace_one(
        {'book_id': book_id, 'chapter_number': chapter_number},
        draft_data,
        upsert=True
    )


def get_chapter_draft(book_id, chapter_number):
    """获取章节草稿"""
    collection = get_mongodb_collection('chapter_drafts')
    if collection is None:
        return None
    
    return collection.find_one({
        'book_id': book_id,
        'chapter_number': chapter_number
    })


def get_pending_reviews():
    """获取待审核内容"""
    chapters_collection = get_mongodb_collection('chapters')
    
    result = {
        'books': [],
        'chapters': []
    }
    
    # 获取待审核作品（从MySQL）
    from .models import Book
    pending_books = Book.objects.filter(
        # AI审核通过但管理员未审核的标题
        models.Q(ai_check_title='approved', adm_check_title__isnull=True) |
        # AI审核通过但管理员未审核的简介
        models.Q(ai_check_description='approved', adm_check_description__isnull=True) |
        # AI审核拒绝但管理员未审核的标题
        models.Q(ai_check_title='rejected', adm_check_title__isnull=True) |
        # AI审核拒绝但管理员未审核的简介
        models.Q(ai_check_description='rejected', adm_check_description__isnull=True) |
        # 有待审核内容且管理员未审核
        models.Q(title_pending__isnull=False, adm_check_title__isnull=True) |
        models.Q(description_pending__isnull=False, adm_check_description__isnull=True)
    ).order_by('-updated_at')
    
    result['books'] = list(pending_books)
    
    if chapters_collection is not None:
        # 获取待审核章节
        # 只有以下情况才需要管理员审核：
        # 1. AI审核通过但管理员未审核
        # 2. AI审核拒绝但管理员未审核
        # 3. 管理员已拒绝（需要重新审核）
        pending_chapters = chapters_collection.find({
            '$or': [
                # AI通过但管理员未审核（标题）
                {
                    'ai_check_title': 'approved', 
                    '$or': [
                        {'adm_check_title': {'$exists': False}},
                        {'adm_check_title': None}
                    ]
                },
                # AI通过但管理员未审核（内容）
                {
                    'ai_check_content': 'approved', 
                    '$or': [
                        {'adm_check_content': {'$exists': False}},
                        {'adm_check_content': None}
                    ]
                },
                # AI拒绝但管理员未审核（标题）
                {
                    'ai_check_title': 'rejected',
                    '$or': [
                        {'adm_check_title': {'$exists': False}},
                        {'adm_check_title': None}
                    ]
                },
                # AI拒绝但管理员未审核（内容）
                {
                    'ai_check_content': 'rejected',
                    '$or': [
                        {'adm_check_content': {'$exists': False}},
                        {'adm_check_content': None}
                    ]
                },
                # 有待审核标题且管理员未审核
                {
                    'title_pending': {'$ne': None},
                    '$or': [
                        {'adm_check_title': {'$exists': False}},
                        {'adm_check_title': None}
                    ]
                },
                # 有待审核内容且管理员未审核
                {
                    'content_pending': {'$ne': None},
                    '$or': [
                        {'adm_check_content': {'$exists': False}},
                        {'adm_check_content': None}
                    ]
                }
            ]
        }).sort('updated_at', -1)
        
        result['chapters'] = list(pending_chapters)
    
    return result


def search_chapters(search_query, book_ids=None):
    """搜索章节内容"""
    collection = get_mongodb_collection('chapters')
    if collection is None:
        return []
    
    search_filter = {
        '$or': [
            {'title': {'$regex': search_query, '$options': 'i'}},
            {'content': {'$regex': search_query, '$options': 'i'}},
        ],
        'ai_check_title': 'approved',
        'ai_check_content': 'approved',
        'adm_check_title': {'$ne': 'rejected'},
        'adm_check_content': {'$ne': 'rejected'},
    }
    
    if book_ids:
        search_filter['book_id'] = {'$in': book_ids}
    
    return list(collection.find(search_filter).sort('updated_at', -1))
