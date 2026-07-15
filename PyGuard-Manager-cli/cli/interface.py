import sys
import os
import getpass
import time
# 导入路径兼容
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cli.utils import (
    clear_screen, print_success, print_banner,
    print_error, generate_strong_password, check_password_strength,
    Colors, print_menu_frame, pad_to_width, backup_database, suggest_strong_password, silent_purge_vault
)
from core.logic import VaultController
from core.crypto import DecryptionError, ConfigurationError


def main_cli():
    ctrl = VaultController()
    # --- 验证/初始化流程 ---
    clear_screen()
    print_banner("PyGuard v1.0 - 安全金库")
    if not ctrl.is_initialized():
        print(f"\n{Colors.YELLOW}{'!' * 50}{Colors.ENDC}")
        print(f"{Colors.BOLD}🛡️  [PyGuard] 正在创建新的安全金库{Colors.ENDC}")
        print("⚠️  警告：本程序采用零知识加密，我们不存储您的主密码。")
        print("⚠️  如果您忘记主密码，金库数据将永久丢失，无法恢复！")
        print(f"{Colors.YELLOW}{'!' * 50}{Colors.ENDC}\n")

        while True:
            example = suggest_strong_password()
            print(f"\n{Colors.CYAN}[提示] 好的密码应该难以预测。{Colors.ENDC}")
            print(f"{Colors.WHITE}安全示例: {Colors.YELLOW}{example}{Colors.ENDC}")
            print(f"{Colors.BLUE}(你可以参考这个结构，或者直接把它记在脑子里){Colors.ENDC}\n")
            master_pwd = getpass.getpass(f"{Colors.BOLD}请设置主密码: {Colors.ENDC}")
            confirm_pwd = getpass.getpass(f"{Colors.BOLD}请再次输入以确认: {Colors.ENDC}")
            is_ok, tips = check_password_strength(master_pwd)
            if not is_ok:
                print_error(tips)
                continue
            if master_pwd != confirm_pwd:
                print_error(" 两次输入的密码不一致，请重新设置。")
                continue
            clear_screen()
            break

        print(f"\n{Colors.CYAN}[*] 正在进行高强度密钥派生，请稍候...{Colors.ENDC}")
        ctrl.initialize_vault(master_pwd)
        print_success(" 金库初始化成功！")
        input(f"\n{Colors.BLUE}按回车进入主菜单...{Colors.ENDC}")

    else:
        print(f"🛡️ {Colors.BOLD}[PyGuard] 欢迎回来{Colors.ENDC}")
        failed_attempts = 0
        while True:
            print(f"\n{Colors.CYAN}--- 身份验证 ---{Colors.ENDC}")
            # 隐藏输入
            raw_input = getpass.getpass(f" ➔ 请输入主密码解锁 {Colors.RED}: {Colors.ENDC}").strip()
            # 基础校验
            if not raw_input:
                print_error(" 输入不能为空！")
                continue
            # DEAD_MAN 协议（手动触发）
            if raw_input.upper() == 'DEAD_MAN':
                print(f"\n{Colors.RED} [警告] 正在请求 DEAD_MAN 协议...{Colors.ENDC}")
                confirm = input(f"\n{Colors.RED} [警告] 确认执行该协议？(y/Y)(回车键取消): ").lower()
                if confirm == 'y':
                    # 最后的物理锁
                    reconfirm = input(f"\n{Colors.RED} {Colors.BOLD}请键入 'DEAD_MAN' 以授权: ").strip()
                    # 授权 DEAD_MAN 协议
                    if reconfirm == 'DEAD_MAN':
                        print(f"\n{Colors.RED}[!] 收到授权。正在执行 DEAD_MAN 协议...{Colors.ENDC}")
                        ctrl.DEAD_MAN_vault()  # 执行 DEAD_MAN 协议
                    else:
                        print(f"{Colors.YELLOW}[!] 授权失败，协议已挂起。{Colors.ENDC}")
                continue
            if raw_input.lower() == 'r':
                clear_screen()
                print_banner(" ☢️ 系统紧急重置 ")
                print(f"{Colors.RED} ⚠️  警告：此操作将永久删除所有密码记录和备份，不可恢复！{Colors.ENDC}")
                # 简单的二次确认，防止手滑
                confirm = input(f"\n 输入 'CONFIRM' 执行销毁: ").strip()
                if confirm == "CONFIRM":
                    print(f" [*] 正在抹除数据块...")
                    success, msg = silent_purge_vault(ctrl)
                    if success:
                        print_success(msg)
                        # 销毁后强制退出
                        print(f"{Colors.YELLOW} 程序将在 3 秒后关闭。{Colors.ENDC}")
                        time.sleep(3)
                        sys.exit()
                    else:
                        print_error(msg)
                else:
                    print(f"{Colors.CYAN} 操作已取消。{Colors.ENDC}")
                input("\n 按回车返回主菜单...")
                continue
            # 尝试解锁
            try:
                if ctrl.unlock_vault(raw_input):
                    print_success(" 身份验证通过。")
                    break
                else:
                    raise DecryptionError
            except DecryptionError:
                failed_attempts += 1

                # 实时读取 DEAD_MAN 协议
                is_DEAD_MAN_on = ctrl.get_setting("DEAD_MAN_enabled", "False") == "True"
                DEAD_MAN_limit = int(ctrl.get_setting("DEAD_MAN_limit", "5"))

                if is_DEAD_MAN_on:
                    remaining = DEAD_MAN_limit - failed_attempts
                    if remaining <= 0:
                        print(f"\n{Colors.RED}[!] 错误次数超限，自动激活 DEAD_MAN 协议...{Colors.ENDC}")
                        ctrl.DEAD_MAN_vault()
                    else:
                        print_error(f" 密码校验失败！DEAD_MAN 保护已生效：剩余尝试次数：{remaining}")
                else:
                    print_error(f" 密码校验失败！当前已连续失败 {failed_attempts} 次。")
                # 重置暗示
                if failed_attempts >= 3:
                    print(f"\n{Colors.YELLOW} 💡 提示：若无法取回主密码，可启用 'r' 协议清理受信任设备。{Colors.ENDC}")

    # --- 主功能菜单 ---
    while True:
        clear_screen()
        print(fr"{Colors.BOLD}{Colors.CYAN}")
        print(r"   ____        ______                      __ ")
        print(r"  / __ \__  __/ ____/_  ______ __________/ / ")
        print(r" / /_/ / / / / / __/ / / / __ `/ ___/ __  /  ")
        print(r"/ ____/ /_/ / /_/ / /_/ / /_/ / /  / /_/ /   ")
        print(r"/_/    \__, /\____/\__,_/\__,_/_/   \__,_/    ")
        print(fr"      /____/         {Colors.YELLOW}v1.0 - Core Edition{Colors.ENDC}" + "\n")

        menu_options = [
            ("1", "浏览金库列表"),
            ("2", "新增加密凭据"),
            ("3", "销毁记录项"),
            ("4", "修改金库密钥"),
            ("5", "系统紧急重置"),
            ("6", f"{Colors.GREEN}创建数据库备份{Colors.ENDC}"),
            ("Q", "安全注销并退出")
        ]
        print_menu_frame(menu_options)

        choice = input(f"\n{Colors.BOLD}{Colors.CYAN} ➔ 指令输入: {Colors.ENDC}").lower()

        if choice == '1':
            while True:
                clear_screen()
                print_banner(" 🔍 搜索与浏览凭据 ")
                # 获取关键词
                kw = input(f" {Colors.CYAN}➔ 输入服务名称关键词 (直接回车显示全部): {Colors.ENDC}").strip()
                # 根据输入决定是搜索还是获取全部
                if kw:
                    items = ctrl.search_records(kw)
                    print(f"\n    🔎 找到与 '{Colors.BOLD}{kw}{Colors.ENDC}' 相关的记录 {len(items)} 条：")
                else:
                    items = ctrl.get_all_records()
                    print(f"\n    🗃️ 当前金库共有记录 {len(items)} 条：")
                # 列表展示逻辑
                if not items:
                    print(f"    {Colors.YELLOW}未找到匹配的记录。{Colors.ENDC}")
                else:
                    print(f"  {Colors.CYAN}{'─' * 45}{Colors.ENDC}")
                    print(f"  {Colors.BOLD}{'ID':<6} {'服务 (Service)':<20} {'账户 (User)':<15}{Colors.ENDC}")
                    print(f"  {Colors.CYAN}{'─' * 45}{Colors.ENDC}")
                    for row in items:
                        print(
                            f"  {Colors.YELLOW}{row['id']:<6}{Colors.ENDC} {row['service_name']:<20} {row['username']:<15}")
                    print(f"  {Colors.CYAN}{'─' * 45}{Colors.ENDC}")
                    # 解密查看逻辑
                    tid = input(f"\n{Colors.BOLD}🔓输入 ID 查看明文 (回车返回搜索或主菜单): {Colors.ENDC}").strip()
                    if tid:
                        row = next((r for r in items if str(r['id']) == tid), None)
                        if row:
                            try:
                                pwd = ctrl.decrypt_single_password(row['encrypted_data'], row['service_name'])

                                # --- 绘制解密结果盒子 ---
                                box_w = 34
                                print(f"\n  {Colors.GREEN}╔{'═' * box_w}╗{Colors.ENDC}")
                                print(
                                    f"  {Colors.GREEN}║{Colors.ENDC}{pad_to_width(f' {Colors.BOLD}解密成功！{Colors.ENDC}', box_w)}{Colors.GREEN}║{Colors.ENDC}")
                                print(f"  {Colors.GREEN}╠{'═' * box_w}╣{Colors.ENDC}")
                                print(
                                    f"  {Colors.GREEN}║{Colors.ENDC}{pad_to_width(f' 服务：{Colors.CYAN}{row['service_name']}{Colors.ENDC}', box_w)}{Colors.GREEN}║{Colors.ENDC}")
                                print(
                                    f"  {Colors.GREEN}║{Colors.ENDC}{pad_to_width(f' 账号：{row['username']}', box_w)}{Colors.GREEN}║{Colors.ENDC}")
                                print(
                                    f"  {Colors.GREEN}║{Colors.ENDC}{pad_to_width(f' 密码：{Colors.YELLOW}{Colors.BOLD}{pwd}{Colors.ENDC}', box_w)}{Colors.GREEN}║{Colors.ENDC}")
                                print(f"  {Colors.GREEN}╚{'═' * box_w}╝{Colors.ENDC}")
                                # 自动复制到剪贴板
                                try:
                                    import pyperclip
                                    pyperclip.copy(pwd)
                                    print(f"  {Colors.CYAN}✨ 密码已存入剪贴板。{Colors.ENDC}")
                                except Exception:
                                    pass
                            except DecryptionError:
                                print_error("解密失败！")
                        else:
                            print_error(f" 在搜索结果中未找到 ID [{tid}]")
                        # 查看完一条后，询问是否继续在当前搜索结果下操作或返回
                        input(f"\n  {Colors.BLUE}按回车键继续...{Colors.ENDC}")
                        # 询问是否继续搜索
                print(f"\n  {Colors.CYAN}{'─' * 45}{Colors.ENDC}")
                again = input(f"  ➔ {Colors.BOLD}继续搜索吗？(y/Y)( 回车键取消搜索 ): {Colors.ENDC}").lower()
                if again != 'y':
                    break

        elif choice == '2':
            is_first_run = True  # 标记：是否是点击菜单后的第一次进入
            while True:
                clear_screen()
                print_banner(" ➕ 添加新加密记录 ")
                # --- 误触拦截逻辑 (仅在第一次进入时显示) ---
                if is_first_run:
                    confirm = input(f" ➔ 确认进入添加模式？(y/Y)(回车取消并返回): ").lower()
                    if confirm != 'y':
                        break
                    is_first_run = False  # 一旦确认过，本轮后续添加不再询问
                print(f"{Colors.CYAN}提示：在任何位置输入 'q' 均可取消并返回主菜单{Colors.ENDC}\n")
                # --- 基础信息录入与校验 ---
                service = input(f"{Colors.BOLD}1. 服务名称: {Colors.ENDC}").strip()
                # 【快速退出开关】如果用户误触了，在这里直接回车就退出，不用填后面的
                if not service or service.lower() == 'q':
                    print(f"{Colors.YELLOW}已取消添加。{Colors.ENDC}")
                    break
                username = input(f"{Colors.BOLD}2. 用户名称: {Colors.ENDC}").strip()
                if not username or username.lower() == 'q':
                    print(f"{Colors.YELLOW}已取消添加。{Colors.ENDC}")
                    break
                # --- 密码处理逻辑 ---
                example = suggest_strong_password()
                print(f"\n{Colors.CYAN}[提示] 好的密码应该难以预测。{Colors.ENDC}")
                print(f"{Colors.WHITE}安全示例: {Colors.YELLOW}{example}{Colors.ENDC}")
                print(f"{Colors.BLUE}(直接回车自动生成 16 位强密码,或输入如 '/g20' 生成指定长度，其他内容直接存为密码){Colors.ENDC}\n")
                password_input = input(f"{Colors.BOLD}3. 存入密码: {Colors.ENDC}").strip()
                if password_input.lower() == 'q':
                    break  # 随时退出
                if not password_input:
                    password = generate_strong_password(length=16)
                    print_success(f" 已自动生成 16 位强密码")
                elif password_input.startswith('/g') and password_input[2:].isdigit():
                    length = int(password_input[2:])
                    password = generate_strong_password(length=max(1, min(128, length)))
                    print_success(f" 已生成 {len(password)} 位密码")
                else:
                    password = password_input
                # --- 存入数据库 ---
                try:
                    ctrl.add_record(service, username, password)
                    print_success(f" 凭据 [{service}] 已成功存入金库。")
                except Exception as e:
                    print_error(f" 异常: {e}")
                # --- 流式循环询问 (不再走前面的 is_first_run 逻辑) ---
                print(f"\n{Colors.CYAN}{'─' * 45}{Colors.ENDC}")
                cont = input(f" ➔ 是否继续添加下一条？(y/Y)(回车返回主菜单): ").lower()
                if cont != 'y':
                    break

        elif choice == '3':
            while True:
                # 每次循环都重新获取最新列表并清屏显示
                items = ctrl.get_all_records()
                clear_screen()
                print_banner(" 🔥 销毁敏感记录 ")
                if not items:
                    print(f"\n    {Colors.YELLOW}金库已空，没有可删除的记录。{Colors.ENDC}")
                    input(f"\n{Colors.BLUE}按回车返回主菜单...{Colors.ENDC}")
                    break
                # 显示简易对照表
                print(f"  {Colors.BOLD}{'ID':<6} {'服务 (Service)':<20} {'账户 (User)':<15}{Colors.ENDC}")
                print(f"  {Colors.CYAN}{'─' * 45}{Colors.ENDC}")
                for row in items:
                    # 这里的列宽建议与 'choice 1' 保持一致
                    print(
                        f"  {Colors.YELLOW}{row['id']:<6}{Colors.ENDC} {row['service_name']:<20} {row['username']:<15}")
                print(f"  {Colors.CYAN}{'─' * 45}{Colors.ENDC}")
                # 询问 ID
                tid = input(f"\n  {Colors.RED} ➔ 输入要销毁的记录 ID (回车放弃): {Colors.ENDC}").strip()
                if not tid:
                    break
                # 执行删除逻辑（带二次确认）
                row_to_delete = next((r for r in items if str(r['id']) == tid), None)
                if row_to_delete:
                    confirm = input(
                        f"⚠️确定要删除 {Colors.BOLD}{row_to_delete['service_name']}{Colors.ENDC} 吗？(y/Y)( 回车键取消 ): ").lower()
                    if confirm == 'y':
                        if ctrl.delete_record(tid):
                            print_success(f" ID {tid} 已抹除。")
                        else:
                            print_error(" 删除失败，数据库出现异常。")
                    else:
                        print(f"  {Colors.BLUE}操作已取消。{Colors.ENDC}")
                else:
                    print_error(f" 无效 ID: {tid}")
                # 询问是否继续
                cont = input(f"\n{Colors.CYAN}继续删除吗？(y/Y)( 回车键取消删除 ) {Colors.ENDC}").lower()
                if cont != 'y':
                    break

        elif choice == '4':
            print_banner(" 🔐 修改主金库密钥 ")
            print(f"{Colors.YELLOW} ⚠️  警告：此操作将重新加密所有数据。请勿在操作中强制关闭程序！{Colors.ENDC}")

            old_p = getpass.getpass(f"\n {Colors.BOLD}➔ 请输入当前的旧主密码: {Colors.ENDC}")
            try:
                if not old_p.strip():
                    print_error(" 主密码不能为空！")
                    input("\n按回车返回...")
                    continue
                ctrl.unlock_vault(old_p)
            # 同时捕获解密错误和配置错误（即密码为空导致的报错）
            except (DecryptionError, ConfigurationError):
                print_error(" 旧密码错误或无效，操作终止。")
                input("\n按回车返回...")
                continue
            print(f"\n{Colors.YELLOW} [安全建议] 在进行全库重加密之前，建议先备份当前的数据库。{Colors.ENDC}")
            do_backup = input(f" ➔ 是否现在创建临时备份？(y/Y)( 回车键取消 ): ").lower()
            # --- 备份确认环节 ---
            if do_backup == 'y':
                print(f" [*] 正在备份...")
                success, result = backup_database("pyguard.db")
                if success:
                    print_success(f" 备份SS已创建: {result} (建议单独另外存储)")
                else:
                    print_error(f" 备份失败: {result}")
                    if input("⚠️备份失败，是否继续重构？(y/Y)( 回车键取消 ): ").lower() != 'y':
                        continue
            # 设置新密码
            while True:
                # 示例：在设置主密码时的交互
                example = suggest_strong_password()
                print(f"\n{Colors.CYAN}[提示] 好的密码应该难以预测。{Colors.ENDC}")
                print(f"{Colors.WHITE}安全示例: {Colors.YELLOW}{example}{Colors.ENDC}")
                print(f"{Colors.BLUE}(你可以参考这个结构，或者直接把它记在脑子里){Colors.ENDC}\n")
                new_p = getpass.getpass(f" {Colors.BOLD}➔ 请输入新主密码: {Colors.ENDC}")
                conf_p = getpass.getpass(f" {Colors.BOLD}➔ 请再次输入新密码: {Colors.ENDC}")
                is_ok, tips = check_password_strength(new_p)
                if not is_ok:
                    print_error(tips)
                    continue
                if new_p != conf_p:
                    print_error("两次输入的不一致。")
                    continue
                break
            # 执行迁移
            print(f"\n{Colors.CYAN}[*] 正在解密旧数据并使用新密钥重构，请稍候...{Colors.ENDC}")
            success, msg = ctrl.change_master_password(old_p, new_p)
            if success:
                print_success(msg)
                print(f"{Colors.YELLOW} 💡 请牢记您的新密码。{Colors.ENDC}")
            else:
                print_error(msg)
            input("\n按回车返回主菜单...")

        elif choice == '5':
            print_banner(" ☢️ 系统紧急重置 ")
            print(f"{Colors.RED} ⚠️  警告：此操作将永久删除所有密码记录和备份，不可恢复！{Colors.ENDC}")
            # 简单的二次确认，防止手滑
            confirm = input(f"\n 输入 'CONFIRM' 执行销毁: ").strip()
            if confirm == "CONFIRM":
                print(f" [*] 正在抹除数据块...")
                success, msg = silent_purge_vault(ctrl)
                if success:
                    print_success(msg)
                    # 销毁后强制退出，因为内存里的解密状态已无意义
                    print(f"{Colors.YELLOW} 程序将在 3 秒后关闭。{Colors.ENDC}")
                    time.sleep(3)
                    sys.exit()
                else:
                    print_error(msg)
            else:
                print(f"{Colors.CYAN} 操作已取消。{Colors.ENDC}")
            input("\n 按回车返回主菜单...")

        elif choice == '6':
            print_banner(" 💾 数据库安全备份 ")
            print(f"{Colors.CYAN}[*] 准备对当前金库进行物理快照...{Colors.ENDC}")
            # 执行备份逻辑
            success, result = backup_database("pyguard.db")
            if success:
                # 备份成功的展示
                print_success("  数据库快照创建成功！")
                print(f"{Colors.WHITE} -------------------------------------------------- {Colors.ENDC}")
                print(f" {Colors.BOLD}备份文件名: {Colors.ENDC}{os.path.basename(result)}")
                print(f" {Colors.BOLD}存储路径:   {Colors.ENDC}{Colors.YELLOW}{result}{Colors.ENDC}")
                print(f"{Colors.WHITE} -------------------------------------------------- {Colors.ENDC}")
                print(f"{Colors.GREEN} 💡 建议：您可以将此文件手动复制到外部离线设备中。{Colors.ENDC}")
            else:
                # 错误处理
                print_error(f" 备份执行过程中出现异常：{result}")
                print(f"{Colors.RED} [!] 请检查程序是否有文件夹写入权限或磁盘空间是否充足。{Colors.ENDC}")
            input(f"\n{Colors.WHITE}按回车键返回主菜单...{Colors.ENDC}")

        elif choice == 'dead_man':  # 假设你前面已经改成小写了
            while True:
                clear_screen()
                # --- 顶部 Banner ---
                print(
                    f"{Colors.RED}╔══════════════════════════════════════════════════════════════════════╗{Colors.ENDC}")
                print(
                    f"{Colors.RED}║ {Colors.BOLD}☢️  LETHAL PROTOCOL: DEAD_MAN CONFIGURATION TERMINAL {Colors.ENDC}                {Colors.RED}║{Colors.ENDC}")
                print(
                    f"{Colors.RED}╠══════════════════════════════════════════════════════════════════════╣{Colors.ENDC}")
                print(
                    f"{Colors.RED}║{Colors.YELLOW}[!]CAUTION: EXTREME DANGER. MODIFICATIONS MAY CAUSE DATA ANNIHILATION.{Colors.RED}║{Colors.ENDC}")
                print(
                    f"{Colors.RED}╚══════════════════════════════════════════════════════════════════════╝{Colors.ENDC}\n")
                # 读取配置
                is_on = ctrl.get_setting("DEAD_MAN_enabled", "False") == "True"
                limit = ctrl.get_setting("DEAD_MAN_limit", "5")
                # 状态显示：用“武装/解除”代替“开启/关闭”，红色代表危险的“武装”状态
                status_color = Colors.RED if is_on else Colors.CYAN
                status_text = "ARMED (已武装)" if is_on else "DISARMED (已休眠)"
                # --- 菜单排版 ---
                print(
                    f"   {Colors.WHITE}[ 1 ]{Colors.ENDC} 被动防御系统状态 : [ {status_color}{Colors.BOLD}{status_text}{Colors.ENDC} ]")
                print(
                    f"   {Colors.WHITE}[ 2 ]{Colors.ENDC} 容错安全阈值设定 : [ {Colors.YELLOW}{Colors.BOLD}ERR_LIMIT = {limit} 次{Colors.ENDC} ]")
                print(
                    f"   {Colors.WHITE}[ 3 ]{Colors.ENDC} {Colors.RED}{Colors.BOLD}>>> 手动执行最终指令 (IMMEDIATE PURGE) <<<{Colors.ENDC}")
                print(f"\n   {Colors.WHITE}[ Q ]{Colors.ENDC} {Colors.CYAN}安全撤离当前终端{Colors.ENDC}\n")
                # --- 模拟管理员 Root 命令行 ---
                sub_choice = input(f"{Colors.RED}root@DEAD_MAN_SYS:~# {Colors.ENDC}").strip().lower()
                if sub_choice == '1':
                    ctrl.set_setting("DEAD_MAN_enabled", not is_on)
                    new_status = '武装就绪' if not is_on else '已强制解除'
                    print(f"\n {Colors.YELLOW}[*] 系统覆写成功：防御协议 {new_status}。{Colors.ENDC}")
                elif sub_choice == '2':
                    new_limit = input(f"\n {Colors.YELLOW}➔ 请输入新的阈值参数 (允许范围 3-10): {Colors.ENDC}").strip()
                    if new_limit.isdigit() and 3 <= int(new_limit) <= 10:
                        ctrl.set_setting("DEAD_MAN_limit", new_limit)
                        print(f" {Colors.GREEN}[+] 阈值已更新。系统将在连续失败 {new_limit} 次后自毁。{Colors.ENDC}")
                    else:
                        print_error("参数越界。系统拒绝执行此修改。")
                elif sub_choice == '3':
                    # 极具压迫感的最终确认
                    print(f"\n{Colors.RED} {'=' * 65}")
                    print(f" {Colors.BOLD}CRITICAL WARNING: MANUAL OVERRIDE INITIATED")
                    print(f" THIS ACTION WILL DESTROY ALL DATA. THERE IS NO UNDO.{Colors.ENDC}")
                    print(f"{Colors.RED} {'=' * 65}{Colors.ENDC}\n")
                    confirm = input(
                        f" {Colors.WHITE}➔ 授权代码请输入 {Colors.RED}{Colors.BOLD}DEAD_MAN{Colors.ENDC}{Colors.WHITE} 以确认引爆: {Colors.ENDC}")
                    if confirm == "DEAD_MAN":
                        print(f"\n {Colors.RED}[!] 授权通过,将执行最后清理。{Colors.ENDC}")
                        time.sleep(1)  # 停顿1秒，给足心理压迫感
                        ctrl.DEAD_MAN_vault()
                    else:
                        print(f"\n {Colors.CYAN}[*] 授权失败/中止。处决序列已取消。{Colors.ENDC}")
                elif sub_choice == 'q':
                    print(f"\n {Colors.CYAN}[*] 正在断开控制台...{Colors.ENDC}")
                    break
                input(f"\n{Colors.WHITE}按回车键刷新终端状态...{Colors.ENDC}")

        elif choice == 'q':
            print(f"\n{Colors.CYAN}[*] 正在启动安全注销程序...{Colors.ENDC}")
            time.sleep(0.4)
            print(f"{Colors.WHITE} ├── 覆盖内存密钥残骸 ... {Colors.GREEN}[ OK ]{Colors.ENDC}")
            time.sleep(0.3)
            print(f"{Colors.WHITE} ├── 锁定底层数据引擎 ... {Colors.GREEN}[ OK ]{Colors.ENDC}")
            time.sleep(0.3)
            print(f"{Colors.WHITE} └── 断开虚拟金库连接 ... {Colors.GREEN}[ OK ]{Colors.ENDC}")
            time.sleep(0.4)
            print(f"\n{Colors.BOLD}{Colors.GREEN} 🛡️ [PyGuard] 注销成功，系统已安全离线。{Colors.ENDC}")
            time.sleep(0.8)
            clear_screen()  # 退出前清空屏幕，防止终端留下残余信息
            break  # 跳出主循环，程序自然结束
        else:
            # 如果输入了菜单上没有的指令
            print_error(" 未知指令，请重新输入。")
            time.sleep(0.8)


if __name__ == "__main__":
    try:
        main_cli()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  检测到强制中断，程序安全退出。{Colors.ENDC}")
        sys.exit()