"""
解析现有的 template.lua 文件
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


class LuaTemplateParser:
    def __init__(self, template_path: str):
        self.path = Path(template_path)
        self.flatten_template: List[Dict[str, Any]] = []
        
    def parse(self) -> Dict[str, Any]:
        """解析template.lua文件"""
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")
        
        content = self.path.read_text(encoding='utf-8')
        return self._parse_content(content)
    
    def _parse_content(self, content: str) -> Dict[str, Any]:
        """解析文件内容"""
        result = {
            'requires': [],
            'flatten_template': []
        }
        
        # 提取require语句
        require_pattern = r"local\s+(\w+)\s*=\s*require\s+'([^']+)'"
        for match in re.finditer(require_pattern, content):
            result['requires'].append({
                'var': match.group(1),
                'module': match.group(2)
            })
        
        # 提取flatten_template内容
        ft_match = re.search(r'flatten_template\s*=\s*\{(.+?)\}\s*\}', content, re.DOTALL)
        if ft_match:
            ft_content = ft_match.group(1)
            result['flatten_template'] = self._parse_flatten_template(ft_content)
        
        return result
    
    def _parse_flatten_template(self, content: str) -> List[Dict[str, Any]]:
        """解析flatten_template内容"""
        items = []
        
        # 匹配每个控件定义
        # 格式: ctrl_wrapper.panel { ... },数字,
        pattern = r'(\w+)\.(\w+)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}\s*,\s*(\d+)\s*,'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            wrapper = match.group(1)
            ctrl_type = match.group(2)
            props_str = match.group(3)
            depth = int(match.group(4))
            
            props = self._parse_props(props_str)
            
            items.append({
                'wrapper': wrapper,
                'type': ctrl_type,
                'props': props,
                'depth': depth
            })
        
        return items
    
    def _parse_props(self, props_str: str) -> Dict[str, Any]:
        """解析属性字符串"""
        props = {}
        
        # 简单的属性解析
        lines = props_str.strip().split('\n')
        for line in lines:
            line = line.strip().rstrip(',')
            if not line or line.startswith('--'):
                continue
            
            # 匹配 key = value
            match = re.match(r'(\w+)\s*=\s*(.+)$', line)
            if match:
                key = match.group(1)
                value_str = match.group(2).strip()
                props[key] = self._parse_value(value_str)
        
        return props
    
    def _parse_value(self, value_str: str) -> Any:
        """解析值"""
        value_str = value_str.strip().rstrip(',')
        
        # 字符串
        if value_str.startswith("'") and value_str.endswith("'"):
            return value_str[1:-1]
        
        # 布尔值
        if value_str == 'true':
            return True
        if value_str == 'false':
            return False
        
        # 数字
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass
        
        # 表
        if value_str.startswith('{'):
            return value_str  # 暂时返回原始字符串
        
        return value_str
    
    def get_component_list(self) -> List[str]:
        """获取组件列表"""
        result = self.parse()
        return [item.get('props', {}).get('name', '') for item in result['flatten_template']]
