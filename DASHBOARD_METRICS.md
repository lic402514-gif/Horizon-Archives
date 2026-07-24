# 仪表盘统计指标清单

> 页面：`/admin` → 仪表盘  
> 数据源：`GET /api/stats/summary` + `GET /api/stats/page-views` + `GET /api/books` + `GET /api/users`

---

## 一、统计卡片（最上方网格）

| 序号 | 指标 | 数据来源 | 计算方式与内涵 |
|------|------|---------|---------------|
| 1 | **图书总数** | `GET /api/books` → `length` | `books` 表中所有记录的数量，包含已发布和草稿 |
| 2 | **已发布** | `GET /api/books` → 过滤 `status='published'` | `books` 表中 `status = 'published'` 的数量。已发布的图书会出现在静态站点中 |
| 3 | **草稿** | 图书总数 - 已发布 | `books` 表中 `status ≠ 'published'` 的数量。草稿不对外显示，管理员可见 |
| 4 | **用户数** | `GET /api/users` → `length` | `users` 表中所有用户的数量（含封禁用户） |
| 5 | **今日下载** | `/api/stats/summary` → `today_downloads` | `download_logs` 表中今日 0 点至今的下载次数。每次用户点击下载按钮生成一条记录 |
| 6 | **总下载** | `/api/stats/summary` → `total_downloads` | `download_logs` 表中全部历史记录总数 |
| 7 | **今日访问人数** | `/api/stats/page-views` → `today_ips` | 今日有访问的所有独立 IP 数量。通过页面浏览追踪（`page_views` 表）统计，含与昨日对比的差异值(+N / -N) |
| 8 | **昨日访问人数** | `/api/stats/page-views` → `yesterday_ips` | 昨日独立 IP 数量，用于和今日做对比 |
| 9 | **总访问人数** | `/api/stats/page-views` → `total_ips` | 有史以来所有独立 IP 总数 |
| 10 | **总浏览** | `/api/stats/page-views` → `total_views` | 累积页面浏览总次数（同一 IP 多次访问计数多次） |

---

## 二、最近下载表格（卡片下方）

| 列名 | 数据来源 | 内涵 |
|------|---------|------|
| 用户 | `download_logs` JOIN `users` → `username` | 触发下载的用户的用户名。匿名下载则显示 `-` |
| 书籍 | `download_logs` JOIN `files` JOIN `books` → `title` | 被下载的图书书名 |
| 格式 | `download_logs` JOIN `files` → `format` | 下载文件的格式（如 PDF、EPUB） |
| 时间 | `download_logs` → `timestamp` | 下载发生的精确时间 |

最多展示最近 10 条记录。

---

## 三、后备统计（后端提供，当前未在前端展示）

| 指标 | API 字段 | 内涵 |
|------|---------|------|
| 近 7 天下载 | `stats_summary` → `week_downloads` | 过去 7 天的下载次数 |
| 近 30 天下载 | `stats_summary` → `month_downloads` | 过去 30 天的下载次数 |
| 活跃用户 | `stats_summary` → `active_users` | 近 30 天有过下载行为的独立用户数 |

---

## 四、数据模型依赖

```
仪表盘卡片
├── books 表          → 图书总数 / 已发布 / 草稿
├── users 表          → 用户数
├── download_logs 表  → 今日下载 / 总下载 / 最近下载列表
└── page_views 表     → 今日/昨日/总访问 IP + 总浏览
```
