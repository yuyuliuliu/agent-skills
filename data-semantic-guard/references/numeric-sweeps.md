# Numeric & Matrix Sweeps（数字/日期/矩阵扫描细则与代码）

> 在做任何 SUM、月度汇总、占比计算之前，先按本文件扫描。**文本数字会被 SUM 静默跳过**——无报错、无警告，只有错误的总数。这坑过一次，少算了 ¥30,765。

## 金额列扫描（Step 2.5）

在信任任何合计前，先扫金额列：

```python
tot = 0; bad = []
for r in range(2, ws.max_row + 1):
    v = ws.cell(r, AMOUNT_COL).value
    if isinstance(v, (int, float)): tot += v
    elif v not in (None, ""): bad.append((r, v))   # ← text like '25765+5000'
print(tot, bad)
```

遇到文本数字时的规则：

- **绝不直接覆盖。** 用户可能是故意写的拆分式（如 `25765+5000` = 工资 + 另一项）。
- 转成数值总和，**并把原拆分保留**——挪进备注列，写法如 `原记 25765+5000（工资25765+另项5000），已合并为数值 30765`。
- 转换后重算总数，把**新旧两个数都给用户**看差额。

## 同期必扫（与金额列一趟做完）

- **日期列**：混着 `str` / int 序列号 / `None` 会破坏排序和月度分组。统一成一种文本格式（序列号用 `date(1899,12,30) + timedelta(days=n)` 转）。
- **序号 / 索引缺口**：新追加的行常缺 ID 和来源引用——回填，或来源不明就标记（**不要猜**它来自哪张照片）。

## 日期矩阵列扫描（Step 2.7，off-by-one 会杀总数）

当日/月数据以**矩阵**铺开（行=客户，列=日期）时，列范围是最高频的静默错误点。

```python
# ❌ 错：漏掉最后一列（7月31天 → B..AF 共31列，range(2,33) 才对）
vals = [ws.cell(r, c).value for c in range(2, 32)]
# ✅ 对：先用表头确认列数，再断言
hdr = [ws.cell(1, c).value for c in range(2, ws.max_column + 1)]
assert len(hdr) == 31, f"期望31天，实际{len(hdr)}"
vals = [ws.cell(r, c).value for c in range(2, 2 + len(hdr))]
```

后果实测：漏 1 列 → 当阳染量 6,821.6 被算成 6,556.6 kg（差 265kg），连带单价、占比、回款黑洞结论全错。

铁律：
1. **先读表头数出列数并断言，禁止硬编码列区间。**
2. 行区间同理：用 `while` 或非空判断取到底，不要写死 `range(6,20)`。
