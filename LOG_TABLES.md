# 日志相关数据库表结构

> 项目：个人图书馆资源小站  
> 模型文件：`app/models.py`

项目包含 **3 张独立的日志表**：

---

## 一、下载日志 download_logs

**模型：** `DownloadLog` | **表名：** `download_logs`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER (PK) | 主键 |
| `user_id` | INTEGER (FK → users.id) | 触发下载的用户 ID（可空） |
| `file_id` | INTEGER (FK → files.id) | 被下载的文件 ID（旧 files 表） |
| `timestamp` | DATETIME | 下载发生的精确时间 |

**写入时机：** 用户点击下载 → `/api/download/{book_id}` → 后端生成记录

**当前状态：** ✅ 正常写入中

**应用场景：**
- 仪表盘"今日下载"和"总下载"统计
- 仪表盘"最近下载"表格
- 近 7 天 / 近 30 天下载趋势
- 活跃用户统计

---

## 二、操作日志 operation_logs

**模型：** `OperationLog` | **表名：** `operation_logs`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER (PK) | 主键 |
| `user_id` | INTEGER (FK → users.id) | 操作者用户 ID（可空） |
| `action` | VARCHAR(50) | 操作类型：create / update / delete / login / ban / publish |
| `target_type` | VARCHAR(50) | 操作目标类型：book / user / asset / article / role |
| `target_id` | VARCHAR(50) | 操作目标 ID（如 "123"） |
| `detail` | TEXT | 操作详情（如 "《资本论》"） |
| `ip_address` | VARCHAR(45) | 操作者 IP 地址 |
| `result` | VARCHAR(20) | 操作结果：success / failure |
| `timestamp` | DATETIME | 操作时间 |

**写入时机：** 管理员在后台进行增删改操作时写入

**当前状态：** ❌ 表已存在，但**尚未在任何路由中写入**。所有 CRUD 操作缺少日志记录

**待补：** 在以下操作中插入日志：
- `POST /api/books` → `action='create'`, `target_type='book'`
- `PUT /api/books/{id}` → `action='update'`
- `DELETE /api/books/{id}` → `action='delete'`
- `PUT /api/users/{id}/ban` → `action='ban'`
- `POST /api/token` → `action='login'`
- `POST /api/assets/upload` → `action='upload'`
- ... 等

---

## 三、页面浏览日志 page_views

**模型：** `PageView` | **表名：** `page_views`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER (PK) | 主键 |
| `path` | VARCHAR(500) | 被访问的页面路径（如 `/book/1.html`） |
| `ip_address` | VARCHAR(45) | 访问者 IP |
| `session_key` | VARCHAR(100) | 浏览器会话标识（localStorage 生成） |
| `user_id` | INTEGER (FK → users.id) | 已登录用户的 ID（可空） |
| `user_agent` | VARCHAR(500) | 浏览器 UA 字符串 |
| `referer` | VARCHAR(500) | 来源页面 URL |
| `view_count` | INTEGER | 该路径的访问次数（同一会话累加） |
| `first_viewed_at` | DATETIME | 该会话首次访问时间 |
| `last_viewed_at` | DATETIME | 该会话最后一次访问时间 |

**写入时机：** 访客页面加载时，前端 `trackPageView()` 调用 `POST /api/page-view`

**当前状态：** ✅ 由搭档实现，前端自动上报

**应用场景：**
- 仪表盘"今日/昨日/总访问人数"（按独立 IP 统计）
- 仪表盘"总浏览"（按 `view_count` 累加）
- 热门页面排行
- 用户访问行为分析

---

## 四、三表关系

```
page_views      download_logs       operation_logs
     │                 │                    │
     ├─ user_id ──────►│                    │
     │                 ├─ user_id ─────────►│
     │                 │                 ├─ user_id
     │                 ├─ file_id         │
     │                 │  (FK→files)     │
     │                 │                  │
     ▼                 ▼                  ▼
  users 表          users 表           users 表
```

三表都关联 `users` 表，但用途不同：
| 表 | 用途 | 写入方 |
|----|------|--------|
| `download_logs` | 下载追溯 | 后端下载端点 ✅ |
| `operation_logs` | 管理审计 | ❌ 未写入 |
| `page_views` | 访问分析 | 前端 JS 自动上报 ✅ |

---

## 五、操作日志（operation_logs）类型与内容明细

### 5.1 action 枚举

| action | 含义 | 触发场景 |
|--------|------|---------|
| `create` | 创建资源 | 新增图书、用户、角色、文章、分类等 |
| `update` | 修改资源 | 编辑图书信息、修改用户、更新文章等 |
| `delete` | 删除资源 | 删除图书、用户、文章、资产等 |
| `login` | 登录 | 管理员登录成功 / 失败 |
| `logout` | 登出 | 管理员主动退出 |
| `publish` | 发布 | 发布图书 / 文章（触发 SSG） |
| `upload` | 上传文件 | 上传电子书、封面、图片等 |
| `download` | 下载资源 | 管理员下载文件 |
| `ban` | 封禁用户 | 管理员封禁 / 解封用户 |
| `assign_role` | 分配角色 | 管理员给用户分配 / 撤销角色 |
| `reset_password` | 重置密码 | 管理员重置用户密码 |
| `assign_permission` | 分配权限 | 管理员给角色分配 / 撤销权限 |
| `rebuild` | 重建站点 | 管理员触发 SSG 全站重建 |

---

### 5.2 target_type 枚举

| target_type | 含义 | 对应的 REST 资源路径 |
|-------------|------|---------------------|
| `book` | 图书 | `/api/books/{id}` |
| `user` | 用户 | `/api/users/{id}` |
| `asset` | 数字资源 | `/api/assets/{id}` |
| `article` | 文章 | `/api/articles/{id}` |
| `role` | 角色 | `/api/roles/{id}` |
| `author` | 作者 | `/api/authors/{id}` |
| `publisher` | 出版社 | `/api/publishers/{id}` |
| `tag` | 标签 | `/api/tags/{id}` |
| `category` | 分类 | `/api/categories/{code}` |
| `system` | 系统配置 | `/api/admin/rebuild` 等 |
| `invite_code` | 邀请码 | `/api/invite-codes/{id}` |

---

### 5.3 每条日志的完整字段示例

#### 示例 1：管理员创建图书

```json
{
  "user_id": 1,
  "action": "create",
  "target_type": "book",
  "target_id": "15",
  "detail": "《大众哲学》",
  "ip_address": "192.168.1.100",
  "result": "success",
  "timestamp": "2026-07-14T22:30:00"
}
```

#### 示例 2：管理员封禁用户

```json
{
  "user_id": 1,
  "action": "ban",
  "target_type": "user",
  "target_id": "4",
  "detail": "封禁用户 charlie",
  "ip_address": "192.168.1.100",
  "result": "success",
  "timestamp": "2026-07-14T22:35:00"
}
```

#### 示例 3：Library Admin 被拒绝删除用户

```json
{
  "user_id": 2,
  "action": "delete",
  "target_type": "user",
  "target_id": "3",
  "detail": "尝试删除用户 bob — 权限不足",
  "ip_address": "10.0.0.5",
  "result": "failure",
  "timestamp": "2026-07-14T23:00:00"
}
```

---

### 5.4 触发日志的完整 API 端点清单

| API 端点 | action | target_type | detail 示例 |
|----------|--------|-------------|-------------|
| `POST /api/books` | create | book | 《{书名}》(ID:{id}) |
| `PUT /api/books/{id}` | update | book | 《{书名}》(ID:{id}) |
| `DELETE /api/books/{id}` | delete | book | 《{书名}》(ID:{id}) |
| `POST /api/books/batch` | create | book | 批量导入 {n} 本图书 |
| `POST /api/articles` | create | article | 《{标题}》(ID:{id}) |
| `PUT /api/articles/{id}` | update | article | 《{标题}》(ID:{id}) |
| `DELETE /api/articles/{id}` | delete | article | 《{标题}》(ID:{id}) |
| `POST /api/articles/{id}/publish` | publish | article | 《{标题}》(ID:{id}) |
| `POST /api/assets/upload` | upload | asset | {文件名} ({size} bytes) |
| `DELETE /api/assets/{id}` | delete | asset | {文件名} |
| `POST /api/users` | create | user | {用户名}(ID:{id}) |
| `PUT /api/users/{id}` | update | user | {用户名}(ID:{id}) |
| `DELETE /api/users/{id}` | delete | user | {用户名}(ID:{id}) |
| `PUT /api/users/{id}/ban` | ban | user | {封禁/解封}用户 {用户名} |
| `PUT /api/users/{id}/roles` | assign_role | user | 分配角色 {角色名} 给 {用户名} |
| `PUT /api/users/{id}/reset-password` | reset_password | user | 重置用户 {用户名} 密码 |
| `POST /api/authors` | create | author | {作者名}(ID:{id}) |
| `PUT /api/authors/{id}` | update | author | {作者名}(ID:{id}) |
| `DELETE /api/authors/{id}` | delete | author | {作者名}(ID:{id}) |
| `POST /api/publishers` | create | publisher | {出版社名}(ID:{id}) |
| `PUT /api/publishers/{id}` | update | publisher | {出版社名}(ID:{id}) |
| `DELETE /api/publishers/{id}` | delete | publisher | {出版社名}(ID:{id}) |
| `POST /api/tags` | create | tag | {标签名}(ID:{id}) |
| `PUT /api/tags/{id}` | update | tag | {标签名}(ID:{id}) |
| `DELETE /api/tags/{id}` | delete | tag | {标签名}(ID:{id}) |
| `POST /api/roles` | create | role | {角色名}(ID:{id}) |
| `DELETE /api/roles/{id}` | delete | role | {角色名}(ID:{id}) |
| `PUT /api/roles/{id}/permissions` | assign_permission | role | 修改角色 {角色名} 权限({n}项) |
| `POST /api/invite-codes` | create | invite_code | {邀请码}(ID:{id}) |
| `DELETE /api/invite-codes/{id}` | delete | invite_code | {邀请码}(ID:{id}) |
| `POST /api/invite-codes/{id}/expire` | update | invite_code | 作废邀请码 {邀请码} |
| `POST /api/token` | login | system | 管理员 {用户名} 登录(成功/失败) |
| `POST /admin/rebuild` | rebuild | system | 重建静态站点 |

---

### 5.5 安全审计价值

| 审计场景 | 可查询的日志条件 |
|----------|-----------------|
| 谁删了那本书？ | `action=delete, target_type=book, target_id=X` |
| 最近谁登录了？ | `action=login, result=success` |
| 谁登录失败了？ | `action=login, result=failure` |
| 谁封了哪个用户？ | `action=ban, target_type=user` |
| 某管理员今天做了什么？ | `user_id=X, timestamp>=today` |
| 哪种操作最频繁？ | `GROUP BY action ORDER BY COUNT(*) DESC` |
| 哪些操作失败了？ | `result=failure` |
| 有异常的越权操作吗？ | `result=failure, detail LIKE '%权限不足%'` |
