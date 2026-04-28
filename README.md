# 英文 → 繁體中文 輸入法解碼器 (ㄅㄆㄇ)

> **30 秒看懂**：你打字時忘了切回注音，整段中文變成 `rup wu0 wu0 fu4 5p cl3` 這種英文亂碼？選取那段，按 **Win + Shift + Z**，原地變回「**今天天氣真好**」。

```
rup wu0 wu0 fu4 5p cl3!   ← 你選取的英文亂碼
       ↓ Win+Shift+Z
今天天氣真好！               ← 原地替換完成
```

線上的「[注音解碼器](https://www.toolskk.com/zhuyin-decode)」（toolskk / vexed.me / IGLOW）只能複製貼上，每次都要開瀏覽器。這是**桌面熱鍵版本**，跨應用程式（Word / VS Code / LINE / Outlook / Discord ...）通用，89-92% 準確度。

---

## 安裝（4 步驟，3 分鐘）

### 系統需求

- **Windows 10 / 11**
- **Python 3.10 或更新**（[python.org 下載](https://www.python.org/downloads/)）
- **AutoHotkey v2**：
  - Win 11 或新 Win 10：`winget install AutoHotkey.AutoHotkey`
  - 較舊版 Win 10：[autohotkey.com/v2/](https://www.autohotkey.com/v2/) 下載安裝程式

### 安裝步驟

打開 PowerShell（不是 cmd 也不是 git-bash），照下面執行：

```powershell
# 1. 下載專案
git clone https://github.com/yian524/zhuyin-decoder.git
cd zhuyin-decoder

# 2. 建立虛擬環境並安裝依賴
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 3. 試跑一次（第一次會自動下載 4MB 的 CC-CEDICT 字典到 ~/.cache/zhuyin-decoder/）
.venv\Scripts\python bopo_fix.py "rup wu0 wu0 fu4 5p cl3!"
# 預期看到：今天天氣真好！

# 4. 啟動熱鍵服務（雙擊資料夾裡的 bopo-fix.ahk）
#    成功時：Windows 工作列右下角出現綠色 H 圖示 + "bopo-fix loaded" 通知
```

### 開機自動啟動（一次設定，永久生效）

按 **Win + R** → 輸入 `shell:startup` → Enter，把 `bopo-fix.ahk` 的**捷徑**（不是檔案本身）拖進那個資料夾。下次開機就會自動載入。

---

## 使用範例

按熱鍵的步驟：**選取那段亂碼 → 按 Win+Shift+Z → 自動替換**。

| 你正在用的軟體 | 怎麼選取亂碼 | 結果 |
|---|---|---|
| LINE / Discord / Telegram | 滑鼠拖曳選取 | 替換後可以直接送出 |
| Outlook / Gmail | 滑鼠拖曳選取（其他段不受影響）| 中段亂碼修好，前後段保持原狀 |
| Word / Google Docs | 滑鼠拖曳，或用 `Shift + 方向鍵` 微調選取 | 直接替換 |
| VS Code / Notepad++ | `Home` → `Shift + End` 選整行 | 註解 / commit message 救回來 |
| 命令列（不需熱鍵）| 直接打 CLI：`bopo-fix.cmd "rup wu0..."` | 印出還原結果 |

> ⚠️ 跨**遠端桌面 / 虛擬機**時，模擬 Ctrl+C/V 不一定可靠，建議改用 CLI 模式。

---

## 為什麼準確度只有 ~90%？

這個工具是**字典查表 + 頻率排名**，不是有上下文理解能力的語言模型：

| 情境 | 準確度 |
|---|---|
| 完整詞彙命中（教授/碩士/研究/實驗/資料/分析）| ~100% |
| 一般敘述句 | 89-92% |
| 同音字無上下文（是/事、和/合、新/心） | 60-80%（看頻率猜）|

要破 95% 需要真正的 LM（local LLM 或 Claude API），那是另一個工程。

---

## 客製化：教引擎你的常用詞

如果你某個詞反覆轉錯，有兩種解法：

### 方式 A：手動加詞（最簡單，1 分鐘）

打開 repo 裡的 **`thesis_phrase_overrides.py`**（檔名雖然叫 thesis 但**任何詞都能加**，不限學術），加上「Bopomofo → 中文」對應：

```python
THESIS_PHRASES = {
    ...
    "ㄒㄧㄣㄒㄩㄝˋㄍㄨㄢˇ": "心血管",   # 醫學常用詞
    "ㄐㄧˋㄒㄩˋ": "繼續",              # 你常打錯的
    "ㄗˋㄉㄨㄥˋㄐㄧㄚˋㄕˇ": "自動駕駛",  # 你領域的詞
}
```

刪掉快取讓新詞生效：

```powershell
Remove-Item ~/.cache/zhuyin-decoder/reverse_dicts.pkl
```

### 方式 B：餵自己的文章自動學詞（適合大量文本）

如果你有大量繁體中文 `.md` / `.txt` 檔（部落格 / 筆記 / 論文），讓工具自動分析常用詞：

```powershell
# 從你的文件目錄挖出常用 2-4 字詞 (出現 ≥ 30 次的)
.venv\Scripts\python tests\build_phrase_overrides.py --corpus "C:\路徑\到\你的文件目錄"

# 套用
Remove-Item ~/.cache/zhuyin-decoder/reverse_dicts.pkl
```

下次按熱鍵就會用你的個人化詞庫。

---

## 故障排除

| 症狀 | 原因 | 解法 |
|---|---|---|
| 跳出 `bopo-fix.cmd not found` 對話框 | AHK 找不到 CLI 程式 | 確認 `bopo-fix.cmd` 跟 `bopo-fix.ahk` 在**同個資料夾** |
| 第一次跑時看到 `CC-CEDICT download failed` | 沒網路 / 公司防火牆擋 | 工具仍可用（~88% 準確度）；之後有網路再跑一次 CLI 觸發下載 |
| 按 Win+Shift+Z 完全沒反應 | AHK 沒在跑 | 雙擊 `bopo-fix.ahk`，確認工作列右下角有**綠色 H 圖示** |
| 替換後游標跑掉 / 選取消失 | Ctrl+V 後焦點變化 | 正常現象，重新點一下輸入框即可 |
| 跨遠端桌面 (RDP) / 虛擬機失效 | 程式化複製貼上在 RDP 不可靠 | 改用 CLI：`bopo-fix.cmd "..."` 然後手動貼 |

---

## 已知限制

- 只支援**大千**鍵盤配置（Microsoft 注音 IME 的預設）
- 同音字偶爾選錯（沒上下文模型解不掉）
- 中英混排時可能誤判 `,` `.` 是標點還是注音 ㄝ/ㄡ — 用前後字 heuristic 處理，覆蓋 ~95% 場景
- 變體字偏好可能跟你預期不同（裏/裡、着/著）

---

<details>
<summary>📐 技術細節（給 contributor / 想 fork 的人）</summary>

### 特性

- **大千 (Microsoft Bopomofo) 鍵盤配置**，鍵碼對照來自 [libchewing](https://github.com/chewing/libchewing) 上游 source
- **170k+ 詞語料庫**：CC-CEDICT 122k + pypinyin 47k + 自動學詞
- **頻率排名挑同音字**：Top-200 中研院/教育部公開頻率表加權
- **OpenCC s2twp 規範化**（消除簡體混入）
- **離線執行**：CC-CEDICT 第一次自動下載 4MB 字典後完全離線
- **~370ms 一次按鍵**（人類感知為即時，pickle 快取後）

### 架構

```
[使用者選取亂碼] → [AutoHotkey 熱鍵 #+z]
        ↓ Ctrl+C 抓進剪貼簿
[layouts.py] 大千鍵盤映射 (libchewing-aligned)
[chewing_wrapper.py] 反向查表 + 頻率排名 + OpenCC + 詞庫
[punct.py] 半形→全形標點
        ↓ 寫回剪貼簿 + Ctrl+V
[原地替換完成]
```

### 測試

```powershell
# 單元 + e2e tests (150 個)
.venv\Scripts\python -m pytest tests\ --ignore=tests\fuzz_thesis.py -v

# 任意語料庫的 fuzz 測試
.venv\Scripts\python tests\fuzz_thesis.py --root "C:\path\to\your-text-folder" --samples 100
```

500 樣本 fuzz（5 種 random seed × 100 樣本）：**89-92% 準確度**。

### 為什麼一個檔案叫 `thesis_phrase_overrides.py`

歷史包袱 — 第一個用 case 是還原作者的論文亂碼。**任何領域的詞都能加進去**（醫學、法律、工程、行銷、ㄎㄧㄤ 文 ...），檔名只是名稱不影響功能。

</details>

---

## Built on

- [libchewing](https://github.com/chewing/libchewing) — 大千鍵盤配置 source of truth
- [pypinyin](https://github.com/mozillazg/python-pinyin) — 漢字→注音字典基礎
- [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) — 繁體詞語料庫
- [OpenCC](https://github.com/BYVoid/OpenCC) — 簡體→繁體規範化
- [AutoHotkey](https://www.autohotkey.com/) — Windows 全域熱鍵

## 授權

MIT — 詳見 [LICENSE](LICENSE)
