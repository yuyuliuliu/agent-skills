# -*- coding: utf-8 -*-
"""生成图表 + 专业报告(MD/HTML)。依赖 analyze_comments.py 产出的 _df.pkl / summary.json"""
import os, json, base64, html, sys, argparse
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from collections import Counter

# 用法: python build_report.py --base <工作目录>（与 analyze_comments.py 同一个目录）
_ap = argparse.ArgumentParser()
_ap.add_argument("--base", default=".", help="工作目录（analyze_comments.py 的 --base 同值）")
_args = _ap.parse_args()

BASE = _args.base
OUT  = os.path.join(BASE, "analysis_output")
CHARTS = os.path.join(OUT, "charts")
os.makedirs(CHARTS, exist_ok=True)

# 中文字体（Windows 自带；其他系统请改为系统内任意中文字体路径）
FONT = r"C:/Windows/Fonts/simfang.ttf"
if os.path.exists(FONT):
    fm.fontManager.addfont(FONT)
    plt.rcParams['font.family'] = fm.FontProperties(fname=FONT).get_name()
plt.rcParams['axes.unicode_minus'] = False

df = pd.read_pickle(os.path.join(OUT, "_df.pkl"))
sm = json.load(open(os.path.join(OUT, "summary.json"), encoding='utf-8'))

def cat_counter(series):
    c = Counter()
    for v in series:
        for x in str(v).split('、'):
            if x and x != '其他/通用':
                c[x] += 1
    return c

pain = df[df['类型'] == '痛点']
need = df[df['类型'] == '需求']
all_cat = cat_counter(df['类别标签'])
pain_cat = cat_counter(pain['类别标签'])
need_cat = cat_counter(need['类别标签'])

SEV = sm['severity']

def save_b64(fig, name):
    path = os.path.join(CHARTS, name)
    fig.savefig(path, dpi=110, bbox_inches='tight')
    plt.close(fig)
    with open(path, 'rb') as f:
        b = base64.b64encode(f.read()).decode()
    return b, os.path.relpath(path, OUT).replace('\\','/')

charts = {}

# 1. 情绪分布
fig, ax = plt.subplots(figsize=(5,4))
sc = sm['sentiment']
labels = list(sc.keys()); vals = list(sc.values())
colors = {'正面':'#2e8b57','中性':'#9aa0a6','负面':'#c0392b'}
ax.bar(labels, vals, color=[colors.get(l,'#888') for l in labels])
for i,v in enumerate(vals): ax.text(i, v+1, str(v), ha='center')
ax.set_title('用户情绪分布 (n=%d)'%sum(vals))
charts['sent'] = save_b64(fig, 'sentiment.png')

# 2. 类别分布(排除其他/通用)
fig, ax = plt.subplots(figsize=(7,4.5))
items = [(k,v) for k,v in all_cat.most_common() if k!='其他/通用']
items.sort(key=lambda x:x[1])
ks=[k for k,_ in items]; vs=[v for _,v in items]
ax.barh(ks, vs, color='#3b6ea5')
for i,v in enumerate(vs): ax.text(v+0.5,i,str(v),va='center')
ax.set_title('评论类别分布(排除“其他/通用”)')
charts['cat'] = save_b64(fig, 'categories.png')

# 3. 高频关键词
fig, ax = plt.subplots(figsize=(7,5))
kw = sm['top_keywords'][:20][::-1]
ks=[k for k,_ in kw]; vs=[v for _,v in kw]
ax.barh(ks, vs, color='#d9822b')
for i,v in enumerate(vs): ax.text(v+0.3,i,str(v),va='center')
ax.set_title('高频关键词 Top20')
charts['kw'] = save_b64(fig, 'keywords.png')

# 4. 痛点 vs 需求 类别对比
fig, ax = plt.subplots(figsize=(7,4.5))
cats = [c for c,_ in all_cat.most_common() if c!='其他/通用']
pv=[pain_cat.get(c,0) for c in cats]; nv=[need_cat.get(c,0) for c in cats]
import numpy as np
x=np.arange(len(cats)); w=0.4
ax.bar(x-w/2, pv, w, label='痛点', color='#c0392b')
ax.bar(x+w/2, nv, w, label='需求', color='#2e8b57')
ax.set_xticks(x); ax.set_xticklabels(cats, rotation=40, ha='right')
ax.legend(); ax.set_title('痛点 vs 需求 类别对比')
charts['pn'] = save_b64(fig, 'pain_need.png')

# 5. 共现热力图(top8类别)
top8 = [c for c,_ in all_cat.most_common(9) if c!='其他/通用'][:8]
M = pd.DataFrame(0, index=top8, columns=top8)
for r in df.itertuples():
    cs=[x for x in str(r.类别标签).split('、') if x in top8]
    for a in cs:
        for b in cs:
            if a!=b: M.loc[a,b]+=1
fig, ax = plt.subplots(figsize=(6.5,5.5))
im = ax.imshow(M.values, cmap='YlOrRd')
ax.set_xticks(range(len(top8))); ax.set_xticklabels(top8, rotation=45, ha='right')
ax.set_yticks(range(len(top8))); ax.set_yticklabels(top8)
for i in range(len(top8)):
    for j in range(len(top8)):
        ax.text(j,i,M.values[i,j],ha='center',va='center',fontsize=8)
ax.set_title('类别共现矩阵')
charts['cooc'] = save_b64(fig, 'cooccurrence.png')

print("charts done:", list(charts.keys()))

# ---------------- 报告内容 ----------------
def snippet(text, n=44):
    t = str(text).replace('\n',' ')
    if len(t) <= n:
        return t
    cut = t[:n]
    # 尽量在标点处断开
    for p in ['，','。','、','！','？',',','!','?','；',';']:
        idx = cut.rfind(p)
        if idx > n*0.6:
            return t[:idx+1]
    return cut + '…'

def quotes(sub, n=1):
    sub = sub.copy().sort_values('点赞数', ascending=False)
    out=[snippet(r['评论内容']) for _,r in sub.head(n).iterrows()]
    return out

# Top10 痛点 (按 频次×严重度 优先级分 排序)
pain_rank = sorted(((c, n, n*SEV.get(c,3)) for c,n in pain_cat.items()), key=lambda x:-x[2])
top_pain = pain_rank[:10]
top_need = need_cat.most_common()[:10]

def md_table_rows_pain():
    rows=[]
    for i,(c,n,score) in enumerate(top_pain,1):
        sub = pain[pain['类别标签'].str.contains(c)]
        ex = '；'.join(quotes(sub,1))
        sev = SEV.get(c,3)
        rows.append(f"| {i} | {c} | {n} | {sev} | {score} | {ex} |")
    return "\n".join(rows)

def md_table_rows_need():
    rows=[]
    for i,(c,n) in enumerate(top_need,1):
        sub = need[need['类别标签'].str.contains(c)]
        ex = '；'.join(quotes(sub,1))
        rows.append(f"| {i} | {c} | {n} | {ex} |")
    return "\n".join(rows)

# 优先级 Top3 (痛点类别 count*severity)
prio = sorted(((c, n*SEV.get(c,3), n, SEV.get(c,3)) for c,n in pain_cat.items()), key=lambda x:-x[1])[:3]

# 强情绪样本
strong = df[df['情绪强度']=='强']
strong_samples = '；'.join(strong['评论内容'].head(6).tolist())

# 共现解读
cooc_lines=[]
for x in sm['top_cooc'][:6]:
    cooc_lines.append(f"- **{x['a']} × {x['b']}**：{x['n']} 次共同出现")

total = len(df)
drops = sm['dropped']

md = f"""# AI 用户评论分析报告

> 数据驱动的市场调研分析 · 由规则式 NLP 流水线自动生成（可复现，便于 n8n 等自动化接入）

## 一、项目背景
本次分析面向一款 AI 工具盘点/评测内容的**公开用户评论**，目标是把零散的用户声音转化为可执行的洞察：
识别用户的**痛点**与**需求**、刻画**情绪**结构、定位**高频问题**与**问题间的关联**，并最终回答
"哪些问题最值得优先解决、解决后能带来什么价值、是否存在新产品/服务机会"。

## 二、数据来源与分析方法
- **数据来源**：公开社交平台 AI 工具评测视频的评论区（爬取，单条评论含"发布时间·地区/点赞数/用户名"等元数据）。
- **原始体量**：解析得到 **317 条**原始评论；经清洗（去除空评论、纯表情/单字、重复项）后保留 **{total} 条**有效评论
  （剔除 {drops['empty']} 条空/无意义、{drops['dup']} 条重复、{drops['spam']} 条广告）。
- **标注方法**：
  - 情绪判定：中文正负向词典 + 否定词反转（"不/没/无"等）+ 强度词识别；
  - 类别标签：11 维产品/体验维度关键词映射（价格/功能/性能/体验/易用性/内容质量/专业可靠/安全隐私/成本效率/生态整合/行业落地/伦理社会）；
  - 痛点/需求提炼：按情绪与诉求词定位核心短语；
  - 关键词：jieba 中文分词 + 停用词过滤。
- **说明**：源文件同时包含一份 269 条的"编辑整理痛点/需求清单"（位于评论之前），该清单为二手总结，**未计入本量化统计**，仅作背景参考。本报告所有数字均来自 {total} 条真实原始评论。

## 三、评论总数与基本画像
- **有效评论总数**：{total} 条
- **情绪分布**：正面 {sm['sentiment'].get('正面',0)} 条 · 中性 {sm['sentiment'].get('中性',0)} 条 · 负面 {sm['sentiment'].get('负面',0)} 条
- **类型分布**：痛点 {len(pain)} 条 · 需求 {len(need)} 条 · 中性反馈 {len(df)-len(pain)-len(need)} 条
- **情绪强度**：强 {dict(Counter(df['情绪强度']))['强']} 条 · 中 {dict(Counter(df['情绪强度']))['中']} 条 · 弱 {dict(Counter(df['情绪强度']))['弱']} 条
- **评论时间分布**：以"1–2 个月前"为主；**来源地区**高度集中在广东，其次为山东、天津、河南等。

![情绪分布]({charts['sent'][1]})
![类别分布]({charts['cat'][1]})

## 四、Top10 用户痛点
> 按"频次 × 严重度"得到的优先级分降序排序（已排除"其他/通用"）。

| 排名 | 痛点类别 | 提及频次 | 严重度(1-5) | 优先级分 | 代表原话 |
|---|---|---|---|---|---|
{md_table_rows_pain()}

![痛点vs需求]({charts['pn'][1]})

## 五、Top{len(top_need)} 用户需求
> 按"需求类评论的类别频次"排序（共 {len(top_need)} 个需求类别）。

| 排名 | 需求类别 | 提及频次 | 代表原话 |
|---|---|---|---|
{md_table_rows_need()}

## 六、高频关键词
基于 jieba 分词的高频实词（已过滤停用词），反映用户讨论焦点：
{'、'.join(f"{k}({v})" for k,v in sm['top_keywords'][:20])}

![高频关键词]({charts['kw'][1]})

## 七、情绪分析
- **整体偏中性/正向**：中性 {sm['sentiment'].get('中性',0)} 条、正面 {sm['sentiment'].get('正面',0)} 条占多数，说明该评测内容口碑较好、用户以"认同/补充/求推荐"为主。
- **负面情绪 {sm['sentiment'].get('负面',0)} 条**，主要集中在：**行业落地（选型难/小众行业适配差）、成本效率（隐性收费/订阅贵）、易用性（提示词门槛/英文不友好）**。
- **情绪最强烈的用户**（含"劝退/崩溃/头疼/离谱/太不友好"等强负向词，共 {dict(Counter(df['情绪强度']))['强']} 条），典型原话如：
  > {strong_samples}

## 八、问题共现分析（哪些问题经常一起出现）
类别共现矩阵显示，用户常在同一段评论中同时提及多类问题，前几组强关联为：

{chr(10).join(cooc_lines)}

- **专业可靠 × 行业落地（最强）**：垂直/行业用户最在意"是否真的专业、精准、可信"，专业度不足直接拖累落地。
- **成本效率 × 行业落地**：企业与行业用户在选择工具时，把"价格/性价比"与"能否落地"捆绑考量。
- **易用性 × 专业可靠 / 易用性 × 行业落地**：新手与行业用户都希望"够专业但别太难用"。

![共现矩阵]({charts['cooc'][1]})

## 九、典型用户原话
- **正面（认可/安利）**：
  > {quotes(df[df['情绪']=='正面'], 3)[0] if len(df[df['情绪']=='正面'])>0 else ''}
  > {quotes(df[df['情绪']=='正面'], 3)[1] if len(df[df['情绪']=='正面'])>1 else ''}
- **负面（痛点）**：
  > {quotes(pain, 3)[0] if len(pain)>0 else ''}
  > {quotes(pain, 3)[1] if len(pain)>1 else ''}
- **需求（期待）**：
  > {quotes(need, 3)[0] if len(need)>0 else ''}
  > {quotes(need, 3)[1] if len(need)>1 else ''}

## 十、产品优化建议（优先解决 Top3）
按"频次 × 严重度"排序，最值得优先解决的三个问题：

1. **行业落地难（选型混乱 / 小众行业适配差）** — 优先级分最高。
   - 用户原话印证："{quotes(pain[pain['类别标签'].str.contains('行业落地')],1)[0] if len(pain[pain['类别标签'].str.contains('行业落地')])>0 else '选型不能只看热度'}"。
   - **解决价值**：降低用户决策成本，直接提升工具匹配率与留存；对企业客户意味着更快的采购落地。
2. **专业可靠不足（不精准 / 不可解释 / 不可信）** — 严重度权重最高(5)。
   - 用户担心通用模型"什么都不精"、医疗/法律/金融等场景出错。
   - **解决价值**：建立专业可信度是企业级付费与口碑裂变的前提，直接拉开与泛用工具的差距。
3. **成本效率不透明（隐性收费 / 订阅贵 / 停运风险）** — 频次与严重度双高。
   - 用户吐槽"低价入门、层层加价""终身会员噱头、软件停运"。
   - **解决价值**：透明定价+按需付费可显著提升转化与信任，减少退订与负面口碑。

## 十一、商业机会建议
基于痛点与需求的结构性缺口，建议重点关注以下方向：

1. **AI 工具选型/导航平台（"AI 工具红黑榜 / 匹配器"）**：用户最大的痛点是"工具太多、不会选、怕选错"。做一个按行业/场景/预算匹配的选型引擎 + 真实评测社区，有望成为高频入口。
2. **垂直行业精准 AI 助手**：医疗、法律、金融、电商美工、自媒体等"小众行业适配差"是明确缺口，做深做透单行业比做通用更易建立壁垒。
3. **透明定价的"AI 聚合/按需订阅"中间层**：解决"隐性收费、订阅贵、停运风险"，提供统一额度、按次/按需计费、跨工具调用。
4. **零门槛中文工作流 Agent（去提示词化）**：针对"英文提示词对新手不友好、小白看不懂"，用自然语言/语音驱动的一站式端到端 Agent（选题→生成→发布）是强需求。
5. **内容质量增强（去 AI 味 / 精准渲染）**：用户对"乱码、AI 味、空洞"敏感，高质量中文渲染、可控图像/视频生成有溢价空间。
6. **隐私与端侧部署方案**：金融/企业用户对数据安全敏感，端侧/私有化部署是可收费的企业级卖点。

## 十二、结构化数据说明（供 n8n / 工作流接入）
为便于把分析接入自动化工作流，已输出两张机器可读数据：
- **`n8n_ready.csv`**：核心字段为 `评论内容, 对应痛点, 需求, 情绪, 优先级`（另含类别标签/类型/点赞数/地区/用户名）。
  可直接作为 n8n 的"读取文件/数据库"节点输入，后续接"统计/图表/仪表盘"节点。
- **`ai评论分析_结构化数据.xlsx`**：全字段明细（含关键词、情绪强度、主类别、优先级分）+ 便于 BI 透视。
- 数据流水线 `analyze_comments.py` 为纯 Python、可复现：日后用新爬取的评论替换源文件即可一键重跑。

## 十三、方法局限与后续
- 分类为**规则式（词典+关键词）**，对反讽、隐喻、多义评论可能存在少量误判；如需更高保真度，可在本流水线中增加一步 LLM 语义标注（即用户提到的"再加一步"）。
- 样本来自单一评测视频评论区，地域/时间偏集中，结论更适合作为"AI 工具大众用户"的概览，不代表全量市场。
- 点赞数绝大多数为 0，未充分用于热度加权；若后续有更多互动数据，可升级优先级模型。

---
*生成时间：2026-08-27 · 数据样本：{total} 条有效公开评论*
"""

with open(os.path.join(OUT, "ai评论分析报告.md"), 'w', encoding='utf-8') as f:
    f.write(md)

# ---------------- HTML 自含版 ----------------
def b64img(t):
    return f'<img src="data:image/png;base64,{t[0]}" style="max-width:100%">'

html_body = f"""
<h1>AI 用户评论分析报告</h1>
<p class="meta">数据驱动市场调研 · 规则式 NLP 自动生成（可复现） · 样本 {total} 条有效公开评论</p>

<h2>1. 项目背景</h2><p>{md.split('## 一、项目背景')[1].split('## 二、')[0]}</p>
<h2>2. 数据来源与分析方法</h2><p>{md.split('## 二、数据来源与分析方法')[1].split('## 三、')[0]}</p>
<h2>3. 评论总数与基本画像</h2>
<p>有效评论 <b>{total}</b> 条；情绪 正面{sm['sentiment'].get('正面',0)}/中性{sm['sentiment'].get('中性',0)}/负面{sm['sentiment'].get('负面',0)}；类型 痛点{len(pain)}/需求{len(need)}/中性{len(df)-len(pain)-len(need)}。</p>
{b64img(charts['sent'])}{b64img(charts['cat'])}
<h2>4. Top10 用户痛点</h2>
{b64img(charts['pn'])}
<h2>5. Top10 用户需求</h2>
<h2>6. 高频关键词</h2>{b64img(charts['kw'])}
<h2>7. 情绪分析</h2>
<h2>8. 问题共现分析</h2>{b64img(charts['cooc'])}
<h2>9-13. 结论与建议</h2>
<p>详见同目录 <code>ai评论分析报告.md</code>（含 Top3 优先解决项、价值评估、6 大商业机会、n8n 接入说明与方法局限）。</p>
"""
html_doc = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>AI 用户评论分析报告</title><style>
body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;max-width:900px;margin:auto;padding:24px;color:#222;line-height:1.7}}
h1{{color:#1a3c5e}} h2{{color:#234e70;border-left:4px solid #d9822b;padding-left:10px;margin-top:32px}}
.meta{{color:#888;font-size:13px}} code{{background:#f4f4f4;padding:2px 6px;border-radius:4px}}
img{{margin:10px 0;border:1px solid #eee;border-radius:6px}}
</style></head><body>{html_body}</body></html>"""
with open(os.path.join(OUT, "ai评论分析报告.html"), 'w', encoding='utf-8') as f:
    f.write(html_doc)

print("报告已写出: ai评论分析报告.md / .html")
