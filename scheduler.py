"""
Overtime 体育门户 - 定时任务调度模块
使用 APScheduler 管理定时抓取和即时刷新任务
"""
import os
import json
import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import scraper
import tts_engine

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# 全局调度器
_scheduler = None
_scheduler_lock = threading.Lock()
_task_status = {}  # 任务执行状态记录


def _record_task(task_name, status, detail=''):
    """记录任务执行状态"""
    _task_status[task_name] = {
        'name': task_name,
        'status': status,
        'last_run': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'detail': detail
    }
    # 保存状态到文件
    status_path = os.path.join(DATA_DIR, 'task_status.json')
    with open(status_path, 'w', encoding='utf-8') as f:
        json.dump(_task_status, f, ensure_ascii=False, indent=2)


def _task_news_refresh():
    """定时任务：刷新新闻"""
    print(f"[调度器] 执行新闻刷新任务 - {datetime.now()}")
    try:
        result = scraper.scrape_sina_news(max_articles=15)
        _record_task('news_refresh', 'success', f'抓取{result.get("count", 0)}条新闻')
    except Exception as e:
        _record_task('news_refresh', 'failed', str(e))
        print(f"[调度器] 新闻刷新失败: {e}")


def _task_morning_briefing():
    """定时任务：生成早间新闻简报+语音"""
    print(f"[调度器] 执行早间简报任务 - {datetime.now()}")
    try:
        # 先刷新新闻
        scraper.scrape_sina_news(max_articles=12)
        # 生成简报文本
        briefing = scraper.generate_morning_briefing()
        # 生成语音
        audio_path = tts_engine.generate_morning_audio(briefing['text'])
        _record_task('morning_briefing', 'success', 
                     f'简报{len(briefing.get("articles", []))}条, 音频: {os.path.basename(audio_path) if audio_path else "失败"}')
    except Exception as e:
        _record_task('morning_briefing', 'failed', str(e))
        print(f"[调度器] 早间简报失败: {e}")


def _task_athletes_refresh():
    """定时任务：刷新运动员资料（每周一次）"""
    print(f"[调度器] 执行运动员资料刷新 - {datetime.now()}")
    try:
        result = scraper.scrape_athletes()
        _record_task('athletes_refresh', 'success', f'更新{result.get("count", 0)}名运动员')
    except Exception as e:
        _record_task('athletes_refresh', 'failed', str(e))


def _task_standings_refresh():
    """定时任务：刷新积分榜（每日一次）"""
    print(f"[调度器] 执行积分榜刷新 - {datetime.now()}")
    try:
        scraper.scrape_standings()
        _record_task('standings_refresh', 'success', '积分榜已更新')
    except Exception as e:
        _record_task('standings_refresh', 'failed', str(e))


def start_scheduler():
    """启动定时调度器"""
    global _scheduler
    with _scheduler_lock:
        if _scheduler and _scheduler.running:
            print("[调度器] 已在运行")
            return _scheduler
        
        _scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        
        # 新闻刷新：每30分钟一次
        _scheduler.add_job(
            _task_news_refresh,
            trigger=IntervalTrigger(minutes=30),
            id='news_refresh',
            name='新闻刷新',
            replace_existing=True
        )
        
        # 早间简报：每天早上7:00
        _scheduler.add_job(
            _task_morning_briefing,
            trigger=CronTrigger(hour=7, minute=0, timezone='Asia/Shanghai'),
            id='morning_briefing',
            name='早间简报',
            replace_existing=True
        )
        
        # 积分榜：每天早上8:00
        _scheduler.add_job(
            _task_standings_refresh,
            trigger=CronTrigger(hour=8, minute=0, timezone='Asia/Shanghai'),
            id='standings_refresh',
            name='积分榜刷新',
            replace_existing=True
        )
        
        # 运动员资料：每周一早上9:00
        _scheduler.add_job(
            _task_athletes_refresh,
            trigger=CronTrigger(day_of_week='mon', hour=9, minute=0, timezone='Asia/Shanghai'),
            id='athletes_refresh',
            name='运动员资料刷新',
            replace_existing=True
        )
        
        _scheduler.start()
        print("[调度器] 已启动")
        print("  - 新闻刷新: 每30分钟")
        print("  - 早间简报: 每天07:00")
        print("  - 积分榜: 每天08:00")
        print("  - 运动员资料: 每周一09:00")
        
        return _scheduler


def stop_scheduler():
    """停止调度器"""
    global _scheduler
    with _scheduler_lock:
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
            _scheduler = None
            print("[调度器] 已停止")


def get_task_status():
    """获取所有任务状态"""
    # 从文件加载
    status_path = os.path.join(DATA_DIR, 'task_status.json')
    if os.path.exists(status_path):
        with open(status_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return _task_status


def trigger_task(task_name):
    """
    即时触发任务（手动刷新）
    :param task_name: 任务名: news / morning / athletes / standings / all
    :return: 执行结果
    """
    print(f"[即时任务] 触发: {task_name} - {datetime.now()}")
    
    task_map = {
        'news': _task_news_refresh,
        'morning': _task_morning_briefing,
        'athletes': _task_athletes_refresh,
        'standings': _task_standings_refresh,
    }
    
    if task_name == 'all':
        # 全量抓取
        try:
            scraper.scrape_all()
            # 生成早间语音
            briefing = scraper.generate_morning_briefing()
            tts_engine.generate_morning_audio(briefing['text'])
            _record_task('manual_all', 'success', '手动全量刷新完成')
            return {'status': 'success', 'message': '全量数据刷新完成'}
        except Exception as e:
            _record_task('manual_all', 'failed', str(e))
            return {'status': 'failed', 'message': str(e)}
    
    if task_name in task_map:
        try:
            task_map[task_name]()
            return {'status': 'success', 'message': f'{task_name} 刷新完成'}
        except Exception as e:
            return {'status': 'failed', 'message': str(e)}
    
    return {'status': 'error', 'message': f'未知任务: {task_name}'}


def get_scheduled_jobs():
    """获取已注册的定时任务列表"""
    if not _scheduler or not _scheduler.running:
        return []
    
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None,
            'trigger': str(job.trigger)
        })
    return jobs


if __name__ == '__main__':
    # 测试即时任务
    result = trigger_task('news')
    print(json.dumps(result, ensure_ascii=False, indent=2))
