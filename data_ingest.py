"""
数据摄取模块 - PDF/Excel/MySQL数据解析
"""
import os
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import pandas as pd
import pdfplumber
from loguru import logger

from config import DATA_DIR, KNOWLEDGE_BASE_DIR


class PDFProcessor:
    """PDF文档处理器"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.filename = os.path.basename(pdf_path)
        logger.info(f"初始化PDF处理器: {self.filename}")
    
    def extract_text_with_pages(self) -> List[Dict]:
        """提取PDF文本，保留页码信息"""
        chunks = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        chunks.append({
                            'content': text.strip(),
                            'source': {
                                'type': 'pdf',
                                'filename': self.filename,
                                'page': page_num
                            },
                            'metadata': {
                                'page': page_num,
                                'total_pages': len(pdf.pages)
                            }
                        })
            logger.info(f"PDF提取完成: {self.filename}, 共{len(chunks)}页有效内容")
        except Exception as e:
            logger.error(f"PDF提取失败: {self.filename}, 错误: {e}")
        return chunks
    
    def extract_tables(self) -> List[Dict]:
        """提取PDF中的表格"""
        tables = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    for table_idx, table in enumerate(page_tables):
                        if table and len(table) > 1:
                            # 将表格转换为文本
                            table_text = self._table_to_text(table)
                            if table_text:
                                tables.append({
                                    'content': table_text,
                                    'source': {
                                        'type': 'pdf_table',
                                        'filename': self.filename,
                                        'page': page_num,
                                        'table_index': table_idx
                                    },
                                    'raw_table': table
                                })
            logger.info(f"表格提取完成: {self.filename}, 共{len(tables)}个表格")
        except Exception as e:
            logger.error(f"表格提取失败: {self.filename}, 错误: {e}")
        return tables
    
    def _table_to_text(self, table: List[List]) -> str:
        """将表格转换为文本"""
        if not table:
            return ""
        
        lines = []
        # 处理表头
        if table[0]:
            header = " | ".join([str(cell) if cell else "" for cell in table[0]])
            lines.append(header)
            lines.append("-" * len(header))
        
        # 处理数据行
        for row in table[1:]:
            if row:
                row_text = " | ".join([str(cell) if cell else "" for cell in row])
                lines.append(row_text)
        
        return "\n".join(lines)
    
    def extract_toc(self) -> List[Dict]:
        """提取目录结构（基于文本模式识别）"""
        toc = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages[:10], 1):  # 通常目录在前10页
                    text = page.extract_text()
                    if text:
                        # 匹配常见目录模式
                        patterns = [
                            r'^(\d+[\.\s]+.+?)[\s\.]{3,}(\d+)',  # 1. 章节名...页码
                            r'^(第[一二三四五六七八九十]+[章节].+?)[\s\.]{3,}(\d+)',  # 第X章...页码
                            r'^([一二三四五六七八九十]+[、\.].+?)[\s\.]{3,}(\d+)',  # 一、标题...页码
                        ]
                        
                        for line in text.split('\n'):
                            for pattern in patterns:
                                match = re.match(pattern, line.strip())
                                if match:
                                    toc.append({
                                        'title': match.group(1).strip(),
                                        'page': match.group(2),
                                        'source_page': page_num
                                    })
                                    break
            
            logger.info(f"目录提取完成: {self.filename}, 共{len(toc)}个条目")
        except Exception as e:
            logger.error(f"目录提取失败: {self.filename}, 错误: {e}")
        return toc
    
    def get_document_info(self) -> Dict:
        """获取文档基本信息"""
        info = {
            'filename': self.filename,
            'path': self.pdf_path,
            'total_pages': 0,
            'file_size': 0,
            'modified_time': None
        }
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                info['total_pages'] = len(pdf.pages)
            
            stat = os.stat(self.pdf_path)
            info['file_size'] = stat.st_size
            info['modified_time'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        except Exception as e:
            logger.error(f"获取文档信息失败: {e}")
        return info


class ExcelProcessor:
    """Excel数据处理器"""
    
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.filename = os.path.basename(excel_path)
        self.df = None
        logger.info(f"初始化Excel处理器: {self.filename}")
    
    def load_data(self) -> pd.DataFrame:
        """加载Excel数据"""
        try:
            self.df = pd.read_excel(self.excel_path)
            logger.info(f"Excel加载成功: {self.filename}, 共{len(self.df)}行")
            return self.df
        except Exception as e:
            logger.error(f"Excel加载失败: {self.filename}, 错误: {e}")
            return pd.DataFrame()
    
    def get_insulin_usage_stats(self) -> Dict:
        """计算胰岛素使用率统计"""
        if self.df is None:
            self.load_data()
        
        if self.df is None or self.df.empty:
            return {}
        
        stats = {
            'total_patients': len(self.df),
            'insulin_users': 0,
            'insulin_non_users': 0,
            'usage_rate': 0.0
        }
        
        # 查找胰岛素相关列
        insulin_cols = []
        for col in self.df.columns:
            col_lower = str(col).lower()
            if '胰岛素' in col_lower or 'insulin' in col_lower:
                insulin_cols.append(col)
        
        if insulin_cols:
            # 如果有胰岛素使用标记列
            for col in insulin_cols:
                if '使用' in str(col) or 'usage' in str(col).lower():
                    stats['insulin_users'] = self.df[col].sum() if self.df[col].dtype == bool else (self.df[col] == 1).sum()
                    break
        
        # 尝试通过空腹胰岛素和餐后胰岛素列判断
        fasting_insulin_col = None
        postprandial_insulin_col = None
        
        for col in self.df.columns:
            col_str = str(col)
            if '空腹胰岛素' in col_str or '空腹INS' in col_str.upper():
                fasting_insulin_col = col
            if '餐后' in col_str and '胰岛素' in col_str:
                postprandial_insulin_col = col
        
        if fasting_insulin_col or postprandial_insulin_col:
            # 如果两个胰岛素列都为空或NaN，则认为没有使用胰岛素
            def has_insulin(row):
                fasting = row.get(fasting_insulin_col) if fasting_insulin_col else None
                postprandial = row.get(postprandial_insulin_col) if postprandial_insulin_col else None
                return pd.notna(fasting) or pd.notna(postprandial)
            
            stats['insulin_users'] = self.df.apply(has_insulin, axis=1).sum()
        
        stats['insulin_non_users'] = stats['total_patients'] - stats['insulin_users']
        stats['usage_rate'] = round(stats['insulin_users'] / stats['total_patients'] * 100, 2) if stats['total_patients'] > 0 else 0
        
        logger.info(f"胰岛素使用率统计完成: 使用率={stats['usage_rate']}%")
        return stats
    
    def get_distribution_by_gender(self) -> Dict:
        """按性别统计分布"""
        if self.df is None:
            self.load_data()
        
        if self.df is None or self.df.empty:
            return {}
        
        # 查找性别列
        gender_col = None
        for col in self.df.columns:
            if '性别' in str(col) or 'gender' in str(col).lower() or 'sex' in str(col).lower():
                gender_col = col
                break
        
        if gender_col is None:
            return {}
        
        return self.df[gender_col].value_counts().to_dict()
    
    def get_distribution_by_age(self) -> Dict:
        """按年龄段统计分布"""
        if self.df is None:
            self.load_data()
        
        if self.df is None or self.df.empty:
            return {}
        
        # 查找年龄列
        age_col = None
        for col in self.df.columns:
            if '年龄' in str(col) or 'age' in str(col).lower():
                age_col = col
                break
        
        if age_col is None:
            return {}
        
        # 定义年龄段
        bins = [0, 30, 40, 50, 60, 70, 80, 200]
        labels = ['<30岁', '30-40岁', '40-50岁', '50-60岁', '60-70岁', '70-80岁', '>80岁']
        
        self.df['age_group'] = pd.cut(self.df[age_col], bins=bins, labels=labels, right=False)
        return self.df['age_group'].value_counts().to_dict()
    
    def get_bmi_distribution(self) -> Dict:
        """按BMI统计分布"""
        if self.df is None:
            self.load_data()
        
        if self.df is None or self.df.empty:
            return {}
        
        # 查找BMI列或身高体重列
        bmi_col = None
        height_col = None
        weight_col = None
        
        for col in self.df.columns:
            col_str = str(col).lower()
            if 'bmi' in col_str:
                bmi_col = col
            if '身高' in str(col) or 'height' in col_str:
                height_col = col
            if '体重' in str(col) or 'weight' in col_str:
                weight_col = col
        
        if bmi_col is None and height_col and weight_col:
            # 计算BMI
            self.df['calculated_bmi'] = self.df[weight_col] / ((self.df[height_col] / 100) ** 2)
            bmi_col = 'calculated_bmi'
        
        if bmi_col is None:
            return {}
        
        # 定义BMI分类
        bins = [0, 18.5, 24, 28, 100]
        labels = ['偏瘦(<18.5)', '正常(18.5-24)', '超重(24-28)', '肥胖(≥28)']
        
        self.df['bmi_category'] = pd.cut(self.df[bmi_col], bins=bins, labels=labels, right=False)
        return self.df['bmi_category'].value_counts().to_dict()
    
    def to_chunks(self) -> List[Dict]:
        """将Excel数据转换为检索块"""
        if self.df is None:
            self.load_data()
        
        if self.df is None or self.df.empty:
            return []
        
        chunks = []
        
        # 添加统计信息作为一个块
        stats_text = f"糖尿病病例统计数据，共{len(self.df)}条记录。\n"
        stats_text += f"包含列: {', '.join(self.df.columns.tolist())}"
        
        chunks.append({
            'content': stats_text,
            'source': {
                'type': 'excel',
                'filename': self.filename,
                'row': 'summary'
            }
        })
        
        # 添加每行数据作为块
        for idx, row in self.df.iterrows():
            row_text = " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
            if row_text:
                chunks.append({
                    'content': row_text,
                    'source': {
                        'type': 'excel',
                        'filename': self.filename,
                        'row': idx + 2  # Excel行号从1开始，加上表头
                    }
                })
        
        logger.info(f"Excel转换为{len(chunks)}个检索块")
        return chunks
    
    def get_column_stats(self) -> Dict:
        """获取列统计信息"""
        if self.df is None:
            self.load_data()
        
        if self.df is None or self.df.empty:
            return {}
        
        stats = {}
        for col in self.df.columns:
            col_stats = {
                'name': col,
                'dtype': str(self.df[col].dtype),
                'non_null_count': self.df[col].count(),
                'null_count': self.df[col].isnull().sum()
            }
            
            if self.df[col].dtype in ['int64', 'float64']:
                col_stats['mean'] = round(self.df[col].mean(), 2) if pd.notna(self.df[col].mean()) else None
                col_stats['min'] = self.df[col].min()
                col_stats['max'] = self.df[col].max()
            
            stats[col] = col_stats
        
        return stats


def load_all_pdfs() -> List[Dict]:
    """加载所有PDF文档"""
    chunks = []
    pdf_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.pdf')]
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(DATA_DIR, pdf_file)
        processor = PDFProcessor(pdf_path)
        
        # 提取文本
        text_chunks = processor.extract_text_with_pages()
        chunks.extend(text_chunks)
        
        # 提取表格
        table_chunks = processor.extract_tables()
        chunks.extend(table_chunks)
    
    logger.info(f"共加载{len(pdf_files)}个PDF文件，生成{len(chunks)}个检索块")
    return chunks


def load_excel_data() -> Tuple[pd.DataFrame, Dict]:
    """加载Excel数据"""
    excel_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.xlsx') or f.endswith('.xls')]
    
    all_data = pd.DataFrame()
    all_stats = {}
    
    for excel_file in excel_files:
        excel_path = os.path.join(DATA_DIR, excel_file)
        processor = ExcelProcessor(excel_path)
        df = processor.load_data()
        
        if not df.empty:
            all_data = pd.concat([all_data, df], ignore_index=True)
            all_stats[excel_file] = {
                'insulin_stats': processor.get_insulin_usage_stats(),
                'gender_distribution': processor.get_distribution_by_gender(),
                'age_distribution': processor.get_distribution_by_age(),
                'bmi_distribution': processor.get_bmi_distribution(),
                'column_stats': processor.get_column_stats()
            }
    
    logger.info(f"共加载{len(excel_files)}个Excel文件，总计{len(all_data)}条数据")
    return all_data, all_stats


def get_pdf_info() -> List[Dict]:
    """获取所有PDF文档信息"""
    pdf_info = []
    pdf_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.pdf')]
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(DATA_DIR, pdf_file)
        processor = PDFProcessor(pdf_path)
        info = processor.get_document_info()
        info['toc'] = processor.extract_toc()
        pdf_info.append(info)
    
    return pdf_info


def get_excel_info() -> List[Dict]:
    """获取所有Excel文件信息"""
    excel_info = []
    excel_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.xlsx') or f.endswith('.xls')]
    
    for excel_file in excel_files:
        excel_path = os.path.join(DATA_DIR, excel_file)
        processor = ExcelProcessor(excel_path)
        processor.load_data()
        
        info = {
            'filename': excel_file,
            'path': excel_path,
            'row_count': len(processor.df) if processor.df is not None else 0,
            'column_count': len(processor.df.columns) if processor.df is not None else 0,
            'columns': processor.df.columns.tolist() if processor.df is not None else [],
            'stats': processor.get_column_stats()
        }
        excel_info.append(info)
    
    return excel_info

