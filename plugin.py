import json
import time
import re
import sqlite3
import threading
import datetime
import hashlib
import os
from typing import Dict, List, Optional, Any

class StyleLearningPlugin:
    """AstrBot 风格学习插件 - 学习真人说话方式和风格"""
    
    def __init__(self):
        self.name = "astrabot_plugin_learning"
        self.version = "1.0.0"
        self.author = "AstrBot"
        self.description = "学习真人说话风格的插件，支持多维度风格分析和应用"
        
        # 配置文件路径
        self.config_path = os.path.join(os.path.dirname(__file__), "config.json")
        self.data_path = os.path.join(os.path.dirname(__file__), "data")
        self.db_path = os.path.join(self.data_path, "learning_data.db")
        
        # 加载配置
        self.config = self._load_config()
        
        # 初始化数据库
        self._init_database()
        
        # 消息缓存
        self.message_cache = {}
        self.cache_lock = threading.Lock()
        
        # 学习任务管理
        self.learning_tasks = {}
        self.tasks_lock = threading.Lock()
        
        # 风格特征存储
        self.style_features = {}
        self.style_lock = threading.Lock()
        
        # 异步任务线程池
        self.task_pool = []
        
        print(f"[{self.name}] 插件初始化完成")
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        default_config = {
            "message_filter": {
                "command_prefix": ["!", "！", "/"],
                "min_message_length": 2,
                "max_duplicate_count": 3,
                "sensitive_words": [],
                "whitelist_users": [],
                "blacklist_users": []
            },
            "learning": {
                "batch_size": 20,
                "learning_interval": 3600,  # 1小时
                "max_cache_size": 1000,
                "style_update_threshold": 0.7
            },
            "database": {
                "type": "sqlite",
                "host": "localhost",
                "port": 3306,
                "username": "",
                "password": "",
                "database": ""
            },
            "style_application": {
                "default_imitation_level": 0.7,
                "max_history_length": 50
            },
            "logging": {
                "level": "INFO",
                "log_file": "learning_plugin.log"
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 合并配置
                    for key, value in user_config.items():
                        if key in default_config:
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
            except Exception as e:
                print(f"[{self.name}] 加载配置失败: {e}")
        
        # 保存配置
        self._save_config(default_config)
        return default_config
    
    def _save_config(self, config: Dict):
        """保存配置文件"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def _init_database(self):
        """初始化数据库"""
        os.makedirs(self.data_path, exist_ok=True)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建消息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    send_time INTEGER NOT NULL,
                    session_id TEXT NOT NULL,
                    is_group BOOLEAN NOT NULL,
                    reply_to INTEGER,
                    is_valid BOOLEAN DEFAULT TRUE,
                    created_at INTEGER DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建风格特征表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS style_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    feature_name TEXT NOT NULL,
                    feature_value TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    update_time INTEGER NOT NULL,
                    UNIQUE(user_id, feature_name)
                )
            ''')
            
            # 创建会话上下文表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    context_data TEXT NOT NULL,
                    update_time INTEGER NOT NULL,
                    UNIQUE(session_id)
                )
            ''')
            
            # 创建统计数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value TEXT NOT NULL,
                    update_time INTEGER NOT NULL,
                    UNIQUE(metric_name)
                )
            ''')
            
            conn.commit()
            conn.close()
            print(f"[{self.name}] 数据库初始化完成")
        except Exception as e:
            print(f"[{self.name}] 数据库初始化失败: {e}")
    
    # 一、基础：有效消息收集与过滤模块
    def handle_message(self, message: Dict):
        """消息处理函数 - AstrBot标准接口"""
        # 全场景消息监听
        if not self._is_valid_message_format(message):
            return
        
        # 提取消息元数据
        message_data = self._extract_message_metadata(message)
        
        # 智能消息过滤
        if not self._filter_message(message_data):
            return
        
        # 消息去重与缓存
        if self._is_duplicate_message(message_data):
            return
        
        # 保存有效消息
        self._save_message(message_data)
        
        # 触发学习
        self._trigger_learning(message_data)
    
    def on_enable(self):
        """插件启用时调用 - AstrBot标准接口"""
        print(f"[{self.name}] 插件已启用")
        return True
    
    def on_disable(self):
        """插件禁用时调用 - AstrBot标准接口"""
        self.on_plugin_unload()
        return True
    
    def on_reload(self):
        """插件重载时调用 - AstrBot标准接口"""
        # 重新加载配置
        self.config = self._load_config()
        print(f"[{self.name}] 插件已重载")
        return True
    
    def _is_valid_message_format(self, message: Dict) -> bool:
        """验证消息格式是否有效"""
        required_fields = ["user_id", "user_name", "content", "send_time", "session_id"]
        for field in required_fields:
            if field not in message:
                return False
        return True
    
    def _extract_message_metadata(self, message: Dict) -> Dict:
        """提取消息核心元数据"""
        return {
            "user_id": message["user_id"],
            "user_name": message["user_name"],
            "content": message["content"],
            "send_time": message["send_time"],
            "session_id": message["session_id"],
            "is_group": message.get("is_group", False),
            "reply_to": message.get("reply_to", None)
        }
    
    def _filter_message(self, message: Dict) -> bool:
        """智能消息过滤"""
        content = message["content"].strip()
        user_id = message["user_id"]
        
        # 命令过滤
        for prefix in self.config["message_filter"]["command_prefix"]:
            if content.startswith(prefix):
                return False
        
        # 长度过滤
        if len(content) < self.config["message_filter"]["min_message_length"]:
            return False
        
        # 用户过滤
        if user_id in self.config["message_filter"]["blacklist_users"]:
            return False
        
        if self.config["message_filter"]["whitelist_users"] and \
           user_id not in self.config["message_filter"]["whitelist_users"]:
            return False
        
        # 内容过滤（广告、链接、敏感信息）
        if re.search(r'(http|https)://\S+', content):
            return False
        
        # 敏感词过滤
        for word in self.config["message_filter"]["sensitive_words"]:
            if word in content:
                return False
        
        return True
    
    def _is_duplicate_message(self, message: Dict) -> bool:
        """检查消息是否重复"""
        content = message["content"]
        session_id = message["session_id"]
        
        # 生成消息哈希
        message_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        with self.cache_lock:
            # 清理过期缓存
            current_time = time.time()
            self.message_cache = {
                k: v for k, v in self.message_cache.items()
                if current_time - v["timestamp"] < 3600  # 1小时过期
            }
            
            # 检查重复
            cache_key = f"{session_id}:{message_hash}"
            if cache_key in self.message_cache:
                self.message_cache[cache_key]["count"] += 1
                if self.message_cache[cache_key]["count"] > self.config["message_filter"]["max_duplicate_count"]:
                    return True
            else:
                self.message_cache[cache_key] = {
                    "timestamp": current_time,
                    "count": 1
                }
        
        return False
    
    def _save_message(self, message: Dict):
        """保存有效消息到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO messages (user_id, user_name, content, send_time, session_id, is_group, reply_to)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                message["user_id"],
                message["user_name"],
                message["content"],
                message["send_time"],
                message["session_id"],
                message["is_group"],
                message["reply_to"]
            ))
            
            conn.commit()
            conn.close()
            
            # 更新统计
            self._update_statistic("total_messages", 1)
            self._update_statistic("valid_messages", 1)
            
        except Exception as e:
            print(f"[{self.name}] 保存消息失败: {e}")
    
    # 二、核心：多维度风格分析模块
    def _analyze_style(self, user_id: str, messages: List[Dict]) -> Dict:
        """分析用户的说话风格"""
        if not messages:
            return {}
        
        style = {
            "user_id": user_id,
            "language_style": self._analyze_language_style(messages),
            "emotional_style": self._analyze_emotional_style(messages),
            "conversation_style": self._analyze_conversation_style(messages),
            "scene_patterns": self._extract_scene_patterns(messages),
            "update_time": int(time.time())
        }
        
        return style
    
    def _analyze_language_style(self, messages: List[Dict]) -> Dict:
        """分析语言风格"""
        # 统计各种语言特征
        total_length = 0
        exclamation_count = 0
        question_count = 0
        emoji_count = 0
        sentence_count = 0
        
        for msg in messages:
            content = msg["content"]
            total_length += len(content)
            sentence_count += len(re.split(r'[。！？!?.]', content))
            exclamation_count += content.count('!') + content.count('！')
            question_count += content.count('?') + content.count('？')
            # 安全的表情符号匹配方式（避免Unicode转义问题）
            emoji_pattern = re.compile(r'[\U0001F600-\U0001F6FF]', re.UNICODE)
            emoji_count += len(emoji_pattern.findall(content))
        
        # 计算平均值
        avg_length = total_length / len(messages) if messages else 0
        avg_sentence_length = total_length / sentence_count if sentence_count else 0
        
        # 分析正式度
        formal_words = ["您好", "请问", "谢谢", "对不起", "请"]
        informal_words = ["哈哈", "嘿嘿", "哦哦", "嗯", "哎"]
        
        formal_count = 0
        informal_count = 0
        
        for msg in messages:
            for word in formal_words:
                if word in msg["content"]:
                    formal_count += 1
                    break
            for word in informal_words:
                if word in msg["content"]:
                    informal_count += 1
                    break
        
        # 确定正式度
        formal_degree = 0.5
        if formal_count > informal_count:
            formal_degree = 0.7
        elif informal_count > formal_count:
            formal_degree = 0.3
        
        return {
            "formal_degree": formal_degree,
            "avg_message_length": avg_length,
            "avg_sentence_length": avg_sentence_length,
            "exclamation_frequency": exclamation_count / len(messages) if messages else 0,
            "question_frequency": question_count / len(messages) if messages else 0,
            "emoji_frequency": emoji_count / len(messages) if messages else 0
        }
    
    def _analyze_emotional_style(self, messages: List[Dict]) -> Dict:
        """分析情感风格"""
        # 简单的情感分析
        positive_words = ["好", "开心", "快乐", "喜欢", "不错", "棒", "优秀"]
        negative_words = ["不好", "难过", "伤心", "讨厌", "糟糕", "差", "失望"]
        
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for msg in messages:
            content = msg["content"]
            has_positive = any(word in content for word in positive_words)
            has_negative = any(word in content for word in negative_words)
            
            if has_positive and has_negative:
                neutral_count += 1
            elif has_positive:
                positive_count += 1
            elif has_negative:
                negative_count += 1
            else:
                neutral_count += 1
        
        total = len(messages)
        return {
            "positive_ratio": positive_count / total if total else 0,
            "negative_ratio": negative_count / total if total else 0,
            "neutral_ratio": neutral_count / total if total else 0,
            "emotion_expression_degree": 0.5  # 简单默认值，可根据实际情况调整
        }
    
    def _analyze_conversation_style(self, messages: List[Dict]) -> Dict:
        """分析对话结构风格"""
        reply_count = 0
        question_count = 0
        statement_count = 0
        
        for msg in messages:
            if msg["reply_to"] is not None:
                reply_count += 1
            
            content = msg["content"]
            if content.endswith(('?', '？')):
                question_count += 1
            else:
                statement_count += 1
        
        return {
            "reply_ratio": reply_count / len(messages) if messages else 0,
            "question_ratio": question_count / len(messages) if messages else 0,
            "statement_ratio": statement_count / len(messages) if messages else 0
        }
    
    def _extract_scene_patterns(self, messages: List[Dict]) -> List[Dict]:
        """提取场景化表达模式"""
        # 简单的场景模式提取示例
        patterns = []
        
        for msg in messages:
            content = msg["content"]
            
            # 问候场景
            if re.search(r'(你好|您好|早上好|晚上好|hello|hi)', content, re.IGNORECASE):
                patterns.append({
                    "scene": "greeting",
                    "expression": content,
                    "confidence": 0.9
                })
            
            # 求助场景
            elif re.search(r'(帮我|求助|需要|怎么|如何)', content):
                patterns.append({
                    "scene": "request_help",
                    "expression": content,
                    "confidence": 0.8
                })
            
            # 感谢场景
            elif re.search(r'(谢谢|感谢|谢了|麻烦了)', content):
                patterns.append({
                    "scene": "thanks",
                    "expression": content,
                    "confidence": 0.9
                })
        
        return patterns
    
    # 三、核心：灵活的学习模式模块
    def _trigger_learning(self, message: Dict):
        """触发学习任务"""
        user_id = message["user_id"]
        session_id = message["session_id"]
        
        # 检查是否需要启动学习任务
        with self.tasks_lock:
            if session_id not in self.learning_tasks or not self.learning_tasks[session_id]:
                # 获取用户的有效消息数量
                valid_count = self._get_valid_message_count(user_id)
                
                if valid_count >= self.config["learning"]["batch_size"]:
                    # 启动异步学习任务
                    task = threading.Thread(
                        target=self._batch_learning,
                        args=(user_id, session_id)
                    )
                    task.daemon = True
                    task.start()
                    
                    self.learning_tasks[session_id] = task
                    print(f"[{self.name}] 启动学习任务: 用户 {user_id}, 会话 {session_id}")
    
    def _get_valid_message_count(self, user_id: str) -> int:
        """获取用户的有效消息数量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM messages 
                WHERE user_id = ? AND is_valid = TRUE
            ''', (user_id,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
        except Exception as e:
            print(f"[{self.name}] 获取消息数量失败: {e}")
            return 0
    
    def _batch_learning(self, user_id: str, session_id: str):
        """批量学习任务"""
        try:
            # 获取用户的有效消息
            messages = self._get_user_messages(user_id, limit=self.config["learning"]["batch_size"])
            
            if not messages:
                return
            
            # 分析风格特征
            style = self._analyze_style(user_id, messages)
            
            # 保存风格特征
            self._save_style_features(user_id, style)
            
            # 更新学习统计
            self._update_statistic("style_updates", 1)
            self._update_statistic("last_learning_time", int(time.time()))
            
            print(f"[{self.name}] 学习完成: 用户 {user_id}, 分析了 {len(messages)} 条消息")
            
        except Exception as e:
            print(f"[{self.name}] 学习任务失败: {e}")
        finally:
            # 清除任务标记
            with self.tasks_lock:
                if session_id in self.learning_tasks:
                    del self.learning_tasks[session_id]
    
    def _get_user_messages(self, user_id: str, limit: int = 100) -> List[Dict]:
        """获取用户的消息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, user_id, user_name, content, send_time, session_id, is_group, reply_to 
                FROM messages 
                WHERE user_id = ? AND is_valid = TRUE 
                ORDER BY send_time DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            messages = []
            for row in rows:
                messages.append({
                    "id": row[0],
                    "user_id": row[1],
                    "user_name": row[2],
                    "content": row[3],
                    "send_time": row[4],
                    "session_id": row[5],
                    "is_group": row[6],
                    "reply_to": row[7]
                })
            
            return messages
        except Exception as e:
            print(f"[{self.name}] 获取用户消息失败: {e}")
            return []
    
    def _save_style_features(self, user_id: str, style: Dict):
        """保存风格特征到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            update_time = int(time.time())
            
            # 保存语言风格
            for feature, value in style["language_style"].items():
                cursor.execute('''
                    INSERT OR REPLACE INTO style_features 
                    (user_id, feature_name, feature_value, confidence, update_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, f"language_{feature}", str(value), 0.8, update_time))
            
            # 保存情感风格
            for feature, value in style["emotional_style"].items():
                cursor.execute('''
                    INSERT OR REPLACE INTO style_features 
                    (user_id, feature_name, feature_value, confidence, update_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, f"emotion_{feature}", str(value), 0.7, update_time))
            
            # 保存对话风格
            for feature, value in style["conversation_style"].items():
                cursor.execute('''
                    INSERT OR REPLACE INTO style_features 
                    (user_id, feature_name, feature_value, confidence, update_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, f"conversation_{feature}", str(value), 0.8, update_time))
            
            conn.commit()
            conn.close()
            
            # 更新内存中的风格特征
            with self.style_lock:
                self.style_features[user_id] = style
                
        except Exception as e:
            print(f"[{self.name}] 保存风格特征失败: {e}")
    
    # 四、关键：学习结果落地应用模块
    def get_style_prompt(self, user_id: str, session_id: str, context: List[Dict]) -> str:
        """获取风格化提示词"""
        # 获取用户的风格特征
        style = self._get_user_style(user_id)
        
        if not style:
            return ""
        
        # 构建风格提示词
        prompt_parts = ["请模仿以下说话风格回复："]
        
        # 语言风格
        lang_style = style["language_style"]
        if lang_style["formal_degree"] > 0.7:
            prompt_parts.append("- 正式礼貌的语气")
        elif lang_style["formal_degree"] < 0.3:
            prompt_parts.append("- 随意轻松的语气")
        else:
            prompt_parts.append("- 适中得体的语气")
        
        if lang_style["emoji_frequency"] > 0.5:
            prompt_parts.append("- 适当使用表情符号")
        
        if lang_style["exclamation_frequency"] > 0.3:
            prompt_parts.append("- 偶尔使用感叹号")
        
        # 情感风格
        emotion_style = style["emotional_style"]
        if emotion_style["positive_ratio"] > 0.6:
            prompt_parts.append("- 积极乐观的态度")
        elif emotion_style["negative_ratio"] > 0.4:
            prompt_parts.append("- 较为谨慎的态度")
        
        # 对话风格
        conv_style = style["conversation_style"]
        if conv_style["reply_ratio"] > 0.5:
            prompt_parts.append("- 注重回复他人的问题")
        
        if conv_style["question_ratio"] > 0.3:
            prompt_parts.append("- 适当提问引导对话")
        
        return "\n".join(prompt_parts)
    
    def _get_user_style(self, user_id: str) -> Optional[Dict]:
        """获取用户的风格特征"""
        # 先从内存中获取
        with self.style_lock:
            if user_id in self.style_features:
                return self.style_features[user_id]
        
        # 从数据库中获取
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT feature_name, feature_value, confidence 
                FROM style_features 
                WHERE user_id = ?
            ''', (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return None
            
            # 重构风格特征
            style = {
                "user_id": user_id,
                "language_style": {},
                "emotional_style": {},
                "conversation_style": {},
                "scene_patterns": [],
                "update_time": int(time.time())
            }
            
            for row in rows:
                feature_name, feature_value, confidence = row
                
                if feature_name.startswith("language_"):
                    style["language_style"][feature_name[9:]] = float(feature_value)
                elif feature_name.startswith("emotion_"):
                    style["emotional_style"][feature_name[8:]] = float(feature_value)
                elif feature_name.startswith("conversation_"):
                    style["conversation_style"][feature_name[13:]] = float(feature_value)
            
            # 保存到内存
            with self.style_lock:
                self.style_features[user_id] = style
            
            return style
            
        except Exception as e:
            print(f"[{self.name}] 获取风格特征失败: {e}")
            return None
    
    # 五、管理：风格与人格管控模块
    def update_style_config(self, user_id: str, config: Dict):
        """更新风格配置"""
        # 实现风格配置更新逻辑
        pass
    
    def backup_styles(self, user_id: Optional[str] = None):
        """备份风格特征"""
        # 实现风格备份逻辑
        pass
    
    def restore_styles(self, backup_file: str):
        """恢复风格特征"""
        # 实现风格恢复逻辑
        pass
    
    # 六、增强：对话交互优化模块
    def update_session_context(self, session_id: str, context: List[Dict]):
        """更新会话上下文"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            context_data = json.dumps(context)
            update_time = int(time.time())
            
            cursor.execute('''
                INSERT OR REPLACE INTO session_context 
                (session_id, context_data, update_time)
                VALUES (?, ?, ?)
            ''', (session_id, context_data, update_time))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[{self.name}] 更新会话上下文失败: {e}")
    
    def get_session_context(self, session_id: str) -> List[Dict]:
        """获取会话上下文"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT context_data FROM session_context 
                WHERE session_id = ?
            ''', (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return json.loads(row[0])
            
            return []
            
        except Exception as e:
            print(f"[{self.name}] 获取会话上下文失败: {e}")
            return []
    
    # 七、保障：数据管理与统计模块
    def _update_statistic(self, metric_name: str, metric_value: Any):
        """更新统计数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            update_time = int(time.time())
            
            cursor.execute('''
                INSERT OR REPLACE INTO statistics 
                (metric_name, metric_value, update_time)
                VALUES (?, ?, ?)
            ''', (metric_name, str(metric_value), update_time))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[{self.name}] 更新统计数据失败: {e}")
    
    def get_statistics(self) -> Dict:
        """获取统计数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT metric_name, metric_value, update_time FROM statistics')
            rows = cursor.fetchall()
            conn.close()
            
            statistics = {}
            for row in rows:
                metric_name, metric_value, update_time = row
                statistics[metric_name] = {
                    "value": metric_value,
                    "update_time": update_time
                }
            
            return statistics
            
        except Exception as e:
            print(f"[{self.name}] 获取统计数据失败: {e}")
            return {}
    
    def export_data(self, user_id: Optional[str] = None, format: str = "json") -> str:
        """导出数据"""
        # 实现数据导出逻辑
        pass
    
    def clear_data(self, user_id: Optional[str] = None, session_id: Optional[str] = None):
        """清空数据"""
        # 实现数据清空逻辑
        pass
    
    def import_chat_history(self, file_path: str, user_id: str, user_name: str, session_id: str = "import_session") -> Dict:
        """导入历史聊天记录
        
        Args:
            file_path: 聊天记录文本文件路径
            user_id: 历史记录中用户的ID
            user_name: 历史记录中用户的昵称
            session_id: 会话ID（默认为import_session）
        
        Returns:
            Dict: 导入结果统计
        """
        result = {
            "total_lines": 0,
            "imported_lines": 0,
            "filtered_lines": 0,
            "duplicate_lines": 0,
            "error_lines": 0,
            "start_time": int(time.time()),
            "end_time": 0
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                result["total_lines"] = len(lines)
                
                # 处理每条记录
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 尝试解析时间戳（支持常见格式如：[2023-10-05 14:30:00] 或 2023/10/05 14:30:00）
                    timestamp_match = re.search(r'^\[?(\d{4}[-/]\d{2}[-/]\d{2}\s\d{2}:\d{2}:\d{2})\]?', line)
                    if timestamp_match:
                        # 解析到时间戳，使用真实时间
                        timestamp = int(datetime.datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S').timestamp())
                    else:
                        # 简单的时间戳生成（使用文件行号作为相对时间）
                        timestamp = int(time.time()) - (len(lines) - i) * 60  # 每条消息间隔1分钟
                    
                    # 创建消息对象
                    message = {
                        "user_id": user_id,
                        "user_name": user_name,
                        "content": line,
                        "send_time": timestamp,
                        "session_id": session_id,
                        "is_group": False,
                        "reply_to": None
                    }
                    
                    try:
                        # 验证消息格式
                        if not self._is_valid_message_format(message):
                            result["error_lines"] += 1
                            continue
                        
                        # 提取元数据
                        message_data = self._extract_message_metadata(message)
                        
                        # 过滤消息
                        if not self._filter_message(message_data):
                            result["filtered_lines"] += 1
                            continue
                        
                        # 检查重复（使用特殊的导入缓存，避免与实时消息冲突）
                        import_cache_key = f"import:{session_id}:{hashlib.md5(line.encode('utf-8')).hexdigest()}"
                        with self.cache_lock:
                            if import_cache_key in self.message_cache:
                                result["duplicate_lines"] += 1
                                continue
                            else:
                                self.message_cache[import_cache_key] = {
                                    "timestamp": time.time(),
                                    "count": 1
                                }
                        
                        # 保存消息
                        self._save_message(message_data)
                        result["imported_lines"] += 1
                        
                        # 每100条消息输出进度
                        if (i + 1) % 100 == 0:
                            print(f"[{self.name}] 导入进度: {i+1}/{len(lines)} 行")
                            
                    except Exception as e:
                        result["error_lines"] += 1
                        print(f"[{self.name}] 导入第 {i+1} 行失败: {e}")
            
            # 导入完成后触发批量学习
            if result["imported_lines"] > 0:
                print(f"[{self.name}] 导入完成，开始批量学习...")
                
                try:
                    # 获取导入的消息
                    messages = self._get_user_messages(user_id, limit=result["imported_lines"])
                    if messages:
                        # 分析风格
                        style = self._analyze_style(user_id, messages)
                        # 保存风格特征
                        self._save_style_features(user_id, style)
                    
                    print(f"[{self.name}] 批量学习完成")
                except Exception as e:
                    print(f"[{self.name}] 批量学习失败: {str(e)}")
            
            # 更新结束时间（使用浮点数，与start_time保持一致）
            result["end_time"] = time.time()
            print(f"[{self.name}] 聊天记录导入完成: {result}")
            
        except Exception as e:
            print(f"[{self.name}] 导入聊天记录失败: {str(e)}")
            result["error_lines"] += result["total_lines"] - result["imported_lines"] - result["filtered_lines"] - result["duplicate_lines"]
        
        return result
    
    # 八、基础：稳定性与运维模块
    def on_plugin_unload(self):
        """插件卸载时的清理工作"""
        # 停止所有学习任务
        with self.tasks_lock:
            for task in self.learning_tasks.values():
                if task and task.is_alive():
                    # 等待任务完成
                    task.join(timeout=5)
        
        # 清理内存缓存
        with self.cache_lock:
            self.message_cache.clear()
        
        with self.style_lock:
            self.style_features.clear()
        
        # 关闭数据库连接
        print(f"[{self.name}] 插件卸载完成")
    
    def get_status(self) -> Dict:
        """获取插件状态"""
        return {
            "name": self.name,
            "version": self.version,
            "status": "running",
            "message_cache_size": len(self.message_cache),
            "style_features_count": len(self.style_features),
            "active_tasks": len([t for t in self.learning_tasks.values() if t and t.is_alive()]),
            "statistics": self.get_statistics()
        }

# 插件入口函数
def get_plugin():
    return StyleLearningPlugin()