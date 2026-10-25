# 本次交付的测试与事实记录

- **交付阶段**：P00 + P01 **原型**，并非 v0.1 完整功能。
- **执行环境**：Linux 自动化容器，而非 Windows 10/11。
- **当前局限**：PySide6 无法在此环境从 PyPI 获取，因此暂时不能启动 Qt GUI，也无法以实际鼠标验证 Windows 的跨进程点击穿透、DPI、焦点和托盘。
- **静态与纯 Python 测试**：运行结果详见随包构建记录。
- **需要用户真机检查**：严格依 `P01_windows_manual_checklist.md`，记录具体机器与结果。
- **GitHub 发布状态**：此包是本地 Git 仓库，尚未推送 GitHub（没有目标远程仓库）。

## 2026-10-25 本地自动化结果

- `python -m compileall -q app.py ui core adapters tests`：通过。
- `python -m pytest -q`：**11 passed, 1 skipped**（跳过的是需要 PySide6 的 Qt GUI 形状测试，因当前容器未安装该包）。
- 图标 PNG / ICO 与原始 SVG：已生成并可打开；图像四角透明。
- PySide6 安装尝试：失败，运行环境网络名称解析不可用，故未声称 Windows / Qt 界面执行成功。

## P02 候选动画增量记录

- 源自原创 P01 SVG，以 CairoSVG + Pillow 生成了 8 个序列共 44 PNG 帧；存在独立可重建脚本。
- 添加 Qt 无依赖的动画播放器状态机、优先级、动作收尾、镜像和可暂停能力，附固定脚本展示。
- GUI 动画、动态遮罩和全程托盘退出已经写入代码，但当前运行环境无 PySide6，**没有 Windows 实测证明**。
- 切勿将分支上的功能视为 P01/P02 质量门禁通过。

## P02 本次实际测试结果（2026-10-25）

- `python -m compileall -q .`：**通过**。
- `python -m pytest -q`：**25 passed, 2 skipped**。跳过了 2 个 PySide6/Qt 界面测试（本环境缺 PySide6）。
- `git diff --check`：**通过**。
- 8 套共 44 帧 256×256 原创 PNG 已通过文件级图像解码和 Alpha 校验。
- Git 分支：`feature/p02-animation`；`main` 保持 P01 版本，没有将未验收动画作为稳定版。

## 2026-10-25 整合候选版增量测试

- 独立分支：`feature/integrated-v03`，并非稳定发布分支。
- `python -m compileall -q app.py core ui tools adapters tests`：通过。
- `python -m pytest -q`：**37 passed, 2 skipped**；跳过的是依赖 PySide6 的 Qt 界面测试。
- `git diff --check`：通过。
- `manifest.json` 现有 **13 种动作、66 张 256×256 RGBA 动画帧**，已进行文件级解码核查。
- 自合成轻音效：5 个 WAV；动作和故事 GIF 已由 Pillow 离线输出。
- 严格区分“实现代码、离线通过测试”与“在真实 Windows 桌面验收”。**本轮没有 Windows 现场录屏、没有 Windows exe、没有 2 小时/4 小时稳定运行结果**。
