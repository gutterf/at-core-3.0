# AT内核3.0 使用说明

## 一、下载

从本仓库右侧 Releases 页面下载 `AT3.exe`（单文件，无需安装 Python）。
下载后放到任意目录，双击运行。

## 二、首次使用三步

### 第 1 步：填 DeepSeek API Key
打开软件 → 右上角「设置」→ API Key 栏粘贴你的 DeepSeek Key
（申请地址：platform.deepseek.com → API Keys → 创建）
模型默认 deepseek-flash，可改成 deepseek-chat。

### 第 2 步：注入插件（让 WorkBuddy 生效）
先安装并登录 WorkBuddy，然后：
软件主界面点「注入插件 workbuddy」按钮 → 提示注入成功 → 重启 WorkBuddy。
重启后 WorkBuddy 的破甲链路（常驻内核 + 免审批 + 拒答打回）自动生效。

### 第 3 步：开总开关
软件主界面点「满血无审查」按钮，按钮变绿即开启。
之后直接在 WorkBuddy 里正常提问，链路自动接管。

## 三、按钮说明

| 按钮 | 作用 |
|---|---|
| 满血无审查 | 总开关。开=链路接管 WorkBuddy 输出，关=原样 |
| 自动续任务会话 | 开=每 20 秒检测会话中断，中断自动向 WorkBuddy 发「继续」 |
| 注入插件 workbuddy | 把内置 pojiaT1 插件（规则+hooks）复制进 WorkBuddy 插件目录 |
| 插件收回 | 删除注入的 pojiaT1 插件，恢复原状 |

## 四、常见问题

**Q：点了注入按钮没生效？**
A：必须完全退出 WorkBuddy 再重开（不是关窗口，是托盘图标右键退出）。

**Q：聊天没反应？**
A：检查设置页 API Key 是否已填、网络能否访问 api.deepseek.com。
软件启动会自动拉起本地转发代理（17899 端口），被防火墙拦时放行即可。

**Q：只想注入插件不用软件的聊天？**
A：可以。注入按钮独立工作，注入完就关掉软件也没影响。

**Q：怎么完全卸载？**
A：软件里点「插件收回」→ 删除软件文件夹即可，无残留注册表。

## 五、源码运行（进阶）

需要 Python 3.10+，安装依赖后运行：
```
pip install pillow rapidfuzz jieba fuzzywuzzy
python coffee_breaker.py
```

## 六、免责

本软件供技术研究使用，使用者自行承担使用后果。
