"""
将entry_data转换为Lua template格式
"""
from typing import Dict, Any, List, Optional, Set
from pathlib import Path


class LuaConverter:
    # 控件类型映射
    WRAPPER_MAP = {
        '$$.gui_ctrl': 'ctrl_wrapper',
        '$$gameui.gui_ctrl': 'gameui',
        '$$lib_control.gui_ctrl': 'lib_control',
        '$$smallcard_inventory.gui_ctrl': 'smallcard_inventory',
        '$$smallcard_mail.gui_ctrl': 'smallcard_mail',
    }
    
    # 需要导入的模块
    REQUIRED_MODULES = {
        'ctrl_wrapper': '@common.base.gui.ctrl_wrapper',
        'gameui': '@gameui.component',
        'lib_control': '@lib_control.component',
        'smallcard_inventory': '@smallcard_inventory.component',
        'smallcard_mail': '@smallcard_mail.component',
        'lib_game_options': '@lib_game_options.component',
    }
    
    def __init__(self, entry_data: Dict[str, Any], display_name: str):
        self.entry_data = entry_data
        self.display_name = display_name
        self.sections = entry_data.get('sections', {})
        self.config = entry_data.get('config', {})
        self.used_wrappers: Set[str] = set()
        
    def convert(self) -> str:
        """转换为Lua代码"""
        # 构建节点树
        nodes = self._build_node_tree()
        
        # 生成flatten_template
        flatten_items = self._flatten_nodes(nodes)
        
        # 生成Lua代码
        return self._generate_lua(flatten_items)
    
    def _build_node_tree(self) -> Dict[str, Any]:
        """构建节点树"""
        nodes = {}
        root_node = None
        
        for name, data in self.sections.items():
            node_type = data.get('NodeType', '')
            game_data = {}
            editor_data = {}
            
            if isinstance(data.get('Data'), dict):
                game_data = data['Data'].get('Game', {})
                editor_data = data['Data'].get('Editor', {})
            
            children_data = game_data.get('children', {})
            children = []
            if isinstance(children_data, dict):
                # 按数字键排序
                for k, v in sorted(children_data.items(), key=lambda x: int(x[0]) if isinstance(x[0], int) or (isinstance(x[0], str) and x[0].isdigit()) else 0):
                    if v is not None:  # 跳过#NIL
                        children.append(v)
            
            nodes[name] = {
                'name': name,
                'node_type': node_type,
                'game_data': game_data,
                'editor_data': editor_data,
                'children': children,
                'children_nodes': []
            }
            
            # 找到根节点（template或root）
            if name in ('template', 'root'):
                root_node = name
        
        # 构建父子关系
        for name, node in nodes.items():
            for child_name in node['children']:
                if child_name in nodes:
                    node['children_nodes'].append(nodes[child_name])
        
        return nodes.get(root_node, {}) if root_node else {}
    
    def _flatten_nodes(self, root: Dict[str, Any], depth: int = 0, parent_has_siblings: bool = False) -> List[Dict[str, Any]]:
        """将节点树扁平化"""
        if not root:
            return []
        
        result = []
        
        # 添加当前节点
        node_info = self._convert_node(root, depth)
        if node_info:
            result.append(node_info)
        
        # 递归处理子节点
        children = root.get('children_nodes', [])
        has_siblings = len(children) > 1
        
        for i, child in enumerate(children):
            # 计算子节点深度
            # 如果当前节点有兄弟节点，子节点深度 = 当前深度 + 2
            # 否则，子节点深度 = 当前深度 + 1
            if parent_has_siblings and depth > 0:
                child_depth = depth + 2
            else:
                child_depth = depth + 1
            
            result.extend(self._flatten_nodes(child, child_depth, has_siblings))
        
        return result
    
    def _convert_node(self, node: Dict[str, Any], depth: int) -> Optional[Dict[str, Any]]:
        """转换单个节点"""
        node_type = node.get('node_type', '')
        game_data = node.get('game_data', {})
        editor_data = node.get('editor_data', {})
        
        if not node_type:
            return None
        
        # 解析wrapper和控件类型
        wrapper, ctrl_type = self._parse_node_type(node_type)
        if not wrapper:
            return None
        
        self.used_wrappers.add(wrapper)
        
        # 构建属性
        props = self._build_props(game_data, editor_data, ctrl_type, node.get('name', ''))
        
        return {
            'wrapper': wrapper,
            'type': ctrl_type,
            'props': props,
            'depth': depth
        }
    
    def _parse_node_type(self, node_type: str) -> tuple:
        """解析节点类型，返回(wrapper, ctrl_type)"""
        for prefix, wrapper in self.WRAPPER_MAP.items():
            if node_type.startswith(prefix + '.'):
                ctrl_type = node_type[len(prefix) + 1:]
                return wrapper, ctrl_type
        
        # 处理特殊情况
        if '.gui_ctrl.' in node_type:
            parts = node_type.split('.gui_ctrl.')
            if len(parts) == 2:
                prefix = parts[0]
                ctrl_type = parts[1]
                # 尝试匹配
                for p, w in self.WRAPPER_MAP.items():
                    if prefix.startswith(p.replace('.gui_ctrl', '')):
                        return w, ctrl_type
        
        return None, None
    
    def _build_props(self, game_data: Dict[str, Any], editor_data: Dict[str, Any], ctrl_type: str, node_name: str) -> Dict[str, Any]:
        """构建属性字典"""
        props = {}
        
        # 处理Editor数据中的特殊属性
        if editor_data and isinstance(editor_data, dict):
            # __EDIT_TIME等编辑器属性
            if '__EDIT_TIME' in editor_data:
                props['__EDIT_TIME'] = editor_data['__EDIT_TIME']
        
        # 基本属性映射
        prop_mapping = [
            ('Name', 'name'),
            ('layout', 'layout'),
            ('color', 'color'),
            ('z_index', 'z_index'),
            ('show', 'show'),
            ('disabled', 'disabled'),
            ('image', 'image'),
            ('text', 'text'),
            ('font', 'font'),
            ('font_size', 'font_size'),
            ('font_color', 'font_color'),
            ('font_family', 'font_family'),
            ('placeholder', 'placeholder'),
            ('text_input', 'text_input'),
            ('progress', 'progress'),
            ('round_corner_radius', 'round_corner_radius'),
            ('loop', 'loop'),
            ('play', 'play'),
            ('view_mode', 'view_mode'),
            ('particle_size', 'particle_size'),
            ('particle_scale', 'particle_scale'),
            ('offset_percent', 'offset_percent'),
            ('auto_scale', 'auto_scale'),
            ('RenderPath', 'RenderPath'),
            ('UseShadow', 'UseShadow'),
            ('CustomString', 'CustomString'),
        ]
        
        for src_key, dst_key in prop_mapping:
            if src_key in game_data:
                value = game_data[src_key]
                if value is not None:
                    props[dst_key] = value
        
        # 确保有show属性（默认true）
        if 'show' not in props:
            props['show'] = True
        
        # 为panel和某些控件添加默认的disabled属性
        controls_with_disabled = ['panel', 'UIScene', 'input_paste']
        if ctrl_type in controls_with_disabled and 'disabled' not in props:
            props['disabled'] = False
        
        return props
    
    def _generate_lua(self, flatten_items: List[Dict[str, Any]]) -> str:
        """生成Lua代码"""
        lines = []
        
        # 文件头注释
        lines.append("-- THIS FILE IS AUTO-GENERATED, WOULD BE OVERWRITTEN BY GUI-EDITOR")
        
        # 基础require（固定顺序）
        lines.append("local component = require '@common.base.gui.component'")
        lines.append("local bind = component.bind")
        lines.append("local call = component.call")
        lines.append("local gui_pkg = require '@common.base.gui.package'")
        lines.append("local get_text = gui_pkg.get_text() or get_text")
        lines.append("local on_player_prop = require '@common.base.gui.on_player_prop'")
        lines.append("local on_unit_prop = require '@common.base.gui.on_unit_prop'")
        lines.append("local ctrl_wrapper = require '@common.base.gui.ctrl_wrapper'")
        lines.append("")
        
        # 动态require（固定顺序，与编辑器生成的一致）
        lines.append("")
        fixed_order = ['lib_game_options', 'smallcard_inventory', 'lib_control', 'gameui']
        for wrapper in fixed_order:
            if wrapper in self.REQUIRED_MODULES:
                lines.append(f"local {wrapper} = require '{self.REQUIRED_MODULES[wrapper]}'")
        lines.append("")
        
        # 开始page_template
        lines.append("return gui_pkg.page_template {")
        lines.append("    flatten_template = {")
        
        # 生成每个控件
        for item in flatten_items:
            ctrl_lua = self._generate_control(item)
            lines.append(ctrl_lua)
        
        lines.append("    }")
        lines.append("}")
        
        return '\n'.join(lines)
    
    def _generate_control(self, item: Dict[str, Any]) -> str:
        """生成单个控件的Lua代码"""
        wrapper = item['wrapper']
        ctrl_type = item['type']
        props = item['props']
        depth = item['depth']
        
        lines = []
        lines.append(f"        {wrapper}.{ctrl_type} {{")
        
        # 属性排序规则（基于现有文件的顺序）
        # 1. CustomString 最先
        # 2. __EDIT_TIME
        # 3. 其他属性按字母顺序（排除特殊后置属性）
        # 4. name
        # 5. 其他特殊属性（按字母顺序）
        # 6. show
        # 7. show之后的属性
        # 8. z_index
        
        special_first = ['CustomString', '__EDIT_TIME']
        special_after_name = ['offset_percent', 'particle_scale', 'particle_size', 
                              'placeholder', 'play', 'progress', 'round_corner_radius']
        special_after_show = ['text_input', 'view_mode']
        special_last = ['show', 'z_index']
        
        sorted_keys = []
        
        # 1. 先添加特殊优先属性
        for key in special_first:
            if key in props:
                sorted_keys.append(key)
        
        # 2. 添加普通属性（按字母顺序，排除所有特殊属性和name）
        all_special = set(special_first + special_after_name + special_after_show + special_last + ['name'])
        normal_keys = sorted([k for k in props.keys() if k not in all_special])
        sorted_keys.extend(normal_keys)
        
        # 3. 添加name
        if 'name' in props:
            sorted_keys.append('name')
        
        # 4. 添加name之后的特殊属性（按字母顺序）
        after_name_keys = sorted([k for k in special_after_name if k in props])
        sorted_keys.extend(after_name_keys)
        
        # 5. 添加show
        if 'show' in props:
            sorted_keys.append('show')
        
        # 6. 添加show之后的特殊属性
        after_show_keys = sorted([k for k in special_after_show if k in props])
        sorted_keys.extend(after_show_keys)
        
        # 7. 最后添加z_index
        if 'z_index' in props:
            sorted_keys.append('z_index')
        
        # 生成属性
        for key in sorted_keys:
            value = props[key]
            prop_line = self._format_prop(key, value, 12)
            if prop_line:
                lines.append(prop_line)
        
        lines.append(f"        }},{depth},")
        
        return '\n'.join(lines)
    
    def _format_prop(self, key: str, value: Any, indent: int = 0) -> str:
        """格式化属性"""
        indent_str = ' ' * indent
        
        if value is None:
            return ""
        
        # 必须在int之前检查bool，因为bool是int的子类
        if isinstance(value, bool):
            return f"{indent_str}{key} = {str(value).lower()},"
        elif isinstance(value, str):
            return f"{indent_str}{key} = '{value}',"
        elif isinstance(value, (int, float)):
            return f"{indent_str}{key} = {value},"
        elif isinstance(value, dict):
            # 空字典写成一行
            if not value:
                return f"{indent_str}{key} = {{}},"
            return self._format_table(key, value, indent)
        elif isinstance(value, list):
            return self._format_array(key, value, indent)
        
        return f"{indent_str}{key} = {value},"
    
    def _format_table(self, key: str, table: Dict[str, Any], indent: int) -> str:
        """格式化表"""
        indent_str = ' ' * indent
        inner_indent = ' ' * (indent + 4)
        
        # 空表写成一行
        if not table:
            return f"{indent_str}{key} = {{}},"
        
        lines = [f"{indent_str}{key} = {{"]
        
        # 特殊处理layout表的顺序
        if key == 'layout':
            layout_order = ['col_self', 'grow_height', 'grow_width', 'height', 'position', 
                           'relative', 'row_self', 'width']
            sorted_keys = []
            for k in layout_order:
                if k in table:
                    sorted_keys.append(k)
            # 添加其他未列出的键
            for k in sorted(table.keys()):
                if k not in sorted_keys:
                    sorted_keys.append(k)
        else:
            sorted_keys = sorted(table.keys(), key=lambda x: (isinstance(x, int), x))
        
        for k in sorted_keys:
            v = table[k]
            if isinstance(k, int):
                # 数字索引
                if isinstance(v, bool):  # 必须在int之前检查，因为bool是int的子类
                    lines.append(f"{inner_indent}[{k}] = {str(v).lower()},")
                elif isinstance(v, (int, float)):
                    lines.append(f"{inner_indent}[{k}] = {v},")
                elif isinstance(v, str):
                    lines.append(f"{inner_indent}[{k}] = '{v}',")
            else:
                # 字符串键
                if isinstance(v, bool):  # 必须在int之前检查，因为bool是int的子类
                    lines.append(f"{inner_indent}{k} = {str(v).lower()},")
                elif isinstance(v, (int, float)):
                    lines.append(f"{inner_indent}{k} = {v},")
                elif isinstance(v, str):
                    lines.append(f"{inner_indent}{k} = '{v}',")
                elif isinstance(v, dict):
                    # 空字典写成一行
                    if not v:
                        lines.append(f"{inner_indent}{k} = {{}},")
                    else:
                        lines.append(self._format_table(k, v, indent + 4))
        
        lines.append(f"{indent_str}}},")
        return '\n'.join(lines)
    
    def _format_array(self, key: str, arr: List[Any], indent: int) -> str:
        """格式化数组"""
        indent_str = ' ' * indent
        
        if all(isinstance(x, (int, float)) for x in arr):
            values = ', '.join(str(x) for x in arr)
            return f"{indent_str}{key} = {{{values}}},"
        
        return f"{indent_str}{key} = {{}},"
