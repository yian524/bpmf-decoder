# bopo-fix · 注音輸入法忘記切換 一鍵還原

打字時忘記切換輸入法 → 整段中文變英文亂碼？選取那段亂碼，按熱鍵，原地替換成繁體中文。

```
rup wu0 wu0 fu4 5p cl3!   ←  選取
       ↓ Win+Shift+Z
今天天氣真好！               ←  替換完成
```

**沒有現成 OSS 工具能做到這件事**。網路上的線上解碼器 (toolskk / vexed.me) 只能複製貼上，AHK 的 KBLAutoSwitch 只切輸入法不還原內容，libchewing 沒 Windows binary。所以做了這個。

## 特性

- **大千 (Microsoft Bopomofo) 鍵盤配置**，鍵碼對照來自 libchewing 上游 source
- **122k+ 詞語料庫**（CC-CEDICT 自動下載 + pypinyin 47k + 你自己論文挖出來的高頻詞）
- **頻率排名挑同音字**（Top-200 中研院/教育部公開頻率表加權，避免冷僻字）
- **OpenCC s2twp 規範化**（消滅簡體混入）
- **Windows 全域熱鍵** (Win+Shift+Z) via AutoHotkey v2
- **離線 100%**，本地查表，~370ms 一次按鍵
- **89-92% 準確度** 在真實繁體中文文本上（500 樣本 fuzz 測試）

## 系統需求

- Windows 10/11
- Python 3.10+
- AutoHotkey v2 (`winget install AutoHotkey.AutoHotkey`)

## 安裝

```bash
git clone https://github.com/<your-username>/bopo-fix.git
cd bopo-fix

# 建虛擬環境並安裝依賴
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 第一次跑時會自動下載 CC-CEDICT (約 4MB) 到 ~/.cache/bopo-fix/
.venv\Scripts\python bopo_fix.py "rup wu0 wu0 fu4 5p cl3!"
# → 今天天氣真好！
```

### 啟用熱鍵

1. 把 `bopo-fix.cmd` (cli shim) 放進 `~/.claude/bin/` 或任何 PATH 路徑
2. 雙擊 `bopo-fix.ahk` → 托盤出現綠 H 圖示
3. 開機自動啟動：把 `bopo-fix.ahk` 捷徑放進 `shell:startup`

## 使用

| 用法 | 範例 |
|---|---|
| 熱鍵（最常用） | 選取亂碼 → `Win+Shift+Z` → 原地替換 |
| CLI（測試用） | `bopo-fix "rup wu0 wu0 fu4 5p cl3!"` |
| Pipe | `echo "rup" \| bopo-fix` |
| 檔案 IO | `bopo-fix --input-file in.txt --output-file out.txt` |

## 為什麼準確度只有 ~90%？

這個工具是**字典查表 + 頻率排名**，不是真正的語言模型。對「教授/碩士/論文/實驗/評估/特徵」這種常用詞 100% 準（因為直接整詞查表命中），但對同音字（是/事/視、和/合、新/心）就只能挑頻率最高的，沒上下文理解能力。

剩下 10% 錯誤幾乎全是同音字消歧。要破 95% 需要真正的 LM（libchewing 自編、本地 LLM 或 Claude API），那是另一個工程。

## 客製化

### 加入你常用的詞

編輯 `chewing_wrapper.py` 的 `PREFERRED_CHAR` dict，加上你想要的「Bopomofo → 字/詞」對應：

```python
PREFERRED_CHAR = {
    ...
    "ㄒㄧㄣㄒㄩㄝˋㄍㄨㄢˇ": "心血管",  # 醫學常用詞
    "ㄐㄧˋㄒㄩˋ": "繼續",           # 你常打錯的詞
}
```

刪除 cache 後生效：

```bash
rm ~/.cache/bopo-fix/reverse_dicts.pkl
```

### 從你自己的文章自動學詞

如果你有大量繁體中文文本（論文 / 部落格 / 筆記），可以讓工具掃描自動產生詞表：

```bash
# 從你的文件目錄挖出常用 2-4 字詞
.venv\Scripts\python tests/build_phrase_overrides.py --corpus ~/Documents/my-papers

# 從你的文件目錄挖出單字偏好
.venv\Scripts\python tests/build_char_overrides.py --corpus ~/Documents/my-papers
```

兩個腳本會自動分析、改寫對應的 override 檔案。下次按熱鍵就生效（記得刪 `~/.cache/bopo-fix/reverse_dicts.pkl`）。

## 架構

```
[使用者選取亂碼] → [AutoHotkey 熱鍵 #+z]
        ↓ Ctrl+C 抓進剪貼簿
[clipboard: "rup wu0 wu0 fu4 5p cl3!"]
        ↓ Python CLI (subprocess)
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

```bash
.venv\Scripts\python -m pytest tests/ --ignore=tests/fuzz_thesis.py -v   # 150 個 unit + e2e tests
.venv\Scripts\python tests/fuzz_thesis.py --root ~/your-text-folder --samples 100   # 真實文本 fuzz
```

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
