# 表达高手后端与 AI 评分接入设计

## 1. 设计目标

这版设计用于把“表达高手”从前台原型推进到可开发状态，重点解决四件事：

- 小程序训练链路如何落到后端服务
- 数据库如何支撑训练、会员、历史和 AI 反馈
- AI 评分如何稳定接入并支持重试
- 后台如何管理 AI 评分 Prompt，而不是把 Prompt 写死在代码里

## 2. 后端模块划分

建议继续采用模块化单体：

- `auth`
  微信登录、会话鉴权、后台登录
- `user`
  用户资料、会员状态、每日额度
- `content`
  词库内容、标签、生成任务、审核发布
- `training`
  训练会话、卡片轮次、训练提交、历史记录
- `speech`
  ASR 转写任务与音频元信息
- `ai`
  AI 评分请求、Prompt 管理、评分任务重试
- `membership`
  会员订单、支付回调、权益生效
- `admin`
  仪表盘、用户管理、订单管理、内容管理、配置管理

## 3. 数据库设计重点

现有主线仍然围绕：

- `training_session`
- `training_submission`
- `training_feedback`
- `card_round`
- `card_instance`

这次新增的 AI 评分核心表：

### 3.1 `ai_prompt_template`

用途：
- 定义一个 Prompt 的业务身份
- 例如：`card_association_feedback_v1`

关键字段：
- `prompt_key`
- `business_domain`
- `mode`
- `current_version_no`
- `status`

### 3.2 `ai_prompt_version`

用途：
- 记录 Prompt 的每个版本内容
- 支持草稿、测试、发布、回滚

关键字段：
- `system_prompt`
- `user_prompt_template`
- `output_schema_json`
- `model_name`
- `temperature`
- `max_output_tokens`
- `prompt_status`

### 3.3 `ai_provider_config`

用途：
- 配置 AI 服务商与模型
- 不把密钥和模型硬编码在业务逻辑里

关键字段：
- `provider_code`
- `api_base_url`
- `model_name`
- `secret_ref`
- `timeout_ms`
- `is_default`

### 3.4 `ai_feedback_job`

用途：
- 把每一次 AI 评分调用变成可追踪任务
- 便于失败重试、后台排查和模型效果对比

关键字段：
- `session_id`
- `submission_id`
- `prompt_template_id`
- `prompt_version_id`
- `provider_code`
- `model_name`
- `job_status`
- `request_payload_json`
- `response_payload_json`
- `error_message`
- `retried_count`

### 3.5 `ai_prompt_test_record`

用途：
- 保存后台每次试跑 Prompt 的输入、输出和解析结果
- 让产品、运营和算法同学能回看“这版 Prompt 到底试过什么”

关键字段：
- `prompt_template_id`
- `prompt_version_id`
- `provider_code`
- `model_name`
- `input_payload_json`
- `output_payload_json`
- `parsed_result_json`
- `test_status`

### 3.6 `training_feedback` 增补字段

建议记录：
- 使用了哪个 Prompt 模板
- 使用了哪个 Prompt 版本
- 最终走了哪个模型
- 返回的元信息

这样后台查看一条评分记录时，能直接知道：
- 当时到底用了哪版 Prompt
- 用的是哪个模型
- 为什么会打出这样的分数

## 4. 训练主链路的后端流程

### 4.1 用户开始训练

1. 小程序调用 `POST /api/training/session/create`
2. 后端校验会员状态和当日免费额度
3. 创建 `training_session`
4. 创建 `card_round`
5. 从词库抽取 16 个形容词，写入 `card_instance`

### 4.2 用户提交表达

1. 小程序调用 `POST /api/training/session/{session_uid}/submit`
2. 后端保存 `training_submission`
3. 将本次所选 2 张卡状态更新为 `used`
4. 创建 `ai_feedback_job`
5. 调用 AI 服务进行评分
6. 解析结果并写入 `training_feedback`

### 4.3 AI 评分失败

1. `ai_feedback_job.job_status = failed`
2. 保留 `training_submission`
3. 小程序可提示“稍后重试”
4. 后台支持人工重试该任务

## 5. AI 评分接入设计

## 5.1 接入原则

- 不把 Prompt 写死在代码里
- 不让页面直接调用第三方 AI API
- 所有评分统一走后端 `ai` 模块
- 评分输出必须按 schema 解析

## 5.2 推荐调用链

```text
小程序提交表达
  -> training 模块落库 submission
  -> ai 模块读取当前生效 prompt
  -> 组装请求 payload
  -> 调用 AI Provider API
  -> 解析结构化评分结果
  -> 回写 training_feedback
  -> 返回前台可展示内容
```

## 5.3 Prompt 变量建议

评分 Prompt 不建议写死文本，而建议支持变量注入：

- `selected_words`
- `user_text`
- `mode`
- `feedback_schema`
- `membership_level`
- `scoring_rules`

示例 user prompt 模板：

```text
你正在评估一次表达训练。

训练模式：{{mode}}
选中词语：{{selected_words}}
用户表达：{{user_text}}

请重点判断：
1. 用户是否先提出了一个明确观点
2. 是否使用了“A是B”或“A是一种B”的结构，或者等价判断结构
3. 是否解释了这个观点为什么成立
4. 语言是否具体、自然、可理解

请严格按 schema 返回 JSON。
```

## 5.4 评分输出 schema 建议

```json
{
  "total_score": 84,
  "summary": "观点成立，解释方向清楚，但场景还不够具体。",
  "dimensions": [
    {
      "label": "观点明确度",
      "score": 88,
      "note": "开头已经提出判断。"
    },
    {
      "label": "合理性解释",
      "score": 82,
      "note": "解释成立，但论据还可以更具体。"
    },
    {
      "label": "表达完整度",
      "score": 81,
      "note": "结尾可以补一句总结。"
    }
  ],
  "suggestions": [
    "先把判断句说满。",
    "补一个具体场景来支撑这句话。",
    "结尾再补一句你的理解。"
  ],
  "rewrite": "热烈是一种松弛，因为真正稳定的人，反而能把情绪放得开。"
}
```

## 6. 后台 Prompt 管理设计

后台至少要支持以下能力：

### 6.1 Prompt 列表

可查看：
- Prompt 名称
- 业务域
- 训练模式
- 当前生效版本
- 绑定模型
- 更新时间

### 6.2 Prompt 编辑

可编辑：
- System Prompt
- User Prompt Template
- 输出 Schema
- 评分维度说明
- 模型参数
- 温度
- 最大输出长度

### 6.3 Prompt 版本管理

要支持：
- 新建草稿版本
- 测试版本输出
- 发布为当前线上版本
- 回滚到旧版本

### 6.4 Prompt 测试台

后台最好提供一个“样例输入测试”区域，运营或产品可以：
- 输入两个词语
- 输入一段表达文本
- 选择 Provider 和 Model
- 选择 free / member 用户身份
- 点击测试
- 直接看到模型返回结果

这一步很关键，因为 AI 评分 Prompt 的调优会非常频繁。

### 6.5 Prompt 管理页字段建议

Prompt 列表页建议直接展示：
- Prompt Key
- Prompt 名称
- 业务域
- 训练模式
- 当前线上版本
- 当前绑定模型
- 最近测试结果
- 更新时间

Prompt 详情页建议拆成四个区块：
- 基础信息
  Prompt 名称、业务域、模式、说明
- 版本区
  版本号、状态、变更说明、发布时间、发布人
- 编辑区
  System Prompt、User Prompt Template、输出 Schema、参数配置
- 测试区
  样例输入、原始响应、解析结果、保存测试记录按钮

### 6.6 AI 评分任务页建议

列表页建议支持：
- 按任务状态筛选
- 按 Prompt 版本筛选
- 按模型筛选
- 按用户或会话检索

详情页建议显示：
- 所属用户 / 会话 / 提交时间
- 所选两个词
- 用户转写文本
- Prompt 版本
- Provider / Model
- 请求 Payload
- 原始响应
- 解析后的评分结果
- 失败原因与重试记录

## 7. 需要补充的后台页面

在现有最小后台之外，建议新增：

- `AI Prompt 管理`
- `AI 评分任务列表`
- `AI 评分任务详情`

其中任务详情页至少能看到：
- 关联的训练会话
- 关联的提交文本
- 使用的 Prompt 版本
- 请求 Payload
- 原始响应
- 解析结果
- 重试按钮

## 8. API 补充建议

前台：
- `POST /api/training/session/{session_uid}/submit`
- `GET /api/training/session/{session_uid}/feedback`

后台：
- `GET /admin-api/config/ai-prompts`
- `GET /admin-api/config/ai-prompts/{prompt_key}`
- `POST /admin-api/config/ai-prompts/{prompt_key}/versions`
- `POST /admin-api/config/ai-prompts/{prompt_key}/versions/{version_no}/publish`
- `POST /admin-api/config/ai-prompts/{prompt_key}/versions/{version_no}/test`
- `GET /admin-api/config/ai-prompts/{prompt_key}/test-records`
- `GET /admin-api/ai-feedback/jobs`
- `GET /admin-api/ai-feedback/jobs/{job_uid}`
- `POST /admin-api/ai-feedback/jobs/{job_uid}/retry`

## 9. 首发建议

如果现在立刻开始后端实现，建议顺序是：

1. 先补 `ai_prompt_template / ai_prompt_version / ai_feedback_job`
2. 先让卡片训练提交能走通一版 AI 评分
3. 后台先做 Prompt 列表、编辑、发布、测试
4. 接着补 AI 评分任务列表、详情、重试
5. 后续再补多模型切换和更复杂的审核/AB 测试

## 10. 结论

“表达高手”的 AI 评分能力，不能只是“接一个模型接口”。

真正要设计的是：
- 训练数据怎么落
- Prompt 怎么版本化
- 评分任务怎么追踪
- 后台怎么让 Prompt 可运营

只有这样，AI 评分这件事才会从一次性 demo，变成能持续迭代的正式产品能力。
