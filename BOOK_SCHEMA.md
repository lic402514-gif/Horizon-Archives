# 图书卡（Book）数据库表结构

## 主表：books

| # | 字段 | 类型 | 空 | 说明 |
|---|------|------|:--:|------|
| 1 | `id` | INTEGER | PK | 自增主键 |
| 2 | `title` | VARCHAR(300) | ❌ | 书名 |
| 3 | `author_id` | INTEGER | ✅ | 外键 → `authors.id` |
| 4 | `publisher_id` | INTEGER | ✅ | 外键 → `publishers.id` |
| 5 | `isbn` | VARCHAR(20) | ✅ | 国际标准书号 |
| 6 | `edition` | VARCHAR(20) | ✅ | 版次（如"第1版"） |
| 7 | `pub_year` | INTEGER | ✅ | 出版年份 |
| 8 | `category_code` | VARCHAR(20) | ✅ | 外键 → `categories.code`（中图法分类号） |
| 9 | `summary` | TEXT | ✅ | 内容简介 |
| 10 | `status` | VARCHAR(20) | ✅ | 状态：published / draft |
| 11 | `created_at` | DATETIME | ✅ | 创建时间 |
| 12 | `updated_at` | DATETIME | ✅ | 最后修改时间 |

### ORM 关系（不是数据库列，但 API 返回时会展开）

| 关系 | 对应模型 | 说明 |
|------|---------|------|
| `author` | Author | 作者对象 `.name` |
| `publisher` | Publisher | 出版社对象 `.name` |
| `category` | Category | 分类对象 `.code` + `.name` |
| `tags` | Tag[] | 多对多标签列表 |
| `files` | File[] | 关联的文件资源（旧版） |
| `book_assets_rel` | BookAsset[] | 新版资源映射 |

---

## 关联表

### authors

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增 |
| `name` | VARCHAR(50) UNIQUE | 作者姓名 |
| `bio` | TEXT | 作者简介 |

### publishers

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增 |
| `name` | VARCHAR(100) | 出版社名称 |
| `address` | VARCHAR(100) | 地址 |

### categories（中图法分类）

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | VARCHAR(10) PK | 分类号，如 "A81" |
| `name` | VARCHAR(100) | 分类名称 |
| `parent_code` | VARCHAR(10) | 父分类号，NULL=顶层 |

### tags

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增 |
| `name` | VARCHAR(50) | 标签名 |

### book_tags（多对多）

| 字段 | 类型 |
|------|------|
| `book_id` | FK → books.id |
| `tag_id` | FK → tags.id |

### files（旧版资源文件）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增 |
| `book_id` | FK → books.id | 所属书籍 |
| `format` | VARCHAR(10) | PDF / EPUB 等 |
| `oss_key` | VARCHAR(256) | OSS 存储路径 |
| `size` | INTEGER | 文件大小 |
| `sha256` | VARCHAR(64) | 哈希校验 |
| `uploaded_at` | DATETIME | 上传时间 |

### assets（新版资源文件）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增 |
| `filename` | VARCHAR(300) | 原始文件名 |
| `oss_key` | VARCHAR(500) | OSS 存储路径 |
| `url` | VARCHAR(500) | 完整访问 URL |
| `size` | INTEGER | 文件大小 |
| `mime` | VARCHAR(50) | MIME 类型 |
| `asset_type` | VARCHAR(50) | ebook / book_cover / user_avatar / article_image 等 |
| `uploaded_by` | FK → users.id | 上传者 |
| `created_at` | DATETIME | 上传时间 |

### book_assets（资源映射）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增 |
| `book_id` | FK → books.id | 所属书籍 |
| `asset_id` | FK → assets.id | 资源文件 |
| `role` | VARCHAR(20) | cover / ebook |
| `format` | VARCHAR(20) | 格式标签（PDF/EPUB 等） |

---

## 数据示例（API 返回格式）

```json
{
  "id": 1,
  "title": "资本论",
  "author_name": "马克思",
  "publisher_name": "人民出版社",
  "isbn": "9787100000000",
  "edition": "第1版",
  "pub_year": 1867,
  "category_code": "A81",
  "summary": "……",
  "status": "published",
  "created_at": "2026-07-10T12:00:00+00:00",
  "updated_at": "2026-07-10T12:30:00+00:00",
  "tags": [
    {"id": 1, "name": "马克思主义"},
    {"id": 4, "name": "经济学"}
  ],
  "files": [
    {"id": 10, "format": "PDF", "size": 2345678}
  ],
  "book_assets_rel": []
}
```

注：`author_name`、`publisher_name`、`tags` 等是 API 层通过 ORM 关系自动加载的，不是数据库原始列。
