# -*- coding: utf-8 -*-
import json, os

BASE = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site"

# ---- 4.5 BOARD_KNOWLEDGE.md incremental append ----
kb_path = os.path.join(BASE, "BOARD_KNOWLEDGE.md")
kb_section = """
## 19. 2026-09-01 增量更新（早班 08:00）

### 特斯拉
- Optimus 人形机器人量产里程碑：9/1 华尔街见闻/第一财经确认已在加州费利蒙(Fremont)工厂进入量产阶段，是「AI+机器人巨头」估值叙事关键催化剂。
- 港澳简配 Model 3（8/31 已前置）仍是近期主线；Cybercab 9/3 奥斯汀公开载客。

### 特斯拉 FSD
- 避坑功能：马斯克 9/1 确认 FSD 自动避让路面坑洼「很快推出」，已列入 FSD v14 待更新列表；坑洼/突发路形仍是其三维建模难点。
- 入华红线：上海数据中心辟谣「关门」、临港 AI 训练中心投运；官方目标 2026 Q3 获批，社区预期 9 月内测/10 月小范围/11 月上线——均属预测，必须标「待官方确认」，禁编确切日期。

### 游戏主机
- Switch 2 涨价：9/1 起美区 MSRP $449.99→$499.99（约+50 美元），加拿大/欧洲同步；新捆绑包（马里奥赛车世界 9 月下旬、运动度假 10/22）随后。注意区分「建议零售价」与零售促销价。

### 漫威宇宙
- 复联4重映「Encore」：Disney UK 8/25 官宣，9/1 开票，9/25(英/印)起 IMAX + 全新 INFINITY VISION 格式，含《末日》(Doomsday, 12/18) 前瞻。澳大利亚 9/24。
- Disney+ 9 月漫威片单：蜘蛛侠《英雄远征》《英雄无归》9/4、《猎人克莱文》9/13。

### 苹果新品
- 库克交棒：8/31 卸任 CEO 最后一天，特努斯 9/1 接任，库克转任执行主席——属 9/1 硬新闻。
- iPhone 18 爆料（待官方确认）：标准版 A20/12GB/6.3" 120Hz/自研 C2 基带/799 美元起；Pro A20 Pro+可变光圈+屏下 Face ID；折叠机 iPhone Fold 同期；发布会预计 9/8-15。所有规格标「待官方确认」。

### 中药材
- 产地快讯日常源：药通网、中药材天地网（每日 9/1 类产地行情）。常见品种：连翘(挥发油合格货)、蝉蜕(沙地/水洗分级)、旋覆花、青翘产新等。
- 下半年研判口径：低位调整、7-9 月夏秋产新增压；野生/矿物类高位，大宗家种过剩品种仍有跌风险；政策端《中医药振兴十五五规划》+饮片追溯码托底优质货。

### 文玩手串（沉香）
- 沉香行情铁律：普通种植新料平稳无升值；高端老料/沉水料/奇楠因存量递减稳中有涨，海南沉香连续多月走高；网售低价「沉水串」多为压油仿品。产区梯度：海南奇楠>富森红土>芽庄>文莱/达拉干>普通加里曼丹。

### 紫砂艺术
- 拍卖日历源：上海国拍（民品专场，紫砂专场编号如第919期）、北京/地方司法拍卖（如北京一中院 6328 件紫砂壶二次拍卖）、保利（当代紫砂壶专场）。注意司法拍卖「不保证真伪/品质」风险提示。

### 养生茶（药食同源）
- 行业规模锚：2026 上半年药食同源终端 2240 亿(+27.6%)，全年有望破 4500 亿；养生茶饮 2025 年 642.7 亿、2028 预测 1189.5 亿（艾媒）。
- 合规红线：食药物质目录 106 种；普通食品(无蓝帽)严禁宣称治疗/保健功效，上半年超千家贴牌作坊出局。用户画像 18-35 占 62%、男性消费首超女性(56.1%)。

### 射阳本地动态
- 与台风监测互补：盐城暴雨黄色预警(8/31 续发)——9/1 全市中到大雨局部暴雨、射阳小雨；9/1-3 海区阵风 7-8 级；9/2 减弱。源：盐城新闻网、盐城气象。

### 台风实时监测
- 9/1 06:00 中央气象台台风蓝色预警：第18号「沙德尔」(2618) 残涡凌晨在南海西北部再度加强为台风(热带风暴级)，05时 19.2N/112.8E、8级18m/s、995hPa，东偏北25km/h、今天白天移入南海东北部、3日起回旋减弱；落区在闽浙粤台/海南，对射阳无直接风力与暴雨贡献。射阳县暴雨橙色预警(00:23升级)仍列最新未解除→维持「高」。

### ChinaJoy / 游戏展
- 国产3A第二波：影之刃零(8/12 预售登顶 Steam 国区)、湮灭之潮(8/15 成都试玩)、黑神话:钟馗(8/20 两周年放实机)、科隆夜 14 款中国游戏登台。
- ChinaJoy 2026 AI 主线：腾讯 Codename Craft / LAP / MagicDawn；索尼中国英雄计划《The Defiant》。

### 漫威正在热映票房
- 9/1 荷兰弟凭《蜘蛛侠：崭新之日》登顶全球影史男演员票房榜（参演影片累计 146.8 亿美元）；影片全球约 23.59 亿美元列影史第三。票房交叉源：新浪/BoxOfficeHype/猫眼/AceShowbiz，各源分歧须标明。
"""

with open(kb_path, "a", encoding="utf-8") as f:
    f.write(kb_section)
print("APPENDED BOARD_KNOWLEDGE.md section 19")

# ---- 5. changelog three-copy update ----
record = {
    "date": "2026-09-01",
    "content": "🤖 自动巡检（早班08:00）：逐板块检索9/1最新动态并交叉验证后更新。有更新的板块——特斯拉(Optimus量产/股价+5.5%)、特斯拉FSD(自动避坑确认+FSD入华Q3冲刺)、游戏主机(Switch 2美区9/1涨价+$50)、漫威宇宙(复联4重映Encore 9/1开票+Disney+ 9月片单)、苹果(库克交棒特努斯+iPhone 18爆料)、中药材(9/1产地快讯+下半年低位研判)、文玩手串(沉香分化·海南料走高)、紫砂(上海国拍9/6紫砂专场+司法拍卖6328件)、养生茶(药食同源4500亿+监管收紧)、射阳本地(9/1中到大雨局部暴雨·海区7-8级风)、ChinaJoy/游戏展(国产3A第二波+ChinaJoy AI)、漫威票房(荷兰弟登顶影史男演员票房榜·全球23.59亿影史第三)；台风监测(沙德尔复活为台风·中央气象台9/1蓝警·射阳橙警未解除维持「高」)。13板块全量巡检完成，各JSON前置今日新增、updated=2026-09-01。",
}
copies = [
    os.path.join(BASE, "static/changelog.json"),
    os.path.join(BASE, "data/changelog.json"),
    os.path.join(BASE, "static/data/changelog.json"),
]
for c in copies:
    with open(c, "r", encoding="utf-8") as f:
        arr = json.load(f)
    arr.insert(0, record)
    # safety: ensure no empty content
    for i, e in enumerate(arr):
        if not isinstance(e, dict) or not e.get("content"):
            e["content"] = e.get("content") or "(空记录已修复)"
            arr[i] = e
    with open(c, "w", encoding="utf-8") as f:
        json.dump(arr, f, ensure_ascii=False, indent=2)
    print("WROTE", c, "len", len(arr))

# verify three copies identical length
lens = []
for c in copies:
    lens.append(len(json.load(open(c, encoding="utf-8"))))
print("COPY LENGTHS:", lens, "MATCH" if len(set(lens)) == 1 else "MISMATCH")
# verify no empty content
bad = 0
for c in copies:
    for e in json.load(open(c, encoding="utf-8")):
        if not e.get("content"):
            bad += 1
print("EMPTY CONTENT COUNT:", bad)
print("DONE")
