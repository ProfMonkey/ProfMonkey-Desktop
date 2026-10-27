# 🐒 ProfMonkey Desktop — 你的电脑里，住进了一只不太正常的猴子

> **当前 GitHub 默认分支保存 v0.9 文本源码及 v0.9 分片素材归档；本 v0.11 开发分支加入六种性格与两幕互动，但不包含未上传的 v0.10 396 帧独立像素素材。尚未完成 Windows 真机验收，不是安装版。**

一只原创教授猴，在 Windows 桌面上走走停停、眨眼、睡觉、吃香蕉，还会给你整出有前因后果的荒诞事故。默认**安静、离线、无输入监听、不抢鼠标**。可随时暂停、拖走、隐藏或退出。

![13 种动作集合](docs/P03_P12_13_actions.png)

## 🌐 产品介绍页（v0.8 已加入猴山关系、家具、每日任务与故事卡预览）

**[在浏览器打开 site/index.html](site/index.html)**：全新响应式 ProfMonkey 官网式介绍页面，包括大尺寸教授猴互动预览、功能介绍、GIF 故事、隐私声明和下载/安装引导。完全离线，不依赖 CDN。源码候选版菜单提供「🌌 关于 ProfMonkey · 介绍页面」，可以从桌宠打开。页面按钮只模拟网页内互动，不能直接操控桌宠程序。

**v0.7 新增（代码已实现，Windows 仍待验收）：** 🐾 猴山行动方式可选「自由生活 / 跟随猴教授」；猴子可发生轻量横向身体接触，接触后分开、弹开并吐槽；「放置公共香蕉」会在桌面显示一个可点击取消的香蕉道具，多只猴子按性格速度竞速，最先到达者吃掉香蕉。碰撞为简化的 2D 横向接触，不是完整刚体物理；公共香蕉只在 2 只以上、非专注且未暂停/演出时可放置。详见 [v0.7 更新说明](docs/release_notes_v07.md) 与 [Windows 物理互动验收表](docs/v07_colony_physics_windows_checklist.md)。**v0.6 新增（代码已实现，Windows 仍待验收）：** 🎛「猴山管理局」可同时修改 1～6 只的名字与性格（学究猴 / 皮猴 / 困猴）；🗳「猴学委员会」与 🍌「香蕉争夺战」让两只以上的独立猴子同步演出对话与动作，用户拖拽/暂停/专注可中断；🔕 猴山模式的**自动联合短剧默认关闭**；📸「猴山合照」从自己的角色 PNG 离线生成深金主题合照（包含名字和性格），绝不截图桌面。网站「猴山社交」模块可模拟两段短剧的台词。详细见 [v0.6 更新说明](docs/release_notes_v06.md) 和 [猴山合照示例](docs/P06_colony_portrait.png)。

**v0.8 新增（源码候选，Windows GUI 待实测）：** 🤝 本地猴山关系档案：会议会增进好感与信任，碰撞和香蕉争夺会增加竞争值；可以手动安排和解、指定师徒。🛋️ 五种可拖动家具/道具：香蕉树、猴学黑板、蹦床、教授椅、猴山镜子；左键互动，右键收起，最多 8 件。📜 每日轮换三项本地任务，完成当天任务可获得猴学积分。🪪 七种故事主题可生成 1200×800 PNG 故事卡，只合成猴子素材与文案，不截图。新增菜单：「猴山关系档案」「今日猴山任务」「猴山家具与道具」「导出猴山故事卡 PNG」。详细见 [v0.8 更新说明](docs/release_notes_v08.md)。

**v0.5 新增：** 🐒 选择 1～6 只真正独立的桌面猴子。点击「右键猴子 / 托盘图标 → 🐒 猴子数量」，在 6 个数字按钮中选择想养的数量，确认后立即生效，且重启仍保留。每只分别拥有一个透明窗口、动画播放器、身体物理和自主行为；右键某一只会将投喂、表情、短剧作用于那只，模式/暂停/隐藏/退出全体生效。多只猴子不会自动同时整活，只有主猴子会自动触发低频小事故。**v0.5 当时尚未开发多猴物理碰撞；v0.7 已加入轻量横向接触模拟，但不是完整刚体物理**；1～3 只更适合普通笔记本，4～6 只可能增加 CPU/内存占用。介绍页右上角有 ＋／− 演示按钮，它只影响网页预览，不会连接真正的桌宠。说明见 [v0.5 更新记录](docs/release_notes_v05.md)。

**v0.4 功能**：🍌 投喂 + 🏅 7 枚可选本地勋章 + 📚 15/25/45/60 分钟专注时钟 + 💬 自定义猴学语录 + 🏠 一键回家 + 🎲 随机短剧。说明见 [v0.4 更新记录](docs/release_notes_v04.md)。


## 🧪 v0.11 开发分支：六猴人格化学反应

六种性格（学究 / 皮 / 困 / 发明 / 队长 / 社恐）在行为概率和香蕉竞速速度上各有差别。可从「🐾 猴山行动与物理互动 → 🧪 指定两只猴子上演双幕短剧」挑选任意两只空闲猴子，亲自触发 7 种专属组合事件；前提条件及关系优先规则详见 [v0.11 说明](docs/release_notes_v011.md)。两幕剧情只有完整结束后才改变关系；拖动、暂停、专注或切模式会取消。

**[打开六猴像素头像与化学反应离线交互预览](site/chemistry.html)**（网页模拟，不连接程序；网页头像是独立示意图，不代表 v0.10 动画合并）。

核心 PR 自动检查只运行无需素材的 Python 测试与 JS 语法检查；完整 Qt GUI / Windows 穿透 / EXE 仍需人工验收。

## 🐾 v0.9 这次更新：猴山自动偶遇

以前的多猴互动主要需要用户手动触发，现在加入了**可选的自主碰面微短剧**：靠近的两只猴子会根据性格、友情或竞争关系，击掌、打招呼、争论、睡觉或互相捉弄。**自动偶遇默认关闭**；用户必须先切到「猴山模式」再勾选「💬 自动碰面」。还有「🎭 让附近两只猴子互动一次」可直接演示。

为控制干扰，全山偶遇间隔不少于 120 秒，同一对猴子不少于 240 秒；焦点计时、暂停、拖动、联合故事和竞速时自动停止触发。所有判断仅来自程序中猴子的坐标和本地关系，不读取用户操作或桌面内容。网页介绍也增加了离线模拟按钮。详见 [`docs/release_notes_v09.md`](docs/release_notes_v09.md)。

**新增自动化测试：** `tests/test_v09_encounters.py`，Windows 检查单见 [`docs/P09_windows_checklist.md`](docs/P09_windows_checklist.md)。**仍不是 Windows 真机验收通过的正式安装包。**

## 📦 Windows 10 / 11 运行

需先安装 Python 3.12（从 python.org 获取，安装时选 Add Python to PATH）。

1. 解压压缩包，进入 `profmonkey-desktop` 文件夹；**首次双击 `setup_windows.bat`**（会联网安装 PySide6 和 Pillow）。
2. 双击 **`run_windows.bat`**。第一次打开默认在右下角出现猴子；新用户大约 40 秒有机会看到第一段短剧。
3. **养几只？**右键猴子或托盘 →「🐒 猴子数量」→ 点选 1～6 只 →「确认，放猴子出来」。也可以在「⚙ 设置」直接调数量。
4. **给猴子取名、选性格？**右键/托盘 →「🎛 猴山管理局」；填写 1～6 只的名字（最长 12 字）、分别选择学究/皮/困猴性格，点「保存配置」。可以点「保存并开会 / 保存并抢香蕉」马上让大家演短剧；也可从「🤝 猴子之间的互动」菜单播放。
5. **想拍一张猴山集体照？**右键/托盘 →「📸 猴山合照 · 导出 PNG」，选择保存位置后生成只包含程序原创角色的合照。
6. **左键轻戳**产生表情；**按住拖动，快速松手**可以抛掷。**右键**打开全部功能菜单；也可从 Windows 通知栏猴子图标进入菜单。
8. 从「🎭 立即上演」选择香蕉事故、教授黑板、镜像、键盘暴走或坠落；观察后可去「📽 导出猴学短剧 GIF」分享它（只渲染猴子的故事画面，不录屏）。
9. 「📚 陪你专注」可启动 15/25/45/60 分钟安静计时，结束后猴子以本地气泡庆祝；「🍌 投喂一根香蕉」可主动恢复它的精力；「💬 猴学语录」随机展示用户设置的话。勋章统计默认关闭，可在「⚙ 设置」自愿启用并从「🏅 猴学档案」清除。
10. 「⚙ 设置」支持安静/猴山模式、大小、事故频率、音效开关、配色和收藏；默认不开声音和事件记录。
11. 退出：右键猴子 → 「退出 ProfMonkey」，或右键通知区托盘图标 → 「退出 ProfMonkey」。

PowerShell 等价启动方式：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

运行测试：双击 `test_windows.bat`，或执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## 🎮 本次实现内容

| 能力 | 当前状态 |
| --- | --- |
| 13 种原创动作（待机、眨眼、走路、跑步、转身、睡觉、醒来、吃香蕉、滑倒、摔倒、起身、生气、拖动） | ✅ 已编写 + 提供 PNG 帧，Windows 动画效果需确认 |
| 横向移动、边缘掉头、投掷、重力落地、可控频率 | ✅ 逻辑候选 |
| 精力 / 心情 / 好奇 / 调皮的自主选择，种子复现 | ✅ 逻辑候选 |
| 香蕉事故两个结局；点击香蕉皮避免摔倒 | ✅ 剧本候选 |
| 教授黑板可纠错、临时镜像分身、键盘暴走（手动）、坠落短剧 | ✅ 简化视觉候选 |
| 安静/猴山、鼠标追逐或躲避、5 个原创轻音效 | ✅ 简化候选；默认静音 |
| 托盘控制、暂停、设置持久化、4 种领带配色 | ✅ 代码完成 |
| 动作 GIF、完整短剧 GIF、可选本地档案 | ✅ 纯素材导出，不截图 |
| 透明区穿透、焦点不闪、100–200% DPI、多屏、长稳、打包后 EXE | ⏳ Windows 真机/打包实测待做 |
| 主动投喂 / 猴学语录 / 自定义语录（最多 12 条） | ✅ v0.4 新增；Windows GUI 待实测 |
| 15/25/45/60 分钟本地专注、暂停/继续、完成庆祝 | ✅ v0.4 新增；不监测电脑活动 |
| 7 枚可选本地勋章、状态面板、清空本地进度 | ✅ v0.4 新增；默认不记录 |
| 响应式离线产品介绍页与菜单打开 | ✅ v0.4 新增；需要浏览器查看 |
| 真正独立多猴实体、数量按钮（1～6）、即时增删、设置持久化 | ✅ v0.5 代码实现；Windows 多窗口联动待实测 |
| 猴山管理局：各自名字、性格、1～6 只、设置持久化 | ✅ v0.6 源码候选 |
| 联合会议 / 香蕉争夺战同步动作与气泡、可中断 | ✅ v0.6 编排剧情候选 |
| 自动联合短剧（只猴山模式、默认关闭） | ✅ v0.6 代码候选 |
| 生成姓名与性格猴山合照 PNG（不截图） | ✅ v0.6 已生成示例 |
| 轻量横向碰撞、接触分离与碰撞吐槽 | ✅ v0.7 逻辑候选；Windows 多窗口实测待做 |
| 自由生活 / 跟随教授群体行动 | ✅ v0.7 代码候选 |
| 公共香蕉透明道具与性格速度竞速 | ✅ v0.7 代码候选；Windows GUI 待测 |
| 猴山关系档案：好感、竞争、信任、师徒、和解 | ✅ v0.8 核心逻辑；GUI 待 Windows 实测 |
| 可拖动家具：香蕉树、黑板、蹦床、教授椅、镜子 | ✅ v0.8 代码候选；悬浮窗口待 Windows 实测 |
| 每日任务、猴学积分与本地完成天数 | ✅ v0.8 核心逻辑与自动测试 |
| 猴山故事卡 PNG（仅角色素材，不录屏） | ✅ v0.8 核心逻辑与图片输出测试 |
| 完整刚体物理、真实窗口攀爬、自动键盘输入频率检测 | ⬜ 未实现 |

**网站预览截图：**[桌面版](docs/P07_landing_preview.png) · [手机预览](docs/P07_landing_mobile_preview.png)。网页竞速按钮只模拟视觉动作，不控制桌宠。

**v0.8 Windows 验收表：** [关系档案、家具、每日任务、故事卡和回归检查](docs/P08_windows_manual_checklist.md)。

**重要：**不要把“支持某功能的代码已经写好”误读为“Windows 实机已稳定通过”。P01 透明区域点击穿透/角色拖动并存，是整个应用必须优先实际核查的门槛。

## 🍌 第一个猴学短剧

猴子吃香蕉 → 扔皮 → 往回走 → 踩皮滑倒 → 生气甩锅：**“都是你的问题！”**。也有随机安全结局：它发现香蕉皮并主动捡起；而在皮出现时点击它，也可能阻止事故。

GIF 演示（根据自身素材离线生成）：[`docs/P03_P12_banana_demo.gif`](docs/P03_P12_banana_demo.gif)。

## 🧱 程序结构

```text
app.py                        Qt 启动、设置与资源加载
core/animation.py             动作播放器及合法状态转移
core/focus.py                 完全本地单次专注时钟
core/progress.py              自愿开启的本地勋章统计
core/state.py                 决策与心情统计（无 Qt）
core/physics.py               屏幕坐标物理（无 Qt）
core/events.py                因果短剧与可中止事件队列（无 Qt）
core/config.py                安全设置/原子保存（无 Qt）
core/history.py               可选事件档案（无 Qt）
core/export.py                只合成自有图像的 GIF 导出
ui/overlay.py                 每只猴子的独立 Qt 异形透明窗口 / 动作 / 道具 / 互动
ui/colony.py                  多猴数量管理、软碰撞、群体行动、公共香蕉与家具互动
ui/banana_token.py            可点击取消的透明公共香蕉道具窗口
core/colony_physics.py        多猴接触分离、弹开与边界夹取（无 Qt）
ui/colony_dialog.py           6 个按钮选择猴子数量
ui/colony_panel.py            猴山管理面板、各自命名/性格选择
core/social.py                群体短剧时间轴（无 Qt）
core/profiles.py              各角色名字、性格的安全校验
core/portrait.py              纯素材离线生成猴山合照 PNG
core/relationships.py         本地关系记忆、好感/竞争/信任与师徒关系
core/quests.py                每日猴山任务、积分和完成记录
core/story_card.py            纯素材生成故事卡 PNG
ui/furniture.py               可拖动、点击互动的桌面家具
ui/relationship_dialog.py     猴山关系档案面板
ui/quest_dialog.py             每日任务面板
core/colony.py                数量边界和生成位置（可独立测试）
ui/tray.py                    模式、暂停、手动短剧、导出和退出
ui/settings_dialog.py         设置界面
ui/dashboard.py               猴学档案与勋章可视面板
site/index.html               离线响应式产品介绍页面
ui/audio.py                   可选低音量本地音效
assets/monkey/animations/     13 组原始生成动作 PNG
assets/audio/                 5 个原创合成 WAV
assets/icons/                 角色图标
config/defaults.json          设计默认值（实际运行用 core/config.py）
qa: tests/, test_windows.bat   纯 Python & Qt 路径测试
```

## 🧪 多猴专项验收

请参照 [`docs/P05_colony_windows_manual_checklist.md`](docs/P05_colony_windows_manual_checklist.md) 实测 1→3→6→1 只、重启设置保存、各猴独立拖拽，以及焦点/点击穿透。**本容器没有 Windows/PySide6，因此尚不能宣称这些 Qt GUI 路径已通过 Windows 实机验收。**

## 🏗 Windows 打包（仍需真实 Windows 验收）

双击 `build_windows.bat`，理论输出 `dist\ProfMonkeyDesktop\ProfMonkeyDesktop.exe`。请**整个文件夹一起保留**；不能在本环境直接生成 Windows 可执行文件，故暂不提供 EXE。

制作公开 Release 前，需做透明穿透、缩放、多屏、全屏、托盘、2 小时长跑、3 位非开发者测试等质量门禁。详情在 [`docs/P03_P14_delivery_status.md`](docs/P03_P14_delivery_status.md)、[`docs/P01_windows_manual_checklist.md`](docs/P01_windows_manual_checklist.md) 和 [`docs/PRIVACY.md`](docs/PRIVACY.md)。

## ✨ 开发与许可

原创教授猴和 13 组动作帧来自本项目的 SVG / Pillow 可重建图形；参考了经典桌宠的交互机制，**未复制第三方桌宠角色素材**。本项目源码使用仓库 [`LICENSE`](LICENSE) 许可证；请核对依赖各自的许可证。

- `python tools/generate_p02_frames.py` 重建基础 8 套帧（开发者额外安装 `requirements-assets.txt`）。
- `python tools/generate_extra_frames.py` 重建后续 5 套帧（需 Pillow）。
- `python tools/generate_sfx.py` 重建原声音效（标准库即可）。
- `python -m tools.make_integrated_preview` 重建宣传素材，**不采集屏幕**。

🌌 宇宙很大，猴子很忙。


## GitHub 仓库说明（首次同步）
GitHub 当前可浏览全部文本源码和文档，二进制角色素材/音效为了绕过当前上传通道的单文件大小限制，保存在 `releases/v0.9/source.zip.part01` 到 `part20`。克隆此仓库后运行：

```bash
python releases/v0.9/restore.py
```

校验通过后得到 `ProfMonkeyDesktop-v0.9-full.zip`，解压其中 `profmonkey-desktop/` 才是**全部源码 + 角色动画 + 音效 + 网站资源**。ZIP SHA-256：`e474a1ea31293f5ea0dff2d4ffd89b72d473ec9391554acdab6323e7ea794e50`。此方式不是可直接安装的 EXE，需按 Windows 脚本配置 Python / PySide6。当前没有完成 Windows 真机验收。
