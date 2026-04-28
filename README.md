# 英文 → 繁體中文 輸入法解碼器（ㄅㄆㄇ）

> **打字打到一半，發現整段中文都變英文亂碼？**
> 選取那段亂碼 → 按熱鍵 → 自動還原為繁體中文。

```
rup wu0 wu0 fu4 5p cl3!   ←  選取（這段是注音忘記切換時打出來的英文亂碼）
       ↓ Win+Shift+Z
今天天氣真好！               ←  原地替換完成
```

## 這是什麼

你用注音輸入法打字，但忘記從英文模式切回中文模式 → 整段中文都變成英文亂碼。這個工具讓你**選取那段亂碼，按一個熱鍵，就自動還原成繁體中文**，不用整段刪掉重打。

跟 [toolskk](https://www.toolskk.com/zhuyin-decode) / [vexed.me](https://vexed.me/tool/zhuyin) / [IGLOW](https://iglowapp.com/bopomofo-decoder/) 這類**線上注音解碼器**做同樣的事，差別在：
- ✅ **離線、本地執行**，不用打開瀏覽器、不用複製貼上
- ✅ **熱鍵一鍵還原**，原地替換選取的文字
- ✅ **Windows 任何輸入框都能用**（LINE、Word、VS Code、Outlook、瀏覽器⋯）
- ✅ **完全免費、開源**

## 系統需求

- Windows 10 或 11
- Python 3.10 以上（[python.org 下載](https://www.python.org/downloads/)）
- AutoHotkey v2（下面安裝步驟會說明）

## 安裝（4 步驟，約 3 分鐘）

開啟 PowerShell，依序執行：

```powershell
# 步驟 1：下載專案
git clone https://github.com/yian524/bpmf-decoder.git
cd bpmf-decoder

# 步驟 2：建立 Python 虛擬環境並裝套件
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 步驟 3：測試轉換功能（第一次跑會自動下載 4MB 中文詞庫）
.venv\Scripts\python bopo_fix.py "rup wu0 wu0 fu4 5p cl3!"
# 應該看到輸出：今天天氣真好！

# 步驟 4：安裝 AutoHotkey v2（熱鍵需要它）
winget install AutoHotkey.AutoHotkey
# 沒有 winget 的話直接到 https://www.autohotkey.com/v2/ 下載安裝程式
```

裝好 AutoHotkey 後，**雙擊 `bpmf-decoder.ahk`** 啟動熱鍵，托盤會出現綠色 H 圖示 + 「bpmf-decoder loaded」通知，表示 `Win + Shift + Z` 熱鍵已生效。

### 開機自動啟動（建議）

不想每次開機都手動雙擊 `.ahk` 的話：

1. 按 `Win + R`，輸入 `shell:startup` → Enter
2. 把 `bpmf-decoder.ahk` 的捷徑（按右鍵 → 複製 → 貼到那個資料夾）

下次開機就會自動載入熱鍵。

## 怎麼用

### 主要用法：熱鍵還原

1. 用滑鼠或鍵盤**選取**那段亂碼
2. 按 **`Win + Shift + Z`**
3. 約 0.4 秒後原地替換成繁體中文

### 備用用法：命令列

如果要批次處理或寫進別的工具：

```powershell
# 直接傳字串
bpmf-decoder.cmd "rup wu0 wu0 fu4 5p cl3!"

# 從檔案讀、寫到另一個檔案
bpmf-decoder.cmd --input-file 亂碼.txt --output-file 還原.txt
```

## 使用情境

| 情境 | 怎麼救 |
|---|---|
| LINE / Discord 聊天打到一半變英文亂碼 | 反白那段 → `Win + Shift + Z` |
| Outlook / Gmail 寫長 email 中段亂掉 | 拖曳選取那段（前後正常的中文不會被影響）→ `Win + Shift + Z` |
| Word 寫文件 / 報告 | 反白那段 → `Win + Shift + Z` |
| VS Code / 寫程式註解 | 反白那一行（用滑鼠拖曳，或按 Home 接著 Shift + End）→ `Win + Shift + Z` |
| 從別人那裡複製貼來的亂碼訊息 | 全選 (`Ctrl + A`) → `Win + Shift + Z` |

## 準確度說明

實測 500 個從台灣論文真實文本抽出的隨機片段：**約 89-92% 字元正確率**。

**會 100% 正確的情況**：
- 常用詞彙（教授、碩士、論文、實驗、評估、特徵、研究方法⋯）— 因為直接整詞查表

**可能會挑錯字的情況**：
- 同音字無上下文時（例如：是/事/視 都讀 ㄕˋ；和/合 都讀 ㄏㄜˊ；新/心 都讀 ㄒㄧㄣ）
- 工具會挑「最常用」那個，但碰到罕見用法（例如名字裡的「事」）會挑錯，得手動改一兩個字

簡單說：**幫你救回 90% 的字，剩下 1-2 個錯字手動修一下**。

## 進階：讓工具更懂你常打的詞

如果你發現某個詞反覆轉錯（例如你寫醫療文章常用「心血管」但工具一直給「新血管」），有兩個解法：

### 方法 A：手動加進詞庫

打開專案資料夾裡的 `thesis_phrase_overrides.py`，新增一行：

```python
THESIS_PHRASES = {
    ...
    "ㄒㄧㄣㄒㄩㄝˋㄍㄨㄢˇ": "心血管",   # 加上你要的詞
    "ㄐㄧˋㄒㄩˋ": "繼續",
}
```

> 注音字串怎麼來？打開 PowerShell 跑：
> ```powershell
> .venv\Scripts\python -c "from pypinyin import pinyin, Style; print(''.join(p[0] for p in pinyin('心血管', style=Style.BOPOMOFO)))"
> ```

存檔後刪掉快取讓新詞生效：
```powershell
Remove-Item ~/.cache/bopo-fix/reverse_dicts.pkl
```

### 方法 B：自動掃描你的文件學詞

如果你有大量繁體中文文本（部落格、筆記、論文、工作文件⋯），讓工具自動掃描挖出常用詞：

```powershell
# 從你的文件目錄挖常用詞（出現 30 次以上）
.venv\Scripts\python tests\build_phrase_overrides.py --corpus C:\Users\你的帳號\Documents\我的文件夾

# 同樣方式挖單字偏好
.venv\Scripts\python tests\build_char_overrides.py --corpus C:\Users\你的帳號\Documents\我的文件夾

# 套用
Remove-Item ~/.cache/bopo-fix/reverse_dicts.pkl
```

下次按熱鍵就會用你個人化的詞庫，準確度會更高。

## 故障排除

| 問題 | 原因 | 解法 |
|---|---|---|
| 跳出「**bpmf-decoder.cmd not found**」對話框 | AutoHotkey 找不到指令程式 | 確認 `bpmf-decoder.cmd` 跟 `bpmf-decoder.ahk` 在同一個資料夾 |
| 第一次跑時看到「CC-CEDICT download failed」 | 沒網路、防火牆擋 | 工具仍可用（準確度約掉 3%）；之後有網路再跑一次 CLI 會自動補下載 |
| 按 `Win + Shift + Z` 沒反應 | AutoHotkey 沒啟動 | 雙擊 `bpmf-decoder.ahk`，確認托盤有綠 H 圖示 |
| 替換完游標跑掉 / 選取消失 | AutoHotkey 模擬複製貼上後焦點變化 | 正常現象，重新點一下輸入框繼續打字即可 |
| 在遠端桌面 / 虛擬機裡用沒效 | 程式化 Ctrl+C/V 在 RDP 不可靠 | 改用命令列：`bpmf-decoder.cmd "..."` 然後手動貼上 |
| 想換熱鍵 | `Win+Shift+Z` 跟你別的設定衝突 | 編輯 `bpmf-decoder.ahk` 第一行 `#+z::` 改成你要的（語法見 [AutoHotkey 文件](https://www.autohotkey.com/docs/v2/Hotkeys.htm)）|

## 已知限制

- **只支援微軟注音標準鍵盤配置**（也就是 Windows 內建注音輸入法的預設配置）— 倚天 / Hsu / IBM 等其他注音鍵盤之後會加
- **同音字偶爾選錯**（如 是/事、和/合、新/心）— 沒上下文模型解不掉，得手動修
- **變體字可能挑你不想要的**（裏/裡、着/著）— 都是合法繁體，但兩岸 / 不同教科書習慣不同
- **`,` 跟 `.` 偶爾被當成 ㄝ / ㄡ**（這兩個鍵在注音鍵盤是音節用、英文鍵盤是標點）— 用「前一字判斷」處理 95% 場景，剩 5% 邊界情況可能誤判

## 為什麼準確度只有 ~90%，不到 100%？

這個工具是**字典查表 + 字頻排名**，不是真正的語言模型（沒有 AI 看上下文）。對「教授」、「碩士」、「論文」這種完整詞彙 100% 準確；但碰到「是 vs 事 vs 視」這種同音字，沒上下文就只能挑最常用的那個。

要破 95% 需要真正的 AI 看句子上下文（例如本地小型 LLM、或 Claude API 後處理），那是另一個工程，未來版本可能加。

## 技術內部運作（給好奇的人）

```
[你選取的亂碼] → [AutoHotkey 抓進剪貼簿]
                ↓
[轉換引擎，純 Python，跑你機器上]
   1. 英文鍵碼 → 注音符號（依鍵盤對照表）
   2. 注音字串 → 中文（先查詞庫 17 萬筆，再查單字）
   3. 自動把混進來的簡體字濾成繁體（用 OpenCC）
   4. 把英文標點 ! ? , . 改成全形！？，。
                ↓
[寫回剪貼簿，模擬 Ctrl+V 貼上]
```

詞庫來源（共 ~17 萬筆）：
- **CC-CEDICT** 12 萬筆（國際公開漢英字典，自動下載）
- **pypinyin** 內建 4.7 萬筆常用詞
- 你自己掃描出來的 N 筆（用上面方法 B）

字頻來源：中央研究院 + 教育部公開的繁體中文最常用 500 字頻率表（消除挑到冷僻字的問題）。

## 一般使用者用不到（給開發者）

```powershell
# 跑單元測試（150 個）
.venv\Scripts\python -m pytest tests\ --ignore=tests\fuzz_thesis.py -v

# 對任意文字資料夾跑隨機測試
.venv\Scripts\python tests\fuzz_thesis.py --root C:\path\to\your-text-folder --samples 100
```

## 用了哪些開源工具

- [libchewing](https://github.com/chewing/libchewing) — 微軟注音標準鍵盤配置的對照表
- [pypinyin](https://github.com/mozillazg/python-pinyin) — 漢字 ↔ 注音對照
- [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) — 漢英詞典
- [OpenCC](https://github.com/BYVoid/OpenCC) — 簡體 → 繁體規範化
- [AutoHotkey](https://www.autohotkey.com/) — Windows 全域熱鍵

## 授權

MIT — 詳見 [LICENSE](LICENSE)，可自由商用、修改、再散布。
