# 产品需求文档（PRD）4.0

# 文章发布及资源管理系统（Article CMS）与内容管理模块

------

# 一、项目背景

目前后台已具备图书及图书数字资源的管理能力，但系统在“非图书类内容”（如公告、使用教程、网站说明）的编辑、发布和展示方面仍存在空白。

目前系统尚未实现文章（Article）的富文本编辑、Markdown 支持、预览、版本管理与 SEO 友好展示等功能。

现有痛点表现为：

- 网站公告、帮助文档只能通过硬编码或简单的富文本框存储，无法与 OSS 资源解耦；
- 文章配图无法统一管理，导致 OSS 出现大量冗余垃圾文件；
- 无法批量处理文章中的图片插入与资源关联；
- 文章缺乏草稿/发布状态管理，无法支持预览；
- 生成的 HTML 页面完全依赖后端渲染，不利于搜索引擎爬虫抓取和检索。

因此，需要建立独立的 **文章管理与发布（Article CMS）** 模块，实现从图文编辑、资源管理到静态页面发布（SSG）的完整生命周期管理。

------

# 二、总体设计目标

将整个系统的内容生产划分为三个独立模块：

text

```
Article
（文章元数据）

↓

ArticleAsset
（文章资源映射）

↓

Asset
（OSS统一资源管理）
```



遵循：

> **数据库管理资源关系，OSS负责存储文件，Article表只负责文章元数据与状态控制。**

前台页面展示静态 HTML 由 **SSG（静态站点生成）** 生成，并通过 **本地缓存 + OSS云存储** 双重兜底策略保证容灾与高可用。

------

# 三、需要开发的后台页面

本次新增两个独立后台页面。

------

# 页面一

## 文章编辑与发布（Article Editor）

建议地址：

text

```
/admin/article-editor
```



职责：

> 用于编写文章正文、上传配图、录入元数据，并通过 SSG 引擎生成静态 HTML 页面。

该页面负责：

- 录入文章基本信息（标题、作者、摘要、分类等）
- 使用 Markdown 编辑内容
- 上传文章内图片
- 实时预览文章渲染效果
- 保存草稿 / 正式发布
- 触发 SSG 生成静态 HTML 并缓存

不负责：

- 直接管理 OSS 内部路径信息
- 清理未关联的冗余资源

------

## 页面布局

建议采用双栏布局，与图书上传页面保持一致：

text

```
────────────────────────────────────
左侧：元数据面板               右侧：编辑与预览区

标题                            ┌──────────────────────┐
                                │                      │
作者                            │   [编辑器]           │
                                │   (支持 Markdown)    │
分类                            │                      │
                                │   ⌜──── 预览 ────⌟  │
标签                            │   [渲染后的HTML]     │
                                │                      │
摘要                            └──────────────────────┘
(篇幅较长的摘要可加分页)

封面图上传
[选择图片]

SEO 标题
(可选)

SEO 描述
(可选)

──────────────
存草稿 / 发布
────────────────────────────────────
```



------

## 上传与发布流程

管理员进行：

text

```
在右侧 Markdown 编辑器中编写正文
```



↓

text

```
点击【插入图片】或拖拽图片至编辑器
```



↓

text

```
图片上传 OSS
（前端直传或后端代理，生成 Asset.id）
```



↓

text

```
将 OSS 图片链接注入到 Markdown 文本中
```



↓

text

```
保存草稿
```



↓

text

```
点击【发布】
```



↓

text

```
触发 SSG 引擎
（Markdown 转换为最终 HTML）
```



↓

text

```
HTML 写入本地服务端缓存
同时备份 HTML 到 OSS（容灾冗余）
```



↓

text

```
修改 Article 状态为 `published`
将 HTML 访客地址对外公开
```



------

## 保存后数据库关系

text

```
Article
（文章元数据）
↓
ArticleAsset
（文章资源映射）
↓
Asset
（OSS资源）
```



例如：

text

```
Article
《阅读器使用教程》
```



↓

text

```
ArticleAsset
cover
↓
Asset 100
```



↓

text

```
ArticleAsset
content_image_01
↓
Asset 101
```



↓

text

```
ArticleAsset
md_source
↓
Asset 102  (对应的 .md 原始文件)
```



------

# 页面二

## Asset（OSS资源管理）

建议地址：

text

```
/admin/assets
```



**该页面直接复用现有“图书数字资源管理”模块的页面。**

该页面统一管理：

- 封面图片
- 文章内联图片
- Markdown 源文件
- 缩略图
- 附件（例如图片）

**新增资源类型枚举支持：**

text

```
article_cover

article_image

markdown_source

ssg_html

article_attachment
```



页面功能和布局与图书资源模块保持完全一致（Toolbar、搜索、Grid、筛选、导出、编辑弹窗、分页等）。

------

# 四、数据库设计

新增独立数据表：

text

```
article
```



和

text

```
article_asset
```



------

## Article 表

建议字段：

| 字段                 | 类型     | 说明                         |
| :------------------- | :------- | :--------------------------- |
| id                   | BIGINT   | 主键                         |
| slug                 | VARCHAR  | 文章 URL 标识（利于 SEO）    |
| title                | VARCHAR  | 文章标题                     |
| summary              | TEXT     | 文章摘要/简介                |
| author_id            | BIGINT   | 作者 ID                      |
| cover_image_oss_url  | VARCHAR  | 封面图 OSS 链接              |
| content_md_oss_key   | VARCHAR  | Markdown 源文件在 OSS 的 Key |
| content_html_oss_key | VARCHAR  | 生成后的 HTML 在 OSS 的 Key  |
| seo_title            | VARCHAR  | 自定义 SEO 标题              |
| seo_description      | VARCHAR  | 自定义 SEO 描述              |
| status               | VARCHAR  | 文章状态（draft, published） |
| published_at         | DATETIME | 发布时间                     |
| created_at           | DATETIME | 创建时间                     |
| updated_at           | DATETIME | 更新时间                     |

------

## ArticleAsset 表

用于维护文章与资源的映射，复用 `book_asset` 的设计思路。

| 字段          | 说明         |
| :------------ | :----------- |
| id            | 主键         |
| article_id    | 文章 ID      |
| asset_id      | 资源 AssetID |
| relation_type | 关系类型     |

**relation_type 枚举建议：**

text

```
cover
article_image
md_source
ssg_html
thumbnail
attachment
```



------

# 五、前端展示要求

文章列表页 / 文章详情页需实现：

1. 文章列表展示：封面图、标题、摘要、作者、发布时间。
2. 文章详情页：直接渲染 **本地服务器缓存** 中的 HTML 静态页面（若无则按需拉取 OSS 的 HTML 或重新 SSG 生成）。
3. 元数据输出：在 HTML 的 `<head>` 区域必须通过 `og:title`, `description`, `keywords` 等标签暴露 SEO 信息。
4. 所有 OSS 内部信息（Bucket、Object Key、MD5、SHA256 等）**绝对不允许**暴露给前端或文章列表页面，仅展示 Asset 的最终 OSS 访问地址（如图片 URL）。

------

# 六、系统实现与容灾重建流程

### 正常发布流程：

text

```
后台编辑器
↓
触发发布按钮
↓
读取 Markdown 文件内容
↓
调用 SSG 引擎（如 markdown-it + highlight.js）
↓
生成完整 HTML 页面
↓
将 HTML 写入服务器本地目录（缓存）
↓
异步将 HTML 备份上传至 OSS
↓
更新数据库中 `status` 和 `content_html_oss_key`
↓
访客访问文章 URL 时，服务器直接读取本地缓存 HTML
```



### 服务器崩溃后自动恢复流程（容灾设计）：

text

```
服务器重启 / 上线
↓
启动自动恢复脚本
↓
连接数据库，读取所有 `status = published` 的文章记录
↓
遍历记录，根据 `content_md_oss_key` 从 OSS 拉取原始 Markdown 文本
↓
调用 SSG 引擎重新编译为 HTML
↓
将 HTML 写入新的服务器本地缓存目录
↓
完全恢复完毕后，恢复对外服务
```



**设计关键：** 服务器无状态，所有源数据、图片、编译生成的静态文件均能在 OSS 和数据库元数据中找到。**即使服务器本地磁盘完全丢失，也仅需运行一次恢复脚本即可在几分钟内将所有已发布文章重建。**

------

# 七、后续扩展能力

本设计可兼容未来新增的资源类型和应用场景：

- 支持代码高亮的文章（需升级 Markdown 渲染引擎配置）
- 知识库或百科文档
- 带有 OCR 的文本资源
- AI 生成或翻译的摘要缓存
- 多语言版本文章（通过不同的 Asset 映射关联）
- Banner 轮播图 / 网站动态通知

新增资源无需修改 `Article` 主表，仅需在 `Asset` 表中新增类型枚举及关联表即可。

------

# 八、设计原则

1. **文章元数据与资源完全解耦**（`Article` 只负责排版和展示逻辑，`Asset` 负责实际文件存储）。
2. **前端展示以静态 HTML 为核心**，保证搜索引擎友好（SEO）和加载速度。
3. **Markdown 编辑器与 OSS 直连**，图片上传自动生成 Asset 映射关系，避免人工记录图片路径。
4. **双重备份与即时恢复**：生成的 HTML 优先缓存到服务器本地，同时在 OSS 中保留一份，确保服务器崩溃后仍可快速重建。
5. **统一资源管理**：所有文章相关的图片、文件、源数据均可在后台全局 `Asset` 列表中统一查看、筛选和清理。
6. **后台页面风格统一**，与现有 `/admin/books` 及 `/admin/assets` 保持高度一致。