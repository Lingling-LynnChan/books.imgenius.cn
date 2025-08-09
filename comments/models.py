"""
评论相关的MongoDB文档存储在MongoDB中

Comment 文档结构:
{
    "_id": ObjectId,
    "book_id": int,  # 作品ID
    "chapter_number": int,  # 章节号（如果是章节评论），null表示作品评论
    "author_id": int,  # 评论者ID
    "content": str,  # 评论内容
    "content_pending": str,  # 待审核内容
    "ai_check": str,  # AI审核状态 pending/approved/rejected
    "adm_check": str,  # 管理员审核状态 pending/approved/rejected
    "reject_reason": str,  # 拒绝原因
    "created_at": datetime,
    "updated_at": datetime,
    "is_visible": bool,  # 是否可见（审核通过后为True）
}
"""

# 由于评论存储在MongoDB中，这里只需要一个占位文件来保持Django应用结构的完整性
# 实际的评论操作将通过MongoDB工具类来处理
