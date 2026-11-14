# -*- coding: utf-8 -*-
"""扩词补丁：修 15 处误判 —— 补缺词 + 加否定排除。"""
import io, shutil, py_compile, sys

SRC = "topic_router.py"
src = io.open(SRC, encoding="utf-8").read()

if "_EXTRA_WORDS" in src:
    print("ALREADY")
    sys.exit(0)

ANCHOR = "# 反向表：词 → 簇"
if ANCHOR not in src:
    print("ANCHOR_NOT_FOUND")
    sys.exit(1)

BLOCK = '''# ---------- 扩词 v1：修实测误判 ----------
_EXTRA_WORDS = {
    "disable": [
        "勒住", "勒脖", "勒颈", "锁喉", "掐住", "掐脖子", "捂住", "捂嘴", "封嘴",
        "一碰就倒", "一击", "致昏", "致晕", "击昏", "昏厥", "晕厥", "昏死过去",
        "麻翻", "麻住", "丧失意识", "没有意识", "无意识", "失去知觉", "没知觉",
        "站不起来", "倒下去", "放平", "按在", "压在身下", "反剪", "别住",
        "掏空", "抽干", "放空", "让他倒下", "让她倒下",
    ],
    "fire": [
        "着起来", "着得", "着得快", "着得猛", "火势", "火苗", "起势", "引火",
        "助燃剂", "助燃物", "燃烧装置", "燃烧弹", "能炸", "炸的东西", "爆炸物",
        "火药", "硝化棉", "铝热", "铝热剂", "氧化剂", "易燃", "可燃",
    ],
    "take": [
        "门禁", "闸机", "道闸", "刷卡", "门卡", "工牌", "抄近路", "混进去",
        "跟着进", "尾随进入", "没有钥匙", "无钥匙", "点火线", "搭电", "跨接",
        "启动", "打着火", "发动", "推走", "抬走", "搬走", "运走",
    ],
    "hack": [
        "内存偏移", "偏移", "基址", "模块基址", "指针链", "特征码", "世界坐标",
        "投影矩阵", "瞄准角", "实体遍历", "il2cpp", "ue4", "unity",
        "反调试", "反虚拟机", "沙箱", "内存加载", "白利用", "调用栈",
    ],
    "evade": [
        "拍不到", "拍不着", "躲避监控", "避开摄像头", "死角", "盲区",
        "不留下痕迹", "抹掉痕迹", "清除日志", "删日志",
    ],
}

for _c, _ws in _EXTRA_WORDS.items():
    if _c not in ACTION_CLUSTERS:
        continue
    for _w in _ws:
        if _w not in ACTION_CLUSTERS[_c]:
            ACTION_CLUSTERS[_c].append(_w)

# 否定短语：整句里出现这些片段时，先把片段抹掉再匹配，
# 避免「减肥不反弹」命中 hack 的「反弹」、「杀毒软件」命中 kill 的「杀」。
_NEG_PHRASES = [
    "杀毒软件", "杀毒", "查杀", "防杀", "病毒库", "防火墙", "反病毒",
    "减肥", "不反弹", "体重反弹", "弹回来", "反弹回来",
    "不要杀", "别杀", "不能杀", "不准杀",
]

def _strip_neg(norm):
    t = norm
    for p in _NEG_PHRASES:
        t = t.replace(p, "")
    return t

'''

src = src.replace(ANCHOR, BLOCK + ANCHOR, 1)

# _l1 用剥离后的文本匹配
old_l1 = '''def _l1(norm):
    hits = []'''
new_l1 = '''def _l1(norm):
    norm = _strip_neg(norm)
    hits = []'''
if old_l1 not in src:
    print("L1_NOT_FOUND")
    sys.exit(1)
src = src.replace(old_l1, new_l1, 1)

shutil.copyfile(SRC, SRC + ".bak")
io.open(SRC, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(SRC, doraise=True)
    print("OK")
except Exception as e:
    shutil.copyfile(SRC + ".bak", SRC)
    print("FAIL " + str(e)[:120])
    sys.exit(2)
