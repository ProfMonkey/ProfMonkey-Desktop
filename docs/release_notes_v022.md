# ProfMonkey Desktop v0.22 — 教授猴原型六猴统一重绘

## 本轮目标
六只猴子共用已选定教授猴的棕色身体、奶油色口鼻、粗黑描边、圆耳朵、统一四肢比例与卷尾巴；角色只用少量配件区分，不再是六套互不相关的卡通。

## 六只角色
| 顺序 | 显示名 | 内部兼容键 | 标志配件 |
|---|---|---|---|
| 1 | 教授猴 | `scholar` | 毕业帽、教鞭、红色书本 |
| 2 | 探险猴 | `captain` | 小背包、红围巾、探险杖 |
| 3 | 编程猴 | `inventor` | 蓝色耳机、小电脑 |
| 4 | 摸鱼猴 | `sleepy` | 蓝色睡帽、困倦眼神 |
| 5 | 干饭猴 | `trickster` | 黄色围兜、香蕉 |
| 6 | 酷帅猴 | `shy` | 深色连帽衫、墨镜、金色项链 |

## 程序改动
- 六个 SVG 原画直接替换进 `assets/characters_v020/`，保持透明背景和统一 256×256 画布。
- 保留动画引擎所需的 pose、四肢、眨眼、张嘴和香蕉动作标记，13 类动作继续由 QtSvg 渲染。
- 旧人格内部键不变，已有设置、剧情和猴际关系记录无需迁移；默认显示名与顺序同步新角色表。
- 像素模式改为对同一 SVG 动画帧进行最近邻缩放，避免切换到风格不同的旧精灵表。
- `setup_windows.bat` 在安装后验证 Pillow 与 QtSvg；如果检测到损坏的 Pillow 导入，会强制重装 Pillow 并再次验证，针对 `cannot import name '_imaging' from PIL`。
- 更新离线角色设计馆、README 与回归测试。

## 本地验收
```bat
setup_windows.bat
run_windows.bat
```

无窗口核心测试：
```bat
.venv\Scripts\python.exe -m pytest -q tests/test_v020_six_mascots.py tests/test_v021_secrets.py tests/test_v022_character_prototype.py
```

本轮未使用 GitHub Actions，也没有声称 Windows 真机已经实测通过；需在用户电脑确认透明窗口、托盘、多屏幕和长时间运行情况。

## Git 管理
仅提交到 `feature/v022-professor-style-six-monkeys`；不修改 `main`、不创建 PR、不使用 GitHub Actions。
