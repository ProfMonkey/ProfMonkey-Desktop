# ProfMonkey Desktop — 离线产品介绍页

打开 `index.html` 即可在现代浏览器中浏览，不需要安装、不需要账号，也不依赖 CDN。

- `assets/` 包含本项目介绍页使用的角色图、动作拼图、合照示意和短剧 GIF。
- 页面里的猴子数量、开会、抢香蕉和公共香蕉竞速按钮只演示网页内动画/台词，不会控制真实桌宠。
- 桌宠应用需要单独下载完整工程，在 Windows 10/11 上安装 Python 3.12 和依赖后运行。
- 主介绍页包含历代功能入口；当前新增 `civic_society.html` 作为 v0.19 独立离线自主社会演示。此前 `society.html` 是 v0.13 猴山议会演示，请勿覆盖。所有网页模拟都不读取桌宠真实存档。透明窗口点击穿透、多屏、缩放和长稳测试仍需 Windows 真机验收。


## 🎨 v0.20 全新六猴形象

- [六猴角色设计馆](characters.html)：展示六个**真实 SVG 游戏资产**的头身比例、外套、配饰、角色性格。网页只是静态展示；Windows 程序另外有 QtSvg 实时动画版本。
- 首页数量从 1 增至 6 只时，会分别显示 `../assets/characters_v020/{scholar,trickster,sleepy,inventor,captain,shy}.svg`，不再复制同一个教授形象。
- [猴山自主社会](civic_society.html)：六个社会成员的头像改为新的 SVG 角色。
- 把 `site/` 文件夹与 `assets/characters_v020/` 一起保留，才可以**完全离线**看到所有角色。请不要只把 `characters.html` 单文件移动到别处。
