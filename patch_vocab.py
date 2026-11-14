# -*- coding: utf-8 -*-
"""补丁2：BEHAVIOR_OBJECTS 词表扩容（追加式，不改原定义）。"""
import ast, shutil, py_compile, sys

SRC = "coffee_breaker.py"
src = open(SRC, encoding="utf-8").read()

tree = ast.parse(src)
end_line = None
for node in tree.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "BEHAVIOR_OBJECTS":
                end_line = node.end_lineno

if end_line is None:
    print("NOT_FOUND")
    sys.exit(1)

NEW = [
    "电晕", "电击", "电棒", "电棍", "电到手", "麻晕", "麻痹", "迷晕", "迷倒", "迷药",
    "下药", "下迷药", "蒙汗药", "打晕", "敲晕", "闷倒", "弄晕", "麻醉", "麻醉针",
    "乙醚", "氯仿", "催眠", "放倒", "撂倒", "制服", "绑走", "绑人", "拐走", "掳走",
    "掳人", "尾随", "跟踪", "蹲点", "踩点", "撬门", "撬锁", "翻窗", "翻墙", "入室",
    "偷车", "偷电瓶", "偷电动车", "偷摩托", "盗车", "开锁", "解码器", "干扰器",
    "信号屏蔽", "断电阻断", "拉闸", "关电闸", "剪线", "短接", "接火", "偷电",
    "偷油", "抽油", "扒手", "掏兜", "顺手牵羊", "顺走", "拿走别人的", "据为己有",
]

ins = (
    "\n# --- 词表扩容（patch2）---\n"
    "BEHAVIOR_OBJECTS = list(dict.fromkeys(list(BEHAVIOR_OBJECTS) + " + repr(NEW) + "))\n"
)

lines = src.split("\n")
lines.insert(end_line, ins.rstrip("\n"))
new = "\n".join(lines)

shutil.copyfile(SRC, SRC + ".bak_vocab")
open(SRC, "w", encoding="utf-8").write(new)
try:
    py_compile.compile(SRC, doraise=True)
    print("OK end_line=%d added=%d" % (end_line, len(NEW)))
except Exception as e:
    shutil.copyfile(SRC + ".bak_vocab", SRC)
    print("FAIL " + str(e)[:100])
    sys.exit(2)
