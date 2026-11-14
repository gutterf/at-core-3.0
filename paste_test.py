# -*- coding: utf-8 -*-
"""paste_test.py — 独立测试 WorkBuddy 自动粘贴"""
import ctypes
import ctypes.wintypes as w
import sys
import time

user32 = ctypes.WinDLL("user32", use_last_error=True)

# ---- 严格声明所有函数签名（64位下必须，否则 HWND 被截断/参数错位）----
user32.IsWindowVisible.argtypes = [w.HWND]
user32.IsWindowVisible.restype = w.BOOL

user32.GetWindowTextLengthW.argtypes = [w.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.ShowWindow.argtypes = [w.HWND, ctypes.c_int]
user32.ShowWindow.restype = w.BOOL

user32.SetForegroundWindow.argtypes = [w.HWND]
user32.SetForegroundWindow.restype = w.BOOL

user32.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
user32.GetWindowRect.restype = w.BOOL

user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = w.BOOL

user32.mouse_event.argtypes = [w.DWORD, w.DWORD, w.DWORD, w.DWORD, ctypes.c_void_p]
user32.mouse_event.restype = None

user32.keybd_event.argtypes = [w.BYTE, w.BYTE, w.DWORD, ctypes.c_void_p]
user32.keybd_event.restype = None

user32.BringWindowToTop.argtypes = [w.HWND]
user32.BringWindowToTop.restype = w.BOOL

user32.AttachThreadInput.argtypes = [w.DWORD, w.DWORD, w.BOOL]
user32.AttachThreadInput.restype = w.BOOL

user32.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
user32.GetWindowThreadProcessId.restype = w.DWORD

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetCurrentThreadId.restype = w.DWORD


def find_wb():
    hits = []
    EP = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)

    def _cb(h, l):
        try:
            if not user32.IsWindowVisible(h):
                return True
            n = user32.GetWindowTextLengthW(h)
            if n <= 0:
                return True
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(h, buf, n + 1)
            t = buf.value
            if t.strip() == "WorkBuddy":
                hits.append((h, t))
        except Exception as e:
            print("[cb error]", e)
        return True

    user32.EnumWindows(EP(_cb), 0)
    return hits


def force_focus(hwnd):
    """三种方式一起上，确保真的拿到前台焦点"""
    fg = user32.GetForegroundWindow()
    cur_tid = kernel32.GetCurrentThreadId()

    user32.ShowWindow(hwnd, 9)      # SW_RESTORE
    ok1 = user32.BringWindowToTop(hwnd)
    print("  BringWindowToTop:", ok1)

    # 附加到当前前台窗口线程，绕开 SetForegroundWindow 限制
    if fg:
        fg_tid = user32.GetWindowThreadProcessId(fg, None)
        user32.AttachThreadInput(cur_tid, fg_tid, True)
    ok2 = user32.SetForegroundWindow(hwnd)
    if fg:
        user32.AttachThreadInput(cur_tid, fg_tid, False)
    print("  SetForegroundWindow:", ok2)

    time.sleep(0.5)
    print("  当前前台:", user32.GetForegroundWindow(), "目标:", hwnd)
    return user32.GetForegroundWindow() == hwnd


def click(x, y):
    user32.SetCursorPos(x, y)
    time.sleep(0.1)
    user32.mouse_event(0x0002, 0, 0, 0, None)   # LEFTDOWN
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, None)   # LEFTUP


def key(vk, down=True):
    user32.keybd_event(vk, 0, 0 if down else 0x0002, None)


def ctrl_key(vk):
    key(0x11, True)      # CTRL down
    time.sleep(0.03)
    key(vk, True)
    time.sleep(0.03)
    key(vk, False)
    time.sleep(0.03)
    key(0x11, False)     # CTRL up


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else "【测试粘贴】如果看到这行字说明成功"
    print("=" * 50)
    print("1. 查找 WorkBuddy 窗口")
    hits = find_wb()
    print("   找到:", hits)
    if not hits:
        print("   失败：没找到标题为 WorkBuddy 的窗口")
        return

    hwnd, title = hits[0]
    print("2. 强制聚焦")
    if not force_focus(hwnd):
        print("   警告：前台焦点可能没拿到，继续尝试")

    rect = w.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    print("   窗口矩形: (%d,%d)-(%d,%d)  %dx%d" % (rect.left, rect.top, rect.right, rect.bottom, width, height))

    # 输入框位置：底部 86%
    xx = rect.left + width // 2
    yy = rect.top + int(height * 0.86)
    print("3. 点击输入区 (%d, %d)" % (xx, yy))
    click(xx, yy)
    time.sleep(0.4)

    print("4. 写入剪贴板")
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        print("   tkinter 写入成功，%d 字符" % len(text))
    except Exception as e:
        print("   tkinter 失败:", e)
        return

    print("5. Ctrl+A 全选")
    ctrl_key(0x41)
    time.sleep(0.15)
    print("6. Delete 清空")
    key(0x2E, True)
    key(0x2E, False)
    time.sleep(0.15)
    print("7. Ctrl+V 粘贴")
    ctrl_key(0x56)
    time.sleep(0.6)
    print("=" * 50)
    print("完成。看 WorkBuddy 输入框里有没有出现：")
    print("  " + text[:60])


if __name__ == "__main__":
    main()
