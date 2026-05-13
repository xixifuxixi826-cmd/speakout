# 开口模块化 API 设计

## 1. 设计目标

API 不再按页面零散生长，而是按领域和训练模式组织。

目标：
- 支持微信小程序前台
- 支持未来 Web 管理后台
- 支持多训练模式
- 支持语音与 AI 扩展
- 保证 V1 能快速落地

## 2. API 总体分层

建议分成两类：

### 前台业务 API
- `/api/auth/*`
- `/api/user/*`
- `/api/membership/*`
- `/api/training/*`
- `/api/content/*`
- `/api/speech/*`

### 后台管理 API
- `/admin-api/auth/*`
- `/admin-api/dashboard/*`
- `/admin-api/users/*`
- `/admin-api/orders/*`
- `/admin-api/content/*`
- `/admin-api/training/*`
- `/admin-api/config/*`

## 3. 前台 API

## 3.1 认证与用户

### `POST /api/auth/wechat/login`
- 用途：微信 code 登录

### `GET /api/user/profile`
- 用途：获取用户资料、会员状态、剩余额度

### `GET /api/user/home-summary`
- 用途：首页汇总信息

建议返回：
- 今日剩余次数
- 最近一次得分
- 连续训练天数
- 当前可用训练模式

## 3.2 会员

### `GET /api/membership/status`
- 用途：获取会员状态

### `POST /api/membership/create-order`
- 用途：创建会员订单

### `POST /api/membership/payment-notify`
- 用途：微信支付回调

## 3.3 内容中心

### `GET /api/content/modes`
- 用途：获取当前开放的训练模式

### `GET /api/content/list`
- 用途：按类型获取内容列表

查询参数建议：
- `content_type`
- `difficulty_level`
- `domain_tag`
- `content_source_type`
- `page`
- `page_size`

### `GET /api/content/detail/{content_uid}`
- 用途：获取某条内容详情

适用：
- 辩题详情
- 演讲稿详情
- 训练素材详情

### `POST /api/content/generate`
- 用途：按条件动态生成训练内容

请求体建议：

```json
{
  "content_type": "word",
  "difficulty_level": "beginner",
  "domain_tag": "daily_life",
  "count": 16
}
```

说明：
- 该接口未来可用于“按领域动态生成词语”
- 是否对普通用户开放，可由会员策略和模式配置控制

## 3.4 训练引擎

### `POST /api/training/session/create`
- 用途：创建训练会话

请求体建议：

```json
{
  "mode": "card_association",
  "difficulty_level": "beginner",
  "content_source_strategy": "preset"
}
```

`content_source_strategy` 建议支持：
- `preset`
- `ai_generated`
- `mixed`

### `GET /api/training/session/{session_uid}`
- 用途：获取训练会话详情

### `POST /api/training/session/{session_uid}/start`
- 用途：开始训练

### `POST /api/training/session/{session_uid}/submit`
- 用途：提交训练内容

### `GET /api/training/session/{session_uid}/feedback`
- 用途：获取训练反馈

### `GET /api/training/history`
- 用途：获取历史记录列表

查询参数：
- `mode`
- `page`
- `page_size`

### `GET /api/training/history/{session_uid}`
- 用途：获取历史记录详情

## 3.5 卡片训练模式 API

### `POST /api/training/modes/card-association/init-round`
- 用途：初始化卡片轮次

建议支持：
- 预置词库抽取
- AI 动态生成后填充
- 混合模式填充

### `POST /api/training/modes/card-association/flip-card`
- 用途：翻开单张卡片

### `POST /api/training/modes/card-association/select-cards`
- 用途：提交本次选中的两张卡

### `POST /api/training/modes/card-association/next-round`
- 用途：进入下一轮

## 3.6 辩论训练模式 API

### `POST /api/training/modes/debate/match-topic`
- 用途：获取辩题

### `POST /api/training/modes/debate/start-round`
- 用途：开始 AI 辩论

### `POST /api/training/modes/debate/reply`
- 用途：用户回复一轮辩论

### `GET /api/training/modes/debate/result/{session_uid}`
- 用途：获取辩论结果

## 3.7 演讲训练模式 API

### `GET /api/training/modes/speech/scripts`
- 用途：获取演讲稿列表

### `GET /api/training/modes/speech/script/{content_uid}`
- 用途：获取演讲稿详情

### `POST /api/training/modes/speech/start`
- 用途：开始朗读或模仿训练

### `POST /api/training/modes/speech/submit`
- 用途：提交演讲训练内容

### `GET /api/training/modes/speech/result/{session_uid}`
- 用途：获取演讲训练结果

## 3.8 语音能力 API

### `POST /api/speech/asr`
- 用途：语音转文字

### `POST /api/speech/tts`
- 用途：文本转语音

### `POST /api/speech/analyze`
- 用途：语音分析

### `GET /api/speech/task/{task_uid}`
- 用途：轮询语音任务结果

## 4. 管理后台 API

## 4.1 后台认证

### `POST /admin-api/auth/login`
- 用途：后台登录

### `POST /admin-api/auth/logout`
- 用途：后台退出

### `GET /admin-api/auth/me`
- 用途：当前后台账号信息

## 4.2 仪表盘

### `GET /admin-api/dashboard/overview`
- 用途：获取核心经营看板

建议返回：
- 注册用户数
- DAU
- 训练完成数
- 付费人数
- 今日营收

### `GET /admin-api/dashboard/training-trend`
- 用途：训练趋势

### `GET /admin-api/dashboard/revenue-trend`
- 用途：收入趋势

## 4.3 用户管理

### `GET /admin-api/users`
- 用途：用户列表

筛选建议：
- 注册时间
- 是否会员
- 最近活跃时间
- 训练次数

### `GET /admin-api/users/{user_uid}`
- 用途：用户详情

### `GET /admin-api/users/{user_uid}/trainings`
- 用途：用户训练记录

### `POST /admin-api/users/{user_uid}/status`
- 用途：禁用或恢复用户

## 4.4 订单与付费

### `GET /admin-api/orders`
- 用途：订单列表

### `GET /admin-api/orders/{order_no}`
- 用途：订单详情

### `GET /admin-api/orders/stats`
- 用途：订单统计

## 4.5 内容管理

### `GET /admin-api/content/items`
- 用途：内容列表

### `POST /admin-api/content/items`
- 用途：创建内容

### `PUT /admin-api/content/items/{content_uid}`
- 用途：更新内容

### `POST /admin-api/content/items/{content_uid}/publish`
- 用途：发布内容

### `POST /admin-api/content/items/{content_uid}/offline`
- 用途：下线内容

### `GET /admin-api/content/bundles`
- 用途：内容包列表

### `POST /admin-api/content/bundles`
- 用途：创建内容包

### `POST /admin-api/content/generation-tasks`
- 用途：后台发起 AI 内容生成任务

### `GET /admin-api/content/generation-tasks`
- 用途：查看内容生成任务列表

### `POST /admin-api/content/generation-tasks/{task_uid}/publish`
- 用途：将生成结果发布到内容池

## 4.6 训练分析

### `GET /admin-api/training/sessions`
- 用途：训练会话列表

### `GET /admin-api/training/sessions/{session_uid}`
- 用途：训练会话详情

### `GET /admin-api/training/mode-stats`
- 用途：不同训练模式统计

### `GET /admin-api/training/difficulty-stats`
- 用途：不同难度统计

## 4.7 配置中心

### `GET /admin-api/config/modes`
- 用途：获取训练模式配置

### `PUT /admin-api/config/modes/{mode}`
- 用途：更新模式配置

### `GET /admin-api/config/ai-prompts`
- 用途：获取 Prompt 配置

建议支持查询参数：
- `business_domain`
- `mode`
- `status`

建议返回：
- Prompt 基础信息
- 当前生效版本
- 绑定模型
- 最近发布时间

### `GET /admin-api/config/ai-prompts/{prompt_key}`
- 用途：获取单个 Prompt 详情与版本列表

### `PUT /admin-api/config/ai-prompts/{prompt_key}`
- 用途：更新 Prompt 配置

### `POST /admin-api/config/ai-prompts`
- 用途：新建 Prompt 模板

### `POST /admin-api/config/ai-prompts/{prompt_key}/versions`
- 用途：创建新的 Prompt 版本草稿

### `POST /admin-api/config/ai-prompts/{prompt_key}/versions/{version_no}/publish`
- 用途：发布指定 Prompt 版本

### `POST /admin-api/config/ai-prompts/{prompt_key}/versions/{version_no}/test`
- 用途：用样例输入测试当前 Prompt 输出

请求体建议：

```json
{
  "selected_words": ["松弛", "锋利"],
  "user_text": "我的观点是，松弛是一种锋利。真正稳定的人，不需要靠音量证明自己。",
  "membership_level": "free",
  "provider_code": "openai",
  "model_name": "gpt-4.1-mini"
}
```

建议返回：
- 原始响应
- 结构化解析结果
- 是否已保存为测试记录

### `GET /admin-api/config/ai-prompts/{prompt_key}/test-records`
- 用途：查看某个 Prompt 的测试记录

建议支持查询参数：
- `version_no`
- `provider_code`
- `page`
- `page_size`

### `GET /admin-api/config/ai-providers`
- 用途：查看 AI 服务商与模型配置

### `PUT /admin-api/config/ai-providers/{provider_code}`
- 用途：更新 AI 服务商配置

## 4.8 AI 评分作业

### `GET /admin-api/ai-feedback/jobs`
- 用途：查看 AI 评分任务列表

筛选建议：
- `job_status`
- `provider_code`
- `mode`
- `created_at`

### `GET /admin-api/ai-feedback/jobs/{job_uid}`
- 用途：查看单个评分任务详情

建议返回：
- 会话信息
- 所选词语
- 提交原文
- 请求 Prompt
- 请求参数
- 模型响应
- 解析后的评分结果
- 错误信息

### `POST /admin-api/ai-feedback/jobs/{job_uid}/retry`
- 用途：重试 AI 评分任务

## 5. 通用响应规范

建议统一响应结构：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

分页返回建议：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [],
    "page": 1,
    "page_size": 20,
    "total": 100,
    "has_more": true
  }
}
```

## 6. 模式扩展原则

今后新增训练模式时：
- 主流程尽量复用 `/api/training/session/*`
- 模式专用能力放在 `/api/training/modes/{mode}/*`
- 不要在根路径上不断堆新接口

今后新增内容来源时：
- 内容查询仍然复用 `/api/content/*`
- 生成任务统一进入 `/api/content/generate` 或后台生成任务 API
- 不要为“AI 词库”“领域词库”再各建一套独立内容体系

这样新增一个新模式时，不会影响已有模式。

## 7. V1 最低接口范围

V1 先做这些就够：
- `/api/auth/wechat/login`
- `/api/user/profile`
- `/api/membership/status`
- `/api/membership/create-order`
- `/api/training/session/create`
- `/api/training/modes/card-association/init-round`
- `/api/training/modes/card-association/flip-card`
- `/api/training/session/{session_uid}/submit`
- `/api/training/session/{session_uid}/feedback`
- `/api/training/history`
- `/api/training/history/{session_uid}`

后台 V1 最低可做：
- `/admin-api/auth/login`
- `/admin-api/dashboard/overview`
- `/admin-api/users`
- `/admin-api/orders`
- `/admin-api/content/items`
- `/admin-api/config/ai-prompts`
- `/admin-api/config/ai-prompts/{prompt_key}/versions/{version_no}/publish`
- `/admin-api/config/ai-prompts/{prompt_key}/test-records`
- `/admin-api/ai-feedback/jobs`

## 8. 最重要的 API 判断

如果现在 API 还只是围绕“卡片翻牌页”设计，后面一定重构。

如果现在按：
- 用户域
- 内容域
- 训练域
- 语音域
- 支付域
- 后台域

来组织，未来增加辩论和演讲训练时，就能很顺。
