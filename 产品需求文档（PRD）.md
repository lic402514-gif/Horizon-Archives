# 产品需求文档（PRD）

# 项目名称

Book Card Editor（图书卡编辑器）

---

# 一、项目简介

Book Card Editor 是一个基于 **Python** 开发的桌面 GUI 应用程序，用于创建、编辑、管理图书元数据（Book Card）。

程序采用 **JSON** 作为唯一的数据存储格式，每一本书对应一个 JSON 文件。

软件定位为：

> 一个轻量级、可扩展的图书元数据编辑器。

主要面向电子书整理、个人图书馆管理、学术文献管理等场景。

---

# 二、总体目标

开发一个具有现代化图形界面的桌面程序，实现：

- 图形化创建图书卡
- 图形化编辑 JSON
- 打开已有 JSON
- 保存 JSON
- 自动补全图书信息
- API Key 图形化管理
- 数据验证
- 自动纠错
- 后续可扩展 OCR、ISBN 扫描等功能

程序应做到：

- 开箱即用
- 不依赖 Python 环境
- 无需安装任何第三方依赖
- 可以直接双击运行

---

# 三、最终交付要求

最终交付应包含：

```
BookCardEditor.exe
```

要求：

- Windows 10 / Windows 11 可直接运行
- 单文件 EXE
- 不需要安装 Python
- 不需要配置环境变量
- 不需要安装 VC Runtime（如可静态打包则优先）
- 所有依赖全部打包进入 EXE
- 可以直接复制到其它电脑运行

推荐使用：

- PyInstaller（--onefile）
- Nuitka（优先，性能更好）
- auto-py-to-exe（仅作为开发辅助）

要求最终生成：

```
BookCardEditor.exe
```

启动后即可运行。

---

# 四、技术要求

开发语言：

- Python 3.11+

GUI：

优先：

- PySide6（推荐）

其次：

- PyQt6

数据格式：

- JSON

网络请求：

- requests
- httpx（均可）

配置文件：

- config.json

日志：

- logging

---

# 五、项目目录结构

建议采用模块化设计：

```
BookCardEditor/

│
├── main.py
│
├── ui/
│     main_window.py
│     settings_dialog.py
│     editor_widget.py
│
├── api/
│     google_books.py
│     deepseek.py
│
├── models/
│     book_card.py
│
├── config/
│     config.py
│
├── utils/
│     validator.py
│     logger.py
│
├── resources/
│
├── cards/
│
├── config.json
│
└── requirements.txt
```

禁止：

- 所有逻辑写到 main.py
- 超长函数
- 全局变量泛滥

要求：

高内聚

低耦合

模块化

---

# 六、Book Card 数据结构

每一本书对应一个 JSON。

标准字段如下：

| 字段                           | 类型     | 说明        |
| ------------------------------ | -------- | ----------- |
| title                          | string   | 书名        |
| authors                        | string[] | 作者        |
| translators                    | string[] | 译者        |
| editors                        | string[] | 编者        |
| publisher                      | string   | 出版社      |
| year                           | integer  | 出版年份    |
| edition                        | string   | 版次        |
| printing                       | string   | 印次        |
| isbn                           | string   | ISBN        |
| series                         | string   | 丛书        |
| language                       | string   | zh/en/ja/de |
| pages                          | integer  | 页数        |
| category                       | string   | 学科分类    |
| tags                           | string[] | 标签        |
| summary                        | string   | 图书简介    |
| chinese_library_classification | string   | 中图法      |

JSON 示例：

```json
{
    "title": "",
    "authors": [],
    "translators": [],
    "editors": [],
    "publisher": "",
    "year": 0,
    "edition": "",
    "printing": "",
    "isbn": "",
    "series": "",
    "language": "",
    "pages": 0,
    "category": "",
    "tags": [],
    "summary": "",
    "chinese_library_classification": ""
}
```

---

# 七、GUI 功能需求

## 1、新建图书卡

点击：

```
新建
```

生成新的空白 Book Card。

---

## 2、打开 JSON

支持：

```
*.json
```

读取后自动填充所有字段。

---

## 3、编辑图书卡

所有字段均支持编辑。

其中：

```
authors
translators
editors
tags
```

采用：

- List Widget
- 新增
- 删除
- 修改
- 调整顺序

禁止采用：

```
作者1;作者2;作者3
```

这种字符串形式。

---

## 4、保存

支持：

```
保存
```

以及：

```
另存为
```

统一 UTF-8。

格式化输出 JSON（缩进 4 Spaces）。

---

# 八、自动补全

根据已有信息自动补全。

例如：

用户输入：

```
title

author

ISBN
```

程序自动补全：

```
publisher

year

summary

language

pages

series

category
```

等字段。

---

# 九、补全方式

支持两种。

## Google Books API

用户填写：

```
Google API Key
```

程序调用：

Google Books API

查询依据：

优先级：

```
ISBN

↓

Title + Author

↓

Title
```

解析返回结果。

自动填充。

---

## DeepSeek API

用户填写：

```
DeepSeek API Key
```

程序发送：

当前 Book Card。

要求 Prompt：

返回：

严格 JSON。

禁止：

Markdown。

禁止：

解释。

不存在的数据：

保持空字符串。

---

# 十、API 设置

软件提供：

```
设置
```

页面。

可填写：

Google API Key

DeepSeek API Key

保存：

```
config.json
```

例如：

```json
{
    "google_api_key":"",
    "deepseek_api_key":""
}
```

程序启动自动加载。

无需重复输入。

API Key 输入框应支持：

- 密码模式显示（可切换显示/隐藏）
- 一键测试连接
- 保存
- 重置

---

# 十一、补全方式选择

GUI 提供：

```
○ Google Books

○ DeepSeek
```

二选一。

点击：

```
开始补全
```

执行。

---

# 十二、补全流程

整体流程：

```
用户填写部分信息

↓

点击补全

↓

选择补全方式

↓

请求 API

↓

返回 JSON

↓

解析

↓

验证

↓

自动填充

↓

保存
```

---

# 十三、JSON 验证

所有补全必须验证。

例如：

year

必须：

```
Integer
```

pages：

```
Integer
```

authors：

```
Array
```

tags：

```
Array
```

summary：

```
String
```

ISBN：

支持：

```
ISBN10

ISBN13
```

language：

推荐：

```
ISO639-1
```

例如：

```
zh

en

ja

de

fr
```

不能为空则保持空字符串。

---

# 十四、自动回滚机制

如果：

DeepSeek 返回：

- JSON 非法
- 字段缺失
- 类型错误

程序：

自动调用：

Google Books API

重新获取。

若：

Google Books 返回异常：

自动：

再次搜索：

```
ISBN

↓

Title + Author

↓

Title
```

若仍失败：

提示：

```
补全失败
```

保留原数据。

不得覆盖。

---

# 十五、覆盖策略

默认：

```
仅补全空字段
```

例如：

已有：

```
publisher

人民出版社
```

Google 返回：

```
商务印书馆
```

不得覆盖。

除非用户勾选：

```
☑ 覆盖已有字段
```

---

# 十六、界面布局建议

```
┌──────────────────────────────────────────────┐

 文件 编辑 设置 工具 帮助

──────────────────────────────────────────────

书名：

___________________________________

作者：

[列表]

[新增]

出版社：

___________________________________

ISBN：

___________________________________

出版年份：

______________

......

简介：

────────────────────────────

────────────────────────────

────────────────────────────

────────────────────────────

────────────────────────────

────────────────────────────

────────────────────────────

────────────────────────────

────────────────────────────

────────────────────────────

○ Google Books

○ DeepSeek

☐ 覆盖已有字段

[开始补全]

────────────────────────────

[新建]

[打开]

[保存]

[另存为]

└──────────────────────────────────────────────┘
```

---

# 十七、异常处理

必须：

所有异常均捕获。

包括：

- JSON 解析失败
- API 请求失败
- 网络异常
- 超时
- API Key 无效
- 文件不存在
- 权限不足

不得：

程序闪退。

应弹窗提示。

---

# 十八、日志系统

采用：

```
logging
```

输出：

```
logs/

2026-07-11.log
```

记录：

- API 请求
- JSON 解析
- 保存
- 打开
- 错误信息

方便调试。

---

# 十九、性能要求

所有 API 请求：

不得阻塞 GUI。

要求：

使用：

- QThread
- 或 ThreadPool
- 或 asyncio（与 Qt 正确集成）

补全过程：

界面保持响应。

显示：

```
正在补全……
```

支持取消。

---

# 二十、代码规范

要求：

- 面向对象（OOP）
- MVC 或 MVVM 风格均可
- 模块化
- 类型注解（Type Hint）
- 所有公开函数编写 Docstring
- 遵循 PEP 8 规范
- 不允许出现大量重复代码
- 配置、数据模型、GUI、API、工具类彼此解耦

---

# 二十一、未来扩展接口（预留）

程序架构需预留扩展能力，便于后续新增以下功能，而无需重构核心代码：

- OCR 自动识别封面或版权页信息
- ISBN 条码扫描
- Open Library API
- 豆瓣图书（如可用）
- 国家图书馆或 WorldCat 等更多数据源
- AI 自动生成摘要
- AI 自动推荐标签
- AI 自动推荐中图法分类
- 封面图片下载
- 批量导入 JSON
- 批量导出 JSON
- 批量自动补全
- EPUB/PDF 元数据提取
- SQLite 数据库存储
- 全文检索
- 多语言界面（中文/英文）
- 自动更新
- 插件系统

所有扩展应通过统一接口注册，实现数据源和补全策略的可插拔设计。

---

# 二十二、验收标准

项目完成后，应满足以下条件：

- 可以直接双击 `BookCardEditor.exe` 运行
- 无需安装 Python 或任何运行环境
- 可以新建、打开、编辑、保存图书卡 JSON
- 图形界面完整、美观、响应流畅
- 可配置并保存 Google Books API Key 与 DeepSeek API Key
- 可任选 Google Books 或 DeepSeek 完成图书信息补全
- 补全过程具备数据验证、异常处理与自动回滚机制
- 所有 API 请求均不会阻塞 GUI
- 数据格式严格符合定义的 JSON Schema
- 项目代码结构清晰，模块化程度高，具备良好的可维护性与可扩展性
- 最终生成单文件 `BookCardEditor.exe`，能够在未安装 Python 的 Windows 10/11 系统上独立运行。