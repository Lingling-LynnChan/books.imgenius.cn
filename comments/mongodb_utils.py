"""
评论相关的MongoDB操作工具类
"""
from datetime import datetime
from django.conf import settings
from bson import ObjectId
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


def get_book_comments(book_id):
    """获取作品评论"""
    collection = get_mongodb_collection('comments')
    if collection is None:
        return []
    
    comments = collection.find({
        'book_id': book_id,
        'chapter_number': None
    }).sort('created_at', -1)
    
    return list(comments)


def get_chapter_comments(book_id, chapter_number):
    """获取章节评论"""
    collection = get_mongodb_collection('comments')
    if collection is None:
        return []
    
    comments = collection.find({
        'book_id': book_id,
        'chapter_number': chapter_number
    }).sort('created_at', -1)
    
    return list(comments)


def add_comment(comment_data):
    """添加评论"""
    collection = get_mongodb_collection('comments')
    if collection is None:
        return None
    
    result = collection.insert_one(comment_data)
    return result.inserted_id


def get_comment(comment_id):
    """获取单个评论"""
    collection = get_mongodb_collection('comments')
    if collection is None:
        return None
    
    if isinstance(comment_id, str):
        comment_id = ObjectId(comment_id)
    
    return collection.find_one({'_id': comment_id})


def update_comment_review_status(comment_id, update_data):
    """更新评论审核状态"""
    collection = get_mongodb_collection('comments')
    if collection is None:
        return None
    
    if isinstance(comment_id, str):
        comment_id = ObjectId(comment_id)
    
    update_data['updated_at'] = datetime.now()
    
    return collection.update_one(
        {'_id': comment_id},
        {'$set': update_data}
    )


def delete_comment(comment_id):
    """删除评论"""
    collection = get_mongodb_collection('comments')
    if collection is None:
        return None
    
    if isinstance(comment_id, str):
        comment_id = ObjectId(comment_id)
    
    return collection.delete_one({'_id': comment_id})


def get_pending_comment_reviews():
    """获取待审核评论"""
    collection = get_mongodb_collection('comments')
    if collection is None:
        return []
    
    comments = collection.find({
        '$or': [
            {'ai_check': 'approved', 'adm_check': {'$ne': 'approved'}},
            {'ai_check': 'rejected'},
            {'adm_check': {'$exists': False}},
        ]
    }).sort('updated_at', -1)
    
    return list(comments)


def search_comments(search_query, book_ids=None):
    """搜索评论"""
    collection = get_mongodb_collection('comments')
    if collection is None:
        return []
    
    search_filter = {
        'content': {'$regex': search_query, '$options': 'i'},
        'is_visible': True,
    }
    
    if book_ids:
        search_filter['book_id'] = {'$in': book_ids}
    
    return list(collection.find(search_filter).sort('created_at', -1))
