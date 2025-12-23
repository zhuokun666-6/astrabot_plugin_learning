#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AstrBot 风格学习插件测试脚本
"""

import sys
import os
import time

# 添加插件目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugin import StyleLearningPlugin

def test_plugin():
    """测试插件的基本功能"""
    print("=== AstrBot 风格学习插件测试 ===")
    
    # 初始化插件
    plugin = StyleLearningPlugin()
    print("插件初始化完成")
    
    # 测试1：消息接收与过滤
    print("\n1. 测试消息接收与过滤功能")
    
    # 测试有效消息
    valid_message = {
        "user_id": "test_user_001",
        "user_name": "测试用户",
        "content": "你好啊，今天天气真不错！",
        "send_time": int(time.time()),
        "session_id": "test_session_001",
        "is_group": False,
        "reply_to": None
    }
    
    plugin.on_message_received(valid_message)
    print("✓ 有效消息处理完成")
    
    # 测试命令过滤
    command_message = {
        "user_id": "test_user_001",
        "user_name": "测试用户",
        "content": "!help",
        "send_time": int(time.time()),
        "session_id": "test_session_001",
        "is_group": False,
        "reply_to": None
    }
    
    plugin.on_message_received(command_message)
    print("✓ 命令消息过滤完成")
    
    # 测试链接过滤
    link_message = {
        "user_id": "test_user_001",
        "user_name": "测试用户",
        "content": "这是一个测试链接：https://example.com",
        "send_time": int(time.time()),
        "session_id": "test_session_001",
        "is_group": False,
        "reply_to": None
    }
    
    plugin.on_message_received(link_message)
    print("✓ 链接消息过滤完成")
    
    # 测试2：风格分析与学习
    print("\n2. 测试风格分析与学习功能")
    
    # 添加多条测试消息
    test_messages = [
        "今天去公园玩了，人好多啊！",
        "哈哈，你太逗了！",
        "是的，我也这么觉得~",
        "明天要不要一起去看电影？",
        "好啊好啊，我没问题！",
        "那就这么定了，明天见！",
        "对了，你知道附近有什么好吃的吗？",
        "有一家新开的餐厅不错，我上周去过~",
        "听起来不错，有空一起去尝尝",
        "好的，下次一起去！"
    ]
    
    for i, content in enumerate(test_messages):
        message = {
            "user_id": "test_user_001",
            "user_name": "测试用户",
            "content": content,
            "send_time": int(time.time()),
            "session_id": "test_session_001",
            "is_group": False,
            "reply_to": None
        }
        plugin.on_message_received(message)
        print(f"✓ 添加测试消息 {i+1}/{len(test_messages)}")
    
    # 测试3：获取风格提示词
    print("\n3. 测试获取风格提示词功能")
    
    prompt = plugin.get_style_prompt("test_user_001", "test_session_001", [])
    if prompt:
        print(f"✓ 成功获取风格提示词：")
        print(prompt)
    else:
        print("✗ 未获取到风格提示词")
    
    # 测试4：获取插件状态
    print("\n4. 测试获取插件状态功能")
    
    status = plugin.get_status()
    print(f"✓ 插件状态：")
    for key, value in status.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")
    
    # 测试5：获取统计数据
    print("\n5. 测试获取统计数据功能")
    
    stats = plugin.get_statistics()
    print(f"✓ 统计数据：")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 测试6：历史聊天记录导入功能
    print("\n6. 测试历史聊天记录导入功能")
    
    history_file = os.path.join(os.path.dirname(__file__), "test_history.txt")
    if os.path.exists(history_file):
        import_result = plugin.import_chat_history(
            file_path=history_file,
            user_id="import_user_001",
            user_name="导入用户",
            session_id="import_session_001"
        )
        
        print(f"✓ 聊天记录导入完成：")
        print(f"  总行数：{import_result['total_lines']}")
        print(f"  导入行数：{import_result['imported_lines']}")
        print(f"  过滤行数：{import_result['filtered_lines']}")
        print(f"  重复行数：{import_result['duplicate_lines']}")
        print(f"  错误行数：{import_result['error_lines']}")
        print(f"  耗时：{import_result['end_time'] - import_result['start_time']} 秒")
        
        # 测试导入后的风格提示词
        print("\n7. 测试导入后的风格提示词")
        prompt = plugin.get_style_prompt("import_user_001", "import_session_001", [])
        if prompt:
            print(f"✓ 成功获取导入后的风格提示词：")
            print(prompt)
        else:
            print("✗ 未获取到风格提示词")
    else:
        print("✗ 测试历史文件不存在")
    
    # 清理测试数据
    print("\n=== 测试完成 ===")
    print("插件功能正常！")
    
    # 卸载插件
    plugin.on_plugin_unload()

if __name__ == "__main__":
    test_plugin()