"""
SQL加载器 - 统一管理和加载SQL文件
"""
import os
import logging
from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

class SQLLoader:
    """SQL文件加载器"""
    
    def __init__(self, sql_dir: str = None):
        """
        初始化SQL加载器
        
        Args:
            sql_dir: SQL文件目录，默认为当前目录下的sql文件夹
        """
        if sql_dir is None:
            # 获取当前文件所在目录
            current_dir = Path(__file__).parent
            sql_dir = current_dir / 'sql'
        
        self.sql_dir = Path(sql_dir)
        self._validate_sql_directory()
        
        logger.info(f"SQL加载器初始化完成，SQL目录: {self.sql_dir}")
    
    def _validate_sql_directory(self):
        """验证SQL目录是否存在"""
        if not self.sql_dir.exists():
            raise FileNotFoundError(f"SQL目录不存在: {self.sql_dir}")
        
        if not self.sql_dir.is_dir():
            raise NotADirectoryError(f"SQL路径不是目录: {self.sql_dir}")
    
    @lru_cache(maxsize=32)
    def load_sql(self, filename: str) -> str:
        """
        加载SQL文件内容
        
        Args:
            filename: SQL文件名（可以带.sql扩展名，也可以不带）
            
        Returns:
            SQL文件内容
            
        Raises:
            FileNotFoundError: 当SQL文件不存在时
            IOError: 当读取文件失败时
        """
        # 确保文件名有.sql扩展名
        if not filename.endswith('.sql'):
            filename += '.sql'
        
        sql_file_path = self.sql_dir / filename
        
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.debug(f"成功加载SQL文件: {filename}")
            return content
            
        except FileNotFoundError:
            logger.error(f"SQL文件不存在: {filename}")
            raise FileNotFoundError(f"SQL文件不存在: {sql_file_path}")
        
        except IOError as e:
            logger.error(f"读取SQL文件失败: {filename}, 错误: {e}")
            raise IOError(f"读取SQL文件失败: {sql_file_path}, 错误: {e}")
    
    def load_sql_with_params(self, filename: str, params: Dict[str, any] = None) -> str:
        """
        加载SQL文件并进行参数替换
        
        Args:
            filename: SQL文件名
            params: 参数字典，用于替换SQL中的占位符
            
        Returns:
            参数替换后的SQL内容
        """
        sql_content = self.load_sql(filename)
        
        if params:
            try:
                # 使用format进行参数替换
                sql_content = sql_content.format(**params)
                logger.debug(f"SQL参数替换完成: {filename}")
            except KeyError as e:
                logger.error(f"SQL参数替换失败，缺少参数: {e}")
                raise KeyError(f"SQL参数替换失败，缺少参数: {e}")
        
        return sql_content
    
    def list_sql_files(self) -> list:
        """
        列出所有可用的SQL文件
        
        Returns:
            SQL文件名列表
        """
        try:
            sql_files = []
            for file_path in self.sql_dir.glob('*.sql'):
                sql_files.append(file_path.name)
            
            logger.info(f"发现 {len(sql_files)} 个SQL文件")
            return sorted(sql_files)
            
        except Exception as e:
            logger.error(f"列出SQL文件失败: {e}")
            return []
    
    def reload_sql(self, filename: str) -> str:
        """
        重新加载SQL文件（清除缓存）
        
        Args:
            filename: SQL文件名
            
        Returns:
            重新加载的SQL内容
        """
        # 清除缓存
        self.load_sql.cache_clear()
        
        # 重新加载
        return self.load_sql(filename)
    
    def get_sql_info(self, filename: str) -> Dict[str, any]:
        """
        获取SQL文件信息
        
        Args:
            filename: SQL文件名
            
        Returns:
            包含文件信息的字典
        """
        if not filename.endswith('.sql'):
            filename += '.sql'
        
        sql_file_path = self.sql_dir / filename
        
        try:
            stat = sql_file_path.stat()
            content = self.load_sql(filename)
            
            return {
                'filename': filename,
                'path': str(sql_file_path),
                'size': stat.st_size,
                'modified_time': stat.st_mtime,
                'line_count': len(content.splitlines()),
                'character_count': len(content),
                'exists': True
            }
            
        except FileNotFoundError:
            return {
                'filename': filename,
                'path': str(sql_file_path),
                'exists': False
            }
    
    def validate_sql_syntax(self, filename: str) -> Dict[str, any]:
        """
        验证SQL文件语法（基础检查）
        
        Args:
            filename: SQL文件名
            
        Returns:
            验证结果字典
        """
        try:
            content = self.load_sql(filename)
            
            # 基础语法检查
            issues = []
            
            # 检查是否有未闭合的括号
            if content.count('(') != content.count(')'):
                issues.append("括号不匹配")
            
            # 检查是否有未闭合的引号
            single_quotes = content.count("'")
            if single_quotes % 2 != 0:
                issues.append("单引号不匹配")
            
            # 检查常见的SQL关键字
            content_upper = content.upper()
            if 'SELECT' not in content_upper and 'INSERT' not in content_upper and 'UPDATE' not in content_upper and 'DELETE' not in content_upper:
                issues.append("没有发现常见的SQL关键字")
            
            return {
                'filename': filename,
                'valid': len(issues) == 0,
                'issues': issues,
                'line_count': len(content.splitlines())
            }
            
        except Exception as e:
            return {
                'filename': filename,
                'valid': False,
                'issues': [f"文件读取错误: {str(e)}"],
                'line_count': 0
            }

# 全局SQL加载器实例
_sql_loader = None

def get_sql_loader(sql_dir: str = None) -> SQLLoader:
    """
    获取SQL加载器单例
    
    Args:
        sql_dir: SQL文件目录
        
    Returns:
        SQL加载器实例
    """
    global _sql_loader
    
    if _sql_loader is None:
        _sql_loader = SQLLoader(sql_dir)
    
    return _sql_loader

# 便捷函数
def load_sql(filename: str, params: Dict[str, any] = None) -> str:
    """
    便捷函数：加载SQL文件
    
    Args:
        filename: SQL文件名
        params: 参数字典
        
    Returns:
        SQL内容
    """
    loader = get_sql_loader()
    
    if params:
        return loader.load_sql_with_params(filename, params)
    else:
        return loader.load_sql(filename)

def list_available_sql_files() -> list:
    """
    便捷函数：列出可用的SQL文件
    
    Returns:
        SQL文件名列表
    """
    loader = get_sql_loader()
    return loader.list_sql_files()
