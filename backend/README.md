# 表达高手后端

这个目录提供一套零依赖 Python 后端，当前既可用于本地开发，也可用于轻量正式部署：

- SQLite 数据库
- 训练轮次与卡片状态持久化
- 历史记录持久化
- 会员开通写库
- 后台用户 / 订单 / 内容 / Prompt / AI 任务读取
- AI 评分服务层

## 1. 启动方式

```bash
python3 /Users/lisa888/Documents/表达高手/backend/server.py
```

本地启动后服务地址：

```text
http://127.0.0.1:8765
```

数据库文件会自动创建在：

```text
/Users/lisa888/Documents/表达高手/backend/data/express_master.db
```

## 2. 小程序与后台的连接方式

当前前端可以这样连接：

- H5 前端：
  `/Users/lisa888/Documents/表达高手/代码原型/biaodagaoshou-h5`
- 小程序前端：
  `/Users/lisa888/Documents/表达高手/代码原型/开口-miniapp-prototype`
- 后台原型：
  `/Users/lisa888/Documents/表达高手/代码原型/开口-miniapp-prototype/admin/index.html`

只要先把后端启动起来，再重新编译小程序、刷新后台页面，就会读真实 SQLite 数据。

## 3. AI 评分说明

当前服务有两种工作方式：

### 默认模式

如果没有配置模型环境变量，会使用本地评分器：

- 可以真实落库
- 可以真实生成历史记录和 AI 任务记录
- 方便你先跑通完整体验

### 模型 API 模式

如果你已经有一个兼容的聊天补全接口，可以配置：

```bash
export MODEL_API_URL='你的完整接口地址'
export MODEL_API_KEY='你的密钥'
export MODEL_API_MODEL='你的模型名'
export MODEL_PROVIDER_CODE='你的服务商标识'
python3 /Users/lisa888/Documents/表达高手/backend/server.py
```

服务会优先请求这个模型接口；如果请求失败，会退回本地评分器，避免前台链路直接中断。

## 4. 当前主要接口

- `GET /health`
- `GET /api/user/home-summary`
- `GET /api/user/profile`
- `POST /api/training/session/create`
- `GET /api/training/session/current`
- `POST /api/training/session/current/cards/toggle`
- `POST /api/training/session/current/draft`
- `POST /api/training/session/current/submit`
- `GET /api/training/session/current/feedback`
- `POST /api/training/session/current/continue`
- `GET /api/training/history`
- `GET /api/training/history/{id}`
- `POST /api/membership/activate`
- `GET /admin-api/dashboard/overview`
- `GET /admin-api/users`
- `GET /admin-api/orders`
- `GET /admin-api/content/words`
- `GET /admin-api/config/ai-prompts`
- `GET /admin-api/ai-feedback/jobs`
- `POST /admin-api/config/ai-prompts/test`

## 5. 当前限制

当前还需要注意这些限制：

- 当前是轻量用户体系，不是正式账号系统
- 会员支付还是本地模拟开通，但会真实写数据库
- 录音转写仍然是前端生成文本片段，不是真实 ASR
- 真模型调用依赖你提供可用的接口地址和密钥

## 6. 正式部署

如果你要把它发成可点击公网链接，请看：

```text
/Users/lisa888/Documents/表达高手/deploy
```
