"""
配置管理模块
支持YAML配置文件的加载、验证和访问
"""
import yaml
import os
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from pathlib import Path
import logging
import time
import threading

logger = logging.getLogger(__name__)

# 错误信息常量
CONFIG_CONTENT_MISSING = "配置文件内容缺失"
CONFIG_FORMAT_ERROR = "配置文件格式错误"
CONFIG_FILE_NOT_EXISTS = "配置文件不存在"
TASK_CONFIG_MISSING = "任务配置文件缺失"

@dataclass
class AIConfig:
    """AI配置"""
    enabled: bool
    api_url: str
    model_name: str
    timeout: int
    max_retries: int
    options: Optional[Dict[str, Any]]

@dataclass
class ServerConfig:
    """服务器配置"""
    host: str
    port: int
    debug: bool
    auto_reload_config: bool

@dataclass
class StorageConfig:
    """存储配置"""
    download_dir: str
    models_dir: str
    export_excel: bool
    auto_backup: bool

@dataclass
class ASRConfig:
    """ASR配置"""
    provider: str
    model: str
    language: str
    sample_rate: int

@dataclass
class TTSConfig:
    """TTS配置"""
    provider: str
    model: str
    speed: float
    chunk_size: int

@dataclass
class LoggingConfig:
    """日志配置"""
    level: str
    format: str
    log_file: Optional[str]

@dataclass
class ProcessingConfig:
    """处理配置"""
    threads: int
    batch_size: int
    enable_concurrent: bool

@dataclass
class TaskConfig:
    """任务配置"""
    task_info: Optional[Dict[str, str]] = None
    score_mapping: Optional[Dict[str, str]] = None
    rating_thresholds: Optional[Dict[str, float]] = None
    takeover_keywords: Optional[Dict[str, List[str]]] = None
    excel_export: Optional[Dict[str, Any]] = None

@dataclass
class DataProcessingConfig:
    """数据处理配置"""
    current_task_config: str
    ai_processing_enabled: bool
    ai_timeout_per_record: int
    ai_retry_failed_records: bool
    
    # 当前任务配置（运行时加载）
    task_config: Optional[TaskConfig] = None

class Config:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config.yaml", auto_reload: bool = None):
        self.config_path = config_path
        self._config_data: Dict[str, Any] = {}
        self._last_modified = 0
        self._auto_reload = auto_reload  # 如果为None，将从配置文件读取
        self._reload_thread = None
        self.load()
        
        # 如果auto_reload未指定，从配置文件读取
        if self._auto_reload is None:
            self._auto_reload = self.server.auto_reload_config
        
        if self._auto_reload:
            self._start_file_watcher()
    
    def _get_error_message(self, simple_msg: str, detailed_msg: str) -> str:
        """根据配置文件中的日志级别返回适当的错误信息"""
        try:
            # 尝试从配置数据中获取日志级别
            if self._config_data and 'logging' in self._config_data:
                log_level_str = self._config_data['logging'].get('level', 'INFO')
                # 将字符串级别转换为数字级别
                log_level = getattr(logging, log_level_str.upper(), logging.INFO)
                
                # DEBUG级别显示详细信息，其他级别显示简单信息
                if log_level <= logging.DEBUG:
                    return detailed_msg
                else:
                    return simple_msg
            else:
                # 如果配置还未加载，默认返回简单信息
                return simple_msg
        except Exception:
            # 出现任何异常时，返回简单信息
            return simple_msg
        
    def load(self) -> None:
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_path):
                error_msg = self._get_error_message(
                    CONFIG_FILE_NOT_EXISTS,
                    f"配置文件不存在: {self.config_path}，项目必须依赖配置文件才能运行"
                )
                raise FileNotFoundError(error_msg)
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
                
            # 检查配置文件是否为空
            if not self._config_data:
                error_msg = self._get_error_message(
                    CONFIG_CONTENT_MISSING,
                    f"配置文件为空: {self.config_path}"
                )
                raise ValueError(error_msg)
                
            # 验证必要的配置段是否存在
            required_sections = ['ai', 'server', 'storage', 'asr', 'tts', 'logging', 'processing', 'data_processing']
            for section in required_sections:
                if section not in self._config_data:
                    error_msg = self._get_error_message(
                        CONFIG_CONTENT_MISSING,
                        f"配置文件中缺少必要的配置段: {section}"
                    )
                    raise ValueError(error_msg)
            
            # 验证AI配置中的必要字段
            ai_config = self._config_data.get('ai', {})
            required_ai_fields = ['api_url', 'model_name', 'timeout', 'max_retries', 'options']
            for field in required_ai_fields:
                if field not in ai_config:
                    error_msg = self._get_error_message(
                        CONFIG_CONTENT_MISSING,
                        f"配置文件中缺少必要的AI配置字段: ai.{field}"
                    )
                    raise ValueError(error_msg)
                
            # 更新最后修改时间
            self._last_modified = os.path.getmtime(self.config_path)
            logger.info(f"配置文件加载成功: {self.config_path}")
            
        except yaml.YAMLError as e:
            logger.error(f"配置文件格式错误: {e}")
            error_msg = self._get_error_message(
                CONFIG_FORMAT_ERROR,
                f"配置文件格式错误: {e}"
            )
            raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    def save(self) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            logger.info(f"配置文件保存成功: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self._config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        config = self._config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
    
    @property
    def ai(self) -> AIConfig:
        """AI配置"""
        ai_data = self._config_data.get('ai')
        if not ai_data:
            error_msg = self._get_error_message(
                CONFIG_CONTENT_MISSING,
                "配置文件中缺少ai配置段"
            )
            raise ValueError(error_msg)
            
        # 检查必要字段
        required_fields = ['enabled', 'api_url', 'model_name', 'timeout', 'max_retries', 'options']
        for field in required_fields:
            if field not in ai_data:
                error_msg = self._get_error_message(
                    CONFIG_CONTENT_MISSING,
                    f"配置文件中缺少必要的AI配置字段: ai.{field}"
                )
                raise ValueError(error_msg)
        
        return AIConfig(
            enabled=ai_data['enabled'],
            api_url=ai_data['api_url'],
            model_name=ai_data['model_name'],
            timeout=ai_data['timeout'],
            max_retries=ai_data['max_retries'],
            options=ai_data['options']
        )
    
    @property
    def server(self) -> ServerConfig:
        """服务器配置"""
        server_data = self._config_data.get('server')
        if not server_data:
            error_msg = self._get_error_message(
                CONFIG_CONTENT_MISSING,
                "配置文件中缺少server配置段"
            )
            raise ValueError(error_msg)
            
        required_fields = ['host', 'port', 'debug', 'auto_reload_config']
        for field in required_fields:
            if field not in server_data:
                error_msg = self._get_error_message(
                    CONFIG_CONTENT_MISSING,
                    f"配置文件中缺少必要的服务器配置字段: server.{field}"
                )
                raise ValueError(error_msg)
        
        return ServerConfig(
            host=server_data['host'],
            port=server_data['port'],
            debug=server_data['debug'],
            auto_reload_config=server_data['auto_reload_config']
        )
    
    @property
    def storage(self) -> StorageConfig:
        """存储配置"""
        storage_data = self._config_data.get('storage')
        if not storage_data:
            error_msg = self._get_error_message(
                CONFIG_CONTENT_MISSING,
                "配置文件中缺少storage配置段"
            )
            raise ValueError(error_msg)
            
        required_fields = ['download_dir', 'models_dir', 'export_excel', 'auto_backup']
        for field in required_fields:
            if field not in storage_data:
                error_msg = self._get_error_message(
                    CONFIG_CONTENT_MISSING,
                    f"配置文件中缺少必要的存储配置字段: storage.{field}"
                )
                raise ValueError(error_msg)
        
        return StorageConfig(
            download_dir=storage_data['download_dir'],
            models_dir=storage_data['models_dir'],
            export_excel=storage_data['export_excel'],
            auto_backup=storage_data['auto_backup']
        )
    
    @property
    def asr(self) -> ASRConfig:
        """ASR配置"""
        asr_data = self._config_data.get('asr')
        if not asr_data:
            error_msg = self._get_error_message(
                CONFIG_CONTENT_MISSING,
                "配置文件中缺少asr配置段"
            )
            raise ValueError(error_msg)
            
        required_fields = ['provider', 'model', 'language', 'sample_rate']
        for field in required_fields:
            if field not in asr_data:
                error_msg = self._get_error_message(
                    CONFIG_CONTENT_MISSING,
                    f"配置文件中缺少必要的ASR配置字段: asr.{field}"
                )
                raise ValueError(error_msg)
        
        return ASRConfig(
            provider=asr_data['provider'],
            model=asr_data['model'],
            language=asr_data['language'],
            sample_rate=asr_data['sample_rate']
        )
    
    @property
    def tts(self) -> TTSConfig:
        """TTS配置"""
        tts_data = self._config_data.get('tts')
        if not tts_data:
            error_msg = self._get_error_message(
                CONFIG_CONTENT_MISSING,
                "配置文件中缺少tts配置段"
            )
            raise ValueError(error_msg)
            
        required_fields = ['provider', 'model', 'speed', 'chunk_size']
        for field in required_fields:
            if field not in tts_data:
                error_msg = self._get_error_message(
                    CONFIG_CONTENT_MISSING,
                    f"配置文件中缺少必要的TTS配置字段: tts.{field}"
                )
                raise ValueError(error_msg)
        
        return TTSConfig(
            provider=tts_data['provider'],
            model=tts_data['model'],
            speed=tts_data['speed'],
            chunk_size=tts_data['chunk_size']
        )
    
    @property
    def logging_config(self) -> LoggingConfig:
        """日志配置"""
        log_data = self._config_data.get('logging')
        if not log_data:
            error_msg = self._get_error_message(
                CONFIG_CONTENT_MISSING,
                "配置文件中缺少logging配置段"
            )
            raise ValueError(error_msg)
        
        required_fields = ['level', 'format']
        for field in required_fields:
            if field not in log_data:
                error_msg = self._get_error_message(
                    CONFIG_CONTENT_MISSING,
                    f"配置文件中缺少必要的日志配置字段: logging.{field}"
                )
                raise ValueError(error_msg)
        
        return LoggingConfig(
            level=log_data['level'],
            format=log_data['format'],
            log_file=log_data.get('log_file')
        )
    
    @property
    def processing(self) -> ProcessingConfig:
        """处理配置"""
        proc_data = self._config_data.get('processing')
        if not proc_data:
            error_msg = self._get_error_message(
                CONFIG_CONTENT_MISSING,
                "配置文件中缺少processing配置段"
            )
            raise ValueError(error_msg)
        
        required_fields = ['threads', 'batch_size', 'enable_concurrent']
        for field in required_fields:
            if field not in proc_data:
                error_msg = self._get_error_message(
                    CONFIG_CONTENT_MISSING,
                    f"配置文件中缺少必要的处理配置字段: processing.{field}"
                )
                raise ValueError(error_msg)
        
        return ProcessingConfig(
            threads=proc_data['threads'],
            batch_size=proc_data['batch_size'],
            enable_concurrent=proc_data['enable_concurrent']
        )
    
    @property
    def data_processing(self) -> DataProcessingConfig:
        """数据处理配置"""
        dp_data = self._config_data.get('data_processing')
        if not dp_data:
            error_msg = self._get_error_message(
                CONFIG_CONTENT_MISSING,
                "配置文件中缺少data_processing配置段"
            )
            raise ValueError(error_msg)
        
        required_fields = ['current_task_config', 'ai_processing_enabled', 'ai_timeout_per_record', 'ai_retry_failed_records']
        for field in required_fields:
            if field not in dp_data:
                error_msg = self._get_error_message(
                    CONFIG_CONTENT_MISSING,
                    f"配置文件中缺少必要的数据处理配置字段: data_processing.{field}"
                )
                raise ValueError(error_msg)
        
        config = DataProcessingConfig(
            current_task_config=dp_data['current_task_config'],
            ai_processing_enabled=dp_data['ai_processing_enabled'],
            ai_timeout_per_record=dp_data['ai_timeout_per_record'],
            ai_retry_failed_records=dp_data['ai_retry_failed_records']
        )
        
        # 加载当前任务配置
        task_config = self.load_task_config(config.current_task_config)
        config.task_config = task_config
        
        return config
    
    def load_task_config(self, task_name: str) -> TaskConfig:
        """加载指定的任务配置文件"""
        task_config_path = f"./toexcel/task_configs/{task_name}.yaml"
        
        if not os.path.exists(task_config_path):
            error_msg = self._get_error_message(
                TASK_CONFIG_MISSING,
                f"任务配置文件不存在: {task_config_path}，项目必须依赖任务配置文件才能运行"
            )
            raise FileNotFoundError(error_msg)
        
        try:
            with open(task_config_path, 'r', encoding='utf-8') as f:
                task_data = yaml.safe_load(f)
            
            if not task_data:
                error_msg = self._get_error_message(
                    TASK_CONFIG_MISSING,
                    f"任务配置文件为空: {task_config_path}"
                )
                raise ValueError(error_msg)
            
            required_fields = ['task_info', 'score_mapping', 'rating_thresholds', 'takeover_keywords', 'excel_export']
            for field in required_fields:
                if field not in task_data:
                    error_msg = self._get_error_message(
                        TASK_CONFIG_MISSING,
                        f"任务配置文件中缺少必要字段: {field}"
                    )
                    raise ValueError(error_msg)
            
            return TaskConfig(
                task_info=task_data['task_info'],
                score_mapping=task_data['score_mapping'],
                rating_thresholds=task_data['rating_thresholds'],
                takeover_keywords=task_data['takeover_keywords'],
                excel_export=task_data['excel_export']
            )
            
        except Exception as e:
            logger.error(f"加载任务配置失败: {e}")
            raise
    
    def validate(self) -> bool:
        """验证配置的有效性"""
        try:
            # 验证端口号
            port = self.server.port
            if not (1 <= port <= 65535):
                raise ValueError(f"端口号无效: {port}")
            
            # 骜证目录
            download_dir = self.storage.download_dir
            if not os.path.exists(download_dir):
                os.makedirs(download_dir, exist_ok=True)
                logger.info(f"创建下载目录: {download_dir}")
            
            models_dir = self.storage.models_dir
            if not os.path.exists(models_dir):
                logger.warning(f"模型目录不存在: {models_dir}")
            
            # 验证AI配置
            if self.ai.enabled and not self.ai.api_url:
                raise ValueError("AI已启用但未配置API地址")
            
            # 验证采样率
            if self.asr.sample_rate <= 0:
                raise ValueError(f"采样率无效: {self.asr.sample_rate}")
            
            # 验证TTS速度
            if self.tts.speed <= 0:
                raise ValueError(f"TTS速度无效: {self.tts.speed}")
            
            logger.info("配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False

    def _start_file_watcher(self) -> None:
        """启动文件监听线程"""
        if self._reload_thread is not None:
            return
            
        def watch_file():
            while self._auto_reload:
                try:
                    if os.path.exists(self.config_path):
                        current_modified = os.path.getmtime(self.config_path)
                        if current_modified > self._last_modified:
                            logger.info("检测到配置文件变化，重新加载...")
                            self.load()
                            self._last_modified = current_modified
                except Exception as e:
                    logger.error(f"文件监听出错: {e}")
                
                time.sleep(1)  # 每秒检查一次
        
        self._reload_thread = threading.Thread(target=watch_file, daemon=True)
        self._reload_thread.start()
        logger.info("配置文件自动重载已启用")
    
    def stop_file_watcher(self) -> None:
        """停止文件监听"""
        self._auto_reload = False
        if self._reload_thread:
            self._reload_thread = None
            logger.info("配置文件自动重载已停止")

# 全局配置实例（根据配置文件决定是否启用自动重载）
config = Config()

def get_config(auto_reload: bool = None) -> Config:
    """获取全局配置实例"""
    global config
    if auto_reload is not None and auto_reload != config._auto_reload:
        # 如果指定了不同的auto_reload设置，创建新实例
        return Config(auto_reload=auto_reload)
    return config

def reload_config() -> None:
    """重新加载配置"""
    global config
    config.load()
    config.validate()
