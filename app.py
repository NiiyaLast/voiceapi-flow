from typing import *
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import logging
from pydantic import BaseModel, Field
import uvicorn
from voiceapi.tts import TTSResult, start_tts_stream, TTSStream
from voiceapi.asr import start_asr_stream, ASRStream, ASRResult
import logging
import argparse
import glob
import os
from datetime import datetime
from toexcel.structured_data import load_excel_data

app = FastAPI()
logger = logging.getLogger(__file__)

# 添加获取最新Excel文件的函数
def get_latest_excel_file():
    """获取download目录下最新的以'asr_results_'开头的Excel文件"""
    download_dir = "./download"
    
    if not os.path.exists(download_dir):
        logger.warning(f"下载目录不存在: {download_dir}")
        return None, None
    
    # 定义搜索模式
    search_patterns = [
        os.path.join(download_dir, "asr_results_*.xlsx"),
        os.path.join(download_dir, "asr_results_*.xls")
    ]
    
    # 获取所有匹配的Excel文件
    excel_files = []
    for pattern in search_patterns:
        excel_files.extend(glob.glob(pattern))
    
    if not excel_files:
        logger.info("没有找到以'asr_results_'开头的Excel文件")
        return None, None
    
    # 按修改时间排序，获取最新的文件
    latest_file = max(excel_files, key=os.path.getmtime)
    file_name = os.path.basename(latest_file)
    
    # 获取文件修改时间用于日志
    file_modified = os.path.getmtime(latest_file)
    modified_time = datetime.fromtimestamp(file_modified).strftime('%Y-%m-%d %H:%M:%S')
    
    logger.info(f"找到最新的ASR结果Excel文件: {file_name} (修改时间: {modified_time})")
    return download_dir, file_name

# 简化的AI处理API端点
@app.post("/ai-process-excel", 
          description="Process the latest Excel file with AI analysis")
async def ai_process_latest_excel():
    """
    处理download目录下最新的Excel文件并进行AI分析
    """
    try:
        # 获取最新要的Excel文件
        file_path, file_name = get_latest_excel_file()
        
        if not file_path or not file_name:
            raise HTTPException(
                status_code=404, 
                detail="没有找到Excel文件，请先进行语音识别生成文件"
            )
        
        logger.info(f"开始AI处理最新文件: {file_path}/{file_name}")
        
        # 调用structured_data的load_excel_data函数
        reader = load_excel_data(
            file_path=file_path,
            file_name=file_name,
            enable_ai_processing=True
        )
        
        # 获取处理结果
        data = reader.get_data()
        total_count = len(data)
        
        # 统计处理成功的记录数（假设AI处理成功的记录会有特定标识）
        processed_count = sum(1 for item in data if item.get('ai_processed', False))
        
        # 获取文件信息
        full_path = os.path.join(file_path, file_name)
        file_size = os.path.getsize(full_path)
        file_modified = os.path.getmtime(full_path)
        
        return {
            "status": "success",
            "message": "AI处理完成",
            "file_info": {
                "name": file_name,
                "size": file_size,
                "modified": file_modified,
                "path": file_path
            },
            "processing_results": {
                "total_records": total_count,
                "processed_records": processed_count,
                "success_rate": f"{(processed_count/total_count*100):.1f}%" if total_count > 0 else "0%"
            }
        }
        
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        raise HTTPException(status_code=404, detail=f"文件未找到: {str(e)}")
        
    except Exception as e:
        logger.error(f"AI处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"AI处理失败: {str(e)}")

@app.websocket("/asr")
async def websocket_asr(websocket: WebSocket,
                        samplerate: int = Query(16000, title="Sample Rate",
                                                description="The sample rate of the audio."),):
    await websocket.accept()

    asr_stream: ASRStream = await start_asr_stream(samplerate, args)
    if not asr_stream:
        logger.error("failed to start ASR stream")
        await websocket.close()
        return

    async def task_recv_pcm():
        while True:
            pcm_bytes = await websocket.receive_bytes()
            if not pcm_bytes:
                return
            await asr_stream.write(pcm_bytes)

    async def task_send_result():
        while True:
            result: ASRResult = await asr_stream.read()
            if not result:
                return
            await websocket.send_json(result.to_dict())
            logger.info(result.to_dict())
    try:
        await asyncio.gather(task_recv_pcm(), task_send_result())
    except WebSocketDisconnect:
        logger.info("asr: disconnected")
    finally:
        await asr_stream.close()


@app.websocket("/tts")
async def websocket_tts(websocket: WebSocket,
                        samplerate: int = Query(16000,
                                                title="Sample Rate",
                                                description="The sample rate of the generated audio."),
                        interrupt: bool = Query(True,
                                                title="Interrupt",
                                                description="Interrupt the current TTS stream when a new text is received."),
                        sid: int = Query(0,
                                         title="Speaker ID",
                                         description="The ID of the speaker to use for TTS."),
                        chunk_size: int = Query(1024,
                                                title="Chunk Size",
                                                description="The size of the chunk to send to the client."),
                        speed: float = Query(1.0,
                                             title="Speed",
                                             description="The speed of the generated audio."),
                        split: bool = Query(True,
                                            title="Split",
                                            description="Split the text into sentences.")):

    await websocket.accept()
    tts_stream: TTSStream = None

    async def task_recv_text():
        nonlocal tts_stream
        while True:
            text = await websocket.receive_text()
            if not text:
                return

            if interrupt or not tts_stream:
                if tts_stream:
                    await tts_stream.close()
                    logger.info("tts: stream interrupt")

                tts_stream = await start_tts_stream(sid, samplerate, speed, args)
                if not tts_stream:
                    logger.error("tts: failed to allocate tts stream")
                    await websocket.close()
                    return
            logger.info(f"tts: received: {text} (split={split})")
            await tts_stream.write(text, split)

    async def task_send_pcm():
        nonlocal tts_stream
        while not tts_stream:
            # wait for tts stream to be created
            await asyncio.sleep(0.1)

        while True:
            result: TTSResult = await tts_stream.read()
            if not result:
                return

            if result.finished:
                await websocket.send_json(result.to_dict())
            else:
                for i in range(0, len(result.pcm_bytes), chunk_size):
                    await websocket.send_bytes(result.pcm_bytes[i:i+chunk_size])

    try:
        await asyncio.gather(task_recv_text(), task_send_pcm())
    except WebSocketDisconnect:
        logger.info("tts: disconnected")
    finally:
        if tts_stream:
            await tts_stream.close()


class TTSRequest(BaseModel):
    text: str = Field(..., title="Text",
                      description="The text to be converted to speech.",
                      examples=["Hello, world!"])
    sid: int = Field(0, title="Speaker ID",
                     description="The ID of the speaker to use for TTS.")
    samplerate: int = Field(16000, title="Sample Rate",
                            description="The sample rate of the generated audio.")
    speed: float = Field(1.0, title="Speed",
                         description="The speed of the generated audio.")


@ app.post("/tts",
           description="Generate speech audio from text.",
           response_class=StreamingResponse, responses={200: {"content": {"audio/wav": {}}}})
async def tts_generate(req: TTSRequest):
    if not req.text:
        raise HTTPException(status_code=400, detail="text is required")

    tts_stream = await start_tts_stream(req.sid, req.samplerate, req.speed,  args)
    if not tts_stream:
        raise HTTPException(
            status_code=500, detail="failed to start TTS stream")

    r = await tts_stream.generate(req.text)
    return StreamingResponse(r, media_type="audio/wav")


if __name__ == "__main__":
    models_root = './models'

    for d in ['.', '..', '../..']:
        if os.path.isdir(f'{d}/models'):
            models_root = f'{d}/models'
            break

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000, help="port number")
    parser.add_argument("--addr", type=str,
                        default="localhost", help="serve address")

    parser.add_argument("--asr-provider", type=str,
                        default="cpu", help="asr provider, cpu or cuda")
    parser.add_argument("--tts-provider", type=str,
                        default="cpu", help="tts provider, cpu or cuda")

    parser.add_argument("--threads", type=int, default=2,
                        help="number of threads")

    parser.add_argument("--models-root", type=str, default=models_root,
                        help="model root directory")

    parser.add_argument("--asr-model", type=str, default='fireredasr',
                        help="ASR model name: zipformer-bilingual, sensevoice, paraformer-trilingual, paraformer-en, fireredasr")

    parser.add_argument("--asr-lang", type=str, default='zh',
                        help="ASR language, zh, en, ja, ko, yue")

    parser.add_argument("--tts-model", type=str, default='vits-zh-hf-theresa',
                        help="TTS model name: vits-zh-hf-theresa, vits-melo-tts-zh_en, kokoro-multi-lang-v1_0")

    args = parser.parse_args()

    if args.tts_model == 'vits-melo-tts-zh_en' and args.tts_provider == 'cuda':
        logger.warning(
            "vits-melo-tts-zh_en does not support CUDA fallback to CPU")
        args.tts_provider = 'cpu'

    app.mount("/", app=StaticFiles(directory="./assets", html=True), name="assets")

    logging.basicConfig(format='%(levelname)s: %(asctime)s %(name)s:%(lineno)s %(message)s',
                        level=logging.INFO)
    uvicorn.run(app, host=args.addr, port=args.port)
