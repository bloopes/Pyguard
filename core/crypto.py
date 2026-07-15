class CryptoError(Exception):
    """加密模块基础异常"""
    pass
class ConfigurationError(CryptoError):
    """配置参数错误（如内存不足，参数越界）"""
    pass
class DecryptionError(CryptoError):
    """解密失败（可能是密码错，AAD不匹配或者数据损坏）"""
    pass

import os
import base64
import binascii
# 引入 Argon2 底层接口
from argon2.low_level import hash_secret_raw, Type
from argon2.exceptions import Argon2Error
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
# 配置基本的日志，记录安全事件
import logging
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_dir = os.path.join(base_dir, "log")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_path = os.path.join(log_dir, "pyguard.log")
logging.basicConfig(
    filename=log_path,  #  指向 log/pyguard.log
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CryptoEngine:
    def __init__(self, master_password: str, salt: bytes,
                 memory_cost: int = 65536,
                 time_cost: int = 3,
                 parallelism: int = 4):
        """
        初始化加密引擎 (使用 Argon2id)
        :param master_password: 用户输入的主密码
        :param salt: 随机盐值 (至少16字节)
        :param memory_cost: 内存成本 (KiB)，65536 即 64MB
        :param time_cost: 时间成本 (迭代次数)
        :param parallelism: 并行度 (线程数)
        """
        if not master_password:
            raise ConfigurationError("主密码不能为空")
        if len(salt) < 16:
            raise ConfigurationError("为了安全，请保证盐值(salt)至少为16字节")
        try:
        # 使用 Argon2id 派生密钥
            self.key = hash_secret_raw(
                secret=master_password.encode(),
                salt=salt,
                time_cost=time_cost,
                memory_cost=memory_cost,
                parallelism=parallelism,
                hash_len=32,  # AES-256 需要 32 字节密钥
                type=Type.ID  # 明确指定 Argon2id 变体
            )
        # 初始化 AES-GCM 工具箱
            self.aes_gcm = AESGCM(self.key)
            logging.info("加密引擎初始化成功")
        except Argon2Error as e:
            logging.error(f"密钥派生失败：{str(e)}")
            raise ConfigurationError(f"Argon2 参数无效：{e}")


    def encrypt(self,plaintext:str,associated_data:str) -> str:
        """
        加密字符串并绑定关联数据
        :param plaintext:原文本
        :param associated_data:关联数据（如服务名），用于防止密文替换攻击
        :return:
        """
        # 空内容校验，可以删掉进一步增加安全性，但是数据数据管理可能会更冗余
        if not plaintext:
            return ""
        try:
            # 生成12字节的随机Nonce
            nonce=os.urandom(12)
            # 执行加密
            ad=associated_data.encode()
            ciphertext=self.aes_gcm.encrypt(nonce, plaintext.encode(),ad)
            # 将nonce和密文拼接，并转为base64方便存入SQLite
            return base64.b64encode(nonce+ciphertext).decode('utf-8')
        except Exception:
            logging.error("加密过程中发生未知错误")
            raise CryptoError("加密失败")

    def decrypt(self,encrypted_base64:str,associated_data:str) -> str:
        """解密字符串并验证关联数据"""
        # 空内容校验，可以删掉进一步增加安全性，但是数据数据管理可能会更冗余
        if not encrypted_base64:
            return ""
        try:
            try:
            #1. base64解码检查
                data = base64.b64decode(encrypted_base64)
            except(binascii.Error,TypeError):
                raise DecryptionError("无效的base64编码格式")
            #2. 数据长度检查(Nonce 12字节 + Tag 16字节 =至少28字节)
            if len(data)<28:
                raise DecryptionError("密文长度异常，数据可能已损坏")
            # 拆分nonce和密文
            nonce=data[:12]
            ciphertext=data[12:]
            #3. 打上标签并执行解密
            ad = associated_data.encode()
            decrypted_data =self.aes_gcm.decrypt(nonce,ciphertext,ad)
            return decrypted_data.decode('utf-8')
        except InvalidTag:
            # 这里的日志只记录尝试失败并返回当前AAD，不记录任何其他数据
            logging.warning(f"解密认证失败：AAD='{associated_data}'")
            raise DecryptionError("认证失败：密码错误或者数据上下文不匹配")
        except Exception as e:
            if isinstance(e,DecryptionError):
                raise
            logging.error(f"非预期的解密错误：{type(e).__name__} - {str(e)}")
            raise DecryptionError("解密过程发生未知异常")