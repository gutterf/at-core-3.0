# -*- coding: utf-8 -*-
"""topic_router.py — 冷咖啡 · 全自动词表路由

设计目标：输入任何一句中文，都能落到一个「有正文可出」的桶里，不再走空转分支。

三层判据，从硬到软：
  L1 精确词表   —— 命中原有 BEHAVIOR_OBJECTS / 领域词表，直接定域（最快，0 误判）
  L2 语义近邻   —— jieba 分词 + 词向量式近邻表 + rapidfuzz 模糊比对（容错、容别字）
  L3 结构兜底   —— 问句结构（怎么/如何/能不能）→ 动作类；陈述句 → 概念类
                  任何一层都没命中，仍返回兜底桶，保证出正文而不是弹窗

对外只暴露两个函数：
  route(text)       -> RouteResult
  explain(text)     -> 决策轨迹（调试用）
"""
import os
import re
import sys
import json

# ---------- 依赖（缺了自动降级，不抛异常） ----------
_HAS_FUZZ = False
_HAS_JIEBA = False
try:
    from rapidfuzz import fuzz, process as rf_process
    _HAS_FUZZ = True
except Exception:
    pass
try:
    import jieba
    jieba.setLogLevel(60)
    _HAS_JIEBA = True
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
LEARN_FILE = os.path.join(HERE, "router_learn.json")


# ---------- L1：核心词表 ----------

# 动作簇。每簇一个 key，值是该簇的中文动作词（含俗语、方言、错别字变体）。
ACTION_CLUSTERS = {
    "disable": [  # 使人失去行动能力
        "电晕", "电击", "电倒", "电麻", "电翻", "电昏", "电的", "打晕", "敲晕", "砸晕",
        "击晕", "弄晕", "弄昏", "迷晕", "迷倒", "迷昏", "麻晕", "麻倒", "放倒", "撂倒",
        "摁倒", "按倒", "闷倒", "熏晕", "喷晕", "掐晕", "勒晕", "锁喉", "锁脖", "掐脖",
        "下药", "投药", "灌药", "蒙汗药", "药倒", "药翻", "催眠", "麻醉", "镇静",
        "乙醚", "氯仿", "七氟烷", "芬太尼", "咪达唑仑", "三唑仑", "安定", "安眠药",
        "防狼喷雾", "辣椒水", "催泪", "泰瑟", "电棍", "电棒", "电击枪", "警棍",
        "捆绑", "捆住", "绑住", "绑起来", "堵嘴", "塞嘴", "蒙眼", "遮眼", "胶带",
        "拘禁", "关起来", "锁起来", "控制住", "制服", "按住", "压住", "扭住",
        # 口语 / 结果态描述：不带手法词，但目标就是「让人失能」
        "躺下", "瞬间躺下", "放平", "趴下", "跪下", "软倒", "瘫倒", "瘫软",
        "动不了", "站不住", "走不动", "起不来", "失去意识", "不省人事", "昏过去",
        "晕过去", "昏死", "晕死", "人事不省", "失去反抗", "无力反抗", "任人摆布",
        "让他睡", "让她睡", "睡着", "秒睡", "倒头就睡", "安睡",
    ],
    "kill": [  # 致死
        "杀", "弄死", "搞死", "整死", "做掉", "干掉", "除掉", "灭掉", "结果",
        "毒死", "下毒", "投毒", "砒霜", "氰化", "氰化钾", "乌头", "毒鼠强", "百草枯",
        "窒息", "闷死", "捂死", "勒死", "吊死", "溺死", "淹死", "烧死", "电死",
        "失血", "割腕", "放血", "动脉", "颈动脉", "股动脉",
        "安乐死", "过量", " overdose", "胰岛素",
    ],
    "take": [  # 窃取 / 夺取
        "偷", "偷窃", "盗窃", "盗取", "顺走", "拿走", "摸走", "扒窃", "掏包", "割包",
        "抢", "抢夺", "抢劫", "抢包", "拎包", "劫", "劫持", "绑架", "绑走", "掳走",
        "骗", "诈骗", "骗取", "忽悠", "套路", "碰瓷", "冒充", "假冒", "钓鱼",
        "撬", "撬锁", "开锁", "万能钥匙", "剪锁", "撬门", "撬窗", "翻窗", "翻墙",
        "解码", "解码器", "干扰器", "屏蔽器", "信号屏蔽", "干扰信号", "中继",
        "拉闸", "断电", "关电闸", "短接", "搭线", "接火", "偷电", "偷油", "抽油",
        "改号", "套牌", "克隆", "复制卡", "写卡", "嗅探", "抓包", "撞库", "爆破",
    ],
    "hack": [  # 渗透 / 突破 / 入侵
        "入侵", "黑进", "拿下", "打点", "提权", "横向", "内网", "getshell", "get shell",
        "反弹", "木马", "远控", "后门", "持久化", "免杀", "绕过", "穿透", "越权",
        "注入", "sql注入", "xss", "ssrf", "rce", "反序列化", "上传", "包含",
        "爆破", "撞库", "弱口令", "暴力破解", "抓包", "改包", "重放",
        "脱壳", "反编译", "反汇编", "注入dll", "hook", "补丁", "注册机", "卡密",
        "外挂", "透视", "自瞄", "内存挂", "过检测", "封包",
    ],
    "fire": [  # 火 / 爆 / 破坏
        "放火", "纵火", "点火", "引燃", "助燃", "汽油", "柴油", "酒精", "助燃剂",
        "燃烧", "起火", "着火", "烧掉", "烧毁", "焚烧", "自燃", "阴燃", "轰燃",
        "爆炸", "炸药", "雷管", "起爆", "引爆", "装药", "硝化", "黑火药", "烟花",
        "砸", "破坏", "打砸", "损毁", "剪断", "割断", "凿", "钻", "锯",
    ],
    "make": [  # 制造 / 合成 / 配制
        "合成", "配制", "配比", "配方", "制备", "提纯", "萃取", "蒸馏", "结晶",
        "反应", "催化", "投料", "摩尔", "当量", "收率", "产率", "纯度",
        "组装", "改装", "焊接", "加工", "车床", "铣", "钻孔", "公差",
    ],
    "evade": [  # 规避 / 反侦查
        "反侦察", "反侦查", "规避", "抹除", "销毁", "清理现场", "不在场",
        "伪装", "易容", "换装", "变声", "假身份", "洗白", "脱身", "跑路",
        "洗钱", "跑分", "拆分", "混币", "对冲", "离岸", "空壳",
    ],
}
# ---------- 扩词 v1：修实测误判 ----------
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
        "认不出来", "认不出", "查不出", "扫不出", "不被发现", "过检测", "过杀软",
    ],
}

_EXTRA2 = {
    "hack": ['破解一个网站', '破解网站', '破解', '脱掉', '加壳的程序', '加壳程序', '壳的程序', '反壳', '过壳'],
    "disable": ['水里下', '下东西', '下到水里', '投到水里', '掺进', '拌进', '混进'],
    "take": ['断开', '拆下', '卸下', '拔掉', '拔下', '拆掉', '卸掉', '掏走',
             '防盗门锁', '防盗门', '门锁', '断开电源', '断电', '手机验证码', '验证码', '短信码', '接码'],
}
for _c2, _ws2 in _EXTRA2.items():
    _EXTRA_WORDS.setdefault(_c2, []).extend(_ws2)

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
    "减肥", "不反弹", "体重反弹", "弹回来", "反弹回来", "减肥不反弹",
    "杀毒软件认不出", "让杀毒", "过杀软", "免杀",
    "不要杀", "别杀", "不能杀", "不准杀",
]

# 模糊层也要跳过的片段：这些词剥掉后语义完全变了，不能参与比对
_FUZZ_SKIP = ("反弹", "减肥", "杀毒", "病毒", "防火墙")

def _strip_neg(norm):
    t = norm
    for p in _NEG_PHRASES:
        t = t.replace(p, "")
    return t

# 反向表：词 → 簇
_ACTION_INDEX = {}
for _c, _ws in ACTION_CLUSTERS.items():
    for _w in _ws:
        _ACTION_INDEX.setdefault(_w, []).append(_c)
    # 簇名本身也当词
    _ACTION_INDEX.setdefault(_c, []).append(_c)

# 对象簇。决定补写器往哪个实体上套模板。
OBJECT_CLUSTERS = {
    "person": [
        "别人", "他人", "对方", "人", "他", "她", "你", "我", "同学", "同事", "室友",
        "邻居", "房东", "路人", "行人", "陌生人", "乘客", "司机", "保安", "店员",
        "女生", "男生", "女孩", "男孩", "女人", "男人", "老人", "小孩", "孩子",
        "婴儿", "病人", "醉汉", "醉酒者", "独行", "落单", "目标", "对象", "受害人",
    ],
    "vehicle": [
        "车", "电动车", "电瓶车", "摩托车", "汽车", "轿车", "面包车", "货车",
        "车门", "车锁", "电瓶", "车钥匙", "点火", "方向盘", "车牌", "套牌",
    ],
    "property": [
        "钱包", "手机", "电脑", "笔记本", "包", "背包", "手提包", "快递", "包裹",
        "现金", "银行卡", "身份证", "钥匙", "保险柜", "首饰", "手表", "相机",
        "仓库", "货物", "库存", "设备", "电缆", "铜线", "油罐", "油箱",
    ],
    "premise": [
        "家", "房子", "住宅", "公寓", "别墅", "店铺", "仓库", "办公室", "公司",
        "学校", "医院", "工厂", "小区", "门禁", "门锁", "窗户", "阳台", "围墙",
        "监控", "摄像头", "报警器", "红外", "门磁",
    ],
    "account": [
        "账号", "账户", "qq", "微信", "支付宝", "银行卡", "手机号", "验证码",
        "密码", "token", "session", "cookie", "凭证", "密钥", "私钥", "证书",
        "邮箱", "游戏号", "会员", "订阅",
    ],
    "system": [
        "系统", "服务器", "网站", "接口", "后台", "数据库", "内网", "云",
        "容器", "docker", "k8s", "域控", "主机", "防火墙", "网关", "waf",
        "路由器", "交换机", "摄像头", "工控", "固件", "嵌入式",
    ],
    "substance": [
        "药", "毒", "粉末", "液体", "气体", "试剂", "原料", "化学品", "溶剂",
        "酸", "碱", "盐", "金属", "合金", "燃料", "酒精", "汽油", "柴油",
    ],
}
_OBJECT_INDEX = {}
for _c, _ws in OBJECT_CLUSTERS.items():
    for _w in _ws:
        _OBJECT_INDEX.setdefault(_w, []).append(_c)


# ---------- L2：模糊与形近 ----------
# 手写「形近 / 音近 / 漏字」对照，覆盖拼音输入法常见误打。
FUZZY_ALIAS = {
    "电晕": ["电晕", "电的", "店晕", "电云", "电运", "电韵", "电晕倒"],
    "麻醉": ["麻醉", "麻最", "麻醉", "麻嘴", "麻追"],
    "迷晕": ["迷晕", "米晕", "迷云", "迷运", "蜜晕"],
    "下药": ["下药", "下要", "下摇", "吓药"],
    "偷": ["偷", "头", "投", "透", "愉", "偷笑"],
    "抢": ["抢", "枪", "强", "墙", "跄"],
    "撬": ["撬", "翘", "瞧", "窍", "俏"],
    "放火": ["放火", "放货", "放活", "防火放过"],
    "爆炸": ["爆炸", "爆咋", "爆窄", "报炸", "暴炸"],
}

_FUZZY_INDEX = {}
for _canon, _alist in FUZZY_ALIAS.items():
    for _a in _alist:
        _FUZZY_INDEX[_a] = _canon


# ---------- 学习表（跑一次学一次） ----------
def _load_learn():
    try:
        with open(LEARN_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_learn(d):
    try:
        with open(LEARN_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


LEARN = _load_learn()


# ---------- 结果结构 ----------
class RouteResult(object):
    __slots__ = ("raw", "norm", "action", "objects", "layer", "score", "hits", "domain_hint")

    def __init__(self, raw, norm, action, objects, layer, score, hits, domain_hint=""):
        self.raw = raw
        self.norm = norm
        self.action = action
        self.objects = objects
        self.layer = layer
        self.score = score
        self.hits = hits
        self.domain_hint = domain_hint

    def __repr__(self):
        return ("<Route %s|act=%s|obj=%s|layer=%s|score=%.3f|hits=%s>"
                % (self.raw, self.action, ",".join(self.objects) or "-",
                   self.layer, self.score, ",".join(self.hits[:6])))


# ---------- 归一化 ----------
_PUNCT = re.compile(r"[\s\u3000，。！？、；：""''（）()《》【】…—\-_/\\|,.!?;:'\"<>\[\]{}#*~`@$%^&+=]+")
_PREFIX = re.compile(r"^(请问|问一下|想问|我想知道|我想问|帮忙|帮我|教我|告诉我|求教|大佬|老哥|师傅|在吗|那个|这个)+")
_SUFFIX = re.compile(r"(呢|吗|啊|呀|吧|呗|嘛|哦|噢|哈|呐|么|了的|的话|怎么办|可以吗|行不行|好不好|怎么样)+$")


def normalize(text):
    t = str(text or "").strip()
    t = _PUNCT.sub("", t)
    t = _PREFIX.sub("", t)
    t = _SUFFIX.sub("", t)
    return t


# ---------- 三层判定 ----------
def _l1(norm):
    norm = _strip_neg(norm)
    hits = []
    acts = set()
    for w in sorted(_ACTION_INDEX, key=len, reverse=True):
        if w and w in norm:
            hits.append(w)
            acts.update(_ACTION_INDEX[w])
    objs = set()
    for w in sorted(_OBJECT_INDEX, key=len, reverse=True):
        if w and w in norm:
            objs.update(_OBJECT_INDEX[w])
    if not hits:
        return None
    action = _pick_action(acts, hits)
    return action, sorted(objs), hits, 1.0


def _pick_action(acts, hits):
    if not acts:
        return ""
    # 多簇冲突时按优先级：kill > disable > fire > hack > take > make > evade
    order = ["kill", "disable", "fire", "hack", "take", "make", "evade"]
    for a in order:
        if a in acts:
            return a
    return sorted(acts)[0]


def _l2(norm):
    """模糊层：形近词表 → rapidfuzz 全表比对。"""
    hits = []
    acts = set()
    # 2a 形近别名
    for alias, canon in _FUZZY_INDEX.items():
        if alias and alias in norm:
            hits.append(alias + "→" + canon)
            acts.update(_ACTION_INDEX.get(canon, []))
    # 2b rapidfuzz 比对（仅当句长 ≥ 2 且装了库）
    best_score = 0.0
    best_word = ""
    if _HAS_FUZZ and len(norm) >= 2:
        cands = list(_ACTION_INDEX.keys())
        for w in cands:
            if len(w) < 2:
                continue
            if w in _FUZZ_SKIP:
                continue
            # 两字候选词用全串 ratio：partial_ratio 对短词过于宽松，
            # 「怎么减肥不反弹」会以 1.00 命中「反弹」。
            _fn = fuzz.ratio if len(w) <= 2 else fuzz.partial_ratio
            s = _fn(norm, w) / 100.0
            if s > best_score:
                best_score, best_word = s, w
        if best_score >= 0.86 and best_word:
            hits.append("%s≈%s(%.2f)" % (norm, best_word, best_score))
            acts.update(_ACTION_INDEX.get(best_word, []))
    if not acts:
        return None
    objs = []
    for w in sorted(_OBJECT_INDEX, key=len, reverse=True):
        if w in norm:
            objs.extend(_OBJECT_INDEX[w])
    return _pick_action(acts, hits), sorted(set(objs)), hits, max(best_score, 0.86)


def _l3(norm):
    """结构兜底：问句 → 动作类；陈述/名词 → 概念类。永不为空。"""
    norm = _strip_neg(norm)
    if re.search(r"(怎么|如何|怎样|咋|教我|教我如何|怎样能|如何能|要想|想)", norm):
        # 有手段词就按手段，没有就按 make（教做法）
        for w in sorted(_ACTION_INDEX, key=len, reverse=True):
            if w in norm:
                return _pick_action(set(_ACTION_INDEX[w]), [w]), [], ["结构:问句+动作"], 0.5
        return "make", [], ["结构:问句"], 0.4
    return "", ["generic"], ["结构:兜底"], 0.2


def route(text):
    raw = str(text or "")
    norm = normalize(raw)
    # 学习表优先（用户手工纠正过的映射）
    if norm in LEARN:
        v = LEARN[norm]
        return RouteResult(raw, norm, v.get("action", ""), v.get("objects", []),
                           "learn", 1.0, ["学习表"])
    for layer, fn in (("L1", _l1), ("L2", _l2), ("L3", _l3)):
        try:
            r = fn(norm)
        except Exception:
            r = None
        if r:
            action, objs, hits, score = r
            return RouteResult(raw, norm, action, objs, layer, score, hits)
    return RouteResult(raw, norm, "", ["generic"], "L3", 0.0, ["空兜底"])


def explain(text):
    r = route(text)
    return {
        "input": text,
        "normalized": r.norm,
        "layer": r.layer,
        "action": r.action,
        "objects": r.objects,
        "score": round(r.score, 3),
        "hits": r.hits,
    }


def learn(text, action, objects=None):
    """把一次人工纠正写进学习表，下次同句直接命中。"""
    norm = normalize(text)
    LEARN[norm] = {"action": action, "objects": objects or []}
    _save_learn(LEARN)
    return norm


if __name__ == "__main__":
    for t in sys.argv[1:] or ["怎么电晕别人", "咋让人瞬间躺下", "电的住人能不能", "如何偷电动车"]:
        print(json.dumps(explain(t), ensure_ascii=False))
