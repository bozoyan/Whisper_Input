import os
import threading
import time
from functools import wraps

import dotenv
import httpx

from src.llm.translate import TranslateProcessor
from ..utils.logger import logger

dotenv.load_dotenv()

def timeout_decorator(seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            error = [None]
            completed = threading.Event()

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    error[0] = e
                finally:
                    completed.set()

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()

            if completed.wait(seconds):
                if error[0] is not None:
                    raise error[0]
                return result[0]
            raise TimeoutError(f"操作超时 ({seconds}秒)")

        return wrapper
    return decorator

class SenseVoiceSmallProcessor:
    # 类级别的配置参数
    DEFAULT_TIMEOUT = 20  # API 超时时间（秒）
    DEFAULT_MODEL = "FunAudioLLM/SenseVoiceSmall"
    
    def __init__(self):
        api_key = os.getenv("SILICONFLOW_API_KEY")
        assert api_key, "未设置 SILICONFLOW_API_KEY 环境变量"
        
        self.convert_to_simplified = os.getenv("CONVERT_TO_SIMPLIFIED", "false").lower() == "true"
        # self.cc = OpenCC('t2s') if self.convert_to_simplified else None
        # self.symbol = SymbolProcessor()
        # self.add_symbol = os.getenv("ADD_SYMBOL", "false").lower() == "true"
        # self.optimize_result = os.getenv("OPTIMIZE_RESULT", "false").lower() == "true"
        self.timeout_seconds = self.DEFAULT_TIMEOUT
        self.translate_processor = TranslateProcessor()
        # 添加一个锁来防止重复处理
        self.processing_lock = threading.Lock()
        self.last_processed_time = 0
        self.min_processing_interval = 1.0  # 最小处理间隔（秒）
        self.last_audio_hash = None  # 用于检测重复音频
        # 增强重复检测机制
        self.recent_audio_hashes = set()  # 存储最近处理的音频哈希值
        self.max_recent_hashes = 10  # 最多存储10个最近的哈希值

    def _convert_traditional_to_simplified(self, text):
        """将繁体中文转换为简体中文"""
        if not self.convert_to_simplified or not text:
            return text
        return self.cc.convert(text)

    @timeout_decorator(10)
    def _call_api(self, audio_data):
        """调用硅流 API"""
        transcription_url = "https://api.siliconflow.cn/v1/audio/transcriptions"
        
        files = {
            'file': ('audio.wav', audio_data),
            'model': (None, self.DEFAULT_MODEL)
        }

        headers = {
            'Authorization': f"Bearer {os.getenv('SILICONFLOW_API_KEY')}"
        }

        with httpx.Client() as client:
            response = client.post(transcription_url, files=files, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json().get('text', '获取失败')


    def process_audio(self, audio_buffer, mode="transcriptions", prompt=""):
        """处理音频（转录或翻译）
        
        Args:
            audio_buffer: 音频数据缓冲
            mode: 'transcriptions' 或 'translations'，决定是转录还是翻译
        
        Returns:
            tuple: (结果文本, 错误信息)
            - 如果成功，错误信息为 None
            - 如果失败，结果文本为 None
        """
        # 使用锁确保同一时间只有一个处理任务在运行
        if not self.processing_lock.acquire(blocking=False):
            return None, "正在处理中，请稍后再试"
        
        try:
            # 检查是否距离上次处理时间太短
            current_time = time.time()
            if current_time - self.last_processed_time < self.min_processing_interval:
                time.sleep(self.min_processing_interval - (current_time - self.last_processed_time))
            
            # 保存原始音频文件
            import datetime
            import pyperclip
            import hashlib
            
            # 创建目录结构
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            audio_dir = os.path.join("output", today)
            os.makedirs(audio_dir, exist_ok=True)
            
            # 生成临时文件名
            timestamp = datetime.datetime.now().strftime("%H%M%S")
            temp_filename = os.path.join(audio_dir, f"recording_{timestamp}.wav")
            
            # 保存原始音频
            audio_buffer.seek(0)
            audio_data = audio_buffer.read()
            
            # 计算音频数据的哈希值以检测重复
            audio_hash = hashlib.md5(audio_data).hexdigest()
            # 增强重复检测机制
            if audio_hash in self.recent_audio_hashes:
                return None, "重复的音频数据，跳过处理"
            
            with open(temp_filename, 'wb') as f:
                f.write(audio_data)
            
            # 重置缓冲区位置
            audio_buffer.seek(0)
            
            start_time = time.time()
            
            logger.info(f"正在调用 硅基流动 API... (模式: {mode})")
            # 修复：传递正确的音频数据而不是audio_buffer
            result = self._call_api(audio_data)

            logger.info(f"API 调用成功 ({mode}), 耗时: {time.time() - start_time:.1f}秒")
            # result = self._convert_traditional_to_simplified(result)
            if mode == "translations":
                result = self.translate_processor.translate(result)
            logger.info(f"识别结果: {result}")
            
            # 将结果保存到剪贴板
            try:
                pyperclip.copy(result)
                logger.info("识别结果已保存到剪贴板")
            except Exception as e:
                logger.warning(f"无法将结果保存到剪贴板: {e}")
            
            # 重命名音频文件为识别结果
            if result:
                # 清理文件名中的非法字符
                safe_result = "".join(c for c in result if c.isalnum() or c in (' ','-','_')).rstrip()
                if safe_result:  # 确保清理后的文件名不为空
                    new_filename = os.path.join(audio_dir, f"{safe_result}.wav")
                    # 如果文件名过长，截断
                    if len(new_filename) > 200:  # 保留一些空间给路径
                        max_len = 200 - len(os.path.join(audio_dir, ".wav"))
                        safe_result = safe_result[:max_len]
                        new_filename = os.path.join(audio_dir, f"{safe_result}.wav")
                    
                    # 避免重命名冲突
                    counter = 1
                    final_filename = new_filename
                    while os.path.exists(final_filename):
                        name, ext = os.path.splitext(new_filename)
                        final_filename = f"{name}_{counter}{ext}"
                        counter += 1
                    
                    try:
                        # 修复：检查临时文件是否存在再重命名
                        if os.path.exists(temp_filename):
                            os.rename(temp_filename, final_filename)
                            logger.info(f"音频文件已重命名为: {os.path.basename(final_filename)}")
                    except Exception as e:
                        logger.warning(f"无法重命名音频文件: {e}")
                else:
                    logger.warning("识别结果为空，无法重命名音频文件")
            
            # 发送结果到字幕窗口
            try:
                # 通过文件共享结果，因为模块间不能直接导入GUI
                subtitle_file = os.path.join("logs", "subtitle.txt")
                if not os.path.exists("logs"):
                    os.makedirs("logs")
                
                with open(subtitle_file, "a", encoding="utf-8") as f:
                    f.write(result + "\n")
            except Exception as e:
                logger.warning(f"无法写入字幕文件: {e}")
            
            # 更新最后处理时间和音频哈希
            self.last_processed_time = time.time()
            self.last_audio_hash = audio_hash
            # 更新最近处理的音频哈希集合
            self.recent_audio_hashes.add(audio_hash)
            if len(self.recent_audio_hashes) > self.max_recent_hashes:
                # 移除最早的哈希值（这里简化处理，实际可以使用更复杂的数据结构）
                oldest_hash = next(iter(self.recent_audio_hashes))
                self.recent_audio_hashes.discard(oldest_hash)
            
            # if self.add_symbol:
            #     result = self.symbol.add_symbol(result)
            #     logger.info(f"添加标点符号: {result}")
            # if self.optimize_result:
            #     result = self.symbol.optimize_result(result)
            #     logger.info(f"优化结果: {result}")

            return result, None

        except TimeoutError:
            error_msg = f"❌ API 请求超时 ({self.timeout_seconds}秒)"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"❌ {str(e)}"
            logger.error(f"音频处理错误: {str(e)}", exc_info=True)
            return None, error_msg
        finally:
            # 确保audio_buffer在所有情况下都被正确关闭
            if 'audio_buffer' in locals():
                audio_buffer.close()  # 显式关闭字节流
            # 释放锁
            self.processing_lock.release()
