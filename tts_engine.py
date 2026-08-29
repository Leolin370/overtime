"""
Overtime 体育门户 - 语音合成模块
使用 edge-tts 生成中文语音播报
"""
import os
import asyncio
try:
    import edge_tts
    TTS_AVAILABLE = True
except ImportError:
    edge_tts = None
    TTS_AVAILABLE = False

AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

# 中文语音角色（自然、专业的新闻播报音色）
VOICE = 'zh-CN-YunxiNeural'  # 云希 - 男声，自然专业
VOICE_FALLBACK = 'zh-CN-YunyangNeural'  # 云扬 - 男声，浑厚


async def _synthesize(text, output_path, voice=VOICE, rate='+0%', volume='+0%'):
    """异步合成语音"""
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)


def text_to_speech(text, filename='morning_briefing.mp3', voice=None, rate='+5%'):
    """
    文本转语音
    :param text: 要合成的文本
    :param filename: 输出文件名
    :param voice: 语音角色，默认使用新闻播报音色
    :param rate: 语速，默认+5%稍快
    :return: 音频文件路径
    """
    output_path = os.path.join(AUDIO_DIR, filename)
    selected_voice = voice or VOICE
    
    if not TTS_AVAILABLE:
        print("[TTS] edge-tts 未安装，跳过语音合成")
        return None
    
    try:
        asyncio.run(_synthesize(text, output_path, selected_voice, rate=rate))
        # 验证文件
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            print(f"[TTS] 语音合成成功: {filename} ({os.path.getsize(output_path)} bytes)")
            return output_path
        else:
            raise Exception("输出文件过小")
    except Exception as e:
        print(f"[TTS] 主音色失败，尝试备用音色: {e}")
        try:
            asyncio.run(_synthesize(text, output_path, VOICE_FALLBACK, rate=rate))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                print(f"[TTS] 备用音色合成成功: {filename}")
                return output_path
        except Exception as e2:
            print(f"[TTS] 备用音色也失败: {e2}")
    
    return None


def generate_morning_audio(briefing_text=None):
    """
    生成早间新闻语音播报
    :param briefing_text: 早间简报文本，为None时从数据文件读取
    :return: 音频文件路径
    """
    import json
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    if briefing_text is None:
        briefing_path = os.path.join(data_dir, 'morning_briefing.json')
        if os.path.exists(briefing_path):
            with open(briefing_path, 'r', encoding='utf-8') as f:
                briefing = json.load(f)
            briefing_text = briefing.get('text', '')
        else:
            briefing_text = "欢迎收听Overtime体坛早报。暂无最新体育新闻，请稍后再试。"
    
    if not briefing_text:
        briefing_text = "欢迎收听Overtime体坛早报。暂无最新体育新闻。"
    
    # 生成带日期的文件名
    from datetime import datetime
    date_str = datetime.now().strftime('%Y%m%d')
    filename = f'morning_{date_str}.mp3'
    
    return text_to_speech(briefing_text, filename, rate='+3%')


def get_latest_morning_audio():
    """获取最新的早间语音文件路径"""
    if not os.path.exists(AUDIO_DIR):
        return None
    
    files = [f for f in os.listdir(AUDIO_DIR) if f.startswith('morning_') and f.endswith('.mp3')]
    if not files:
        return None
    
    files.sort(reverse=True)
    return os.path.join(AUDIO_DIR, files[0])


if __name__ == '__main__':
    # 测试
    test_text = "各位早上好，欢迎收听Overtime体坛早报。今天是2026年8月29日，以下是今日体育要闻。第一条，足球：德甲夺冠赔率更新，拜仁慕尼黑断层领跑。以上就是今日体坛早报，感谢收听。"
    path = text_to_speech(test_text, 'test.mp3')
    print(f"测试音频: {path}")
