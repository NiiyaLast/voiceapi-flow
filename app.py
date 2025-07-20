from typing import *
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import logging
from pydantic import BaseModel, Field
from typing import List, Any
import uvicorn
from voiceapi.tts import TTSResult, start_tts_stream, TTSStream
from voiceapi.asr import start_asr_stream, ASRStream, ASRResult
import logging
import argparse
import glob
import os
from datetime import datetime
from business_logic.business_logic import BusinessLogicRouter
from config_manager import get_config
from toexcel.toexcel import export_to_excel 
import time

app = FastAPI()
logger = logging.getLogger(__file__)

# 获取配置实例（根据配置文件设置决定是否启用自动重载）
try:
    config = get_config()
except Exception as e:
    logger.error(f"无法加载配置文件，项目必须依赖配置文件才能运行: {e}")
    raise RuntimeError(f"无法加载配置文件，项目必须依赖配置文件才能运行: {e}")

start_mission_time_global = None  # 定义全局变量

# 简化的AI处理API端点
@app.post("/ai-process-excel", 
          description="Process the latest Excel file with AI analysis")
async def ai_process_latest_excel():
    """
    处理download目录下最新的Excel文件并进行AI分析
    通过业务逻辑层进行处理
    """
    global start_mission_time_global
    if not start_mission_time_global:
        raise HTTPException(
            status_code=400,
            detail="请先开始ASR任务"
        )
    task_dir = start_mission_time_global.replace(":", "_").replace(" ", "_").replace("-", "_")
    try:
        # 初始化业务逻辑路由器
        router = BusinessLogicRouter()
        
        # 获取对应的任务处理器
        processor = router.route_to_processor()
        
        
        # 执行完整的业务流程
        result = processor.execute_task_flow(task_dir)
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=f"业务流程执行失败: {result.get('error', '未知错误')}"
            )
        
        return
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"业务逻辑层处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"业务逻辑层处理失败: {str(e)}")

@app.websocket("/asr")
async def websocket_asr(websocket: WebSocket,
                        samplerate: int = Query(config.asr.sample_rate, title="Sample Rate",
                                                description="The sample rate of the audio."),):
    await websocket.accept()
    global start_mission_time_global
    start_mission_time_global = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    asr_stream: ASRStream = await start_asr_stream(samplerate, args, start_mission_time_global)
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
            logger.debug(result.to_dict())
    try:
        await asyncio.gather(task_recv_pcm(), task_send_result())
    except WebSocketDisconnect:
        logger.info("asr: disconnected")
    finally:
        await asr_stream.close()


@app.websocket("/tts")
async def websocket_tts(websocket: WebSocket,
                        samplerate: int = Query(config.asr.sample_rate,
                                                title="Sample Rate",
                                                description="The sample rate of the generated audio."),
                        interrupt: bool = Query(True,
                                                title="Interrupt",
                                                description="Interrupt the current TTS stream when a new text is received."),
                        sid: int = Query(0,
                                         title="Speaker ID",
                                         description="The ID of the speaker to use for TTS."),
                        chunk_size: int = Query(config.tts.chunk_size,
                                                title="Chunk Size",
                                                description="The size of the chunk to send to the client."),
                        speed: float = Query(config.tts.speed,
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
    samplerate: int = Field(config.asr.sample_rate, title="Sample Rate",
                            description="The sample rate of the generated audio.")
    speed: float = Field(config.tts.speed, title="Speed",
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


# 配置管理API端点

class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    key: str = Field(..., description="配置键（支持点号分隔的嵌套键）")
    value: Any = Field(..., description="配置值")

@app.post("/api/config", description="Update configuration")
async def update_config(request: ConfigUpdateRequest):
    """更新配置"""
    try:
        config.set(request.key, request.value)
        config.save()
        
        # 重新验证配置
        if not config.validate():
            raise HTTPException(status_code=400, detail="配置更新后验证失败")
        
        return {
            "status": "success",
            "message": f"配置 {request.key} 更新成功",
            "new_value": config.get(request.key)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"配置更新失败: {str(e)}")

@app.post("/api/config/reload", description="Reload configuration from file")
async def reload_configuration():
    """重新加载配置文件"""
    try:
        from config_manager import reload_config
        reload_config()
        return {
            "status": "success",
            "message": "配置重新加载成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置重新加载失败: {str(e)}")

@app.get("/api/system/status")
async def get_system_status():
    """
    获取系统状态信息
    """
    try:
        # 导入AI处理器并检查ollama服务状态
        from ai_service.ai_api import CarTestDataProcessor
        processor = CarTestDataProcessor()
        ollama_status = processor.check_service_status()
        
        return {
            "api_connection": "Active" if ollama_status else "Inactive",
            "api_connection_status": ollama_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"检查系统状态时出错: {e}")
        return {
            "api_connection": "Error",
            "api_connection_status": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

class ResultsData(BaseModel):
    """接收ResultsData数据的模型"""
    results: List[dict] = Field(..., description="日志数据列表")

@app.post("/api/results", description="Save ResultsData data and export to Excel")
async def get_results_to_excel(results_data: ResultsData):
    """
    接收前端发送的ResultsData数据并导出为Excel
    """
    try:
        results = results_data.results
        
        if not results:
            raise HTTPException(status_code=400, detail="数据为空")
        
        # 转换数据格式以匹配ASR导出函数的期望格式
        # 前端发送的格式: [{"result": "文本", "time": "时间", "idx": 索引}, ...]
        # ASR函数期望的格式: [{"time": "时间", "result": "文本"}, ...]
        combined_results = []
        for result in results:
            combined_results.append({
                "time": result.get("time", ""),
                "result": result.get("result", "")
            })
        global start_mission_time_global
        current_time = start_mission_time_global.replace(":", "_").replace(" ", "_").replace("-", "_")
        filename = f"asr_results_{current_time}.xlsx"

        # 导出到 Excel
        export_to_excel(combined_results, filename, current_time)
        logger.info(f"成功导出 Excel 文件: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"导出 Excel 文件失败: {e}")
        return None

if __name__ == "__main__":
    # 从配置文件获取默认值
    models_root = config.storage.models_dir

    for d in ['.', '..', '../..']:
        if os.path.isdir(f'{d}/models'):
            models_root = f'{d}/models'
            break

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=config.server.port, help="port number")
    parser.add_argument("--addr", type=str,
                        default=config.server.host, help="serve address")

    parser.add_argument("--asr-provider", type=str,
                        default=config.asr.provider, help="asr provider, cpu or cuda")
    parser.add_argument("--tts-provider", type=str,
                        default=config.tts.provider, help="tts provider, cpu or cuda")

    parser.add_argument("--threads", type=int, default=config.processing.threads,
                        help="number of threads")

    parser.add_argument("--models-root", type=str, default=models_root,
                        help="model root directory")

    parser.add_argument("--asr-model", type=str, default=config.asr.model,
                        help="ASR model name: zipformer-bilingual, sensevoice, paraformer-trilingual, paraformer-en, fireredasr")

    parser.add_argument("--asr-lang", type=str, default=config.asr.language,
                        help="ASR language, zh, en, ja, ko, yue")

    parser.add_argument("--tts-model", type=str, default=config.tts.model,
                        help="TTS model name: vits-zh-hf-theresa, vits-melo-tts-zh_en, kokoro-multi-lang-v1_0")

    # 处理调试模式下的参数解析问题
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # 在调试模式下，如果参数解析失败，使用默认值
        if e.code == 2:  # 参数解析错误
            logger.warning("参数解析失败，使用默认配置值")
            args = parser.parse_args([])  # 使用空参数列表，将使用所有默认值
        else:
            # 其他系统退出情况（如 --help），重新抛出异常
            raise

    if args.tts_model == 'vits-melo-tts-zh_en' and args.tts_provider == 'cuda':
        logger.warning(
            "vits-melo-tts-zh_en does not support CUDA fallback to CPU")
        args.tts_provider = 'cpu'

    app.mount("/", app=StaticFiles(directory="./assets", html=True), name="assets")

    # 使用配置的日志设置
    log_config = config.logging_config
    logging.basicConfig(format=log_config.format, level=getattr(logging, log_config.level.upper()))
    
    # 验证配置
    if not config.validate():
        logger.error("配置验证失败，程序退出")
        exit(1)
    
    # logger.info(f"启动服务器: {args.addr}:{args.port}")
    logger.info(f"AI处理: {'启用' if config.ai.enabled else '禁用'}")
    logger.info(f"Excel导出: {'启用' if config.storage.export_excel else '禁用'}")
    
    uvicorn.run(app, host=args.addr, port=args.port)
