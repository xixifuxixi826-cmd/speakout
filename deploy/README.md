# 表达高手部署说明

这套部署面向当前的正式目标：

- H5 对外提供可点击链接
- 后端提供真实 API
- 使用同一个域名对外暴露
- 通过 Nginx 反向代理把 H5 和 `/api`、`/admin-api` 收到同一个站点下

## 1. 推荐上线形态

建议使用：

- 一台公网 Linux 服务器
- 一个域名
- Nginx
- Python 3.11+

对外访问形态建议是：

- `https://你的域名/` -> H5
- `https://你的域名/api/...` -> 后端 API
- `https://你的域名/admin-api/...` -> 后台 API

这样前端不需要再暴露 `:8765` 端口，也更适合后续发到小红书。

## 2. 目录建议

服务器上可以放成这样：

```text
/srv/speakout/
  backend/
  h5/
  logs/
```

其中：

- `backend/` 放 `/Users/lisa888/Documents/表达高手/backend`
- `h5/` 放 `/Users/lisa888/Documents/表达高手/代码原型/biaodagaoshou-h5`

## 3. 后端启动

后端可以直接运行：

```bash
python3 /srv/speakout/backend/server.py
```

默认监听：

```text
0.0.0.0:8765
```

### Railway 数据持久化要求

如果后端部署在 Railway，必须为 backend service 挂载持久卷。不要把 SQLite 数据库放在 `/tmp` 或容器临时目录里，否则每次部署或重启都可能清空用户、订单、Prompt 和运行配置。

Railway 推荐配置：

```bash
npx @railway/cli volume add --service <backend-service> --mount-path /data --json
npx @railway/cli variable set APP_DATA_DIR=/data --service <backend-service> --skip-deploys --json
```

配置完成后，后端数据库路径应为：

```text
/data/express_master.db
```

当前后端已经加了启动保护：在 Railway 环境中，如果没有 `APP_DATA_DIR`，并且没有可用的非 `/tmp` 持久卷路径，服务会拒绝启动。这样可以避免悄悄创建一套空库上线。

## 4. Nginx 代理

参考：

- [nginx.speakout.conf](./nginx.speakout.conf)

这个配置会：

- 直接托管 H5 静态文件
- 把 `/api/` 和 `/admin-api/` 转发到 `127.0.0.1:8765`
- 保留 `X-Client-Id`

## 5. systemd 守护

参考：

- [speakout-backend.service](./speakout-backend.service)

部署后可以用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable speakout-backend
sudo systemctl start speakout-backend
sudo systemctl status speakout-backend
```

## 6. 今晚如果要发小红书，最少需要什么

你至少需要：

1. 一台公网服务器
2. 一个域名
3. 域名解析到服务器
4. Nginx 把站点跑起来
5. HTTPS 证书

没有公网域名时：

- 不能把本地 `127.0.0.1`
- 不能把局域网 `192.168.x.x`

直接发给小红书用户。

## 7. 发布前检查

发布前至少检查：

1. H5 首页能打开
2. 训练主链能走通
3. 教练点评能返回
4. 注册能成功
5. 后台概览的注册用户、权益用户、付费用户口径正确
6. 记录页能显示刚刚生成的内容
7. 手机浏览器访问时没有明显排版错乱
8. Railway 线上日志里数据库路径是 `/data/express_master.db`，不是 `/tmp/...`
9. 重新部署后，后台 Prompt、模型配置、用户列表不会被重置
