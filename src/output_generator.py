"""
输出生成模块：从 JSONL 读取记录，生成 success.csv 和 failure.csv
"""
import json
import csv
from pathlib import Path
from typing import List, Dict, Any


def read_jsonl_records(jsonl_path: Path) -> List[Dict[str, Any]]:
    """
    读取 JSONL 文件中的所有记录
    :param jsonl_path: JSONL 文件路径
    :return: 记录列表
    """
    records = []
    if not jsonl_path.exists():
        return records
    
    with jsonl_path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError:
                    continue
    
    return records


def generate_success_csv(records: List[Dict[str, Any]], output_path: Path) -> int:
    """
    生成成功构建的 CSV 文件
    :param records: 所有构建记录
    :param output_path: 输出文件路径
    :return: 成功记录数
    """
    success_records = [r for r in records if r.get('build_status') == 'OK']
    
    if not success_records:
        # 即使没有成功，也创建空的 CSV 文件（带表头）
        with output_path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['软件包名', 'GitHub 链接', '类型', '是否调用 AI', '成功方式'])
        return 0
    
    with output_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 写入表头
        writer.writerow(['软件包名', 'GitHub 链接', '类型', '是否调用 AI', '成功方式'])
        
        # 写入数据行
        for record in success_records:
            row = [
                record.get('repo_name', ''),
                record.get('repo_url', ''),
                record.get('build_type', 'OTHER'),
                '否',  # 是否调用 AI - 固定
                'DIRECT_SUCCESS'  # 成功方式 - 固定
            ]
            writer.writerow(row)
    
    return len(success_records)


def generate_failure_csv(records: List[Dict[str, Any]], output_path: Path) -> int:
    """
    生成失败构建的 CSV 文件
    :param records: 所有构建记录
    :param output_path: 输出文件路径
    :return: 失败记录数
    """
    failure_records = [r for r in records if r.get('build_status') != 'OK']
    
    if not failure_records:
        # 即使没有失败，也创建空的 CSV 文件（带表头）
        with output_path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                '软件包名', 'GitHub 链接', '类型', '失败阶段', 
                '失败原因', '是否调用 AI', 'AI 是否判断可补', '失败关键日志片段'
            ])
        return 0
    
    with output_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 写入表头
        writer.writerow([
            '软件包名', 'GitHub 链接', '类型', '失败阶段', 
            '失败原因', '是否调用 AI', 'AI 是否判断可补', '失败关键日志片段'
        ])
        
        # 写入数据行
        for record in failure_records:
            # 获取失败原因（如果 build_status 为 FAIL，从 failure_reason；否则从clone_status）
            if record.get('build_status') == 'FAIL':
                failure_reason = record.get('failure_reason', '未知')
                failure_stage = record.get('failure_stage', 'UNKNOWN')
                build_log = record.get('build_log', '')
            else:
                # Clone 失败的情况
                failure_reason = 'Clone 失败'
                failure_stage = 'UNKNOWN'
                build_log = record.get('clone_log', '')
            
            row = [
                record.get('repo_name', ''),
                record.get('repo_url', ''),
                record.get('build_type', 'OTHER'),
                failure_stage,
                failure_reason,
                '否',  # 是否调用 AI - 固定
                '未调用',  # AI 是否判断可补 - 固定
                build_log
            ]
            writer.writerow(row)
    
    return len(failure_records)


def generate_output_files(jsonl_path: Path, success_csv_path: Path, failure_csv_path: Path) -> Dict[str, int]:
    """
    从 JSONL 文件生成 success.csv 和 failure.csv
    :param jsonl_path: JSONL 输入文件路径
    :param success_csv_path: success.csv 输出路径
    :param failure_csv_path: failure.csv 输出路径
    :return: {"success_count": int, "failure_count": int}
    """
    print(f"[输出生成] 读取 JSONL 文件: {jsonl_path}")
    records = read_jsonl_records(jsonl_path)
    
    if not records:
        print("[输出生成] 警告：JSONL 文件为空或不存在")
        return {"success_count": 0, "failure_count": 0}
    
    print(f"[输出生成] 读取到 {len(records)} 条记录")
    
    # 生成成功 CSV
    print(f"[输出生成] 生成 {success_csv_path}")
    success_count = generate_success_csv(records, success_csv_path)
    print(f"[输出生成] success.csv: {success_count} 条成功记录")
    
    # 生成失败 CSV
    print(f"[输出生成] 生成 {failure_csv_path}")
    failure_count = generate_failure_csv(records, failure_csv_path)
    print(f"[输出生成] failure.csv: {failure_count} 条失败记录")
    
    print(f"[输出生成] 总计: {len(records)} 条记录 (成功: {success_count}, 失败: {failure_count})")
    
    return {"success_count": success_count, "failure_count": failure_count}
