#!/usr/bin/env python3
import hashlib
import json
import os
import re
import sys
import tty
import termios
import fcntl
import textwrap
import time
import platform

# 获取当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 小说目录和进度目录都相对于脚本位置
DEFAULT_NOVEL_DIR = os.path.join(SCRIPT_DIR, "text")
PROGRESS_DIR = os.path.join(SCRIPT_DIR, "nvpgs")

# 创建必要的目录（如果不存在）
os.makedirs(DEFAULT_NOVEL_DIR, exist_ok=True)
os.makedirs(PROGRESS_DIR, exist_ok=True)

# 安全退出函数
def safe_exit():
    sys.stdout.write('\x1b[2K\r')
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    try:
        old_settings = termios.tcgetattr(fd)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except:
        pass

    sys.exit(0)

# 获取唯一进度文件名，并指定保存到 nvpgs 目录
def get_progress_file(book_path):
    book_path = os.path.abspath(book_path)
    m = hashlib.md5()
    m.update(book_path.encode('utf-8'))
    return os.path.join(PROGRESS_DIR, f".novel_progress_{m.hexdigest()}")


# 保存阅读进度
def save_progress(book_path, page):
    progress_file = get_progress_file(book_path)
    progress_data = {
        "file": book_path,
        "page": page
    }
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress_data, f)


# 加载阅读进度
def load_progress(book_path):
    progress_file = get_progress_file(book_path)
    if not os.path.exists(progress_file):
        return None
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get("file") == book_path:
            return data["page"]
        else:
            return None
    except Exception:
        return None


# 列出小说文件（基于相对路径的 text 目录）
def list_novel_files(novel_dir):
    if not os.path.isdir(novel_dir):
        print(f"错误：目录不存在 {novel_dir}")
        sys.exit(1)
    files = [f for f in os.listdir(novel_dir) if f.endswith(".txt")]
    return sorted(files)


# 查找关键词所在页
def find_best_page(pages, keyword, last_page):
    matches_after_last = [i for i in range(last_page, len(pages)) if keyword.lower() in pages[i].lower()]
    if matches_after_last:
        return matches_after_last[0]

    matches_from_start = [i for i in range(len(pages)) if keyword.lower() in pages[i].lower()]
    if matches_from_start:
        return matches_from_start[0]

    prompt = generate_prompt()

    sys.stdout.write(f"\x1b[2K\r{prompt}未找到包含该关键词的内容(回车进入下一步)。\r")
    sys.stdout.flush()

    while True:
        key = get_key()
        if key in ('\n', '\r'):
            break

    sys.stdout.write('\x1b[2K\r')
    sys.stdout.flush()

    return None


# 小说选择界面（只在一行显示切换的小说名）
def select_novel_file(novel_dir):
    novels = list_novel_files(novel_dir)
    if not novels:
        print(f"{generate_prompt()}没有找到可阅读的小说文件")
        sys.exit(1)

    selected_index = 0

    def redraw():
        prompt = generate_prompt()
        sys.stdout.write("\x1b[2K\r")
        sys.stdout.write(f"{prompt}请选择一本小说（↑↓选择，回车确认，ESC退出）: {novels[selected_index]}\r")
        sys.stdout.flush()

    redraw()
    while True:
        key = get_key()
        if key == 'UP':
            selected_index = (selected_index - 1) % len(novels)
            redraw()
        elif key == 'DOWN':
            selected_index = (selected_index + 1) % len(novels)
            redraw()
        elif key in ('\n', '\r'):
            return os.path.join(novel_dir, novels[selected_index])
        elif key == 'ESC':
            safe_exit()
        elif key == 'b':
            pass


# 获取按键事件
def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            prev_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, prev_flags | os.O_NONBLOCK)
            try:
                next1 = sys.stdin.read(1)
                next2 = sys.stdin.read(1)
                if next1 == '[':
                    if next2 == 'A':
                        return 'UP'
                    elif next2 == 'B':
                        return 'DOWN'
                return 'ESC'  # 我们现在直接返回字符串 "ESC"
            except OSError:
                return 'ESC'
            finally:
                fcntl.fcntl(fd, fcntl.F_SETFL, prev_flags)
        else:
            return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def input_single_line(prompt_text):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        new_settings = termios.tcgetattr(fd)
        new_settings[3] &= ~termios.ECHO
        new_settings[3] &= ~termios.ICANON
        termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)

        user_input = []

        prompt = generate_prompt()
        sys.stdout.write(f"{prompt}{prompt_text}")
        sys.stdout.flush()

        while True:
            char = sys.stdin.read(1)

            if char == '\n' or char == '\r':
                break
            elif char == '\x7f' or char == '\x08':
                if user_input:
                    user_input.pop()
                    sys.stdout.write('\x08 \x08')
                    sys.stdout.flush()
            elif ord(char) == 3:
                raise KeyboardInterrupt
            elif ord(char) == 27:
                safe_exit()
            elif char == 'b':
                sys.stdout.write('\x1b[2K\r')
                return 'b'
            elif char.isprintable():
                user_input.append(char)
                sys.stdout.write(char)
                sys.stdout.flush()

        result = ''.join(user_input)

        sys.stdout.write('\x1b[2K\r')
        sys.stdout.flush()
        return result
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# 计算颜色占用的长度
def visible_length(s):
    """计算去除所有 ANSI 转义序列后的字符串长度"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return len(ansi_escape.sub('', s))


def read_bashrc_ps1():
    """
    读取 ~/.bashrc 文件，解析出 PS1 的值
    """
    bashrc_path = os.path.expanduser("~/.bashrc")
    if not os.path.exists(bashrc_path):
        return None
    with open(bashrc_path, 'r') as f:
        content = f.read()
    # 匹配 PS1 的设置
    match = re.search(r"PS1='([^']+)'", content)
    if match:
        ps1 = match.group(1)
        return ps1
    return None


def parse_ps1_colors(ps1):
    # 匹配 \[\033[xxm\] 这种格式
    color_pattern = r'\\\[\\033\[([0-9;]+)m\\\]'
    matches = re.findall(color_pattern, ps1)
    colors = []
    for match in matches:
        colors.append(f'\033[{match}m')
    return colors


def generate_prompt():
    username = os.getenv('USER', 'root')
    hostname = os.uname().nodename
    pwd = os.getcwd()
    home_dir = os.path.expanduser("~")
    if pwd.startswith(home_dir):
        pwd = "~" + pwd[len(home_dir):]
    if username == 'root' and pwd == '/root':
        pwd = '~'

    prompt_char = '#' if os.geteuid() == 0 else '$'

    os_info = platform.system()

    if os_info == 'Linux':
        try:
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('ID='):
                        distro = line.split('=')[1].strip().strip('"')
                        break
                if distro == 'ubuntu':
                    ps1 = read_bashrc_ps1()
                    if ps1:
                        colors = parse_ps1_colors(ps1)
                        if len(colors) >= 2:
                            color_user_host = colors[0]
                            color_path = colors[2]  # 这里根据实际情况调整索引
                            reset_color = '\033[00m'
                            prompt = f"{color_user_host}{username}@{hostname}{reset_color}:{color_path}{pwd}{reset_color}{prompt_char} "
                            return prompt
        except FileNotFoundError:
            pass

    return f"[{username}@{hostname} {os.path.basename(pwd)}]{prompt_char} "


# 分页处理函数
def prepare_pages(novel_lines):
    _, cols = os.get_terminal_size()
    prompt = generate_prompt()
    # 使用 visible_length 来计算提示符的实际文本长度
    prompt_len = visible_length(prompt)

    pages = []
    for line in novel_lines:
        # 注意：这里不需要额外增加颜色代码的长度，因为我们关注的是最终输出的可见部分
        parts = textwrap.wrap(line, width=cols - prompt_len)
        if not parts:
            continue
        pages.extend(parts)
    return pages


# 主函数
def main():
    while True:
        novel_file = select_novel_file(DEFAULT_NOVEL_DIR)

        raw_lines = []
        with open(novel_file, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    raw_lines.append(stripped)

        pages = prepare_pages(raw_lines)
        if not pages:
            sys.stdout.write("没有内容可读\n")
            return

        last_page = load_progress(novel_file)
        current_page = last_page if last_page is not None and last_page < len(pages) else 0

        # === 单行交互式菜单 ===
        operation_menu_loop = True
        while operation_menu_loop:
            sys.stdout.write('\x1b[2K\r')  # 清除当前行
            choice = input_single_line(f"请选择操作 [1.继续阅读 / 2.跳转关键词，b 返回上一级]: ")
            if choice == 'b':
                # 操作菜单按 b 回到小说选择界面
                break
            if not choice:
                continue

            if choice == '1':
                # 进入主阅读循环
                try:
                    while True:
                        prompt = generate_prompt()
                        sys.stdout.write("\x1b[2K\r")  # 清空当前行
                        sys.stdout.write(f"{prompt}{pages[current_page]}\r")
                        sys.stdout.flush()
                        key = get_key()

                        if key == 'UP':
                            current_page = (current_page - 1) % len(pages)
                        elif key == 'DOWN':
                            current_page = (current_page + 1) % len(pages)
                        elif key == 'ESC':  # 处理 ESC 键退出
                            save_progress(novel_file, current_page)
                            safe_exit()
                        elif key == 'b':
                            save_progress(novel_file, current_page)
                            sys.stdout.write('\x1b[2K\r')  # 清除当前行
                            # 小说界面按 b 返回到操作选择界面
                            break
                        save_progress(novel_file, current_page)
                except KeyboardInterrupt:
                    save_progress(novel_file, current_page)
                    safe_exit()
            elif choice == '2':
                keyword = input_single_line(f"请输入关键词: ")
                if keyword == 'b':
                    continue
                if not keyword:
                    continue

                result_page = find_best_page(pages, keyword, current_page)
                if result_page is not None:
                    current_page = result_page
                    # 进入主阅读循环
                    try:
                        while True:
                            prompt = generate_prompt()
                            sys.stdout.write("\x1b[2K\r")  # 清空当前行
                            sys.stdout.write(f"{prompt}{pages[current_page]}\r")
                            sys.stdout.flush()
                            key = get_key()

                            if key == 'UP':
                                current_page = (current_page - 1) % len(pages)
                            elif key == 'DOWN':
                                current_page = (current_page + 1) % len(pages)
                            elif key == 'ESC':  # 处理 ESC 键退出
                                save_progress(novel_file, current_page)
                                safe_exit()
                            elif key == 'b':
                                save_progress(novel_file, current_page)
                                sys.stdout.write('\x1b[2K\r')  # 清除当前行
                                # 小说界面按 b 返回到操作选择界面
                                break
                            save_progress(novel_file, current_page)
                    except KeyboardInterrupt:
                        save_progress(novel_file, current_page)
                        safe_exit()
            else:
                prompt = generate_prompt()
                sys.stdout.write(f"\x1b[2K\r{prompt}输入无效，请重新选择。\r")
                sys.stdout.flush()
                time.sleep(0.6)
                continue


if __name__ == "__main__":
    main()
    
