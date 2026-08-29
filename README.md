# Overtime · 体坛风云

真实数据驱动的全景体育门户应用。

## 功能特性

- **真实体育新闻**：从新浪体育实时抓取，支持点击查看详情和原文跳转
- **运动员百科**：从百度百科抓取真实运动员简介、照片，支持「了解更多」跳转百科
- **早间新闻语音播报**：每日自动生成中文语音早报，前端可播放（edge-tts 合成）
- **联赛积分榜**：抓取真实联赛积分数据
- **我的主队**：三步投票设定主队，首页优先展示该队相关资讯
- **体育巨星盲盒**：从真实运动员库中随机抽取，每日限一次
- **定时+即时数据刷新**：APScheduler 定时任务 + 前端手动刷新按钮

## 技术栈

- **后端**：Python 3 + Flask
- **爬虫**：Playwright (Chromium headless)
- **语音合成**：edge-tts (微软 Edge 在线 TTS)
- **任务调度**：APScheduler
- **前端**：原生 HTML/CSS/JavaScript 单页应用

## 项目结构

```
overtime/
├── app.py              # Flask 主服务 + API 路由
├── scraper.py          # 爬虫模块（新闻/运动员/积分榜）
├── scheduler.py        # 定时任务调度
├── tts_engine.py       # 语音合成引擎
├── requirements.txt    # Python 依赖
├── run.sh              # 启动脚本
├── static/
│   └── index.html      # 前端单页应用
├── data/               # 抓取数据缓存（JSON）
│   ├── news.json
│   ├── athletes.json
│   ├── standings.json
│   └── morning_briefing.json
└── audio/              # 生成的语音文件
    └── morning_YYYYMMDD.mp3
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 启动服务

```bash
# 方式一：使用启动脚本（自动初始化数据）
bash run.sh

# 方式二：手动启动
python3 app.py
```

首次启动会自动抓取初始数据（新闻、运动员、早报语音），约需 3-5 分钟。

### 3. 访问应用

浏览器打开：http://localhost:5000

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/news` | GET | 获取新闻列表，支持 `?category=足球` 筛选 |
| `/api/news/<id>` | GET | 获取单条新闻详情 |
| `/api/athletes` | GET | 获取运动员列表，支持 `?sport=足球` 筛选 |
| `/api/standings` | GET | 获取联赛积分榜 |
| `/api/morning-briefing` | GET | 获取早间简报文本和条目 |
| `/api/morning-audio` | GET | 获取早间语音文件（MP3） |
| `/api/refresh/<task>` | POST | 即时刷新数据，task: news/morning/athletes/standings/all |
| `/api/task-status` | GET | 获取定时任务状态和下次执行时间 |
| `/api/health` | GET | 健康检查 |

## 定时任务

| 任务 | 频率 | 说明 |
|------|------|------|
| 新闻刷新 | 每 30 分钟 | 抓取最新体育新闻 |
| 早间简报 | 每天 07:00 | 生成早报文本 + 语音 |
| 积分榜刷新 | 每天 08:00 | 更新联赛积分数据 |
| 运动员资料 | 每周一 09:00 | 更新运动员百科资料 |

## 数据来源

- **新闻**：新浪体育 (sports.sina.com.cn)
- **运动员资料**：百度百科 (baike.baidu.com)
- **积分榜**：虎扑 NBA (nba.hupu.com) 等

## 注意事项

- 首次运行需下载 Playwright Chromium 浏览器（约 115MB）
- 语音合成使用微软 Edge 在线服务，需联网
- 百度百科图片有防盗链，前端已添加 `no-referrer` meta 标签
- 数据抓取频率受目标网站限制，请勿过于频繁刷新
