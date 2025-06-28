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

@dataclass
class AIConfig:
    """AI配置"""
    enabled: bool = True
    api_url: str = "http://localhost:11434"
    model_name: str = "qwen2.5:7b"
    timeout: int = 30
    max_retries: int = 3

@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "localhost"
    port: int = 8000
    debug: bool = False
    auto_reload_config: bool = False

@dataclass
class StorageConfig:
    """存储配置"""
    download_dir: str = "./download"
    models_dir: str = "./models"
    export_excel: bool = True
    auto_backup: bool = True

@dataclass
class ASRConfig:
    """ASR配置"""
    provider: str = "cpu"
    model: str = "fireredasr"
    language: str = "zh"
    sample_rate: int = 16000

@dataclass
class TTSConfig:
    """TTS配置"""
    provider: str = "cpu"
    model: str = "vits-zh-hf-theresa"
    speed: float = 1.0
    chunk_size: int = 1024

@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(levelname)s: %(asctime)s %(name)s:%(lineno)s %(message)s"
    log_file: Optional[str] = None

@dataclass
class ProcessingConfig:
    """处理配置"""
    threads: int = 2
    batch_size: int = 100
    enable_concurrent: bool = True

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
    current_task_config: str = "driving_evaluation"
    ai_processing_enabled: bool = True
    ai_timeout_per_record: int = 30
    ai_retry_failed_records: bool = False
    
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
        
    def load(self) -> None:
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"配置文件不存在: {self.config_path}，将使用默认配置")
                self._create_default_config()
                return
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
                
            # 更新最后修改时间
            self._last_modified = os.path.getmtime(self.config_path)
            logger.info(f"配置文件加载成功: {self.config_path}")
            
        except yaml.YAMLError as e:
            logger.error(f"配置文件格式错误: {e}")
            raise ValueError(f"配置文件格式错误: {e}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    def _create_default_config(self) -> None:
        """创建默认配置"""
        default_config = {
            'ai': {
                'enabled': True,
                'api_url': 'http://localhost:11434',
                'model_name': 'qwen2.5:7b',
                'timeout': 30,
                'max_retries': 3
            },
            'server': {
                'host': 'localhost',
                'port': 8000,
                'debug': False,
                'auto_reload_config': False
            },
            'storage': {
                'download_dir': './download',
                'models_dir': './models',
                'export_excel': True,
                'auto_backup': True
            },
            'asr': {
                'provider': 'cpu',
                'model': 'fireredasr',
                'language': 'zh',
                'sample_rate': 16000
            },
            'tts': {
                'provider': 'cpu',
                'model': 'vits-zh-hf-theresa',
                'speed': 1.0,
                'chunk_size': 1024
            },
            'logging': {
                'level': 'INFO',
                'format': '%(levelname)s: %(asctime)s %(name)s:%(lineno)s %(message)s',
                'log_file': None
            },
            'processing': {
                'threads': 2,
                'batch_size': 100,
                'enable_concurrent': True
            },
            'data_processing': {
                'score_mapping': {
                    '压力性': 'Mental_Load',
                    '可预测性': 'Predicatabl', 
                    '响应性': 'Timely_Response',
                    '舒适性': 'Comfort',
                    '效率性': 'Efficiency',
                    '功能性': 'Features',
                    '安全性': 'safety'
                },
                'rating_thresholds': {
                    'excellent': 8.0,
                    'good': 7.0,
                    'fair': 5.0
                },
                'takeover_keywords': {
                    '危险接管': ['危险接管', '紧急接管', '安全接管'],
                    '车机接管': ['车机接管', '系统接管', '自动接管'],
                    '人为接管': ['人为接管', '手动接管', '优化接管']
                },
                'excel_export': {
                    'enabled': True,
                    'include_statistics': True,
                    'default_columns': ['time', 'comment', 'function', 'Mental_Load', 'Predicatabl', 'Timely_Response', 'Comfort', 'Efficiency', 'Features', 'safety', '是否剪辑']
                },
                'ai_processing': {
                    'enabled': True,
                    'timeout_per_record': 30,
                    'retry_failed_records': False
                }
            }
        }
        
        self._config_data = default_config
        self.save()
    
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
        ai_data = self._config_data.get('ai', {})
        return AIConfig(
            enabled=ai_data.get('enabled', True),
            api_url=ai_data.get('api_url', 'http://localhost:11434'),
            model_name=ai_data.get('model_name', 'qwen2.5:7b'),
            timeout=ai_data.get('timeout', 30),
            max_retries=ai_data.get('max_retries', 3)
        )
    
    @property
    def server(self) -> ServerConfig:
        """服务器配置"""
        server_data = self._config_data.get('server', {})
        return ServerConfig(
            host=server_data.get('host', 'localhost'),
            port=server_data.get('port', 8000),
            debug=server_data.get('debug', False),
            auto_reload_config=server_data.get('auto_reload_config', False)
        )
    
    @property
    def storage(self) -> StorageConfig:
        """存储配置"""
        storage_data = self._config_data.get('storage', {})
        return StorageConfig(
            download_dir=storage_data.get('download_dir', './download'),
            models_dir=storage_data.get('models_dir', './models'),
            export_excel=storage_data.get('export_excel', True),
            auto_backup=storage_data.get('auto_backup', True)
        )
    
    @property
    def asr(self) -> ASRConfig:
        """ASR配置"""
        asr_data = self._config_data.get('asr', {})
        return ASRConfig(
            provider=asr_data.get('provider', 'cpu'),
            model=asr_data.get('model', 'fireredasr'),
            language=asr_data.get('language', 'zh'),
            sample_rate=asr_data.get('sample_rate', 16000)
        )
    
    @property
    def tts(self) -> TTSConfig:
        """TTS配置"""
        tts_data = self._config_data.get('tts', {})
        return TTSConfig(
            provider=tts_data.get('provider', 'cpu'),
            model=tts_data.get('model', 'vits-zh-hf-theresa'),
            speed=tts_data.get('speed', 1.0),
            chunk_size=tts_data.get('chunk_size', 1024)
        )
    
    @property
    def logging_config(self) -> LoggingConfig:
        """日志配置"""
        log_data = self._config_data.get('logging', {})
        return LoggingConfig(
            level=log_data.get('level', 'INFO'),
            format=log_data.get('format', '%(levelname)s: %(asctime)s %(name)s:%(lineno)s %(message)s'),
            log_file=log_data.get('log_file')
        )
    
    @property
    def processing(self) -> ProcessingConfig:
        """处理配置"""
        proc_data = self._config_data.get('processing', {})
        return ProcessingConfig(
            threads=proc_data.get('threads', 2),
            batch_size=proc_data.get('batch_size', 100),
            enable_concurrent=proc_data.get('enable_concurrent', True)
        )
    
    @property
    def data_processing(self) -> DataProcessingConfig:
        """数据处理配置"""
        dp_data = self._config_data.get('data_processing', {})
        config = DataProcessingConfig(
            current_task_config=dp_data.get('current_task_config', 'driving_evaluation'),
            ai_processing_enabled=dp_data.get('ai_processing_enabled', True),
            ai_timeout_per_record=dp_data.get('ai_timeout_per_record', 30),
            ai_retry_failed_records=dp_data.get('ai_retry_failed_records', False)
        )
        
        # 加载当前任务配置
        task_config = self.load_task_config(config.current_task_config)
        config.task_config = task_config
        
        return config
    
    def load_task_config(self, task_name: str) -> TaskConfig:
        """加载指定的任务配置文件"""
        task_config_path = f"./toexcel/task_configs/{task_name}.yaml"
        
        try:
            if not os.path.exists(task_config_path):
                logger.warning(f"任务配置文件不存在: {task_config_path}，使用默认配置")
                return self._get_default_task_config()
            
            with open(task_config_path, 'r', encoding='utf-8') as f:
                task_data = yaml.safe_load(f) or {}
            
            return TaskConfig(
                task_info=task_data.get('task_info', {}),
                score_mapping=task_data.get('score_mapping', {}),
                rating_thresholds=task_data.get('rating_thresholds', {}),
                takeover_keywords=task_data.get('takeover_keywords', {}),
                excel_export=task_data.get('excel_export', {})
            )
            
        except Exception as e:
            logger.error(f"加载任务配置失败: {e}")
            return self._get_default_task_config()
    
    def _get_default_task_config(self) -> TaskConfig:
        """获取默认任务配置"""
        return TaskConfig(
            task_info={
                'name': '默认任务',
                'description': '默认数据处理任务',
                'version': '1.0'
            },
            score_mapping={
                '压力性': 'Mental_Load',
                '可预测性': 'Predicatabl', 
                '响应性': 'Timely_Response',
                '舒适性': 'Comfort',
                '效率性': 'Efficiency',
                '功能性': 'Features',
                '安全性': 'safety'
            },
            rating_thresholds={
                'excellent': 8.0,
                'good': 7.0,
                'fair': 5.0
            },
            takeover_keywords={
                '危险接管': ['危险接管', '紧急接管', '安全接管'],
                '车机接管': ['车机接管', '系统接管', '自动接管'],
                '人为接管': ['人为接管', '手动接管', '优化接管']
            },
            excel_export={
                'enabled': True,
                'include_statistics': True,
                'default_columns': ['time', 'comment', 'function', 'Mental_Load', 'Predicatabl', 'Timely_Response', 'Comfort', 'Efficiency', 'Features', 'safety', '是否剪辑']
            }
        )
    
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
