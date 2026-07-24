# 图片资源管理与 Markdown 可视化编辑系统 PRD

## 1. 产品概述

### 1.1 产品名称

Markdown + OSS 图片管理与可视化编辑系统

### 1.2 产品定位

本系统用于支持基于 Markdown 的文章编辑、图片管理、静态页面生成（SSG）以及 OSS 图片托管。

系统目标：

- 编辑阶段保持 Markdown 纯文本结构；
- 图片资源由 OSS 负责存储与分发；
- SSG 构建阶段自动解析图片引用；
- 自动生成符合文章 UI 规范的 HTML；
- 前端访问时所有图片均通过 OSS 直链加载；
- CMS 编辑阶段提供实时图片预览体验。

---

# 2. 核心设计原则

## 2.1 内容与资源分离

文章内容：

- Markdown 文件
- 数据库存储正文内容

图片资源：

- OSS Object Storage

HTML 页面：

- SSG 构建生成

访问关系：

用户
|
↓
静态HTML页面
|
↓
OSS图片资源

```
VPS 不承担图片传输。


---

## 2.2 Markdown 为唯一编辑源

编辑人员只操作 Markdown。

例如：

```markdown
# 马克思主义研究

正文内容。

![马克思手稿](images/marx-page01.webp)

继续正文。
```

禁止直接编辑：

```html
<img>
```

所有 HTML 由 SSG 自动生成。

------

# 3. 图片处理流程

## 3.1 总体流程

```
CMS编辑器

        |
        ↓

Markdown文本

        |
        ↓

图片语法解析器

        |
        ↓

图片资源管理模块

        |
        ├── 本地图片检测
        |
        ├── OSS上传
        |
        ├── 获取图片Metadata
        |
        └── 生成OSS URL


        |
        ↓

SSG构建


        |
        ↓

生成HTML


        |
        ↓

用户访问


        |
        ↓

OSS直链加载图片
```

------

# 4. Markdown 图片语法支持

## 4.1 标准语法

支持：

```markdown
![图片描述](图片路径)
```

示例：

```markdown
![书籍封面](./assets/book-cover.webp)
```

------

## 4.2 OSS地址转换

编辑阶段：

```markdown
![封面](./assets/book.webp)
```

构建阶段自动转换：

```html
<img
src="https://oss.example.com/book.webp"
alt="封面">
```

------

# 5. CMS 编辑器需求

# 5.1 Markdown源码编辑

编辑器必须提供：

- Markdown源码区域；
- 语法高亮；
- 光标定位；
- 插入图片语法。

示例：

```
---------------------------------

Markdown编辑区

![图片](image.webp)


---------------------------------
```

------

# 5.2 实时图片预览

编辑器需要提供：

实时解析 Markdown 图片语法。

输入：

```markdown
![图片](image.webp)
```

自动显示：

```
+----------------+
|                |
|     图片       |
|                |
+----------------+
```

要求：

- 不修改 Markdown 原文；
- 预览层独立渲染；
- 保存时保存 Markdown。

------

# 5.3 图片语法解析

编辑器自动检测：

```
![alt](path)
```

解析：

```json
{
"type":"image",
"path":"path",
"alt":"alt"
}
```

生成：

```
图片预览组件
```

------

# 6. 图片上传系统

# 6.1 拖入图片上传

支持：

- 文件拖入编辑器；
- 图片复制粘贴；
- 图片选择上传。

------

# 6.2 上传流程

禁止：

```
浏览器
 |
 ↓
VPS
 |
 ↓
OSS
```

采用：

```
浏览器

 |
 |
请求上传授权

 ↓

VPS API

 |
 |
返回OSS临时凭证

 ↓

浏览器

 |
 |
直接上传

 ↓

OSS
```

要求：

- VPS不承担图片流量；
- 不产生服务器带宽消耗。

------

# 7. 拖拽插入位置管理

## 7.1 光标保持

用户操作：

```
正文内容|

拖入图片
```

系统行为：

保存当前光标位置。

上传完成：

自动恢复光标。

插入：

```markdown
正文内容

![图片](OSS_URL)

|
```

------

## 7.2 实现要求

编辑器必须支持：

- Selection保存；
- Range恢复；
- 异步上传后插入。

流程：

```
保存Cursor

↓

上传图片

↓

恢复Cursor

↓

插入Markdown
```

------

# 8. OSS资源管理

## 8.1 图片存储结构

建议：

```
OSS Bucket

/library

    /article

        /2026

            image001.webp


    /books

        /covers

            cover001.webp
```

------

# 8.2 图片Metadata

数据库保存：

```json
{
"id":"image001",

"url":"oss/path/image.webp",

"width":2400,

"height":3500,

"ratio":1.45,

"hash":"xxxx",

"size":102400,

"mime":"image/webp"
}
```

字段：

| 字段   | 说明       |
| ------ | ---------- |
| id     | 图片唯一ID |
| url    | OSS地址    |
| width  | 原始宽度   |
| height | 原始高度   |
| ratio  | 宽高比例   |
| hash   | 文件去重   |
| size   | 文件大小   |
| mime   | 文件类型   |

------

# 9. SSG 图片渲染系统

## 9.1 构建阶段处理

SSG读取：

```markdown
![图片](image001)
```

执行：

```
解析图片节点

↓

读取Metadata

↓

计算尺寸

↓

生成HTML
```

------

# 9.2 图片尺寸计算

文章内容区域：

```
content_width = 860px
```

图片：

```
original_width = 2400

original_height = 3500
```

计算：

```
display_height =
content_width × original_height / original_width
```

结果：

```
860 × 3500 / 2400

=1254px
```

------

# 9.3 输出HTML规范

生成：

```html
<img
src="OSS_URL"
width="860"
height="1254"
loading="lazy"
alt="图片描述">
```

要求：

- 自动适应文章宽度；
- 自动计算高度；
- 防止页面布局跳动；
- 支持SEO。

------

# 10. 前端图片加载要求

## 10.1 图片来源

所有文章图片：

必须：

```
OSS直链加载
```

禁止：

```
HTML服务器代理图片
```

------

## 10.2 页面访问流程

```
用户访问文章

↓

加载HTML

↓

发现OSS图片URL

↓

浏览器直接请求OSS

↓

显示图片
```

------

# 11. 图片优化要求

支持：

- WebP转换；
- 图片压缩；
- 缩略图生成；
- 原图保存。

例如：

```
original/

image.jpg


processed/

image.webp

image-small.webp

image-thumb.webp
```

------

# 12. 图片状态管理

图片生命周期：

```
本地文件

↓

上传中

↓

OSS完成

↓

绑定Markdown

↓

发布文章
```

状态：

```json
{
"status":"uploaded",

"oss_url":"xxx",

"width":2400,

"height":3500
}
```

------

# 13. 非功能需求

## 13.1 性能

要求：

- 图片加载不经过VPS；
- 支持OSS CDN；
- 支持Lazy Loading；
- 支持大量文章图片。

------

## 13.2 可维护性

要求：

- Markdown永久可读；
- 图片资源独立管理；
- HTML可重新生成；
- OSS路径可迁移。

------

## 13.3 安全

要求：

- OSS上传使用临时授权；
- 不暴露AccessKey；
- 上传权限最小化；
- 图片资源权限可控制。

------

# 14. 最终系统架构

```
                CMS

        Markdown编辑器

              |
              |

        图片管理模块

              |
              |

          OSS上传

              |
              |

          Markdown

              |
              |

             SSG

              |
              |

        静态HTML页面

              |
              |

             用户

              |
              |

             OSS
```

------

# 15. MVP实现范围

第一阶段：

- Markdown编辑器；
- 图片语法解析；
- OSS直传；
- 图片预览；
- SSG图片替换；
- 自动尺寸计算。

第二阶段：

- 图片库管理；
- 图片搜索；
- 图片去重；
- 自动压缩；
- CDN优化。

第三阶段：

- 富媒体编辑；
- 图片版本管理；
- 权限控制；
- 图片审核。

------

# 产品目标总结

实现一个：

**Markdown作为内容源，OSS作为图片资源中心，SSG负责页面生成，CMS提供实时可视化编辑体验的现代静态内容管理系统。**

核心特点：

1. 编辑使用纯Markdown；
2. 图片自动上传OSS；
3. 图片预览与源码分离；
4. 拖拽图片自动插入；
5. 光标位置保持；
6. SSG自动生成规范HTML；
7. 所有图片通过OSS直链访问；
8. VPS只承担业务逻辑，不承担媒体流量。

```

```