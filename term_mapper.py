"""
术语映射模块 - 医学术语标准化
"""
from typing import List, Dict, Optional, Tuple
import jieba
from loguru import logger

from config import TERM_MAPPINGS


class TermMapper:
    """医学术语映射器"""
    
    def __init__(self):
        self.mappings = TERM_MAPPINGS.copy()
        self.reverse_mappings = {}  # 标准术语 -> 别名列表
        self._build_reverse_mappings()
        
        # 将医学术语添加到jieba词典
        for term in list(self.mappings.keys()) + list(self.mappings.values()):
            jieba.add_word(term)
        
        logger.info(f"术语映射器初始化完成，共{len(self.mappings)}个映射")
    
    def _build_reverse_mappings(self):
        """构建反向映射（标准术语到别名）"""
        for alias, standard in self.mappings.items():
            if standard not in self.reverse_mappings:
                self.reverse_mappings[standard] = []
            self.reverse_mappings[standard].append(alias)
    
    def normalize(self, term: str) -> str:
        """
        标准化术语
        
        Args:
            term: 输入术语（可能是俗称或别名）
            
        Returns:
            str: 标准化后的术语
        """
        term = term.strip()
        
        # 直接查找映射
        if term in self.mappings:
            standard = self.mappings[term]
            logger.info(f"术语标准化: '{term}' -> '{standard}'")
            return standard
        
        # 已经是标准术语
        if term in self.reverse_mappings:
            return term
        
        # 未找到映射，返回原术语
        return term
    
    def normalize_text(self, text: str) -> Tuple[str, List[Dict]]:
        """
        标准化文本中的术语
        
        Args:
            text: 输入文本
            
        Returns:
            Tuple[str, List[Dict]]: (标准化后的文本, 替换记录列表)
        """
        replacements = []
        normalized_text = text
        
        # 分词
        words = jieba.lcut(text)
        
        for word in words:
            if word in self.mappings:
                standard = self.mappings[word]
                normalized_text = normalized_text.replace(word, standard)
                replacements.append({
                    'original': word,
                    'normalized': standard,
                    'type': 'direct_mapping'
                })
        
        if replacements:
            logger.info(f"文本标准化完成，共{len(replacements)}处替换")
        
        return normalized_text, replacements
    
    def suggest(self, term: str, max_suggestions: int = 5) -> List[Dict]:
        """
        为输入术语提供建议（近似匹配）
        
        Args:
            term: 输入术语
            max_suggestions: 最大建议数
            
        Returns:
            List[Dict]: 建议列表
        """
        suggestions = []
        term_lower = term.lower()
        
        # 精确匹配
        if term in self.mappings:
            suggestions.append({
                'term': self.mappings[term],
                'type': 'exact_match',
                'confidence': 1.0
            })
        
        # 部分匹配
        for alias, standard in self.mappings.items():
            if term_lower in alias.lower() or alias.lower() in term_lower:
                if standard not in [s['term'] for s in suggestions]:
                    suggestions.append({
                        'term': standard,
                        'type': 'partial_match',
                        'confidence': 0.8,
                        'matched_alias': alias
                    })
        
        # 检查是否匹配标准术语
        for standard, aliases in self.reverse_mappings.items():
            if term_lower in standard.lower():
                if standard not in [s['term'] for s in suggestions]:
                    suggestions.append({
                        'term': standard,
                        'type': 'standard_match',
                        'confidence': 0.9
                    })
        
        # 按置信度排序并截取
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:max_suggestions]
    
    def get_aliases(self, standard_term: str) -> List[str]:
        """
        获取标准术语的所有别名
        
        Args:
            standard_term: 标准术语
            
        Returns:
            List[str]: 别名列表
        """
        return self.reverse_mappings.get(standard_term, [])
    
    def add_mapping(self, alias: str, standard: str) -> bool:
        """
        添加新的术语映射
        
        Args:
            alias: 别名
            standard: 标准术语
            
        Returns:
            bool: 是否添加成功
        """
        if alias in self.mappings:
            logger.warning(f"映射已存在: '{alias}' -> '{self.mappings[alias]}'")
            return False
        
        self.mappings[alias] = standard
        if standard not in self.reverse_mappings:
            self.reverse_mappings[standard] = []
        self.reverse_mappings[standard].append(alias)
        
        # 添加到jieba词典
        jieba.add_word(alias)
        jieba.add_word(standard)
        
        logger.info(f"添加术语映射: '{alias}' -> '{standard}'")
        return True
    
    def get_all_mappings(self) -> Dict[str, str]:
        """获取所有术语映射"""
        return self.mappings.copy()
    
    def get_mapping_table(self) -> List[Dict]:
        """获取映射表（用于前端展示）"""
        table = []
        for alias, standard in self.mappings.items():
            table.append({
                'alias': alias,
                'standard': standard,
                'category': self._get_term_category(standard)
            })
        return table
    
    def _get_term_category(self, term: str) -> str:
        """判断术语类别"""
        disease_keywords = ['死', '病', '症', '癌', '炎', '伤', '损', '衰', '障碍', '综合征']
        drug_keywords = ['普利', '沙坦', '地平', '洛尔', '双胍', '胰岛素', '片', '注射液']
        symptom_keywords = ['痛', '晕', '闷', '悸', '短', '吐', '泻']
        test_keywords = ['检查', '检验', '图', '超', '功能']
        
        for keyword in disease_keywords:
            if keyword in term:
                return '疾病名称'
        
        for keyword in drug_keywords:
            if keyword in term:
                return '药物名称'
        
        for keyword in symptom_keywords:
            if keyword in term:
                return '症状名称'
        
        for keyword in test_keywords:
            if keyword in term:
                return '检查项目'
        
        return '其他'
    
    def expand_query(self, query: str) -> str:
        """
        扩展查询（添加同义词）
        
        Args:
            query: 原始查询
            
        Returns:
            str: 扩展后的查询
        """
        words = jieba.lcut(query)
        expanded_terms = []
        
        for word in words:
            expanded_terms.append(word)
            
            # 如果是别名，添加标准术语
            if word in self.mappings:
                expanded_terms.append(self.mappings[word])
            
            # 如果是标准术语，添加别名
            if word in self.reverse_mappings:
                expanded_terms.extend(self.reverse_mappings[word])
        
        # 去重并保持顺序
        seen = set()
        unique_terms = []
        for term in expanded_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return " ".join(unique_terms)


# 全局术语映射器实例
_term_mapper = None

def get_term_mapper() -> TermMapper:
    """获取全局术语映射器实例"""
    global _term_mapper
    if _term_mapper is None:
        _term_mapper = TermMapper()
    return _term_mapper

