# 智竞工大竞赛爬虫副本

本目录是从桌面原项目复制出的开发副本。所有本次修改都在此目录内完成，没有修改 GitHub 仓库。

## 本次新增能力

- 后端新增竞赛爬虫：`backend/contest_crawler.py`
- 爬虫源配置：`backend/contest_sources.json`
- 竞赛列表接口支持搜索、分类筛选和强制刷新：`GET /contests`
- 详情接口返回官网链接、报名时间、地点、条件、材料、赛程、规则等字段：`GET /contest/{id}`
- 小程序竞赛页新增搜索、分类、重新爬取、官网入口
- 小程序详情页新增基础信息、报名条件、日程、规则、官网访问和复制链接
- 新增 `pages/webview/webview` 用于打开竞赛官网

## 启动后端

进入本目录的 `backend` 文件夹后运行：

```powershell
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

如果只是演示竞赛页，也可以不用安装依赖，直接运行标准库演示后端：

```powershell
C:\Users\river\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe backend\dev_server.py
```

如果本机没有配置 `DASHSCOPE_API_KEY`，只会影响 AI 问答接口，不影响竞赛爬虫和竞赛展示。

## 打开小程序

在微信开发者工具中打开这个副本目录：

```text
C:\Users\river\Documents\Codex\2026-05-15\files-mentioned-by-the-user-1146216996\competition-crawler-miniapp
```

前端当前请求地址是：

```text
http://127.0.0.1:8000
```

如果需要真机预览，要把 `pages/contest/contest.js` 和 `pages/detail/detail.js` 里的 `BASE_URL` 改成本机局域网 IP 或正式后端域名。

## 官网跳转注意

微信小程序的 `web-view` 打开外部网站时，正式环境需要在微信公众平台配置业务域名。开发阶段如果遇到域名限制，可以先使用详情页的“复制官网”按钮，把链接复制到浏览器访问。
