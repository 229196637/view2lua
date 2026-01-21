"""
解析 entry_data.ini 文件（Lua-like格式的配置文件）
"""
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class EntryDataParser:
    def __init__(self, entry_data_path: str):
        self.path = Path(entry_data_path)
        self.sections: Dict[str, Dict[str, Any]] = {}
        self.config: Dict[str, Any] = {}
        
    def parse(self) -> Dict[str, Any]:
        """解析entry_data.ini文件"""
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")
        
        content = self.path.read_text(encoding='utf-8')
        self._parse_content(content)
        return {
            'config': self.config,
            'sections': self.sections
        }
    
    def _parse_content(self, content: str):
        """解析文件内容"""
        lines = content.split('\n')
        current_section = None
        current_data = {}
        brace_depth = 0
        collecting_value = False
        value_buffer = []
        current_key = None
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # 跳过注释和空行
            if stripped.startswith('--') or not stripped:
                i += 1
                continue
            
            # 检测section开始 [#CONFIG] 或 ['name']
            section_match = re.match(r"^\[([^\]]+)\]", stripped)
            if section_match and brace_depth == 0:
                # 保存之前的section
                if current_section is not None:
                    if current_section == '#CONFIG':
                        self.config = current_data
                    else:
                        self.sections[current_section] = current_data
                
                section_name = section_match.group(1)
                # 去掉引号
                if section_name.startswith("'") and section_name.endswith("'"):
                    section_name = section_name[1:-1]
                current_section = section_name
                current_data = {}
                i += 1
                continue
            
            # 解析键值对
            if current_section is not None:
                # 检测键值对开始
                kv_match = re.match(r"^'([^']+)'\s*=\s*(.*)$", stripped)
                if kv_match and brace_depth == 0:
                    key = kv_match.group(1)
                    value_part = kv_match.group(2)
                    
                    # 检查是否是简单值
                    parsed_value, complete = self._try_parse_value(value_part)
                    if complete:
                        current_data[key] = parsed_value
                    else:
                        # 需要收集多行
                        collecting_value = True
                        current_key = key
                        value_buffer = [value_part]
                        brace_depth = value_part.count('{') - value_part.count('}')
                elif collecting_value:
                    value_buffer.append(line)
                    brace_depth += stripped.count('{') - stripped.count('}')
                    
                    if brace_depth <= 0:
                        # 值收集完成
                        full_value = '\n'.join(value_buffer)
                        parsed_value, _ = self._try_parse_value(full_value)
                        current_data[current_key] = parsed_value
                        collecting_value = False
                        value_buffer = []
                        current_key = None
                        brace_depth = 0
            
            i += 1
        
        # 保存最后一个section
        if current_section is not None:
            if current_section == '#CONFIG':
                self.config = current_data
            else:
                self.sections[current_section] = current_data
    
    def _try_parse_value(self, value_str: str) -> Tuple[Any, bool]:
        """尝试解析值，返回(解析结果, 是否完成)"""
        value_str = value_str.strip()
        
        # 检查是否是#NIL
        if value_str == '#NIL':
            return None, True
        
        # 检查是否是字符串
        if value_str.startswith("'") and value_str.endswith("'"):
            return value_str[1:-1], True
        
        # 检查是否是数字
        try:
            if '.' in value_str:
                return float(value_str), True
            return int(value_str), True
        except ValueError:
            pass
        
        # 检查是否是布尔值
        if value_str == 'true':
            return True, True
        if value_str == 'false':
            return False, True
        
        # 检查是否是表（需要完整的大括号匹配）
        if value_str.startswith('{'):
            brace_count = value_str.count('{') - value_str.count('}')
            if brace_count == 0:
                return self._parse_lua_table(value_str), True
            else:
                return None, False
        
        # 其他情况返回原始字符串
        return value_str, True
    
    def _parse_lua_table(self, table_str: str) -> Dict[str, Any]:
        """解析Lua表格式的字符串"""
        result = {}
        table_str = table_str.strip()
        
        if not table_str.startswith('{') or not table_str.endswith('}'):
            return result
        
        # 去掉外层大括号
        inner = table_str[1:-1].strip()
        if not inner:
            return result
        
        # 分割键值对（考虑嵌套）
        pairs = self._split_table_pairs(inner)
        
        for pair in pairs:
            pair = pair.strip()
            if not pair:
                continue
            
            # 解析键值对
            # 格式: 'key' = value 或 key = value 或 数字 = value
            kv_match = re.match(r"^'([^']+)'\s*=\s*(.+)$", pair, re.DOTALL)
            if kv_match:
                key = kv_match.group(1)
                value_str = kv_match.group(2).strip()
                value, _ = self._try_parse_value(value_str)
                result[key] = value
                continue
            
            # 数字索引格式: 1 = value
            num_match = re.match(r"^(\d+)\s*=\s*(.+)$", pair, re.DOTALL)
            if num_match:
                key = int(num_match.group(1))
                value_str = num_match.group(2).strip()
                value, _ = self._try_parse_value(value_str)
                result[key] = value
                continue
        
        return result
    
    def _split_table_pairs(self, inner: str) -> List[str]:
        """分割表中的键值对，考虑嵌套"""
        pairs = []
        current = []
        brace_depth = 0
        
        for char in inner:
            if char == '{':
                brace_depth += 1
                current.append(char)
            elif char == '}':
                brace_depth -= 1
                current.append(char)
            elif char == ',' and brace_depth == 0:
                pairs.append(''.join(current))
                current = []
            else:
                current.append(char)
        
        if current:
            pairs.append(''.join(current))
        
        return pairs
    
    def get_display_name(self) -> Optional[str]:
        """从i18n文件获取显示名称"""
        i18n_path = self.path.parent / 'i18n' / 'default.json'
        if i18n_path.exists():
            try:
                data = json.loads(i18n_path.read_text(encoding='utf-8'))
                for key, value in data.items():
                    if 'DisplayName' in key:
                        return value
            except:
                pass
        return None
    
    def get_node_hierarchy(self) -> List[Dict[str, Any]]:
        """获取节点层级结构"""
        nodes = []
        for name, data in self.sections.items():
            node_type = data.get('NodeType', '')
            inherit = data.get('Inherit', '')
            game_data = data.get('Data', {}).get('Game', {}) if isinstance(data.get('Data'), dict) else {}
            
            nodes.append({
                'name': name,
                'node_type': node_type,
                'inherit': inherit,
                'game_data': game_data,
                'children': game_data.get('children', {})
            })
        
        return nodes
