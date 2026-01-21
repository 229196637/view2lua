"""
验证转换结果与编辑器生成的Lua是否一致
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple


class Validator:
    def __init__(self, generated_lua: str, existing_lua_path: str):
        self.generated = generated_lua
        self.existing_path = Path(existing_lua_path)
        
    def validate(self) -> Tuple[bool, List[str]]:
        """验证两个Lua文件是否一致"""
        if not self.existing_path.exists():
            return False, [f"Existing file not found: {self.existing_path}"]
        
        existing = self.existing_path.read_text(encoding='utf-8')
        
        # 标准化比较
        gen_normalized = self._normalize(self.generated)
        exist_normalized = self._normalize(existing)
        
        if gen_normalized == exist_normalized:
            return True, []
        
        # 找出差异
        differences = self._find_differences(gen_normalized, exist_normalized)
        return False, differences
    
    def _normalize(self, content: str) -> str:
        """标准化Lua代码以便比较"""
        # 移除注释
        content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
        # 移除空行
        content = re.sub(r'\n\s*\n', '\n', content)
        # 标准化空白
        content = re.sub(r'[ \t]+', ' ', content)
        # 移除行首尾空白
        lines = [line.strip() for line in content.split('\n')]
        return '\n'.join(line for line in lines if line)
    
    def _find_differences(self, gen: str, exist: str) -> List[str]:
        """找出差异"""
        differences = []
        
        gen_lines = gen.split('\n')
        exist_lines = exist.split('\n')
        
        max_lines = max(len(gen_lines), len(exist_lines))
        
        for i in range(max_lines):
            gen_line = gen_lines[i] if i < len(gen_lines) else '<missing>'
            exist_line = exist_lines[i] if i < len(exist_lines) else '<missing>'
            
            if gen_line != exist_line:
                differences.append(f"Line {i+1}:")
                differences.append(f"  Generated: {gen_line[:100]}")
                differences.append(f"  Existing:  {exist_line[:100]}")
                
                if len(differences) > 30:  # 限制差异数量
                    differences.append("... (more differences)")
                    break
        
        return differences


class StructureValidator:
    """验证结构是否正确"""
    
    def __init__(self, entry_data: Dict[str, Any], lua_content: str):
        self.entry_data = entry_data
        self.lua_content = lua_content
        
    def validate_structure(self) -> Tuple[bool, List[str]]:
        """验证结构"""
        errors = []
        
        # 检查所有节点是否都被转换
        sections = self.entry_data.get('sections', {})
        for name, data in sections.items():
            node_type = data.get('NodeType', '')
            if node_type and '.gui_ctrl.' in node_type:
                # 检查是否在Lua中存在
                game_data = data.get('Data', {}).get('Game', {}) if isinstance(data.get('Data'), dict) else {}
                ctrl_name = game_data.get('Name', name)
                
                if ctrl_name and f"name = '{ctrl_name}'" not in self.lua_content:
                    errors.append(f"Node '{name}' (name='{ctrl_name}') not found in generated Lua")
        
        return len(errors) == 0, errors
