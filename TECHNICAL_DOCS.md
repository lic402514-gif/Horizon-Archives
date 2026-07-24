# 个人图书馆资源小站 — 技术文档

> 版本 0.2.0 · 2026-07-11 · 工作区 `C:\Users\Lucian\personal-library\`

---

## 1. 架构概览

```
                     ┌──────────────┐
       浏览/搜索 ───►│  dist/ 静态页  │◄── SSG 构建器 ◄── 管理后台发布按钮
                     └──────┬───────┘
       下载鉴权 ───►│  FastAPI 后端  │──► SQLite / PostgreSQL
                     └──────┬───────┘
                     ┌──────┴───────┐
               本地模式         OSS 模式
            data/files/    阿里云 OSS 预签名URL
```

- **用户端**：预生成静态 HTML（Jinja2 → dist/），搜索引擎通过 sitemap.xml 索引
- **下载鉴权**：JWT 验证 → 302 重定向到本地文件或 OSS 预签名 URL（文件流不经过 VPS）
- **管理后台**：服务端渲染页面，客户端 JS 鉴权，完整 CRUD + 批量 JSON 导入
- **存储抽象**：一处环境变量切换本地/OSS，业务代码零改动

---

## 2. 项目结构

```
personal-library/
├── app/                          # FastAPI 后端
│   ├── main.py                   # 入口：生命周期、路由注册、统计API
│   ├── database.py               # SQLite 连接 + Session 管理
│   ├── models.py                 # 8 张表的 SQLAlchemy 模型
│   ├── schemas.py                # Pydantic 请求/响应模型
│   ├── auth.py                   # JWT、bcrypt、存储抽象层（本地/OSS）
│   └── routers/
│       ├── auth.py               # 登录、用户 CRUD、封禁/解封
│       ├── books.py              # 图书 CRUD + 批量 JSON 导入
│       ├── downloads.py          # 下载鉴权 → 302 重定向
│       ├── uploads.py            # 文件上传（本地 multipart / OSS 预签名 PUT）
│       └── admin.py              # 管理后台页面路由 + 站点重建
├── static_site/                  # 静态站点生成器
│   ├── generator.py              # 全量/增量构建、sitemap/robots/RSS
│   └── templates/                # Jinja2 模板
│       ├── base.html             # 公共头部（含登录入口）
│       ├── index.html            # 首页（分类导航 + 最新图书）
│       ├── book.html             # 图书详情（下载按钮 → /login?redirect=...）
│       ├── category.html         # 分类页
│       ├── author.html           # 作者页
│       ├── publisher.html        # 出版社页
│       └── tag.html              # 标签页
├── templates/                    # 服务端模板
│   ├── admin/
│   │   ├── base.html             # 管理后台布局（侧边栏 + JS SDK）
│   │   ├── login.html            # 管理员登录页
│   │   ├── dashboard.html        # 仪表盘（统计卡片 + 最近下载）
│   │   ├── books.html            # 图书管理（CRUD + 文件上传 + JSON批量导入）
│   │   ├── users.html            # 用户管理（封禁/解封/角色切换）
│   │   ├── catalog.html          # 分类/作者/出版社/标签管理
│   │   └── stats.html            # 下载统计
│   └── user/
│       └── login.html            # 用户登录页（支持 redirect 参数）
├── static/                       # 静态资源
│   └── style.css                 # 用户端样式
├── dist/                         # SSG 输出目录（gitignore）
├── data/                         # 运行时数据（gitignore）
│   ├── library.db                # SQLite 数据库
│   └── files/                    # 本地文件存储
├── .venv/                        # Python 虚拟环境
├── seed_data.py                  # 种子数据（中图法52分类 + 7本样书 + 4用户）
├── test_api.py                   # API 端到端测试
├── Dockerfile                    # Docker 镜像
├── docker-compose.yml            # Docker Compose（Nginx + FastAPI）
├── nginx.conf                    # Nginx 配置（静态站 + API反向代理）
├── requirements.txt              # Python 依赖
└── .env.example                  # 环境变量模板
```

---

## 3. 数据库设计

引擎：SQLite（开发），PostgreSQL 替换只需改 `DATABASE_URL`。

### 3.1 ER 图

```
categories (中图法树)         authors              publishers
┌──────────────────┐    ┌──────────────┐    ┌────────────────┐
│ code       PK    │    │ id      PK   │    │ id        PK   │
│ name             │    │ name         │    │ name           │
│ parent_code FK───┘    │ bio          │    │ address        │
└──────┬───────────┘    └──────┬───────┘    └──────┬─────────┘
       │                       │                   │
       │ category_code         │ author_id         │ publisher_id
       ▼                       ▼                   ▼
┌────────────────────────────────────────────────────────────┐
│                         books                               │
│  id PK | title | isbn | edition | pub_year | summary       │
│  cover_url | status (draft/published) | created/updated_at │
└──────┬──────────────┬──────────────────┬───────────────────┘
       │              │                  │
       │ book_id      │ book_id          │
       ▼              ▼                  ▼
┌──────────┐  ┌──────────────┐  ┌──────────────────┐
│ book_tags│  │    files      │  │ tags             │
│ book_id  │  │ id PK        │  │ id PK | name     │
│ tag_id   │  │ book_id FK   │  └──────────────────┘
└──────────┘  │ format       │
              │ oss_key      │
              │ size         │
              │ sha256       │
              │ uploaded_at  │
              └──────┬───────┘
                     │ file_id
                     ▼
           ┌──────────────────┐
           │ download_logs    │
           │ id PK            │
           │ user_id FK ──────┼────► users
           │ file_id FK       │     ┌────────────────────┐
           │ timestamp        │     │ id PK | username   │
           └──────────────────┘     │ password_hash(bcrypt)│
                                    │ email | role       │
                                    │ status (ACTIVE/     │
                                    │  DISABLED/BANNED)  │
                                    └────────────────────┘
```

### 3.2 表结构

**users** — 用户
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| username | VARCHAR(30) UNIQUE | |
| password_hash | VARCHAR(128) | bcrypt |
| email | VARCHAR(100) | |
| role | VARCHAR(10) | admin / user |
| status | VARCHAR(10) | ACTIVE / DISABLED / BANNED |
| created_at | DATETIME | |

**categories** — 中图法分类（自引用树）
| 字段 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR(10) PK | 例: "A81" |
| name | VARCHAR(100) | |
| parent_code | VARCHAR(10) FK→categories.code | NULL=顶层 |

**authors** — 作者
| 字段 | 类型 |
|------|------|
| id | INTEGER PK |
| name | VARCHAR(50) |
| bio | TEXT |

**publishers** — 出版社
| 字段 | 类型 |
|------|------|
| id | INTEGER PK |
| name | VARCHAR(100) |
| address | VARCHAR(100) |

**tags** — 标签 (与 books 多对多)
| 字段 | 类型 |
|------|------|
| id | INTEGER PK |
| name | VARCHAR(50) UNIQUE |

**books** — 图书
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| title | TEXT NOT NULL | |
| author_id | INTEGER FK | |
| publisher_id | INTEGER FK | |
| isbn | VARCHAR(20) | |
| edition | VARCHAR(20) | |
| pub_year | INTEGER | |
| category_code | VARCHAR(10) FK | |
| summary | TEXT | |
| cover_url | TEXT | |
| status | VARCHAR(10) | draft / published |
| created_at | DATETIME | |
| updated_at | DATETIME | auto-update |

**book_tags** — 图书-标签关联表
| 字段 | 类型 |
|------|------|
| book_id | INTEGER FK (CASCADE) |
| tag_id | INTEGER FK (CASCADE) |

**files** — 资源文件
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| book_id | INTEGER FK (CASCADE) | |
| format | VARCHAR(10) | PDF/EPUB/MOBI/TXT/AZW3 |
| oss_key | VARCHAR(256) | OSS 或本地路径 |
| size | INTEGER | 字节数 |
| sha256 | CHAR(64) | |
| uploaded_at | DATETIME | |

**download_logs** — 下载记录
| 字段 | 类型 |
|------|------|
| id | INTEGER PK |
| user_id | INTEGER FK |
| file_id | INTEGER FK |
| timestamp | DATETIME |

---

## 4. API 参考

Base URL: `http://localhost:8000`

### 4.1 认证

所有管理接口需 `Authorization: Bearer <JWT>`。

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/token` | 登录，返回 JWT | 无 |
| GET | `/api/me` | 当前用户信息 | JWT |

### 4.2 图书

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/books?status=published` | 图书列表 | 无 |
| GET | `/api/books/{id}` | 图书详情 | 无 |
| POST | `/api/books` | 创建图书 | admin |
| PUT | `/api/books/{id}` | 更新图书 | admin |
| DELETE | `/api/books/{id}` | 删除图书 | admin |
| POST | `/api/books/batch` | **JSON 批量导入** | admin |

### 4.3 下载

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/download/{book_id}?format=pdf` | 302 重定向到下载 URL | JWT |

点击静态页面的下载按钮 → 跳转 `/login?redirect=/api/download/...` → 登录后自动下载。

### 4.4 上传

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/upload-url` | 生成上传 URL（本地或 OSS 预签名） | admin |
| POST | `/api/upload-file` | 本地模式直接上传 | admin |
| POST | `/api/files` | 记录 OSS 上传完成 | admin |

### 4.5 用户管理

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/users` | 用户列表 | admin |
| POST | `/api/users` | 创建用户 | admin |
| PUT | `/api/users/{id}/role` | 改角色/状态 | admin |
| PUT | `/api/users/{id}/ban` | 封禁用户 | admin |

### 4.6 元数据管理

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET/POST | `/api/authors` | 作者列表/创建 | admin(写) |
| GET/POST | `/api/publishers` | 出版社列表/创建 | admin(写) |
| GET/POST | `/api/categories` | 分类列表/创建 | admin(写) |
| GET/POST | `/api/tags` | 标签列表/创建 | admin(写) |

### 4.7 统计与运维

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/api/stats/summary` | 总/日/周/月下载数、活跃用户 | 无 |
| GET | `/api/stats/logs?limit=50` | 下载日志 | 无 |
| POST | `/admin/rebuild` | 触发 SSG 重建 | admin |
| GET | `/api/health` | 健康检查 | 无 |

### 4.8 JSON 批量导入格式

```json
[
  {
    "action": "create",
    "title": "论语",                          // 必填
    "author": "孔子",                         // 按名查找，不存在则自动创建
    "publisher": "中华书局",                   // 同上
    "isbn": "9787101000001",
    "edition": "第1版",
    "pub_year": 2022,
    "category_code": "B2",
    "summary": "儒家经典",
    "tags": ["哲学", "经典"],                 // 同上
    "status": "published"
  },
  {
    "action": "update",
    "id": 1,
    "summary": "更新后的简介"                  // 只写要改的字段
  },
  {
    "action": "delete",
    "id": 5
  }
]
```

返回值：`{"created": N, "updated": N, "deleted": N, "errors": [...]}`

---

## 5. 存储抽象层 (OSS 对接)

位于 `app/auth.py` 底部。通过四个环境变量控制模式：

```python
OSS_ENDPOINT       # 例: https://oss-cn-hongkong.aliyuncs.com
OSS_ACCESS_KEY_ID
OSS_ACCESS_KEY_SECRET
OSS_BUCKET_NAME
```

- **全设** → OSS 模式，生成预签名 URL（上传 PUT / 下载 GET）
- **缺一** → 本地模式，文件存 `data/files/`，FastAPI 直接 serve

| 操作 | 本地模式 | OSS 模式 |
|------|----------|----------|
| 上传 | POST /api/upload-file → 存本地磁盘 | 浏览器直传 OSS（预签名 PUT） |
| 下载 | /static-files/{oss_key} | OSS 预签名 GET URL（302 重定向） |
| 流量 | 经 VPS | 不经过 VPS |

OSS 预签名下载 URL 有效期 300 秒，不可长期分享。部署时只需在 `docker-compose.yml` 或 `.env` 中配置上述四个变量，代码零改动。

---

## 6. 管理后台

URL：`/admin` → 自动跳转 `/admin/login`

默认管理员：`admin` / `admin123`

功能页面：

| 页面 | 功能 |
|------|------|
| 仪表盘 | 图书数/用户数/今日下载/最近下载 |
| 图书管理 | 增删改查 + 单文件上传 + JSON 批量导入 + 发布站点按钮 |
| 用户管理 | 列表/新增/封禁/解封/角色切换 |
| 分类管理 | 作者/出版社/标签/分类 的新增 |
| 统计 | 总/日/周/月下载量 + 下载日志 |

鉴权方式：服务端渲染页面，客户端 JS 读 `localStorage.admin_token` 后调用 API，401 时自动跳转登录页。

---

## 7. 用户端站点

URL：`/` → 静态首页

| 功能 | 实现 |
|------|------|
| 首页 | 中图法分类卡片 + 最新 20 本书 |
| 分类页 | `/category/{code}.html` |
| 作者页 | `/author/{name}.html` |
| 出版社页 | `/publisher/{name}.html` |
| 标签页 | `/tag/{name}.html` |
| 图书详情 | `/book/{id}.html`（含下载按钮） |
| 搜索 | 不内置，依赖浏览器 Ctrl+F 或 `site:域名 关键词` |
| SEO | sitemap.xml、robots.txt、RSS、语义化 HTML |
| 登录入口 | 页面右上角 "🔑 登录" → `/login` |

下载流程：点击下载 → `/login?redirect=/api/download/{id}` → 登录 → 302 重定向到文件。

---

## 8. 部署

### 8.1 本地开发

```bash
cd C:\Users\Lucian\personal-library

# 安装
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 初始化
.venv\Scripts\python seed_data.py
.venv\Scripts\python -m static_site.generator

# 启动（单端口同时服务 API + 静态站 + 管理后台）
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问：`http://localhost:8000`（用户端）、`/admin`（管理后台）、`/docs`（Swagger）

### 8.2 Docker 部署

```bash
# 修改 docker-compose.yml 中的环境变量
# SITE_URL, SECRET_KEY, ADMIN_PASSWORD, OSS_*

scp -r personal-library/ root@VPS:/home/deploy/
cd /home/deploy/personal-library
docker-compose up -d
```

容器内自动完成：pip install → 种子数据 → SSG 构建 → uvicorn 启动。

### 8.3 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接串 | `sqlite:///./data/library.db` |
| `SECRET_KEY` | JWT 签名密钥 | **生产必改** |
| `ADMIN_USERNAME` | 初始管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 初始管理员密码 | `admin123` |
| `SITE_URL` | 站点完整 URL | `https://library.example.com` |
| `STORAGE_DIR` | 本地文件目录 | `./data/files` |
| `OSS_ENDPOINT` | OSS endpoint | — |
| `OSS_ACCESS_KEY_ID` | OSS AccessKey | — |
| `OSS_ACCESS_KEY_SECRET` | OSS Secret | — |
| `OSS_BUCKET_NAME` | OSS Bucket | — |

---

## 9. 依赖

```
fastapi==0.139.0       uvicorn==0.51.0        sqlalchemy==2.0.51
jinja2==3.1.6          python-jose==3.5.0     bcrypt==5.0.0
python-multipart==0.0.32  pydantic==2.13.4    aiosqlite==0.22.1
oss2==2.19.1           httpx==0.28.1          email-validator==2.3.0
```

---

## 10. 当前种子数据

| 表 | 记录数 |
|----|--------|
| categories | 52（中图法 A-Z 完整简表） |
| authors | 8（马克思、恩格斯、毛泽东、鲁迅、钱钟书、费孝通、孔子、老子） |
| publishers | 5（人民、商务、中华、三联、人民文学） |
| tags | 8（马克思主义、哲学、经济学、经典 等） |
| books | 10（7 原有 + 2 批量导入 + 1 验证） |
| users | 4（admin、alice、bob、charlie） |
