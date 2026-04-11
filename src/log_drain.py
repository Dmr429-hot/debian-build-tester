"""
日志关键片段提取器
基于 Drain-like 思想，针对构建日志进行快速关键信息提取
"""
from typing import List, Tuple
import re


class LogExtractor:
    """提取构建日志中的关键错误信息"""
    
    # 错误关键词模式 (注意顺序：更具体的模式先匹配)
    ERROR_PATTERNS = [
        # 链接错误必须在依赖缺失前检查（因为链接错误可能包含 undefined）
        (r"(?i)(undefined reference|unresolved symbol|relocation|collect2.*error)", "LINK_ERROR"),
        # 依赖缺失
        (r"(?i)(missing|not found|no such file|could not find|not installed)", "MISSING_DEP"),
        # 测试失败
        (r"(?i)(test.*fail|assertion.*fail|expected.*got)", "TEST_FAIL"),
        # 通用错误
        (r"(?i)(error|failed|cannot)", "ERROR"),
        # 警告作为错误
        (r"(?i)(warning:.*error|treated as error)", "WARN_AS_ERROR"),
    ]
    
    # 需要过滤掉的行（日志噪音）
    NOISE_PATTERNS = [
        r"^$",  # 空行
        r"^[-=+\s]*$",  # 分隔线
        r"^(In|During) ",  # 统计信息开头
        r"^Scanning",  # 扫描信息
        r"^\s*\|",  # 表格行
    ]
    
    @staticmethod
    def tokenize_log_line(line: str) -> str:
        """
        将日志行标准化：替换数字、路径等为通配符，便于模式识别
        例如：/home/user/file.c:123 -> /home/user/file.c:<NUM>
        """
        # 替换数字为 <NUM>
        line = re.sub(r'\b\d+\b', '<NUM>', line)
        # 替换 IPv4 地址
        line = re.sub(r'\d+\.\d+\.\d+\.\d+', '<IP>', line)
        # 替换文件路径（保留文件名）
        line = re.sub(r'(/[^ ]*)+/([^ /]+)', r'/.../<PATH>/\2', line)
        return line
    
    @staticmethod
    def is_noise(line: str) -> bool:
        """检查该行是否是日志噪音"""
        stripped = line.strip()
        if not stripped:
            return True
        for pattern in LogExtractor.NOISE_PATTERNS:
            if re.search(pattern, stripped):
                return True
        return False
    
    @staticmethod
    def extract_error_context(lines: List[str], error_idx: int, context_lines: int = 2) -> str:
        """
        提取错误行及其前后文
        :param lines: 日志行列表
        :param error_idx: 错误行索引
        :param context_lines: 前后各保留几行
        :return: 前后文组成的字符串
        """
        start = max(0, error_idx - context_lines)
        end = min(len(lines), error_idx + context_lines + 1)
        return '\n'.join(lines[start:end])
    
    @classmethod
    def extract_key_logs(cls, full_log: str, max_snippets: int = 5) -> Tuple[str, List[str]]:
        """
        从完整日志中提取关键错误片段
        :param full_log: 完整日志文本
        :param max_snippets: 最多提取几个关键片段
        :return: (提取类型, [关键片段列表])
        """
        lines = full_log.split('\n')
        
        # 过滤噪音行
        clean_lines = [line for line in lines if not cls.is_noise(line)]
        
        if not clean_lines:
            return "UNKNOWN", ["[日志全为噪音或为空]"]
        
        # 识别错误行
        error_info = []  # (错误类型, 行索引, 原始行)
        
        for idx, line in enumerate(clean_lines):
            for pattern, error_type in cls.ERROR_PATTERNS:
                if re.search(pattern, line):
                    error_info.append((error_type, idx, line))
                    break
        
        if not error_info:
            # 如果没有明显错误关键词，采用启发式方法：取最后几行（通常包含错误信息）
            key_snippets = clean_lines[-5:] if len(clean_lines) >= 5 else clean_lines
            return "UNKNOWN", key_snippets
        
        # 按错误类型分组
        error_groups = {}
        for error_type, idx, line in error_info:
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append((idx, line))
        
        # 确定主错误类型（优先级）
        priority = {
            "MISSING_DEP": 1,
            "ERROR": 2,
            "LINK_ERROR": 3,
            "WARN_AS_ERROR": 4,
            "TEST_FAIL": 5,
        }
        main_error_type = min(error_groups.keys(), key=lambda x: priority.get(x, 999))
        
        # 提取关键片段
        key_snippets = []
        seen_snippets = set()
        
        # 首先收集主错误类型的片段
        for idx, line in error_groups[main_error_type][:max_snippets]:
            snippet = cls.extract_error_context(clean_lines, idx, context_lines=2)
            # 去重（基于标准化后的行）
            snippet_token = cls.tokenize_log_line(snippet)
            if snippet_token not in seen_snippets:
                key_snippets.append(snippet)
                seen_snippets.add(snippet_token)
        
        # 如果片段不足，补充其他错误类型
        if len(key_snippets) < max_snippets:
            for error_type in sorted(error_groups.keys(), key=lambda x: priority.get(x, 999)):
                if error_type == main_error_type:
                    continue
                for idx, line in error_groups[error_type]:
                    if len(key_snippets) >= max_snippets:
                        break
                    snippet = cls.extract_error_context(clean_lines, idx, context_lines=2)
                    snippet_token = cls.tokenize_log_line(snippet)
                    if snippet_token not in seen_snippets:
                        key_snippets.append(snippet)
                        seen_snippets.add(snippet_token)
        
        return main_error_type, key_snippets
    
    @classmethod
    def classify_failure_reason(cls, full_log: str, error_type: str) -> str:
        """
        根据日志内容和错误类型推断失败原因
        :param full_log: 完整日志
        :param error_type: 主错误类型
        :return: 失败原因描述
        """
        log_lower = full_log.lower()
        
        if error_type == "LINK_ERROR":
            return "链接错误"
        
        elif error_type == "MISSING_DEP":
            return "依赖缺失"
        
        elif error_type == "TEST_FAIL":
            return "测试失败"
        
        elif error_type == "WARN_AS_ERROR":
            return "警告作为错误"
        
        elif error_type == "ERROR":
            # 进一步细化
            if "undefined reference" in log_lower or "unresolved symbol" in log_lower:
                return "链接错误"
            elif "not found" in log_lower or "missing" in log_lower or "could not find" in log_lower:
                return "依赖缺失"
            elif "syntax" in log_lower or "parse error" in log_lower:
                return "编译错误"
            elif "assertion" in log_lower or "test" in log_lower:
                return "测试失败"
            return "编译错误"
        
        return "未知"


def extract_key_log_snippet(
    full_log: str,
    failure_stage: str = "UNKNOWN",
    max_length: int = 1000,
) -> Tuple[str, str]:

    error_type, snippets = LogExtractor.extract_key_logs(full_log, max_snippets=5)
    failure_reason = LogExtractor.classify_failure_reason(full_log, error_type)
    
    # 拼接片段
    combined = "\n---\n".join(snippets)
    if len(combined) > max_length:
        combined = combined[:max_length] + "...[截断]"
    
    return failure_reason, combined
