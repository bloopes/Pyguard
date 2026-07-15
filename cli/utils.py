import string
import secrets
import re
import shutil
import datetime
from pygame import mixer
import os
import sys
import time
import random
import logging


# --- 界面美化工具 ---
class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'
    WHITE = '\033[97m'
    UNDERLINE = '\033[4m'
    HEADER = '\033[95m'

def get_display_width(text):
    """计算字符串在终端中的实际显示宽度 (处理 ANSI 和 中文)"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    plain_text = ansi_escape.sub('', text)
    width = 0
    for char in plain_text:
        # 如果是中文字符或中文标点，宽度加 2，否则加 1
        if '\u4e00' <= char <= '\u9fff' or char in '：，。！？【】（）':
            width += 2
        else:
            width += 1
    return width


def pad_to_width(text, target_width):
    """根据显示宽度填充空格"""
    return text + " " * (target_width - get_display_width(text))

def print_menu_frame(options):
    """绘制一个精致的 Unicode 边框菜单"""
    # 这里的 box_width 是指内部可用的总宽度（单元格数）
    box_width = 44

    # 1. 打印顶部边框
    print(f"{Colors.CYAN}╔{'═' * box_width}╗{Colors.ENDC}")

    # 2. 打印菜单项
    for key, desc in options:
        # 构建这一行的原始内容 (左边留一个空格)
        content = f" {Colors.BOLD}{Colors.YELLOW}[{key}]{Colors.ENDC} {desc}"

        # 使用我们的对齐工具补齐右侧空格
        # 这样不管 desc 是中文还是英文，padded_line 的显示宽度永远是 box_width
        padded_line = pad_to_width(content, box_width)

        # 拼接两边的边框并打印
        print(f"{Colors.CYAN}║{Colors.ENDC}{padded_line}{Colors.CYAN}║{Colors.ENDC}")

    # 3. 打印底部边框
    print(f"{Colors.CYAN}╚{'═' * box_width}╝{Colors.ENDC}")
def clear_screen():
    """清屏命令，保持界面整洁"""
    os.system('cls' if os.name =='nt' else 'clear')
def print_banner(text):
    """打印漂亮的标题横幅"""
    width = 50
    print(f"{Colors.BLUE}{'='*width}{Colors.ENDC}")
    print(f"{Colors.BOLD}{text.center(width-10)}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'=' * width}{Colors.ENDC}")

def print_success(message):
    print(f"{Colors.GREEN}✅{message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.RED}❌{message}{Colors.ENDC}")

# --- B. 随机密码生成器 ---
def generate_strong_password(length=16, include_symbols=True):
    characters = string.ascii_letters + string.digits
    if include_symbols:
        characters += "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # --- 修复逻辑 ---
    # 如果长度小于 4，强行要求四种字符共存会导致死循环
    if length < 4:
        return ''.join(secrets.choice(characters) for _ in range(length))

    while True:
        password = ''.join(secrets.choice(characters) for _ in range(length))
        # 只有长度够长时才检查强度
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and (not include_symbols or any(c in string.punctuation for c in password))):
            return password

# --- C. 输入校验 ---
def check_password_strength(password):
    """
    检查密码强度：
    返回（是否合格：bool，建议：str）
    """
    # 1. 长度检查
    if len(password) < 12:
        return False, " 密码长度至少需要12位。"
    # 2. 数字检查
    if not any(c.isdigit() for c in password):
        return False, " 密码必须包含数字。"
    # 3. 大写字母检查
    if not any(c.isupper() for c in password):
        return False, " 密码必须包含大写字母。"
    # 4. 新增：小写字母检查（补全“大小写”要求）
    if not any(c.islower() for c in password):
        return False, " 密码必须包含小写字母。"
    # 5. 新增：标点符号检查
    # string.punctuation 包含了所有的标准特殊字符：!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
    if not any(c in string.punctuation for c in password):
        return False, " 密码必须包含标点符号（特殊字符）。"
    return True, "强度合格"

def suggest_strong_password(length=14):
    """
    随机生成一个符合极高强度要求的示例密码
    """
    # 确保每个分类至少有一个字符
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    punc = random.choice(string.punctuation)
    # 剩余的长度从全集中随机抽取
    all_chars = string.ascii_letters + string.digits + string.punctuation
    remaining = "".join(random.choices(all_chars, k=length - 4))
    # 打乱顺序，防止出现“大写+小写+数字+符号”的固定开头模式
    password_list = list(upper + lower + digit + punc + remaining)
    random.shuffle(password_list)
    return "".join(password_list)

# --D. 备份工具 ---
def backup_database(db_name):
    try:
        # 1. 锁定项目根目录 (cli 的上一级)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 2. 修正：源文件必须在根目录下的 file 文件夹内
        # 这样拼接出来的就是：.../PyGuard-Manager-cli/file/pyguard.db
        full_db_path = os.path.join(base_dir, "file", os.path.basename(db_name))

        # 3. 修正：备份文件夹在根目录下的 file/backup 内
        backup_folder = os.path.join(base_dir, "file", "backup")

        # --- 后续逻辑保持不变 ---
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)

        if not os.path.exists(full_db_path):
            # 这里的报错会显示更清晰的路径，方便你排查
            return False, f"❌ 未找到源数据库文件: {full_db_path}"

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(full_db_path)
        backup_path = os.path.join(backup_folder, f"{filename}.{timestamp}.bak")

        shutil.copy2(full_db_path, backup_path)
        return True, backup_path

    except Exception as e:
        return False, str(e)


def ensure_dirs():
    """确保数据和日志目录存在（使用绝对路径锁死项目根目录）"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_dir = os.path.join(base_dir, "file")
    log_dir = os.path.join(base_dir, "log")
    for target_dir in [file_dir, log_dir]:
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

def silent_purge_vault(ctrl_instance):
    """
    静默销毁逻辑：接收控制器实例以切断连接，然后物理抹除
    """
    try:
        # --- 1. 安全断开数据库连接 ---
        # 通过传进来的 ctrl_instance 访问 db 并关闭
        if hasattr(ctrl_instance, 'db') and ctrl_instance.db:
            try:
                ctrl_instance.db.close()
                ctrl_instance.db = None
            except:
                pass
        # --- 2. 安全断开日志系统 ---
        logging.shutdown()
        # --- 3. 定位路径 ---
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_dir = os.path.join(base_dir, "file")
        log_dir = os.path.join(base_dir, "log")
        # --- 4. 执行物理抹除 ---
        for target in [file_dir, log_dir]:
            if os.path.exists(target):
                shutil.rmtree(target)
                os.makedirs(target)
        return True, " 所有连接已切断，数据库与日志已物理抹除。"
    except Exception as e:
        return False, f"销毁失败: {str(e)}"

def play_audio(file_path):
    """【最终方案】使用 pygame 解决所有 Windows 路径和编码问题"""
    try:
        full_path = os.path.abspath(file_path)
        if not os.path.exists(full_path):
            print(f"{Colors.RED}[!] 找不到音频文件: {full_path}{Colors.ENDC}")
            return False
        mixer.init()
        mixer.music.load(full_path)
        mixer.music.set_volume(0.8)  # 80% 音量，够震撼
        mixer.music.play()
        return True
    except Exception as e:
        print(f"{Colors.RED}[!] 音频系统启动失败: {e}{Colors.ENDC}")
        return False

def stop_audio():
    """清理音频资源"""
    try:
        mixer.music.stop()
        mixer.quit()
    except:
        pass

def dead_man_sequence():
    """DEAD_MAN 协议：90秒极致音画同步"""
    current_file_path = os.path.abspath(__file__)
    cli_dir = os.path.dirname(current_file_path)
    project_root = os.path.dirname(cli_dir)
    audio_path = os.path.join(project_root, "source", "DEAD_MAN.wav")
    if not play_audio(audio_path):
        print(f"{Colors.YELLOW}[!] 警告: 音频系统未就绪，将进入静默处毁模式。{Colors.ENDC}")
        time.sleep(2)

    for i in range(11, 0, -1):
        os.system('cls' if os.name == 'nt' else 'clear')

        # 警报频闪效果：利用奇偶数秒在红、黄之间疯狂切换
        alert_color = Colors.RED if i % 2 != 0 else Colors.YELLOW
        border = f"{alert_color}{'═' * 70}{Colors.ENDC}"

        print(f"\n{border}")
        print(
                f"{alert_color}║{' ' * 12}{Colors.BOLD}⚠  CRITICAL ERROR: DEAD_MAN PROTOCOL ENGAGED  ⚠{' ' * 9}{alert_color}║{Colors.ENDC}")
        print(f"{border}\n")

        print(f"{Colors.RED} [!] 协议已接管系统内核级别 I/O。进入不可逆自毁前置序列。{Colors.ENDC}")
        print(f"{Colors.YELLOW} [!] 任何强制关闭进程 / 断电行为，将立即触发介质物理坏道锁定。{Colors.ENDC}\n")

        print(f"{Colors.CYAN} ┌── [ 核心模块强行接管中 ]{Colors.ENDC}")
        print(f"{Colors.CYAN} │ {Colors.WHITE}外部网络通信: {Colors.RED}SEVERED (已物理切断){Colors.ENDC}")
        print(f"{Colors.CYAN} │ {Colors.WHITE}键盘硬件中断: {Colors.RED}BLOCKED (已阻断捕获){Colors.ENDC}")
        print(f"{Colors.CYAN} │ {Colors.WHITE}磁盘写入权限: {Colors.RED}REVOKED (已强制剥夺){Colors.ENDC}\n")

            # 倒计时强化：带伪随机毫秒数
        ms = random.randint(11, 989) if i > 1 else 0
        countdown_str = f"T - {i - 1}.{ms:03d}s" if i > 1 else "T - 0.000s"

        print(f"{' ' * 18}{Colors.BOLD}{Colors.RED}>>> 最终锁定倒计时 <<<{Colors.ENDC}")
        print(f"{' ' * 22}{Colors.WHITE}{Colors.BOLD}  [ {countdown_str} ]  {Colors.ENDC}\n")

            # 底层瀑布流：底部疯狂刷新的十六进制内存锁死记录
        print(f"{Colors.RED}{'-' * 70}{Colors.ENDC}")
        for _ in range(4):
            addr = f"0x{random.randint(0x10000000, 0xFFFFFFFF):08X}"
            hex_data = " ".join([f"{random.randint(0, 255):02X}" for _ in range(8)])
            print(
                    f"{Colors.RED} [PID: {random.randint(1000, 9999)}] {addr} -> {hex_data} ... {Colors.BOLD}LOCKED{Colors.ENDC}")

        time.sleep(1)

    ops = [
        "FLUSHING_CACHE", "DROPPING_KEYS", "SIG_TERMINATE",
        "OVERWRITING_MBR", "SHREDDING_SECTOR", "PURGING_MEM_BANK",
        "UNMOUNTING_VFS", "DESTROYING_FSTAB", "CORRUPTING_INODES",
        "NULLIFYING_POINTERS", "BYPASSING_RING0"
    ]

    for i in range(90, 60, -1):
        os.system('cls' if os.name == 'nt' else 'clear')

        # 顶部保留进度条
        print(f"\n{Colors.CYAN}[SYSTEM] 正在暴力卸载核心卷...{Colors.ENDC}")
        print(f"{Colors.CYAN}[SYSTEM] 全盘物理块扫描进度... {Colors.RED}{90 - i + 1}%{Colors.ENDC}")
        bar_len = 30
        filled = int((90 - i) / 30 * bar_len)
        bar = '█' * filled + '░' * (bar_len - filled)
        print(f"\n{' ' * 5}PREPARING_ERASE: [{bar}] {Colors.RED}{Colors.BOLD}T-{i}s{Colors.ENDC}\n")

        # 增加单秒内的输出行数（从10行增加到18行），制造刷屏感
        for _ in range(18):
            # 随机事件 1：15% 的概率爆出巨大的红色致命错误
            if random.random() > 0.85:
                print(
                    f"{Colors.RED}{Colors.BOLD}{'!' * 15} FATAL EXCEPTION: SECURE BOOT CORRUPTED {'!' * 15}{Colors.ENDC}")
                print(f"{Colors.YELLOW}{' ' * 5}>> OVERRIDE FORCED. CONTINUING DATA DESTRUCTION...{Colors.ENDC}")

            # 随机事件 2：15% 的概率爆出黄色权限警告
            elif random.random() > 0.85:
                print(f"{Colors.YELLOW}{' ' * 10}[WARNING] UNAUTHORIZED HALT ATTEMPT BLOCKED. PURGING... {Colors.ENDC}")

            # 常规刷屏：带有真实感的 16 进制内存地址和错位排版
            else:
                op = random.choice(ops)
                hex_addr = f"0x{random.randint(0x10000000, 0xFFFFFFFF):08X}"
                hex_val = "".join(random.choices("0123456789ABCDEF", k=8))

                # 随机缩进，制造屏幕正在“故障(Glitch)”的视觉撕裂感
                indent = " " * random.randint(0, 8)
                print(f"{indent}{Colors.WHITE}DEBUG >> {op} [{hex_addr}] -> {hex_val}{Colors.ENDC}")

        time.sleep(1)

    folders = ["/vault/keys/", "/db/config/", "/sys/logs/", "/kernel/auth/", "/dev/urandom/"]

    for i in range(60, 30, -1):
        os.system('cls' if os.name == 'nt' else 'clear')

        # 让百分比随着时间从大概 50% 跌到 0%，加入一点随机波动显得真实
        integrity = max(0, int(((i - 30) / 30) * 45) + random.randint(0, 4))
        print(
            f"\n{Colors.RED}{Colors.BOLD} [!!!] 核心存储穹顶结构完整性: {integrity}% {'↓' * random.randint(1, 4)}{Colors.ENDC}")
        print(f"{Colors.YELLOW} [!] 正在执行深层逻辑粉碎 (INODE TABLES SHREDDING)...{Colors.ENDC}\n")

        # 25% 的概率突然爆出全屏大警告
        if random.random() > 0.75:
            print(f"{Colors.RED}{'=' * 65}{Colors.ENDC}")
            print(f"{Colors.RED}{Colors.BOLD}    ███████╗ █████╗ ██╗██╗     ██╗   ██╗██████╗ ███████╗{Colors.ENDC}")
            print(f"{Colors.RED}{Colors.BOLD}    ██╔════╝██╔══██╗██║██║     ██║   ██║██╔══██╗██╔════╝{Colors.ENDC}")
            print(f"{Colors.RED}{Colors.BOLD}    █████╗  ███████║██║██║     ██║   ██║██████╔╝█████╗  {Colors.ENDC}")
            print(f"{Colors.RED}{Colors.BOLD}    ██╔══╝  ██╔══██║██║██║     ██║   ██║██╔══██╗██╔══╝  {Colors.ENDC}")
            print(f"{Colors.RED}{Colors.BOLD}    ██║     ██║  ██║██║███████╗╚██████╔╝██║  ██║███████╗{Colors.ENDC}")
            print(f"{Colors.RED}{Colors.BOLD}    ╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝{Colors.ENDC}")
            print(f"{Colors.RED}{'=' * 65}{Colors.ENDC}")
            print(f"{Colors.WHITE}{Colors.BOLD}       >> MULTIPLE SECTOR COLLAPSE DETECTED <<{Colors.ENDC}\n")
            loop_count = 6  # 如果砸了大警告，碎文件的日志就少打印几行，留出视觉空间
        else:
            loop_count = 18  # 平静的时候疯狂刷屏粉碎日志

        # 错乱的粉碎日志 (表现数据彻底被撕裂)
        for _ in range(loop_count):
            folder = random.choice(folders)
            file_hex = "".join(random.choices("0123456789ABCDEF", k=8))

            # 60%概率出现正常的粉碎，40%概率出现严重乱码
            if random.random() > 0.6:
                # 生成一段像乱码一样的恶性字符串
                glitch = "".join(random.choices("!@#$%^&*()_+{}|:<>?~", k=random.randint(5, 18)))
                print(f"{Colors.RED} SHREDDING >> {folder}{file_hex}.dat {Colors.WHITE}[{glitch}]{Colors.ENDC}")
            else:
                # 随机缩进，破坏整齐感，就像控制台的排版系统也坏掉了一样
                indent = " " * random.randint(0, 6)
                print(
                    f"{indent}{Colors.RED} SHREDDING >> {folder}{file_hex}.dat {Colors.YELLOW}...[PURGED]{Colors.ENDC}")

        # 底部死亡倒计时
        print(f"\n{' ' * 15}{Colors.BOLD}{Colors.WHITE}距离物理层数据湮灭: {Colors.RED}T - {i}s{Colors.ENDC}")
        time.sleep(1)

    for i in range(30, 5, -1):
        os.system('cls' if os.name == 'nt' else 'clear')

        print(f"\n{Colors.RED}{'█' * 65}{Colors.ENDC}")
        print(f"{Colors.WHITE}{Colors.BOLD}{' ' * 12}POINT OF NO RETURN PASSED / 临界点已突破{Colors.ENDC}")
        print(f"{Colors.RED}{'█' * 65}{Colors.ENDC}\n")

        # 间歇性地显示“取消失败”的系统底层反馈
        if i % 3 == 0 or i % 4 == 0:
            print(
                f"{Colors.CYAN} [KERNEL] 捕获到强行中断信号 (SIGINT/SIGTERM)... {Colors.RED}DENIED (已拒绝){Colors.ENDC}")
            print(f"{Colors.CYAN} [KERNEL] 尝试挂载只读恢复卷... {Colors.RED}FAILED (硬件锁死){Colors.ENDC}\n")
        else:
            print(f"{Colors.YELLOW} [!] 所有物理扇区已被封锁。{Colors.ENDC}")
            print(f"{Colors.YELLOW} [!] 正在执行最终覆写... 任何断电操作将触发硬件级熔断。{Colors.ENDC}\n")

        # 死亡阵列：数据一点点变成 00 (物理消亡的视觉化)
        print(f"{Colors.RED}{'-' * 65}{Colors.ENDC}")
        for _ in range(12):
            addr = f"0x{random.randint(0x00000000, 0x0FFFFFFF):08X}"

            # 随着时间流逝（i越小），数据被清零 (00) 和覆写 (FF) 的概率越来越大
            if i < 18:
                # 已经快删完了，满屏都是 00 和 FF
                hex_data = " ".join(
                    [random.choice(["00", "00", "00", "FF", "FF", f"{random.randint(0, 255):02X}"]) for _ in range(8)])
            else:
                # 刚进这个阶段，数据还在挣扎
                hex_data = " ".join([f"{random.randint(0, 255):02X}" for _ in range(8)])

            # 偶尔闪过一丝惨白的“已覆写”标识
            row_color = Colors.RED if random.random() > 0.15 else Colors.WHITE
            print(f"{row_color} {addr} │ {hex_data} │ {'▓' * 8} [ZEROED]{Colors.ENDC}")
        # 终局静默倒数
        print(
            f"\n{' ' * 16}{Colors.BOLD}{Colors.WHITE}>>> 终极静默倒计时: {Colors.RED} {i}s {Colors.WHITE}<<<{Colors.ENDC}")
        time.sleep(1)
        # 定义巨型数字的像素矩阵 (宽度 10 个字符)
    huge_digits = {
            5: ["██████████", "██╔═══════", "██████████", "╚═══════██", "██████████"],
            4: ["██╗     ██", "██║     ██", "██████████", "╚═══════██", "        ██"],
            3: ["██████████", "╚═══════██", "██████████", "╚═══════██", "██████████"],
            2: ["██████████", "╚═══════██", "██████████", "██╔═══════", "██████████"],
            1: ["        ██", "        ██", "        ██", "        ██", "        ██"]
        }

    for i in range(5, 0, -1):
            # 每一秒内渲染 5 帧，制造高频狂闪和剧烈震动
        for _ in range(5):
            os.system('cls' if os.name == 'nt' else 'clear')

                # 1. 剧烈震动：随机顶部和左侧的留白
            top_margin = "\n" * random.randint(2, 6)
            left_margin = " " * random.randint(10, 25)

                # 2. 警报频闪：红白交替，红色概率更高，模拟刺眼的警报灯
            flash_color = random.choice([Colors.RED, Colors.RED, Colors.WHITE])

            print(top_margin, end="")

                # 3. 渲染巨型警告框 (内宽 36)
            print(f"{flash_color}{left_margin}▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄{Colors.ENDC}")
            print(f"{flash_color}{left_margin}██                                      ██{Colors.ENDC}")
            print(f"{flash_color}{left_margin}██      F I N A L  P U R G E  I N       ██{Colors.ENDC}")
            print(f"{flash_color}{left_margin}██                                      ██{Colors.ENDC}")

                # 逐行渲染巨型数字，两边留白 13 个空格保持绝对居中
            for line in huge_digits[i]:
                print(f"{flash_color}{left_margin}██             {line}             ██{Colors.ENDC}")

            print(f"{flash_color}{left_margin}██                                      ██{Colors.ENDC}")
            print(f"{flash_color}{left_margin}▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀{Colors.ENDC}")

                # 4. 底部随机刷屏乱码，代表系统最后的一点意识正在消散
            glitch = "".join(random.choices("!@#$%^&*()_+{}|:<>?~", k=random.randint(20, 50)))
            print(f"\n{' ' * random.randint(5, 15)}{Colors.RED}{glitch}{Colors.ENDC}")

            time.sleep(0.185)

        # --- [阶段 5：引爆瞬间] ---

    time.sleep(0.8)    # 对齐音频中的爆炸声
    for idx in range(20):
        os.system('cls' if os.name == 'nt' else 'clear')

            # 起爆前几帧产生“白屏闪光弹”和“血红”的交替致盲效果
        if idx in [0, 1, 3]:
            flash_color = Colors.WHITE if idx != 3 else Colors.RED
            print(f"{flash_color}{'█' * (80 * 24)}{Colors.ENDC}")
            time.sleep(0.04)
            continue

            # 数字碎片与冲击波
        frame = "\n" * random.randint(0, 3)  # Y轴屏幕剧烈震动
        for _ in range(21):
                # 随机决定这行的主色调，高潮阶段红色和黄色主导
            line_color = random.choice([Colors.RED, Colors.RED, Colors.YELLOW, Colors.WHITE])

                # 字符权重池：加入大量空白模拟“被炸开”，加入渐变方块模拟“碎片”
            chars = random.choices(
                    ['█', '▓', '▒', '░', 'X', '!', '*', ' ', '0', '1'],
                    weights=[4, 3, 2, 2, 1, 1, 1, 8, 1, 1],  # 空格权重最高
                    k=80
                )

            if random.random() > 0.6:
                shift = random.randint(10, 30)
                chars = [' '] * shift + chars[:-shift]

            frame += f"{line_color}{''.join(chars)}{Colors.ENDC}\n"

        print(frame)
        time.sleep(0.04)

    print(f"\n{Colors.RED}{'═' * 65}{Colors.ENDC}\n")

    final_msg_1 = "A L L   S E C R E T S   R E D U C E D   T O   A S H ."
    sys.stdout.write(f"{' ' * 5}{Colors.RED}{Colors.BOLD}")
    for char in final_msg_1:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.12)
    print(f"{Colors.ENDC}")

    time.sleep(0.5)

    final_msg_2 = "See you again."
    sys.stdout.write(f"{' ' * 22}{Colors.WHITE}")
    for char in final_msg_2:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.08)
    print(f"{Colors.ENDC}\n\n{Colors.RED}{'═' * 65}{Colors.ENDC}")

    for _ in range(4):
        sys.stdout.write(f"\r{' ' * 58}{Colors.RED}█{Colors.ENDC}")
        sys.stdout.flush()
        time.sleep(0.4)
        sys.stdout.write(f"\r{' ' * 58} ")  # 光标消失
        sys.stdout.flush()
        time.sleep(0.4)

    stop_audio()



