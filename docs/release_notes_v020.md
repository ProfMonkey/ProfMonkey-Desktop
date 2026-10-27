# ProfMonkey Desktop v0.20 — 六猴原创造型整体替换

## 目标与交付

用户明确指出过去抖音封面与桌宠都存在“猴子脑袋太大，六只角色像同一张图复制”的问题，并要求**不是改封面，而是把六只猴子的设计全部装进运行代码**。本分支从 v0.19 分支独立产生：`feature/v020-six-monkey-redesign`。

此次制作的是**六张不同且可编辑的原创 SVG 本体**，并接入 Windows 程序运行时整个动画渲染链路、鼠标透明区、变更性格后的即时更新，以及此前的合照/GIF/网页。没有使用知名卡通 IP 的人物设计或直接借图。设计方法借鉴成熟卡通角色的通用原则——明确剪影、头身比例、标志道具、统一世界观与差异化配色。

### 角色美术：对准“大头过大”问题

统一 256×256 画布，底部接触 y≈239–245，头部约 y≈41–152，躯干与四肢约 y≈132–242；旧版近乎头部覆盖身体的形象已经改为看得到胸部、腿、手和脚的完整比例。不是 3D 高精度模型，但在 90–240 像素范围内保持可读性。角色性格与配色：

| 人格键 | 人设 | 识别元素 |
| --- | --- | --- |
| `scholar` | 学究猴 | 花呢学院服、红色领饰、圆眼镜、书 |
| `trickster` | 皮猴 | 深色连帽造型、眨眼、香蕉袋 |
| `sleepy` | 困猴 | 蓝色休闲衣、耳机、眯眼 |
| `inventor` | 发明猴 | 发光护目镜、白色实验服、试管 |
| `captain` | 队长猴 | 红色制服、徽章、队长帽、规划书 |
| `shy` | 社恐猴 | 绿色服装、安静表情、阅读道具 |

具体原画位于 `assets/characters_v020/*.svg`，不仅是宣传图；可通过 SVG 编辑器修改服装、四肢、表情和配饰。每份文件都保留了 `pose`、`eyes-open`、`eyes-closed`、`mouth-smile`、`mouth-open`、`left-leg`、`right-leg`、`left-arm`、`right-arm`、`prop-banana` 等动画挂载点。

### Windows 客户端实际生效

- `core/character_art.py`: 帧姿态生成与安全路径白名单，保留旧 `manifest.json` 的所有 13 类动作、速度与优先级；根据动作名和当前帧做局部关节摆动、表情变化、体态摇晃、香蕉出现、滑倒/起身。
- `ui/character_render.py`: 使用已安装 PySide6 自带 QtSvg **在内存中直接转成 RGBA QPixmap**，无外部 PNG 或网络依赖；产生新的实际像素与 alpha。
- `ui/overlay.py`: 6只猴子分别从自己的 `personality` 渲染，独立缓存动作帧和点击蒙版；配置人格变更后立即清理旧缓存、重绘全新角色。
- `app.py`: 启动初始素材和托盘图标都从新学究猴生成；老版 `assets/monkey/idle.png` 即使缺失也能加载角色。
- `ui/character_gallery.py`: 菜单中的「🎨 六猴全新造型」一次显示6个不同角色，可切换13种实际动画，窗口关闭后自动停止预览定时器。
- `core/character_raster.py`: 导出专用的独立透明 PNG 合成桥接：优先使用开发环境可选 CairoSVG，用户运行环境没有 CairoSVG 时由 PySide6 的 QtSvg 渲染。
- `core/portrait.py`, `core/story_card.py`, `core/export.py`, `ui/tray.py`: 合照、故事卡、动作 GIF、故事 GIF 改用6只专属角色的像素数据；GIF 以当前右键指定的猴子人格为准，不再用单一教授图。
- `build_windows.bat`: 当旧版图标二进制缺失时，不因硬编码 ICO 路径而提前报错；所有文件都随 `--add-data "assets;assets"` 打包。本次没有启动该脚本。
- `site/index.html`: 网页数量切换 1~6 时逐一生成不同 SVG 不再复制同一个 `assets/monkey.png`。
- `site/civic_society.html`: 社会模拟头像从 emoji 升级为6份真实角色资产。
- `site/characters.html`: 新六猴角色馆；移动端响应式布局、光影切换、选择角色查看说明。浏览器展示静态 SVG，动作预览由 Windows Qt 画廊完成。

### 关于像素画和抖音封面

v0.20 是**原创矢量卡通方案**。它能够直接放入现有软件，且单套角色不需要手绘13套 PNG；不应将其宣传为“已经完成 396 帧独立像素动画”或“已经和先前的高精度 3D 抖音封面完全一致”。封面属于风格概念图；实际游戏素材以这六张独立 SVG 为准。

### 测试现状及本地命令

新增：

- `tests/test_v020_six_mascots.py`：XML 合法性、6份不同资源、13类动作逐帧 XML 可解析、路径拒绝、网页引用、可选离线 CairoSVG 出图、原生合照/故事卡输出。
- `tests/test_qt_v020_characters.py`：可选 QtSvg 无头环境：六个独立像素形象、6真实桌宠实例、切换人格之后清除缓存、13动画画廊展示。

**尚未在 GitHub Actions 运行，也没有 Windows 真机 GUI 验收。** 可以在用户本机运行：

```bat
set QT_QPA_PLATFORM=offscreen
.venv\Scripts\python.exe -m pytest -q tests/test_v020_six_mascots.py tests/test_qt_v020_characters.py
```

可先运行 `python -m pytest -q tests/test_v020_six_mascots.py`。默认依赖仍为 `PySide6>=6.7,<7` 和 `Pillow>=10,<13`；首次设置环境请使用 `setup_windows.bat`。QtSvg 是 PySide6 组件，CairoSVG 非运行必需。

**承诺边界：** 源码已接入角色生成及所有主要周边；任何未通过的新增测试、Windows 透明窗口/多显示器与性能问题，均应在真正运行后验收；不应把本分支标记成正式 Windows Release。

**仓库管理：** 本次只更新 `feature/v020-six-monkey-redesign`；不修改主分支、不开 PR、不触发或消耗 GitHub Actions。提交均带 `[skip ci]`。
