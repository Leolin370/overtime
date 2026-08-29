"""
Overtime 体育门户 - 爬虫模块
使用 Playwright 抓取真实体育数据：新闻、运动员资料、联赛积分榜
"""
import json
import os
import re
import time
import hashlib
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 运动分类关键词映射
SPORT_KEYWORDS = {
    '足球': ['足球', '英超', '西甲', '意甲', '德甲', '法甲', '欧冠', '中超', '国足', '世界杯', '梅西', 'C罗', '姆巴佩', '哈兰德', '皇马', '巴萨', '曼联', '利物浦', '拜仁', '巴黎', '曼城', '阿森纳', '亚冠', '欧洲杯', '美洲杯'],
    '篮球': ['篮球', 'NBA', 'CBA', '詹姆斯', '库里', '科比', '乔丹', '东契奇', '约基奇', '湖人', '勇士', '凯尔特人', '公牛', '热火', '季后赛', '总决赛', 'MVP'],
    '羽毛球': ['羽毛球', '汤尤杯', '苏迪曼', '世锦赛', '林丹', '李宗伟', '陈雨菲', '安赛龙', '桃田'],
    '乒乓球': ['乒乓球', '乒超', 'WTT', '世乒赛', '马龙', '樊振东', '孙颖莎', '王楚钦', '国乒'],
    '网球': ['网球', '大满贯', '法网', '温网', '美网', '澳网', 'ATP', 'WTA', '德约', '纳达尔', '费德勒', '阿尔卡拉斯'],
    '赛车': ['F1', '赛车', '一级方程式', '维斯塔潘', '汉密尔顿', '勒克莱尔', '红牛车队', '法拉利', '迈凯伦'],
    '排球': ['排球', '女排', '世界联赛', '朱婷', '郎平', '中国女排'],
    '棒球': ['棒球', 'MLB', '大谷翔平', '本垒打', '道奇', '洋基'],
    '高尔夫': ['高尔夫', '大师赛', '伍兹', 'PGA'],
    '游泳': ['游泳', '菲尔普斯', '孙杨', '自由泳', '蝶泳', '世锦赛', '奥运'],
    '电竞': ['电竞', '英雄联盟', 'S赛', 'TI', 'DOTA', 'Faker', 'LPL', 'KPL'],
    '橄榄球': ['橄榄球', 'NFL', '超级碗', '马霍姆斯', '四分卫'],
}

# 运动员种子列表（用于百度百科抓取）
ATHLETE_SEEDS = [
    # 足球
    {'name': '梅西', 'sport': '足球', 'position': '前锋'},
    {'name': 'C罗', 'sport': '足球', 'position': '前锋'},
    {'name': '姆巴佩', 'sport': '足球', 'position': '前锋'},
    {'name': '哈兰德', 'sport': '足球', 'position': '前锋'},
    {'name': '贝林厄姆', 'sport': '足球', 'position': '中场', 'baike_key': '祖德·贝林厄姆'},
    {'name': '内马尔', 'sport': '足球', 'position': '前锋'},
    # 篮球
    {'name': '詹姆斯', 'sport': '篮球', 'position': '小前锋'},
    {'name': '库里', 'sport': '篮球', 'position': '控球后卫'},
    {'name': '约基奇', 'sport': '篮球', 'position': '中锋', 'baike_key': '尼古拉·约基奇'},
    {'name': '东契奇', 'sport': '篮球', 'position': '后卫'},
    # 羽毛球
    {'name': '林丹', 'sport': '羽毛球', 'position': '男单'},
    {'name': '陈雨菲', 'sport': '羽毛球', 'position': '女单'},
    # 乒乓球
    {'name': '马龙', 'sport': '乒乓球', 'position': '男单'},
    {'name': '樊振东', 'sport': '乒乓球', 'position': '男单'},
    {'name': '孙颖莎', 'sport': '乒乓球', 'position': '女单'},
    # 网球
    {'name': '德约科维奇', 'sport': '网球', 'position': '男单'},
    {'name': '阿尔卡拉斯', 'sport': '网球', 'position': '男单', 'baike_key': '卡洛斯·阿尔卡拉斯'},
    # 赛车
    {'name': '维斯塔潘', 'sport': '赛车', 'position': 'F1车手'},
    {'name': '汉密尔顿', 'sport': '赛车', 'position': 'F1车手', 'baike_key': '刘易斯·汉密尔顿'},
    # 排球
    {'name': '朱婷', 'sport': '排球', 'position': '主攻'},
    # 棒球
    {'name': '大谷翔平', 'sport': '棒球', 'position': '投打双修'},
    # 高尔夫
    {'name': '泰格·伍兹', 'sport': '高尔夫', 'position': '高尔夫球手'},
    # 游泳
    {'name': '菲尔普斯', 'sport': '游泳', 'position': '自由泳/蝶泳'},
    # 电竞
    {'name': 'Faker', 'sport': '电竞', 'position': '中单', 'baike_key': '李相赫'},
    # 橄榄球
    {'name': '马霍姆斯', 'sport': '橄榄球', 'position': '四分卫'},
]


def _save_json(filename, data):
    """保存JSON数据到文件"""
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _load_json(filename, default=None):
    """加载JSON数据"""
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else []


def _gen_id(text):
    """生成唯一ID"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]


def _categorize_sport(title):
    """根据标题关键词判断运动分类"""
    for sport, keywords in SPORT_KEYWORDS.items():
        for kw in keywords:
            if kw in title:
                return sport
    return '综合'


def _get_browser():
    """获取Playwright浏览器实例"""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    )
    return pw, browser


# ============================================================
# 新闻抓取
# ============================================================
def scrape_sina_news(max_articles=20):
    """
    从新浪体育抓取最新新闻
    返回新闻列表，包含标题、分类、来源链接、发布时间、正文
    """
    print(f"[爬虫] 开始抓取新浪体育新闻 (最多{max_articles}条)...")
    pw, browser = _get_browser()
    news_list = []
    
    try:
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        page.goto('https://sports.sina.com.cn/', timeout=25000, wait_until='domcontentloaded')
        page.wait_for_timeout(3000)
        
        # 提取所有新闻链接
        links = page.evaluate('''() => {
            const result = [];
            const seen = new Set();
            document.querySelectorAll('a').forEach(a => {
                const text = (a.innerText || '').trim();
                const href = a.href || '';
                // 过滤：文本长度足够、是sina域名、是文章链接
                if (text.length >= 10 && 
                    (href.includes('k.sina.com.cn/article') || 
                     href.includes('sports.sina.com.cn/') ||
                     href.includes('finance.sina.com.cn/roll')) &&
                    !seen.has(href)) {
                    seen.add(href);
                    result.push({title: text, url: href});
                }
            });
            return result;
        }''')
        
        print(f"[爬虫] 首页发现 {len(links)} 条新闻链接")
        
        # 抓取每条新闻的正文
        count = 0
        for item in links:
            if count >= max_articles:
                break
            try:
                article = _fetch_article_content(page, item['url'], item['title'])
                if article:
                    news_list.append(article)
                    count += 1
                    print(f"  [{count}/{max_articles}] {article['title'][:35]}...")
            except Exception as e:
                print(f"  [跳过] {item['title'][:30]}: {e}")
                continue
        
        browser.close()
        pw.stop()
        
    except Exception as e:
        print(f"[爬虫错误] 新浪体育抓取失败: {e}")
        try:
            browser.close()
            pw.stop()
        except:
            pass
    
    # 保存
    result = {
        'source': '新浪体育',
        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'count': len(news_list),
        'articles': news_list
    }
    _save_json('news.json', result)
    print(f"[爬虫] 新闻抓取完成，共 {len(news_list)} 条，已保存")
    return result


def _fetch_article_content(page, url, title):
    """抓取单篇新闻正文"""
    try:
        page.goto(url, timeout=15000, wait_until='domcontentloaded')
        page.wait_for_timeout(1500)
        
        data = page.evaluate('''() => {
            // 标题
            let title = '';
            const h1 = document.querySelector('h1');
            if (h1) title = h1.innerText.trim();
            
            // 发布时间
            let time = '';
            const timeEl = document.querySelector('.date, .time, [class*="time"], [class*="date"]');
            if (timeEl) time = timeEl.innerText.trim().substring(0, 30);
            
            // 正文 - 尝试多种选择器
            let content = '';
            const selectors = [
                '#artibody', '.article-content-left', '.article', 
                '#article', '.main-content', '.article-body',
                '[class*="article-content"]', '[class*="artibody"]'
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.innerText.length > 80) {
                    // 提取段落
                    const ps = el.querySelectorAll('p');
                    if (ps.length > 0) {
                        content = Array.from(ps).map(p => p.innerText.trim())
                            .filter(t => t.length > 10 && !t.includes('责任编辑') && !t.includes('点击查看'))
                            .join('\\n\\n');
                    }
                    if (!content) content = el.innerText;
                    break;
                }
            }
            
            // 如果还没找到，用所有p标签
            if (!content || content.length < 50) {
                const ps = document.querySelectorAll('p');
                const texts = [];
                for (const p of ps) {
                    const t = p.innerText.trim();
                    if (t.length > 20 && !t.includes('责任编辑') && !t.includes('新浪')) {
                        texts.push(t);
                    }
                    if (texts.length >= 8) break;
                }
                content = texts.join('\\n\\n');
            }
            
            // 清理内容
            content = content.replace(/\\[.*?\\]/g, '').replace(/【.*?】/g, '').trim();
            
            return {title, time, content: content.substring(0, 2000)};
        }''')
        
        if not data['content'] or len(data['content']) < 50:
            return None
        
        article_title = data['title'] if data['title'] else title
        sport = _categorize_sport(article_title)
        
        # 清理发布时间：提取日期时间部分
        raw_time = data.get('time', '') or ''
        clean_time = raw_time
        # 尝试匹配 "2026年08月29日 14:22" 格式
        m = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日\s*\d{1,2}:\d{2})', raw_time)
        if m:
            clean_time = m.group(1)
        else:
            # 尝试匹配 "2026-08-29 14:22" 格式
            m2 = re.search(r'(\d{4}-\d{1,2}-\d{1,2}\s*\d{1,2}:\d{2})', raw_time)
            if m2:
                clean_time = m2.group(1)
            elif len(raw_time) > 20:
                clean_time = raw_time[:16].strip()
        
        return {
            'id': _gen_id(url),
            'category': sport,
            'title': article_title,
            'content': data['content'],
            'source': '新浪体育',
            'source_url': url,
            'time': clean_time if clean_time else '刚刚',
            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return None


# ============================================================
# 运动员百度百科抓取
# ============================================================
def scrape_athletes():
    """
    从百度百科抓取运动员真实资料
    返回运动员列表，包含姓名、运动、位置、真实简介、真实图片、百科链接
    """
    print(f"[爬虫] 开始抓取运动员百度百科资料 (共{len(ATHLETE_SEEDS)}人)...")
    pw, browser = _get_browser()
    athletes = []
    
    try:
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        
        for i, seed in enumerate(ATHLETE_SEEDS):
            try:
                athlete = _fetch_baike_athlete(page, seed)
                if athlete:
                    athletes.append(athlete)
                    print(f"  [{i+1}/{len(ATHLETE_SEEDS)}] {athlete['name']} - {athlete['bio'][:40]}...")
                else:
                    # 抓取失败时保留种子信息
                    athletes.append({
                        'name': seed['name'],
                        'sport': seed['sport'],
                        'position': seed['position'],
                        'photo': '',
                        'bio': f"{seed['name']}，{seed['sport']}运动员，司职{seed['position']}。",
                        'baike_url': f"https://baike.baidu.com/item/{seed['name']}",
                        'nationality': '',
                        'birth': ''
                    })
                    print(f"  [{i+1}/{len(ATHLETE_SEEDS)}] {seed['name']} - 使用默认资料")
            except Exception as e:
                print(f"  [错误] {seed['name']}: {e}")
                athletes.append({
                    'name': seed['name'], 'sport': seed['sport'],
                    'position': seed['position'], 'photo': '',
                    'bio': f"{seed['name']}，{seed['sport']}运动员。",
                    'baike_url': f"https://baike.baidu.com/item/{seed['name']}",
                    'nationality': '', 'birth': ''
                })
        
        browser.close()
        pw.stop()
        
    except Exception as e:
        print(f"[爬虫错误] 运动员抓取失败: {e}")
        try:
            browser.close()
            pw.stop()
        except:
            pass
    
    result = {
        'source': '百度百科',
        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'count': len(athletes),
        'athletes': athletes
    }
    _save_json('athletes.json', result)
    print(f"[爬虫] 运动员资料抓取完成，共 {len(athletes)} 人")
    return result


def _fetch_baike_athlete(page, seed):
    """从百度百科抓取单个运动员资料（适配新版React布局）"""
    search_key = seed.get('baike_key', seed['name'])
    url = f"https://baike.baidu.com/item/{search_key}"
    page.goto(url, timeout=20000, wait_until='domcontentloaded')
    page.wait_for_timeout(3000)
    
    data = page.evaluate('''(seedName) => {
        const result = {name: seedName, title: '', summary: '', photo: '', nationality: '', birth: '', baike_url: location.href};
        
        // 标题
        const h1 = document.querySelector('h1');
        if (h1) result.title = h1.innerText.trim();
        
        // ===== 摘要（新版百度百科: lemmaSummary_xxx J-summary）=====
        let summaryEl = document.querySelector('[class*="lemmaSummary"], [class*="J-summary"], .lemma-summary');
        if (summaryEl) {
            result.summary = summaryEl.innerText.trim()
                .replace(/\\n+/g, ' ')
                .replace(/\\[.*?\\]/g, '')
                .replace(/\\s+/g, ' ')
                .substring(0, 500);
        }
        
        // 备用：找包含全名且不含"人物关系/妻子/儿子"的段落
        if (!result.summary || result.summary.length < 30) {
            const allDivs = document.querySelectorAll('div, p');
            for (const div of allDivs) {
                const text = div.innerText?.trim();
                if (text && text.length > 80 && text.length < 600 &&
                    (text.includes('出生') || text.includes('司职')) &&
                    !text.includes('人物关系') && !text.includes('妻子') &&
                    !text.includes('儿子') && !text.includes('女儿') &&
                    div.children.length <= 5) {
                    result.summary = text.replace(/\\n+/g, ' ').replace(/\\[.*?\\]/g, '').substring(0, 500);
                    break;
                }
            }
        }
        
        // ===== 图片（找摘要区域附近的头像图，或第一个bkimg大图）=====
        // 优先：摘要区域内的图片
        if (summaryEl) {
            const sumImg = summaryEl.querySelector('img');
            if (sumImg && sumImg.src && sumImg.src.includes('bkimg')) {
                result.photo = sumImg.src;
            }
        }
        // 其次：页面中第一个 bkimg 域名且 >=100px 的图片
        if (!result.photo) {
            const imgs = document.querySelectorAll('img');
            for (const img of imgs) {
                if (img.src && img.src.includes('bkimg') && 
                    (img.naturalWidth >= 100 || img.width >= 100)) {
                    result.photo = img.src;
                    break;
                }
            }
        }
        // 最后备用
        if (!result.photo) {
            const imgs = document.querySelectorAll('img');
            for (const img of imgs) {
                if (img.src && img.naturalWidth >= 150 && 
                    !img.src.includes('logo') && !img.src.includes('svg')) {
                    result.photo = img.src;
                    break;
                }
            }
        }
        
        // ===== 基本信息（新版: div.para_xxx 中 "标签：值" 格式）=====
        const info = {};
        // 方法1: 解析所有 para div 中的 "key：value" 格式
        document.querySelectorAll('div[class*="para"], div[class*="MARK_MODULE"]').forEach(el => {
            const text = el.innerText?.trim();
            if (text && text.length < 100 && text.includes('：')) {
                const parts = text.split('：');
                if (parts.length >= 2) {
                    const key = parts[0].trim();
                    const value = parts.slice(1).join('：').trim();
                    if (key && value && key.length < 15 && !key.includes(' ')) {
                        info[key] = value.substring(0, 50);
                    }
                }
            }
        });
        
        // 方法2: dt/dd 对（旧版兼容）
        if (Object.keys(info).length === 0) {
            const dts = document.querySelectorAll('dt');
            dts.forEach(dt => {
                const key = dt.innerText?.trim()?.replace(/[：:]/g, '');
                const dd = dt.nextElementSibling;
                if (key && dd && dd.tagName === 'DD') {
                    info[key] = dd.innerText?.trim()?.substring(0, 50) || '';
                }
            });
        }
        
        result.nationality = info['国籍'] || info['国\xa0\xa0\xa0\xa0籍'] || '';
        result.birth = info['出生日期'] || info['出生年月'] || info['出生'] || info['生日'] || '';
        
        return result;
    }''', seed['name'])
    
    if not data['summary'] or len(data['summary']) < 20:
        return None
    
    # 从摘要中提取出生日期兜底
    birth = data['birth']
    if not birth:
        m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', data['summary'])
        if m:
            birth = f"{m.group(1)}年{m.group(2)}月{m.group(3)}日"
    
    # 显示名：百科标题过长（>12字）时使用种子名
    name = data['title'] if data['title'] else seed['name']
    name = re.sub(r'[（(].*?[）)]', '', name).strip()
    if len(name) > 12:
        name = seed['name']
    
    return {
        'name': name,
        'sport': seed['sport'],
        'position': seed['position'],
        'photo': data['photo'],
        'bio': data['summary'],
        'baike_url': data['baike_url'] if data['baike_url'] else url,
        'nationality': data['nationality'],
        'birth': birth
    }


# ============================================================
# 联赛积分榜抓取
# ============================================================
def scrape_standings():
    """
    抓取联赛积分榜数据
    优先从真实网站抓取，失败时使用最近缓存
    """
    print("[爬虫] 开始抓取联赛积分榜...")
    pw, browser = _get_browser()
    standings = {'足球': {}, '篮球': {}}
    
    try:
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        
        # 足球 - 英超积分榜（从新浪体育或其他源）
        try:
            epl = _scrape_epl_standings(page)
            if epl:
                standings['足球']['英超联赛'] = epl
                print(f"  [足球] 英超积分榜: {len(epl)} 支球队")
        except Exception as e:
            print(f"  [足球] 英超抓取失败: {e}")
        
        # 篮球 - NBA 东西部
        try:
            nba = _scrape_nba_standings(page)
            if nba:
                standings['篮球']['NBA'] = nba
                print(f"  [篮球] NBA积分榜: {len(nba)} 支球队")
        except Exception as e:
            print(f"  [篮球] NBA抓取失败: {e}")
        
        browser.close()
        pw.stop()
        
    except Exception as e:
        print(f"[爬虫错误] 积分榜抓取失败: {e}")
        try:
            browser.close()
            pw.stop()
        except:
            pass
    
    # 如果抓取为空，加载缓存
    if not standings['足球'] and not standings['篮球']:
        cached = _load_json('standings.json', {})
        if cached.get('standings'):
            standings = cached['standings']
            print("[爬虫] 使用缓存积分榜数据")
    
    result = {
        'source': '网络抓取',
        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'standings': standings
    }
    _save_json('standings.json', result)
    print(f"[爬虫] 积分榜抓取完成")
    return result


def _scrape_epl_standings(page):
    """抓取英超积分榜（多源尝试）"""
    sources = [
        'https://www.dongqiudi.com/data/1',
        'https://zq.win007.com/cn/League/36.html',
    ]
    for url in sources:
        try:
            page.goto(url, timeout=15000, wait_until='domcontentloaded')
            page.wait_for_timeout(3000)
            
            data = page.evaluate('''() => {
                const rows = [];
                // 通用表格解析：找所有table，解析数据行
                const tables = document.querySelectorAll('table');
                for (const table of tables) {
                    const trs = table.querySelectorAll('tr');
                    for (const tr of trs) {
                        const cells = Array.from(tr.querySelectorAll('td')).map(c => c.innerText.trim());
                        // 数据行特征：第一列是数字排名，有球队名和积分
                        if (cells.length >= 4 && /^\\d+$/.test(cells[0])) {
                            // 找球队名（非纯数字、长度2-15）
                            let team = '';
                            let points = 0;
                            let played = 0;
                            for (let i = 1; i < cells.length; i++) {
                                const c = cells[i];
                                if (!team && c && c.length >= 2 && c.length <= 15 && !/^\\d+$/.test(c) && !c.includes('%') && !c.includes('-')) {
                                    team = c;
                                }
                                const num = parseInt(c);
                                if (!isNaN(num) && num >= 0 && num <= 120) {
                                    if (played === 0 && num <= 38) played = num;
                                    if (num > played && num <= 120) points = num;
                                }
                            }
                            if (team && team.length >= 2) {
                                rows.push({
                                    rank: parseInt(cells[0]) || rows.length + 1,
                                    team: team,
                                    played: played,
                                    points: points
                                });
                            }
                        }
                    }
                    if (rows.length >= 5) break;
                }
                // 去重并排序
                const seen = new Set();
                const unique = [];
                for (const r of rows) {
                    if (!seen.has(r.team)) {
                        seen.add(r.team);
                        unique.push(r);
                    }
                }
                unique.sort((a, b) => b.points - a.points);
                unique.forEach((r, i) => r.rank = i + 1);
                return unique.slice(0, 10);
            }''')
            
            if data and len(data) >= 5:
                return data
        except Exception as e:
            print(f"    EPL源 {url[:30]} 失败: {e}")
            continue
    
    return None


def _scrape_nba_standings(page):
    """抓取NBA积分榜（虎扑），合并东西部"""
    try:
        page.goto('https://nba.hupu.com/standings', timeout=15000, wait_until='domcontentloaded')
        page.wait_for_timeout(3000)
        
        data = page.evaluate('''() => {
            const rows = [];
            const tables = document.querySelectorAll('table');
            tables.forEach(table => {
                const trs = table.querySelectorAll('tr');
                trs.forEach(tr => {
                    const cells = Array.from(tr.querySelectorAll('td')).map(c => c.innerText.trim());
                    // 数据行：第一列是数字排名，第二列是队名（非"队名"表头）
                    if (cells.length >= 5 && /^\\d+$/.test(cells[0]) && 
                        cells[1] && cells[1] !== '队名' && cells[1].length < 20) {
                        const wins = parseInt(cells[2]) || 0;
                        const losses = parseInt(cells[3]) || 0;
                        rows.push({
                            rank: parseInt(cells[0]) || rows.length + 1,
                            team: cells[1],
                            played: wins + losses,
                            wins: wins,
                            losses: losses,
                            points: wins  // NBA用胜场数作为积分参考
                        });
                    }
                });
            });
            // 按胜场排序
            rows.sort((a, b) => b.wins - a.wins);
            // 重新排名
            rows.forEach((r, i) => r.rank = i + 1);
            return rows.slice(0, 15);
        }''')
        
        if data and len(data) >= 3:
            return data
    except Exception as e:
        print(f"    NBA抓取异常: {e}")
    
    return None


# ============================================================
# 早间新闻摘要（用于TTS）
# ============================================================
def generate_morning_briefing():
    """
    生成早间新闻简报文本
    从最新新闻中挑选重要条目，整理成语音播报文本
    """
    news_data = _load_json('news.json', {})
    articles = news_data.get('articles', [])
    
    if not articles:
        return {
            'date': datetime.now().strftime('%Y年%m月%d日'),
            'text': '暂无最新体育新闻。',
            'articles': []
        }
    
    # 按分类分组，每类取1-2条
    selected = []
    by_sport = {}
    for a in articles:
        cat = a.get('category', '综合')
        if cat not in by_sport:
            by_sport[cat] = []
        by_sport[cat].append(a)
    
    for sport, items in by_sport.items():
        selected.extend(items[:2])
    
    # 生成播报文本
    date_str = datetime.now().strftime('%Y年%m月%d日')
    text_parts = [f"各位早上好，欢迎收听Overtime体坛早报，今天是{date_str}。以下是今日体育要闻："]
    
    for i, a in enumerate(selected[:8], 1):
        # 取正文前两句作为摘要
        content = a.get('content', '')
        sentences = re.split(r'[。！？\n]', content)
        summary = '。'.join([s for s in sentences if len(s) > 10][:2])
        if not summary:
            summary = a['title']
        text_parts.append(f"第{i}条，{a['category']}：{a['title']}。{summary}。")
    
    text_parts.append("以上就是今日体坛早报的全部内容，感谢收听，祝您一天好心情。")
    
    briefing = {
        'date': date_str,
        'text': '\n'.join(text_parts),
        'articles': [{'id': a['id'], 'title': a['title'], 'category': a['category']} for a in selected[:8]],
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    _save_json('morning_briefing.json', briefing)
    return briefing


# ============================================================
# 一键全量抓取
# ============================================================
def scrape_all():
    """执行全量数据抓取"""
    print("=" * 50)
    print("[爬虫] 开始全量数据抓取")
    print("=" * 50)
    
    results = {}
    
    # 1. 新闻
    try:
        results['news'] = scrape_sina_news(max_articles=15)
    except Exception as e:
        print(f"[错误] 新闻抓取异常: {e}")
        results['news'] = _load_json('news.json', {})
    
    # 2. 运动员
    try:
        results['athletes'] = scrape_athletes()
    except Exception as e:
        print(f"[错误] 运动员抓取异常: {e}")
        results['athletes'] = _load_json('athletes.json', {})
    
    # 3. 积分榜
    try:
        results['standings'] = scrape_standings()
    except Exception as e:
        print(f"[错误] 积分榜抓取异常: {e}")
        results['standings'] = _load_json('standings.json', {})
    
    # 4. 早间简报
    try:
        results['morning_briefing'] = generate_morning_briefing()
    except Exception as e:
        print(f"[错误] 早间简报生成异常: {e}")
    
    print("=" * 50)
    print("[爬虫] 全量抓取完成")
    print("=" * 50)
    return results


if __name__ == '__main__':
    scrape_all()
