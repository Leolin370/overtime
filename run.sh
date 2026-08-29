#!/bin/bash
# Overtime 体坛风云 - 启动脚本
cd "$(dirname "$0")"

echo "========================================="
echo "  Overtime · 体坛风云 启动中"
echo "========================================="

# 检查数据是否存在，不存在则先抓取
if [ ! -f "data/news.json" ]; then
    echo "[初始化] 首次运行，开始抓取初始数据..."
    python3 -c "import scraper; scraper.scrape_all()"
    echo "[初始化] 数据抓取完成"
fi

# 生成早间语音（如果今天还没有）
TODAY=$(date +%Y%m%d)
if [ ! -f "audio/morning_${TODAY}.mp3" ]; then
    echo "[初始化] 生成今日早间语音..."
    python3 -c "
import scraper, tts_engine
briefing = scraper.generate_morning_briefing()
tts_engine.generate_morning_audio(briefing['text'])
"
fi

echo "[启动] 启动 Flask 服务 (端口 5000)..."
echo "[访问] http://localhost:5000"
echo "========================================="

python3 app.py
