# 意见收集与议题投票系统 PRD

## 1. 产品概述

### 1.1 产品名称

议题意见征集与民主投票系统（Issue Governance System）

---

## 1.2 产品定位

本系统用于实现网站内部的：

- 公共议题发布
- 用户意见征集
- 多方案讨论
- 在线投票
- 投票结果统计
- 结果公示
- 历史归档

形成完整的议题生命周期管理。

系统参考：

- RFC（Request For Comments）意见征集机制
- 社区治理提案系统
- DAO Proposal 治理模型
- 政策意见征集平台

---

# 2. 产品目标

## 2.1 核心目标

实现一个公开透明的议题治理流程：

议题创建
↓
意见征集
↓
用户讨论
↓
方案投票
↓
自动计票
↓
结果公示
↓
历史归档

```
---

## 2.2 用户目标

### 普通用户

用户可以：

- 浏览公开议题
- 阅读议题背景
- 查看方案
- 发布意见
- 回复讨论
- 参与投票
- 查看最终结果


### 管理员

管理员可以：

- 创建议题
- 编辑议题
- 设置投票规则
- 管理讨论
- 发布结果
- 查看统计数据

---

# 3. 功能范围

系统包含：
```

议题管理模块
|
|
├── 议题发布
├── 议题编辑
├── 议题状态管理
|
|
方案管理模块
|
|
├── 创建投票选项
├── 修改方案
├── 删除方案
|
|
意见讨论模块
|
|
├── 评论
├── 回复
├── 审核
|
|
投票模块
|
|
├── 简单多数
├── 绝对多数
├── 批准投票
├── STV
|
|
结果模块
|
|
├── 自动统计
├── 结果公示
├── 历史保存

```
---

# 4. 议题生命周期设计

## 4.1 状态定义


|状态|说明|
|-|-|
|draft|草稿|
|discussion|意见征集阶段|
|voting|投票阶段|
|counting|统计阶段|
|finished|结果公布|
|archived|历史归档|


---

## 4.2 状态流转
```

draft

↓

discussion

↓

voting

↓

counting

↓

finished

↓

archived

```
---

# 5. 用户端功能需求


# 5.1 议题列表页

## 功能

展示所有公开议题。


## 页面字段


|字段|说明|
|-|-|
|标题|议题名称|
|状态|当前阶段|
|发布时间|创建时间|
|截止时间|意见/投票截止时间|
|参与人数|参与讨论和投票人数|
|结果状态|是否公布结果|


---

# 5.2 议题详情页


页面结构：
```

------

议题标题

状态：

投票中

------

议题正文

------

方案列表

------

投票区域

------

讨论区

------

结果区域

------

```
---

# 5.3 议题正文


支持 Markdown。


内容包括：

- 背景介绍
- 当前问题
- 提案内容
- 相关资料
- 参考文件


示例：
```

## 背景

目前图书馆开放时间不足。

## 问题

学生晚上缺少学习空间。

## 提案

开放时间延长至22:00。

```
---

# 5.4 用户评论功能


用户可以：

- 发布意见
- 回复其他用户
- 删除自己的评论


评论支持：
```

一级评论

```
↓
```

回复评论

```
---

# 6. 投票系统设计


## 6.1 投票方式


系统支持：

1. 简单多数投票
2. 绝对多数投票
3. 批准投票
4. STV 单票可转移制


---

# 6.2 简单多数


规则：

票数最高方案获胜。


示例：
```

方案A:

600票

方案B:

400票

结果：

A通过

```
---

# 6.3 绝对多数


规则：

方案支持率必须超过50%。


计算：
```

支持票数 / 总票数 > 50%

```
否则：
```

未通过

```
---

# 6.4 批准投票


特点：

用户可以同时支持多个方案。


示例：
```

请选择支持方案：

☑ A

☑ B

☐ C

```
统计：

每个方案独立计算票数。


---

# 6.5 STV 投票


用于：

多个候选方案竞争。


用户提交排序：
```

第一选择：

A

第二选择：

C

第三选择：

B

```
系统按照STV算法计算最终结果。

---

# 7. 数据库设计


# 7.1 用户表

users

已有用户系统。


---

# 7.2 议题表 issues


```sql
CREATE TABLE issues (

id BIGINT PRIMARY KEY,


title VARCHAR(255),


content TEXT,


creator_id BIGINT,


status VARCHAR(30),


vote_type VARCHAR(50),


discussion_start DATETIME,


discussion_end DATETIME,


vote_start DATETIME,


vote_end DATETIME,


result_publish_time DATETIME,


created_at DATETIME,


updated_at DATETIME

);
```

------

# 7.3 议题选项表 issue_options

```sql
CREATE TABLE issue_options (

id BIGINT PRIMARY KEY,


issue_id BIGINT,


title VARCHAR(255),


content TEXT,


sort INT,


vote_count INT DEFAULT 0

);
```

------

# 7.4 投票记录表 votes

```sql
CREATE TABLE votes (

id BIGINT PRIMARY KEY,


issue_id BIGINT,


option_id BIGINT,


user_id BIGINT,


created_at DATETIME

);
```

约束：

普通投票：

```
(issue_id,user_id)
唯一
```

批准投票：

```
(issue_id,user_id,option_id)
唯一
```

------

# 7.5 STV排序表 vote_preferences

```sql
CREATE TABLE vote_preferences (

id BIGINT PRIMARY KEY,


vote_id BIGINT,


option_id BIGINT,


rank INT

);
```

------

# 7.6 评论表 issue_comments

```sql
CREATE TABLE issue_comments (

id BIGINT PRIMARY KEY,


issue_id BIGINT,


user_id BIGINT,


parent_id BIGINT,


content TEXT,


status VARCHAR(20),


created_at DATETIME

);
```

------

# 7.7 结果表 issue_results

```sql
CREATE TABLE issue_results (

id BIGINT PRIMARY KEY,


issue_id BIGINT,


option_id BIGINT,


vote_count INT,


percentage DECIMAL(5,2),


rank INT,


created_at DATETIME

);
```

------

# 8. 管理后台需求

## 8.1 议题管理

管理员可以：

- 新建议题
- 编辑议题
- 删除草稿
- 发布议题
- 关闭议题

------

## 8.2 方案管理

管理员可以：

- 添加方案
- 修改方案
- 调整排序
- 设置方案说明

------

## 8.3 投票管理

管理员可以：

设置：

```
投票方式

投票开始时间

投票结束时间

结果公开时间
```

------

## 8.4 结果管理

系统自动：

- 统计票数
- 计算比例
- 判断是否通过
- 生成结果页面

------

# 9. 权限设计

## 普通用户

权限：

```
查看议题

评论

投票

查看结果
```

------

## 管理员

权限：

```
创建议题

编辑议题

审核评论

管理投票

发布结果
```

------

# 10. 安全要求

## 10.1 防重复投票

要求：

服务器验证：

```
用户ID

+

议题ID

+

投票状态
```

禁止：

- 修改请求参数重复投票
- 前端伪造票数

------

## 10.2 投票截止锁定

当：

```
当前时间 > vote_end
```

禁止：

- 新增投票
- 修改投票

------

## 10.3 结果不可篡改

投票结束后：

生成结果快照。

历史结果不受：

- 方案修改
- 用户删除
- 管理操作

影响。

------

# 11. 前端页面需求

## 用户端

```
/issues

议题列表


/issues/{id}

议题详情


/issues/{id}/result

结果页面
```

------

## 管理端

```
/admin/issues

议题管理


/admin/issues/create

创建议题


/admin/issues/{id}/statistics

统计页面
```

------

# 12. 后端接口设计

## 创建议题

POST

```
/api/issues
```

------

## 获取议题

GET

```
/api/issues/{id}
```

------

## 发布评论

POST

```
/api/issues/{id}/comments
```

------

## 投票

POST

```
/api/issues/{id}/vote
```

------

## 获取结果

GET

```
/api/issues/{id}/result
```

------

# 13. 后续扩展

未来支持：

- 匿名投票
- 投票审计日志
- 委托投票
- 权重投票
- 用户信誉系统
- 投票记录公开
- AI辅助总结意见
- 自动生成议题报告

------

# 14. MVP最低实现版本

第一阶段只实现：

```
议题发布

↓

评论讨论

↓

单选投票

↓

简单多数统计

↓

结果公布
```

第二阶段：

```
批准投票

绝对多数

多方案管理
```

第三阶段：

```
STV

复杂治理模型

审计系统
```

------

# 产品目标总结

本系统最终形成一个：

「公开透明、可讨论、可投票、可追踪、可归档」

的在线议题治理平台。



下面作为 PRD 的附件文档使用，重点说明四种投票机制的**运行流程、数据结构要求、计算算法以及系统实现逻辑**。

# 附件：投票机制与算法说明文档

## 文档说明

本文档用于说明议题治理系统支持的四种投票方式：

1. 简单多数投票（Simple Majority）
2. 绝对多数投票（Absolute Majority）
3. 批准投票（Approval Voting）
4. 单票可转移制（Single Transferable Vote，STV）

系统需要根据议题创建时选择的投票类型，自动调用对应的计票算法，并生成最终结果。

---

# 一、简单多数投票（Simple Majority）

## 1.1 机制说明

简单多数投票是最基础的投票方式。

规则：

> 获得有效票数最多的选项获得通过。

该方式不要求候选方案获得超过半数支持，只比较各方案之间的相对票数。

适用于：

- 单一方案选择
- 意见倾向调查
- 多方案竞争


---

## 1.2 用户投票方式

用户只能选择一个选项。

例如：

议题：

是否增加夜间开放时间？

```
选项：
```

A. 延长至22点

B. 延长至24点

C. 保持现状

```
用户选择：
```

○ A

○ B

○ C

```
---

# 1.3 数据存储


votes表：

|字段|说明|
|-|-|
|issue_id|议题ID|
|option_id|选择的方案|
|user_id|用户ID|


限制：

同一用户：
```

一个议题只能产生一票

```
数据库约束：
```

UNIQUE(issue_id,user_id)

```
---

# 1.4 计算算法


输入：
```

options = [
A,
B,
C
]

votes = [
A票数,
B票数,
C票数
]

```
计算：
```

winner = max(vote_count)

```
伪代码：

```python
def simple_majority(options):

    winner = None

    max_votes = 0


    for option in options:

        if option.vote_count > max_votes:

            winner = option

            max_votes = option.vote_count


    return winner
```

------

# 1.5 平票处理

如果：

```
A = 500票

B = 500票
```

系统需要：

方式一：

```
宣布平票
重新投票
```

方式二：

```
进入管理员裁决流程
```

默认推荐：

```
平票 => 无结果
```

------

------

# 二、绝对多数投票（Absolute Majority）

## 2.1 机制说明

绝对多数要求：

> 一个方案必须获得超过全部有效票的一半才能通过。

计算公式：

```
支持率 =
方案票数 ÷ 有效总票数
```

通过条件：

```
支持率 > 50%
```

------

# 2.2 用户投票方式

通常采用单选：

```
○ 支持方案A

○ 支持方案B

○ 反对
```

------

# 2.3 数据结构

与简单多数一致。

votes：

```
issue_id

option_id

user_id
```

------

# 2.4 计算算法

步骤：

## 第一步

计算总票数：

```
total_votes =
所有有效投票数量
```

------

## 第二步

计算每个方案支持率：

```
percentage =
option_votes / total_votes
```

------

## 第三步

判断：

```
if percentage > 0.5:

    approved

else:

    rejected
```

伪代码：

```python
def absolute_majority(option,total_votes):

    rate = option.vote_count / total_votes


    if rate > 0.5:

        return "通过"

    else:

        return "未通过"
```

------

# 2.5 特殊情况

例如：

```
总票数：

1000


支持：

500
```

结果：

```
未通过
```

因为：

绝对多数要求：

```
>50%

不是

>=50%
```

------

------

# 三、批准投票（Approval Voting）

## 3.1 机制说明

批准投票允许用户：

> 同时支持多个方案。

与普通投票区别：

普通投票：

```
一个用户只能选择一个
```

批准投票：

```
一个用户可以选择多个
```

------

# 3.2 使用场景

适用于：

- 多个方案均可能接受
- 候选人选举
- 推荐系统
- 方案筛选

------

# 3.3 用户界面

示例：

```
请选择支持方案：


☑ 延长开放时间

☑ 增加自习室

☐ 增加咖啡厅
```

用户提交：

```
A+B
```

------

# 3.4 数据结构变化

普通投票：

```
用户
 |
 |
一个选项
```

批准投票：

```
用户
 |
 |
多个选项
```

因此数据库约束修改：

取消：

```
UNIQUE(issue_id,user_id)
```

改为：

```
UNIQUE(issue_id,user_id,option_id)
```

------

# 3.5 计算算法

每个选项独立统计。

例如：

```
用户数量：

1000


A:

800支持


B:

600支持


C:

200支持
```

计算：

```
A排名第一
```

伪代码：

```python
def approval_vote(options):

    result=[]


    for option in options:

        result.append(
            option.vote_count
        )


    sort(result)

    return result
```

------

# 3.6 结果规则

默认：

```
最高批准数方案获胜
```

也可以：

```
公布全部支持率
```

例如：

```
A:
80%

B:
60%

C:
20%
```

------

------

# 四、单票可转移制（STV）

## 4.1 机制说明

STV是一种排序投票制度。

核心思想：

> 用户不是只选择一个候选方案，而是按照偏好顺序排列候选方案。

如果第一选择无法获胜：

该选票自动转移到第二选择。

------

# 4.2 使用场景

适用于：

- 多候选人选举
- 多方案竞争
- 避免赢家只获得少数支持

------

# 4.3 用户投票方式

用户排序：

```
第一选择：

A


第二选择：

C


第三选择：

B
```

数据库保存：

```
rank=1 A

rank=2 C

rank=3 B
```

------

# 4.4 数据结构

需要增加：

vote_preferences

字段：

| 字段      | 说明     |
| --------- | -------- |
| vote_id   | 投票记录 |
| option_id | 候选方案 |
| rank      | 排序     |

例如：

| rank | option |
| ---- | ------ |
| 1    | A      |
| 2    | C      |
| 3    | B      |

------

# 4.5 STV算法流程

## 第一步：

计算胜选门槛。

Droop quota：

公式：

```
quota =
floor(
有效票数/(席位数+1)
)+1
```

单席位：

```
quota =
floor(
votes/2
)+1
```

------

# 第二步：

统计第一选择。

例如：

```
A:

45票


B:

35票


C:

20票
```

------

# 第三步：

判断是否达到门槛。

如果：

```
A >= quota
```

A胜。

------

# 第四步：

如果无人达到门槛。

淘汰最低票候选。

例如：

```
C最低
```

删除C。

------

# 第五步：

转移C的选票。

C支持者：

查看第二选择。

例如：

```
C选票：

30张


其中：

20转给A

10转给B
```

重新计算。

------

# 第六步：

重复：

```
统计

↓

淘汰最低

↓

转移选票

↓

重新统计
```

直到：

```
产生胜者
```

------

# 4.6 STV伪代码

```python
def STV(options,votes):


    while True:


        count_first_choices()


        winner = check_quota()


        if winner:

            return winner



        lowest = find_lowest()


        eliminate(lowest)


        transfer_votes()
```

------

# 五、四种投票方式对比

| 类型     | 用户选择 | 算法复杂度 | 适用场景     |
| -------- | -------- | ---------- | ------------ |
| 简单多数 | 单选     | 低         | 普通方案选择 |
| 绝对多数 | 单选     | 低         | 重大决策     |
| 批准投票 | 多选     | 中         | 候选筛选     |
| STV      | 排序     | 高         | 多人竞争     |

------

# 六、系统实现要求

## 6.1 投票类型字段

issues表：

```
vote_type
```

取值：

```
simple_majority

absolute_majority

approval

stv
```

------

## 6.2 计票服务设计

后端建立统一接口：

```python
calculate_result(issue_id)
```

内部根据类型调用：

```
if vote_type == simple_majority:

    SimpleMajority()


elif vote_type == absolute_majority:

    AbsoluteMajority()


elif vote_type == approval:

    ApprovalVoting()


elif vote_type == stv:

    STV()
```

------

# 七、结果输出格式

所有投票方式统一生成：

```json
{
    "issue_id":1,

    "vote_type":"simple_majority",

    "winner":"option_a",

    "options":[

        {
        "name":"方案A",
        "votes":600,
        "percentage":"60%"
        }

    ],

    "status":"passed"

}
```

------

# 八、未来扩展

未来可以增加：

- 二次投票（Runoff Voting）
- 排序选择投票（Ranked Choice Voting）
- 评分投票（Score Voting）
- 权重投票（Weighted Voting）
- 委托投票（Liquid Democracy）
- 匿名加密投票
- 投票审计日志

------

# 文档结束

