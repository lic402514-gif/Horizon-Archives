# 产品需求文档（PRD）3.0

# 后台资源管理系统（Asset Management）与图书资源上传模块

---

# 一、项目背景

目前后台已经具备图书元数据（Book）管理能力，包括：

- 图书信息录入
- 图书编辑
- 图书删除
- 标签管理
- 中图法分类
- 搜索与筛选

但系统尚未实现电子书文件（EPUB、PDF 等）及封面图片等数字资源的统一管理。

随着系统逐步扩展，仅依靠 Book 数据表维护 OSS 信息存在以下问题：

- 图书元数据与文件资源高度耦合；
- OSS 文件无法统一管理；
- 无法统计资源引用情况；
- 无法清理未关联资源；
- 不利于后续扩展文章图片、OCR 文件、缩略图等资源。

因此，需要建立独立的 **资源管理（Asset）** 模块，实现数字资源生命周期管理。

---

# 二、总体设计目标

将整个系统划分为三个独立模块：

```
Book
（图书元数据）

↓

Asset Mapping
（资源映射）

↓

Asset
（OSS资源）
```

遵循：

> **数据库管理资源关系，OSS负责存储文件，Book只负责元数据。**

Book 页面不得直接管理 OSS。

所有资源统一由 Asset 模块维护。

---

# 三、需要开发的后台页面

本次新增两个独立后台页面。

---

# 页面一

## 图书资源上传（Book Upload）

建议地址：

```
/admin/book-upload
```

职责：

> 用于上传电子书、封面，并建立与图书卡(Book)之间的映射关系。

该页面负责：

- 上传电子书
- 上传封面
- 创建图书卡
- 建立资源映射

不负责：

- OSS资源维护
- OSS清理
- 文件统计

---

## 页面布局

建议采用：

```
左侧：

图书元数据

右侧：

资源上传
```

例如：

```
────────────────────────────────────

书名

作者

出版社

ISBN

分类

标签

摘要

────────────────────────────────────

上传封面

[选择图片]

上传电子书

[选择EPUB/PDF]

备注

──────────────

保存

────────────────────────────────────
```

---

## 上传流程

管理员：

```
上传封面
```

↓

上传：

```
OSS
```

↓

生成：

```
Asset.id
```

↓

继续：

```
上传电子书
```

↓

OSS

↓

生成：

```
Asset.id
```

↓

创建：

```
Book
```

↓

建立：

```
BookAsset
```

映射关系。

---

## 保存后数据库关系

```
Book

↓

BookAsset

↓

Asset

↓

OSS
```

例如：

```
Book

资本论
```

↓

```
BookAsset

cover

↓

Asset 25
```

↓

```
BookAsset

ebook

↓

Asset 26
```

---

# 页面二

## Asset（OSS资源管理）

建议地址：

```
/admin/assets
```

该页面用于统一管理：

- 图书文件
- 封面
- 文章图片
- OCR文件
- 缩略图
- HTML附件
- 其它OSS资源

所有数字资源均在该页面维护。

---

## 页面风格

页面风格保持与：

```
http://localhost:8000/admin/books
```

完全一致。

包括：

- Toolbar
- 搜索
- Grid
- 编辑弹窗
- 筛选
- 批量操作
- 分页
- 导入导出

保持统一后台风格。

---

## Grid建议显示字段

| 字段     | 说明                           |
| -------- | ------------------------------ |
| ID       | Asset唯一编号                  |
| 缩略图   | 图片预览（非图片显示文件图标） |
| 文件名   | 原始文件名                     |
| 类型     | 资源类型                       |
| 扩展名   | pdf、epub、webp 等             |
| 文件大小 | 自动计算                       |
| 备注     | 管理用途说明                   |
| 上传时间 | 上传日期                       |
| 上传者   | 创建用户                       |
| 引用次数 | 被引用数量                     |
| 当前状态 | 正常 / 未关联 / 已删除         |

默认不显示：

- Object Key
- Bucket
- Region
- MD5
- SHA256

详情窗口可查看。

---

## Toolbar功能

支持：

```
搜索

上传资源

批量删除

批量导出

刷新

筛选

资源类型过滤

状态过滤
```

支持：

```
正常资源

↓

封面

↓

图书

↓

文章图片

↓

OCR

↓

其它
```

快速筛选。

---

## 编辑窗口

允许修改：

```
文件名

备注

资源类型

状态
```

不允许直接修改：

```
Object Key

Bucket

MD5

SHA256
```

如需修改资源内容，应重新上传。

---

## 删除逻辑

采用：

```
逻辑删除
```

Asset：

```
status

↓

deleted
```

OSS文件根据后台策略：

可立即删除；

或：

进入回收站。

---

## 引用关系查看

点击：

```
查看引用
```

可查看：

```
当前资源

↓

被哪些Book使用

↓

被哪些Article使用
```

方便确认是否可以删除。

---

# 四、数据库设计

新增独立数据表：

```
asset
```

---

## Asset表

建议字段：

| 字段        | 类型     | 说明           |
| ----------- | -------- | -------------- |
| id          | BIGINT   | 主键           |
| filename    | VARCHAR  | 原始文件名     |
| extension   | VARCHAR  | 扩展名         |
| mime_type   | VARCHAR  | MIME类型       |
| size        | BIGINT   | 文件大小(Byte) |
| md5         | VARCHAR  | MD5            |
| sha256      | VARCHAR  | SHA256（可选） |
| provider    | VARCHAR  | OSS提供商      |
| bucket      | VARCHAR  | Bucket         |
| object_key  | VARCHAR  | OSS对象路径    |
| asset_type  | VARCHAR  | 资源类型       |
| remark      | TEXT     | 管理员备注     |
| upload_by   | BIGINT   | 上传用户       |
| upload_time | DATETIME | 上传时间       |
| update_time | DATETIME | 更新时间       |
| status      | VARCHAR  | 当前状态       |

---

## Asset Type

建议枚举：

```
book

cover

article_image

thumbnail

preview

ocr

attachment

other
```

便于统一管理。

---

## BookAsset表

新增：

```
book_asset
```

用于维护：

```
Book

↓

Asset
```

关系。

字段：

| 字段          | 说明     |
| ------------- | -------- |
| id            | 主键     |
| book_id       | 图书ID   |
| asset_id      | Asset ID |
| relation_type | 关系类型 |

其中：

```
relation_type
```

建议：

```
cover

ebook

pdf

mobi

preview

thumbnail
```

后续无需修改数据库即可扩展。

---

# 五、前端展示要求

Books 页面：

禁止展示：

- Asset ID
- Bucket
- Object Key
- OSS路径
- MD5
- SHA256

图书卡仅显示：

- 封面
- 书名
- 作者
- ISBN
- 分类
- 标签
- 简介

封面通过：

```
BookAsset

↓

Asset

↓

OSS URL
```

自动解析。

下载按钮同理。

所有 OSS 内部信息均不暴露给管理员日常操作界面。

---

# 六、系统实现流程

资源上传：

```
上传文件

↓

后端

↓

上传OSS

↓

返回Object Key

↓

写入Asset表

↓

生成Asset.id
```

建立图书：

```
创建Book

↓

选择Asset

↓

写入BookAsset

↓

建立映射
```

前端展示：

```
Book

↓

BookAsset

↓

Asset

↓

OSS URL

↓

HTML页面
```

下载：

```
Book

↓

BookAsset

↓

Asset

↓

后端生成访问地址

↓

浏览器直接访问OSS
```

整个过程中：

前端不保存OSS路径。

OSS相关信息仅存在：

```
Asset
```

数据表中。

---

# 七、后续扩展能力

本设计应兼容未来新增资源类型，例如：

- Markdown文章配图
- 网站公告附件
- OCR文本
- AI摘要缓存
- HTML静态资源
- EPUB预览页
- PDF预览图
- 用户头像
- Banner图片

新增资源无需修改 Book 表，仅需新增 Asset 类型及映射关系即可。

---

# 八、设计原则

1. **资源与元数据完全解耦。**
2. **Book 不直接管理 OSS 信息。**
3. **Asset 统一管理所有数字资源。**
4. **通过映射表建立 Book 与 Asset 的关联。**
5. **OSS 内部信息仅后台维护，不在图书管理页面直接展示。**
6. **后台页面风格统一，与现有 `/admin/books` 保持一致。**
7. **为未来文章系统、知识库系统及其他资源类型预留扩展能力。**