# -*- coding: utf-8 -*-
"""
AI 用户评论分析流水线
输入: 单列评论的 xlsx（Sheet1，列名任意，取第一列）——路径由 --base 参数指定
  - 示例数据: 从社交平台抓取的 ~317 条真实用户原始评论
输出:
  analysis_output/结构化数据.xlsx  (全字段表 + 统计摘要)
  analysis_output/n8n_ready.csv              (评论内容,对应痛点,需求,情绪,优先级...)
  analysis_output/报告.md           (专业报告)
  analysis_output/charts/*.png               (可视化)
方法: 规则式 NLP(词典+关键词), 可复现, 便于后续 n8n 自动化接入。
"""
import os, re, math, json, sys, argparse
from collections import Counter, defaultdict
import pandas as pd

# 用法: python analyze_comments.py --base <你的工作目录>（内含评论 xlsx）
_ap = argparse.ArgumentParser()
_ap.add_argument("--base", default=".", help="工作目录：包含评论 xlsx，输出写到其下 analysis_output/")
_args = _ap.parse_args()

BASE = _args.base
SRC = next((os.path.join(BASE, f) for f in sorted(os.listdir(BASE)) if f.lower().endswith(".xlsx")), None)
if not SRC:
    print("错误: 在", BASE, "下没找到 xlsx 输入文件"); sys.exit(1)
OUT  = os.path.join(BASE, "analysis_output")
CHARTS = os.path.join(OUT, "charts")
os.makedirs(CHARTS, exist_ok=True)

# ---------------------------------------------------------------- 1. 解析原始评论
def load_col(path):
    df = pd.read_excel(path)
    col = df.columns[0]
    raw = df[col].tolist()
    return ['' if (x is None or (isinstance(x, float) and pd.isna(x))) else str(x) for x in raw]

def is_date(v):
    return bool(re.search(r'^(.+?)(前|昨天|刚刚)[·：:]', v))

def parse_comments(s, start=312):
    N = len(s)
    out = []
    i = start
    while i < N:
        v = s[i].strip()
        if is_date(v):
            j = i - 1
            while j >= 0 and s[j].strip().lower() in ('nan', ''):
                j -= 1
            comment = s[j].strip() if j >= 0 else ''
            likes = s[i + 1].strip() if i + 1 < N else ''
            uname = ''
            k = i + 4
            while k < N:
                c = s[k].strip()
                if c.lower() in ('nan', ''):
                    k += 1; continue
                if c in ('分享', '回复') or c.startswith('展开'):
                    k += 1; continue
                if c == '...':
                    break
                if re.fullmatch(r'\d+', c):
                    k += 1; continue
                uname = c
                break
            # 拆分 时间·地区
            m = re.match(r'^(.*?)[·：:](.+)$', v)
            if m:
                ctime, region = m.group(1).strip(), m.group(2).strip()
            else:
                ctime, region = v, ''
            try:
                like_n = int(likes)
            except Exception:
                like_n = 0
            out.append(dict(comment=comment, time=ctime, region=region,
                            likes=like_n, user=uname))
            i = k + 1 if uname else i + 5
        else:
            i += 1
    return out

# ---------------------------------------------------------------- 2. 清洗
SPAM = ['加微信', '私聊', '代写', '引流', '关注我', '领取', '免费送', '加我', '私信',
        '扫码', '公众号', '点击链接', '下单', '优惠', '折扣', '招代理', '加盟']
BOT = re.compile(r'【.+?锐评】|【.+?评】')

def norm(t):
    t = re.sub(r'http\S+', '', t)
    t = re.sub(r'#[^#]+#', '', t)
    t = re.sub(r'@[\w\u4e00-\u9fa5]+', '', t)   # 去掉 @提及
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def is_meaningless(t):
    if len(t) < 3:
        return True
    # 纯标点/表情/符号
    if re.fullmatch(r'[\W_]+', t):
        return True
    if t in ('...', '了！', '了', '。', '！', '？', '回复', '分享'):
        return True
    return False

def clean(comments):
    seen = set()
    cleaned = []
    dropped = dict(empty=0, spam=0, dup=0, kept=0)
    for c in comments:
        t = norm(c['comment'])
        if is_meaningless(t):
            dropped['empty'] += 1
            continue
        if any(w in t for w in SPAM) or BOT.search(t):
            dropped['spam'] += 1
            continue
        key = re.sub(r'[\W_]+', '', t).lower()
        if len(key) < 4 or key in seen:
            if key in seen:
                dropped['dup'] += 1
            else:
                dropped['empty'] += 1
            continue
        seen.add(key)
        c['comment'] = t
        cleaned.append(c)
    dropped['kept'] = len(cleaned)
    return cleaned, dropped

# ---------------------------------------------------------------- 3. 分析(规则式 NLP)
CATS = {
    '体验交互': ['体验','交互','工作流','认知','打断','割裂','不自然','别扭','反人性','不顺手','割裂感','认知负担','绕弯','繁琐','卡手','麻烦'],
    '易用性':   ['门槛','学习成本','复杂','听不懂','看不懂','难以','不会用','上手','简易','零门槛','自然语言','提示词','指令','小白','新手','友好','简单','易懂','易用','操作难','懵','头大','门槛高'],
    '功能':     ['功能','缺失','缺乏','不支持','做不到','无法','不能','限制','自定义','选项','希望有','建议增加','加上','功能不全','功能少','对口'],
    '性能':     ['延迟','响应慢','速度慢','慢','卡','端侧','算力','性能','实时','流畅','崩溃','卡顿','加载','转圈','掉线','超时','闪退'],
    '内容质量': ['同质化','ai味','空洞','幻觉','深度','个性','创意','质量差','准确','逼真','自然','文风','乱码','虚假','编造','胡说','低质','套话','模板','重复','废话','啰嗦','拉胯','辣眼睛'],
    '专业可靠': ['专业','专家','可靠','可解释','精准','误诊','风险','合规','权威','领域','行业知识','靠谱','信任','稳定','严谨'],
    '安全隐私': ['隐私','数据','安全','生物','版权','泄露','授权','条款','控制权','被遗忘','加密','盗','偷','滥用','实名','信息泄露'],
    '成本效率': ['价格','费用','订阅','成本','付费','贵','收费','免费','性价比','计费','省钱','会员','降价','便宜','经济','羊毛','划算','烧钱','冤枉钱'],
    '生态整合': ['协同','整合','全屋','跨','兼容','打通','生态','联动','互联','统一','一站式','接入','互通'],
    '行业落地': ['行业','企业','制造业','落地','选型','场景','业务','垂直','细分领域','小众行业','医疗','法律','金融','教育','政务','适配度'],
    '伦理社会': ['伦理','偏见','公平','学术','诚信','信息茧房','价值观','就业','责任','误导','诈骗'],
    '其他/通用': [],
}
SEVERITY = {'安全隐私':5,'专业可靠':5,'成本效率':4,'内容质量':4,'体验交互':4,'行业落地':4,
            '易用性':3,'性能':3,'功能':3,'生态整合':3,'伦理社会':3,'其他/通用':2}

POS = ['好','喜欢','香','顶','刚需','实用','棒','爱','推荐','强','快','省','方便','友好','绝',
       '神','牛','yyds','YYDS','惊艳','满意','高效','划算','良心','救','轻松','清晰','靠谱',
       '惊喜','赞','优秀','值得','吊打','给力','舒服','顺手','真香','巴适','舒服','丝滑','稳']
NEG = ['太不友好','劝退','麻烦','难','贵','差','垃圾','坑','崩溃','卡','慢','水','痛','吐槽','失望',
       '烦','乱','难用','反人性','担忧','焦虑','风险','骗','虚假','胡说','编造','泄露','滥','差评',
       '无语','搞笑','弱','废','鸡肋','累','看不懂','听不懂','恶心','离谱','智障','蠢','瞎','糊弄',
       '头大','懵','绕','割韭菜','套路','坑爹','卡顿','闪退','掉线','乱码','幻觉','同质化']
NEG_WEAK = ['不够','不足','欠缺','有待','提升','优化','改进','提高']  # 弱负面/建议
NEGATION = ['不','没','无','别','未','莫','非']
DESIRE = ['希望','需要','想要','能不能','建议','期待','最好','如何','怎么','求','应该','要是','盼',
          '渴望','愿','若能','要是能','可以','能否','能不能','希望有','建议增加','增加','加上','提供','开放']

def has_word(t, words):
    for w in words:
        if w in t:
            return w
    return None

def sentiment(t):
    # 负面线索(含否定反转)
    neg_hits = 0; pos_hits = 0; strong = False
    # 找负面词并判断是否被否定
    for w in NEG:
        idx = t.find(w)
        if idx == -1:
            continue
        # 检查前面4字符是否有否定词
        pre = t[max(0, idx-4):idx]
        if any(n in pre for n in NEGATION):
            pos_hits += 1   # 被否定 -> 转为正面/中性
        else:
            neg_hits += 1
            if w in ('太不友好','劝退','垃圾','崩溃','坑','痛','骗','恶心','离哭','离谱','智障','割韭菜','套路'):
                strong = True
    for w in POS:
        if w.lower() in t.lower():
            pos_hits += 1
    if '！' in t or '!' in t:
        strong = strong or neg_hits > 0
    if neg_hits > pos_hits:
        return ('负面', '强' if strong else '中')
    if pos_hits > neg_hits:
        return ('正面', '中')
    # 弱负面/建议词
    if has_word(t, NEG_WEAK):
        return ('负面', '弱')
    return ('中性', '弱')

def categorize(t):
    matched = []
    for cat, kws in CATS.items():
        if cat == '其他/通用':
            continue
        if has_word(t, kws):
            matched.append(cat)
    if not matched:
        matched = ['其他/通用']
    return matched

def extract_phrases(t, sent, cats):
    # 需求提炼: 取"希望/需要/能不能/建议..."等诉求词之后的内容
    desire_word = has_word(t, DESIRE)
    need = '—'
    if desire_word:
        pos = t.find(desire_word)
        seg = t[pos + len(desire_word):]
        seg = re.split(r'[。！？!?，,；;]', seg)[0].strip(' ，,。！？!?')
        need = seg[:40] if seg else t[:40]
    # 痛点提炼: 取首句
    first = re.split(r'[。！？!?]', t)[0]
    if len(first) > 55:
        first = first.split('，')[0][:55]
    first = first[:60].strip(' ，,。！？!?')
    if sent == '负面':
        pain = first
    elif desire_word:
        pain = '—'
    else:
        pain = first
    return pain, need

def keywords(t, top=5):
    import jieba
    stop = set('的 了 是 在 我 你 他 她 它 们 这 那 有 和 也 都 就 不 人 们 啊 吧 吗 呢 哦 啦 个 之 与 及 或 等 被 把 让 给 对 从 到 上 下 中 后 前 还 又 很 太 最 更 会 要 能 可 没 别 是 说 看 用 做 想 觉得 感觉 现在 一直 真的 完全 直接 这种 一种'.split())
    words = [w for w in jieba.cut(t) if len(w) >= 2 and w not in stop and not re.fullmatch(r'[\W_0-9a-zA-Z]+', w)]
    return [w for w, _ in Counter(words).most_common(top)]

def priority_bucket(score, ranks):
    # ranks: sorted list of scores desc; 返回 高/中/低
    n = len(ranks)
    p80 = ranks[int(n*0.20)] if n else 0
    p50 = ranks[int(n*0.50)] if n else 0
    if score >= p80:
        return '高'
    if score >= p50:
        return '中'
    return '低'

# ---------------------------------------------------------------- 主流程
def main():
    s = load_col(SRC)
    raw = parse_comments(s, start=312)
    print('解析原始评论:', len(raw))
    cleaned, dropped = clean(raw)
    print('清洗统计:', dropped)

    rows = []
    for idx, c in enumerate(cleaned, 1):
        t = c['comment']
        sent, intensity = sentiment(t)
        cats = categorize(t)
        primary = max(cats, key=lambda x: SEVERITY[x])
        pain, need = extract_phrases(t, sent, cats)
        kw = keywords(t)
        # 优先级分 = 严重度(主类) + 互动(log) + 负面加权
        eng = math.log10(c['likes'] + 1) * 2   # 0~约3.2
        negw = 1.0 if sent == '负面' else (0.5 if sent == '中性' else 0.0)
        score = SEVERITY[primary] + eng + negw
        rows.append(dict(
            序号=idx, 评论内容=t, 来源时间=c['time'], 来源地区=c['region'],
            点赞数=c['likes'], 用户名=c['user'],
            情绪=sent, 情绪强度=intensity, 类型=('痛点' if sent=='负面' else ('需求' if has_word(t, DESIRE) else '中性反馈')),
            痛点提炼=pain, 需求提炼=need,
            类别标签='、'.join(cats), 主类别=primary,
            关键词='、'.join(kw), 优先级分=round(score, 2)))

    # 优先级分桶
    scores = sorted([r['优先级分'] for r in rows], reverse=True)
    for r in rows:
        r['优先级'] = priority_bucket(r['优先级分'], scores)

    df = pd.DataFrame(rows)
    # 写入结构化 Excel
    # 统计
    cat_counter = Counter()
    for r in rows:
        for c in r['类别标签'].split('、'):
            cat_counter[c] += 1
    sent_counter = Counter(r['情绪'] for r in rows)
    # 痛点 vs 需求类别 (按类型)
    pain_cats = Counter()
    need_cats = Counter()
    for r in rows:
        if r['类型'] == '痛点':
            for c in r['类别标签'].split('、'):
                pain_cats[c] += 1
        elif r['类型'] == '需求':
            for c in r['类别标签'].split('、'):
                need_cats[c] += 1
    # 关键词总频
    kw_all = Counter()
    for r in rows:
        for k in r['关键词'].split('、'):
            if k:
                kw_all[k] += 1
    # 共现
    cooc = defaultdict(int)
    for r in rows:
        cs = r['类别标签'].split('、')
        for a in range(len(cs)):
            for b in range(a+1, len(cs)):
                cooc[(cs[a], cs[b])] += 1
    top_cooc = sorted(cooc.items(), key=lambda x: -x[1])[:15]

    # 保存
    df.to_excel(os.path.join(OUT, 'ai评论分析_结构化数据.xlsx'), index=False, sheet_name='结构化数据')

    # n8n 专用 CSV (核心5列 + 辅助列)
    n8n = df[['评论内容','痛点提炼','需求提炼','情绪','优先级','类别标签','类型','点赞数','来源地区','用户名']].copy()
    n8n.columns = ['评论内容','对应痛点','需求','情绪','优先级','类别标签','类型','点赞数','来源地区','用户名']
    n8n.to_csv(os.path.join(OUT, 'n8n_ready.csv'), index=False, encoding='utf-8-sig')

    # 汇总 JSON(供报告/图表复用)
    summary = dict(
        total=len(rows),
        dropped=dropped,
        sentiment=dict(sent_counter),
        cat_counter=dict(cat_counter),
        pain_cats=dict(pain_cats.most_common()),
        need_cats=dict(need_cats.most_common()),
        top_keywords=kw_all.most_common(25),
        top_cooc=[{'a':a,'b':b,'n':n} for (a,b),n in top_cooc],
        severity=SEVERITY,
    )
    with open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print('已写出: 结构化数据 / n8n_ready.csv / summary.json')
    print('情绪分布:', dict(sent_counter))
    print('Top 类别:', cat_counter.most_common(6))
    # 保存 df 供后续画图/报告脚本
    df.to_pickle(os.path.join(OUT, '_df.pkl'))
    return df, summary

if __name__ == '__main__':
    main()
