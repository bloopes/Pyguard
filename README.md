## 🚀 Quick Start / 快速开始

**[EN]** Run the following command in your terminal to enter the vault. Upon the first run, the system will automatically initialize the local vault structure and prompt you to set a highly secure master password. 

**[ZH]**  在终端运行以下命令进入金库。初次运行，系统会自动初始化本地文件结构并要求设定极强主密码。

Bash

```
python -m cli.interface
```

*(Tips: For Windows users, you can also just double-click the `run.bat` file if configured.)*

------

## 📁 Directory Structure / 目录结构

Plaintext

```
PyGuard-Manager-cli/
├── cli/            # UI Layer (Terminal rendering, effects, DEAD_MAN animations)
├── core/           # Core Layer (CryptoEngine, Logic Controller, Database Manager)
├── source/         # Static Assets (Audio files, Icons)
├── requirements.txt# Dependency list
└── README.md       # Project documentation

# The following directories are generated automatically at runtime:
# 以下目录将在程序运行时安全生成 (需加入 .gitignore):
├── file/           # Encrypted SQLite database & backup snapshots
└── log/            # Security execution logs
```

------

## ⚠️ Disclaimer / 免责声明

**[EN]** 1. This project is a personal cryptography/security practice project. **The codebase has not been formally audited by third-party security agencies.** 2. The developer assumes **NO RESPONSIBILITY** for any password loss or data destruction (especially after triggering the DEAD_MAN protocol). Please keep your master password safe and make regular offline physical backups!

**[ZH]** 1. 本项目为个人安全与密码学实践项目，**代码尚未经过第三方安全机构的正式安全审计**，请勿用于存放涉及身家性命的极端敏感信息。 2. 开发者不对因使用本软件导致的任何密码遗失、数据损毁（尤其是触发 DEAD_MAN 协议后）承担任何法律或连带责任。请务必妥善保管您的主密码，并定期进行异地物理备份！

------

## 📄 License / 许可证

This project is licensed under the **MIT License**. See the `LICENSE` file for details. 本项目采用 **MIT 许可证** 开源。