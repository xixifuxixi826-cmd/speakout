# 表达高手

“表达高手”是一个围绕词语联想表达训练的项目，当前以 H5 作为主前端形态，同时保留微信小程序原型分支，并共用一套 Python 后端与 SQLite 数据库。

## 当前项目结构

- `backend/`
  Python 后端、AI 评分接入、SQLite 数据库、后台接口
- `代码原型/biaodagaoshou-h5/`
  当前主推进的 H5 前端
- `代码原型/开口-miniapp-prototype/`
  保留的小程序原型分支
- `deploy/`
  Nginx、systemd、正式部署说明
- `低保真原型/`
  Pencil 等原型资产
- `文章素材/`
  对外内容和图示素材

## 当前主链路

1. 用户进入 H5
2. 选择 4×4 词卡中的两个词
3. 进入 30 秒构思
4. 进入 2 分钟表达
5. 提交给教练点评
6. 查看评分、思考路径和参考表达
7. 注册保存记录 / 输入兑换码开通会员

## 本地启动

启动后端：

```bash
python3 /Users/lisa888/Documents/表达高手/backend/server.py
```

启动 H5 静态服务：

```bash
cd /Users/lisa888/Documents/表达高手/代码原型/biaodagaoshou-h5
python3 -m http.server 8088 --bind 127.0.0.1
```

访问地址：

- H5：`http://127.0.0.1:8088/`
- 后端健康检查：`http://127.0.0.1:8765/health`

## GitHub 准备说明

以下内容不会进入 GitHub：

- `backend/runtime_config.json`
- `backend/data/`

原因是这里包含本地运行配置、真实 API key 和数据库文件。仓库里已经提供安全模板文件：

- `backend/runtime_config.example.json`

## 正式部署

正式上线相关文件见：

```text
/Users/lisa888/Documents/表达高手/deploy
```

推荐上线形态：

- H5 前端 + Python 后端部署在同一台服务器
- 使用 Nginx 反向代理
- 通过 Cloudflare 做域名解析、HTTPS 和代理层
