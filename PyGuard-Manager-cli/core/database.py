import sqlite3
import os
import logging

class DatabaseManager:
    def __init__(self, db_name="pyguard.db"):
        # 获取当前文件 (database.py) 的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 向上跳一级到项目根目录 (从 core 文件夹跳出来)
        project_root = os.path.dirname(current_dir)
        # 定义数据文件夹：项目根目录/file
        data_dir = os.path.join(project_root, "file")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        self.db_path = os.path.join(data_dir, db_name)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """初始化数据库表结构"""
        # 存储用户安全配置
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY,
            salt BLOB NOT NULL,
            version TEXT DEFAULT '1.0'
            )
        ''')

        #金丝雀表：用于验证主密码是否正确
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS canary (
                id INTEGER PRIMARY KEY CHECK (id = 1), -- 强制 ID 只能为 1
                encrypted_verifier TEXT NOT NULL
                )
            ''')
        # 密码储存表
        self.cursor.execute('''
    CREATE TABLE IF NOT EXISTS vault (
        id INTEGER PRIMARY KEY,
        service_name TEXT NOT NULL,
        username TEXT NOT NULL,
        encrypted_data TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 新增：自动记录插入时间
        )
    ''')

        # 自爆装置
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        self.conn.commit()

    def has_user(self):
        """检查数据库是否已经有初始化记录"""
        self.cursor.execute("SELECT COUNT(*) FROM config")
        return self.cursor.fetchone()[0] > 0

    def get_user_salt(self):
        """获取存储地盐值"""
        self.cursor.execute("SELECT salt FROM config WHERE id =1")
        result = self.cursor.fetchone()
        return result[0] if result else None

    def initialize_vault(self, salt, encrypted_canary):
        """
        一次性初始化金库：保存盐值和金丝雀
        这是新用户注册的唯一入口
        """
        try:
            # 使用 INSERT OR REPLACE 防止重复初始化导致的冲突
            self.cursor.execute("INSERT OR REPLACE INTO config (id, salt) VALUES (1, ?)", (salt,))
            self.cursor.execute("INSERT OR REPLACE INTO canary (id, encrypted_verifier) VALUES (1, ?)", (encrypted_canary,))
            self.conn.commit()
            logging.info("金库底层元数据 (Salt & Canary) 初始化成功")
        except sqlite3.Error as e:
            logging.error(f"数据库初始化严重失败: {e}")
            self.conn.rollback()
            # 底层错误必须抛出，让 logic.py 知道初始化失败了
            raise Exception("数据库写入被拒绝或发生底层损坏")

    def save_password(self, service, username, encrypted_blob):
        """保存一条加密记录"""
        try:
            sql = "INSERT INTO vault (service_name, username, encrypted_data) VALUES (?, ?, ?)"
            self.cursor.execute(sql, (service, username, encrypted_blob))
            self.conn.commit()
            logging.info(f"凭据 [{service}] 已安全写入数据库")
        except sqlite3.Error as e:
            logging.error(f"保存凭据 [{service}] 时数据库写入失败: {e}")
            self.conn.rollback()
            raise Exception("数据库写入被拒绝或文件被意外锁死")

    def get_canary(self):
        """用于获取验证地密文"""
        self.cursor.execute("SELECT encrypted_verifier FROM canary WHERE id=1")
        result =self.cursor.fetchone()
        return result[0] if result else None

    def get_all_credentials(self):
        """获取所有存储地服务名称和用户名（用于列表展示）"""
        self.cursor.execute("SELECT id,service_name,username,encrypted_data FROM vault")
        #由于设置了row_factory,这里返回的是类似字典的对象列表
        return self.cursor.fetchall()

    def delete_credential(self, entry_id):
        """根据ID删除一条记录"""
        try:
            self.cursor.execute("DELETE FROM vault WHERE id=?", (entry_id,))
            self.conn.commit()
            success = self.cursor.rowcount > 0
            if success:
                logging.info(f"成功物理抹除 ID: {entry_id} 的凭据记录")
            return success
        except sqlite3.Error as e:
            logging.error(f"尝试删除 ID: {entry_id} 时数据库报错：{e}")
            return False

    def search_credentials(self, keyword):
        """根据服务名称进行模糊搜索 (数据层)"""
        query = "SELECT id, service_name, username, encrypted_data FROM vault WHERE service_name LIKE ?"
        self.cursor.execute(query, (f'%{keyword}%',))
        # 设置了 row_factory，这里返回的就是可以直接按键名访问的 Row 对象列表
        return self.cursor.fetchall()

    def read_setting(self, key):
        """读取系统配置 (数据层)"""
        try:
            self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = self.cursor.fetchone()
            # 因为之前设置了 row_factory，可以使用列索引或列名获取数据
            return row[0] if row else None
        except sqlite3.Error as e:
            import logging
            logging.error(f"读取配置项 [{key}] 时发生数据库错误: {e}")
            return None

    def write_setting(self, key, value):
        """写入或更新系统配置 (数据层)"""
        try:
            self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            self.conn.commit()
            import logging
            logging.info(f"系统配置 [{key}] 已成功更新底层写入")
        except sqlite3.Error as e:
            import logging
            logging.error(f"写入配置项 [{key}] 时发生数据库错误: {e}")
            self.conn.rollback()

    def close(self):
        """安全关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logging.info("数据库底层连接已安全释放")
