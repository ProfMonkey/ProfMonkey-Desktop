# ProfMonkey Desktop 🐒

> 你的电脑里，住进了一只不太正常的猴子。

**项目状态：v0.9 开发候选版；不是 Windows 稳定发行版。**

ProfMonkey Desktop 是一个离线 Windows 桌面猴子项目，使用 Python / PySide6。支持 1–6 只独立猴子、拖动、可控的虚构猴学剧情、猴子性格与关系、本地小任务，以及 v0.9 新增的**可选自动碰面微短剧**。

## 代码交付状态
当前 GitHub 仓库首先同步 v0.9 的自主偶遇决策模块、自动测试和演示页面。**此 GitHub 仓库暂非完整可运行 Windows 工程，不能直接按此 README 安装**。完整项目（包括 UI、图片、音效、脚本、开发历史）已作为 ChatGPT 对话中的 `ProfMonkey_Desktop_v0.9_...` ZIP 交付，等待在可正常 Git 推送的环境将完整工程同步到仓库。在完整源码同步和 Windows 实机测试之前，不发布虚假的 EXE/Release。

### 本版新增
- 自主偶遇可选择开启（默认关闭，仅猴山模式、至少两只猴）。
- 好朋友击掌、死对头争论、困猴打盹、皮猴恶作剧、普通问候。
- 每对猴子至少 240 秒冷却、全体至少 120 秒冷却；用户专注、暂停、拖动或其他短剧期间不触发。
- 手动一键演示，不必开启自动模式。
- 不访问键盘输入、鼠标内容、剪贴板、浏览器或桌面画面。

### 已同步的可独立运行测试
```bash
python -m pytest -q tests/test_v09_encounters.py
```
测试需要同时取得 `core/encounters.py`、`core/config.py` 等完整依赖，当前这里只能验证独立的 `EncounterDirector` 用例。

## 本地完整源码同步（已有 ZIP 的贡献者）
在 Windows 解压完整 ZIP 后，进入 `profmonkey-desktop`：

```powershell
git remote add origin https://github.com/ProfMonkey/ProfMonkey-Desktop.git
git fetch origin
# 建议确认 GitHub 远程的代码与本地目录差异，避免覆盖他人提交
git status
```

**请勿直接强制推送覆盖仓库**。完整代码及素材需要在有 GitHub 网络连通和已配置写入权限的本机环境以正常 commit / pull request 同步。

## 隐私与限制
项目离线、默认不监控输入、不录屏。当前未经过 Windows 10/11 透明窗口穿透、DPI、后台稳定性及 EXE 验收。

🌌 宇宙很大，猴子很忙。
