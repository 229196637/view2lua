#!/usr/bin/env python3
"""
view2lua - Editor UI数据转Lua工具

用法:
    python main.py --validate              验证所有组件
    python main.py --convert test          转换单个组件
    python main.py --convert-all           转换所有组件
    python main.py --list                  列出所有组件
"""
import argparse
import sys
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from parser.entry_data import EntryDataParser
from parser.lua_template import LuaTemplateParser
from converter.to_lua import LuaConverter
from validator.compare import Validator, StructureValidator


class View2Lua:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.editor_dir = project_root / 'editor' / 'table' / 'entry_data' / 'template@gui_ctrl'
        self.ui_script_dir = project_root / 'ui' / 'script' / 'gui' / 'page'
        
    def list_components(self) -> List[Dict[str, Any]]:
        """列出所有组件"""
        components = []
        
        if not self.editor_dir.exists():
            print(f"Editor directory not found: {self.editor_dir}")
            return components
        
        for item in self.editor_dir.iterdir():
            if item.is_dir():
                entry_data_path = item / 'entry_data.ini'
                if entry_data_path.exists():
                    # 获取显示名称
                    parser = EntryDataParser(str(entry_data_path))
                    display_name = parser.get_display_name()
                    
                    # 检查是否有对应的Lua文件
                    lua_dir = self.ui_script_dir / (display_name or item.name)
                    has_lua = (lua_dir / 'template.lua').exists() if lua_dir.exists() else False
                    
                    components.append({
                        'dir_name': item.name,
                        'display_name': display_name,
                        'editor_path': str(item),
                        'lua_path': str(lua_dir) if has_lua else None,
                        'has_lua': has_lua
                    })
        
        return components
    
    def validate_component(self, component_name: str) -> bool:
        """验证单个组件"""
        print(f"\n=== Validating: {component_name} ===")
        
        # 查找组件
        component = self._find_component(component_name)
        if not component:
            print(f"Component not found: {component_name}")
            return False
        
        editor_path = Path(component['editor_path'])
        entry_data_path = editor_path / 'entry_data.ini'
        
        # 解析entry_data
        parser = EntryDataParser(str(entry_data_path))
        try:
            entry_data = parser.parse()
            display_name = parser.get_display_name() or component_name
        except Exception as e:
            print(f"Failed to parse entry_data: {e}")
            return False
        
        # 检查是否有对应的Lua文件
        lua_dir = self.ui_script_dir / display_name
        template_path = lua_dir / 'template.lua'
        
        if not template_path.exists():
            print(f"No existing template.lua found at: {template_path}")
            print("Skipping validation (no reference file)")
            return True
        
        # 转换
        converter = LuaConverter(entry_data, display_name)
        generated_lua = converter.convert()
        
        # 验证结构
        struct_validator = StructureValidator(entry_data, generated_lua)
        struct_ok, struct_errors = struct_validator.validate_structure()
        
        if not struct_ok:
            print("Structure validation failed:")
            for err in struct_errors:
                print(f"  - {err}")
        
        # 验证与现有文件的一致性
        validator = Validator(generated_lua, str(template_path))
        is_valid, differences = validator.validate()
        
        if is_valid:
            print(f"[OK] Component '{display_name}' validation passed")
            return True
        else:
            print(f"[DIFF] Component '{display_name}' has differences:")
            for diff in differences[:20]:
                print(f"  {diff}")
            return False
    
    def validate_all(self) -> bool:
        """验证所有组件"""
        components = self.list_components()
        
        if not components:
            print("No components found")
            return False
        
        results = []
        for comp in components:
            name = comp['display_name'] or comp['dir_name']
            if comp['has_lua']:
                result = self.validate_component(name)
                results.append((name, result))
        
        print("\n=== Validation Summary ===")
        passed = sum(1 for _, r in results if r)
        failed = sum(1 for _, r in results if not r)
        print(f"Passed: {passed}, Failed: {failed}")
        
        return failed == 0
    
    def convert_component(self, component_name: str, dry_run: bool = False) -> bool:
        """转换单个组件"""
        print(f"\n=== Converting: {component_name} ===")
        
        # 查找组件
        component = self._find_component(component_name)
        if not component:
            print(f"Component not found: {component_name}")
            return False
        
        editor_path = Path(component['editor_path'])
        entry_data_path = editor_path / 'entry_data.ini'
        
        # 解析entry_data
        parser = EntryDataParser(str(entry_data_path))
        try:
            entry_data = parser.parse()
            display_name = parser.get_display_name() or component_name
        except Exception as e:
            print(f"Failed to parse entry_data: {e}")
            return False
        
        print(f"Display name: {display_name}")
        print(f"Sections: {list(entry_data.get('sections', {}).keys())}")
        
        # 转换
        converter = LuaConverter(entry_data, display_name)
        generated_lua = converter.convert()
        
        # 目标路径
        lua_dir = self.ui_script_dir / display_name
        template_path = lua_dir / 'template.lua'
        
        if dry_run:
            print(f"\n[DRY RUN] Would write to: {template_path}")
            print("\n--- Generated Lua ---")
            print(generated_lua[:2000])
            if len(generated_lua) > 2000:
                print(f"... ({len(generated_lua)} total characters)")
            return True
        
        # 创建目录
        lua_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份现有文件
        if template_path.exists():
            backup_path = template_path.with_suffix('.lua.bak')
            shutil.copy(template_path, backup_path)
            print(f"Backed up existing file to: {backup_path}")
        
        # 写入新文件
        template_path.write_text(generated_lua, encoding='utf-8')
        print(f"Written to: {template_path}")
        
        # 创建component.lua如果不存在
        component_path = lua_dir / 'component.lua'
        if not component_path.exists():
            component_lua = self._generate_component_lua(display_name)
            component_path.write_text(component_lua, encoding='utf-8')
            print(f"Created component.lua: {component_path}")
        
        return True
    
    def convert_all(self, dry_run: bool = False) -> bool:
        """转换所有组件"""
        components = self.list_components()
        
        if not components:
            print("No components found")
            return False
        
        results = []
        for comp in components:
            name = comp['display_name'] or comp['dir_name']
            # 跳过以$$开头的内部组件
            if comp['dir_name'].startswith('$$'):
                print(f"Skipping internal component: {comp['dir_name']}")
                continue
            
            result = self.convert_component(name, dry_run)
            results.append((name, result))
        
        print("\n=== Conversion Summary ===")
        success = sum(1 for _, r in results if r)
        failed = sum(1 for _, r in results if not r)
        print(f"Success: {success}, Failed: {failed}")
        
        return failed == 0
    
    def _find_component(self, name: str) -> Optional[Dict[str, Any]]:
        """查找组件"""
        components = self.list_components()
        
        for comp in components:
            if comp['display_name'] == name or comp['dir_name'] == name:
                return comp
        
        return None
    
    def _generate_component_lua(self, name: str) -> str:
        """生成component.lua模板"""
        return f"""-- THIS FILE IS AUTO-GENERATED, MIGHT BE OVERWRITTEN BY GUI-EDITOR
local pkg = require '@common.base.gui.package'
local component = require '@common.base.gui.component'

return component '{name}' {{
    pkg.require_template(lib_env, '{name}'),

    event = {{

    }},

    prop = {{

    }},

    method = {{

    }},
    
    state = {{

    }},
}}
"""


def main():
    parser = argparse.ArgumentParser(description='Editor UI数据转Lua工具')
    parser.add_argument('--list', action='store_true', help='列出所有组件')
    parser.add_argument('--validate', action='store_true', help='验证所有组件')
    parser.add_argument('--validate-one', type=str, help='验证单个组件')
    parser.add_argument('--convert', type=str, help='转换单个组件')
    parser.add_argument('--convert-all', action='store_true', help='转换所有组件')
    parser.add_argument('--dry-run', action='store_true', help='仅显示将要执行的操作')
    parser.add_argument('--project', type=str, default=str(PROJECT_ROOT), help='项目根目录')
    
    args = parser.parse_args()
    
    tool = View2Lua(Path(args.project))
    
    if args.list:
        components = tool.list_components()
        print("\n=== Components ===")
        print(f"{'Dir Name':<40} {'Display Name':<20} {'Has Lua'}")
        print("-" * 70)
        for comp in components:
            has_lua = 'Yes' if comp['has_lua'] else 'No'
            print(f"{comp['dir_name']:<40} {comp['display_name'] or '-':<20} {has_lua}")
        print(f"\nTotal: {len(components)} components")
        
    elif args.validate:
        success = tool.validate_all()
        sys.exit(0 if success else 1)
        
    elif args.validate_one:
        success = tool.validate_component(args.validate_one)
        sys.exit(0 if success else 1)
        
    elif args.convert:
        success = tool.convert_component(args.convert, args.dry_run)
        sys.exit(0 if success else 1)
        
    elif args.convert_all:
        success = tool.convert_all(args.dry_run)
        sys.exit(0 if success else 1)
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
