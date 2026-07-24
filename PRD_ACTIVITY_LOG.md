# 产品需求文档（PRD）
# 公开操作日志页面（Public Activity Log）

**版本：** v1.0  
**状态：** 待开发  
**优先级：** P1  
**页面地址：** `/activity`

---

## 一、产品目标

为普通访问者提供一组公开、透明的操作日志页面，展示管理员对图书馆馆藏的维护动态。日志仅公开最近 7 天内的管理行为，不涉及隐私或内部审计信息。

### 1.1 设计原则

- **透明问责**：每条日志署名具体管理员账号（如 `alice`）
- **隐私安全**：不公开 IP、User-Agent、Cookie 等敏感信息
- **限时可见**：仅展示最近 7 天的日志，过期后自动在页面上消失
- **风格统一**：与现有 SSG 静态页面保持一致的视觉风格

---

## 二、页面结构

```
/activity                     ← 一级页面：时间轴
  └── /activity/2026-07-15    ← 二级页面：当日日志列表
```

---

## 三、一级页面 — 时间轴

### 3.1 页面布局

```
┌──────────────────────────────────────────────┐
│  📚 个人图书馆资源小站                         │
│  [首页] [登录] [注册]                          │
├──────────────────────────────────────────────┤
│                                              │
│  📋 馆藏动态（最近 7 天）                       │
│                                              │
│         ┃                                    │
│         ┃                                    │
│    ┌────╋────┐   ← 日期卡片 1                 │
│    │ 7月15日 │                                │
│    │  3 条   │                                │
│    └────╋────┘                                │
│         ┃                                    │
│         ┃                                    │
│    ┌────╋────┐   ← 日期卡片 2                 │
│    │ 7月14日 │                                │
│    │  12 条  │                                │
│    └────╋────┘                                │
│         ┃                                    │
│         ┃                                    │
│    ┌────╋────┐   ← 日期卡片 3                 │
│    │ 7月13日 │                                │
│    │  5 条   │                                │
│    └─────────┘                                │
│                                              │
├──────────────────────────────────────────────┤
│  © 2026 个人图书馆资源小站                      │
└──────────────────────────────────────────────┘
```

### 3.2 交互行为

- 时间轴从顶部（今天）向下排列到 7 天前
- 每条竖线代表一个**有日志的日期**（无日志的日期不显示）
- 日期卡片显示：日期标题（如"7 月 15 日"）+ 当日操作条数
- 点击日期卡片 → 跳转到 `/activity/YYYY-MM-DD?page=1` 查看当日日志详情
- 卡片悬停时有微妙的颜色或阴影变化

### 3.3 数据来源

- 后端 API：`GET /api/activity/timeline`（需新增）
- 返回最近 7 天有日志的日期列表及每日条数

```json
[
  {"date": "2026-07-15", "count": 3},
  {"date": "2026-07-14", "count": 12},
  {"date": "2026-07-13", "count": 5}
]
```

---

## 四、二级页面 — 当日日志列表

### 4.1 页面布局

```
┌──────────────────────────────────────────────┐
│  ← 返回时间轴   2026 年 7 月 15 日（共 3 条）     │
├──────────────────────────────────────────────┤
│                                              │
│  09:45     alice    封禁了用户 User #87       │
│           ❌ 失败 · 操作被拒绝                  │
│                                              │
│  09:20     alice    创建了图书 《大众哲学》      │
│           ✅ 成功                               │
│                                              │
│  08:30     bob      上传了 1 个数字资源         │
│           ✅ 成功                               │
│                                              │
├──────────────────────────────────────────────┤
│  © 2026 个人图书馆资源小站                      │
└──────────────────────────────────────────────┘
```

### 4.2 列表项结构

每条日志显示：

```
MM:SS   [操作者]   [操作描述]   [结果标记]
        [操作类型标识] · [资源名称]
```

- **时间**：`09:45`（不显示日期，日期在标题中）
- **操作者**：管理员用户名（如 `alice`）
- **操作描述**：根据 `action` + `target_type` 生成的自然语言
- **结果**：✅ 成功 / ❌ 失败（失败项附简单原因如"权限不足"）

### 4.3 描述文本生成规则

| action | target_type | 公开描述模板 |
|--------|-------------|-------------|
| `create` | `book` | 创建了图书《{title}》 |
| `update` | `book` | 修改了图书《{title}》 |
| `delete` | `book` | 删除了图书《{title}》 |
| `publish` | `book` | 发布了图书《{title}》 |
| `create` | `article` | 发布了文章《{title}》 |
| `update` | `article` | 修改了文章《{title}》 |
| `delete` | `article` | 删除了文章《{title}》 |
| `upload` | `asset` | 上传了 1 个数字资源 |
| `delete` | `asset` | 删除了 1 个数字资源 |
| `create` | `user` | 创建了用户 {username} |
| `ban` | `user` | 封禁了用户 {username} |
| `unban` | `user` | 解封了用户 {username} |
| `assign_role` | `user` | 修改了用户 {username} 的角色 |
| `create` | `invite_code` | 创建了 1 个邀请码 |
| `create` | `author` | 新增了作者 {name} |
| `delete` | `author` | 删除了作者 {name} |
| `rebuild` | `system` | 重建了整站静态页面 |
| `create` | `role` | 创建了角色 {role_name} |
| `delete` | `role` | 删除了角色 {role_name} |

---

## 五、后端 API 设计

### 5.1 时间轴接口

```
GET /api/activity/timeline
```

**响应：**
```json
[
  {"date": "2026-07-15", "count": 3},
  {"date": "2026-07-14", "count": 12}
]
```

**逻辑：** 查询最近 7 天 `operation_logs` 表中 `is_public = true` 的记录，按日期分组计数。

### 5.2 日志列表接口

```
GET /api/activity?date=2026-07-15&page=1&page_size=50
```

**响应：**
```json
{
  "date": "2026-07-15",
  "total": 3,
  "page": 1,
  "entries": [
    {
      "id": 10235,
      "time": "09:45",
      "operator": "alice",
      "action": "ban",
      "target_type": "user",
      "target_name": "User #87",
      "description": "封禁了用户 User #87",
      "result": "failure",
      "reason": "权限不足"
    }
  ]
}
```

### 5.3 写入时需新增字段

在 `operation_logs` 表新增 `is_public` 字段：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `is_public` | BOOLEAN | TRUE | 是否允许在公开日志中展示 |

后端在写入操作日志时，自动根据 `action` 类型判断 `is_public`：
- 图书/文章/作者/出版社/标签/资源/封禁/角色/邀请码/重建 → `is_public = TRUE`
- 登录/登出/下载/密码重置/API 调用/SQL → `is_public = FALSE`

---

## 六、前端页面

### 6.1 页面路由

| 路径 | 页面 | 模板文件 |
|------|------|----------|
| `/activity` | 时间轴首页 | `templates/activity/index.html` |
| `/activity/{date}` | 当日日志列表 | `templates/activity/day.html` |

### 6.2 路由注册

在 `app/main.py` 中添加两个 Server-Rendered 路由（非 SSG 静态页，因为数据实时变化）：

```python
@app.get("/activity", response_class=HTMLResponse)
def activity_timeline():
    return HTMLResponse(TEMPLATES.get_template("activity/index.html").render())

@app.get("/activity/{date}", response_class=HTMLResponse)
def activity_day(date: str):
    return HTMLResponse(TEMPLATES.get_template("activity/day.html").render(date=date))
```

### 6.3 导航入口

在 SSG `base.html` 的顶部导航栏中添加：

```html
<a href="/activity">📋 动态</a>
```

### 6.4 前端逻辑

- 页面加载时通过 `fetch('/api/activity/timeline')` 获取最近 7 天日期列表
- 纯 JS 渲染时间轴，无需预生成静态页面
- 点击日期卡片 → 跳转二级页面，再通过 `fetch('/api/activity?date=...')` 获取当日日志
- 二级页面的 `<title>` 显示"馆藏动态 - YYYY年M月D日"

### 6.5 UI 风格

- 沿用现有 SSG 页面风格：顶部导航栏（site-header）、底部页脚（site-footer）
- 字体、颜色、间距与现有页面一致
- 时间轴使用 CSS `border-left` 画竖线
- 日期卡片使用现有的 `.card` 样式
- 日志列表项使用简单的行式布局，不引入新的设计语言

---

## 七、公开日志字段表（最终）

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `id` | INTEGER | operation_logs.id | 日志唯一编号 |
| `timestamp` | DATETIME | operation_logs.timestamp | 精确操作时间 |
| `operator` | VARCHAR | users.username | 操作者用户名 |
| `action` | VARCHAR | operation_logs.action | 操作类型 |
| `target_type` | VARCHAR | operation_logs.target_type | 操作对象类型 |
| `target_name` | VARCHAR | 拼接生成 | 资源名称（如《资本论》） |
| `description` | VARCHAR | 模板生成 | 自然语言描述 |
| `result` | VARCHAR | operation_logs.result | success / failure |
| `reason` | VARCHAR | 自动填入 | 失败原因（仅 failure 时显示） |

**永不公开的字段：**
`user_id`, `ip_address`, `session_key`, `user_agent`, `referer`, JWT Token 等

---

## 八、验收标准

1. 访问 `/activity` 显示最近 7 天的时间轴，每个有日志的日期对应一个可点击卡片
2. 无日志的日期不出现在时间轴上
3. 点击日期卡片 → 跳转当日日志列表，按时间升序排列
4. 日志显示操作者用户名（如 `alice`），而非角色名
5. 失败的日志显示红色 ❌ 和失败原因
6. 登录、下载、浏览等内部日志不出现在公开页面上
7. 8 天前的日志不出现在时间轴上
8. 页面风格、字体、颜色与现有 SSG 站点一致
9. 顶部导航栏有"📋 动态"入口
