"""
Lua代码生成工具
"""
from typing import Any, Dict, List


def format_lua_value(value: Any, indent: int = 0) -> str:
    """格式化Lua值"""
    indent_str = ' ' * indent
    
    if value is None:
        return 'nil'
    elif isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, str):
        # 转义特殊字符
        escaped = value.replace('\\', '\\\\').replace("'", "\\'")
        return f"'{escaped}'"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, dict):
        return format_lua_table(value, indent)
    elif isinstance(value, list):
        return format_lua_array(value, indent)
    
    return str(value)


def format_lua_table(table: Dict[str, Any], indent: int = 0) -> str:
    """格式化Lua表"""
    if not table:
        return '{}'
    
    indent_str = ' ' * indent
    inner_indent = ' ' * (indent + 4)
    
    lines = ['{']
    
    for key, value in table.items():
        formatted_value = format_lua_value(value, indent + 4)
        
        if isinstance(key, int):
            lines.append(f"{inner_indent}[{key}] = {formatted_value},")
        else:
            lines.append(f"{inner_indent}{key} = {formatted_value},")
    
    lines.append(f"{indent_str}}}")
    
    return '\n'.join(lines)


def format_lua_array(arr: List[Any], indent: int = 0) -> str:
    """格式化Lua数组"""
    if not arr:
        return '{}'
    
    # 简单数组（全是数字）可以写成一行
    if all(isinstance(x, (int, float)) for x in arr):
        values = ', '.join(str(x) for x in arr)
        return f'{{{values}}}'
    
    indent_str = ' ' * indent
    inner_indent = ' ' * (indent + 4)
    
    lines = ['{']
    for i, value in enumerate(arr, 1):
        formatted_value = format_lua_value(value, indent + 4)
        lines.append(f"{inner_indent}[{i}] = {formatted_value},")
    lines.append(f"{indent_str}}}")
    
    return '\n'.join(lines)


class LuaWriter:
    """Lua代码写入器"""
    
    def __init__(self):
        self.lines: List[str] = []
        self.indent_level = 0
        
    def add_line(self, line: str = ''):
        """添加一行"""
        if line:
            self.lines.append(' ' * (self.indent_level * 4) + line)
        else:
            self.lines.append('')
    
    def add_comment(self, comment: str):
        """添加注释"""
        self.add_line(f'-- {comment}')
    
    def add_require(self, var_name: str, module: str):
        """添加require语句"""
        self.add_line(f"local {var_name} = require '{module}'")
    
    def begin_table(self, name: str = None):
        """开始表"""
        if name:
            self.add_line(f'{name} = {{')
        else:
            self.add_line('{')
        self.indent_level += 1
    
    def end_table(self, trailing_comma: bool = True):
        """结束表"""
        self.indent_level -= 1
        self.add_line('},' if trailing_comma else '}')
    
    def add_property(self, key: str, value: Any):
        """添加属性"""
        formatted = format_lua_value(value, self.indent_level * 4)
        self.add_line(f'{key} = {formatted},')
    
    def get_content(self) -> str:
        """获取生成的内容"""
        return '\n'.join(self.lines)
