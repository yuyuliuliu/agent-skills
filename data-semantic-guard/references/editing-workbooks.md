# Editing Workbooks（openpyxl 模式 / 文件锁 / 用户手改 diff）

> 需要**往 Excel 里写注释、加批注、改名、或核对用户手改**时，先读本文件拿现成代码模式，别从零写。

## OpenPyXL 注释与改名模式

```python
from openpyxl import load_workbook
from openpyxl.comments import Comment

wb = load_workbook(path, data_only=False)
ws = wb["Sheet1"]

# Append a clarification to the top note cell
ws["A1"] = (ws["A1"].value or "") + "；补充说明：『红/蓝/黑』为纸记天数轮次记号，并非染色颜色。"

# Attach a hover comment to the ambiguous label's first cell
ws["B5"].comment = Comment(
    "红/蓝/黑 = 纸记天数轮次记号，不是染的颜色。\n"
    "纸本台账每天轮流标一个记号，只为方便数天数、对账用。",
    "Agent")

# Rename a misleading header
ws["C3"] = "轮次记号"

wb.save(path)
```

## Excel 文件锁处理（Step 4）

openpyxl `save()` 在目标 xlsx 被 Excel 打开时（Windows 独占锁）会报 `PermissionError`。

- 失败发生在**拿到文件句柄之前**，原文件不会损坏（用 `stat` 验证：大小/mtime 不变）。
- 变通：生成 `-预览版` 副本到别的文件名 → 让用户关 Excel → 写回原文件或直接交付预览版 → 事后清理预览副本。
- 改任何文件前先备份：`cp file.xlsx .bak_<原因>_<日期>/`。

## Diffing a user's manual edits（用户手改核对）

用户手改过生成的表时，必须**精确知道**他们改了什么，再决定审查或重建。**绝不把生成器直接重跑盖掉他们的手改。**

1. **先备份他们的版本**（`.bak_<原因>_<日期>/`）——他们的手改从此是真源。
2. 生成器重跑到**临时路径**（改生成器的 `OUT` 常量；**不要**对真实文件跑）：
   ```python
   src = open("build.py", encoding="utf-8").read()
   src = src.replace('OUT = r"<real path>"', 'OUT = r"<temp path>"')
   ```
3. 逐格 diff，用可读的列名映射，让输出可审查：
   ```python
   for r in range(1, max(wa.max_row, wb.max_row) + 1):
       for c in range(1, max(wa.max_column, wb.max_column) + 1):
           va = wa.cell(r, c).value if r <= wa.max_row and c <= wa.max_column else "<无此格>"
           vb = wb.cell(r, c).value if r <= wb.max_row and c <= wb.max_column else "<无此格>"
           if va != vb:
               print(f"[r{r}] {COL_NAMES[c-1]}: {va!r} -> {vb!r}")
   ```
4. 逐条分类每处改动：
   - **OCR 修正**（信任它）
   - **语义重判**（问：这暗示别处也要改吗？）
   - **格式损坏**（静默修）
   - **过期备注**（改名后旧「待核」文字还挂在别的列 → 清掉）

最后这一类最阴：用户修了值、没修描述旧值的备注。任何改名后都要 **grep 兄弟备注列里的旧字符串**。

参考实现：`scripts/add_antimisread_annotation.py`（加注释 + 批注 + 可选改名 + 先备份 + 用预览版扛文件锁的参数化示例）。
