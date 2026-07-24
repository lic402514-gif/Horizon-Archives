# 产品需求文档（PRD）

# 权限管理系统（RBAC，Role-Based Access Control）

---

## 一、需求背景

随着网站功能逐步完善，后台管理将不再仅由单一管理员负责，而可能涉及多个具有不同职责的管理人员。

为了提高系统安全性、降低误操作风险，并便于后续功能扩展，需要引入 **RBAC（Role-Based Access Control，基于角色的权限控制）** 模型，对后台各项功能进行细粒度权限管理。

系统应避免采用传统的"管理员 / 普通用户"二元权限模型，而应支持多个角色以及可扩展的权限体系。

---

# 二、设计目标

实现：

- 多角色管理
- 多权限管理
- 权限可扩展
- 后端统一权限校验
- 操作日志可追溯
- 不向任何后台用户暴露 OSS 凭据

所有涉及数据修改、删除、上传、封禁等敏感操作，均必须经过后端权限验证。

---

# 三、角色设计（Role）

系统默认提供以下角色。

---

## 1、Super Admin（超级管理员）

系统最高权限。

拥有全部权限，包括但不限于：

### 用户管理

- 创建用户
- 删除用户
- 修改用户信息
- 封禁用户
- 解封用户
- 重置密码
- 修改用户角色

### 图书管理

- 新增图书
- 编辑图书
- 删除图书
- 批量导入
- 批量导出
- 修改元数据

### OSS 管理

- 上传文件
- 删除文件
- 更新文件
- 查看 OSS 使用情况

### 系统管理

- 系统配置
- 查看日志
- 权限配置
- 创建角色
- 删除角色
- 分配权限

一般情况下，仅允许存在极少数账号拥有该权限。

---

## 2、Library Admin（图书管理员）

负责图书资源维护。

拥有：

- 浏览全部图书
- 新增图书
- 编辑图书元数据
- 删除图书
- 上传 EPUB
- 上传 PDF
- 上传 Cover
- 上传 OCR 文件
- 上传附件
- 批量 JSON 导入
- 批量 CSV 导入
- CSV 导出
- 标签管理
- 分类管理

不允许：

- 创建用户
- 删除用户
- 封禁用户
- 修改用户权限
- 修改系统配置

---

## 3、Account Admin（账号管理员）

负责用户管理。

拥有：

- 查看用户
- 创建账号
- 编辑账号
- 删除账号
- 封禁账号
- 启用账号
- 重置密码
- 修改昵称
- 修改邮箱
- 分配普通角色

不允许：

- 编辑图书
- 删除图书
- 修改元数据
- 上传图书
- 删除 OSS 文件
- 修改系统配置

---

## 4、Auditor（审核员，可选）

用于未来支持用户投稿或共享资源。

拥有：

- 查看待审核资源
- 审核图书
- 发布图书
- 驳回图书
- 查看审核历史

不允许：

- 删除用户
- 删除 OSS 文件
- 修改系统配置

---

## 5、Member（普通会员）

拥有：

- 登录
- 浏览图书
- 搜索图书
- 收藏图书
- 下载图书
- 修改个人资料

不允许进入后台。

---

## 6、Guest（游客，可选）

拥有：

- 浏览公开图书目录
- 查看公开元数据

不可下载图书。

---

# 四、权限设计（Permission）

权限应采用"资源 + 动作"命名方式。

例如：

```
book.read
book.create
book.update
book.delete

book.import
book.export

book.batch_update

book.manage_metadata

user.read
user.create
user.update
user.delete

user.disable
user.enable

user.reset_password

oss.upload
oss.delete
oss.read

system.config

system.log.read

role.create
role.update
role.delete

permission.assign
```

系统应支持后续新增权限，而无需修改权限模型。

---

# 五、数据库设计

建议采用 RBAC 标准结构。

## User

```
id
username
email
password_hash
status
created_at
```

---

## Role

```
id
name
description
```

例如：

```
Super Admin

Library Admin

Account Admin

Member
```

---

## Permission

```
id
code
description
```

例如：

```
book.read

book.create

book.delete

user.disable
```

---

## UserRole

```
user_id

role_id
```

一个用户可拥有多个角色。

---

## RolePermission

```
role_id

permission_id
```

一个角色拥有多个权限。

---

# 六、权限校验

所有后台接口均必须进行权限验证。

例如：

```
POST /api/books
```

验证：

```
book.create
```

若无权限：

返回：

```
403 Forbidden
```

---

例如：

```
DELETE /api/books/{id}
```

验证：

```
book.delete
```

---

例如：

```
POST /api/users/{id}/ban
```

验证：

```
user.disable
```

---

禁止仅依据角色名称进行判断，例如：

```
❌

if user.role == "admin"
```

应统一采用权限判断：

```
✅

user.has_permission("book.delete")
```

提高系统扩展性。

---

# 七、OSS 权限管理

后台用户不得直接拥有 OSS AccessKey。

所有 OSS 操作均通过后端完成。

流程：

```
管理员

↓

FastAPI

↓

权限验证

↓

OSS SDK

↓

阿里云 OSS
```

例如：

```
Library Admin

↓

上传 EPUB

↓

POST /api/books/upload

↓

FastAPI

↓

book.create

↓

oss.upload

↓

上传 OSS
```

删除同理：

```
DELETE /api/books/{id}

↓

book.delete

↓

删除数据库记录

↓

删除 OSS Object
```

OSS 凭据始终保存在服务器端。

---

# 八、后台页面权限

不同角色仅显示其有权限访问的菜单。

例如：

Library Admin：

```
图书管理

分类管理

标签管理
```

不会显示：

```
用户管理

系统设置

权限管理
```

---

Account Admin：

```
用户管理

角色管理
```

不会显示：

```
图书管理
```

---

Member：

不显示后台入口。

---

# 九、操作日志（Operation Log）

所有重要操作必须记录日志。

记录内容包括：

```
操作时间

操作用户

用户 IP

操作对象

操作类型

操作结果

详细内容
```

例如：

```
2026-07-11

Lucian

新增图书

《资本论》
```

```
2026-07-11

Library Admin

修改 ISBN
```

```
2026-07-11

Account Admin

封禁用户

user123
```

日志支持：

- 查询
- 筛选
- 导出
- 按时间排序

---

# 十、安全要求

系统应满足：

- 所有后台接口必须验证 JWT 身份认证。
- 所有后台接口必须验证 RBAC 权限。
- 所有敏感操作必须记录操作日志。
- 所有文件操作必须通过后端代理完成。
- 不允许任何用户获取 OSS AccessKey 或 Secret。
- 删除图书时，应同步删除数据库记录及对应 OSS Object。
- 支持未来扩展更细粒度权限，而无需修改数据库结构。

---

# 十一、未来扩展

后续可新增：

- Metadata Editor（元数据编辑员）
- OCR Operator（OCR 管理员）
- Translator（翻译管理员）
- Reviewer（资源审核员）
- API Token 权限
- OAuth 第三方权限映射
- 基于部门或用户组的权限控制
- 数据级权限（例如仅允许管理自己创建的图书）
- 权限继承（Role Hierarchy）
- 临时授权（Temporary Permission）

---

# 十二、总体目标

构建一套具备企业级可扩展性的后台权限管理系统，实现：

- 基于角色（Role）的权限管理
- 基于权限（Permission）的接口控制
- 前后端统一权限体系
- 高安全性
- 高可维护性
- 高可扩展性

该系统应能够满足数字图书馆、知识库及资源管理平台长期演进需求，并为未来多管理员协作提供稳定、安全的权限基础。