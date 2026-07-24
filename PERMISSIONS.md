# 个人图书馆 — 后台管理权限明细

> 版本：v1.0  
> 项目路径：`C:\Users\Lucian\personal-library`  
> 权限模型：RBAC（Role-Based Access Control），角色 → 权限 → API 端点

---

## 一、权限总表（共 39 项）

### 📖 图书管理 book.*（8 项）

| 权限码 | 对应操作 | 影响的 API 端点 |
|--------|---------|----------------|
| `book.read` | 查看图书列表 | `GET /api/books`, `GET /api/books/datagrid` |
| `book.create` | 新增图书 | `POST /api/books` |
| `book.update` | 编辑图书 | `PUT /api/books/{id}` |
| `book.delete` | 删除图书 | `DELETE /api/books/{id}` |
| `book.import` | JSON 批量导入 | `POST /api/books/batch` |
| `book.export` | CSV 导出 | `GET /api/books/export/csv` |
| `book.batch_update` | 批量修改 | `PUT /api/books/batch` |
| `book.publish` | 发布图书并触发 SSG 重建 | `POST /admin/rebuild` |

---

### 👥 用户管理 user.*（7 项）

| 权限码 | 对应操作 | 影响的 API 端点 |
|--------|---------|----------------|
| `user.read` | 查看用户列表 | `GET /api/users`, `GET /api/me/permissions` |
| `user.create` | 创建用户 | `POST /api/users` |
| `user.update` | 编辑用户信息 | `PUT /api/users/{id}` |
| `user.delete` | 删除用户 | `DELETE /api/users/{id}` |
| `user.disable` | 封禁 / 解封用户 | `PUT /api/users/{id}/ban` |
| `user.reset_password` | 重置用户密码    | `PUT /api/users/{id}/reset-password`        |

### 🎫 邀请码 invite.*（4 项）

| 权限码 | 对应操作 | 影响的 API 端点 |
|--------|---------|----------------|
| `invite.read` | 查看邀请码列表 | `GET /api/invite-codes` |
| `invite.create` | 生成邀请码 | `POST /api/invite-codes` |
| `invite.delete` | 删除邀请码 | `DELETE /api/invite-codes/{id}` |
| `invite.expire` | 作废邀请码 | `POST /api/invite-codes/{id}/expire` |

---

### 🗄 资源管理 asset.*（4 项）

| 权限码 | 对应操作 | 影响的 API 端点 |
|--------|---------|----------------|
| `asset.read` | 查看资源库列表 | `GET /api/assets/datagrid`, `GET /api/assets/{id}` |
| `asset.upload` | 上传文件 | `POST /api/assets/upload` |
| `asset.delete` | 删除资源 | `DELETE /api/assets/{id}` |
| `asset.view_refs` | 查看资源引用关系 | `GET /api/assets/{id}/refs` |

---

### 📰 文章管理 article.*（4 项）

| 权限码 | 对应操作 | 影响的 API 端点 |
|--------|---------|----------------|
| `article.read` | 查看文章列表和详情 | `GET /api/articles`, `GET /api/articles/{id}` |
| `article.create` | 创建 / 编辑文章 | `POST /api/articles`, `PUT /api/articles/{id}` |
| `article.delete` | 删除文章 | `DELETE /api/articles/{id}` |
| `article.publish` | 发布文章并生成静态 HTML | `POST /api/articles/{id}/publish` |

---

### 🏷 元数据管理 catalog.*（4 项）

| 权限码 | 对应操作 | 影响的 API 端点 |
|--------|---------|----------------|
| `catalog.read` | 查看分类 / 作者 / 出版社 / 标签 | `GET /api/categories`, `GET /api/authors`, `GET /api/publishers`, `GET /api/tags` |
| `catalog.create` | 新增分类 / 作者 / 出版社 / 标签 | `POST /api/categories`, `POST /api/authors`, `POST /api/publishers`, `POST /api/tags` |
| `catalog.update` | 编辑 | `PUT /api/categories/{id}`, `PUT /api/authors/{id}`, `PUT /api/publishers/{id}`, `PUT /api/tags/{id}` |
| `catalog.delete` | 删除 | `DELETE /api/categories/{id}`, `DELETE /api/authors/{id}`, `DELETE /api/publishers/{id}`, `DELETE /api/tags/{id}` |

---

### 🔐 权限管理 role.*（4 项）

| 权限码 | 对应操作 | 影响的 API 端点 |
|--------|---------|----------------|
| `role.read` | 查看角色和权限列表 | `GET /api/admin/rbac/roles`, `GET /api/admin/rbac/permissions` |
| `role.create` | 创建 / 编辑角色 | `POST /api/admin/rbac/roles`, `PUT /api/admin/rbac/roles/{id}` |
| `role.delete` | 删除角色 | `DELETE /api/admin/rbac/roles/{id}` |
| `role.assign_permission` | 分配权限给角色 | `PUT /api/admin/rbac/roles/{id}/permissions` |

---

### 📈 日志与统计 audit.*（3 项）

| 权限码 | 对应操作 | 影响的 API 端点 |
|--------|---------|----------------|
| `audit.read` | 查看操作日志 | `GET /api/stats/logs` |
| `audit.download_log` | 查看下载记录 | `GET /api/stats/downloads` |
| `audit.page_view` | 查看页面访问统计 | `GET /api/stats/page-views` |

---

### ⚙ 系统配置 system.*（1 项）

| 权限码 | 对应操作 | 影响的 API 端点 |
|--------|---------|----------------|
| `system.config` | 查看仪表盘统计数据 | `GET /api/stats/summary` |

---

## 二、角色权限分配矩阵

| 权限 | Super Admin | Library Admin | Account Admin | Member |
|------|:--:|:--:|:--:|:--:|
| `book.read` | ✅ | ✅ | | ✅ |
| `book.create` | ✅ | ✅ | | |
| `book.update` | ✅ | ✅ | | |
| `book.delete` | ✅ | ✅ | | |
| `book.import` | ✅ | ✅ | | |
| `book.export` | ✅ | ✅ | | |
| `book.batch_update` | ✅ | ✅ | | |
| `book.publish` | ✅ | ✅ | | |
| `user.read` | ✅ | | ✅ | |
| `user.create` | ✅ | | ✅ | |
| `user.update` | ✅ | | ✅ | |
| `user.delete` | ✅ | | ✅ | |
| `user.disable` | ✅ | | ✅ | |
| `user.assign_role` | ✅ | | | |
| `user.reset_password` | ✅ | | ✅ | |
| `invite.read` | ✅ | | ✅ | |
| `invite.create` | ✅ | | ✅ | |
| `invite.delete` | ✅ | | ✅ | |
| `invite.expire` | ✅ | | ✅ | |
| `asset.read` | ✅ | ✅ | | |
| `asset.upload` | ✅ | ✅ | | |
| `asset.delete` | ✅ | ✅ | | |
| `asset.view_refs` | ✅ | ✅ | | |
| `article.read` | ✅ | ✅ | | ✅ |
| `article.create` | ✅ | ✅ | | |
| `article.delete` | ✅ | ✅ | | |
| `article.publish` | ✅ | ✅ | | |
| `catalog.read` | ✅ | ✅ | | |
| `catalog.create` | ✅ | ✅ | | |
| `catalog.update` | ✅ | ✅ | | |
| `catalog.delete` | ✅ | ✅ | | |
| `role.read` | ✅ | | | |
| `role.create` | ✅ | | | |
| `role.delete` | ✅ | | | |
| `role.assign_permission` | ✅ | | | |
| `audit.read` | ✅ | | | |
| `audit.download_log` | ✅ | | | |
| `audit.page_view` | ✅ | | | |
| `system.config` | ✅ | | | |

---

## 三、角色职责说明

| 角色 | 说明 | 权限数 |
|------|------|--------|
| **Super Admin** | 超级管理员，拥有全部权限 | 39 |
| **Library Admin** | 图书管理员，管理图书、文章、资源和元数据 | 21 |
| **Account Admin** | 账号管理员，管理用户和邀请码 | 12 |
| **Member** | 普通注册用户，只能浏览和下载 | 2 |

---

## 四、权限校验流程

```
用户请求 → 解析 Cookie JWT → 获取用户 → 查用户角色 → 查角色权限
                                                              ↓
                                                    require_permission(code)
                                                              ↓
                                                    权限列表中包含该 code？
                                                       ↓           ↓
                                                      ✅ 放行     ❌ 403
```
