# view2lua - Editor UI数据转Lua工具

## 概述

将星火编辑器的 `entry_data.ini` 配置文件转换为 Lua `template.lua` 文件。

## 路径配置

| 类型 | 路径 |
|------|------|
| 源数据目录 | `editor/table/entry_data/template@gui_ctrl/` |
| 输出目录 | `ui/script/gui/page/` |

## 使用方法

```bash
# 进入工具目录
cd mytools/view2lua

# 列出所有可转换的组件
python main.py --list

# 验证所有组件
python main.py --validate

# 验证单个组件
python main.py --validate-one <组件名>

# 转换单个组件（预览模式）
python main.py --convert <组件名> --dry-run

# 转换单个组件（实际写入）
python main.py --convert <组件名>

# 转换所有组件（预览模式）
python main.py --convert-all --dry-run

# 转换所有组件（实际写入）
python main.py --convert-all

# 指定项目根目录
python main.py --list --project D:\Project\GameProject\dahuaxiyou_checkout
```

## 命令参数

| 参数 | 说明 |
|------|------|
| `--list` | 列出所有组件及其状态 |
| `--validate` | 验证所有组件的转换结果 |
| `--validate-one <name>` | 验证单个组件 |
| `--convert <name>` | 转换单个组件 |
| `--convert-all` | 转换所有组件 |
| `--dry-run` | 预览模式，不实际写入文件 |
| `--project <path>` | 指定项目根目录 |

## 输出文件

转换后会在 `ui/script/gui/page/<组件名>/` 目录下生成：

- `template.lua` - UI模板定义文件
- `component.lua` - 组件逻辑文件（如不存在则自动创建）

## 模块结构

```
view2lua/
├── main.py              # 主入口，命令行处理
├── parser/
│   ├── entry_data.py    # 解析 entry_data.ini 文件
│   └── lua_template.py  # 解析现有 template.lua 文件
├── converter/
│   └── to_lua.py        # 转换为 Lua 代码
├── validator/
│   └── compare.py       # 验证转换结果
└── utils/
    └── lua_writer.py    # Lua 代码生成工具
```

## 示例

### 列出组件
```bash
python main.py --list
```
输出：
```
=== Components ===
Dir Name                                 Display Name         Has Lua
----------------------------------------------------------------------
ChatMainView                             ChatMainView         Yes
WarMainView                              WarMainView          Yes
...
Total: 200 components
```

### 转换组件
```bash
python main.py --convert ChatMainView --dry-run
```
输出：
```
=== Converting: ChatMainView ===
Display name: ChatMainView
Sections: ['template', 'panel_bg', 'btn_close', ...]

[DRY RUN] Would write to: ui/script/gui/page/ChatMainView/template.lua

--- Generated Lua ---
-- THIS FILE IS AUTO-GENERATED, WOULD BE OVERWRITTEN BY GUI-EDITOR
local component = require '@common.base.gui.component'
...
```

## 注意事项

1. 以 `$$` 开头的目录为内部组件，转换时会自动跳过
2. 转换前会自动备份现有的 `template.lua` 为 `template.lua.bak`
3. 建议先使用 `--dry-run` 预览，确认无误后再实际转换
4. 验证功能会比较生成的代码与现有文件的差异
