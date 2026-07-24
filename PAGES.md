# 个人图书馆资源小站 — 页面结构与功能总览

> 生成时间：2026-07-13  
> 项目路径：`C:\Users\Lucian\personal-library`  
> 本地访问：`http://localhost:8000`

---

## 一、页面树

```
/
├── index.html                          ← 首页（📖 图书 + 📰 文章）
├── book/
│   ├── 1.html   (德意志意识形态)
│   ├── 2.html   (资本论 第一卷)
│   ├── 3.html   (自然辩证法)
│   ├── 4.html   (毛泽东选集 第一卷)
│   ├── 5.html   (呐喊)
│   ├── 6.html   (围城)
│   └── 7.html   (乡土中国)
├── category/
│   ├── A.html    (马克思主义、列宁主义...)
│   ├── A4.html
│   ├── A8.html
│   ├── A81.html
│   ├── C.html    (社会科学总论)
│   ├── I.html    (文学)
│   ├── I2.html
│   └── I24.html
├── author/
│   ├── 马克思-karl-marx.html
│   ├── 恩格斯-friedrich-engels.html
│   ├── 毛泽东.html
│   ├── 鲁迅.html
│   ├── 钱钟书.html
│   └── 费孝通.html
├── publisher/
│   ├── 人民出版社.html
│   ├── 人民文学出版社.html
│   └── 三联书店.html
├── tag/
│   ├── 经典.html
│   ├── 经济学.html
│   ├── 历史唯物主义.html
│   ├── 马克思主义.html
│   ├── 社会学.html
│   ├── 哲学.html
│   └── 中国文学.html
├── articles/
│   └── {slug}.html                     ← 已发布文章（SSG 生成）
├── login                               ← 用户登录
├── register                            ← 用户注册（邀请码）
├── sitemap.xml                         ← 搜索引擎站点地图
├── robots.txt                          ← 爬虫规则
├── rss.xml                             ← RSS 订阅源
├── admin/                              ← 管理后台（需登录）
│   ├── login                           ← 管理员登录
│   ├── (dashboard)                     ← 仪表盘
│   ├── book-upload                     ← 资源上传
│   ├── books                           ← 图书管理
│   ├── assets                          ← 资源库（OSS 资源管理）
│   ├── articles                        ← 文章管理列表
│   ├── article-editor                  ← 文章编辑器（Markdown）
│   ├── users                           ← 用户管理
│   ├── invite-codes                    ← 邀请码管理
│   ├── catalog                         ← 分类 / 作者 / 出版社 / 标签管理
│   ├── roles                           ← 角色权限管理
│   └── stats                           ← 下载统计
└── api/                                ← REST API（JSON，非页面）
    ├── /api/token                      ← 登录获取 JWT Cookie
    ├── /api/me                         ← 当前用户信息 + 头像
    ├── /api/me/permissions             ← 当前用户权限列表
    ├── /api/users                      ← 用户管理 CRUD
    ├── /api/users/{id}/roles           ← 用户角色分配
    ├── /api/users/me/avatar            ← 更新头像
    ├── /api/books                      ← 图书 CRUD
    ├── /api/books/datagrid             ← 图书列表（分页/搜索/排序）
    ├── /api/books/batch                ← 批量导入 JSON
    ├── /api/books/export/csv           ← CSV 导出
    ├── /api/authors                    ← 作者 CRUD
    ├── /api/publishers                 ← 出版社 CRUD
    ├── /api/tags                       ← 标签 CRUD
    ├── /api/categories                 ← 分类 CRUD
    ├── /api/download/{book_id}         ← 下载（Cookie 鉴权 → 302 OSS）
    ├── /api/upload-url                 ← 生成上传链接
    ├── /api/assets/upload              ← 上传文件到 OSS
    ├── /api/assets/datagrid            ← 资源列表
    ├── /api/assets/{id}/refs           ← 资源引用关系
    ├── /api/articles                   ← 文章 CRUD
    ├── /api/articles/{id}/publish      ← 发布文章（SSG 生成 HTML）
    ├── /api/invite-codes               ← 邀请码 CRUD
    ├── /api/register                   ← 用户注册
    ├── /api/admin/rbac/roles           ← 角色列表
    ├── /api/admin/rbac/permissions     ← 权限列表
    ├── /api/admin/rebuild              ← 触发 SSG 重建
    ├── /api/stats/summary              ← 统计数据
    └── /api/health                     ← 健康检查
```

---

## 二、逐页功能说明

### 公共前台（SSG 静态页面）

| 页面 | URL | 功能 |
|------|-----|------|
| 首页 | `/` | 展示最新 20 本图书列表 + 最新 10 篇文章 + 分类浏览卡片 + 搜索引擎入口 |
| 图书详情 | `/book/{id}.html` | 书名、作者、出版社、ISBN、分类、摘要、标签、下载按钮（Cookie 检测登录状态） |
| 分类页 | `/category/{code}.html` | 该分类及其子分类下所有图书列表（前缀匹配，如 A 包含 A4/A8/A81） |
| 作者页 | `/author/{slug}.html` | 该作者所有图书列表 |
| 出版社页 | `/publisher/{slug}.html` | 该出版社所有图书列表 |
| 标签页 | `/tag/{slug}.html` | 该标签所有图书列表 |
| 文章详情 | `/articles/{slug}.html` | 文章正文（Markdown→HTML）、封面图、SEO meta 标签 |
| 用户登录 | `/login` | 表单登录，Set-Cookie JWT，登录后跳回来源页 |
| 用户注册 | `/register` | 邀请码校验 → 填写用户信息 → 自动获得 Member 角色 → 自动登录 |

### 管理后台（需登录，Cookie 鉴权）

| 页面 | URL | 功能 |
|------|-----|------|
| 管理员登录 | `/admin/login` | 登录后跳转仪表盘 |
| 仪表盘 | `/admin` | 图书数量、用户数量、下载次数统计卡片 |
| 资源上传 | `/admin/book-upload` | 双栏：左侧填写图书元数据，右侧上传封面 + 电子书，一键创建并建立 BookAsset 映射 |
| 图书管理 | `/admin/books` | Grid 表格：搜索、筛选、排序、新增/编辑/删除、JSON 批量导入、CSV 导出、发布按钮 |
| 资源库 | `/admin/assets` | Grid 表格：全局 OSS 资源管理，类型筛选（chips）、搜索、上传、编辑、批量删除、CSV 导出、引用查看 |
| 文章管理 | `/admin/articles` | 文章列表：发布、编辑、删除、查看 |
| 文章编辑器 | `/admin/article-editor` | 双栏 Markdown 编辑器 + 实时预览，工具栏（加粗/斜体/标题/列表/引用/链接/图片上传） |
| 用户管理 | `/admin/users` | 用户列表：创建、封禁/解封、改角色、角色分配、重置密码 |
| 邀请码 | `/admin/invite-codes` | 生成邀请码（含备注/有效期/使用次数），一键复制，作废/删除 |
| 分类管理 | `/admin/catalog` | 中图法分类 + 作者 + 出版社 + 标签 的 CRUD |
| 权限管理 | `/admin/roles` | 4 个预定义角色（Super Admin / Library Admin / Account Admin / Member），21 个权限码分配 |
| 统计 | `/admin/stats` | 下载日志表格、按日期筛选 |

---

## 三、无入口的孤立页面

以下页面无法通过任何链接点击到达，只能手动输入 URL：

| 页面 | URL | 缺少入口的位置 |
|------|-----|---------------|
| 用户注册 | `/register` | 首页无"注册"链接 |
| 出版社页 | `/publisher/{slug}.html` | 首页无出版社浏览入口 |
| 标签页 | `/tag/{slug}.html` | 首页无标签浏览入口 |
| 作者页 | `/author/{slug}.html` | 首页无作者浏览入口 |

---

## 四、权限体系

| 角色 | 权限范围 |
|------|---------|
| Super Admin | 全部 21 项权限（user.*, book.*, oss.*, system.*, role.*, audit.*） |
| Library Admin | 图书管理 + 上传 + 发布 + OSS (book.*, oss.*, book.publish) |
| Account Admin | 用户管理 + 邀请码 (user.*) |
| Member | 仅 book.read（浏览 + 下载） |

---

## 五、技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI (Python 3.11) |
| 数据库 | SQLite (13 张表) |
| 前端模板 | Jinja2（SSG 生成静态 HTML） |
| 管理后台 | 纯 HTML + Vanilla JS（无框架） |
| 认证 | JWT → Cookie (session) |
| 文件存储 | 阿里云 OSS（或本地 data/files/） |
| 部署 | Docker Compose (Nginx + FastAPI) |
| CDN/下载 | OSS 预签名 URL，302 重定向 |
