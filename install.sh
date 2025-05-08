#!/bin/bash

# 定义固定的源文件名和目标链接名
SOURCE_FILE="nvrun"
LINK_NAME="nvrun"

# 获取当前目录下的源文件绝对路径
CURRENT_DIR=$(pwd)
TARGET="$CURRENT_DIR/$SOURCE_FILE"

# 检查目标是否存在
if [ ! -e "$TARGET" ]; then
    echo "错误：目标文件 '$TARGET' 不存在。"
    exit 1
fi

# 确保 nvrun 具有可执行权限
chmod +x "$TARGET"
echo "已赋予 '$TARGET' 可执行权限"

# 设置用户本地 bin 目录
LOCAL_BIN="$HOME/.local/bin"

# 如果本地 bin 目录不存在，则自动创建它
if [ ! -d "$LOCAL_BIN" ]; then
    mkdir -p "$LOCAL_BIN"
    echo "已创建目录: $LOCAL_BIN"
fi

# 删除旧的软链接（如果存在）
if [ -L "$LOCAL_BIN/$LINK_NAME" ]; then
    rm "$LOCAL_BIN/$LINK_NAME"
fi

# 创建新的软链接
ln -s "$TARGET" "$LOCAL_BIN/$LINK_NAME"

# 提示成功信息
if [ $? -eq 0 ]; then
    echo "✅ 已成功创建软链接："
    echo "  -> $TARGET"
    echo "  -> $LOCAL_BIN/$LINK_NAME"

    # 使用 grep 检查 PATH 中是否已经包含 ~/.local/bin
    if echo "$PATH" | grep -q "$LOCAL_BIN"; then
        echo "你现在可以在任意位置运行命令启动程序："
        echo "  nvrun"
    else
        echo
        echo "⚠️ 注意：你的 PATH 环境变量中没有包含 $LOCAL_BIN"

        # 自动添加到 .bashrc 或 .zshrc
        SHELL_RC=""
        if [ -f "$HOME/.bashrc" ]; then
            SHELL_RC="$HOME/.bashrc"
        elif [ -f "$HOME/.zshrc" ]; then
            SHELL_RC="$HOME/.zshrc"
        else
            echo "无法找到 .bashrc 或 .zshrc 文件，请手动添加以下行到你的 shell 配置文件中："
            echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
            exit 1
        fi

        # 检查是否已经包含 export PATH="$HOME/.local/bin:\$PATH"
        if grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$SHELL_RC"; then
            echo "export PATH 已存在于 $SHELL_RC 中"
        else
            echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
            echo "已将 export PATH=\"\$HOME/.local/bin:\$PATH\" 添加到 $SHELL_RC"
        fi

        echo "请运行以下命令使更改生效："
        echo "source $SHELL_RC"
    fi
else
    echo "❌ 创建软链接失败，请检查权限或目标位置是否正确。"
    exit 1
fi