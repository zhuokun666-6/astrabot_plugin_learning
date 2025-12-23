# AstrBot 风格学习插件

一个能够学习真人说话方式和风格的插件，支持多维度风格分析和应用，帮助机器人生成更符合目标用户说话特点的回复。

## 功能特性

### 消息处理与过滤
- **智能消息过滤**：自动识别并过滤命令、无效消息、广告链接等非对话内容
- **用户黑白名单**：支持指定只学习特定用户的说话风格
- **消息去重**：避免重复消息干扰学习效果
- **历史聊天导入**：支持从文本文件导入历史聊天记录进行批量学习

### 风格分析
- **语言风格**：分析正式度、语气特征、常用词汇、标点使用习惯
- **情感倾向**：识别情绪表达风格
- **表达习惯**：提取口头禅、句式结构等个性化特征

### 学习与应用
- **实时学习**：每收到一条有效消息立即进行分析
- **批量学习**：支持积累一定数量消息后进行深度学习
- **风格提示词生成**：根据学习结果生成风格化提示词，用于影响机器人回复
- **多用户支持**：为不同用户独立存储和应用风格特征

### 数据管理
- **SQLite数据库**：使用本地数据库存储学习数据
- **数据统计**：提供学习状态、消息数量等统计信息
- **数据清理**：支持清空学习数据

## 安装使用

### 安装
将插件文件夹 `astrabot_plugin_learning` 放置在 AstrBot 的插件目录下：
```
AstrBot/data/plugins/
```

插件会自动被 AstrBot 加载，无需额外安装步骤。

### 元数据配置
插件使用 `metadata.yaml` 文件定义基本信息和配置选项，符合 AstrBot 插件规范：

```yaml
name: StyleLearningPlugin
display_name: 风格学习插件
author: AstrBot Team
description: 学习用户说话风格并应用到回复中
version: 1.0.0
type: normal
requirement: []
tags: [style, learning, chat]

config:
  enable_learning:
    type: bool
    default: true
    description: 是否启用学习功能
  batch_size:
    type: int
    default: 20
    description: 批量学习的消息数量
  max_message_length:
    type: int
    default: 500
    description: 最大消息长度
  learning_interval:
    type: int
    default: 3600
    description: 学习间隔（秒）
```

### 依赖管理
插件当前仅使用 Python 标准库，无需额外安装依赖。如未来需要添加依赖，会在 `requirements.txt` 文件中声明：

```
# 当前无第三方依赖，仅使用Python标准库
# 示例：如需添加依赖，请按以下格式
# requests>=2.28.0
# numpy>=1.24.0
```

## 配置选项

插件支持通过 AstrBot 后台或手动编辑 `config.json` 文件进行配置：

### 消息过滤配置
```json
"message_filter": {
  "command_prefix": ["!", "！", "/"],
  "min_message_length": 2,
  "max_duplicate_count": 3,
  "whitelist_users": [],
  "blacklist_users": []
}
```

### 学习配置
```json
"learning": {
  "batch_size": 20,
  "learning_interval": 3600,
  "max_cache_size": 1000,
  "style_update_threshold": 0.7
}
```

### 风格应用配置
```json
"style_application": {
  "default_imitation_level": 0.7,
  "max_history_length": 50
}
```

## 使用方法

### 基本使用
插件会自动监听并处理所有通过 AstrBot 传递的消息，无需手动调用。

### 导入历史聊天记录
1. 准备文本文件 `test_history.txt`，格式如下：
   ```
   [2023-10-01 10:00:00] 用户：你好啊，今天天气真不错！
   [2023-10-01 10:01:30] 用户：打算下午去公园散步，你要一起吗？
   [2023-10-01 10:02:15] 用户：听说公园里的菊花开了，应该很漂亮。
   ```

2. 调用导入方法：
   ```python
   plugin.import_chat_history("123456", "session_001", "test_history.txt")
   ```

3. 导入完成后，插件会自动进行批量学习并生成风格提示词。

### 获取风格提示词
```python
from astrabot_plugin_learning import StyleLearningPlugin

plugin = StyleLearningPlugin()
prompt = plugin.get_style_prompt("123456", "session_001", [])
print(prompt)  # 输出风格化提示词
```

## API 接口

### 核心方法

#### `on_message_received(message)`
接收并处理消息，自动进行过滤和学习。

**参数**：
- `message`：包含消息内容的字典，需包含 `user_id`、`content`、`send_time`、`session_id` 等字段

#### `get_style_prompt(user_id, session_id, context)`
获取指定用户的风格化提示词。

**参数**：
- `user_id`：用户ID
- `session_id`：会话ID
- `context`：上下文信息

**返回**：
- 风格化提示词字符串

#### `import_chat_history(user_id, session_id, file_path)`
导入历史聊天记录。

**参数**：
- `user_id`：用户ID
- `session_id`：会话ID
- `file_path`：历史聊天文件路径

**返回**：
- 导入结果字典，包含成功/失败数量等信息

#### `get_statistics()`
获取插件统计数据。

**返回**：
- 统计信息字典

## 数据存储

插件使用 SQLite 数据库存储学习数据，数据库文件位于：
```
data/learning_data.db
```

主要表结构：
- `messages`：存储收集到的有效消息
- `style_features`：存储分析得到的风格特征
- `statistics`：存储统计数据

## 开发与扩展

### 插件结构
```
astrabot_plugin_learning/
├── __init__.py          # 插件入口
├── plugin.py            # 主要实现
├── metadata.yaml        # 元数据配置（必填）
├── requirements.txt     # 依赖声明（必填）
├── config.json          # 运行时配置
├── README.md            # 说明文档
├── HISTORY_IMPORT_GUIDE.md  # 历史导入指南
├── test_plugin.py       # 测试脚本
├── test_history.txt     # 测试用历史聊天数据
└── data/                # 数据目录
    └── learning_data.db  # SQLite数据库
```

### 扩展开发

#### 添加新的风格分析维度
编辑 `plugin.py` 中的 `_analyze_style` 方法，添加新的分析逻辑：

```python
def _analyze_style(self, messages):
    # 现有分析逻辑
    # 添加新的分析维度
    new_dimension = self._analyze_new_dimension(messages)
    style_features["new_dimension"] = new_dimension
    return style_features
```

#### 添加新的过滤规则
编辑 `plugin.py` 中的 `_filter_message` 方法：

```python
def _filter_message(self, message):
    # 现有过滤逻辑
    # 添加新的过滤条件
    if new_filter_condition(message):
        return False
    return True
```

## 注意事项

1. **数据隐私**：插件会收集用户对话数据用于学习，请确保遵守相关隐私政策
2. **首次使用**：需要积累一定数量的消息才能生成有效的风格特征
3. **性能影响**：批量学习可能会占用一定系统资源，可通过配置调整学习间隔
4. **历史导入**：导入的历史记录需遵循特定格式，详见 `HISTORY_IMPORT_GUIDE.md`

## 更新日志

### v1.0.0
- 初始版本发布
- 实现核心的风格学习和应用功能
- 支持历史聊天记录导入
- 符合 AstrBot 插件开发规范

## 联系方式

如有问题或建议，欢迎通过 AstrBot 官方渠道反馈。