from typing import *
import logging
import time
import logging
import sherpa_onnx
import os
import asyncio
import numpy as np
from toexcel.toexcel import export_to_excel  # 导入 toexcel.py 中的函数
import sys
import keyboard 
import pygame
import threading
import winsound  # Windows系统

logger = logging.getLogger(__file__)
_asr_engines = {}


class ASRResult:
    def __init__(self, text: str, start_time: str, finished: bool, idx: int):
        self.text = text
        self.finished = finished
        self.idx = idx
        self.start_time = start_time
    def to_dict(self):
        return {"text": self.text, "start_time": self.start_time,  "finished": self.finished, "idx": self.idx}


class ASRStream:
    def __init__(self, recognizer: Union[sherpa_onnx.OnlineRecognizer | sherpa_onnx.OfflineRecognizer], sample_rate: int) -> None:
        self.recognizer = recognizer
        self.inbuf = asyncio.Queue()
        self.outbuf = asyncio.Queue()
        self.sample_rate = sample_rate
        self.is_closed = False
        self.online = isinstance(recognizer, sherpa_onnx.OnlineRecognizer)
        self.results = []
        self.combined_results = []  # 用于存储合并的结果
    async def start(self):
        if self.online:
            asyncio.create_task(self.run_online())
        else:
            asyncio.create_task(self.run_offline())

    # async def run_online(self):
    #     stream = self.recognizer.create_stream()
    #     last_result = ""
    #     segment_id = 0
    #     logger.info('asr: start real-time recognizer')
    #     while not self.is_closed:
    #         samples = await self.inbuf.get()
    #         stream.accept_waveform(self.sample_rate, samples)
    #         while self.recognizer.is_ready(stream):
    #             self.recognizer.decode_stream(stream)

    #         is_endpoint = self.recognizer.is_endpoint(stream)
    #         result = self.recognizer.get_result(stream)

    #         if result and (last_result != result):
    #             last_result = result
    #             logger.info(f' > {segment_id}:{result}')
    #             self.outbuf.put_nowait(
    #                 ASRResult(result, False, segment_id))

    #         if is_endpoint:
    #             if result:
    #                 logger.info(f'{segment_id}: {result}')
    #                 self.outbuf.put_nowait(
    #                     ASRResult(result, True, segment_id))
    #                 segment_id += 1
    #             self.recognizer.reset(stream)

    async def run_offline(self):

        vad = _asr_engines['vad']

        segment_id = 0
        st = None
        combined_result = ""  # 用于存储合并的识别结果
        combined_current_time = None  # 用于存储合并的时间结果
        previous_space_state = False  # 记录空格键的前一个状态
        while not self.is_closed:
            samples = await self.inbuf.get()
            current_space_state = keyboard.is_pressed(' ')

            # 检测空格键从按下转变为松开
            if previous_space_state and not current_space_state:
                # 松开空格键时，如果有合并的结果，则输出
                if combined_result.strip():
                    logger.debug(f'松开空格键，输出合并结果: {combined_result.strip()}')
                    # 替换标点
                    # combined_result = combined_result.replace(" ", "")
                    # combined_result = combined_result[:-2].replace("。", "，") + "。"
                    self.outbuf.put_nowait(ASRResult(combined_result.strip(), combined_current_time, True, segment_id))
                    self.combined_results.append({"time": combined_current_time, "result": combined_result})
                    segment_id += 1
                    combined_result = ""  # 重置合并结果
                    combined_current_time = None  # 重置时间
        
            # 如果空格没按下，直接丢弃样本，不进行处理
            if not current_space_state:
                vad.reset()
                previous_space_state = current_space_state  # 更新状态
                continue
            # 如果空格键从未按下到按下，播放开始提示音并写入时间
            if not previous_space_state and current_space_state:
                # 在新线程中播放开始提示音，避免阻塞主线程
                threading.Thread(target=self.play_start_sound, daemon=True).start()
                # logger.info("开始录制 - 播放提示音")
                combined_current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            # 空格已按下，才将音频送入 VAD
            vad.accept_waveform(samples)
            while not vad.empty() and keyboard.is_pressed(' '):
                if not st:
                    st = time.time()
                stream = self.recognizer.create_stream()
                stream.accept_waveform(self.sample_rate, vad.front.samples)

                vad.pop()
                self.recognizer.decode_stream(stream)

                result = stream.result.text.strip()
                if result:
                    duration = time.time() - st
                    current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st))
                    self.results.append({"time": current_time, "result": result})
                    logger.info(f'{segment_id}:{result} ({duration:.2f}s)')
                    # self.outbuf.put_nowait(ASRResult(result, current_time, True, segment_id))
                    combined_result += result + " "  # 将结果合并到字符串中
                    # 在新线程中播放处理结束提示音，避免阻塞主线程
                    threading.Thread(target=self.play_end_sound, daemon=True).start()
                    # segment_id += 1
            # 更新前一个状态
            previous_space_state = current_space_state
            st = None

    def play_start_sound(self):
        """播放提示音"""
        try:
            # 初始化 pygame mixer
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            
            # 音频文件路径
            sound_file = os.path.join("assets", "voice", "start.mp3")  # 或 .mp3
            
            # 检查文件是否存在
            if os.path.exists(sound_file):
                sound = pygame.mixer.Sound(sound_file)
                sound.play()
                # logger.info(f"播放提示音: {sound_file}")
        except Exception as e:
            logger.warning(f"无法播放提示音: {e}")
            # 备选方案
            try:
                winsound.Beep(800, 150)
            except:
                pass

    def play_end_sound(self):
        """播放提示音"""
        try:
            # 初始化 pygame mixer
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            
            # 音频文件路径
            sound_file = os.path.join("assets", "voice", "end.mp3")  # 或 .mp3
            
            # 检查文件是否存在
            if os.path.exists(sound_file):
                sound = pygame.mixer.Sound(sound_file)
                sound.play()
                # logger.info(f"播放提示音: {sound_file}")
        except Exception as e:
            logger.warning(f"无法播放提示音: {e}")
            # 备选方案
            try:
                winsound.Beep(800, 150)
            except:
                pass

    async def close(self):
        self.is_closed = True
        self.outbuf.put_nowait(None)
        # 调用 toexcel.py 的方法，将 self.results 导出为 Excel
        # if self.combined_results:
        #     print(self.combined_results)
        #     first_time = self.combined_results[0]["time"].replace(":", "-").replace(" ", "_")
        #     filename = f"asr_results_{first_time}.xlsx"
        #     export_to_excel(self.combined_results, filename)

    async def write(self, pcm_bytes: bytes):
        pcm_data = np.frombuffer(pcm_bytes, dtype=np.int16)
        samples = pcm_data.astype(np.float32) / 32768.0
        self.inbuf.put_nowait(samples)

    async def read(self) -> ASRResult:
        return await self.outbuf.get()


def create_zipformer(samplerate: int, args) -> sherpa_onnx.OnlineRecognizer:
    d = os.path.join(
        args.models_root, 'sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20')
    if not os.path.exists(d):
        raise ValueError(f"asr: model not found {d}")

    encoder = os.path.join(d, "encoder-epoch-99-avg-1.onnx")
    decoder = os.path.join(d, "decoder-epoch-99-avg-1.onnx")
    joiner = os.path.join(d, "joiner-epoch-99-avg-1.onnx")
    tokens = os.path.join(d, "tokens.txt")

    recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=tokens,
        encoder=encoder,
        decoder=decoder,
        joiner=joiner,
        provider=args.asr_provider,
        num_threads=args.threads,
        sample_rate=samplerate,
        feature_dim=80,
        enable_endpoint_detection=True,
        rule1_min_trailing_silence=2.4,
        rule2_min_trailing_silence=1.2,
        rule3_min_utterance_length=20,  # it essentially disables this rule
    )
    return recognizer


def create_sensevoice(samplerate: int, args) -> sherpa_onnx.OfflineRecognizer:
    d = os.path.join(args.models_root,
                     'sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17')

    if not os.path.exists(d):
        raise ValueError(f"asr: model not found {d}")

    recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=os.path.join(d, 'model.onnx'),
        tokens=os.path.join(d, 'tokens.txt'),
        num_threads=args.threads,
        sample_rate=samplerate,
        use_itn=True,
        debug=0,
        language=args.asr_lang,
    )
    return recognizer


def create_paraformer_trilingual(samplerate: int, args) -> sherpa_onnx.OnlineRecognizer:
    d = os.path.join(
        args.models_root, 'sherpa-onnx-paraformer-trilingual-zh-cantonese-en')
    if not os.path.exists(d):
        raise ValueError(f"asr: model not found {d}")

    recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
        paraformer=os.path.join(d, 'model.onnx'),
        tokens=os.path.join(d, 'tokens.txt'),
        num_threads=args.threads,
        sample_rate=samplerate,
        debug=0,
        provider=args.asr_provider,
    )
    return recognizer


def create_paraformer_en(samplerate: int, args) -> sherpa_onnx.OnlineRecognizer:
    d = os.path.join(
        args.models_root, 'sherpa-onnx-paraformer-en')
    if not os.path.exists(d):
        raise ValueError(f"asr: model not found {d}")

    recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
        paraformer=os.path.join(d, 'model.onnx'),
        tokens=os.path.join(d, 'tokens.txt'),
        num_threads=args.threads,
        sample_rate=samplerate,
        use_itn=True,
        debug=0,
        provider=args.asr_provider,
    )
    return recognizer

def create_fireredasr(samplerate: int, args) -> sherpa_onnx.OnlineRecognizer:
    d = os.path.join(
        args.models_root, 'sherpa-onnx-fire-red-asr-large-zh_en-2025-02-16')
    if not os.path.exists(d):
        raise ValueError(f"asr: model not found {d}")

    encoder = os.path.join(d, "encoder.int8.onnx")
    decoder = os.path.join(d, "decoder.int8.onnx")
    tokens = os.path.join(d, "tokens.txt")

    # 添加文件存在性检查
    for file_path, file_name in [(encoder, "encoder.int8.onnx"), 
                                 (decoder, "decoder.int8.onnx"), 
                                 (tokens, "tokens.txt")]:
        if not os.path.exists(file_path):
            raise ValueError(f"asr: required file not found: {file_path}")
        
        # 检查文件大小（ONNX 文件不应该为空）
        if file_name.endswith('.onnx') and os.path.getsize(file_path) == 0:
            raise ValueError(f"asr: model file is empty: {file_path}")
    
    # logger.info(f"Loading FireRedASR model from {d}")
    # logger.info(f"Encoder: {encoder} (size: {os.path.getsize(encoder)} bytes)")
    # logger.info(f"Decoder: {decoder} (size: {os.path.getsize(decoder)} bytes)")

    recognizer = sherpa_onnx.OfflineRecognizer.from_fire_red_asr(
        encoder=encoder,
        decoder=decoder,
        tokens=tokens,
        debug=0,
        provider=args.asr_provider,
    )
    return recognizer



def load_asr_engine(samplerate: int, args) -> sherpa_onnx.OnlineRecognizer:
    cache_engine = _asr_engines.get(args.asr_model)
    if cache_engine:
        return cache_engine
    st = time.time()
    if args.asr_model == 'zipformer-bilingual':
        cache_engine = create_zipformer(samplerate, args)
    elif args.asr_model == 'sensevoice':
        cache_engine = create_sensevoice(samplerate, args)
        _asr_engines['vad'] = load_vad_engine(samplerate, args)
    elif args.asr_model == 'paraformer-trilingual':
        cache_engine = create_paraformer_trilingual(samplerate, args)
        _asr_engines['vad'] = load_vad_engine(samplerate, args)
    elif args.asr_model == 'paraformer-en':
        cache_engine = create_paraformer_en(samplerate, args)
        _asr_engines['vad'] = load_vad_engine(samplerate, args)
    elif args.asr_model == 'fireredasr':
        cache_engine = create_fireredasr(samplerate, args)
        _asr_engines['vad'] = load_vad_engine(samplerate, args)
    else:
        raise ValueError(f"asr: unknown model {args.asr_model}")
    _asr_engines[args.asr_model] = cache_engine
    logger.info(f"asr: engine loaded in {time.time() - st:.2f}s")
    return cache_engine


def load_vad_engine(samplerate: int, args, min_silence_duration: float = 0.25, buffer_size_in_seconds: int = 100) -> sherpa_onnx.VoiceActivityDetector:
    config = sherpa_onnx.VadModelConfig()
    d = os.path.join(args.models_root, 'silero_vad')
    if not os.path.exists(d):
        raise ValueError(f"vad: model not found {d}")

    config.silero_vad.model = os.path.join(d, 'silero_vad.onnx')
    config.silero_vad.min_silence_duration = min_silence_duration
    config.sample_rate = samplerate
    config.provider = args.asr_provider
    config.num_threads = args.threads

    vad = sherpa_onnx.VoiceActivityDetector(
        config,
        buffer_size_in_seconds=buffer_size_in_seconds)
    return vad


async def start_asr_stream(samplerate: int, args) -> ASRStream:
    """
    Start a ASR stream
    """
    stream = ASRStream(load_asr_engine(samplerate, args), samplerate)
    await stream.start()
    return stream
