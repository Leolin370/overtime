"""
Overtime 体育门户 - Flask API 服务
提供数据API、静态文件服务、即时刷新接口
"""
import os
import json
import sys
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, send_file, Response

# 确保模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scraper
import tts_engine
import scheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
AUDIO_DIR = os.path.join(BASE_DIR, 'audio')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='')


def _load_data(filename, default=None):
    """加载数据文件"""
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}


# ============================================================
# 页面路由
# ============================================================
@app.route('/')
def index():
    """首页 - 前端单页应用"""
    return send_from_directory(STATIC_DIR, 'index.html')


# ============================================================
# 数据API
# ============================================================
@app.route('/api/news')
def get_news():
    """获取新闻列表"""
    category = request.args.get('category', '')
    data = _load_data('news.json', {'articles': []})
    articles = data.get('articles', [])
    
    if category:
        articles = [a for a in articles if a.get('category') == category]
    
    return jsonify({
        'success': True,
        'source': data.get('source', ''),
        'scraped_at': data.get('scraped_at', ''),
        'count': len(articles),
        'articles': articles
    })


@app.route('/api/news/<news_id>')
def get_news_detail(news_id):
    """获取单条新闻详情"""
    data = _load_data('news.json', {'articles': []})
    for a in data.get('articles', []):
        if a.get('id') == news_id:
            return jsonify({'success': True, 'article': a})
    return jsonify({'success': False, 'message': '新闻不存在'}), 404


@app.route('/api/athletes')
def get_athletes():
    """获取运动员列表"""
    sport = request.args.get('sport', '')
    data = _load_data('athletes.json', {'athletes': []})
    athletes = data.get('athletes', [])
    
    if sport:
        athletes = [a for a in athletes if a.get('sport') == sport]
    
    return jsonify({
        'success': True,
        'source': data.get('source', ''),
        'scraped_at': data.get('scraped_at', ''),
        'count': len(athletes),
        'athletes': athletes
    })


@app.route('/api/standings')
def get_standings():
    """获取联赛积分榜"""
    sport = request.args.get('sport', '')
    data = _load_data('standings.json', {'standings': {}})
    standings = data.get('standings', {})
    
    if sport:
        standings = {sport: standings.get(sport, {})}
    
    return jsonify({
        'success': True,
        'scraped_at': data.get('scraped_at', ''),
        'standings': standings
    })


@app.route('/api/morning-briefing')
def get_morning_briefing():
    """获取早间简报"""
    data = _load_data('morning_briefing.json', {})
    audio_path = tts_engine.get_latest_morning_audio()
    
    return jsonify({
        'success': True,
        'date': data.get('date', ''),
        'text': data.get('text', ''),
        'articles': data.get('articles', []),
        'generated_at': data.get('generated_at', ''),
        'audio_available': audio_path is not None,
        'audio_url': '/api/morning-audio' if audio_path else None
    })


@app.route('/api/morning-audio')
def get_morning_audio():
    """获取早间语音文件"""
    audio_path = tts_engine.get_latest_morning_audio()
    if not audio_path:
        return jsonify({'success': False, 'message': '语音文件不存在'}), 404
    return send_file(audio_path, mimetype='audio/mpeg')


# ============================================================
# 即时刷新API
# ============================================================
@app.route('/api/refresh/<task>', methods=['POST'])
def refresh_data(task):
    """
    即时刷新数据
    task: news / morning / athletes / standings / all
    """
    valid_tasks = ['news', 'morning', 'athletes', 'standings', 'all']
    if task not in valid_tasks:
        return jsonify({'success': False, 'message': f'无效任务，可选: {valid_tasks}'}), 400
    
    result = scheduler.trigger_task(task)
    return jsonify(result)


@app.route('/api/task-status')
def task_status():
    """获取任务执行状态"""
    status = scheduler.get_task_status()
    jobs = scheduler.get_scheduled_jobs()
    return jsonify({
        'success': True,
        'tasks': status,
        'scheduled_jobs': jobs
    })


# ============================================================
# 系统信息
# ============================================================
@app.route('/api/health')
def health():
    """健康检查"""
    return jsonify({
        'success': True,
        'app': 'Overtime 体坛风云',
        'version': '2.0',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'scheduler_running': scheduler._scheduler is not None and scheduler._scheduler.running
    })


# ============================================================
# 启动
# ============================================================
def ensure_data():
    """确保数据目录和初始数据存在"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    
    # 检查是否有数据，没有则执行首次抓取
    news_path = os.path.join(DATA_DIR, 'news.json')
    if not os.path.exists(news_path):
        print("[启动] 首次运行，执行初始数据抓取...")
        try:
            scraper.scrape_all()
        except Exception as e:
            print(f"[启动] 初始抓取失败: {e}")


if __name__ == '__main__':
    ensure_data()
    scheduler.start_scheduler()
    print("\n" + "=" * 50)
    print("Overtime 体坛风云 - 服务启动")
    print("访问地址: http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
