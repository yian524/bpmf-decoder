#Requires AutoHotkey v2.0
;;
;; bopo-fix.ahk — hotkey wrapper for the wrong-IME-layout undo tool.
;;
;; Hotkey:   Win + Shift + Z
;; Action:   Selected English-keys garble → 繁體中文 in place.
;;
;; Implementation notes
;; --------------------
;; - We use temp files (not pipes) for stdin/stdout because the Python
;;   CLI emits UTF-8 to stdout.buffer; AHK's COM-based pipe APIs
;;   (WScript.Shell.Exec / .StdOut.ReadAll) default to ANSI/cp950 on
;;   Windows-Taiwan and would mangle CJK output. FileRead with
;;   "UTF-8" encoding is the lowest-friction way to get clean text.
;; - Clipboard is saved before, restored after, so the user's prior
;;   clipboard contents (text/image/files) survive the operation.
;; - ClipWait timeout 0.3s — long enough for slow apps like browsers
;;   to deliver selection on Ctrl+C, short enough not to feel laggy
;;   when nothing is selected (we abort early in that case).

; A_UserProfile is NOT a built-in in AHK v2 (v2 has A_AppData / A_Temp /
; A_MyDocuments etc. but no UserProfile). Read it from the environment.
CMD := EnvGet("USERPROFILE") . "\.claude\bin\bopo-fix.cmd"

#+z::  ; Win + Shift + Z
{
    static TmpIn := A_Temp . "\bopo-fix-in.txt"
    static TmpOut := A_Temp . "\bopo-fix-out.txt"

    ; Save current clipboard (binary blob — preserves images / files / formats).
    saved := ClipboardAll()
    A_Clipboard := ""
    Send "^c"
    if !ClipWait(0.3) {
        TrayTip "bopo-fix", "請先選取要還原的英文亂碼", 0x10
        A_Clipboard := saved
        return
    }

    garbled := A_Clipboard
    if (Trim(garbled) = "") {
        TrayTip "bopo-fix", "選取為空白", 0x10
        A_Clipboard := saved
        return
    }

    ; Write input as UTF-8 (no BOM) so the Python CLI's stdin reader
    ; sees clean bytes regardless of console codepage.
    try FileDelete TmpIn
    try FileDelete TmpOut
    FileAppend garbled, TmpIn, "UTF-8"

    ; Redirect stdin/stdout via cmd.exe. RunWait + Hide so the spawned
    ; cmd.exe has no visible window. Note: on Win11 + Windows Terminal,
    ; this still works because RunWait uses a hidden console (unlike the
    ; claude-mem case where windowsHide:true was being ignored — that
    ; was a Node.js quirk specific to detached:true. AHK's Run is
    ; different and respects "Hide".)
    ; Avoid `cmd /c "..." < in > out` triple-quoting (which hangs on AHK v2).
    ; Instead pass --input-file / --output-file directly so the Python CLI
    ; reads/writes the temp files without involving cmd.exe redirection.
    cmdline := '"' . CMD . '" --input-file "' . TmpIn . '" --output-file "' . TmpOut . '"'
    RunWait cmdline,, "Hide"

    ; Read recovered Chinese as UTF-8.
    chinese := ""
    try chinese := FileRead(TmpOut, "UTF-8")
    chinese := Trim(chinese, "`r`n")  ; drop trailing newline if any

    try FileDelete TmpIn
    try FileDelete TmpOut

    if (chinese = "") {
        TrayTip "bopo-fix", "轉換失敗（空輸出）", 0x10
        A_Clipboard := saved
        return
    }

    ; Replace selection with the recovered Chinese.
    A_Clipboard := chinese
    if !ClipWait(0.5) {
        TrayTip "bopo-fix", "剪貼簿寫入失敗", 0x10
        A_Clipboard := saved
        return
    }
    Send "^v"

    ; Restore the user's original clipboard after the paste settles.
    Sleep 150
    A_Clipboard := saved
}

;;
;; Tray menu — quick-test command for verifying the install end-to-end
;; without needing to find a window with selectable garbled text.
;;
A_TrayMenu.Add()
A_TrayMenu.Add("bopo-fix: Self-test", BopoFixSelfTest)

BopoFixSelfTest(*)
{
    sample := "rup wu0 wu0 fu4 5p cl3!"
    expected := "今天天氣真好！"
    static TmpIn := A_Temp . "\bopo-fix-selftest-in.txt"
    static TmpOut := A_Temp . "\bopo-fix-selftest-out.txt"

    try FileDelete TmpIn
    try FileDelete TmpOut
    FileAppend sample, TmpIn, "UTF-8"
    ; Avoid `cmd /c "..." < in > out` triple-quoting (which hangs on AHK v2).
    ; Instead pass --input-file / --output-file directly so the Python CLI
    ; reads/writes the temp files without involving cmd.exe redirection.
    cmdline := '"' . CMD . '" --input-file "' . TmpIn . '" --output-file "' . TmpOut . '"'
    RunWait cmdline,, "Hide"

    actual := ""
    try actual := Trim(FileRead(TmpOut, "UTF-8"), "`r`n")

    try FileDelete TmpIn
    try FileDelete TmpOut

    if (actual = expected) {
        TrayTip "bopo-fix self-test: OK", "Input:`n  " . sample . "`nOutput:`n  " . actual, 0x40
    } else {
        TrayTip "bopo-fix self-test: FAIL",
            "Expected:`n  " . expected . "`nGot:`n  " . actual, 0x10
    }
}

TrayTip "bopo-fix loaded", "熱鍵: Win+Shift+Z 將選取的英文亂碼還原為繁體中文", 0x40
