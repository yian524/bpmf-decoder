# bopo-fix · 注音輸入法忘記切換 一鍵還原

打字時忘記切換輸入法 → 整段中文變英文亂碼？選取那段亂碼，按熱鍵，原地替換成繁體中文。

```
rup wu0 wu0 fu4 5p cl3!   ←  選取
       ↓ Win+Shift+Z
今天天氣真好！               ←  替換完成
```

**沒有現成 OSS 工具能做到這件事**：網路上的線上解碼器 (toolskk / vexed.me) 只能複製貼上，AHK 的 KBLAutoSwitch 只切輸入法不還原內容，libchewing 沒 Windows binary。所以做了這個。

## 特性

- **大千 (Microsoft Bopomofo) 鍵盤配置**，鍵碼對照來自 libchewing 上游 source
- **170k+ 詞語料庫**（CC-CEDICT 122k + pypinyin 47k + 你自己語料挖出來的高頻詞）
- **頻率排名挑同音字**（Top-200 中研院/教育部公開頻率表加權，避免冷僻字）
- **OpenCC s2twp 規範化**（消滅簡體混入）
- **Windows 全域熱鍵** (Win+Shift+Z) via AutoHotkey v2
- **離線執行**（CC-CEDICT 第一次跑時自動下載一次 4MB 字典，之後完全離線）
- **89-92% 準確度** 在真實繁體中文文本上（500 樣本 fuzz 測試）
- **~370ms 一次按鍵**（首次建字典 ~5s，pickle 快取後極快）

## 系統需求

- Windows 10 / 11
- Python 3.10+（[python.org](https://www.python.org/downloads/) 下載）
- AutoHotkey v2 (`winget install AutoHotkey.AutoHotkey`)

## 安裝（4 步驟，約 3 分鐘）

```powershell
# 1. clone repo
git clone https://github.com/yian524/bopo-fix.git
cd bopo-fix

# 2. 建虛擬環境並裝依賴
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 3. 試跑 CLI 確認轉換引擎能用
#    （第一次跑時會自動從 mdbg.net 下載 CC-CEDICT 字典 4MB 到 ~/.cache/bopo-fix/）
.venv\Scripts\python bopo_fix.py "rup wu0 wu0 fu4 5p cl3!"
# 預期輸出: 今天天氣真好！

# 4. 啟動熱鍵 daemon (AutoHotkey v2)
#    雙擊 bopo-fix.ahk 即可，托盤會出現綠 H 圖示 + "bopo-fix loaded" 通知
```

### 開機自動啟動（建議）

按 `Win + R` → 輸入 `shell:startup` → Enter，把 `bopo-fix.ahk` 的捷徑放進那個資料夾。下次開機自動載入熱鍵。

## 使用

| 用法 | 範例 |
|---|---|
| 熱鍵（最常用） | 選取亂碼 → `Win+Shift+Z` → 原地替換 |
| CLI（測試 / 整合用） | `bopo-fix.cmd "rup wu0 wu0 fu4 5p cl3!"` |
| Stdin pipe | `echo "rup" \| bopo-fix.cmd` |
| 檔案 IO | `bopo-fix.cmd --input-file in.txt --output-file out.txt` |

> CLI 入口是 `bopo-fix.cmd`（在 repo 根目錄），不需放進 PATH——AHK 腳本會用相對路徑找它。想在 cmd / PowerShell 直接打 `bopo-fix` 的話，可以把 repo 目錄加進 PATH，或把 `bopo-fix.cmd` 複製到 PATH 裡的某個目錄。

## 使用情境

| 情境 | 操作 |
|---|---|
| LINE / Discord 聊天打到一半發現亂碼 | 選取那段 → Win+Shift+Z |
| Outlook / Gmail 寫長 email 中段是亂碼 | 滑鼠拖選那段 → Win+Shift+Z（其他段不受影響）|
| VS Code 寫 Python 註解 / git commit message | Ctrl+L 選整行 → Win+Shift+Z |
| Word 寫論文 | 反白那段 → Win+Shift+Z |

## 為什麼準確度只有 ~90%？

這個工具是**字典查表 + 頻率排名**，不是真正的語言模型。對「教授/碩士/論文/實驗/評估/特徵」這種常用詞 100% 準（因為直接整詞查表命中），但對同音字（是/事/視、和/合、新/心）就只能挑頻率最高的，沒上下文理解能力。

剩下 10% 錯誤幾乎全是同音字消歧。要破 95% 需要真正的 LM（libchewing 自編、本地 LLM 或 Claude API），那是另一個工程。

## 客製化（讓引擎更懂你的領域）

### 加入你常用的詞（手動）

編輯 `thesis_phrase_overrides.py`，加上「Bopomofo → 詞」對應：

```python
THESIS_PHRASES = {
    ...
    "ㄒㄧㄣㄒㄩㄝˋㄍㄨㄢˇ": "心血管",  # 醫學常用詞
    "ㄐㄧˋㄒㄩˋ": "繼續",            # 你常打錯的詞
}
```

刪除 cache 後生效：

```powershell
Remove-Item ~/.cache/bopo-fix/reverse_dicts.pkl
```

### 從你自己的文章自動學詞（自動）

如果你有大量繁體中文文本（論文 / 部落格 / 筆記），可以讓工具掃描自動產生詞表：

```powershell
# 從你的文件目錄挖出常用 2-4 字詞 (≥30 次)
.venv\Scripts\python tests\build_phrase_overrides.py --corpus C:\Users\YOU\Documents\my-papers

# 從你的文件目錄挖出單字偏好
.venv\Scripts\python tests\build_char_overrides.py --corpus C:\Users\YOU\Documents\my-papers

# 套用
Remove-Item ~/.cache/bopo-fix/reverse_dicts.pkl
```

兩個腳本會自動分析、改寫對應的 override 檔案。下次按熱鍵就生效。

## 架構

```
[使用者選取亂碼] → [AutoHotkey 熱鍵 #+z]
        ↓ Ctrl+C 抓進剪貼簿
[clipboard: "rup wu0 wu0 fu4 5p cl3!"]
        ↓ Python CLI (subprocess via bopo-fix.cmd)
[layouts.py]   ← 大千鍵盤映射 (libchewing 對齊)
[chewing_wrapper.py]  ← 反向查表 + 頻率排名 + OpenCC + 詞庫
[punct.py]     ← 半形→全形標點
        ↓ 寫回剪貼簿
[clipboard: "今天天氣真好！"]
        ↓ Ctrl+V
[原地替換]
```

兩層分離（AHK 只管 IO + 熱鍵；Python 管純轉換邏輯）→ Python 部分能用 pytest 完整覆蓋，AHK 那層極薄。

## 測試

```powershell
# 單元 + e2e tests (150 個)
.venv\Scripts\python -m pytest tests\ --ignore=tests\fuzz_thesis.py -v

# 任意語料庫的 fuzz 測試
.venv\Scripts\python tests\fuzz_thesis.py --root C:\path\to\your-text-folder --samples 100
```

## 故障排除

| 症狀 | 原因 | 解法 |
|---|---|---|
| `bopo-fix.cmd not found` 對話框 | AHK 找不到 CLI shim | 確認 `bopo-fix.cmd` 跟 `bopo-fix.ahk` 在同個目錄；或設環境變數 `BOPO_FIX_CMD` 指向 cmd 路徑 |
| 第一次跑時印 `CC-CEDICT download failed` | 沒網路 / 防火牆擋 | 工具仍可用（~88% 準確度）；之後有網路時手動再跑一次 CLI 觸發下載 |
| 按 Win+Shift+Z 沒反應 | AHK daemon 沒起來 | 雙擊 `bopo-fix.ahk` 確認托盤有綠 H 圖示 |
| 替換後游標跑掉、選取消失 | AHK 模擬 Ctrl+V 後焦點變化 | 正常，重新點一下輸入框即可 |
| 跨遠端桌面 / VM 失效 | 程式化 Ctrl+C/V 在 RDP 不可靠 | 改用 CLI：`bopo-fix.cmd "..."` 然後手動貼 |

## 已知限制

- 只支援大千 (Microsoft Bopomofo IME 預設) 鍵盤配置（v2 計畫加倚天/Hsu/IBM）
- 同音字偶爾選錯（如 是/事、和/合）— 沒上下文模型解不掉
- 變體字可能挑你不想要的（裏/裡、着/著）
- `,` `.` 在句尾被當標點 vs 在 ㄝ/ㄡ 的角色 — 用前一字 context heuristic 處理，覆蓋 ~95% 場景

## 致謝

- [libchewing](https://github.com/chewing/libchewing) — 大千鍵盤配置 source of truth
- [pypinyin](https://github.com/mozillazg/python-pinyin) — 漢字→注音字典基礎
- [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) — 繁體詞語料庫
- [OpenCC](https://github.com/BYVoid/OpenCC) — 簡體→繁體規範化
- [AutoHotkey](https://www.autohotkey.com/) — Windows 全域熱鍵

## 授權

MIT — 詳見 [LICENSE](LICENSE)
