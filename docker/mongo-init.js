// MongoDB初始化脚本
// 创建应用数据库和用户

// 切换到admin数据库
db = db.getSiblingDB('admin');

// 创建应用用户
db.createUser({
  user: 'booksite_user',
  pwd: 'booksite_password',
  roles: [
    {
      role: 'readWrite',
      db: 'booksite'
    }
  ]
});

// 切换到应用数据库
db = db.getSiblingDB('booksite');

// 创建一些基础集合和索引
db.createCollection('books');
db.createCollection('comments');
db.createCollection('users');

// 为books集合创建索引
db.books.createIndex({ "title": "text", "content": "text" });
db.books.createIndex({ "author": 1 });
db.books.createIndex({ "created_at": -1 });

// 为comments集合创建索引
db.comments.createIndex({ "book_id": 1 });
db.comments.createIndex({ "created_at": -1 });

// 为users集合创建索引
db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });

print('MongoDB initialization completed!');
