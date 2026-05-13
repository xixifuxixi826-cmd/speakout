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
5. 兑换码能开通会员
6. 记录页能显示刚刚生成的内容
7. 手机浏览器访问时没有明显排版错乱
