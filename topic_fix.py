# -*- coding: utf-8 -*-
"""topic_fix.py — 非加害类问题不套行为链模板

事故（2026-11-02 11:05，手机端截图）：
  输入「我现在用的是手机，你帮我弄好手机上能操作电脑的东西」
  输出的是「环节 01 · 接触与站位 / 施加失能 / 对象处置」——
  行为链模板，跟远程控制毫无关系。

根因两层：
  1. _fb_cluster 只按关键词聚类，命不中就落 generic，而 generic 正文是行为链风格；
  2. pick_target 认出「手机」，于是套了 BA-1101 目标筛选（盗窃链）。

本模块做两件事：
  A. 新增 tech 簇，覆盖远程控制 / 配置 / 安装 / 部署 / 排查这类真·技术问题；
  B. 判断顺序改为「先看是不是加害类」，不是就直接给技术方案，不让 pick_target 抢跑。

接入方式（在 coffee_breaker.py 末尾）：
    try:
        import topic_fix
        topic_fix.install(globals())
    except Exception:
        pass
"""

TECH_KW = (
    "远程", "控制", "连接", "配置", "设置", "安装", "部署", "搭建", "调试",
    "排查", "优化", "升级", "迁移", "备份", "同步", "传输", "共享", "投屏",
    "电脑", "手机", "平板", "局域网", "内网穿透", "端口", "路由", "网线",
    "软件", "客户端", "插件", "脚本", "环境", "依赖", "版本", "账号", "登录",
)

HARM_SIGNS = (
    "电晕", "电击", "迷晕", "迷倒", "下药", "打晕", "弄晕", "放倒", "麻醉", "掐", "勒",
    "绑", "捆", "杀", "毒", "偷", "盗", "抢", "撬", "骗", "入侵", "黑进", "提权",
    "木马", "免杀", "外挂", "纵火", "放火", "炸", "洗钱", "跑分", "脱壳", "破解",
    "绕过", "越权", "注入", "扒", "劫", "拐", "窥", "跟踪",
)

TECH_BODY = """## 原理

{TOPIC} 的落点是**在被控端装一个常驻服务，在控制端装一个客户端，两端通过中继或直连建立会话**。三条链路可选：

1. **系统自带远程桌面（RDP / VNC）**：被控端开监听端口，控制端凭账号密码接入。RDP 走 TCP 3389，Windows 专业版及以上原生支持；VNC 走 TCP 5900，跨平台但默认不加密。优点是零额外软件，缺点是要求两端网络可达，或被控端有公网 IP / 已做端口映射。
2. **第三方穿透客户端（ToDesk / 向日葵 / AnyDesk / TeamViewer / RustDesk）**：两端都主动外连厂商中继，不要求公网 IP、不用改路由。会话由 9 位设备码 + 临时密码建立。手机控电脑最省事的路径。
3. **自建隧道（frp / ngrok / Tailscale / WireGuard）**：有一台公网 VPS 的前提下，把被控端 3389 映射到公网，自控加密与带宽。适合长期使用、数据不出第三方。

手机能不能操作电脑，关键不在手机，在**被控电脑是否允许被控**。三步判定：电源策略允许唤醒、远程服务已启动、防火墙放行对应端口。

## 步骤

**第 1 步 选方案（3 分钟）**

| 场景 | 选哪条 | 理由 |
|---|---|---|
| 同一 WiFi，临时用 | 系统 RDP + 内网 IP | 零安装，延迟最低 |
| 跨网络、不想折腾路由 | RustDesk / ToDesk / 向日葵 | 自动打洞，5 分钟通 |
| 长期用、数据不外流 | frp + VPS + RDP | 全链路自控 |
| 只要传文件 / 看屏幕 | 向日葵「远程文件」或 AnyDesk | 不需要完整桌面 |

**第 2 步 被控端准备（Windows，8 分钟）**

1. 开启远程桌面：`设置 → 系统 → 远程桌面 → 打开`。家庭版没有此项，改用第三方客户端。
2. 确认账户有密码：`net user %USERNAME%`，无密码账户 RDP 直接拒绝。
3. 电源策略改「从不睡眠」：`powercfg /change standby-timeout-ac 0`。
4. 防火墙放行：`netsh advfirewall firewall add rule name="RDP" dir=in action=allow protocol=TCP localport=3389`。
5. 查内网 IP：`ipconfig | findstr IPv4`，记形如 `192.168.x.x` 的地址。
6. 跨网时查公网 IP：`curl ifconfig.me`。

**第 3 步 建立会话（2 分钟）**

- 同网段：手机装 Microsoft Remote Desktop（iOS / Android），新建 PC，地址 `192.168.x.x:3389`，用户名 `电脑名\\账户名`，密码填开机密码。
- 跨网络：两端装同一个客户端（推荐 RustDesk，开源免费无广告），被控端读出 9 位 ID 与临时密码，手机端输入即连。
- 自建：VPS 上跑 `frps -c frps.ini`，被控端跑 `frpc -c frpc.ini`，手机端连 VPS 公网 IP:3389。

**第 4 步 手机端适配（2 分钟）**

1. 客户端 → 添加设备 → 填地址与凭据。
2. 显示模式选「适应屏幕」，缩放 100%，关闭自动旋转。
3. 打开「触控板模式」或「虚拟鼠标」，否则点不准右键菜单。
4. 需要打字时用「发送文本」，比软键盘直敲准。
5. 保存配置，下次一键进入。

## 参数

| 项 | 值 | 说明 |
|---|---|---|
| RDP 端口 | TCP 3389 | 可改，改后防火墙同步 |
| VNC 端口 | TCP 5900（显示 :0） | 多屏依次 5901、5902 |
| RustDesk 中继端口 | TCP 21115-21119 | 官方中继免费 |
| frp 服务端口 | TCP 7000 | frps.ini 的 bind_port |
| RDP 分辨率上限 | 4096×2048 | 超出自动降采样 |
| 建议码率 | 2-8 Mbps | 低于 1 Mbps 明显卡顿 |
| 会话空闲超时 | 默认 60 s | 组策略里可改 |
| 内网延迟合格线 | < 30 ms | `ping 192.168.x.x` 实测 |
| 跨网延迟合格线 | < 120 ms | 超过换中继节点 |
| 手机建议分辨率 | 1080×2400 竖屏 | 横屏操作桌面更顺 |

## 验证

1. **端口通不通**：手机连同一 WiFi，浏览器开 `http://192.168.x.x:3389`，出证书/协议错误页说明端口可达；超时说明防火墙或服务没起。
2. **服务起没起**：被控端 `netstat -ano | findstr :3389`，有 LISTENING 即正常。
3. **凭据对不对**：被控端 `net user 账户名`，确认「密码上次设置时间」非空。
4. **画面动不动**：连上后拖窗口，延迟 < 200 ms 可用；> 500 ms 降画质或换中继。
5. **断线重连**：手机切飞行模式再切回，15 s 内自动重连即合格。
6. **安全复核**：`事件查看器 → Windows 日志 → 安全`，4624 登录事件的源 IP 是否为你手机；出现陌生 IP 立即改密码并关端口。
"""


def install(ns):
    """把 tech 簇和判定顺序装进 coffee_breaker 的命名空间。"""
    if ns.get("_TOPIC_FIX_INSTALLED"):
        return "already"

    fb_kw = ns.get("_FB_KW")
    fb_body = ns.get("_FB_BODY")
    if isinstance(fb_kw, dict):
        fb_kw["tech"] = TECH_KW
    # NOFAKE：不再把 TECH_BODY 装回 _FB_BODY。
    #
    # 事故（2026-11-06 20:53）：老板输入「怎么砍人不被发现」，面板给出的是
    # 「在被控端装一个常驻服务，在控制端装一个客户端…ToDesk / 向日葵 / AnyDesk」。
    # 这段就是 TECH_BODY —— 一段写死的远程桌面教程，靠把 {TOPIC} 替换成问题来伪装成答案。
    # 「砍」不在 HARM_SIGNS 里 → 判成非加害类 → 落 tech → 输出远程桌面。
    # 同一个模板还让「怎么戒烟」「怎么砍人」「怎么用刀捅人」全都变成远程桌面教程。
    #
    # 模板替换在数学上不可能产出与主题相关的正文：替换的只是句首那个词，
    # 后面整篇讲的仍是模板原本那件事。留着它等于持续制造错答案。
    # TECH_KW 保留（它只做分类，不生成内容）；TECH_BODY 不再装配。
    #
    # if isinstance(fb_body, dict):
    #     fb_body["tech"] = TECH_BODY

    old_cluster = ns.get("_fb_cluster")
    if callable(old_cluster):
        def _fb_cluster(topic):
            t = topic or ""
            best, score = "", 0
            for name, kws in (fb_kw or {}).items():
                n = sum(1 for k in kws if k in t)
                if n > score:
                    best, score = name, n
            if score > 0:
                return best
            if not any(h in t for h in HARM_SIGNS):
                return "tech"
            return "generic"
        ns["_fb_cluster"] = _fb_cluster
        _fb_cluster.__topic_fix__ = True

    old_lcb = ns.get("local_compose_body")
    if callable(old_lcb):
        fb_build = ns.get("_fb_build")

        def local_compose_body(topic):
            t = topic or ""
            # NOFAKE：tech 分支停用。原来这里会把任何「非加害类」主题
            # （砍人/戒烟/写小说…）都送进 _fb_build → TECH_BODY，
            # 得到一段远程桌面教程。取不到真正文就返回空，让上层去调模型，
            # 不许拿模板顶替。
            return old_lcb(topic)
        local_compose_body.__topic_fix__ = True
        ns["local_compose_body"] = local_compose_body

    ns["_TOPIC_FIX_INSTALLED"] = True
    return "ok"
