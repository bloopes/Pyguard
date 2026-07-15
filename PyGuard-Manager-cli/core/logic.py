import os
import sys
from core.crypto import CryptoEngine
from core.database import DatabaseManager

class VaultController:
    def __init__(self):
        self.db =DatabaseManager()
        self.engine = None

    def get_setting(self, key, default):
        """获取系统配置 (业务层)"""
        val = self.db.read_setting(key)
        return val if val is not None else default

    def set_setting(self, key, value):
        """修改系统配置 (业务层)"""
        self.db.write_setting(key, value)

    def search_records(self, keyword):
        """根据服务名称进行模糊搜索 (业务层)"""
        # 转换为字典列表，直接调用底层封装好的接口
        rows = self.db.search_credentials(keyword)
        return [
            {
                'id': row['id'],
                'service_name': row['service_name'],
                'username': row['username'],
                'encrypted_data': row['encrypted_data']
            } for row in rows
        ]

    def is_initialized(self):
        """
        检查金丝雀表是否有数据，这是判定初始化的唯一真理
        """
        try:
            self.db.cursor.execute("SELECT COUNT(*) FROM canary")
            row = self.db.cursor.fetchone()
            return row and row[0] > 0
        except Exception:
            # 如果连表都没创建或报错，说明绝对没初始化
            return False

    def initialize_vault(self,master_password):
        """核心初始化逻辑"""
        salt = os.urandom(16)
        # 派生密钥
        temp_engine =CryptoEngine(master_password,salt)
        # 生成验证金丝雀
        canary_blob = temp_engine.encrypt("VERIFY_OK","SYSTEM_CANARY")
        # 写入数据库
        self.db.initialize_vault(salt,canary_blob)
        # 初始化完成后自动保持登录状态
        self.engine = temp_engine
        return True

    def unlock_vault(self,master_password):
        """验证主密码并建立会话"""
        salt = self.db.get_user_salt()
        canary_blob = self.db.get_canary()
        # 尝试重建引擎
        new_engine =CryptoEngine(master_password,salt)
        #验证金丝雀密文
        new_engine.decrypt(canary_blob,"SYSTEM_CANARY")
        #验证通过，保存引擎
        self.engine = new_engine
        return True

    def add_record(self,service,username,password):
        """加密并存储新密码"""
        if not self.engine:raise Exception("金库未解锁")
        encrypted_blob =self.engine.encrypt(password,service)
        self.db.save_password(service,username,encrypted_blob)

    def get_all_records(self):
        """获取所有记录"""
        return self.db.get_all_credentials()

    def decrypt_single_password(self,encrypted_data,service_name):
        """解密单条记录内容"""
        if not self.engine:raise Exception("金库未解锁")
        return self.engine.decrypt(encrypted_data,service_name)

    def delete_record(self,entry_id):
        """删除指定ID记录"""
        return self.db.delete_credential(entry_id)

    def DEAD_MAN_vault(self):
        """【核心自爆】彻底抹除数据库文件并强制退出"""
        # 注意：从 utils 中导入你的动画和终极物理销毁函数
        from cli.utils import clear_screen, dead_man_sequence, silent_purge_vault
        clear_screen()
        dead_man_sequence()
        silent_purge_vault(self)
        sys.exit()

    def change_master_password(self, old_pwd, new_pwd):
        """
        修改主密码：全库重构逻辑
        """
        # 再次验证旧密码
        if not self.unlock_vault(old_pwd):
            return False, "旧密码验证失败"
        try:
            # 获取所有原始数据
            all_records = self.get_all_records()
            decrypted_list = []
            # 尝试解密所有记录到内存
            for row in all_records:
                plaintext = self.decrypt_single_password(row['encrypted_data'], row['service_name'])
                decrypted_list.append({
                    'id': row['id'],
                    'service_name': row['service_name'],
                    'username': row['username'],
                    'password': plaintext
                })
            # 初始化新密码（生成新盐值、新哈希）
            # 更新 self.crypto 里的密钥
            self.initialize_vault(new_pwd)
            #  重新加密并更新数据库
            for item in decrypted_list:
                # 重新加密
                new_encrypted = self.engine.encrypt(item['password'], item['service_name'])
                # 更新数据库对应行
                query = "UPDATE vault SET encrypted_data = ? WHERE id = ?"
                self.db.conn.execute(query, (new_encrypted, item['id']))

            self.db.conn.commit()
            return True, "主密码修改成功，全库已重新加密"

        except Exception as e:
            # 生产环境建议这里增加更细致的错误处理
            return False, f"迁移过程中出现错误: {str(e)}"






