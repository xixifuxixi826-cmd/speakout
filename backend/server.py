#!/usr/bin/env python3
import json
import os
import re
import random
import sqlite3
import traceback
import time
import uuid
import csv
import io
import hashlib
import threading
import mimetypes
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse, urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT.parent / "代码原型" / "biaodagaoshou-h5"
ADMIN_FRONTEND_DIR = ROOT.parent / "代码原型" / "开口-miniapp-prototype" / "admin"
ADMIN_ROUTE_PREFIX = "/admin-console"
DEFAULT_DATA_DIR = ROOT / "data"
if os.getenv("APP_DATA_DIR"):
    DATA_DIR = Path(os.getenv("APP_DATA_DIR", "")).expanduser()
elif os.getenv("RAILWAY_ENVIRONMENT"):
    DATA_DIR = Path(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/tmp/speakout-data")).expanduser()
else:
    DATA_DIR = DEFAULT_DATA_DIR
DB_PATH = DATA_DIR / "express_master.db"
CONFIG_PATH = ROOT / "runtime_config.json"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8765"))

WORD_DECKS = [
    {
        "id": "deck-a",
        "title": "自我与成长",
        "starter": True,
        "cards": [
            "自由", "独立", "成长", "自洽", "自律", "自尊", "自信", "勇气",
            "选择", "边界", "潜力", "野心", "意义", "身份", "主体性", "松弛感"
        ],
    },
    {
        "id": "deck-b",
        "title": "情绪与心理",
        "starter": True,
        "cards": [
            "焦虑", "内耗", "羞耻", "脆弱", "孤独", "痛苦", "恐惧", "愤怒",
            "悲伤", "不安", "压抑", "疲惫", "迟疑", "敏感", "韧性", "失控"
        ],
    },
    {
        "id": "deck-c",
        "title": "亲密关系",
        "starter": True,
        "cards": [
            "爱情", "亲密", "信任", "陪伴", "安全感", "依赖", "吸引", "疏离",
            "控制", "嫉妒", "承诺", "界限", "体谅", "沟通", "冷战", "分手"
        ],
    },
    {
        "id": "deck-d",
        "title": "家庭与代际",
        "cards": [
            "原生家庭", "父母", "孝顺", "亏欠", "期待", "规训", "偏爱", "比较",
            "牺牲", "溺爱", "代沟", "服从", "认可", "缺席", "投射", "窒息"
        ],
    },
    {
        "id": "deck-e",
        "title": "职场与组织",
        "starter": True,
        "cards": [
            "工作", "效率", "稳定", "跳槽", "管理", "升职", "加班", "内卷",
            "竞争", "汇报", "权力", "倦怠", "天花板", "试错", "绩效", "协作"
        ],
    },
    {
        "id": "deck-f",
        "title": "女性与性别",
        "cards": [
            "女性主义", "婚育", "母职", "悦己", "容貌焦虑", "生育成本", "性别偏见", "玻璃天花板",
            "彩礼", "贤妻良母", "照顾劳动", "身体自主", "月经羞耻", "姐妹情谊", "大女主", "服美役"
        ],
    },
    {
        "id": "deck-g",
        "title": "消费与金钱",
        "cards": [
            "消费主义", "理财", "贫穷", "欲望", "体面", "奢侈", "节俭", "分期",
            "负债", "存款", "投资", "机会成本", "性价比", "及时行乐", "溢价", "消费降级"
        ],
    },
    {
        "id": "deck-h",
        "title": "社交与边界",
        "cards": [
            "社交", "面子", "人情世故", "拒绝", "讨好", "真诚", "搭子", "社恐",
            "连接", "共鸣", "礼貌", "自我暴露", "边界感", "轻社交", "断联", "情绪价值"
        ],
    },
    {
        "id": "deck-i",
        "title": "社会与价值",
        "cards": [
            "公平", "偏见", "秩序", "规则", "资格", "特权", "正义", "惩罚",
            "控诉", "共识", "冲突", "责任", "阶层", "资源", "规矩", "话语权"
        ],
    },
    {
        "id": "deck-j",
        "title": "表达与说服",
        "cards": [
            "说服", "观点", "立场", "反驳", "证据", "叙事", "想象力", "逻辑",
            "例子", "语言", "真实感", "节奏", "张力", "判断", "解释", "共情"
        ],
    },
    {
        "id": "deck-k",
        "title": "时代与选择",
        "cards": [
            "城市", "漂泊", "安稳", "冒险", "机会", "迁移", "归属", "房子",
            "租房", "买房", "养老", "延迟退休", "灵活就业", "副业", "失业", "自由职业"
        ],
    },
    {
        "id": "deck-l",
        "title": "互联网与身份",
        "cards": [
            "流量", "算法", "标签", "人设", "赛博社交", "曝光", "比较心", "关注度",
            "评价体系", "自媒体", "乙游", "虚拟亲密", "饭圈", "上头", "直播间", "私域"
        ],
    },
    {
        "id": "deck-m",
        "title": "修复与成熟",
        "cards": [
            "原谅", "妥协", "宽容", "接纳", "改变", "修复", "觉察", "复盘",
            "沉默", "逃避", "坦诚", "尊严", "同理心", "自我接纳", "稳定感", "信念"
        ],
    },
]

BEGINNER_CARD_POOLS = {
    "anchor": [
        "自由", "独立", "成长", "体面", "真诚", "安全感", "自尊", "勇气",
        "稳定", "公平", "尊严", "意义", "选择", "边界", "信任", "责任",
        "爱情", "亲情", "友情", "人生", "家庭", "工作", "关系", "婚姻",
    ],
    "tension": [
        "代价", "谎言", "控制", "失去", "焦虑", "束缚", "依赖", "比较",
        "妥协", "亏欠", "规训", "压力", "羞耻", "逃避", "内耗", "孤独",
    ],
    "scene": [
        "职场", "婚姻", "原生家庭", "消费", "短视频", "房子", "相亲", "加班",
        "自媒体", "朋友圈", "父母", "伴侣", "工作", "租房", "辞职", "社交",
    ],
    "metaphor": [
        "镜子", "天平", "消防栓", "电梯", "闹钟", "地图", "钥匙", "盲盒",
        "滤镜", "账单", "存钱罐", "安全带", "避风港", "跑步机", "回音壁", "放大镜",
        "橡皮筋", "温室", "围墙", "桥", "门票", "说明书", "垃圾桶", "充电宝",
        "烟花", "雪花", "火焰", "潮汐", "风筝", "沙漏", "迷宫", "灯塔",
        "港口", "孤岛", "漩涡", "种子", "花园", "仙人掌", "刺猬", "海绵",
        "苹果", "火龙果", "榴莲", "柠檬", "糖葫芦", "咖啡", "洋葱", "蜂蜜",
        "玻璃杯", "保温杯", "雨伞", "创可贴", "枕头", "抽屉", "背包", "拼图",
        "指南针", "红绿灯", "遥控器", "显微镜", "望远镜", "弹簧", "锚", "船",
        "气球", "面具", "盔甲", "羽毛", "石头", "藤蔓", "野草", "猫",
        "候鸟", "蚂蚁", "章鱼", "鲸鱼", "贝壳", "珍珠", "月亮", "星星",
        "孔雀", "乌龟", "蜗牛", "狐狸", "蒲公英", "玫瑰", "青苔", "玻璃",
        "糖衣", "辣椒", "冰块", "热水", "毛线团", "万花筒", "跷跷板", "多米诺骨牌",
    ],
    "mechanism": [
        "评价", "标签", "算法", "规则", "奖励", "惩罚", "惯性", "机会成本",
        "人情世故", "话语权", "身份", "竞争", "共识", "偏见", "沟通", "边界感",
    ],
}

BEGINNER_FORBIDDEN_CLOSE_PAIRS = {
    frozenset(("焦虑", "内耗")),
    frozenset(("内耗", "压抑")),
    frozenset(("自由", "成长")),
    frozenset(("稳定", "安稳")),
    frozenset(("安全感", "稳定感")),
    frozenset(("边界", "边界感")),
    frozenset(("自尊", "尊严")),
    frozenset(("房子", "租房")),
    frozenset(("房子", "买房")),
    frozenset(("职场", "工作")),
    frozenset(("社交", "朋友圈")),
    frozenset(("父母", "原生家庭")),
    frozenset(("钥匙", "门票")),
    frozenset(("镜子", "滤镜")),
    frozenset(("地图", "说明书")),
    frozenset(("显微镜", "望远镜")),
    frozenset(("灯塔", "港口")),
    frozenset(("珍珠", "贝壳")),
    frozenset(("月亮", "星星")),
    frozenset(("苹果", "火龙果")),
    frozenset(("雨伞", "避风港")),
    frozenset(("盔甲", "安全带")),
}

QUOTE_SEED_TEXT = """
语言的边界，也是思维的边界|维特根斯坦|表达与思维|Wikiquote Language|https://en.wikiquote.org/wiki/Language
修辞是说服的艺术。|亚里士多德|表达与说服|Wikiquote Public speaking|https://en.wikiquote.org/wiki/Public_speaking
说话的目的，不是取胜，而是照亮。|表达高手编辑部|表达练习|产品内置|internal
好的表达，是把别人心里的模糊说清楚。|表达高手编辑部|表达练习|产品内置|internal
观点不是情绪的放大器，而是经验的结构。|表达高手编辑部|表达练习|产品内置|internal
先把一个人讲具体，再把一群人讲明白。|表达高手编辑部|表达练习|产品内置|internal
故事留住注意力，判断决定方向。|表达高手编辑部|表达练习|产品内置|internal
不要急着正确，先把感受讲准确。|表达高手编辑部|表达练习|产品内置|internal
一句话能站住，是因为它背后有人。|表达高手编辑部|表达练习|产品内置|internal
表达不是把话说满，而是把重点说透。|表达高手编辑部|表达练习|产品内置|internal
沉默有时也是一种意见。|表达高手编辑部|表达练习|产品内置|internal
真诚不是想到什么说什么，而是知道为什么要说。|表达高手编辑部|表达练习|产品内置|internal
不要用概念代替场景。|表达高手编辑部|表达练习|产品内置|internal
别急着升华，先让人看见。|表达高手编辑部|表达练习|产品内置|internal
能被复述的观点，才真正进入了别人心里。|表达高手编辑部|表达练习|产品内置|internal
用一个具体时刻，抵达一个抽象命题。|表达高手编辑部|表达练习|产品内置|internal
观点要锋利，语气要有人味。|表达高手编辑部|表达练习|产品内置|internal
最有力的表达，常常从承认复杂开始。|表达高手编辑部|表达练习|产品内置|internal
把话说清楚，本身就是一种负责。|表达高手编辑部|表达练习|产品内置|internal
会说话的人，不是没有情绪，而是能安放情绪。|表达高手编辑部|表达练习|产品内置|internal
一句判断，一条理由，一个场景。|表达高手编辑部|表达练习|产品内置|internal
当你说“很多人”，最好先想起一个人。|表达高手编辑部|表达练习|产品内置|internal
好观点通常不是更大，而是更准。|表达高手编辑部|表达练习|产品内置|internal
表达的训练，是把脑内雾气变成路标。|表达高手编辑部|表达练习|产品内置|internal
真正的清晰，不是简单，而是有秩序。|表达高手编辑部|表达练习|产品内置|internal
不要只证明你有想法，也要证明你看见了人。|表达高手编辑部|表达练习|产品内置|internal
一段话最怕的不是短，而是没有靶心。|表达高手编辑部|表达练习|产品内置|internal
越抽象的词，越需要具体的人来托住。|表达高手编辑部|表达练习|产品内置|internal
表达不是表演聪明，是建立理解。|表达高手编辑部|表达练习|产品内置|internal
讲道理之前，先让人相信你知道痛在哪里。|表达高手编辑部|表达练习|产品内置|internal
与其堆三个观点，不如讲透一个判断。|表达高手编辑部|表达练习|产品内置|internal
观点负责方向，例子负责重量。|表达高手编辑部|表达练习|产品内置|internal
不愤不启，不悱不发。|孔子|学习与表达|《论语》|https://ctext.org/analects
君子欲讷于言而敏于行。|孔子|行动与语言|《论语》|https://ctext.org/analects
知之为知之，不知为不知，是知也。|孔子|诚实表达|《论语》|https://ctext.org/analects
听其言而观其行。|孔子|语言与行动|《论语》|https://ctext.org/analects
辞达而已矣。|孔子|表达标准|《论语》|https://ctext.org/analects
君子和而不同。|孔子|讨论与差异|《论语》|https://ctext.org/analects
质胜文则野，文胜质则史。|孔子|内容与形式|《论语》|https://ctext.org/analects
敏于事而慎于言。|孔子|慎言|《论语》|https://ctext.org/analects
言必信，行必果。|孔子|承诺与行动|《论语》|https://ctext.org/analects
巧言令色，鲜矣仁。|孔子|真诚表达|《论语》|https://ctext.org/analects
学而不思则罔，思而不学则殆。|孔子|思考|《论语》|https://ctext.org/analects
三思而后行。|孔子|判断|《论语》|https://ctext.org/analects
道听而涂说，德之弃也。|孔子|二手观点|《论语》|https://ctext.org/analects
君子坦荡荡，小人长戚戚。|孔子|人格与表达|《论语》|https://ctext.org/analects
己所不欲，勿施于人。|孔子|共情|《论语》|https://ctext.org/analects
工欲善其事，必先利其器。|孔子|训练方法|《论语》|https://ctext.org/analects
人之患在好为人师。|孟子|表达姿态|《孟子》|https://ctext.org/mengzi
尽信书，则不如无书。|孟子|独立判断|《孟子》|https://ctext.org/mengzi
说大人，则藐之。|孟子|表达勇气|《孟子》|https://ctext.org/mengzi
生于忧患，死于安乐。|孟子|成长|《孟子》|https://ctext.org/mengzi
得道者多助，失道者寡助。|孟子|立场|《孟子》|https://ctext.org/mengzi
权，然后知轻重。|孟子|判断|《孟子》|https://ctext.org/mengzi
穷则独善其身，达则兼善天下。|孟子|责任|《孟子》|https://ctext.org/mengzi
大人者，不失其赤子之心者也。|孟子|真实感|《孟子》|https://ctext.org/mengzi
吾善养吾浩然之气。|孟子|气势|《孟子》|https://ctext.org/mengzi
天时不如地利，地利不如人和。|孟子|关系|《孟子》|https://ctext.org/mengzi
知人者智，自知者明。|老子|自我认知|《道德经》|https://ctext.org/dao-de-jing
胜人者有力，自胜者强。|老子|成长|《道德经》|https://ctext.org/dao-de-jing
大音希声，大象无形。|老子|表达留白|《道德经》|https://ctext.org/dao-de-jing
信言不美，美言不信。|老子|真话|《道德经》|https://ctext.org/dao-de-jing
知者不言，言者不知。|老子|沉默|《道德经》|https://ctext.org/dao-de-jing
合抱之木，生于毫末。|老子|成长|《道德经》|https://ctext.org/dao-de-jing
千里之行，始于足下。|老子|行动|《道德经》|https://ctext.org/dao-de-jing
祸兮福之所倚，福兮祸之所伏。|老子|辩证|《道德经》|https://ctext.org/dao-de-jing
自见者不明，自是者不彰。|老子|自省|《道德经》|https://ctext.org/dao-de-jing
夫轻诺必寡信。|老子|承诺|《道德经》|https://ctext.org/dao-de-jing
吾生也有涯，而知也无涯。|庄子|认知边界|《庄子》|https://ctext.org/zhuangzi
相濡以沫，不如相忘于江湖。|庄子|关系|《庄子》|https://ctext.org/zhuangzi
人生天地之间，若白驹之过隙。|庄子|时间|《庄子》|https://ctext.org/zhuangzi
井蛙不可以语于海。|庄子|视野|《庄子》|https://ctext.org/zhuangzi
子非鱼，安知鱼之乐。|庄子|理解他人|《庄子》|https://ctext.org/zhuangzi
知其不可奈何而安之若命。|庄子|接纳|《庄子》|https://ctext.org/zhuangzi
不以物挫志。|庄子|自我|《庄子》|https://ctext.org/zhuangzi
独与天地精神往来。|庄子|精神自由|《庄子》|https://ctext.org/zhuangzi
无用之用，方为大用。|庄子|价值|《庄子》|https://ctext.org/zhuangzi
天地与我并生，万物与我为一。|庄子|整体感|《庄子》|https://ctext.org/zhuangzi
不积跬步，无以至千里。|荀子|训练|《荀子》|https://ctext.org/xunzi
不积小流，无以成江海。|荀子|积累|《荀子》|https://ctext.org/xunzi
锲而不舍，金石可镂。|荀子|坚持|《荀子》|https://ctext.org/xunzi
蓬生麻中，不扶而直。|荀子|环境|《荀子》|https://ctext.org/xunzi
青，取之于蓝，而青于蓝。|荀子|学习|《荀子》|https://ctext.org/xunzi
目不能两视而明，耳不能两听而聪。|荀子|聚焦|《荀子》|https://ctext.org/xunzi
君子生非异也，善假于物也。|荀子|借力|《荀子》|https://ctext.org/xunzi
学不可以已。|荀子|学习|《荀子》|https://ctext.org/xunzi
水则载舟，水则覆舟。|荀子|关系与权力|《荀子》|https://ctext.org/xunzi
道阻且长，行则将至。|《荀子》相关俗语|行动|传统语汇|https://ctext.org/xunzi
博观而约取，厚积而薄发。|苏轼|积累与表达|苏轼文集|https://ctext.org/wiki.pl?if=gb&res=776787
腹有诗书气自华。|苏轼|表达气质|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
横看成岭侧成峰。|苏轼|视角|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
不识庐山真面目，只缘身在此山中。|苏轼|视角盲区|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
人有悲欢离合，月有阴晴圆缺。|苏轼|人生复杂性|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
竹杖芒鞋轻胜马。|苏轼|自由|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
回首向来萧瑟处，归去，也无风雨也无晴。|苏轼|接纳|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
人生如逆旅，我亦是行人。|苏轼|人生处境|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
枝上柳绵吹又少，天涯何处无芳草。|苏轼|失去与可能|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
一点浩然气，千里快哉风。|苏轼|气象|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
纸上得来终觉浅，绝知此事要躬行。|陆游|实践|陆游诗文|https://ctext.org/wiki.pl?if=gb&res=668220
山重水复疑无路，柳暗花明又一村。|陆游|转机|陆游诗文|https://ctext.org/wiki.pl?if=gb&res=668220
位卑未敢忘忧国。|陆游|责任|陆游诗文|https://ctext.org/wiki.pl?if=gb&res=668220
文章本天成，妙手偶得之。|陆游|创作|陆游诗文|https://ctext.org/wiki.pl?if=gb&res=668220
汝果欲学诗，工夫在诗外。|陆游|表达训练|陆游诗文|https://ctext.org/wiki.pl?if=gb&res=668220
旧书不厌百回读，熟读深思子自知。|苏轼|学习|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
问渠那得清如许，为有源头活水来。|朱熹|思想源头|朱熹诗文|https://ctext.org/wiki.pl?if=gb
等闲识得东风面，万紫千红总是春。|朱熹|发现|朱熹诗文|https://ctext.org/wiki.pl?if=gb
少年易老学难成，一寸光阴不可轻。|朱熹|学习|朱熹诗文|https://ctext.org/wiki.pl?if=gb
半亩方塘一鉴开，天光云影共徘徊。|朱熹|思考|朱熹诗文|https://ctext.org/wiki.pl?if=gb
纸上得来终觉浅。|陆游|实践|陆游诗文|https://ctext.org/wiki.pl?if=gb&res=668220
千磨万击还坚劲，任尔东西南北风。|郑燮|韧性|郑燮诗文|https://ctext.org/wiki.pl?if=gb
删繁就简三秋树，领异标新二月花。|郑燮|表达取舍|郑燮题画|https://ctext.org/wiki.pl?if=gb
咬定青山不放松。|郑燮|坚持|郑燮诗文|https://ctext.org/wiki.pl?if=gb
世事洞明皆学问，人情练达即文章。|曹雪芹|人情与表达|《红楼梦》|https://ctext.org/hongloumeng
假作真时真亦假，无为有处有还无。|曹雪芹|真假|《红楼梦》|https://ctext.org/hongloumeng
满纸荒唐言，一把辛酸泪。|曹雪芹|表达与真相|《红楼梦》|https://ctext.org/hongloumeng
机关算尽太聪明，反误了卿卿性命。|曹雪芹|聪明与代价|《红楼梦》|https://ctext.org/hongloumeng
草蛇灰线，伏脉千里。|脂砚斋|结构|《红楼梦》评语|https://ctext.org/hongloumeng
世事一场大梦，人生几度秋凉。|苏轼|人生感|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
大江东去，浪淘尽，千古风流人物。|苏轼|历史感|苏轼诗文|https://ctext.org/wiki.pl?if=gb&res=776787
仰天大笑出门去，我辈岂是蓬蒿人。|李白|自信|李白诗文|https://ctext.org/wiki.pl?if=gb
天生我材必有用。|李白|自我价值|李白诗文|https://ctext.org/wiki.pl?if=gb
长风破浪会有时。|李白|希望|李白诗文|https://ctext.org/wiki.pl?if=gb
安能摧眉折腰事权贵。|李白|独立|李白诗文|https://ctext.org/wiki.pl?if=gb
人生得意须尽欢。|李白|生命感|李白诗文|https://ctext.org/wiki.pl?if=gb
抽刀断水水更流，举杯消愁愁更愁。|李白|情绪|李白诗文|https://ctext.org/wiki.pl?if=gb
举杯邀明月，对影成三人。|李白|孤独|李白诗文|https://ctext.org/wiki.pl?if=gb
大道如青天，我独不得出。|李白|困境|李白诗文|https://ctext.org/wiki.pl?if=gb
会当凌绝顶，一览众山小。|杜甫|视野|杜甫诗文|https://ctext.org/wiki.pl?if=gb
读书破万卷，下笔如有神。|杜甫|表达积累|杜甫诗文|https://ctext.org/wiki.pl?if=gb
朱门酒肉臭，路有冻死骨。|杜甫|社会观察|杜甫诗文|https://ctext.org/wiki.pl?if=gb
文章千古事，得失寸心知。|杜甫|表达责任|杜甫诗文|https://ctext.org/wiki.pl?if=gb
露从今夜白，月是故乡明。|杜甫|情感具体性|杜甫诗文|https://ctext.org/wiki.pl?if=gb
射人先射马，擒贼先擒王。|杜甫|抓重点|杜甫诗文|https://ctext.org/wiki.pl?if=gb
感时花溅泪，恨别鸟惊心。|杜甫|情绪投射|杜甫诗文|https://ctext.org/wiki.pl?if=gb
烽火连三月，家书抵万金。|杜甫|时代与个人|杜甫诗文|https://ctext.org/wiki.pl?if=gb
沉舟侧畔千帆过，病树前头万木春。|刘禹锡|变化|刘禹锡诗文|https://ctext.org/wiki.pl?if=gb
千淘万漉虽辛苦，吹尽狂沙始到金。|刘禹锡|筛选|刘禹锡诗文|https://ctext.org/wiki.pl?if=gb
东边日出西边雨，道是无晴却有晴。|刘禹锡|暧昧与判断|刘禹锡诗文|https://ctext.org/wiki.pl?if=gb
芳林新叶催陈叶，流水前波让后波。|刘禹锡|更替|刘禹锡诗文|https://ctext.org/wiki.pl?if=gb
请君莫奏前朝曲，听唱新翻杨柳枝。|刘禹锡|创新|刘禹锡诗文|https://ctext.org/wiki.pl?if=gb
山不在高，有仙则名。|刘禹锡|价值|刘禹锡诗文|https://ctext.org/wiki.pl?if=gb
谈笑有鸿儒，往来无白丁。|刘禹锡|圈层|刘禹锡诗文|https://ctext.org/wiki.pl?if=gb
无丝竹之乱耳，无案牍之劳形。|刘禹锡|秩序|刘禹锡诗文|https://ctext.org/wiki.pl?if=gb
野火烧不尽，春风吹又生。|白居易|韧性|白居易诗文|https://ctext.org/wiki.pl?if=gb
同是天涯沦落人，相逢何必曾相识。|白居易|共情|白居易诗文|https://ctext.org/wiki.pl?if=gb
在天愿作比翼鸟，在地愿为连理枝。|白居易|亲密关系|白居易诗文|https://ctext.org/wiki.pl?if=gb
文章合为时而著。|白居易|表达与时代|白居易诗文|https://ctext.org/wiki.pl?if=gb
诗歌合为事而作。|白居易|表达动机|白居易诗文|https://ctext.org/wiki.pl?if=gb
日出江花红胜火，春来江水绿如蓝。|白居易|画面感|白居易诗文|https://ctext.org/wiki.pl?if=gb
试玉要烧三日满，辨材须待七年期。|白居易|判断|白居易诗文|https://ctext.org/wiki.pl?if=gb
乱花渐欲迷人眼，浅草才能没马蹄。|白居易|细节|白居易诗文|https://ctext.org/wiki.pl?if=gb
先天下之忧而忧，后天下之乐而乐。|范仲淹|责任|范仲淹文集|https://ctext.org/wiki.pl?if=gb
不以物喜，不以己悲。|范仲淹|情绪稳定|范仲淹文集|https://ctext.org/wiki.pl?if=gb
居庙堂之高则忧其民。|范仲淹|位置与责任|范仲淹文集|https://ctext.org/wiki.pl?if=gb
处江湖之远则忧其君。|范仲淹|位置与责任|范仲淹文集|https://ctext.org/wiki.pl?if=gb
云山苍苍，江水泱泱。|范仲淹|气象|范仲淹文集|https://ctext.org/wiki.pl?if=gb
士不可以不弘毅，任重而道远。|曾子|责任|《论语》|https://ctext.org/analects
吾日三省吾身。|曾子|复盘|《论语》|https://ctext.org/analects
鸟之将死，其鸣也哀。|曾子|真情|《论语》|https://ctext.org/analects
任重而道远。|曾子|长期主义|《论语》|https://ctext.org/analects
可以托六尺之孤，可以寄百里之命。|曾子|信任|《论语》|https://ctext.org/analects
精诚所至，金石为开。|王充相关俗语|真诚|传统语汇|https://ctext.org
疾风知劲草，板荡识诚臣。|李世民|考验|李世民诗文|https://ctext.org/wiki.pl?if=gb
以铜为镜，可以正衣冠。|李世民|自省|《旧唐书》|https://ctext.org/wiki.pl?if=gb
以人为镜，可以明得失。|李世民|反馈|《旧唐书》|https://ctext.org/wiki.pl?if=gb
兼听则明，偏信则暗。|魏徵|判断|《资治通鉴》|https://ctext.org/wiki.pl?if=gb
居安思危，戒奢以俭。|魏徵|风险意识|《谏太宗十思疏》|https://ctext.org/wiki.pl?if=gb
求木之长者，必固其根本。|魏徵|根基|《谏太宗十思疏》|https://ctext.org/wiki.pl?if=gb
欲流之远者，必浚其泉源。|魏徵|源头|《谏太宗十思疏》|https://ctext.org/wiki.pl?if=gb
善始者实繁，克终者盖寡。|魏徵|坚持|《谏太宗十思疏》|https://ctext.org/wiki.pl?if=gb
前事不忘，后事之师。|司马迁|经验|《史记》|https://ctext.org/shiji
桃李不言，下自成蹊。|司马迁|影响力|《史记》|https://ctext.org/shiji
人固有一死，或重于泰山，或轻于鸿毛。|司马迁|价值|《报任安书》|https://ctext.org/wiki.pl?if=gb
究天人之际，通古今之变。|司马迁|思考尺度|《报任安书》|https://ctext.org/wiki.pl?if=gb
失之东隅，收之桑榆。|范晔|得失|《后汉书》|https://ctext.org/wiki.pl?if=gb
精诚所加，金石为亏。|范晔|诚意|《后汉书》|https://ctext.org/wiki.pl?if=gb
志不求易，事不避难。|范晔|困难|《后汉书》|https://ctext.org/wiki.pl?if=gb
有志者事竟成。|范晔|意志|《后汉书》|https://ctext.org/wiki.pl?if=gb
不入虎穴，焉得虎子。|班超|冒险|《后汉书》|https://ctext.org/wiki.pl?if=gb
海内存知己，天涯若比邻。|王勃|关系|王勃诗文|https://ctext.org/wiki.pl?if=gb
落霞与孤鹜齐飞，秋水共长天一色。|王勃|画面感|王勃诗文|https://ctext.org/wiki.pl?if=gb
穷且益坚，不坠青云之志。|王勃|逆境|王勃诗文|https://ctext.org/wiki.pl?if=gb
老当益壮，宁移白首之心。|王勃|年龄|王勃诗文|https://ctext.org/wiki.pl?if=gb
物华天宝，人杰地灵。|王勃|环境与人|王勃诗文|https://ctext.org/wiki.pl?if=gb
行到水穷处，坐看云起时。|王维|转念|王维诗文|https://ctext.org/wiki.pl?if=gb
明月松间照，清泉石上流。|王维|画面感|王维诗文|https://ctext.org/wiki.pl?if=gb
深林人不知，明月来相照。|王维|孤独|王维诗文|https://ctext.org/wiki.pl?if=gb
劝君更尽一杯酒，西出阳关无故人。|王维|离别|王维诗文|https://ctext.org/wiki.pl?if=gb
大漠孤烟直，长河落日圆。|王维|意象|王维诗文|https://ctext.org/wiki.pl?if=gb
Who controls the past controls the future.|乔治·奥威尔|权力与叙事|Wikiquote George Orwell|https://en.wikiquote.org/wiki/George_Orwell
All animals are equal, but some animals are more equal than others.|乔治·奥威尔|平等与权力|Wikiquote George Orwell|https://en.wikiquote.org/wiki/George_Orwell
If liberty means anything, it means telling people what they do not want to hear.|乔治·奥威尔|自由表达|Wikiquote George Orwell|https://en.wikiquote.org/wiki/George_Orwell
The limits of my language mean the limits of my world.|维特根斯坦|语言与世界|Wikiquote Language|https://en.wikiquote.org/wiki/Language
Whereof one cannot speak, thereof one must be silent.|维特根斯坦|语言边界|Wikiquote Ludwig Wittgenstein|https://en.wikiquote.org/wiki/Ludwig_Wittgenstein
I have nothing to declare except my genius.|奥斯卡·王尔德|自我表达|Wikiquote Oscar Wilde|https://en.wikiquote.org/wiki/Oscar_Wilde
Be yourself; everyone else is already taken.|奥斯卡·王尔德|自我|Wikiquote Oscar Wilde|https://en.wikiquote.org/wiki/Oscar_Wilde
The truth is rarely pure and never simple.|奥斯卡·王尔德|真相复杂性|Wikiquote Oscar Wilde|https://en.wikiquote.org/wiki/Oscar_Wilde
To define is to limit.|奥斯卡·王尔德|定义与限制|Wikiquote Oscar Wilde|https://en.wikiquote.org/wiki/Oscar_Wilde
Experience is the name everyone gives to their mistakes.|奥斯卡·王尔德|经验|Wikiquote Oscar Wilde|https://en.wikiquote.org/wiki/Oscar_Wilde
There is no sin except stupidity.|奥斯卡·王尔德|锋利判断|Wikiquote Oscar Wilde|https://en.wikiquote.org/wiki/Oscar_Wilde
The unexamined life is not worth living.|苏格拉底|反思|Wikiquote Socrates|https://en.wikiquote.org/wiki/Socrates
I know that I know nothing.|苏格拉底|谦逊|Wikiquote Socrates|https://en.wikiquote.org/wiki/Socrates
Wonder is the beginning of wisdom.|苏格拉底|好奇|Wikiquote Socrates|https://en.wikiquote.org/wiki/Socrates
Know thyself.|苏格拉底|自我认知|Wikiquote Socrates|https://en.wikiquote.org/wiki/Socrates
The beginning is the most important part of the work.|柏拉图|开始|Wikiquote Plato|https://en.wikiquote.org/wiki/Plato
Wise men speak because they have something to say.|柏拉图|表达动机|Wikiquote Plato|https://en.wikiquote.org/wiki/Plato
Opinion is the medium between knowledge and ignorance.|柏拉图|观点|Wikiquote Plato|https://en.wikiquote.org/wiki/Plato
Courage is knowing what not to fear.|柏拉图|勇气|Wikiquote Plato|https://en.wikiquote.org/wiki/Plato
We are what we repeatedly do.|亚里士多德|习惯|Wikiquote Aristotle|https://en.wikiquote.org/wiki/Aristotle
Hope is a waking dream.|亚里士多德|希望|Wikiquote Aristotle|https://en.wikiquote.org/wiki/Aristotle
Knowing yourself is the beginning of all wisdom.|亚里士多德|自我认知|Wikiquote Aristotle|https://en.wikiquote.org/wiki/Aristotle
The whole is greater than the sum of its parts.|亚里士多德|系统|Wikiquote Aristotle|https://en.wikiquote.org/wiki/Aristotle
No great mind has ever existed without a touch of madness.|亚里士多德|创造|Wikiquote Aristotle|https://en.wikiquote.org/wiki/Aristotle
Time discovers truth.|塞内加|时间与真相|Wikiquote Seneca|https://en.wikiquote.org/wiki/Seneca_the_Younger
We suffer more often in imagination than in reality.|塞内加|焦虑|Wikiquote Seneca|https://en.wikiquote.org/wiki/Seneca_the_Younger
Luck is what happens when preparation meets opportunity.|塞内加|机会|Wikiquote Seneca|https://en.wikiquote.org/wiki/Seneca_the_Younger
No man was ever wise by chance.|塞内加|智慧|Wikiquote Seneca|https://en.wikiquote.org/wiki/Seneca_the_Younger
He who is brave is free.|塞内加|自由|Wikiquote Seneca|https://en.wikiquote.org/wiki/Seneca_the_Younger
First say to yourself what you would be.|爱比克泰德|自我塑造|Wikiquote Epictetus|https://en.wikiquote.org/wiki/Epictetus
It is not things that disturb us, but our judgments about things.|爱比克泰德|判断|Wikiquote Epictetus|https://en.wikiquote.org/wiki/Epictetus
Make the best use of what is in your power.|爱比克泰德|掌控感|Wikiquote Epictetus|https://en.wikiquote.org/wiki/Epictetus
No man is free who is not master of himself.|爱比克泰德|自由|Wikiquote Epictetus|https://en.wikiquote.org/wiki/Epictetus
Men are disturbed not by things, but by views.|爱比克泰德|认知|Wikiquote Epictetus|https://en.wikiquote.org/wiki/Epictetus
The impediment to action advances action.|马可·奥勒留|障碍|Wikiquote Marcus Aurelius|https://en.wikiquote.org/wiki/Marcus_Aurelius
Waste no more time arguing what a good man should be.|马可·奥勒留|行动|Wikiquote Marcus Aurelius|https://en.wikiquote.org/wiki/Marcus_Aurelius
You have power over your mind, not outside events.|马可·奥勒留|内在掌控|Wikiquote Marcus Aurelius|https://en.wikiquote.org/wiki/Marcus_Aurelius
The soul becomes dyed with the color of its thoughts.|马可·奥勒留|思想|Wikiquote Marcus Aurelius|https://en.wikiquote.org/wiki/Marcus_Aurelius
What we do now echoes in eternity.|马可·奥勒留|行动影响|Wikiquote Marcus Aurelius|https://en.wikiquote.org/wiki/Marcus_Aurelius
All the world's a stage.|莎士比亚|人生角色|Wikiquote William Shakespeare|https://en.wikiquote.org/wiki/William_Shakespeare
Brevity is the soul of wit.|莎士比亚|表达简洁|Wikiquote William Shakespeare|https://en.wikiquote.org/wiki/William_Shakespeare
To be, or not to be, that is the question.|莎士比亚|存在选择|Wikiquote William Shakespeare|https://en.wikiquote.org/wiki/William_Shakespeare
The better part of valor is discretion.|莎士比亚|勇敢与判断|Wikiquote William Shakespeare|https://en.wikiquote.org/wiki/William_Shakespeare
What's past is prologue.|莎士比亚|过去与未来|Wikiquote William Shakespeare|https://en.wikiquote.org/wiki/William_Shakespeare
Our doubts are traitors.|莎士比亚|怀疑|Wikiquote William Shakespeare|https://en.wikiquote.org/wiki/William_Shakespeare
There is nothing either good or bad, but thinking makes it so.|莎士比亚|认知|Wikiquote William Shakespeare|https://en.wikiquote.org/wiki/William_Shakespeare
Speak what we feel, not what we ought to say.|莎士比亚|真实表达|Wikiquote William Shakespeare|https://en.wikiquote.org/wiki/William_Shakespeare
Knowledge is power.|弗朗西斯·培根|知识|Wikiquote Francis Bacon|https://en.wikiquote.org/wiki/Francis_Bacon
Reading maketh a full man; conference a ready man; writing an exact man.|弗朗西斯·培根|读写表达|Wikiquote Francis Bacon|https://en.wikiquote.org/wiki/Francis_Bacon
Truth is the daughter of time.|弗朗西斯·培根|真相|Wikiquote Francis Bacon|https://en.wikiquote.org/wiki/Francis_Bacon
Silence is the virtue of fools.|弗朗西斯·培根|沉默|Wikiquote Francis Bacon|https://en.wikiquote.org/wiki/Francis_Bacon
Hope is a good breakfast, but it is a bad supper.|弗朗西斯·培根|希望|Wikiquote Francis Bacon|https://en.wikiquote.org/wiki/Francis_Bacon
I think, therefore I am.|笛卡尔|自我确认|Wikiquote René Descartes|https://en.wikiquote.org/wiki/Ren%C3%A9_Descartes
Doubt is the origin of wisdom.|笛卡尔|怀疑|Wikiquote René Descartes|https://en.wikiquote.org/wiki/Ren%C3%A9_Descartes
To live without philosophizing is to have one's eyes closed.|笛卡尔|思考|Wikiquote René Descartes|https://en.wikiquote.org/wiki/Ren%C3%A9_Descartes
Common sense is the best distributed thing in the world.|笛卡尔|常识|Wikiquote René Descartes|https://en.wikiquote.org/wiki/Ren%C3%A9_Descartes
We never understand a thing so well as when we teach it.|笛卡尔|表达与理解|Wikiquote René Descartes|https://en.wikiquote.org/wiki/Ren%C3%A9_Descartes
Man is born free, and everywhere he is in chains.|卢梭|自由与束缚|Wikiquote Jean-Jacques Rousseau|https://en.wikiquote.org/wiki/Jean-Jacques_Rousseau
Patience is bitter, but its fruit is sweet.|卢梭|耐心|Wikiquote Jean-Jacques Rousseau|https://en.wikiquote.org/wiki/Jean-Jacques_Rousseau
The world of reality has its limits; imagination is boundless.|卢梭|想象力|Wikiquote Jean-Jacques Rousseau|https://en.wikiquote.org/wiki/Jean-Jacques_Rousseau
Nature never deceives us; it is we who deceive ourselves.|卢梭|自欺|Wikiquote Jean-Jacques Rousseau|https://en.wikiquote.org/wiki/Jean-Jacques_Rousseau
Liberty consists in doing what one desires.|约翰·斯图亚特·密尔|自由|Wikiquote John Stuart Mill|https://en.wikiquote.org/wiki/John_Stuart_Mill
He who knows only his own side knows little of that.|约翰·斯图亚特·密尔|辩论|Wikiquote John Stuart Mill|https://en.wikiquote.org/wiki/John_Stuart_Mill
Originality is the one thing unoriginal minds cannot feel the use of.|约翰·斯图亚特·密尔|原创|Wikiquote John Stuart Mill|https://en.wikiquote.org/wiki/John_Stuart_Mill
Ask yourself whether you are happy, and you cease to be so.|约翰·斯图亚特·密尔|幸福|Wikiquote John Stuart Mill|https://en.wikiquote.org/wiki/John_Stuart_Mill
Genius can only breathe freely in an atmosphere of freedom.|约翰·斯图亚特·密尔|自由与创造|Wikiquote John Stuart Mill|https://en.wikiquote.org/wiki/John_Stuart_Mill
Sapere aude.|康德|独立思考|Wikiquote Immanuel Kant|https://en.wikiquote.org/wiki/Immanuel_Kant
Out of the crooked timber of humanity, no straight thing was ever made.|康德|人性复杂|Wikiquote Immanuel Kant|https://en.wikiquote.org/wiki/Immanuel_Kant
Thoughts without content are empty.|康德|思考|Wikiquote Immanuel Kant|https://en.wikiquote.org/wiki/Immanuel_Kant
Experience without theory is blind.|康德|经验与理论|Wikiquote Immanuel Kant|https://en.wikiquote.org/wiki/Immanuel_Kant
Act only according to that maxim whereby you can will it universal.|康德|原则|Wikiquote Immanuel Kant|https://en.wikiquote.org/wiki/Immanuel_Kant
What does not kill me makes me stronger.|尼采|逆境|Wikiquote Friedrich Nietzsche|https://en.wikiquote.org/wiki/Friedrich_Nietzsche
He who has a why can bear almost any how.|尼采|意义感|Wikiquote Friedrich Nietzsche|https://en.wikiquote.org/wiki/Friedrich_Nietzsche
There are no facts, only interpretations.|尼采|解释|Wikiquote Friedrich Nietzsche|https://en.wikiquote.org/wiki/Friedrich_Nietzsche
Become who you are.|尼采|自我生成|Wikiquote Friedrich Nietzsche|https://en.wikiquote.org/wiki/Friedrich_Nietzsche
One must still have chaos in oneself to give birth to a dancing star.|尼采|创造|Wikiquote Friedrich Nietzsche|https://en.wikiquote.org/wiki/Friedrich_Nietzsche
Without music, life would be a mistake.|尼采|生命感|Wikiquote Friedrich Nietzsche|https://en.wikiquote.org/wiki/Friedrich_Nietzsche
Convictions are more dangerous enemies of truth than lies.|尼采|执念|Wikiquote Friedrich Nietzsche|https://en.wikiquote.org/wiki/Friedrich_Nietzsche
The secret of being boring is to say everything.|伏尔泰|表达留白|Wikiquote Voltaire|https://en.wikiquote.org/wiki/Voltaire
Judge a man by his questions rather than his answers.|伏尔泰|提问|Wikiquote Voltaire|https://en.wikiquote.org/wiki/Voltaire
Doubt is not a pleasant condition, but certainty is absurd.|伏尔泰|怀疑|Wikiquote Voltaire|https://en.wikiquote.org/wiki/Voltaire
Common sense is not so common.|伏尔泰|常识|Wikiquote Voltaire|https://en.wikiquote.org/wiki/Voltaire
The best is the enemy of the good.|伏尔泰|完美主义|Wikiquote Voltaire|https://en.wikiquote.org/wiki/Voltaire
To be is to be perceived.|贝克莱|存在|Wikiquote George Berkeley|https://en.wikiquote.org/wiki/George_Berkeley
Custom is the great guide of human life.|休谟|习惯|Wikiquote David Hume|https://en.wikiquote.org/wiki/David_Hume
Reason is the slave of the passions.|休谟|理性与情绪|Wikiquote David Hume|https://en.wikiquote.org/wiki/David_Hume
Beauty is no quality in things themselves.|休谟|审美|Wikiquote David Hume|https://en.wikiquote.org/wiki/David_Hume
Truth springs from argument amongst friends.|休谟|讨论|Wikiquote David Hume|https://en.wikiquote.org/wiki/David_Hume
The life of man is solitary, poor, nasty, brutish, and short.|霍布斯|人性|Wikiquote Thomas Hobbes|https://en.wikiquote.org/wiki/Thomas_Hobbes
Leisure is the mother of philosophy.|霍布斯|闲暇|Wikiquote Thomas Hobbes|https://en.wikiquote.org/wiki/Thomas_Hobbes
Words are wise men's counters.|霍布斯|语言|Wikiquote Thomas Hobbes|https://en.wikiquote.org/wiki/Thomas_Hobbes
The end of knowledge is power.|霍布斯|知识与权力|Wikiquote Thomas Hobbes|https://en.wikiquote.org/wiki/Thomas_Hobbes
Curiosity is the lust of the mind.|霍布斯|好奇|Wikiquote Thomas Hobbes|https://en.wikiquote.org/wiki/Thomas_Hobbes
To thine own self be true.|莎士比亚|真诚|Wikiquote William Shakespeare|https://en.wikiquote.org/wiki/William_Shakespeare
Hell is other people.|萨特|他人与自我|Wikiquote Jean-Paul Sartre|https://en.wikiquote.org/wiki/Jean-Paul_Sartre
Existence precedes essence.|萨特|存在|Wikiquote Jean-Paul Sartre|https://en.wikiquote.org/wiki/Jean-Paul_Sartre
Man is condemned to be free.|萨特|自由代价|Wikiquote Jean-Paul Sartre|https://en.wikiquote.org/wiki/Jean-Paul_Sartre
Freedom is what we do with what is done to us.|萨特|自由与处境|Wikiquote Jean-Paul Sartre|https://en.wikiquote.org/wiki/Jean-Paul_Sartre
We do not know what we want and yet we are responsible for what we are.|萨特|责任|Wikiquote Jean-Paul Sartre|https://en.wikiquote.org/wiki/Jean-Paul_Sartre
One is not born, but rather becomes, a woman.|波伏娃|女性与生成|Wikiquote Simone de Beauvoir|https://en.wikiquote.org/wiki/Simone_de_Beauvoir
Change your life today.|波伏娃|行动|Wikiquote Simone de Beauvoir|https://en.wikiquote.org/wiki/Simone_de_Beauvoir
To catch a husband is an art; to hold him is a job.|波伏娃|关系|Wikiquote Simone de Beauvoir|https://en.wikiquote.org/wiki/Simone_de_Beauvoir
Representation of the world, like the world itself, is the work of men.|波伏娃|叙事权|Wikiquote Simone de Beauvoir|https://en.wikiquote.org/wiki/Simone_de_Beauvoir
Self-awareness is not self-knowledge.|波伏娃|自我认知|Wikiquote Simone de Beauvoir|https://en.wikiquote.org/wiki/Simone_de_Beauvoir
The most common way people give up their power is by thinking they don't have any.|艾丽斯·沃克|力量感|Wikiquote Alice Walker|https://en.wikiquote.org/wiki/Alice_Walker
No person is your friend who demands your silence.|艾丽斯·沃克|沉默与关系|Wikiquote Alice Walker|https://en.wikiquote.org/wiki/Alice_Walker
Hard times require furious dancing.|艾丽斯·沃克|韧性|Wikiquote Alice Walker|https://en.wikiquote.org/wiki/Alice_Walker
The animals of the world exist for their own reasons.|艾丽斯·沃克|平等|Wikiquote Alice Walker|https://en.wikiquote.org/wiki/Alice_Walker
Nobody is as powerful as we make them out to be.|艾丽斯·沃克|权力想象|Wikiquote Alice Walker|https://en.wikiquote.org/wiki/Alice_Walker
The personal is political.|卡罗尔·哈尼施|个人与社会|Wikiquote Feminism|https://en.wikiquote.org/wiki/Feminism
The master's tools will never dismantle the master's house.|奥德丽·洛德|结构与反抗|Wikiquote Audre Lorde|https://en.wikiquote.org/wiki/Audre_Lorde
Your silence will not protect you.|奥德丽·洛德|表达勇气|Wikiquote Audre Lorde|https://en.wikiquote.org/wiki/Audre_Lorde
I am deliberate and afraid of nothing.|奥德丽·洛德|勇气|Wikiquote Audre Lorde|https://en.wikiquote.org/wiki/Audre_Lorde
Caring for myself is self-preservation.|奥德丽·洛德|自我照顾|Wikiquote Audre Lorde|https://en.wikiquote.org/wiki/Audre_Lorde
No need to hurry. No need to sparkle. No need to be anybody but oneself.|弗吉尼亚·伍尔夫|自我|Wikiquote Virginia Woolf|https://en.wikiquote.org/wiki/Virginia_Woolf
Arrange whatever pieces come your way.|弗吉尼亚·伍尔夫|生活秩序|Wikiquote Virginia Woolf|https://en.wikiquote.org/wiki/Virginia_Woolf
Growing up is losing some illusions, in order to acquire others.|弗吉尼亚·伍尔夫|成长|Wikiquote Virginia Woolf|https://en.wikiquote.org/wiki/Virginia_Woolf
Language is wine upon the lips.|弗吉尼亚·伍尔夫|语言|Wikiquote Virginia Woolf|https://en.wikiquote.org/wiki/Virginia_Woolf
For most of history, Anonymous was a woman.|弗吉尼亚·伍尔夫|女性与历史|Wikiquote Virginia Woolf|https://en.wikiquote.org/wiki/Virginia_Woolf
The most courageous act is still to think for yourself.|香奈儿|独立思考|Wikiquote Coco Chanel|https://en.wikiquote.org/wiki/Coco_Chanel
In order to be irreplaceable one must always be different.|香奈儿|差异|Wikiquote Coco Chanel|https://en.wikiquote.org/wiki/Coco_Chanel
Simplicity is the keynote of all true elegance.|香奈儿|简洁|Wikiquote Coco Chanel|https://en.wikiquote.org/wiki/Coco_Chanel
Fashion passes, style remains.|香奈儿|风格|Wikiquote Coco Chanel|https://en.wikiquote.org/wiki/Coco_Chanel
Elegance is refusal.|香奈儿|选择|Wikiquote Coco Chanel|https://en.wikiquote.org/wiki/Coco_Chanel
If I have seen further, it is by standing on the shoulders of giants.|牛顿|借力|Wikiquote Isaac Newton|https://en.wikiquote.org/wiki/Isaac_Newton
Truth is ever to be found in simplicity.|牛顿|简洁与真相|Wikiquote Isaac Newton|https://en.wikiquote.org/wiki/Isaac_Newton
I can calculate the motion of heavenly bodies, but not the madness of people.|牛顿|人性复杂|Wikiquote Isaac Newton|https://en.wikiquote.org/wiki/Isaac_Newton
We build too many walls and not enough bridges.|牛顿相关引语|关系|Wikiquote Isaac Newton|https://en.wikiquote.org/wiki/Isaac_Newton
Tact is the knack of making a point without making an enemy.|牛顿相关引语|表达分寸|Wikiquote Isaac Newton|https://en.wikiquote.org/wiki/Isaac_Newton
Imagination is more important than knowledge.|爱因斯坦|想象力|Wikiquote Albert Einstein|https://en.wikiquote.org/wiki/Albert_Einstein
The important thing is not to stop questioning.|爱因斯坦|提问|Wikiquote Albert Einstein|https://en.wikiquote.org/wiki/Albert_Einstein
Everything should be made as simple as possible, but not simpler.|爱因斯坦|简洁|Wikiquote Albert Einstein|https://en.wikiquote.org/wiki/Albert_Einstein
Try not to become a man of success, but rather a man of value.|爱因斯坦|价值|Wikiquote Albert Einstein|https://en.wikiquote.org/wiki/Albert_Einstein
Peace cannot be kept by force; it can only be achieved by understanding.|爱因斯坦|理解|Wikiquote Albert Einstein|https://en.wikiquote.org/wiki/Albert_Einstein
The only thing we have to fear is fear itself.|罗斯福|恐惧|Wikiquote Franklin D. Roosevelt|https://en.wikiquote.org/wiki/Franklin_D._Roosevelt
The truth is found when men are free to pursue it.|罗斯福|自由与真相|Wikiquote Franklin D. Roosevelt|https://en.wikiquote.org/wiki/Franklin_D._Roosevelt
Confidence thrives on honesty, on honor, on obligations sacredly kept.|罗斯福|信任|Wikiquote Franklin D. Roosevelt|https://en.wikiquote.org/wiki/Franklin_D._Roosevelt
We cannot always build the future for our youth.|罗斯福|成长|Wikiquote Franklin D. Roosevelt|https://en.wikiquote.org/wiki/Franklin_D._Roosevelt
Rules are not necessarily sacred; principles are.|罗斯福|规则与原则|Wikiquote Franklin D. Roosevelt|https://en.wikiquote.org/wiki/Franklin_D._Roosevelt
Ask not what your country can do for you.|肯尼迪|责任|Wikiquote John F. Kennedy|https://en.wikiquote.org/wiki/John_F._Kennedy
The time to repair the roof is when the sun is shining.|肯尼迪|风险准备|Wikiquote John F. Kennedy|https://en.wikiquote.org/wiki/John_F._Kennedy
Leadership and learning are indispensable to each other.|肯尼迪|领导力|Wikiquote John F. Kennedy|https://en.wikiquote.org/wiki/John_F._Kennedy
We choose to go to the Moon.|肯尼迪|选择与挑战|Wikiquote John F. Kennedy|https://en.wikiquote.org/wiki/John_F._Kennedy
Conformity is the jailer of freedom.|肯尼迪|自由与一致|Wikiquote John F. Kennedy|https://en.wikiquote.org/wiki/John_F._Kennedy
The price of greatness is responsibility.|丘吉尔|责任|Wikiquote Winston Churchill|https://en.wikiquote.org/wiki/Winston_Churchill
Success is not final, failure is not fatal.|丘吉尔|成败|Wikiquote Winston Churchill|https://en.wikiquote.org/wiki/Winston_Churchill
History will be kind to me for I intend to write it.|丘吉尔|叙事权|Wikiquote Winston Churchill|https://en.wikiquote.org/wiki/Winston_Churchill
Courage is what it takes to stand up and speak.|丘吉尔|表达勇气|Wikiquote Winston Churchill|https://en.wikiquote.org/wiki/Winston_Churchill
If you're going through hell, keep going.|丘吉尔|坚持|Wikiquote Winston Churchill|https://en.wikiquote.org/wiki/Winston_Churchill
It always seems impossible until it's done.|曼德拉|行动|Wikiquote Nelson Mandela|https://en.wikiquote.org/wiki/Nelson_Mandela
Education is the most powerful weapon.|曼德拉|教育|Wikiquote Nelson Mandela|https://en.wikiquote.org/wiki/Nelson_Mandela
I never lose. I either win or learn.|曼德拉相关引语|学习心态|Wikiquote Nelson Mandela|https://en.wikiquote.org/wiki/Nelson_Mandela
May your choices reflect your hopes, not your fears.|曼德拉|选择|Wikiquote Nelson Mandela|https://en.wikiquote.org/wiki/Nelson_Mandela
Resentment is like drinking poison.|曼德拉相关引语|怨恨|Wikiquote Nelson Mandela|https://en.wikiquote.org/wiki/Nelson_Mandela
The journey of a thousand miles begins with one step.|传统谚语|行动|Chinese proverbs|https://en.wikiquote.org/wiki/Chinese_proverbs
Speech is silver, silence is golden.|传统谚语|沉默|Wikipedia|https://en.wikipedia.org/wiki/Speech_is_silver,_silence_is_golden
Well-timed silence hath more eloquence than speech.|马丁·塔珀|表达留白|Wikiquote Silence|https://en.wikiquote.org/wiki/Silence
Be silent always when you doubt your sense.|亚历山大·蒲柏|谨慎表达|Wikiquote Silence|https://en.wikiquote.org/wiki/Silence
More have repented of speech than of silence.|传统谚语|慎言|Wikiquote Silence|https://en.wikiquote.org/wiki/Silence
The pen is mightier than the sword.|爱德华·布尔沃-利顿|表达力量|Wikiquote Writing|https://en.wikiquote.org/wiki/Writing
The medium is the message.|麦克卢汉|媒介|Wikiquote Marshall McLuhan|https://en.wikiquote.org/wiki/Marshall_McLuhan
I disapprove of what you say, but I will defend your right to say it.|伏尔泰相关引语|表达自由|Wikiquote Voltaire|https://en.wikiquote.org/wiki/Voltaire
好好说话，是每一个人应当完成的事。|马东等《奇葩说》相关表述|表达训练|GQ|https://www.gq.com.cn/magazine/news_1111321a29d26819.html
平静的湖面，练不出强壮的水手。|傅首尔相关《奇葩说》发言|挑战|央视网|https://ent.cctv.com/2017/05/23/ARTIPNuxeO1hOJwtjcJ8xoFr170523.shtml
鞭策最大的问题在于：永无止境。|傅首尔相关《奇葩说》发言|关系|360娱乐|https://yule.360.com/content/607101
人类不需要伟大，活得有滋味已经非常棒了。|蔡康永|人生|Vogue Taiwan|https://www.vogue.com.tw/entertainment/article/tsaikang-quotes
越能理解别人，越不容易只想赢。|表达高手编辑部|讨论姿态|产品内置|internal
说服不是压倒对方，是让对方愿意往前走一步。|表达高手编辑部|说服|产品内置|internal
如果一句话没有对象，它很容易变成口号。|表达高手编辑部|表达练习|产品内置|internal
先承认对方的难，再提出你的路。|表达高手编辑部|说服结构|产品内置|internal
不要把复杂的人，讲成简单的标签。|表达高手编辑部|人群观察|产品内置|internal
""".strip()


def quote_seed_rows():
    rows = []
    for index, line in enumerate(QUOTE_SEED_TEXT.splitlines(), start=1):
        text, author, theme, source_label, source_url = [part.strip() for part in line.split("|", 4)]
        rows.append(
            {
                "id": f"quote-{index:03d}",
                "text": text,
                "author": author,
                "theme": theme,
                "sourceLabel": source_label,
                "sourceUrl": source_url,
            }
        )
    return rows


MODERN_QUOTE_SEED_TEXT = """
qipa-001|好好说话，是每一个人应当完成的事。|马东等《奇葩说》相关表述|表达训练|GQ|https://www.gq.com.cn/magazine/news_1111321a29d26819.html
qipa-002|平静的湖面，练不出强壮的水手。|傅首尔相关《奇葩说》发言|挑战|央视网|https://ent.cctv.com/2017/05/23/ARTIPNuxeO1hOJwtjcJ8xoFr170523.shtml
qipa-003|鞭策最大的问题在于：永无止境。|傅首尔相关《奇葩说》发言|亲密关系|360娱乐|https://yule.360.com/content/607101
qipa-004|人类不需要伟大，活得有滋味已经非常棒了。|蔡康永|人生|Vogue Taiwan|https://www.vogue.com.tw/entertainment/article/tsaikang-quotes
qipa-005|你以为你喜欢的人就是你喜欢的人吗，喜欢从来都是误会。|蔡康永|关系|新浪财经|https://cj.sina.com.cn/articles/view/6752490806/1927ad53600100thgj
qipa-006|每一段爱情都有一颗彩蛋，这颗彩蛋的名字叫成长。|《奇葩说》相关金句|亲密关系|新浪新闻|https://k.sina.cn/article_3207814252_bf335c6c00100e5pi.html
qipa-007|这个时代最杰出的头脑都已经毁于过度的精明。|詹青云相关《奇葩说》发言|时代观察|数英|https://www.digitaling.com/articles/253399.html
qipa-008|后悔意味着人相信可能。|詹青云相关《奇葩说》发言|后悔|数英|https://www.digitaling.com/articles/253399.html
qipa-009|不后悔背后的洒脱，也可能是彻底的绝望。|詹青云相关《奇葩说》发言|选择|数英|https://www.digitaling.com/articles/253399.html
qipa-010|我们真正想要的自由，是我可以精致但不必贫穷的自由。|詹青云相关《奇葩说》发言|自由|Reddit 摘录|https://www.reddit.com/r/DoubanGoosegroup/comments/uoittq
qipa-011|这是一个什么都缺，唯独不缺梦想的时代。|马薇薇相关《奇葩说》发言|梦想|句子控|https://www.juzikong.com/post/78c0e1fc-bb8f-4ed5-bea0-7d11218b2056
qipa-012|你要脱离大众做不一样的烟火，结果发现满地的鞭炮都比你使劲。|马薇薇相关《奇葩说》发言|自我|TOM 娱乐|https://ent.tom.com/201809/1922394842.html
qipa-013|没有不受重力的飞翔。|马薇薇相关《奇葩说》发言|自由与代价|作文素材 PDF|https://m.zwsc8.com/doc/ysqp.pdf
qipa-014|键盘侠只是在自己不专业的领域，说了几句自以为是的话。|李诞相关《奇葩说》发言|表达分寸|烟台大学共青团|https://youth.ytu.edu.cn/info/1004/8443.htm
qipa-015|哲学是一门反叛的学科，总是在推倒过去，挑战权威。|《奇葩说7》相关选手发言|思考|Reddit 摘录|https://www.reddit.com/r/u_getmalus/comments/khdsan
modern-001|When something is important enough, you do it even if the odds are not in your favor.|Elon Musk|行动|Wikiquote Elon Musk|https://en.wikiquote.org/wiki/Elon_Musk
modern-002|Failure is an option here. If things are not failing, you are not innovating enough.|Elon Musk|创新|Wikiquote Elon Musk|https://en.wikiquote.org/wiki/Elon_Musk
modern-003|Persistence is very important. You should not give up unless you are forced to give up.|Elon Musk|坚持|Wikiquote Elon Musk|https://en.wikiquote.org/wiki/Elon_Musk
modern-004|I could either watch it happen or be a part of it.|Elon Musk|参与|Wikiquote Elon Musk|https://en.wikiquote.org/wiki/Elon_Musk
modern-005|Great companies are built on great products.|Elon Musk|产品|Wikiquote Elon Musk|https://en.wikiquote.org/wiki/Elon_Musk
modern-006|I don’t do anything that I don’t think is important.|Elon Musk|选择|Wikiquote Elon Musk|https://en.wikiquote.org/wiki/Elon_Musk
modern-007|The first principle is that you must not fool yourself.|Richard Feynman|诚实|Wikiquote Richard Feynman|https://en.wikiquote.org/wiki/Richard_Feynman
modern-008|What I cannot create, I do not understand.|Richard Feynman|理解|Wikiquote Richard Feynman|https://en.wikiquote.org/wiki/Richard_Feynman
modern-009|The imagination of nature is far, far greater than the imagination of man.|Richard Feynman|想象|Wikiquote Richard Feynman|https://en.wikiquote.org/wiki/Richard_Feynman
modern-010|The best way to learn is to teach.|Richard Feynman 相关表述|学习|Wikiquote Richard Feynman|https://en.wikiquote.org/wiki/Richard_Feynman
modern-011|Your work is going to fill a large part of your life.|Steve Jobs|工作|Wikiquote Steve Jobs|https://en.wikiquote.org/wiki/Steve_Jobs
modern-012|Stay hungry, stay foolish.|Steve Jobs|成长|Wikiquote Steve Jobs|https://en.wikiquote.org/wiki/Steve_Jobs
modern-013|Innovation distinguishes between a leader and a follower.|Steve Jobs|创新|Wikiquote Steve Jobs|https://en.wikiquote.org/wiki/Steve_Jobs
modern-014|People don’t know what they want until you show it to them.|Steve Jobs|产品|Wikiquote Steve Jobs|https://en.wikiquote.org/wiki/Steve_Jobs
modern-015|The people who are crazy enough to think they can change the world are the ones who do.|Steve Jobs 相关广告语|改变|Wikiquote Steve Jobs|https://en.wikiquote.org/wiki/Steve_Jobs
modern-016|Suffering builds character.|Jensen Huang|磨难|Wikiquote Jensen Huang|https://en.wikiquote.org/wiki/Jensen_Huang
modern-017|No task is beneath me.|Jensen Huang|行动姿态|Wikiquote Jensen Huang|https://en.wikiquote.org/wiki/Jensen_Huang
modern-018|The world has changed. Everyone is a programmer now.|Jensen Huang|AI时代|Wikiquote Jensen Huang|https://en.wikiquote.org/wiki/Jensen_Huang
modern-019|Run, don’t walk.|Jensen Huang|速度|Esquire HK|https://www.esquirehk.com/money-investment/10-quotes-from-jensen-huang
modern-020|Every setback is a new opportunity.|Jensen Huang 相关金句|机会|Esquire HK|https://www.esquirehk.com/money-investment/10-quotes-from-jensen-huang
modern-021|I want to show girls that they can break boundaries.|Eileen Gu|女性成长|Wikiquote Eileen Gu|https://en.wikiquote.org/wiki/Eileen_Gu
modern-022|I am just trying to be myself.|Eileen Gu|自我|Wikiquote Eileen Gu|https://en.wikiquote.org/wiki/Eileen_Gu
modern-023|Sport is a platform to unite people.|Eileen Gu|连接|Wikiquote Eileen Gu|https://en.wikiquote.org/wiki/Eileen_Gu
modern-024|Fear is a really powerful thing, but courage is stronger.|Eileen Gu|勇气|Wikiquote Eileen Gu|https://en.wikiquote.org/wiki/Eileen_Gu
modern-025|I want to be a bridge.|Eileen Gu|身份与连接|Wikiquote Eileen Gu|https://en.wikiquote.org/wiki/Eileen_Gu
modern-026|The most common way people give up their power is by thinking they don’t have any.|Alice Walker|力量感|Wikiquote Alice Walker|https://en.wikiquote.org/wiki/Alice_Walker
modern-027|No person is your friend who demands your silence.|Alice Walker|沉默|Wikiquote Alice Walker|https://en.wikiquote.org/wiki/Alice_Walker
modern-028|Your silence will not protect you.|Audre Lorde|表达勇气|Wikiquote Audre Lorde|https://en.wikiquote.org/wiki/Audre_Lorde
modern-029|I am deliberate and afraid of nothing.|Audre Lorde|勇气|Wikiquote Audre Lorde|https://en.wikiquote.org/wiki/Audre_Lorde
modern-030|Caring for myself is self-preservation.|Audre Lorde|自我照顾|Wikiquote Audre Lorde|https://en.wikiquote.org/wiki/Audre_Lorde
modern-031|One is not born, but rather becomes, a woman.|Simone de Beauvoir|女性与生成|Wikiquote Simone de Beauvoir|https://en.wikiquote.org/wiki/Simone_de_Beauvoir
modern-032|Representation of the world, like the world itself, is the work of men.|Simone de Beauvoir|叙事权|Wikiquote Simone de Beauvoir|https://en.wikiquote.org/wiki/Simone_de_Beauvoir
modern-033|Freedom is what we do with what is done to us.|Jean-Paul Sartre|自由与处境|Wikiquote Jean-Paul Sartre|https://en.wikiquote.org/wiki/Jean-Paul_Sartre
modern-034|Man is condemned to be free.|Jean-Paul Sartre|自由代价|Wikiquote Jean-Paul Sartre|https://en.wikiquote.org/wiki/Jean-Paul_Sartre
modern-035|Hell is other people.|Jean-Paul Sartre|他人与自我|Wikiquote Jean-Paul Sartre|https://en.wikiquote.org/wiki/Jean-Paul_Sartre
modern-036|The personal is political.|Carol Hanisch|个人与社会|Wikiquote Feminism|https://en.wikiquote.org/wiki/Feminism
modern-037|The medium is the message.|Marshall McLuhan|媒介|Wikiquote Marshall McLuhan|https://en.wikiquote.org/wiki/Marshall_McLuhan
modern-038|We shape our tools and thereafter our tools shape us.|Marshall McLuhan|工具|Wikiquote Marshall McLuhan|https://en.wikiquote.org/wiki/Marshall_McLuhan
modern-039|The future is already here — it’s just not evenly distributed.|William Gibson|未来|Wikiquote William Gibson|https://en.wikiquote.org/wiki/William_Gibson
modern-040|The street finds its own uses for things.|William Gibson|创新|Wikiquote William Gibson|https://en.wikiquote.org/wiki/William_Gibson
""".strip()


def modern_quote_seed_rows():
    rows = []
    for line in MODERN_QUOTE_SEED_TEXT.splitlines():
        quote_id, text, author, theme, source_label, source_url = [part.strip() for part in line.split("|", 5)]
        rows.append(
            {
                "id": quote_id,
                "text": text,
                "author": author,
                "theme": theme,
                "sourceLabel": source_label,
                "sourceUrl": source_url,
            }
        )
    return rows


SPEAKER_QUOTE_SEED_TEXT = """
speaker-001|你说什么样的话，你就是什么样的人。|蔡康永|说话之道|《蔡康永的说话之道》相关资料|https://www.sumzi.com/upload/files/2011/08/2011082914440517861.pdf
speaker-002|沉默没问题的，沉默很正常的。|蔡康永|沟通姿态|《蔡康永的说话之道》相关资料|https://www.sumzi.com/upload/files/2011/08/2011082914440517861.pdf
speaker-003|把无谓的胜利丢给对方，懂得认输的人会说话。|蔡康永|沟通分寸|《蔡康永的说话之道》相关资料|https://www.sumzi.com/upload/files/2011/08/2011082914440517861.pdf
speaker-004|做自己跟没礼貌，常常就是一线之间。|蔡康永|表达边界|《蔡康永的说话之道》相关资料|https://www.sumzi.com/upload/files/2011/08/2011082914440517861.pdf
speaker-005|不是去爱那个本来就很美的人，而是去爱那个能使你的世界变美的人。|蔡康永|关系|udn 女子漾|https://woman.udn.com/woman/story/123164/7800443
speaker-006|人类不需要伟大，活得有滋味已经非常棒了。|蔡康永|人生|Vogue Taiwan|https://www.vogue.com.tw/entertainment/article/tsaikang-quotes
speaker-007|喜欢从来都是误会。|蔡康永|关系|新浪财经|https://cj.sina.com.cn/articles/view/6752490806/1927ad53600100thgj
speaker-008|想出另外十句可以接的话，不会让话题死掉。|蔡康永|聊天方法|《蔡康永的说话之道》相关资料|https://www.sumzi.com/upload/files/2011/08/2011082914440517861.pdf
speaker-009|人间不值得，不是说人间不值得你活。|李诞|人生态度|新浪新闻|https://k.sina.cn/article_1233279910_49825ba600100friv.html
speaker-010|你只有真正努力过，才有资格说佛系。|李诞|努力|新浪新闻|https://k.sina.cn/article_2687299131_a02cee3b01900uy4e.html
speaker-011|提升自己，耐心等待。|李诞|成长|新浪新闻|https://k.sina.cn/article_2687299131_a02cee3b01900uy4e.html
speaker-012|学音乐要像学母语那样学。|李诞|学习|新浪新闻|https://k.sina.cn/article_1731986465_673c042100100c67i.html
speaker-013|在自己不专业的领域，说几句自以为是的话，很容易。|李诞相关《奇葩说》发言|表达分寸|烟台大学共青团|https://youth.ytu.edu.cn/info/1004/8443.htm
speaker-014|爱情和酒是一样的东西，第一次喝是最猛的。|李诞直播相关语录|关系|运营派|https://www.yunyingpai.com/media/1050427.html
speaker-015|仪式感不是形式主义，是给生活一个提醒。|李诞相关语录|生活感|新浪新闻|https://k.sina.com.cn/article_6926176449_19cd510c10010135db.html
speaker-016|辩论最大的魅力，是思想上的转变。|黄执中|辩论|新浪教育|https://edu.sina.com.cn/l/2010-09-30/1004193852.shtml
speaker-017|语言已经到达巅峰时，剩下的就是疲乏。|黄执中|语言边界|新浪教育|https://edu.sina.com.cn/l/2010-09-30/1004193852.shtml
speaker-018|如晶是一个很成熟的小孩，我是一个很小孩的大人。|黄执中|自我观察|TOPYS|https://www.topys.cn/article/28384
speaker-019|撒泼打滚类的选手在《奇葩说》更吃香。|黄执中|节目观察|TOPYS|https://www.topys.cn/article/28384
speaker-020|辩论还可以这么拆解。|黄执中评价熊浩相关表述|辩论拆解|脉脉|https://maimai.cn/article/detail?efid=hJv72_77aZRzdbwabJQ7pw&fid=1358188783
speaker-021|岁月是一场有去无回的浪漫。|黄执中相关语录|时间|奇怪网整理|https://www.qiguaiwang.com/read-21997.html
speaker-022|我们确实有些套路，笑点、观点、泪点。|熊浩|表达结构|梨视频|https://www.pearvideo.com/video_1717706
speaker-023|人们接受外界影响时，有深层逻辑。|熊浩|影响力|梨视频|https://www.pearvideo.com/video_1717706
speaker-024|爱情当中最本质的力量不是合适，而是我愿意。|熊浩|关系|腾讯云开发者社区|https://cloud.tencent.com/developer/news/350344
speaker-025|合适这件事跟真爱，一点关系都没有。|熊浩|关系|腾讯云开发者社区|https://cloud.tencent.com/developer/news/350344
speaker-026|我想知道我自己，也想知道我有没有信心面对更好的世界。|熊浩|自我认识|腾讯云开发者社区|https://cloud.tencent.com/developer/news/350344
speaker-027|将微光照进现实。|熊浩相关报道|现实感|360娱乐|https://yule.360.com/detail/2638218
speaker-028|表达思维像一个翻译机器，把晦涩论据转化成简洁观点。|熊浩相关报道|表达方法|南方plus|https://static.nfapp.southcn.com/content/201811/26/c1696118.html
speaker-029|人是人这句话永远不会错，因为它没有意义。|陈铭|判断|武汉纺织大学|https://ec.wtu.edu.cn/info/1166/6087.htm
speaker-030|我们要真实地表达当下最真实的想法。|陈铭|真实表达|游乐园整理|https://www.17yly.com/wiki/295162.html
speaker-031|真实表达，是对这个社会最大的善意。|陈铭|表达善意|游乐园整理|https://www.17yly.com/wiki/295162.html
speaker-032|鸡汤也需要正确的姿势。|陈铭相关报道|表达方式|央视网|https://ent.cctv.com/2017/06/05/ARTIyMoUrfFxO6B2ZJctIqXp170605.shtml
speaker-033|会说话不只是技巧，也是一种把人放在心上的能力。|陈铭相关报道|沟通|新浪新闻|https://k.sina.com.cn/article_2091622063_7cab9eaf01900eavc.html
speaker-034|前任有时像磨刀石，把人调教成更好的人。|陈铭相关《奇葩说》发言|关系|酒泉信息网整理|https://tj.jiuquan.cc/a-2236459/
speaker-035|你只引用了前半句，后半句被你隐藏了。|陈铭相关《奇葩说》发言|反驳|新浪新闻|https://k.sina.cn/article_1894475142_70eb6586020010eyc.html
speaker-036|不要只追求赢，要追求让别人听懂你为什么这么想。|表达高手编辑部整理方向|表达训练|产品内置|internal
""".strip()


def speaker_quote_seed_rows():
    rows = []
    for line in SPEAKER_QUOTE_SEED_TEXT.splitlines():
        quote_id, text, author, theme, source_label, source_url = [part.strip() for part in line.split("|", 5)]
        rows.append(
            {
                "id": quote_id,
                "text": text,
                "author": author,
                "theme": theme,
                "sourceLabel": source_label,
                "sourceUrl": source_url,
            }
        )
    return rows

DEFAULT_HISTORY = [
    {
        "id": "history-seed-1",
        "title": "第1轮｜自由 + 束缚",
        "timeLabel": "04-19 10:32",
        "pair": ["自由", "束缚"],
        "excerpt": "我会把自由理解成一种更高级的束缚，因为真正长久的自由，往往建立在自我约束和边界感之上。",
        "score": 86,
        "summary": "判断句成立，解释方向清楚，已经有现代人常见困惑的味道。",
        "details": [
            {"label": "判断句", "score": 90, "note": "开头已经提出清晰判断。"},
            {"label": "合理性解释", "score": 82, "note": "可以再补一个更具体的生活场景。"},
            {"label": "表达完整度", "score": 86, "note": "结尾已经有收束，但还可以再更鲜明一点。"},
        ],
        "suggestions": ["补一个你真实经历过的选择场景。", "解释清楚“为什么没有束缚反而不自由”。"],
    },
    {
        "id": "history-seed-2",
        "title": "第1轮｜成长 + 谎言",
        "timeLabel": "04-18 21:14",
        "pair": ["成长", "谎言"],
        "excerpt": "我觉得成长有时是一种谎言，因为很多人嘴上说自己变成熟了，本质上只是学会了隐藏脆弱。",
        "score": 91,
        "summary": "观点很抓人，也有社会讨论度，适合在 H5 场景里形成传播。",
        "details": [
            {"label": "判断句", "score": 95, "note": "判断句很有张力，也有讨论空间。"},
            {"label": "解释逻辑", "score": 88, "note": "解释已经成立，但可以更生活化。"},
            {"label": "语言张力", "score": 90, "note": "有明显观点感，适合短内容传播。"},
        ],
        "suggestions": ["补一句你为什么反感“成长叙事”。", "再举一个成年人隐藏情绪的细节。"],
    },
]


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def json_dumps(value):
    return json.dumps(value, ensure_ascii=False)


def json_loads(value, default=None):
    if not value:
        return default if default is not None else []
    return json.loads(value)


def read_runtime_config_file():
    config = {}
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            config = {}
    return config


def read_runtime_config_from_db():
    if not DB_PATH.exists():
        return {}
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT config_key, config_value FROM app_config WHERE config_key LIKE 'runtime.%'"
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return {}

    config = {}
    for row in rows:
        key = row["config_key"].replace("runtime.", "", 1)
        raw = row["config_value"]
        if key == "require_real_ai":
            config[key] = str(raw).lower() in ("1", "true", "yes")
        else:
            config[key] = raw
    return config


def load_runtime_config():
    file_config = read_runtime_config_file()
    db_config = read_runtime_config_from_db()

    return {
        "model_api_url": os.getenv("MODEL_API_URL", db_config.get("model_api_url", file_config.get("model_api_url", ""))),
        "model_api_key": os.getenv("MODEL_API_KEY", db_config.get("model_api_key", file_config.get("model_api_key", ""))),
        "model_api_model": os.getenv("MODEL_API_MODEL", db_config.get("model_api_model", file_config.get("model_api_model", "gpt-4o"))),
        "model_provider_code": os.getenv(
            "MODEL_PROVIDER_CODE",
            db_config.get("model_provider_code", file_config.get("model_provider_code", "yunwu")),
        ),
        "require_real_ai": str(
            os.getenv("REQUIRE_REAL_AI", db_config.get("require_real_ai", file_config.get("require_real_ai", False)))
        ).lower() in ("1", "true", "yes"),
    }


PAYMENT_PLAN_CATALOG = {
    "trial7": {
        "planId": "trial7",
        "planName": "7天观点唤醒",
        "displayPrice": 29,
        "testPrice": 29.0,
        "livePrice": 29.0,
        "days": 7,
        "totalCredits": 30,
        "description": "30次教练点评 · 7个自然日内有效",
        "tagline": "先把表达的语感练出来。",
        "fitFor": "适合刚开始练，先把表达的语感找回来",
    },
    "month30": {
        "planId": "month30",
        "planName": "30天表达养成",
        "displayPrice": 89,
        "testPrice": 89.0,
        "livePrice": 89.0,
        "days": 30,
        "totalCredits": 150,
        "description": "150次教练点评 · 30个自然日内有效",
        "tagline": "把思路练顺，把表达练熟。",
        "fitFor": "适合想持续训练，把表达练进日常。",
    },
}

FREE_TRIAL_CREDITS = 1
FREE_TRIAL_DAYS = 7
REGISTER_DEVICE_LIMIT = 2
DAILY_FLIP_LIMIT_INACTIVE = 8
DAILY_FLIP_LIMIT_GIFT = 14
DAILY_FLIP_LIMIT_PAID = 30


def app_config_value(conn, key, default=""):
    row = conn.execute(
        "SELECT config_value FROM app_config WHERE config_key = ?",
        (key,),
    ).fetchone()
    return row["config_value"] if row else default


def app_config_int(conn, key, default):
    try:
        return int(os.getenv(key.upper().replace(".", "_"), app_config_value(conn, key, default)))
    except (TypeError, ValueError):
        return default


def app_config_list(conn, key, default=""):
    raw = os.getenv(key.upper().replace(".", "_"), app_config_value(conn, key, default))
    return [item.strip() for item in str(raw or "").split(",") if item.strip()]


def free_trial_config(conn):
    return {
        "credits": max(0, app_config_int(conn, "account.free_trial_credits", FREE_TRIAL_CREDITS)),
        "days": max(1, app_config_int(conn, "account.free_trial_days", FREE_TRIAL_DAYS)),
    }


def register_device_config(conn):
    return {
        "limit": max(1, app_config_int(conn, "account.register_device_limit", REGISTER_DEVICE_LIMIT)),
        "whitelist": set(app_config_list(conn, "account.register_device_whitelist", "")),
    }


def training_flip_limit_config(conn):
    return {
        "inactive": max(0, app_config_int(conn, "training.flip_limit.inactive", DAILY_FLIP_LIMIT_INACTIVE)),
        "gift": max(0, app_config_int(conn, "training.flip_limit.gift", DAILY_FLIP_LIMIT_GIFT)),
        "paid": max(0, app_config_int(conn, "training.flip_limit.paid", DAILY_FLIP_LIMIT_PAID)),
    }


def load_payment_demo_config():
    file_config = read_runtime_config_file()
    return {
        "pid": os.getenv("ZPAY_PID", file_config.get("zpay_pid", "")),
        "key": os.getenv("ZPAY_KEY", file_config.get("zpay_key", "")),
        "submit_url": os.getenv("ZPAY_SUBMIT_URL", file_config.get("zpay_submit_url", "https://zpayz.cn/submit.php")),
        "order_query_url": os.getenv("ZPAY_ORDER_QUERY_URL", file_config.get("zpay_order_query_url", "https://zpayz.cn/api.php")),
    }


def zpay_sign(params, key):
    sign_parts = []
    for name in sorted(params.keys()):
        value = params[name]
        if name in ("sign", "sign_type", "payReturn") or value in ("", None):
            continue
        sign_parts.append(f"{name}={value}")
    raw = "&".join(sign_parts) + key
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def payment_demo_base_url(handler):
    forwarded_proto = handler.headers.get("X-Forwarded-Proto")
    scheme = forwarded_proto or "http"
    host = handler.headers.get("Host", f"127.0.0.1:{PORT}")
    return f"{scheme}://{host}"


def is_local_base_url(base_url):
    parsed = urlparse(base_url or "")
    hostname = parsed.hostname or ""
    if hostname in {"127.0.0.1", "localhost", "::1"}:
        return True
    if re.match(r"^192\.168\.\d+\.\d+$", hostname):
        return True
    if re.match(r"^10\.\d+\.\d+\.\d+$", hostname):
        return True
    if re.match(r"^172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+$", hostname):
        return True
    return False


def payment_plan_payload(plan, base_url=""):
    amount = plan["testPrice"] if is_local_base_url(base_url) else plan["livePrice"]
    return {
        "planId": plan["planId"],
        "planName": plan["planName"],
        "displayPrice": plan["displayPrice"],
        "amount": amount,
        "days": plan["days"],
        "totalCredits": plan["totalCredits"],
        "totalGroups": plan["totalCredits"],
        "description": plan["description"],
        "tagline": plan["tagline"],
        "fitFor": plan["fitFor"],
    }


def plan_charge_amount(plan, base_url=""):
    return plan["testPrice"] if is_local_base_url(base_url) else plan["livePrice"]


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          nickname TEXT NOT NULL,
          started_rounds_today INTEGER NOT NULL DEFAULT 0,
          current_round_index INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS membership (
          user_id INTEGER PRIMARY KEY,
          is_member INTEGER NOT NULL DEFAULT 0,
          plan_name TEXT NOT NULL DEFAULT '普通版'
        );

        CREATE TABLE IF NOT EXISTS words (
          id TEXT PRIMARY KEY,
          deck_id TEXT NOT NULL,
          word TEXT NOT NULL,
          kind TEXT NOT NULL DEFAULT 'adjective',
          position_index INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'published',
          used_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sessions (
          id TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL,
          round_no INTEGER NOT NULL,
          source_deck_id TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active',
          selected_json TEXT NOT NULL DEFAULT '[]',
          draft_text TEXT NOT NULL DEFAULT '',
          attempt_count INTEGER NOT NULL DEFAULT 0,
          feedback_json TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS session_cards (
          id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL,
          word TEXT NOT NULL,
          kind TEXT NOT NULL DEFAULT 'adjective',
          position_index INTEGER NOT NULL,
          state TEXT NOT NULL DEFAULT 'hidden'
        );

        CREATE TABLE IF NOT EXISTS history_records (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          session_id TEXT,
          time_label TEXT NOT NULL,
          pair_json TEXT NOT NULL,
          excerpt TEXT NOT NULL,
          transcript_text TEXT NOT NULL DEFAULT '',
          score INTEGER NOT NULL,
          summary TEXT NOT NULL,
          details_json TEXT NOT NULL,
          suggestions_json TEXT NOT NULL,
          attempts_json TEXT NOT NULL DEFAULT '[]',
          final_feedback_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS coaching_attempts (
          id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL,
          attempt_no INTEGER NOT NULL,
          transcript_text TEXT NOT NULL,
          feedback_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS membership_orders (
          id TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL,
          amount REAL NOT NULL,
          status TEXT NOT NULL,
          paid_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS redeem_codes (
          code TEXT PRIMARY KEY,
          plan_name TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active',
          used_by INTEGER,
          used_at TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_quotes (
          id TEXT PRIMARY KEY,
          quote_text TEXT NOT NULL,
          author TEXT NOT NULL,
          theme TEXT NOT NULL DEFAULT '',
          source_label TEXT NOT NULL DEFAULT '',
          source_url TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'published',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS deleted_daily_quotes (
          id TEXT PRIMARY KEY,
          quote_text TEXT NOT NULL DEFAULT '',
          deleted_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS deleted_words (
          id TEXT PRIMARY KEY,
          deck_id TEXT NOT NULL DEFAULT '',
          word TEXT NOT NULL,
          deleted_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_prompts (
          prompt_key TEXT PRIMARY KEY,
          prompt_name TEXT NOT NULL,
          version_no INTEGER NOT NULL,
          system_prompt TEXT NOT NULL,
          user_prompt_template TEXT NOT NULL,
          model_name TEXT NOT NULL,
          provider_code TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'published',
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_prompt_versions (
          id TEXT PRIMARY KEY,
          prompt_key TEXT NOT NULL,
          prompt_name TEXT NOT NULL,
          version_no INTEGER NOT NULL,
          system_prompt TEXT NOT NULL,
          user_prompt_template TEXT NOT NULL,
          model_name TEXT NOT NULL,
          provider_code TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'published',
          change_note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          UNIQUE(prompt_key, version_no)
        );

        CREATE TABLE IF NOT EXISTS ai_jobs (
          id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL,
          prompt_key TEXT NOT NULL,
          version_no INTEGER NOT NULL,
          provider_code TEXT NOT NULL,
          model_name TEXT NOT NULL,
          status TEXT NOT NULL,
          selected_words_json TEXT NOT NULL,
          transcript_text TEXT NOT NULL,
          request_json TEXT NOT NULL,
          response_json TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_prompt_tests (
          id TEXT PRIMARY KEY,
          prompt_key TEXT NOT NULL,
          version_no INTEGER NOT NULL,
          provider_code TEXT NOT NULL,
          model_name TEXT NOT NULL,
          input_json TEXT NOT NULL,
          output_json TEXT,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_models (
          id TEXT PRIMARY KEY,
          model_name TEXT NOT NULL,
          display_name TEXT NOT NULL,
          provider_code TEXT NOT NULL DEFAULT 'yunwu',
          api_key TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'active',
          version_note TEXT NOT NULL DEFAULT '',
          last_test_status TEXT NOT NULL DEFAULT '',
          last_test_message TEXT NOT NULL DEFAULT '',
          last_test_at TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS prompt_eval_batches (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          prompt_key TEXT NOT NULL,
          version_no INTEGER NOT NULL,
          model_name TEXT NOT NULL,
          provider_code TEXT NOT NULL,
          sample_count INTEGER NOT NULL,
          success_count INTEGER NOT NULL DEFAULT 0,
          error_count INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS prompt_eval_results (
          id TEXT PRIMARY KEY,
          batch_id TEXT NOT NULL,
          sample_id TEXT NOT NULL,
          selected_words_json TEXT NOT NULL,
          attempt_no INTEGER NOT NULL,
          user_text TEXT NOT NULL,
          prompt_version INTEGER NOT NULL,
          provider_code TEXT NOT NULL,
          model_name TEXT NOT NULL,
          total_score INTEGER,
          dimension_scores_json TEXT NOT NULL DEFAULT '{}',
          summary TEXT NOT NULL DEFAULT '',
          details_json TEXT NOT NULL DEFAULT '[]',
          next_task TEXT NOT NULL DEFAULT '',
          rewrite TEXT NOT NULL DEFAULT '',
          raw_response_json TEXT,
          error TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS app_config (
          config_key TEXT PRIMARY KEY,
          config_value TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS admin_daily_snapshots (
          snapshot_date TEXT PRIMARY KEY,
          metrics_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS training_events (
          id TEXT PRIMARY KEY,
          event_name TEXT NOT NULL,
          event_key TEXT NOT NULL UNIQUE,
          user_id INTEGER,
          session_id TEXT,
          pair_json TEXT NOT NULL DEFAULT '[]',
          metadata_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payment_demo_accounts (
          client_id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          phone TEXT NOT NULL,
          plan_id TEXT NOT NULL,
          plan_name TEXT NOT NULL,
          total_groups INTEGER NOT NULL DEFAULT 0,
          remaining_groups INTEGER NOT NULL DEFAULT 0,
          activated_at TEXT NOT NULL,
          expire_at TEXT NOT NULL,
          current_order_no TEXT NOT NULL DEFAULT '',
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payment_demo_orders (
          order_no TEXT PRIMARY KEY,
          client_id TEXT NOT NULL,
          phone TEXT NOT NULL,
          plan_id TEXT NOT NULL,
          plan_name TEXT NOT NULL,
          amount REAL NOT NULL,
          total_groups INTEGER NOT NULL DEFAULT 0,
          total_days INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL DEFAULT 'pending',
          pay_type TEXT NOT NULL DEFAULT 'alipay',
          zpay_trade_no TEXT NOT NULL DEFAULT '',
          submit_payload_json TEXT NOT NULL DEFAULT '{}',
          callback_payload_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          paid_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS payment_demo_users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          phone TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          registered_client_id TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payment_demo_auth_sessions (
          token TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL,
          client_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payment_demo_memberships (
          user_id INTEGER PRIMARY KEY,
          phone TEXT NOT NULL,
          plan_id TEXT NOT NULL,
          plan_name TEXT NOT NULL,
          total_groups INTEGER NOT NULL DEFAULT 0,
          remaining_groups INTEGER NOT NULL DEFAULT 0,
          activated_at TEXT NOT NULL,
          expire_at TEXT NOT NULL,
          current_order_no TEXT NOT NULL DEFAULT '',
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS admin_pending_entitlements (
          phone TEXT PRIMARY KEY,
          credits INTEGER NOT NULL DEFAULT 0,
          days INTEGER NOT NULL DEFAULT 0,
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS admin_entitlement_adjustments (
          id TEXT PRIMARY KEY,
          phone TEXT NOT NULL,
          user_id INTEGER,
          credits INTEGER NOT NULL DEFAULT 0,
          days INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );
        """
    )

    user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "client_id" not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN client_id TEXT")
    if "contact" not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN contact TEXT NOT NULL DEFAULT ''")
    if "is_registered" not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN is_registered INTEGER NOT NULL DEFAULT 0")
    if "registered_at" not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN registered_at TEXT")
    if "created_at" not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN created_at TEXT")

    history_columns = {row["name"] for row in conn.execute("PRAGMA table_info(history_records)").fetchall()}
    if "user_id" not in history_columns:
        cur.execute("ALTER TABLE history_records ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
    if "session_id" not in history_columns:
        cur.execute("ALTER TABLE history_records ADD COLUMN session_id TEXT")
    if "transcript_text" not in history_columns:
        cur.execute("ALTER TABLE history_records ADD COLUMN transcript_text TEXT NOT NULL DEFAULT ''")
    if "attempts_json" not in history_columns:
        cur.execute("ALTER TABLE history_records ADD COLUMN attempts_json TEXT NOT NULL DEFAULT '[]'")
    if "final_feedback_json" not in history_columns:
        cur.execute("ALTER TABLE history_records ADD COLUMN final_feedback_json TEXT NOT NULL DEFAULT '{}'")

    session_columns = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    if "attempt_count" not in session_columns:
        cur.execute("ALTER TABLE sessions ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0")

    payment_order_columns = {row["name"] for row in conn.execute("PRAGMA table_info(payment_demo_orders)").fetchall()}
    if "user_id" not in payment_order_columns:
        cur.execute("ALTER TABLE payment_demo_orders ADD COLUMN user_id INTEGER")
    payment_user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(payment_demo_users)").fetchall()}
    if "app_user_id" not in payment_user_columns:
        cur.execute("ALTER TABLE payment_demo_users ADD COLUMN app_user_id INTEGER")
    if "registered_client_id" not in payment_user_columns:
        cur.execute("ALTER TABLE payment_demo_users ADD COLUMN registered_client_id TEXT NOT NULL DEFAULT ''")

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_client_id ON users(client_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_training_events_name_created ON training_events(event_name, created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_training_events_session ON training_events(session_id)")

    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        cur.execute(
            """
            INSERT INTO users
            (id, nickname, started_rounds_today, current_round_index, client_id, contact, is_registered, registered_at, created_at)
            VALUES (1, ?, 0, 0, 'legacy-demo-user', '', 0, NULL, ?)
            """,
            ("表达高手体验官", now_text()),
        )
        cur.execute(
            "INSERT INTO membership (user_id, is_member, plan_name) VALUES (1, 0, '普通版')"
        )
    else:
        cur.execute(
            "UPDATE users SET client_id = COALESCE(client_id, 'legacy-demo-user'), created_at = COALESCE(created_at, ?) WHERE id = 1",
            (now_text(),),
        )

    deleted_word_values = {
        (row["deck_id"], row["word"])
        for row in cur.execute("SELECT deck_id, word FROM deleted_words").fetchall()
    }
    cur.execute("DELETE FROM words")
    for deck in WORD_DECKS:
        for index, word in enumerate(deck["cards"]):
            if (deck["id"], word) in deleted_word_values:
                continue
            cur.execute(
                """
                INSERT INTO words (id, deck_id, word, position_index)
                VALUES (?, ?, ?, ?)
                """,
                (f"{deck['id']}-{index + 1}", deck["id"], word, index),
            )

    for record in DEFAULT_HISTORY:
        cur.execute(
            """
        INSERT OR REPLACE INTO history_records
            (id, title, session_id, time_label, pair_json, excerpt, transcript_text, score, summary, details_json, suggestions_json, attempts_json, final_feedback_json, created_at, user_id)
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '{}', COALESCE((SELECT created_at FROM history_records WHERE id = ?), ?), 1)
            """,
            (
                record["id"],
                record["title"],
                record["timeLabel"],
                json_dumps(record["pair"]),
                record["excerpt"],
                record["excerpt"],
                record["score"],
                record["summary"],
                json_dumps(record["details"]),
                json_dumps(record["suggestions"]),
                record["id"],
                now_text(),
            ),
        )

    if cur.execute("SELECT COUNT(*) FROM membership_orders").fetchone()[0] == 0:
        cur.executemany(
            """
            INSERT INTO membership_orders (id, user_id, amount, status, paid_at)
            VALUES (?, 1, ?, ?, ?)
            """,
            [
                ("KK20260419001", 19, "已支付", "2026-04-19 09:23:00"),
                ("KK20260418007", 19, "已支付", "2026-04-18 22:10:00"),
            ],
        )

    cur.execute(
        """
        INSERT OR IGNORE INTO training_events
        (id, event_name, event_key, user_id, session_id, pair_json, metadata_json, created_at)
        SELECT
          'evt-' || lower(hex(randomblob(5))),
          'speaking_page_entered',
          'speaking_page_entered:' || id,
          user_id,
          id,
          selected_json,
          json_object('source', 'backfill_sessions'),
          created_at
        FROM sessions
        WHERE json_array_length(selected_json) >= 2
        """
    )
    cur.execute(
        """
        INSERT OR IGNORE INTO training_events
        (id, event_name, event_key, user_id, session_id, pair_json, metadata_json, created_at)
        SELECT
          'evt-' || lower(hex(randomblob(5))),
          'coach_feedback_submitted',
          'coach_feedback_submitted:' || COALESCE(session_id, id),
          user_id,
          COALESCE(session_id, id),
          pair_json,
          json_object('source', 'backfill_history'),
          MIN(created_at)
        FROM history_records
        GROUP BY COALESCE(session_id, id)
        """
    )
    cur.execute(
        """
        INSERT OR IGNORE INTO training_events
        (id, event_name, event_key, user_id, session_id, pair_json, metadata_json, created_at)
        SELECT
          'evt-' || lower(hex(randomblob(5))),
          'coach_feedback_success',
          'coach_feedback_success:' || session_id,
          NULL,
          session_id,
          COALESCE(selected_words_json, '[]'),
          json_object('source', 'backfill_ai_jobs'),
          MIN(updated_at)
        FROM ai_jobs
        WHERE status = 'success'
        GROUP BY session_id
        """
    )

    if cur.execute("SELECT COUNT(*) FROM redeem_codes").fetchone()[0] == 0:
        cur.executemany(
            """
            INSERT INTO redeem_codes (code, plan_name, status, used_by, used_at)
            VALUES (?, ?, 'active', NULL, NULL)
            """,
            [
                ("GAOSHOU-2026-VIP", "高手会员"),
                ("XIAOHONGSHU-TRIAL", "高手会员"),
                ("BIAODA-GROWTH", "高手会员"),
            ],
        )

    cur.execute(
        """
        INSERT OR IGNORE INTO deleted_daily_quotes (id, quote_text, deleted_at)
        VALUES ('speaker-019', '撒泼打滚类的选手在《奇葩说》更吃香。', ?)
        """,
        (now_text(),),
    )

    for item in [*quote_seed_rows(), *modern_quote_seed_rows(), *speaker_quote_seed_rows()]:
        cur.execute(
            """
            INSERT OR IGNORE INTO daily_quotes
            (id, quote_text, author, theme, source_label, source_url, status, created_at, updated_at)
            SELECT ?, ?, ?, ?, ?, ?, 'published', ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM deleted_daily_quotes WHERE id = ?)
            """,
            (
                item["id"],
                item["text"],
                item["author"],
                item["theme"],
                item["sourceLabel"],
                item["sourceUrl"],
                now_text(),
                now_text(),
                item["id"],
            ),
        )
    cur.execute(
        """
        UPDATE daily_quotes
        SET status = 'hidden', updated_at = ?
        WHERE id LIKE 'quote-%'
          AND (
            author = '表达高手编辑部'
            OR source_url LIKE 'https://ctext.org%'
            OR source_label LIKE '《%'
            OR source_label LIKE '%诗文%'
            OR source_label LIKE '%文集%'
          )
        """,
        (now_text(),),
    )
    hidden_quote_rows = cur.execute("SELECT id, quote_text FROM daily_quotes WHERE status = 'hidden'").fetchall()
    for row in hidden_quote_rows:
        cur.execute(
            "INSERT OR IGNORE INTO deleted_daily_quotes (id, quote_text, deleted_at) VALUES (?, ?, ?)",
            (row["id"], row["quote_text"], now_text()),
        )
    cur.execute("DELETE FROM daily_quotes WHERE status = 'hidden'")
    cur.execute(
        """
        DELETE FROM daily_quotes
        WHERE id IN (SELECT id FROM deleted_daily_quotes)
           OR quote_text LIKE '%撒泼打滚%'
        """
    )

    file_runtime_config = read_runtime_config_file()
    if cur.execute("SELECT COUNT(*) FROM app_config").fetchone()[0] == 0:
        initial_runtime_config = {
            "model_api_url": file_runtime_config.get("model_api_url", ""),
            "model_api_key": file_runtime_config.get("model_api_key", ""),
            "model_api_model": file_runtime_config.get("model_api_model", "gpt-4o"),
            "model_provider_code": file_runtime_config.get("model_provider_code", "yunwu"),
            "require_real_ai": file_runtime_config.get("require_real_ai", False),
        }
        cur.executemany(
            """
            INSERT OR REPLACE INTO app_config (config_key, config_value, updated_at)
            VALUES (?, ?, ?)
            """,
            [
                ("runtime.model_api_url", initial_runtime_config["model_api_url"], now_text()),
                ("runtime.model_api_key", initial_runtime_config["model_api_key"], now_text()),
                ("runtime.model_api_model", initial_runtime_config["model_api_model"], now_text()),
                ("runtime.model_provider_code", initial_runtime_config["model_provider_code"], now_text()),
                ("runtime.require_real_ai", "true" if initial_runtime_config["require_real_ai"] else "false", now_text()),
            ],
        )
    cur.executemany(
        """
        INSERT OR IGNORE INTO app_config (config_key, config_value, updated_at)
        VALUES (?, ?, ?)
        """,
        [
            ("account.free_trial_credits", str(FREE_TRIAL_CREDITS), now_text()),
            ("account.free_trial_days", str(FREE_TRIAL_DAYS), now_text()),
            ("account.register_device_limit", str(REGISTER_DEVICE_LIMIT), now_text()),
            ("account.register_device_whitelist", "", now_text()),
            ("training.flip_limit.inactive", str(DAILY_FLIP_LIMIT_INACTIVE), now_text()),
            ("training.flip_limit.gift", str(DAILY_FLIP_LIMIT_GIFT), now_text()),
            ("training.flip_limit.paid", str(DAILY_FLIP_LIMIT_PAID), now_text()),
        ],
        )

    runtime_config = load_runtime_config()
    if cur.execute("SELECT COUNT(*) FROM ai_models").fetchone()[0] == 0 and runtime_config["model_api_model"]:
        cur.execute(
            """
            INSERT INTO ai_models
            (id, model_name, display_name, provider_code, api_key, status, version_note, created_at, updated_at)
            VALUES (?, ?, ?, 'yunwu', ?, 'active', ?, ?, ?)
            """,
            (
                f"model-{uuid.uuid4().hex[:10]}",
                runtime_config["model_api_model"],
                runtime_config["model_api_model"],
                runtime_config["model_api_key"],
                "从当前运行配置自动迁移",
                now_text(),
                now_text(),
            ),
        )

    runtime_config = load_runtime_config()
    if cur.execute("SELECT COUNT(*) FROM ai_prompts").fetchone()[0] == 0:
        cur.execute(
            """
            INSERT INTO ai_prompts
            (prompt_key, prompt_name, version_no, system_prompt, user_prompt_template, model_name, provider_code, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'published', ?)
            """,
            (
                "card_association_feedback",
                "卡片联想评分",
                5,
                "你是一名严格但鼓励式的表达教练，任务不是一次性给完答案，而是按轮次把学员往前带。你必须返回严格 JSON，不要输出 Markdown，不要输出 JSON 之外的任何内容。评分时请区分“大判断”和“用来支撑它的具体观点”。当用户第一轮讲得很散时，优先帮他收一个点；当用户已经有点了但缺故事时，优先提醒他补一个具体的人和一个具体时刻；只有在材料足够时，才给完整整理版。请少说套话，多用人话，要让用户感觉你真的听到了他刚才在讲什么。所有分数都必须使用100分制：总分 totalScore 为 0-100 的整数；六个维度分数也都必须是 0-100 的整数，绝对不要返回 10 分制、5 分制或小数制。",
                "训练词语：{{selected_words}}\n用户表达：{{user_text}}\n请返回 JSON 字段：totalScore、summary、details、suggestions、rewrite、heardPoints、bestPoint、coachNote、nextTask、shouldContinue、isFinal、rewriteMode。heardPoints 是数组，列出你听到用户实际上讲了哪几个点；bestPoint 只选一个当前最值得保留和继续展开的点；如果材料不足不要硬编故事，rewriteMode 可以写 demo，表示下面只是示范性整理。details 必须是长度为 6 的数组，每一项都包含 label、score、note。六个 label 必须依次是：核心观点清晰度、解释成立度、结构连贯度、观点深度与力度、例子与场景的具体性、表达自然度与可信感。六个 score 全部使用 0-100 的整数。",
                runtime_config["model_api_model"] or "gpt-4o",
                runtime_config["model_provider_code"] or "yunwu",
                now_text(),
            ),
        )
    else:
        current_prompt = cur.execute(
            "SELECT version_no FROM ai_prompts WHERE prompt_key = 'card_association_feedback'"
        ).fetchone()
        # 只迁移旧版默认 Prompt；后台保存过的新版本不能在服务重启时被覆盖。
        if current_prompt and int(current_prompt["version_no"]) < 5:
            cur.execute(
                """
                UPDATE ai_prompts
                SET
                  version_no = ?,
                  system_prompt = ?,
                  user_prompt_template = ?,
                  model_name = ?,
                  provider_code = ?,
                  updated_at = ?
                WHERE prompt_key = 'card_association_feedback'
                """,
                (
                    5,
                    "你是一名严格但鼓励式的表达教练，任务不是一次性给完答案，而是按轮次把学员往前带。你必须返回严格 JSON，不要输出 Markdown，不要输出 JSON 之外的任何内容。评分时请区分“大判断”和“用来支撑它的具体观点”。当用户第一轮讲得很散时，优先帮他收一个点；当用户已经有点了但缺故事时，优先提醒他补一个具体的人和一个具体时刻；只有在材料足够时，才给完整整理版。请少说套话，多用人话，要让用户感觉你真的听到了他刚才在讲什么。所有分数都必须使用100分制：总分 totalScore 为 0-100 的整数；六个维度分数也都必须是 0-100 的整数，绝对不要返回 10 分制、5 分制或小数制。",
                    "训练词语：{{selected_words}}\n用户表达：{{user_text}}\n请返回 JSON 字段：totalScore、summary、details、suggestions、rewrite、heardPoints、bestPoint、coachNote、nextTask、shouldContinue、isFinal、rewriteMode。heardPoints 是数组，列出你听到用户实际上讲了哪几个点；bestPoint 只选一个当前最值得保留和继续展开的点；如果材料不足不要硬编故事，rewriteMode 可以写 demo，表示下面只是示范性整理。details 必须是长度为 6 的数组，每一项都包含 label、score、note。六个 label 必须依次是：核心观点清晰度、解释成立度、结构连贯度、观点深度与力度、例子与场景的具体性、表达自然度与可信感。六个 score 全部使用 0-100 的整数。",
                    runtime_config["model_api_model"] or "gpt-4o",
                    runtime_config["model_provider_code"] or "yunwu",
                    now_text(),
                ),
            )

    for prompt_row in cur.execute("SELECT * FROM ai_prompts").fetchall():
        cur.execute(
            """
            INSERT OR IGNORE INTO ai_prompt_versions
            (id, prompt_key, prompt_name, version_no, system_prompt, user_prompt_template, model_name, provider_code, status, change_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{prompt_row['prompt_key']}-v{prompt_row['version_no']}",
                prompt_row["prompt_key"],
                prompt_row["prompt_name"],
                prompt_row["version_no"],
                prompt_row["system_prompt"],
                prompt_row["user_prompt_template"],
                prompt_row["model_name"],
                prompt_row["provider_code"],
                prompt_row["status"],
                "系统初始化版本",
                prompt_row["updated_at"],
            ),
        )

    conn.commit()
    conn.close()


def guest_nickname(client_id):
    tail = (client_id or uuid.uuid4().hex)[-4:].upper()
    return f"游客{tail}"


def resolve_user(conn, client_id):
    client_id = (client_id or "legacy-demo-user").strip() or "legacy-demo-user"
    user = conn.execute("SELECT * FROM users WHERE client_id = ?", (client_id,)).fetchone()
    if user:
        return user

    conn.execute(
        """
        INSERT OR IGNORE INTO users
        (nickname, started_rounds_today, current_round_index, client_id, contact, is_registered, registered_at, created_at)
        VALUES (?, 0, 0, ?, '', 0, NULL, ?)
        """,
        (guest_nickname(client_id), client_id, now_text()),
    )
    user = conn.execute("SELECT * FROM users WHERE client_id = ?", (client_id,)).fetchone()
    user_id = user["id"]
    conn.execute(
        "INSERT OR IGNORE INTO membership (user_id, is_member, plan_name) VALUES (?, 0, '普通版')",
        (user_id,),
    )
    conn.commit()
    return user


def fetch_user_state(conn, user_id):
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    membership = conn.execute("SELECT * FROM membership WHERE user_id = ?", (user_id,)).fetchone()
    return user, membership


def remaining_quota(user, membership):
    if membership["is_member"]:
        return float("inf")
    return max(0, 3 - user["started_rounds_today"])


def fetch_active_session(conn, user_id, heal=True):
    row = conn.execute(
        "SELECT * FROM sessions WHERE user_id = ? AND status IN ('active', 'feedback_ready') ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if not heal:
        return row
    return heal_active_session_if_needed(conn, row)


def session_cards(conn, session_id):
    rows = conn.execute(
        "SELECT * FROM session_cards WHERE session_id = ? ORDER BY position_index ASC",
        (session_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def coaching_attempts(conn, session_id):
    rows = conn.execute(
        "SELECT * FROM coaching_attempts WHERE session_id = ? ORDER BY attempt_no ASC, created_at ASC",
        (session_id,),
    ).fetchall()
    attempts = []
    for row in rows:
        feedback = json_loads(row["feedback_json"], {})
        attempts.append(
            {
                "id": row["id"],
                "attemptNo": row["attempt_no"],
                "transcriptText": row["transcript_text"],
                "feedback": feedback,
                "createdAt": row["created_at"],
            }
        )
    return attempts


def pair_title_from_words(words):
    clean_words = [str(word).strip() for word in (words or []) if str(word).strip()]
    if len(clean_words) != 2:
        return ""
    return f"{clean_words[0]} + {clean_words[1]}"


def pair_history_id(session_id, words):
    clean_words = [str(word).strip() for word in (words or []) if str(word).strip()][:2]
    pair_key = "|".join(clean_words) if len(clean_words) == 2 else "unknown"
    digest = hashlib.md5(pair_key.encode("utf-8")).hexdigest()[:10]
    return f"history-{session_id}-{digest}"


def current_pair_words(conn, session_row):
    selected_ids = json_loads(session_row["selected_json"], [])
    if len(selected_ids) != 2:
        return []
    rows = conn.execute(
        f"SELECT word FROM session_cards WHERE session_id = ? AND id IN ({','.join(['?'] * len(selected_ids))}) ORDER BY position_index ASC",
        [session_row["id"], *selected_ids],
    ).fetchall()
    return [row["word"] for row in rows]


def record_training_event(conn, event_name, user_id=None, session_id="", pair=None, metadata=None, event_key=None):
    session_id = session_id or ""
    pair = pair or []
    metadata = metadata or {}
    stable_pair = "|".join(str(item) for item in pair) if pair else "none"
    stable_key = event_key or f"{event_name}:{session_id or user_id or 'anon'}:{stable_pair}"
    conn.execute(
        """
        INSERT OR IGNORE INTO training_events
        (id, event_name, event_key, user_id, session_id, pair_json, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"evt-{uuid.uuid4().hex[:10]}",
            event_name,
            stable_key,
            user_id,
            session_id,
            json_dumps(pair),
            json_dumps(metadata),
            now_text(),
        ),
    )


def today_range_text():
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def daily_flipped_word_count(conn, user_id):
    start, end = today_range_text()
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM training_events
        WHERE user_id = ?
          AND event_name = 'card_flipped'
          AND created_at >= ?
          AND created_at < ?
        """,
        (user_id, start, end),
    ).fetchone()
    return int(row["count"] or 0)


def daily_flip_limit_for_user(conn, user_id, auth_token=""):
    limits = training_flip_limit_config(conn)
    access_status, membership_row = training_access_status(conn, auth_token, user_id)
    if access_status != "active" or not membership_row:
        return limits["inactive"], "inactive"
    if membership_row["plan_id"] == "gift_trial":
        return limits["gift"], "gift"
    return limits["paid"], "paid"


def track_training_event(conn, user_id, body):
    event_name = (body.get("eventName") or "").strip()
    allowed_events = {
        "speaking_page_entered",
        "word_batch_viewed",
        "word_batch_refreshed",
        "card_flipped",
        "two_words_selected",
        "coach_feedback_submit_clicked",
        "coach_feedback_blocked_payment",
        "plan_page_viewed",
    }
    if event_name not in allowed_events:
        raise ValueError("暂不支持这个埋点事件")
    session_row = fetch_active_session(conn, user_id)
    if not session_row and event_name not in {"plan_page_viewed"}:
        raise ValueError("当前没有进行中的训练")
    pair = [str(item).strip() for item in (body.get("selectedWords") or []) if str(item).strip()]
    if len(pair) != 2 and session_row:
        pair = current_pair_words(conn, session_row)
    record_training_event(
        conn,
        event_name,
        user_id=user_id,
        session_id=session_row["id"] if session_row else "",
        pair=pair,
        metadata={"source": "h5"},
        event_key=f"{event_name}:{session_row['id'] if session_row else user_id}",
    )
    conn.commit()
    return {"tracked": True}


def reset_pair_progress(conn, session_id, selected_json=None):
    conn.execute(
        """
        UPDATE sessions
        SET attempt_count = 0,
            draft_text = '',
            feedback_json = NULL,
            status = 'active',
            selected_json = COALESCE(?, selected_json),
            updated_at = ?
        WHERE id = ?
        """,
        (json_dumps(selected_json) if selected_json is not None else None, now_text(), session_id),
    )
    conn.execute("DELETE FROM coaching_attempts WHERE session_id = ?", (session_id,))


def recover_session_pair_from_feedback(conn, session_row):
    if not session_row:
        return session_row
    if len(json_loads(session_row["selected_json"], [])) == 2:
        return session_row

    feedback = json_loads(session_row["feedback_json"], {}) if session_row["feedback_json"] else {}
    selected_words = feedback.get("selectedWords") or []
    if len(selected_words) != 2:
        latest_attempt = conn.execute(
            "SELECT feedback_json FROM coaching_attempts WHERE session_id = ? ORDER BY attempt_no DESC, created_at DESC LIMIT 1",
            (session_row["id"],),
        ).fetchone()
        if latest_attempt:
            latest_feedback = json_loads(latest_attempt["feedback_json"], {})
            selected_words = latest_feedback.get("selectedWords") or []

    selected_words = [str(word).strip() for word in selected_words if str(word).strip()]
    if len(selected_words) != 2:
        return session_row

    cards = session_cards(conn, session_row["id"])
    recovered_ids = [card["id"] for card in cards if card["word"] in selected_words]
    if len(recovered_ids) != 2:
        return session_row

    conn.execute(
        "UPDATE sessions SET selected_json = ?, updated_at = ? WHERE id = ?",
        (json_dumps(recovered_ids), now_text(), session_row["id"]),
    )
    conn.commit()
    return conn.execute("SELECT * FROM sessions WHERE id = ?", (session_row["id"],)).fetchone()


def session_pair_context_dirty(conn, session_row):
    attempts = coaching_attempts(conn, session_row["id"])
    feedback = json_loads(session_row["feedback_json"], {}) if session_row["feedback_json"] else {}
    selected_words = current_pair_words(conn, session_row)
    selected_title = pair_title_from_words(selected_words)

    if (session_row["attempt_count"] or 0) > 3:
        return True
    if attempts and (session_row["attempt_count"] or 0) != len(attempts):
        return True
    if not selected_title:
        if attempts:
            return True
        return False

    seen_titles = set()
    for attempt in attempts:
        words = attempt.get("feedback", {}).get("selectedWords") or []
        title = attempt.get("feedback", {}).get("pairTitle") or pair_title_from_words(words)
        if title:
            seen_titles.add(title)
    if feedback:
        feedback_words = feedback.get("selectedWords") or []
        feedback_title = feedback.get("pairTitle") or pair_title_from_words(feedback_words)
        if feedback_title:
            seen_titles.add(feedback_title)

    if len(seen_titles) > 1:
        return True
    if seen_titles and selected_title not in seen_titles:
        return True
    return False


def heal_active_session_if_needed(conn, session_row):
    if not session_row:
        return None
    session_row = recover_session_pair_from_feedback(conn, session_row)
    if not session_pair_context_dirty(conn, session_row):
        return session_row
    reset_pair_progress(conn, session_row["id"], [])
    conn.execute(
        "UPDATE session_cards SET state = 'hidden' WHERE session_id = ? AND state = 'flipped'",
        (session_row["id"],),
    )
    conn.commit()
    return conn.execute("SELECT * FROM sessions WHERE id = ?", (session_row["id"],)).fetchone()


def cleanup_dirty_sessions():
    conn = db()
    rows = conn.execute(
        "SELECT * FROM sessions WHERE status IN ('active', 'feedback_ready') ORDER BY created_at DESC"
    ).fetchall()
    changed = False
    for row in rows:
        if session_pair_context_dirty(conn, row):
            reset_pair_progress(conn, row["id"], [])
            conn.execute(
                "UPDATE session_cards SET state = 'hidden' WHERE session_id = ? AND state = 'flipped'",
                (row["id"],),
            )
            changed = True
    if changed:
        conn.commit()
    conn.close()


def truncate_text(value, limit=900):
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def compact_rewrite_summary(rewrite):
    text = (rewrite or "").strip()
    if not text:
        return ""
    paragraphs = [item.strip() for item in text.splitlines() if item.strip()]
    return truncate_text(" / ".join(paragraphs[:2]), 220)


def compact_feedback_for_context(feedback):
    feedback = feedback or {}
    details = normalize_feedback_details(feedback.get("visibleDetails") or feedback.get("details") or [])
    return {
        "totalScore": feedback.get("totalScore"),
        "scores": {item.get("label") or item.get("name"): item.get("score") for item in details},
        "summary": truncate_text(feedback.get("summary", ""), 260),
        "heardPoints": list(feedback.get("heardPoints") or [])[:4],
        "strengths": list(feedback.get("strengths") or [])[:3],
        "improvement": truncate_text(feedback.get("improvement", ""), 360),
        "rewriteMode": feedback.get("rewriteMode", "none"),
        "rewriteSummary": compact_rewrite_summary(feedback.get("rewrite", "")),
    }


def previous_attempts_prompt_context(previous_attempts, max_items=2):
    context = []
    for item in previous_attempts[-max_items:]:
        context.append(
            {
                "attemptNo": item.get("attemptNo"),
                "userText": (item.get("transcriptText", "") or "").strip(),
                "feedback": compact_feedback_for_context(item.get("feedback", {})),
            }
        )
    return context


def sanitize_freeform_previous_context(value):
    text = (value or "").strip()
    if not text:
        return ""
    # Admin prompt tests often paste raw JSON containing the previous rewrite.
    # Keep enough context for comparison, but prevent the model from copying it.
    text = re.sub(r'("rewrite"\s*:\s*")((?:\\.|[^"\\])*)(")', r'\1[上一轮 rewrite 已省略，避免复制]\3', text)
    text = re.sub(r"(rewrite\s*[:：]\s*)([\s\S]{0,1200})", r"\1[上一轮 rewrite 已省略，避免复制]", text, flags=re.IGNORECASE)
    return truncate_text(text, 2400)


def expected_words_for_deck(deck_id):
    if deck_id == "beginner-mixed":
        return []
    for deck in WORD_DECKS:
        if deck["id"] == deck_id:
            return deck["cards"]
    return []


def build_beginner_mixed_words(conn, user, round_no=None, nonce=None):
    client_id = user["client_id"] if "client_id" in user.keys() and user["client_id"] else ""
    seed = f"{user['id']}-{client_id}-{round_no or user['started_rounds_today']}-{nonce or uuid.uuid4().hex}"
    rng = random.Random(seed)
    selected = []
    removed_words = deleted_word_values(conn)

    def add_words(pool_name, count):
        candidates = [
            word
            for word in BEGINNER_CARD_POOLS[pool_name]
            if (f"beginner-{pool_name}", word) not in removed_words
        ]
        rng.shuffle(candidates)
        for word in candidates:
            if len([item for item in selected if item["pool"] == pool_name]) >= count:
                break
            if any(word == item["word"] for item in selected):
                continue
            if any(frozenset((word, item["word"])) in BEGINNER_FORBIDDEN_CLOSE_PAIRS for item in selected):
                continue
            selected.append({"word": word, "pool": pool_name})

    # 每轮都保证：有抽象主词、有冲突词、有生活场景、有具象隐喻物、有解释机制。
    # 用户仍然随机翻牌，但 16 张牌整体不会陷入全正向、全负向或全抽象。
    add_words("anchor", 4)
    add_words("tension", 3)
    add_words("scene", 3)
    add_words("metaphor", 4)
    add_words("mechanism", 2)

    fallback = [
        {"word": word, "pool": pool_name}
        for pool_name, words in BEGINNER_CARD_POOLS.items()
        for word in words
        if (f"beginner-{pool_name}", word) not in removed_words
    ]
    rng.shuffle(fallback)
    for item in fallback:
        if len(selected) >= 16:
            break
        if item["word"] not in [existing["word"] for existing in selected]:
            selected.append(item)

    rng.shuffle(selected)
    return selected[:16]


def deleted_word_values(conn):
    return {
        (row["deck_id"], row["word"])
        for row in conn.execute("SELECT deck_id, word FROM deleted_words").fetchall()
    }


def active_beginner_pool_words(conn, pool_name):
    removed = deleted_word_values(conn)
    return [word for word in BEGINNER_CARD_POOLS[pool_name] if (f"beginner-{pool_name}", word) not in removed]


def session_is_stale(conn, session_row):
    cards = session_cards(conn, session_row["id"])
    expected_words = expected_words_for_deck(session_row["source_deck_id"])
    actual_words = [card["word"] for card in cards]
    if not cards or not expected_words:
        return False
    return actual_words != expected_words


def serialize_session(conn, session_row, user_id, auth_token="", recover_pair=True):
    if not session_row:
        return None
    if recover_pair:
        session_row = heal_active_session_if_needed(conn, session_row)
    user, membership = fetch_user_state(conn, user_id)
    cards = session_cards(conn, session_row["id"])
    selected_ids = set(json_loads(session_row["selected_json"], []))
    selected_cards = [card for card in cards if card["id"] in selected_ids]
    used_count = len([card for card in cards if card["state"] == "used"])
    flipped_count = len([card for card in cards if card["state"] != "hidden"])

    for card in cards:
        card["isSelected"] = card["id"] in selected_ids

    access_status, payment_membership = training_access_status(conn, auth_token, user_id)
    remaining_credits = payment_membership["remaining_groups"] if payment_membership else 0

    return {
        "sessionId": session_row["id"],
        "roundNo": session_row["round_no"],
        "attemptCount": session_row["attempt_count"] or 0,
        "usedCount": used_count,
        "flippedCount": flipped_count,
        "totalCount": len(cards),
        "selectedCount": len(selected_cards),
        "isComplete": used_count == len(cards),
        "cards": cards,
        "selectedCards": selected_cards,
        "remainingQuota": remaining_credits,
        "remainingCredits": remaining_credits,
        "accountStatus": access_status,
        "draftText": session_row["draft_text"] or "",
        "feedback": json_loads(session_row["feedback_json"], None),
        "attempts": coaching_attempts(conn, session_row["id"]),
    }


def create_round(conn, user_id, auth_token=""):
    access_status, payment_membership = training_access_status(conn, auth_token, user_id)
    if access_status == "unauthenticated":
        return {
            "blocked": True,
            "reason": access_status,
            "remainingCredits": payment_membership["remaining_groups"] if payment_membership else 0,
        }

    user, membership = fetch_user_state(conn, user_id)
    active = fetch_active_session(conn, user_id)
    if active:
        if session_is_stale(conn, active):
            conn.execute(
                "UPDATE sessions SET status = 'expired', updated_at = ? WHERE id = ?",
                (now_text(), active["id"]),
            )
            conn.commit()
            active = None
        else:
            state = serialize_session(conn, active, user_id, auth_token)
            if not state["isComplete"]:
                return {"blocked": False, "state": state}

    round_no = user["started_rounds_today"] + 1
    session_id = f"session-{uuid.uuid4().hex[:10]}"
    deck = {
        "id": "beginner-mixed",
        "cards": build_beginner_mixed_words(conn, user, round_no=round_no, nonce=session_id),
    }
    timestamp = now_text()
    conn.execute(
        """
        INSERT INTO sessions (id, user_id, round_no, source_deck_id, status, selected_json, draft_text, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'active', '[]', '', ?, ?)
        """,
        (session_id, user_id, round_no, deck["id"], timestamp, timestamp),
    )

    for index, card_item in enumerate(deck["cards"]):
        word = card_item["word"] if isinstance(card_item, dict) else card_item
        kind = card_item.get("pool", "concept") if isinstance(card_item, dict) else "concept"
        conn.execute(
            """
            INSERT INTO session_cards (id, session_id, word, kind, position_index, state)
            VALUES (?, ?, ?, ?, ?, 'hidden')
            """,
            (f"{session_id}-card-{index + 1}", session_id, word, kind, index),
        )

    conn.execute(
        "UPDATE users SET started_rounds_today = started_rounds_today + 1, current_round_index = current_round_index + 1 WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    return {"blocked": False, "state": serialize_session(conn, fetch_active_session(conn, user_id), user_id, auth_token)}


def refresh_round(conn, user_id, auth_token=""):
    access_status, payment_membership = training_access_status(conn, auth_token, user_id)
    if access_status == "unauthenticated":
        return {
            "blocked": True,
            "reason": access_status,
            "remainingCredits": payment_membership["remaining_groups"] if payment_membership else 0,
        }
    daily_limit, limit_tier = daily_flip_limit_for_user(conn, user_id, auth_token)
    if daily_flipped_word_count(conn, user_id) >= daily_limit:
        return {"error": f"daily_flip_limit_{limit_tier}"}
    active = fetch_active_session(conn, user_id)
    if active:
        active = heal_active_session_if_needed(conn, active)
        conn.execute(
            "UPDATE sessions SET status = 'refreshed', updated_at = ? WHERE id = ?",
            (now_text(), active["id"]),
        )
        conn.commit()
    return create_round(conn, user_id, auth_token)


def toggle_card(conn, user_id, card_id, auth_token=""):
    active = fetch_active_session(conn, user_id)
    if not active:
        return {"error": "round_missing"}

    active = heal_active_session_if_needed(conn, active)
    selected_ids = json_loads(active["selected_json"], [])
    card = conn.execute(
        "SELECT * FROM session_cards WHERE id = ? AND session_id = ?",
        (card_id, active["id"]),
    ).fetchone()
    if not card:
        return {"error": "card_locked"}

    # 如果这张卡已经在当前选择里，即使状态被脏数据标成 used，也允许先取消选择，
    # 不要把用户的“再点一下取消”误判成卡片不可用。
    if card_id in selected_ids:
        selected_ids.remove(card_id)
        if active["feedback_json"] or (active["attempt_count"] or 0) > 0:
            reset_pair_progress(conn, active["id"], selected_ids)
        else:
            conn.execute(
                "UPDATE sessions SET selected_json = ?, updated_at = ? WHERE id = ?",
                (json_dumps(selected_ids), now_text(), active["id"]),
            )
        conn.commit()
        return {
            "ok": True,
            "state": serialize_session(
                conn,
                fetch_active_session(conn, user_id, heal=False),
                user_id,
                auth_token,
                recover_pair=False,
            ),
        }

    if card["state"] == "used":
        return {"error": "card_locked"}

    previous_pair_words = []
    if active["feedback_json"] or (active["attempt_count"] or 0) > 0:
        feedback = json_loads(active["feedback_json"], {}) if active["feedback_json"] else {}
        previous_pair_words = list(feedback.get("selectedWords") or current_pair_words(conn, active))

    if card["state"] == "hidden":
        daily_limit, limit_tier = daily_flip_limit_for_user(conn, user_id, auth_token)
        if daily_flipped_word_count(conn, user_id) >= daily_limit:
            return {"error": f"daily_flip_limit_{limit_tier}"}
        conn.execute(
            "UPDATE session_cards SET state = 'flipped' WHERE id = ?",
            (card_id,),
        )
        today_key = datetime.now().strftime("%Y-%m-%d")
        record_training_event(
            conn,
            "card_flipped",
            user_id=user_id,
            session_id=active["id"],
            metadata={"cardId": card_id, "word": card["word"]},
            event_key=f"card_flipped:{user_id}:{today_key}:{card_id}",
        )

    if len(selected_ids) >= 2:
        return {"error": "selection_full"}
    selected_ids.append(card_id)

    new_words = []
    if len(selected_ids) == 2:
        rows = conn.execute(
            f"SELECT word FROM session_cards WHERE session_id = ? AND id IN ({','.join(['?'] * len(selected_ids))}) ORDER BY position_index ASC",
            [active["id"], *selected_ids],
        ).fetchall()
        new_words = [row["word"] for row in rows]

    if previous_pair_words and new_words and previous_pair_words != new_words:
        reset_pair_progress(conn, active["id"], selected_ids)

    conn.execute(
        "UPDATE sessions SET selected_json = ?, updated_at = ? WHERE id = ?",
        (json_dumps(selected_ids), now_text(), active["id"]),
    )
    conn.commit()
    return {"ok": True, "state": serialize_session(conn, fetch_active_session(conn, user_id), user_id, auth_token)}


def save_draft(conn, user_id, draft_text, auth_token=""):
    active = fetch_active_session(conn, user_id)
    if not active:
        return None
    conn.execute(
        "UPDATE sessions SET draft_text = ?, updated_at = ? WHERE id = ?",
        (draft_text, now_text(), active["id"]),
    )
    conn.commit()
    return serialize_session(conn, fetch_active_session(conn, user_id), user_id, auth_token)


def build_thinking_paths(first, second):
    return [
        f"先别急着讲很多点，只留一句你最想证明的话：为什么“{first}”会是“{second}”？",
        f"再给这句话找一个具体人和一个具体时刻。不是“很多人都会”，而是谁、几岁、在什么场景里，被哪句话刺到了。",
        f"最后用“因为……所以……”把桥搭出来：这个人为什么会这样想，这个时刻为什么刚好能证明“{first}是一种{second}”。",
    ]


def story_signal_count(text):
    markers = [
        "我", "她", "他", "朋友", "同事", "主管", "妈妈", "爸爸", "亲戚", "客户",
        "那天", "有一次", "那次", "午饭", "开会", "下班", "回家", "30岁", "离异",
        "孩子", "岗位", "公司", "面试", "工厂", "学校",
    ]
    return sum(1 for item in markers if item in text)


def scattering_signal_count(text):
    markers = ["第一", "第二", "第三", "另外", "还有", "一方面", "另一方面", "同时", "比如", "而且"]
    return sum(text.count(item) for item in markers)


def split_sentences(text):
    raw = (text or "").replace("\r", "\n")
    chunks = []
    current = []
    for char in raw:
        current.append(char)
        if char in "。！？\n":
            sentence = "".join(current).strip()
            if sentence:
                chunks.append(sentence)
            current = []
    tail = "".join(current).strip()
    if tail:
        chunks.append(tail)
    return [item.strip(" \n\t。") for item in chunks if item.strip(" \n\t。")]


def find_story_sentences(text):
    markers = [
        "我", "她", "他", "朋友", "同事", "主管", "亲戚", "客户", "那天", "有一次", "当时",
        "中午", "开会", "下班", "回家", "30岁", "离异", "孩子", "岗位", "公司", "工厂",
    ]
    return [
        sentence
        for sentence in split_sentences(text)
        if any(marker in sentence for marker in markers) and len(sentence) >= 10
    ]


def pick_scene_sentence(sentences):
    if not sentences:
        return ""
    priority_markers = ["问", "说", "那天", "当时", "中午", "吃饭", "同事", "亲戚", "客户", "开会", "回家"]
    for sentence in sentences:
        if any(marker in sentence for marker in priority_markers):
            return sentence
    return sentences[0]


def story_specificity_level(text):
    transcript = (text or "").strip()
    story_sentences = find_story_sentences(transcript)
    level = 0
    if story_sentences:
        level += 1
    if any(marker in transcript for marker in ["问我", "问她", "问他", "我说", "她说", "他说", "那天", "当时", "中午", "开会", "回家"]):
        level += 1
    if any(marker in transcript for marker in ["30岁", "离异", "主管", "同事", "亲戚", "客户", "自媒体", "工厂", "公司", "岗位"]):
        level += 1
    return min(level, 3)


def concise_point(sentence, limit=46):
    cleaned = " ".join((sentence or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip("，,；; ") + "…"


def fallback_heard_points(transcript_text):
    heard = []
    if "独立女性" in transcript_text or "标签" in transcript_text:
        heard.append("你先在讲“独立女性”这个标签为什么会让很多人向往。")
    if "生孩子" in transcript_text or "社会" in transcript_text or "期待" in transcript_text or "评价" in transcript_text:
        heard.append("你主要在讲：一个女性只要不按期待活，就会不断被追问、被评价、被要求解释。")
    if "30岁" in transcript_text or "三十岁" in transcript_text:
        if "自媒体" in transcript_text:
            heard.append("你已经把人放出来了：一个三十岁、做自媒体、正处在事业上升期的女性。")
        else:
            heard.append("你已经给了一个更具体的人：一个三十岁左右、正处在人生选择节点上的女性。")
    if "同事" in transcript_text and "问" in transcript_text:
        heard.append("你还放进了一个具体时刻：吃饭或聊天时，同事追问你为什么不要孩子、为什么不按默认路线活。")
    if "事业" in transcript_text or "上升" in transcript_text:
        heard.append("你其实也在讲另一层代价：不是你不想要那些东西，而是你知道现在的事业窗口期对你更重要。")
    if "岗位" in transcript_text or "竞争" in transcript_text or "男人" in transcript_text or "男性" in transcript_text:
        heard.append("你还带到了另一条线：女性想争取同样机会时，往往要付出更多现实成本。")
    if not heard:
        for sentence in split_sentences(transcript_text)[:3]:
            if len(sentence) >= 8:
                heard.append(f"你在讲：{concise_point(sentence)}")
            if len(heard) >= 3:
                break
    if not heard:
        heard.append("你已经开始尝试解释这句判断为什么成立。")
    return heard[:4]


def merge_heard_points(primary, fallback):
    merged = []
    for item in list(primary or []) + list(fallback or []):
        item = (item or "").strip()
        if item and item not in merged:
            merged.append(item)
    return merged[:4]


def build_strengths(transcript_text, has_story, scattered, best_point=""):
    strengths = []
    story_sentences = find_story_sentences(transcript_text)
    scene = concise_point(pick_scene_sentence(story_sentences), 24) if story_sentences else ""
    if best_point:
        strengths.append(f"你这轮已经抓到一个能成立的点了，比如“{concise_point(best_point, 24)}”。")
    if "因为" in transcript_text or "所以" in transcript_text:
        strengths.append("你不是只在丢结论，已经开始解释“为什么这句话成立”。")
    if has_story and scene:
        strengths.append(f"你这轮已经给了具体人物或场景，比如“{scene}”，这会比纯概念更有说服力。")
    if ("我" in transcript_text or "朋友" in transcript_text or "同事" in transcript_text) and not has_story:
        strengths.append("你已经在往自己的处境靠了，这会让表达更像你自己，而不是一段标准答案。")
    if not scattered:
        strengths.append("这轮主线相对更收，听的人更容易知道你到底想证明哪一句话。")
    return strengths[:3]


def normalize_feedback_details(raw_details):
    labels = [
        "主张清楚",
        "解释成立",
        "结构聚焦",
        "观点深度",
        "案例具体",
        "表达自然",
    ]
    alias_map = {
        "核心观点清晰度": "主张清楚",
        "主张清楚": "主张清楚",
        "clarity": "主张清楚",
        "解释成立度": "解释成立",
        "解释成立": "解释成立",
        "logicalFlow": "解释成立",
        "结构连贯度": "结构聚焦",
        "结构聚焦": "结构聚焦",
        "观点深度与力度": "观点深度",
        "观点深度": "观点深度",
        "emotionalImpact": "观点深度",
        "例子与场景的具体性": "案例具体",
        "案例具体": "案例具体",
        "specificity": "案例具体",
        "表达自然度与可信感": "表达自然",
        "表达自然": "表达自然",
        "naturalness": "表达自然",
    }
    if isinstance(raw_details, dict):
        mapped = [
            {"label": "主张清楚", "score": raw_details.get("clarity", 5), "note": "你这轮到底有没有把最想证明的那句话说清楚。"},
            {"label": "解释成立", "score": raw_details.get("logicalFlow", 5), "note": "你有没有把“为什么成立”这一步讲通。"},
            {"label": "结构聚焦", "score": raw_details.get("logicalFlow", 5), "note": "你的表达有没有一直围着同一条主线往前走。"},
            {"label": "观点深度", "score": raw_details.get("emotionalImpact", 5), "note": "这个点有没有往更深一层扎进去。"},
            {"label": "案例具体", "score": raw_details.get("specificity", 5), "note": "你有没有给出具体的人、具体时刻和具体画面。"},
            {"label": "表达自然", "score": raw_details.get("emotionalImpact", 5), "note": "这段话像不像你真的会说出来的话。"},
        ]
        raw_details = mapped
    elif not isinstance(raw_details, list):
        raw_details = []

    normalized = []
    list_scores = []
    if isinstance(raw_details, list):
        for item in raw_details:
            if isinstance(item, dict) and item.get("score") is not None:
                try:
                    list_scores.append(float(item.get("score")))
                except (TypeError, ValueError):
                    pass
    for index, label in enumerate(labels):
        source = raw_details[index] if index < len(raw_details) else {}
        if isinstance(source, dict):
            score_value = source.get("score")
            raw_score = 55 if score_value is None else float(score_value)
            raw_label = source.get("label") or source.get("name") or label
            score = naturalize_score(raw_score, index)
            normalized.append(
                {
                    "label": alias_map.get(raw_label, raw_label) if raw_label else label,
                    "score": score,
                    "note": source.get("note") or source.get("reason") or "这一维还可以继续展开。",
                }
            )
        else:
            normalized.append(
                {
                    "label": label,
                    "score": 55,
                    "note": str(source) if source else "这一维还可以继续展开。",
                }
            )
    return normalized


def naturalize_score(raw_score, index=0):
    return max(0, min(100, int(round(float(raw_score)))))


def normalize_text_list(items, limit=4):
    normalized = []
    for item in list(items or []):
        text = " ".join(str(item or "").split()).strip()
        if text and text not in normalized:
            normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized


def cleanup_feedback_text(text):
    if not text:
        return ""
    cleaned = str(text).replace("\r", "\n").strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def shape_feedback_payload(selected_cards, transcript_text, attempt_no, previous_attempts, base_feedback):
    transcript = (transcript_text or "").strip()
    heard_points = normalize_text_list(base_feedback.get("heardPoints") or [], 4)
    strengths = normalize_text_list(base_feedback.get("strengths") or [], 3)
    details = normalize_feedback_details(base_feedback.get("details", []))
    try:
        total_score = naturalize_score(base_feedback.get("totalScore"), 6)
    except (TypeError, ValueError):
        total_score = 0

    summary = cleanup_feedback_text(
        base_feedback.get("summary")
        or base_feedback.get("coachNote")
        or ""
    )
    improvement = cleanup_feedback_text(
        base_feedback.get("improvement")
        or base_feedback.get("nextTask")
        or base_feedback.get("mainIssue")
        or ""
    )

    should_continue = bool(base_feedback.get("shouldContinue", True))
    is_final = bool(base_feedback.get("isFinal", False))
    if attempt_no >= 3:
        is_final = True
        should_continue = False

    rewrite = cleanup_feedback_text(base_feedback.get("rewrite", ""))
    rewrite_mode = (base_feedback.get("rewriteMode") or "").strip()
    if rewrite and not rewrite_mode:
        rewrite_mode = "coach-polish"
    elif not rewrite:
        rewrite_mode = "none"

    shaped = {
        "pairTitle": f"{selected_cards[0]['word']} + {selected_cards[1]['word']}",
        "attemptNo": attempt_no,
        "maxAttempts": 3,
        "totalScore": total_score,
        "summary": summary,
        "details": details,
        "visibleDetails": details,
        "heardPoints": heard_points,
        "strengths": strengths,
        "improvement": improvement,
        "shouldContinue": should_continue,
        "isFinal": is_final,
        "rewriteMode": rewrite_mode,
        "rewrite": rewrite,
        "selectedWords": [selected_cards[0]["word"], selected_cards[1]["word"]],
    }
    if "freeModeNote" in base_feedback:
        shaped["freeModeNote"] = base_feedback["freeModeNote"]
    if "aiSource" in base_feedback:
        shaped["aiSource"] = base_feedback["aiSource"]
    if "coachSystemNote" in base_feedback:
        shaped["coachSystemNote"] = base_feedback["coachSystemNote"]
    return shaped


def call_model_api(selected_cards, submission_text, prompt_row, attempt_no=1, previous_attempts_context=None, model_override=None):
    runtime_config = load_runtime_config()
    api_url = runtime_config["model_api_url"]
    model_override = model_override or {}
    api_key = model_override.get("api_key") or runtime_config["model_api_key"]
    model_name = model_override.get("model_name") or runtime_config["model_api_model"] or prompt_row["model_name"]
    provider_code = model_override.get("provider_code") or runtime_config["model_provider_code"] or "yunwu"
    timeout_seconds = 45 if not os.getenv("RAILWAY_ENVIRONMENT") else 30

    if not api_url or not api_key:
        return None

    selected_words = " / ".join(card["word"] for card in selected_cards)
    previous_attempts_context = previous_attempts_context if previous_attempts_context is not None else []
    if isinstance(previous_attempts_context, str):
        previous_attempts_text = previous_attempts_context
    else:
        previous_attempts_text = json_dumps(previous_attempts_context)
    user_prompt = (
        prompt_row["user_prompt_template"]
        .replace("{{selected_words}}", selected_words)
        .replace("{{user_text}}", submission_text)
        .replace("{{attempt_no}}", str(attempt_no))
        .replace("{{attemptNo}}", str(attempt_no))
        .replace("{{previous_attempts}}", previous_attempts_text or "[]")
        .replace("{{previousAttempts}}", previous_attempts_text or "[]")
        .replace("{{previousContext}}", previous_attempts_text or "[]")
    )

    payload = {
        "model": model_name,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": prompt_row["system_prompt"]},
            {"role": "user", "content": user_prompt},
        ],
    }

    if "gpt" in model_name.lower() or "o" in model_name.lower():
        payload["response_format"] = {"type": "json_object"}

    request = Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
            content = raw["choices"][0]["message"]["content"]
            content = content.strip()
            if content.startswith("```"):
                lines = [line for line in content.splitlines() if not line.strip().startswith("```")]
                content = "\n".join(lines).strip()
            parsed = json.loads(content)
            parsed.setdefault("details", [])
            parsed.setdefault("suggestions", [])
            parsed.setdefault("summary", "AI 已返回评分结果。")
            parsed.setdefault("rewrite", "")
            if "totalScore" not in parsed and "total_score" in parsed:
                parsed["totalScore"] = parsed["total_score"]
            if "details" in parsed:
                for item in parsed["details"]:
                    if "label" not in item and "name" in item:
                        item["label"] = item["name"]
            return {
                "provider_code": provider_code,
                "model_name": model_name,
                "raw_response": raw,
                "feedback": parsed,
            }
    except Exception:
        traceback.print_exc()
        return None


def score_submission(conn, session_row, submission_text, attempt_no, previous_attempts):
    prompt = conn.execute("SELECT * FROM ai_prompts WHERE prompt_key = 'card_association_feedback'").fetchone()
    selected_ids = set(json_loads(session_row["selected_json"], []))
    cards = session_cards(conn, session_row["id"])
    selected_cards = [card for card in cards if card["id"] in selected_ids]

    previous_context = previous_attempts_prompt_context(previous_attempts)
    model_result = call_model_api(
        selected_cards,
        submission_text,
        prompt,
        attempt_no=attempt_no,
        previous_attempts_context=previous_context,
    )
    if model_result and model_result.get("feedback"):
        feedback = model_result["feedback"]
        if not isinstance(feedback, dict) or "totalScore" not in feedback:
            model_result = None
        elif not isinstance(feedback.get("details"), list) or len(feedback.get("details")) != 6:
            model_result = None
        elif any(not isinstance(item, dict) or item.get("score") is None for item in feedback.get("details")):
            model_result = None

    if model_result:
        feedback = model_result["feedback"]
        feedback["details"] = normalize_feedback_details(feedback.get("details", []))
        feedback.setdefault("rewrite", "")
        feedback = shape_feedback_payload(selected_cards, submission_text, attempt_no, previous_attempts, feedback)
        provider_code = model_result["provider_code"]
        feedback["aiSource"] = provider_code
        model_name = model_result["model_name"]
        response_payload = model_result["raw_response"]
        status = "success"
    else:
        raise RuntimeError("真实 AI 调用失败或返回结构不完整：未使用本地评分兜底。请检查模型接口、API Key、prompt 输出格式或模型可用性。")

    job_id = f"JOB{int(time.time() * 1000)}"
    request_payload = {
        "selected_words": [card["word"] for card in selected_cards],
        "user_text": submission_text,
        "attempt_no": attempt_no,
        "previous_attempts": previous_attempts_prompt_context(previous_attempts),
        "prompt_key": prompt["prompt_key"],
        "prompt_version": prompt["version_no"],
    }
    conn.execute(
        """
        INSERT INTO ai_jobs
        (id, session_id, prompt_key, version_no, provider_code, model_name, status, selected_words_json, transcript_text, request_json, response_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            session_row["id"],
            prompt["prompt_key"],
            prompt["version_no"],
            provider_code,
            model_name,
            status,
            json_dumps(request_payload["selected_words"]),
            submission_text,
            json_dumps(request_payload),
            json_dumps(response_payload),
            now_text(),
            now_text(),
        ),
    )
    return feedback


def finalize_training_session(conn, user_id, session_row, transcript_text, feedback, auth_token=""):
    selected_ids = json_loads(session_row["selected_json"], [])
    is_final = bool(feedback.get("isFinal"))
    if is_final:
        for card_id in selected_ids:
            conn.execute("UPDATE session_cards SET state = 'used' WHERE id = ?", (card_id,))
            word = conn.execute("SELECT word FROM session_cards WHERE id = ?", (card_id,)).fetchone()["word"]
            conn.execute("UPDATE words SET used_count = used_count + 1 WHERE word = ?", (word,))

    cards = session_cards(conn, session_row["id"])
    pair = [card["word"] for card in cards if card["id"] in selected_ids]
    if len(pair) != 2 and len(feedback.get("selectedWords") or []) == 2:
        pair = [str(item).strip() for item in feedback.get("selectedWords") if str(item).strip()]
    attempts = coaching_attempts(conn, session_row["id"])
    feedback["attemptHistory"] = attempts
    feedback["selectedWords"] = pair
    feedback["latestHistoryId"] = upsert_history_record_for_session(
        conn,
        user_id,
        session_row,
        pair,
        transcript_text,
        feedback,
        attempts,
    )

    next_selected_json = "[]" if is_final else json_dumps(selected_ids)
    conn.execute(
        """
        UPDATE sessions
        SET selected_json = ?, draft_text = ?, feedback_json = ?, status = 'feedback_ready', updated_at = ?
        WHERE id = ?
        """,
        (next_selected_json, transcript_text, json_dumps(feedback), now_text(), session_row["id"]),
    )
    conn.commit()
    active = fetch_active_session(conn, user_id)
    state = serialize_session(conn, active, user_id, auth_token)
    feedback["isRoundComplete"] = state["isComplete"] if state else bool(is_final)
    return feedback


def upsert_history_record_for_session(conn, user_id, session_row, pair, transcript_text, feedback, attempts):
    title_pair = [str(item).strip() for item in (pair if len(pair) == 2 else (feedback.get("selectedWords") or [])) if str(item).strip()][:2]
    record_id = pair_history_id(session_row["id"], title_pair)
    existing = conn.execute(
        "SELECT id, created_at FROM history_records WHERE id = ? AND user_id = ?",
        (record_id, user_id),
    ).fetchone()
    created_at = existing["created_at"] if existing else now_text()
    latest_attempt = attempts[-1] if attempts else {}
    original_text = (latest_attempt.get("transcriptText") or transcript_text or "").strip()
    if not original_text or original_text in {
        (feedback.get("improvement") or "").strip(),
        (feedback.get("summary") or "").strip(),
        (feedback.get("rewrite") or "").strip(),
    }:
        original_text = (transcript_text or "").strip()
    title = f"第{session_row['round_no']}轮｜{title_pair[0]} + {title_pair[1]}" if len(title_pair) == 2 else f"第{session_row['round_no']}轮"
    conn.execute(
        """
        INSERT INTO history_records
        (id, title, session_id, time_label, pair_json, excerpt, transcript_text, score, summary, details_json, suggestions_json, attempts_json, final_feedback_json, created_at, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          title = excluded.title,
          time_label = excluded.time_label,
          pair_json = excluded.pair_json,
          excerpt = excluded.excerpt,
          transcript_text = excluded.transcript_text,
          score = excluded.score,
          summary = excluded.summary,
          details_json = excluded.details_json,
          suggestions_json = excluded.suggestions_json,
          attempts_json = excluded.attempts_json,
          final_feedback_json = excluded.final_feedback_json,
          user_id = excluded.user_id
        """,
        (
            record_id,
            title,
            session_row["id"],
            datetime.now().strftime("%m-%d %H:%M"),
            json_dumps(title_pair),
            original_text,
            original_text,
            int(feedback.get("totalScore") or 0),
            feedback.get("summary") or "",
            json_dumps(feedback.get("details") or feedback.get("visibleDetails") or []),
            json_dumps([]),
            json_dumps(attempts),
            json_dumps(feedback),
            created_at,
            user_id,
        ),
    )
    return record_id


def finish_current_feedback(conn, user_id, auth_token=""):
    session_row = fetch_active_session(conn, user_id)
    if not session_row:
        raise ValueError("当前没有可收口的训练")
    feedback = json_loads(session_row["feedback_json"], {})
    if not feedback:
        raise ValueError("当前还没有教练反馈")
    if feedback.get("isFinal"):
        return feedback

    selected_ids = json_loads(session_row["selected_json"], [])
    cards = session_cards(conn, session_row["id"])
    selected_cards = [card for card in cards if card["id"] in selected_ids]
    if len(selected_cards) != 2 and len(feedback.get("selectedWords") or []) == 2:
        selected_words = feedback.get("selectedWords") or []
        selected_cards = [card for card in cards if card["word"] in selected_words]
        selected_ids = [card["id"] for card in selected_cards]
        if len(selected_ids) == 2:
            conn.execute(
                "UPDATE sessions SET selected_json = ?, updated_at = ? WHERE id = ?",
                (json_dumps(selected_ids), now_text(), session_row["id"]),
            )
            conn.commit()
            session_row = fetch_active_session(conn, user_id)
    if not selected_cards:
        raise ValueError("当前没有可收口的词语组合")

    feedback["isFinal"] = True
    feedback["shouldContinue"] = False
    feedback["summary"] = feedback.get("summary") or "这一组先在这里收口，先看教练整理版，再决定要不要继续下一组词。"
    if not feedback.get("rewrite"):
        feedback["rewrite"] = ""
        feedback["rewriteMode"] = "none"
    return finalize_training_session(conn, user_id, session_row, session_row["draft_text"] or "", feedback, auth_token)


def submit_training(conn, user_id, transcript_text, submitted_words=None, auth_token=""):
    access_status, payment_membership = training_access_status(conn, auth_token, user_id)
    if access_status != "active":
        raise ValueError("当前训练权益不可用，请先开通或续费")

    session_row = fetch_active_session(conn, user_id)
    if not session_row:
        raise ValueError("当前没有进行中的训练")

    selected_ids = json_loads(session_row["selected_json"], [])
    if len(selected_ids) != 2:
        selected_words = [str(item).strip() for item in (submitted_words or []) if str(item).strip()]
        feedback_snapshot = json_loads(session_row["feedback_json"], {}) if session_row["feedback_json"] else {}
        if len(selected_words) != 2:
            selected_words = feedback_snapshot.get("selectedWords") or []
        if len(selected_words) != 2:
            latest_attempt = conn.execute(
                "SELECT feedback_json FROM coaching_attempts WHERE session_id = ? ORDER BY attempt_no DESC, created_at DESC LIMIT 1",
                (session_row["id"],),
            ).fetchone()
            if latest_attempt:
                latest_feedback = json_loads(latest_attempt["feedback_json"], {})
                selected_words = latest_feedback.get("selectedWords") or []
        if len(selected_words) == 2:
            cards = session_cards(conn, session_row["id"])
            recovered_ids = [
                card["id"]
                for card in cards
                if card["word"] in selected_words
            ]
            if len(recovered_ids) == 2:
                selected_ids = recovered_ids
                conn.execute(
                    "UPDATE sessions SET selected_json = ?, updated_at = ? WHERE id = ?",
                    (json_dumps(selected_ids), now_text(), session_row["id"]),
                )
                conn.commit()
                session_row = fetch_active_session(conn, user_id)
        if len(selected_ids) != 2:
            flipped_ids = [
                card["id"]
                for card in session_cards(conn, session_row["id"])
                if card["state"] == "flipped"
            ]
            if len(flipped_ids) == 2:
                selected_ids = flipped_ids
                conn.execute(
                    "UPDATE sessions SET selected_json = ?, updated_at = ? WHERE id = ?",
                    (json_dumps(selected_ids), now_text(), session_row["id"]),
                )
                conn.commit()
                session_row = fetch_active_session(conn, user_id)
        if len(selected_ids) != 2:
            raise ValueError("当前必须先选中两张卡片")
    previous_attempts = coaching_attempts(conn, session_row["id"])
    attempt_no = len(previous_attempts) + 1
    selected_cards_for_event = [
        {"word": word}
        for word in current_pair_words(conn, session_row)
    ]
    event_pair = [item["word"] for item in selected_cards_for_event]
    record_training_event(
        conn,
        "coach_feedback_submitted",
        user_id=user_id,
        session_id=session_row["id"],
        pair=event_pair,
        metadata={"attemptNo": attempt_no, "source": "submit_training"},
        event_key=f"coach_feedback_submitted:{session_row['id']}",
    )
    conn.commit()
    feedback = score_submission(conn, session_row, transcript_text, attempt_no, previous_attempts)
    record_training_event(
        conn,
        "coach_feedback_success",
        user_id=user_id,
        session_id=session_row["id"],
        pair=event_pair or feedback.get("selectedWords") or [],
        metadata={"attemptNo": attempt_no, "source": "submit_training"},
        event_key=f"coach_feedback_success:{session_row['id']}",
    )
    remaining_after_consume = consume_training_credit(conn, user_id)
    feedback["remainingCredits"] = remaining_after_consume

    conn.execute(
        """
        INSERT INTO coaching_attempts (id, session_id, attempt_no, transcript_text, feedback_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            f"attempt-{uuid.uuid4().hex[:10]}",
            session_row["id"],
            attempt_no,
            transcript_text,
            json_dumps(feedback),
            now_text(),
        ),
    )
    conn.execute(
        """
        UPDATE sessions
        SET attempt_count = ?, draft_text = ?, feedback_json = ?, status = 'feedback_ready', updated_at = ?
        WHERE id = ?
        """,
        (attempt_no, transcript_text, json_dumps(feedback), now_text(), session_row["id"]),
    )
    conn.commit()
    feedback["attemptHistory"] = coaching_attempts(conn, session_row["id"])
    selected_pair = current_pair_words(conn, session_row) or feedback.get("selectedWords") or []
    feedback["latestHistoryId"] = upsert_history_record_for_session(
        conn,
        user_id,
        session_row,
        selected_pair,
        transcript_text,
        feedback,
        feedback["attemptHistory"],
    )
    conn.commit()

    if feedback.get("isFinal"):
        return finalize_training_session(conn, user_id, fetch_active_session(conn, user_id), transcript_text, feedback, auth_token)

    return feedback


def continue_after_feedback(conn, user_id, auth_token=""):
    active = fetch_active_session(conn, user_id)
    if not active:
        access_status, payment_membership = training_access_status(conn, auth_token, user_id)
        if access_status in ("inactive", "expired", "quota_exhausted", "unauthenticated"):
            return {"route": "/pages/account/plan", "reason": access_status}
        return {"route": "/pages/home/index"}

    state = serialize_session(conn, active, user_id, auth_token)
    latest_feedback = state["feedback"] if state else None
    if latest_feedback and not latest_feedback.get("isFinal"):
        conn.execute(
            "UPDATE sessions SET status = 'active', updated_at = ? WHERE id = ?",
            (now_text(), active["id"]),
        )
        conn.commit()
        return {"route": "/pages/speaking/index?mode=retry"}

    access_status, payment_membership = training_access_status(conn, auth_token, user_id)
    if access_status in ("inactive", "expired", "quota_exhausted", "unauthenticated"):
        return {"route": "/pages/account/plan", "reason": access_status}

    reset_pair_progress(conn, active["id"], [])
    conn.execute(
        "UPDATE session_cards SET state = 'hidden' WHERE session_id = ? AND state = 'flipped'",
        (active["id"],),
    )

    if state["isComplete"]:
        conn.execute(
            "UPDATE sessions SET status = 'completed', updated_at = ? WHERE id = ?",
            (now_text(), active["id"]),
        )
        conn.commit()
        next_status, next_membership = training_access_status(conn, auth_token, user_id)
        if next_status in ("quota_exhausted", "expired"):
            return {"route": "/pages/account/plan", "reason": next_status, "remainingCredits": next_membership["remaining_groups"] if next_membership else 0}
        return {"route": "/pages/training/index?mode=next"}

    conn.commit()
    return {"route": "/pages/training/index"}


def daily_quote(conn):
    rows = conn.execute(
        """
        SELECT * FROM daily_quotes
        WHERE status = 'published'
        ORDER BY id ASC
        """
    ).fetchall()
    if not rows:
        return {
            "text": "语言的边界，也是思维的边界",
            "author": "维特根斯坦",
            "theme": "表达与思维",
        }
    row = random.choice(rows)
    return {
        "id": row["id"],
        "text": row["quote_text"],
        "author": row["author"],
        "theme": row["theme"],
        "sourceLabel": row["source_label"],
        "sourceUrl": row["source_url"],
    }


def home_summary(conn, user_id, auth_token=""):
    user, membership = fetch_user_state(conn, user_id)
    client_id = user["client_id"] if "client_id" in user.keys() and user["client_id"] else ""
    account = account_context(conn, auth_token, client_id)
    payment_membership = account["membership"]
    account_status = account["status"]
    latest = conn.execute(
        "SELECT * FROM history_records WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    active = fetch_active_session(conn, user_id)
    plan_name = payment_membership["plan_name"] if payment_membership else "未开启训练计划"
    remaining_quota_text = (
        f"{payment_membership['remaining_groups']} 次点评"
        if payment_membership
        else "还没有开启训练计划"
    )
    if account_status == "quota_exhausted":
        remaining_quota_text = "点评次数已用完"
    elif account_status == "expired":
        remaining_quota_text = "训练计划已到期"
    start_button_text = (
        f"开始第 {user['started_rounds_today'] + 1} 轮"
        if account_status == "active"
        else "去我的继续开启训练计划"
    )
    return {
        "nickname": user["nickname"],
        "isRegistered": bool(user["is_registered"]),
        "isMember": account_status == "active",
        "planName": plan_name,
        "memberLabel": plan_name,
        "remainingQuotaText": remaining_quota_text,
        "accountStatus": account_status,
        "remainingCredits": payment_membership["remaining_groups"] if payment_membership else 0,
        "totalCredits": payment_membership["total_groups"] if payment_membership else 0,
        "activeRoundText": "当前轮次进行中" if active else "今日可开新轮次",
        "startButtonText": start_button_text,
        "hasLatestHistory": latest is not None,
        "latestHistoryTitle": latest["title"] if latest else "",
        "latestHistoryScore": str(latest["score"]) if latest else "",
        "latestHistorySummary": latest["summary"] if latest else "",
        "dailyQuote": daily_quote(conn),
    }


def profile_state(conn, user_id, auth_token=""):
    user, membership = fetch_user_state(conn, user_id)
    client_id = user["client_id"] if "client_id" in user.keys() and user["client_id"] else ""
    account = account_context(conn, auth_token, client_id)
    payment_membership = account["membership"]
    status = account["status"]
    trained_groups = conn.execute(
        "SELECT COUNT(*) AS count FROM history_records WHERE user_id = ?",
        (user_id,),
    ).fetchone()["count"]
    trained_attempts = conn.execute(
        """
        SELECT COALESCE(SUM(
          CASE
            WHEN json_array_length(attempts_json) > 0 THEN json_array_length(attempts_json)
            ELSE 1
          END
        ), 0) AS count
        FROM history_records
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()["count"]
    return {
        "nickname": user["nickname"],
        "contact": user["contact"] or "",
        "isRegistered": bool(user["is_registered"]),
        "registeredAt": user["registered_at"] or "",
        "isMember": status == "active",
        "trainedGroups": trained_attempts or trained_groups or 0,
        "trainedAttempts": trained_attempts or 0,
        "planName": payment_membership["plan_name"] if payment_membership else "未开启训练计划",
        "accountStatus": status,
        "phoneMasked": payment_demo_mask_phone(account["paymentUser"]["phone"]) if account["paymentUser"] else "",
        "usedFreeRounds": min(user["started_rounds_today"], 3),
        "remainingQuota": payment_membership["remaining_groups"] if payment_membership else 0,
        "remainingCredits": payment_membership["remaining_groups"] if payment_membership else 0,
        "totalCredits": payment_membership["total_groups"] if payment_membership else 0,
        "expireAt": payment_membership["expire_at"] if payment_membership else "",
    }


def register_user(conn, user_id, nickname, contact):
    nickname = (nickname or "").strip()
    contact = (contact or "").strip()
    if len(nickname) < 2:
        raise ValueError("昵称至少 2 个字")
    if len(contact) < 5:
        raise ValueError("请填写手机号或微信号，方便找回记录")

    conn.execute(
        """
        UPDATE users
        SET nickname = ?, contact = ?, is_registered = 1, registered_at = COALESCE(registered_at, ?)
        WHERE id = ?
        """,
        (nickname, contact, now_text(), user_id),
    )
    conn.commit()
    return profile_state(conn, user_id)


def redeem_membership(conn, user_id, code):
    code = (code or "").strip().upper()
    if not code:
        raise ValueError("请输入兑换码")

    row = conn.execute("SELECT * FROM redeem_codes WHERE code = ?", (code,)).fetchone()
    if not row:
        raise ValueError("兑换码不存在")
    if row["status"] != "active":
        raise ValueError("兑换码已失效或已使用")

    conn.execute("UPDATE membership SET is_member = 1, plan_name = ? WHERE user_id = ?", (row["plan_name"], user_id))
    conn.execute(
        "UPDATE redeem_codes SET status = 'used', used_by = ?, used_at = ? WHERE code = ?",
        (user_id, now_text(), code),
    )
    conn.execute(
        "INSERT INTO membership_orders (id, user_id, amount, status, paid_at) VALUES (?, ?, 0, '兑换码开通', ?)",
        (f"CODE-{int(time.time())}", user_id, now_text()),
    )
    conn.commit()
    return {
        "profile": profile_state(conn, user_id),
        "code": code,
        "planName": row["plan_name"],
    }


def payment_demo_records_preview(account_row):
    if not account_row:
        return []
    if account_row["plan_id"] == "trial7":
        return [
            {
                "title": "孤独 + 电梯",
                "score": 68,
                "status": "已完成 2 轮",
                "summary": "已经能把判断句讲通，但例子还可以更具体。",
            },
            {
                "title": "自由 + 选择",
                "score": 74,
                "status": "已完成 3 轮",
                "summary": "观点更聚焦了，教练整理版已经成形。",
            },
        ]
    return [
        {
            "title": "成长 + 代价",
            "score": 77,
            "status": "已完成 3 轮",
            "summary": "结构更稳，案例也开始支撑观点。",
        },
        {
            "title": "身份 + 迟疑",
            "score": 71,
            "status": "已完成 2 轮",
            "summary": "观点有了，但还可以继续打磨故事。",
        },
        {
            "title": "工作 + 勇气",
            "score": 81,
            "status": "已完成 3 轮",
            "summary": "表达自然，已有比较完整的整理版。",
        },
    ]


def normalize_phone(phone):
    phone = (phone or "").strip()
    if not re.fullmatch(r"1\d{10}", phone):
        raise ValueError("请输入正确的 11 位手机号")
    return phone


def payment_demo_hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def payment_demo_mask_phone(phone):
    if not phone:
        return ""
    return f"{phone[:3]}****{phone[-4:]}"


def payment_demo_current_user(conn, auth_token):
    if not auth_token:
        return None, None
    session_row = conn.execute(
        "SELECT * FROM payment_demo_auth_sessions WHERE token = ?",
        (auth_token,),
    ).fetchone()
    if not session_row:
        return None, None
    user_row = conn.execute(
        "SELECT * FROM payment_demo_users WHERE id = ?",
        (session_row["user_id"],),
    ).fetchone()
    if not user_row:
        return None, None
    return user_row, session_row


def payment_demo_create_session(conn, user_id, client_id):
    token = f"paytok-{uuid.uuid4().hex}"
    conn.execute(
        """
        INSERT INTO payment_demo_auth_sessions
        (token, user_id, client_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (token, user_id, client_id, now_text(), now_text()),
    )
    conn.commit()
    return token


def ensure_app_user_for_account(conn, payment_user_row, client_id=""):
    if not payment_user_row:
        return None

    linked_user = None
    linked_id = payment_user_row["app_user_id"] if "app_user_id" in payment_user_row.keys() else None
    if linked_id:
        linked_user = conn.execute("SELECT * FROM users WHERE id = ?", (linked_id,)).fetchone()

    if not linked_user:
        nickname = f"用户{payment_user_row['phone'][-4:]}"
        now = now_text()
        if client_id:
            conn.execute("UPDATE users SET client_id = NULL WHERE client_id = ?", (client_id,))
        conn.execute(
            """
            INSERT INTO users
            (nickname, started_rounds_today, current_round_index, client_id, contact, is_registered, registered_at, created_at)
            VALUES (?, 0, 0, ?, ?, 1, ?, ?)
            """,
            (nickname, client_id or f"acct-{payment_user_row['phone']}", payment_user_row["phone"], now, now),
        )
        linked_user = conn.execute("SELECT * FROM users WHERE rowid = last_insert_rowid()").fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO membership (user_id, is_member, plan_name) VALUES (?, 0, '未开通训练卡')",
            (linked_user["id"],),
        )
        conn.execute(
            "UPDATE payment_demo_users SET app_user_id = ?, updated_at = ? WHERE id = ?",
            (linked_user["id"], now_text(), payment_user_row["id"]),
        )
        conn.commit()

    if client_id:
        existing_client_owner = conn.execute(
            "SELECT id FROM users WHERE client_id = ? AND id != ?",
            (client_id, linked_user["id"]),
        ).fetchone()
        if existing_client_owner:
            conn.execute(
                "UPDATE users SET client_id = NULL WHERE id = ?",
                (existing_client_owner["id"],),
            )

    conn.execute(
        """
        UPDATE users
        SET client_id = ?, contact = ?, is_registered = 1, registered_at = COALESCE(registered_at, ?)
        WHERE id = ?
        """,
        (client_id or linked_user["client_id"], payment_user_row["phone"], now_text(), linked_user["id"]),
    )
    conn.commit()
    return conn.execute("SELECT * FROM users WHERE id = ?", (linked_user["id"],)).fetchone()


def resolve_request_user(conn, client_id, auth_token=""):
    payment_user_row, _ = payment_demo_current_user(conn, auth_token)
    if payment_user_row:
        return ensure_app_user_for_account(conn, payment_user_row, client_id)
    return resolve_user(conn, client_id)


def account_context(conn, auth_token, client_id=""):
    payment_user_row, session_row = payment_demo_current_user(conn, auth_token)
    app_user_row = None
    membership_row = None
    latest_order = None
    status = "inactive"

    if payment_user_row:
        app_user_row = ensure_app_user_for_account(conn, payment_user_row, client_id)
        membership_row = conn.execute(
            "SELECT * FROM payment_demo_memberships WHERE user_id = ?",
            (payment_user_row["id"],),
        ).fetchone()
        latest_order = conn.execute(
            "SELECT * FROM payment_demo_orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (payment_user_row["id"],),
        ).fetchone()
        status = payment_demo_membership_status(membership_row)

    return {
        "paymentUser": payment_user_row,
        "session": session_row,
        "appUser": app_user_row,
        "membership": membership_row,
        "latestOrder": latest_order,
        "status": status,
    }


def payment_membership_for_training_user(conn, app_user_id):
    row = conn.execute(
        """
        SELECT m.*
        FROM payment_demo_memberships m
        JOIN payment_demo_users u ON u.id = m.user_id
        WHERE u.app_user_id = ?
        """,
        (app_user_id,),
    ).fetchone()
    return row


def training_access_status(conn, auth_token, app_user_id):
    if not auth_token:
        return "unauthenticated", None
    membership_row = payment_membership_for_training_user(conn, app_user_id)
    if not membership_row:
        return "inactive", None
    return payment_demo_membership_status(membership_row), membership_row


def consume_training_credit(conn, app_user_id):
    membership_row = payment_membership_for_training_user(conn, app_user_id)
    status = payment_demo_membership_status(membership_row)
    if status != "active":
        raise ValueError("当前训练权益不可用")
    remaining = max(0, int(membership_row["remaining_groups"]) - 1)
    conn.execute(
        "UPDATE payment_demo_memberships SET remaining_groups = ?, updated_at = ? WHERE user_id = ?",
        (remaining, now_text(), membership_row["user_id"]),
    )
    conn.commit()
    return remaining


def payment_demo_membership_status(membership_row):
    if not membership_row:
        return "inactive"
    now = datetime.now()
    expire_at = datetime.fromisoformat(membership_row["expire_at"])
    if membership_row["remaining_groups"] <= 0:
        return "quota_exhausted"
    if expire_at < now:
        return "expired"
    return "active"


def upsert_payment_membership(conn, user_id, phone, credits, days, plan_id="admin_grant", plan_name="后台手动增加", order_no=""):
    credits = max(0, int(credits or 0))
    days = max(0, int(days or 0))
    if credits <= 0 and days <= 0:
        raise ValueError("增加权益时，次数和延长天数至少填一个")

    activated_at = datetime.now()
    existing = conn.execute(
        "SELECT * FROM payment_demo_memberships WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if existing:
        try:
            current_expire = datetime.fromisoformat(existing["expire_at"])
        except (TypeError, ValueError):
            current_expire = activated_at
        base_expire = current_expire if current_expire > activated_at else activated_at
        expire_at = base_expire + timedelta(days=days)
        total_groups = int(existing["total_groups"] or 0) + credits
        remaining_groups = max(0, int(existing["remaining_groups"] or 0)) + credits
        conn.execute(
            """
            UPDATE payment_demo_memberships
            SET phone = ?,
                plan_id = ?,
                plan_name = ?,
                total_groups = ?,
                remaining_groups = ?,
                expire_at = ?,
                current_order_no = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                phone,
                plan_id,
                plan_name,
                total_groups,
                remaining_groups,
                expire_at.isoformat(),
                order_no or existing["current_order_no"] or "",
                now_text(),
                user_id,
            ),
        )
    else:
        expire_at = activated_at + timedelta(days=max(days, 1))
        conn.execute(
            """
            INSERT INTO payment_demo_memberships
            (user_id, phone, plan_id, plan_name, total_groups, remaining_groups, activated_at, expire_at, current_order_no, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                phone,
                plan_id,
                plan_name,
                credits,
                credits,
                activated_at.isoformat(),
                expire_at.isoformat(),
                order_no,
                now_text(),
            ),
        )


def apply_pending_entitlement_for_user(conn, user_id, phone):
    pending = conn.execute(
        "SELECT * FROM admin_pending_entitlements WHERE phone = ?",
        (phone,),
    ).fetchone()
    if not pending:
        return
    upsert_payment_membership(
        conn,
        user_id,
        phone,
        pending["credits"],
        pending["days"],
        "admin_pending_grant",
        "后台预置权益",
    )
    conn.execute(
        """
        INSERT INTO admin_entitlement_adjustments
        (id, phone, user_id, credits, days, status, note, created_at)
        VALUES (?, ?, ?, ?, ?, 'applied_on_register', ?, ?)
        """,
        (
            f"grant-{uuid.uuid4().hex[:12]}",
            phone,
            user_id,
            pending["credits"],
            pending["days"],
            pending["note"],
            now_text(),
        ),
    )
    conn.execute("DELETE FROM admin_pending_entitlements WHERE phone = ?", (phone,))


def payment_demo_state(conn, client_id, auth_token=None):
    ctx = account_context(conn, auth_token, client_id)
    trial = free_trial_config(conn)
    user_row = ctx["paymentUser"]
    membership_row = ctx["membership"]
    latest_order = ctx["latestOrder"]
    status = ctx["status"]

    account_data = None
    if membership_row:
        account_data = {
            "phone": membership_row["phone"],
            "phoneMasked": payment_demo_mask_phone(membership_row["phone"]),
            "planId": membership_row["plan_id"],
            "planName": membership_row["plan_name"],
            "displayPrice": PAYMENT_PLAN_CATALOG.get(membership_row["plan_id"], {}).get("displayPrice"),
            "totalGroups": membership_row["total_groups"],
            "remainingGroups": membership_row["remaining_groups"],
            "totalCredits": membership_row["total_groups"],
            "remainingCredits": membership_row["remaining_groups"],
            "activatedAt": membership_row["activated_at"],
            "expireAt": membership_row["expire_at"],
            "currentOrderNo": membership_row["current_order_no"],
        }

    order_data = None
    if latest_order:
        order_data = {
            "orderNo": latest_order["order_no"],
            "phone": latest_order["phone"],
            "planId": latest_order["plan_id"],
            "planName": latest_order["plan_name"],
            "amount": latest_order["amount"],
            "displayPrice": PAYMENT_PLAN_CATALOG.get(latest_order["plan_id"], {}).get("displayPrice"),
            "status": latest_order["status"],
            "createdAt": latest_order["created_at"],
            "paidAt": latest_order["paid_at"],
        }

    return {
        "clientId": client_id,
        "auth": {
            "loggedIn": bool(user_row),
            "phone": user_row["phone"] if user_row else "",
            "phoneMasked": payment_demo_mask_phone(user_row["phone"]) if user_row else "",
            "authToken": auth_token if user_row else "",
        },
        "status": status,
        "plans": [payment_plan_payload(plan) for plan in PAYMENT_PLAN_CATALOG.values()],
        "account": account_data,
        "latestOrder": order_data,
        "recordsPreview": payment_demo_records_preview(membership_row),
        "freeTrialCredits": trial["credits"],
        "freeTrialDays": trial["days"],
    }


def payment_demo_submit_fields(order, base_url, client_ip, user_agent):
    config = load_payment_demo_config()
    if not config["pid"] or not config["key"]:
        raise ValueError("本地支付 demo 还没有配置 z-pay 商户 PID / KEY")

    device = "mobile" if "Mobile" in (user_agent or "") else "pc"
    notify_url = f"{base_url}/api/payment-demo/notify"
    return_url = f"{base_url}/?payReturn=1"
    payload = {
        "pid": config["pid"],
        "type": order["pay_type"],
        "out_trade_no": order["order_no"],
        "notify_url": notify_url,
        "return_url": return_url,
        "name": order["plan_name"],
        "money": f"{order['amount']:.2f}",
        "clientip": client_ip or "127.0.0.1",
        "device": device,
        "param": str(order["user_id"]),
        "sign_type": "MD5",
    }
    payload["sign"] = zpay_sign(payload, config["key"])
    return {
        "action": config["submit_url"],
        "method": "POST",
        "fields": payload,
    }


def payment_demo_register(conn, client_id, phone, password, confirm_password):
    client_id = (client_id or "").strip()
    phone = normalize_phone(phone)
    password = (password or "").strip()
    confirm_password = (confirm_password or "").strip()
    if len(password) < 6:
        raise ValueError("密码至少需要 6 位")
    if password != confirm_password:
        raise ValueError("两次输入的密码不一致")
    existing = conn.execute("SELECT id FROM payment_demo_users WHERE phone = ?", (phone,)).fetchone()
    if existing:
        raise ValueError("这个手机号已经注册过了，请直接登录")
    device_config = register_device_config(conn)
    if client_id and client_id not in device_config["whitelist"]:
        registered_count = conn.execute(
            """
            SELECT COUNT(DISTINCT phone) AS count
            FROM payment_demo_users
            WHERE registered_client_id = ?
            """,
            (client_id,),
        ).fetchone()["count"]
        if registered_count >= device_config["limit"]:
            raise ValueError("注册可能存在异常，请稍后再试或联系开发人员～")
    conn.execute(
        """
        INSERT INTO payment_demo_users
        (phone, password_hash, registered_client_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (phone, payment_demo_hash_password(password), client_id, now_text(), now_text()),
    )
    user_id = conn.execute("SELECT id FROM payment_demo_users WHERE phone = ?", (phone,)).fetchone()["id"]
    trial = free_trial_config(conn)
    activated_at = datetime.now()
    expire_at = activated_at + timedelta(days=trial["days"])
    conn.execute(
        """
        INSERT INTO payment_demo_memberships
        (user_id, phone, plan_id, plan_name, total_groups, remaining_groups, activated_at, expire_at, current_order_no, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            phone,
            "gift_trial",
            "新用户赠送",
            trial["credits"],
            trial["credits"],
            activated_at.isoformat(),
            expire_at.isoformat(),
            "",
            now_text(),
        ),
    )
    apply_pending_entitlement_for_user(conn, user_id, phone)
    conn.commit()
    token = payment_demo_create_session(conn, user_id, client_id)
    return payment_demo_state(conn, client_id, token)


def payment_demo_login(conn, client_id, phone, password):
    phone = normalize_phone(phone)
    password = (password or "").strip()
    user_row = conn.execute("SELECT * FROM payment_demo_users WHERE phone = ?", (phone,)).fetchone()
    if not user_row:
        raise ValueError("这个手机号还没有注册，请先注册。")
    if user_row["password_hash"] != payment_demo_hash_password(password):
        raise ValueError("密码不正确，请重新输入。")
    token = payment_demo_create_session(conn, user_row["id"], client_id)
    return payment_demo_state(conn, client_id, token)


def payment_demo_logout(conn, auth_token, client_id):
    if auth_token:
        conn.execute("DELETE FROM payment_demo_auth_sessions WHERE token = ?", (auth_token,))
        conn.commit()
    return payment_demo_state(conn, client_id, None)


def payment_demo_create_order(conn, client_id, auth_token, plan_id, base_url, client_ip, user_agent):
    user_row, _ = payment_demo_current_user(conn, auth_token)
    if not user_row:
        raise ValueError("请先登录账户，再继续支付")
    phone = user_row["phone"]
    plan = PAYMENT_PLAN_CATALOG.get(plan_id)
    if not plan:
        raise ValueError("请选择要开通的训练卡")
    amount = plan_charge_amount(plan, base_url)

    order_no = f"PD{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
    order_row = {
        "order_no": order_no,
        "client_id": client_id,
        "user_id": user_row["id"],
        "phone": phone,
        "plan_id": plan["planId"],
        "plan_name": plan["planName"],
        "amount": amount,
        "total_groups": plan["totalCredits"],
        "total_days": plan["days"],
        "status": "pending",
        "pay_type": "alipay",
        "created_at": now_text(),
    }

    payment_form = payment_demo_submit_fields(order_row, base_url, client_ip, user_agent)
    conn.execute(
        """
        INSERT INTO payment_demo_orders
        (order_no, client_id, user_id, phone, plan_id, plan_name, amount, total_groups, total_days, status, pay_type, submit_payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        """,
        (
            order_row["order_no"],
            order_row["client_id"],
            order_row["user_id"],
            order_row["phone"],
            order_row["plan_id"],
            order_row["plan_name"],
            order_row["amount"],
            order_row["total_groups"],
            order_row["total_days"],
            order_row["pay_type"],
            json_dumps(payment_form["fields"]),
            order_row["created_at"],
        ),
    )
    conn.commit()

    return {
        "orderNo": order_no,
        "phone": phone,
        "planId": plan["planId"],
        "planName": plan["planName"],
        "amount": amount,
        "displayPrice": plan["displayPrice"],
        "totalGroups": plan["totalCredits"],
        "totalCredits": plan["totalCredits"],
        "days": plan["days"],
        "paymentForm": payment_form,
    }


def payment_demo_activate_account(conn, order_row, trade_no="", callback_payload=None):
    activated_at = datetime.now()
    paid_at = now_text()
    updated = conn.execute(
        """
        UPDATE payment_demo_orders
        SET status = 'paid',
            zpay_trade_no = ?,
            callback_payload_json = ?,
            paid_at = CASE WHEN paid_at = '' THEN ? ELSE paid_at END
        WHERE order_no = ? AND status != 'paid'
        """,
        (
            trade_no or "",
            json_dumps(callback_payload or {}),
            paid_at,
            order_row["order_no"],
        ),
    )
    if updated.rowcount == 0:
        conn.commit()
        return

    existing = conn.execute(
        "SELECT * FROM payment_demo_memberships WHERE user_id = ?",
        (order_row["user_id"],),
    ).fetchone()
    if existing:
        try:
            current_expire = datetime.fromisoformat(existing["expire_at"])
        except (TypeError, ValueError):
            current_expire = activated_at
        base_expire = current_expire if current_expire > activated_at else activated_at
        expire_at = base_expire + timedelta(days=order_row["total_days"])
        total_groups = int(existing["total_groups"] or 0) + int(order_row["total_groups"] or 0)
        remaining_groups = max(0, int(existing["remaining_groups"] or 0)) + int(order_row["total_groups"] or 0)
        activated_value = existing["activated_at"] or activated_at.isoformat()
        conn.execute(
            """
            UPDATE payment_demo_memberships
            SET phone = ?,
                plan_id = ?,
                plan_name = ?,
                total_groups = ?,
                remaining_groups = ?,
                activated_at = ?,
                expire_at = ?,
                current_order_no = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                order_row["phone"],
                order_row["plan_id"],
                order_row["plan_name"],
                total_groups,
                remaining_groups,
                activated_value,
                expire_at.isoformat(),
                order_row["order_no"],
                now_text(),
                order_row["user_id"],
            ),
        )
    else:
        expire_at = activated_at + timedelta(days=order_row["total_days"])
        conn.execute(
            """
            INSERT INTO payment_demo_memberships
            (user_id, phone, plan_id, plan_name, total_groups, remaining_groups, activated_at, expire_at, current_order_no, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_row["user_id"],
                order_row["phone"],
                order_row["plan_id"],
                order_row["plan_name"],
                order_row["total_groups"],
                order_row["total_groups"],
                activated_at.isoformat(),
                expire_at.isoformat(),
                order_row["order_no"],
                now_text(),
            ),
        )
    conn.commit()


def payment_demo_query_order(order_no):
    config = load_payment_demo_config()
    if not config["pid"] or not config["key"]:
        return None
    query = urlencode(
        {
            "act": "order",
            "pid": config["pid"],
            "key": config["key"],
            "out_trade_no": order_no,
        }
    )
    url = f"{config['order_query_url']}?{query}"
    try:
        request = Request(url, method="GET")
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    return payload


def payment_demo_verify_callback_params(params):
    config = load_payment_demo_config()
    sign = (params.get("sign") or "").strip()
    if not sign:
        raise ValueError("支付返回里缺少签名")
    expected = zpay_sign(params, config["key"])
    if expected != sign:
        raise ValueError("支付返回签名校验失败")


def payment_demo_complete_return(conn, callback_params, client_id=None, auth_token=None):
    order_no = (callback_params.get("out_trade_no") or "").strip()
    if not order_no:
        raise ValueError("支付返回里缺少商户订单号")

    order_row = conn.execute(
        "SELECT * FROM payment_demo_orders WHERE order_no = ?",
        (order_no,),
    ).fetchone()
    if not order_row:
        raise ValueError("本地没有找到这笔支付订单")
    if order_row["status"] == "paid":
        return payment_demo_state(conn, client_id or order_row["client_id"], auth_token)

    payment_demo_verify_callback_params(callback_params)

    query_result = payment_demo_query_order(order_no)
    query_paid = bool(query_result and str(query_result.get("code")) == "1" and str(query_result.get("status")) == "1")
    return_paid = callback_params.get("trade_status") == "TRADE_SUCCESS"
    if not (query_paid or return_paid):
        raise ValueError("这笔订单还没有确认支付成功")

    payment_demo_activate_account(
        conn,
        order_row,
        trade_no=callback_params.get("trade_no", ""),
        callback_payload=callback_params,
    )
    return payment_demo_state(conn, client_id or order_row["client_id"], auth_token)


def payment_demo_reset(conn, client_id, auth_token=None):
    user_row, _ = payment_demo_current_user(conn, auth_token)
    if user_row:
        conn.execute("DELETE FROM payment_demo_memberships WHERE user_id = ?", (user_row["id"],))
        conn.execute("DELETE FROM payment_demo_orders WHERE user_id = ?", (user_row["id"],))
    else:
        conn.execute("DELETE FROM payment_demo_orders WHERE client_id = ?", (client_id,))
    conn.commit()
    return payment_demo_state(conn, client_id, auth_token)


def history_list(conn, user_id):
    rows = conn.execute(
        "SELECT * FROM history_records WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "timeLabel": row["time_label"],
            "pair": json_loads(row["pair_json"], []),
            "excerpt": row["excerpt"],
            "transcriptText": row["transcript_text"] or row["excerpt"],
            "score": row["score"],
            "summary": row["summary"],
            "details": json_loads(row["details_json"], []),
            "suggestions": json_loads(row["suggestions_json"], []),
            "attemptCount": len(json_loads(row["attempts_json"], [])),
            "attempts": json_loads(row["attempts_json"], []),
            "finalFeedback": json_loads(row["final_feedback_json"], {}),
        }
        for row in rows
    ]


def payment_demo_orders_for_user(conn, user_id):
    rows = conn.execute(
        """
        SELECT *
        FROM payment_demo_orders
        WHERE user_id = ?
        ORDER BY COALESCE(paid_at, created_at) DESC
        """,
        (user_id,),
    ).fetchall()
    return [
        {
            "orderNo": row["order_no"],
            "planId": row["plan_id"],
            "planName": row["plan_name"],
            "amount": row["amount"],
            "displayAmount": f"¥{float(row['amount'] or 0):.2f}",
            "credits": row["total_groups"],
            "days": row["total_days"],
            "status": "已支付" if row["status"] == "paid" else "未完成支付",
            "statusRaw": row["status"],
            "createdAt": row["created_at"],
            "paidAt": row["paid_at"],
        }
        for row in rows
    ]


def payment_demo_refresh_order_status(conn, client_id, auth_token, order_no=""):
    user_row, _ = payment_demo_current_user(conn, auth_token)
    if not user_row:
        raise ValueError("请先登录账户")

    row = None
    if order_no:
        row = conn.execute(
            "SELECT * FROM payment_demo_orders WHERE order_no = ? AND user_id = ?",
            (order_no, user_row["id"]),
        ).fetchone()
    if not row:
        row = conn.execute(
            """
            SELECT * FROM payment_demo_orders
            WHERE user_id = ? AND status != 'paid'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_row["id"],),
        ).fetchone()

    if not row:
        return {
            "paid": False,
            "orderNo": order_no,
            "message": "暂时没有需要确认的未完成订单",
            "state": payment_demo_state(conn, client_id, auth_token),
        }
    if row["status"] == "paid":
        return {
            "paid": True,
            "orderNo": row["order_no"],
            "message": "支付已完成",
            "state": payment_demo_state(conn, client_id, auth_token),
        }

    query_result = payment_demo_query_order(row["order_no"])
    query_paid = bool(query_result and str(query_result.get("code")) == "1" and str(query_result.get("status")) == "1")
    if query_paid:
        payment_demo_activate_account(
            conn,
            row,
            trade_no=str(query_result.get("trade_no") or ""),
            callback_payload=query_result,
        )
        return {
            "paid": True,
            "orderNo": row["order_no"],
            "message": "支付已完成，权益已到账",
            "state": payment_demo_state(conn, client_id, auth_token),
        }

    return {
        "paid": False,
        "orderNo": row["order_no"],
        "message": "支付暂未完成，可稍后刷新状态或重新购买。",
        "state": payment_demo_state(conn, client_id, auth_token),
    }


def beginner_word_count():
    words = set()
    for pool in BEGINNER_CARD_POOLS.values():
        words.update(pool)
    return len(words)


def paid_repurchase_order_count(conn, date_clause="", params=()):
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM payment_demo_orders o
        WHERE o.status = 'paid'
          {date_clause}
          AND (
            SELECT COUNT(*)
            FROM payment_demo_orders earlier
            WHERE earlier.status = 'paid'
              AND earlier.phone = o.phone
              AND COALESCE(earlier.paid_at, earlier.created_at, earlier.order_no) < COALESCE(o.paid_at, o.created_at, o.order_no)
          ) >= 1
        """,
        params,
    ).fetchone()
    return row["count"]


def training_metrics(conn, date_clause="", params=()):
    entered_pairs = conn.execute(
        f"""
        SELECT COUNT(DISTINCT event_key) AS count
        FROM training_events
        WHERE event_name = 'speaking_page_entered'
          {date_clause}
        """,
        params,
    ).fetchone()["count"]
    submitted_pairs = conn.execute(
        f"""
        SELECT COUNT(DISTINCT event_key) AS count
        FROM training_events
        WHERE event_name = 'coach_feedback_submitted'
          {date_clause}
        """,
        params,
    ).fetchone()["count"]
    success_pairs = conn.execute(
        f"""
        SELECT COUNT(DISTINCT event_key) AS count
        FROM training_events
        WHERE event_name = 'coach_feedback_success'
          {date_clause}
        """,
        params,
    ).fetchone()["count"]
    feedback_count = conn.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM history_records
        WHERE 1 = 1
          {date_clause}
        """,
        params,
    ).fetchone()["count"]
    avg_score = conn.execute(
        f"""
        SELECT COALESCE(AVG(score), 0) AS value
        FROM history_records
        WHERE 1 = 1
          {date_clause}
        """,
        params,
    ).fetchone()["value"]
    avg_attempts = conn.execute(
        f"""
        SELECT COALESCE(AVG(CASE
          WHEN json_array_length(attempts_json) > 0 THEN json_array_length(attempts_json)
          ELSE 1
        END), 0) AS value
        FROM history_records
        WHERE 1 = 1
          {date_clause}
        """,
        params,
    ).fetchone()["value"]
    return {
        "feedbackCount": feedback_count,
        "enteredPairCount": entered_pairs,
        "submittedPairCount": submitted_pairs,
        "coachSuccessPairCount": success_pairs,
        "avgAttemptCount": round(float(avg_attempts or 0), 2),
        "avgScore": round(float(avg_score or 0), 1),
    }


def admin_dashboard_metrics(conn):
    users = conn.execute("SELECT COUNT(*) AS count FROM payment_demo_users").fetchone()["count"]
    paid_users = conn.execute("SELECT COUNT(*) AS count FROM payment_demo_memberships").fetchone()["count"]
    paid_orders = conn.execute(
        "SELECT COUNT(*) AS count FROM payment_demo_orders WHERE status = 'paid'"
    ).fetchone()["count"]
    pending_orders = conn.execute(
        "SELECT COUNT(*) AS count FROM payment_demo_orders WHERE status != 'paid'"
    ).fetchone()["count"]
    revenue_row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM payment_demo_orders WHERE status = 'paid'"
    ).fetchone()
    training = training_metrics(conn)
    return {
        "users": {
            "registeredUsers": users,
            "paidUsers": paid_users,
        },
        "orders": {
            "paidOrders": paid_orders,
            "pendingOrders": pending_orders,
            "repurchaseOrders": paid_repurchase_order_count(conn),
            "orderRevenue": float(revenue_row["total"] or 0),
            "revenue": f"¥{float(revenue_row['total'] or 0):.2f}",
        },
        "training": {
            **training,
            "wordCount": beginner_word_count(),
        },
    }


def save_admin_daily_snapshot(conn, metrics):
    snapshot_date = datetime.now().strftime("%Y-%m-%d")
    existing = conn.execute(
        "SELECT snapshot_date FROM admin_daily_snapshots WHERE snapshot_date = ?",
        (snapshot_date,),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE admin_daily_snapshots SET metrics_json = ?, updated_at = ? WHERE snapshot_date = ?",
            (json_dumps(metrics), now_text(), snapshot_date),
        )
    else:
        conn.execute(
            """
            INSERT INTO admin_daily_snapshots (snapshot_date, metrics_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_date, json_dumps(metrics), now_text(), now_text()),
        )
    conn.commit()


def admin_dashboard(conn):
    metrics = admin_dashboard_metrics(conn)
    save_admin_daily_snapshot(conn, metrics)
    return metrics


def admin_seven_day_export_rows(conn):
    rows = []
    for offset in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d")
        registered = conn.execute(
            "SELECT COUNT(*) AS count FROM payment_demo_users WHERE substr(created_at, 1, 10) = ?",
            (day,),
        ).fetchone()["count"]
        paid_users = conn.execute(
            """
            SELECT COUNT(DISTINCT user_id) AS count
            FROM payment_demo_memberships
            WHERE substr(activated_at, 1, 10) = ?
            """,
            (day,),
        ).fetchone()["count"]
        paid_orders = conn.execute(
            """
            SELECT COUNT(*) AS count FROM payment_demo_orders
            WHERE status = 'paid' AND substr(COALESCE(paid_at, created_at), 1, 10) = ?
            """,
            (day,),
        ).fetchone()["count"]
        pending_orders = conn.execute(
            "SELECT COUNT(*) AS count FROM payment_demo_orders WHERE status != 'paid' AND substr(created_at, 1, 10) = ?",
            (day,),
        ).fetchone()["count"]
        revenue = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total FROM payment_demo_orders
            WHERE status = 'paid' AND substr(COALESCE(paid_at, created_at), 1, 10) = ?
            """,
            (day,),
        ).fetchone()["total"]
        training = training_metrics(conn, "AND substr(created_at, 1, 10) = ?", (day,))
        rows.append(
            {
                "日期": day,
                "注册用户数": registered,
                "付费用户数": paid_users,
                "已支付订单数": paid_orders,
                "待支付订单数": pending_orders,
                "订单收入": f"¥{float(revenue or 0):.2f}",
                "复购订单数": paid_repurchase_order_count(
                    conn,
                    "AND substr(COALESCE(o.paid_at, o.created_at), 1, 10) = ?",
                    (day,),
                ),
                "累计点评次数": training["feedbackCount"],
                "进入表达页词组数": training["enteredPairCount"],
                "提交教练点评词组数": training["submittedPairCount"],
                "教练点评成功词组数": training["coachSuccessPairCount"],
                "平均训练轮次": training["avgAttemptCount"],
                "点评平均分": training["avgScore"],
            }
        )
    return rows


def admin_users(conn):
    rows = conn.execute(
        """
        SELECT
          p.id,
          p.phone,
          p.created_at,
          p.app_user_id,
          p.registered_client_id,
          m.plan_name,
          m.total_groups,
          m.remaining_groups,
          m.expire_at,
          COALESCE(d.device_register_count, 0) AS device_register_count,
          COALESCE(o.paid_order_count, 0) AS paid_order_count,
          COALESCE(t.training_count, 0) AS training_count
        FROM payment_demo_users p
        LEFT JOIN payment_demo_memberships m ON m.user_id = p.id
        LEFT JOIN (
          SELECT registered_client_id, COUNT(DISTINCT phone) AS device_register_count
          FROM payment_demo_users
          WHERE registered_client_id != ''
          GROUP BY registered_client_id
        ) d ON d.registered_client_id = p.registered_client_id
        LEFT JOIN (
          SELECT user_id, COUNT(*) AS paid_order_count
          FROM payment_demo_orders
          WHERE status = 'paid'
          GROUP BY user_id
        ) o ON o.user_id = p.id
        LEFT JOIN (
          SELECT user_id, COUNT(*) AS training_count
          FROM history_records
          GROUP BY user_id
        ) t ON t.user_id = p.app_user_id
        ORDER BY p.id DESC
        """
    ).fetchall()
    def admin_benefit_status(row):
        if not row["plan_name"]:
            return "未开通"
        try:
            expire_at = datetime.fromisoformat(row["expire_at"])
        except (TypeError, ValueError):
            return "权益已失效"
        if int(row["remaining_groups"] or 0) <= 0 or expire_at < datetime.now():
            return "权益已失效"
        return "权益生效中"

    pending_rows = conn.execute(
        """
        SELECT p.phone, p.credits, p.days, p.note, p.updated_at
        FROM admin_pending_entitlements p
        LEFT JOIN payment_demo_users u ON u.phone = p.phone
        WHERE u.id IS NULL
        ORDER BY p.updated_at DESC
        """
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "displayId": f"A{int(row['id']):04d}",
            "nickname": row["phone"],
            "phone": row["phone"],
            "registeredAt": (row["created_at"] or "-")[:16],
            "registeredClientId": row["registered_client_id"] or "",
            "deviceRegisterCount": row["device_register_count"] or 0,
            "activityState": admin_benefit_status(row),
            "membershipStatus": row["plan_name"] or "未开通",
            "totalTrainingCount": row["training_count"],
            "totalCredits": row["total_groups"] or 0,
            "remainingCredits": row["remaining_groups"] or 0,
            "expireAt": str(row["expire_at"] or "-")[:10],
            "paidOrderCount": row["paid_order_count"],
            "trainingSummary": f"累计 {row['training_count']} 次 / 剩余 {row['remaining_groups'] or 0} 次",
            "pendingEntitlement": False,
        }
        for row in rows
    ] + [
        {
            "id": "",
            "displayId": "未注册",
            "nickname": row["phone"],
            "phone": row["phone"],
            "registeredAt": "-",
            "registeredClientId": "",
            "deviceRegisterCount": 0,
            "activityState": "待注册到账",
            "membershipStatus": "待注册领取",
            "totalTrainingCount": 0,
            "totalCredits": row["credits"],
            "remainingCredits": row["credits"],
            "expireAt": f"注册后 {row['days']} 天",
            "paidOrderCount": 0,
            "trainingSummary": row["note"] or "手机号注册后自动到账",
            "pendingEntitlement": True,
        }
        for row in pending_rows
    ]


def admin_user_benefits_config(conn):
    trial = free_trial_config(conn)
    pending_count = conn.execute("SELECT COUNT(*) AS count FROM admin_pending_entitlements").fetchone()["count"]
    return {
        "freeTrialCredits": trial["credits"],
        "freeTrialDays": trial["days"],
        "pendingEntitlementCount": pending_count,
    }


def update_admin_user_benefits_config(conn, body):
    old_config = free_trial_config(conn)
    try:
        free_trial_credits = max(0, int(body.get("freeTrialCredits", FREE_TRIAL_CREDITS)))
        free_trial_days = max(1, int(body.get("freeTrialDays", FREE_TRIAL_DAYS)))
    except (TypeError, ValueError):
        raise ValueError("注册赠送次数和有效天数必须是数字")
    conn.executemany(
        """
        INSERT INTO app_config (config_key, config_value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(config_key) DO UPDATE SET
          config_value = excluded.config_value,
          updated_at = excluded.updated_at
        """,
        [
            ("account.free_trial_credits", str(free_trial_credits), now_text()),
            ("account.free_trial_days", str(free_trial_days), now_text()),
        ],
    )
    conn.execute(
        """
        INSERT INTO admin_entitlement_adjustments
        (id, phone, user_id, credits, days, status, note, created_at)
        VALUES (?, '', NULL, ?, ?, 'registration_config_updated', ?, ?)
        """,
        (
            f"benefit-{uuid.uuid4().hex[:12]}",
            free_trial_credits,
            free_trial_days,
            f"注册赠送从 {old_config['credits']} 次/{old_config['days']} 天调整为 {free_trial_credits} 次/{free_trial_days} 天",
            now_text(),
        ),
    )
    conn.commit()
    return admin_user_benefits_config(conn)


def admin_entitlement_history(conn):
    rows = conn.execute(
        """
        SELECT id, phone, user_id, credits, days, status, note, created_at
        FROM admin_entitlement_adjustments
        ORDER BY created_at DESC, id DESC
        LIMIT 100
        """
    ).fetchall()
    status_labels = {
        "registration_config_updated": "注册权益设置",
        "applied": "已注册用户加权益",
        "pending_register": "未注册手机号加权益",
        "applied_on_register": "注册后自动到账",
        "expire_at_updated": "设置到期时间",
    }
    return [
        {
            "id": row["id"],
            "type": "注册权益" if row["status"] == "registration_config_updated" else "手动加权益",
            "phone": row["phone"] or "-",
            "userId": row["user_id"] or "",
            "credits": row["credits"],
            "days": row["days"],
            "status": row["status"],
            "statusLabel": status_labels.get(row["status"], row["status"]),
            "note": row["note"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def admin_pending_entitlements(conn):
    rows = conn.execute(
        """
        SELECT phone, credits, days, note, created_at, updated_at
        FROM admin_pending_entitlements
        ORDER BY updated_at DESC
        """
    ).fetchall()
    return [
        {
            "phone": row["phone"],
            "credits": row["credits"],
            "days": row["days"],
            "note": row["note"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
        for row in rows
    ]


def admin_grant_entitlement(conn, body):
    phone = normalize_phone(body.get("phone", ""))
    try:
        credits = max(0, int(body.get("credits", 0)))
        days = max(0, int(body.get("days", 0)))
    except (TypeError, ValueError):
        raise ValueError("增加次数和延长天数必须是数字")
    note = (body.get("note") or "").strip()
    if credits <= 0 and days <= 0:
        raise ValueError("增加权益时，次数和延长天数至少填一个")

    user_row = conn.execute("SELECT * FROM payment_demo_users WHERE phone = ?", (phone,)).fetchone()
    if user_row:
        upsert_payment_membership(conn, user_row["id"], phone, credits, days)
        status = "applied"
        user_id = user_row["id"]
    else:
        existing = conn.execute("SELECT * FROM admin_pending_entitlements WHERE phone = ?", (phone,)).fetchone()
        conn.execute(
            """
            INSERT INTO admin_pending_entitlements
            (phone, credits, days, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
              credits = admin_pending_entitlements.credits + excluded.credits,
              days = admin_pending_entitlements.days + excluded.days,
              note = excluded.note,
              updated_at = excluded.updated_at
            """,
            (phone, credits, days, note, existing["created_at"] if existing else now_text(), now_text()),
        )
        status = "pending_register"
        user_id = None

    conn.execute(
        """
        INSERT INTO admin_entitlement_adjustments
        (id, phone, user_id, credits, days, status, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (f"grant-{uuid.uuid4().hex[:12]}", phone, user_id, credits, days, status, note, now_text()),
    )
    conn.commit()
    return {
        "status": status,
        "users": admin_users(conn),
        "benefitsConfig": admin_user_benefits_config(conn),
        "pendingEntitlements": admin_pending_entitlements(conn),
        "history": admin_entitlement_history(conn),
    }


def parse_admin_expire_date(value):
    raw = (value or "").strip()
    if not raw:
        raise ValueError("请选择到期日期")
    try:
        expire_day = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        raise ValueError("到期日期格式不正确")
    return expire_day.replace(hour=23, minute=59, second=59, microsecond=0)


def admin_set_entitlement_expire_at(conn, body):
    phone = normalize_phone(body.get("phone", ""))
    expire_at = parse_admin_expire_date(body.get("expireDate", ""))
    note = (body.get("note") or "").strip()
    user_row = conn.execute("SELECT * FROM payment_demo_users WHERE phone = ?", (phone,)).fetchone()
    if not user_row:
        raise ValueError("这个手机号还没注册，无法设置到期时间；可以先在手动加权益里预置次数和天数")
    membership = conn.execute(
        "SELECT * FROM payment_demo_memberships WHERE user_id = ?",
        (user_row["id"],),
    ).fetchone()
    if not membership:
        raise ValueError("这个用户还没有训练权益，先增加权益后再设置到期时间")

    conn.execute(
        """
        UPDATE payment_demo_memberships
        SET expire_at = ?, updated_at = ?
        WHERE user_id = ?
        """,
        (expire_at.isoformat(), now_text(), user_row["id"]),
    )
    conn.execute(
        """
        INSERT INTO admin_entitlement_adjustments
        (id, phone, user_id, credits, days, status, note, created_at)
        VALUES (?, ?, ?, 0, 0, 'expire_at_updated', ?, ?)
        """,
        (
            f"expire-{uuid.uuid4().hex[:12]}",
            phone,
            user_row["id"],
            note or f"到期时间设置为 {expire_at.strftime('%Y-%m-%d 23:59:59')}",
            now_text(),
        ),
    )
    conn.commit()
    return {
        "expireAt": expire_at.isoformat(),
        "users": admin_users(conn),
        "history": admin_entitlement_history(conn),
    }


def delete_admin_user(conn, body):
    phone = normalize_phone(body.get("phone", ""))
    user_row = conn.execute("SELECT * FROM payment_demo_users WHERE phone = ?", (phone,)).fetchone()
    if not user_row:
        pending = conn.execute("SELECT phone FROM admin_pending_entitlements WHERE phone = ?", (phone,)).fetchone()
        if pending:
            conn.execute("DELETE FROM admin_pending_entitlements WHERE phone = ?", (phone,))
            conn.commit()
            return {
                "users": admin_users(conn),
                "pendingEntitlements": admin_pending_entitlements(conn),
                "history": admin_entitlement_history(conn),
            }
        raise ValueError("没有找到这个手机号")

    app_user_id = user_row["app_user_id"] if "app_user_id" in user_row.keys() else None
    payment_user_id = user_row["id"]
    session_ids = []
    if app_user_id:
        session_ids = [
            row["id"]
            for row in conn.execute("SELECT id FROM sessions WHERE user_id = ?", (app_user_id,)).fetchall()
        ]
    for session_id in session_ids:
        conn.execute("DELETE FROM session_cards WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM coaching_attempts WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM ai_jobs WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM training_events WHERE session_id = ?", (session_id,))
    if app_user_id:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (app_user_id,))
        conn.execute("DELETE FROM history_records WHERE user_id = ?", (app_user_id,))
        conn.execute("DELETE FROM membership WHERE user_id = ?", (app_user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (app_user_id,))
    conn.execute("DELETE FROM payment_demo_auth_sessions WHERE user_id = ?", (payment_user_id,))
    conn.execute("DELETE FROM payment_demo_memberships WHERE user_id = ?", (payment_user_id,))
    conn.execute("DELETE FROM payment_demo_orders WHERE phone = ? OR user_id = ?", (phone, payment_user_id))
    conn.execute("DELETE FROM admin_pending_entitlements WHERE phone = ?", (phone,))
    conn.execute("DELETE FROM payment_demo_users WHERE id = ?", (payment_user_id,))
    conn.execute(
        """
        INSERT INTO admin_entitlement_adjustments
        (id, phone, user_id, credits, days, status, note, created_at)
        VALUES (?, ?, NULL, 0, 0, 'user_deleted', '后台删除测试用户，可重新注册', ?)
        """,
        (f"delete-{uuid.uuid4().hex[:12]}", phone, now_text()),
    )
    conn.commit()
    return {
        "users": admin_users(conn),
        "orders": admin_orders(conn),
        "history": admin_entitlement_history(conn),
        "pendingEntitlements": admin_pending_entitlements(conn),
    }


def admin_orders(conn):
    rows = conn.execute(
        """
        SELECT o.*
        FROM payment_demo_orders o
        ORDER BY COALESCE(o.paid_at, o.created_at) DESC
        """
    ).fetchall()
    return [
        {
            "orderNo": row["order_no"],
            "user": row["phone"],
            "planName": row["plan_name"],
            "amount": f"¥{row['amount']:.2f}" if row["amount"] else "¥0.00",
            "status": "已支付" if row["status"] == "paid" else "待支付",
            "paidAt": (row["paid_at"] or row["created_at"] or "-")[:16],
        }
        for row in rows
    ]


def admin_words(conn):
    rows = conn.execute(
        "SELECT id, deck_id, word, status, used_count, position_index FROM words ORDER BY deck_id ASC, position_index ASC"
    ).fetchall()
    removed = deleted_word_values(conn)
    deck_meta = {
        deck["id"]: {
            "title": deck.get("title", deck["id"]),
            "starter": bool(deck.get("starter")),
        }
        for deck in WORD_DECKS
    }
    deck_groups = []
    current_deck_id = None
    current_group = None

    for row in rows:
        if row["deck_id"] != current_deck_id:
            current_deck_id = row["deck_id"]
            current_group = {
                "deckId": row["deck_id"],
                "title": deck_meta.get(row["deck_id"], {}).get("title", row["deck_id"]),
                "starter": deck_meta.get(row["deck_id"], {}).get("starter", False),
                "count": 0,
                "words": [],
            }
            deck_groups.append(current_group)

        current_group["words"].append(
            {
                "word": row["word"],
                "id": row["id"],
                "deckId": row["deck_id"],
                "canDelete": True,
                "status": "已发布" if row["status"] == "published" else "待审核",
                "usedCount": row["used_count"],
            }
        )
        current_group["count"] += 1

    beginner_pools = [
        {
            "deckId": f"beginner-{pool_name}",
            "title": {
                "anchor": "新手主词：抽象对象",
                "tension": "新手冲突：代价情绪",
                "scene": "新手场景：生活处境",
                "metaphor": "新手隐喻：具象物象",
                "mechanism": "新手机制：解释结构",
            }.get(pool_name, pool_name),
            "starter": True,
            "activePool": True,
            "count": len([word for word in words if (f"beginner-{pool_name}", word) not in removed]),
            "words": [
                {
                    "word": word,
                    "id": f"beginner-{pool_name}:{word}",
                    "deckId": f"beginner-{pool_name}",
                    "canDelete": True,
                    "status": "实际抽取池",
                    "usedCount": 0,
                }
                for word in words
                if (f"beginner-{pool_name}", word) not in removed
            ],
        }
        for pool_name, words in BEGINNER_CARD_POOLS.items()
    ]

    return {
        "totalWords": len(rows),
        "deckCount": len(deck_groups),
        "starterWords": sum(group["count"] for group in deck_groups if group["starter"]),
        "starterDeckCount": sum(1 for group in deck_groups if group["starter"]),
        "activeBeginnerWords": sum(group["count"] for group in beginner_pools),
        "activeBeginnerDeckCount": len(beginner_pools),
        "decks": deck_groups,
        "beginnerPools": beginner_pools,
    }


def admin_quotes(conn):
    hidden_quote_rows = conn.execute("SELECT id, quote_text FROM daily_quotes WHERE status = 'hidden'").fetchall()
    for row in hidden_quote_rows:
        conn.execute(
            "INSERT OR IGNORE INTO deleted_daily_quotes (id, quote_text, deleted_at) VALUES (?, ?, ?)",
            (row["id"], row["quote_text"], now_text()),
        )
    conn.execute("DELETE FROM daily_quotes WHERE status = 'hidden' OR id IN (SELECT id FROM deleted_daily_quotes)")
    conn.commit()
    rows = conn.execute(
        """
        SELECT * FROM daily_quotes
        ORDER BY updated_at DESC, id ASC
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "text": row["quote_text"],
            "author": row["author"],
            "theme": row["theme"],
            "sourceLabel": row["source_label"],
            "sourceUrl": row["source_url"],
            "status": row["status"],
            "updatedAt": row["updated_at"],
        }
        for row in rows
    ]


def create_quote(conn, body):
    text = (body.get("text") or "").strip()
    author = (body.get("author") or "").strip()
    theme = (body.get("theme") or "").strip()
    source_label = (body.get("sourceLabel") or "").strip()
    source_url = (body.get("sourceUrl") or "").strip()
    if len(text) < 4:
        raise ValueError("金句内容太短")
    if not author:
        raise ValueError("请填写作者/出处")
    quote_id = f"quote-custom-{int(time.time() * 1000)}"
    conn.execute(
        """
        INSERT INTO daily_quotes
        (id, quote_text, author, theme, source_label, source_url, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'published', ?, ?)
        """,
        (quote_id, text, author, theme, source_label, source_url, now_text(), now_text()),
    )
    conn.commit()
    return admin_quotes(conn)


def update_quote_status(conn, body):
    quote_id = (body.get("id") or "").strip()
    status = (body.get("status") or "").strip()
    if status not in {"published", "hidden"}:
        raise ValueError("状态不合法")
    if status == "hidden":
        row = conn.execute("SELECT quote_text FROM daily_quotes WHERE id = ?", (quote_id,)).fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO deleted_daily_quotes (id, quote_text, deleted_at) VALUES (?, ?, ?)",
            (quote_id, row["quote_text"] if row else "", now_text()),
        )
        conn.execute("DELETE FROM daily_quotes WHERE id = ?", (quote_id,))
        conn.commit()
        return admin_quotes(conn)
    conn.execute(
        "UPDATE daily_quotes SET status = ?, updated_at = ? WHERE id = ?",
        (status, now_text(), quote_id),
    )
    conn.commit()
    return admin_quotes(conn)


def delete_quote(conn, body):
    quote_id = (body.get("id") or "").strip()
    row = conn.execute("SELECT quote_text FROM daily_quotes WHERE id = ?", (quote_id,)).fetchone()
    conn.execute(
        "INSERT OR IGNORE INTO deleted_daily_quotes (id, quote_text, deleted_at) VALUES (?, ?, ?)",
        (quote_id, row["quote_text"] if row else "", now_text()),
    )
    conn.execute("DELETE FROM daily_quotes WHERE id = ?", (quote_id,))
    conn.commit()
    return admin_quotes(conn)


def delete_admin_word(conn, body):
    deck_id = (body.get("deckId") or "").strip()
    word_id = (body.get("id") or "").strip()
    word = (body.get("word") or "").strip()
    if not word:
        raise ValueError("缺少要删除的词语")
    if not deck_id and word_id.startswith("beginner-") and ":" in word_id:
        deck_id = word_id.split(":", 1)[0]
    if not deck_id:
        row = conn.execute("SELECT deck_id, word FROM words WHERE id = ?", (word_id,)).fetchone()
        if row:
            deck_id = row["deck_id"]
            word = row["word"]
    if not deck_id:
        raise ValueError("缺少词库信息")
    conn.execute(
        "INSERT OR IGNORE INTO deleted_words (id, deck_id, word, deleted_at) VALUES (?, ?, ?, ?)",
        (word_id or f"{deck_id}:{word}", deck_id, word, now_text()),
    )
    conn.execute("DELETE FROM words WHERE id = ? OR (deck_id = ? AND word = ?)", (word_id, deck_id, word))
    conn.commit()
    return admin_words(conn)


def delete_admin_order(conn, body):
    order_no = (body.get("orderNo") or "").strip()
    if not order_no:
        raise ValueError("缺少订单号")
    conn.execute("DELETE FROM payment_demo_orders WHERE order_no = ?", (order_no,))
    conn.execute(
        "UPDATE payment_demo_memberships SET current_order_no = '' WHERE current_order_no = ?",
        (order_no,),
    )
    conn.commit()
    return admin_orders(conn)


def delete_admin_training_history(conn, body):
    record_id = (body.get("id") or "").strip()
    session_id = (body.get("sessionId") or record_id).strip()
    if not record_id:
        raise ValueError("缺少训练记录 ID")
    conn.execute("DELETE FROM history_records WHERE id = ?", (record_id,))
    if session_id:
        conn.execute("DELETE FROM coaching_attempts WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM ai_jobs WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM training_events WHERE session_id = ?", (session_id,))
    conn.commit()
    return admin_training_history(conn)


def admin_training_history(conn):
    rows = conn.execute(
        """
        SELECT h.*, u.nickname
        FROM history_records h
        LEFT JOIN users u ON u.id = h.user_id
        ORDER BY h.created_at DESC
        LIMIT 50
        """
    ).fetchall()
    records = []
    for row in rows:
        model_jobs = conn.execute(
            """
            SELECT * FROM ai_jobs
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (row["session_id"] or row["id"],),
        ).fetchall()
        attempts = json_loads(row["attempts_json"], [])
        final_feedback = json_loads(row["final_feedback_json"], {})
        records.append(
            {
            "id": row["id"],
            "sessionId": row["session_id"],
            "user": row["nickname"] or "游客用户",
            "title": row["title"],
            "score": row["score"],
            "pair": json_loads(row["pair_json"], []),
            "excerpt": row["excerpt"],
            "transcriptText": row["transcript_text"],
            "timeLabel": row["time_label"],
            "attemptCount": len(attempts) if attempts else 1,
            "summary": row["summary"],
            "details": json_loads(row["details_json"], []),
            "suggestions": json_loads(row["suggestions_json"], []),
            "attempts": attempts,
            "finalFeedback": final_feedback,
            "modelOutputs": [
                {
                    "jobId": job["id"],
                    "promptKey": job["prompt_key"],
                    "versionNo": job["version_no"],
                    "providerCode": job["provider_code"],
                    "modelName": job["model_name"],
                    "status": job["status"],
                    "selectedWords": json_loads(job["selected_words_json"], []),
                    "transcriptText": job["transcript_text"],
                    "requestJson": json_loads(job["request_json"], {}),
                    "responseJson": json_loads(job["response_json"], {}),
                    "createdAt": job["created_at"],
                    "updatedAt": job["updated_at"],
                }
                for job in model_jobs
            ],
        })
    return records


def admin_prompts(conn):
    rows = conn.execute("SELECT * FROM ai_prompts ORDER BY updated_at DESC").fetchall()
    return [
        {
            "promptKey": row["prompt_key"],
            "promptName": row["prompt_name"],
            "versionNo": row["version_no"],
            "modelName": row["model_name"],
            "providerCode": row["provider_code"],
            "status": row["status"],
            "updatedAt": row["updated_at"],
            "systemPrompt": row["system_prompt"],
            "userPromptTemplate": row["user_prompt_template"],
        }
        for row in rows
    ]


def admin_prompt_versions(conn, prompt_key="card_association_feedback"):
    rows = conn.execute(
        """
        SELECT * FROM ai_prompt_versions
        WHERE prompt_key = ?
        ORDER BY version_no DESC
        """,
        (prompt_key,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "promptKey": row["prompt_key"],
            "promptName": row["prompt_name"],
            "versionNo": row["version_no"],
            "modelName": row["model_name"],
            "providerCode": row["provider_code"],
            "status": row["status"],
            "changeNote": row["change_note"],
            "createdAt": row["created_at"],
            "systemPrompt": row["system_prompt"],
            "userPromptTemplate": row["user_prompt_template"],
        }
        for row in rows
    ]


def insert_prompt_version(conn, prompt_row, status="published", change_note=""):
    conn.execute(
        """
        INSERT OR REPLACE INTO ai_prompt_versions
        (id, prompt_key, prompt_name, version_no, system_prompt, user_prompt_template, model_name, provider_code, status, change_note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"{prompt_row['prompt_key']}-v{prompt_row['version_no']}",
            prompt_row["prompt_key"],
            prompt_row["prompt_name"],
            prompt_row["version_no"],
            prompt_row["system_prompt"],
            prompt_row["user_prompt_template"],
            prompt_row["model_name"],
            prompt_row["provider_code"],
            status,
            change_note,
            now_text(),
        ),
    )


def admin_runtime_config():
    runtime_config = load_runtime_config()
    return {
        "modelApiUrl": runtime_config["model_api_url"],
        "modelApiKey": runtime_config["model_api_key"],
        "modelApiModel": runtime_config["model_api_model"],
        "modelProviderCode": runtime_config["model_provider_code"],
        "requireRealAi": runtime_config["require_real_ai"],
    }

def model_row_to_dict(row):
    return {
        "id": row["id"],
        "modelName": row["model_name"],
        "displayName": row["display_name"],
        "providerCode": row["provider_code"],
        "apiKeyConfigured": bool(row["api_key"]),
        "status": row["status"],
        "versionNote": row["version_note"],
        "lastTestStatus": row["last_test_status"],
        "lastTestMessage": row["last_test_message"],
        "lastTestAt": row["last_test_at"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def admin_models(conn):
    rows = conn.execute("SELECT * FROM ai_models ORDER BY updated_at DESC, created_at DESC").fetchall()
    return [model_row_to_dict(row) for row in rows]


def upsert_admin_model(conn, body):
    model_id = (body.get("id") or "").strip()
    model_name = (body.get("modelName") or "").strip()
    display_name = (body.get("displayName") or model_name).strip()
    api_key = (body.get("apiKey") or "").strip()
    status = (body.get("status") or "active").strip()
    version_note = (body.get("versionNote") or "").strip()
    if not model_name:
        raise ValueError("请填写模型名称")
    if status not in {"active", "inactive", "deprecated", "testing"}:
        raise ValueError("模型状态不合法")
    if model_id:
        row = conn.execute("SELECT * FROM ai_models WHERE id = ?", (model_id,)).fetchone()
        if not row:
            raise ValueError("模型不存在")
        next_key = api_key or row["api_key"]
        conn.execute(
            """
            UPDATE ai_models
            SET model_name = ?, display_name = ?, api_key = ?, status = ?, version_note = ?, updated_at = ?
            WHERE id = ?
            """,
            (model_name, display_name, next_key, status, version_note, now_text(), model_id),
        )
    else:
        model_id = f"model-{uuid.uuid4().hex[:10]}"
        conn.execute(
            """
            INSERT INTO ai_models
            (id, model_name, display_name, provider_code, api_key, status, version_note, created_at, updated_at)
            VALUES (?, ?, ?, 'yunwu', ?, ?, ?, ?, ?)
            """,
            (model_id, model_name, display_name, api_key, status, version_note, now_text(), now_text()),
        )
    conn.commit()
    return admin_models(conn)


def set_active_admin_model(conn, body):
    model_id = (body.get("id") or "").strip()
    row = conn.execute("SELECT * FROM ai_models WHERE id = ?", (model_id,)).fetchone()
    if not row:
        raise ValueError("模型不存在")
    if not row["api_key"]:
        raise ValueError("这个模型还没有 API Key，不能设为运行模型")
    runtime_config = load_runtime_config()
    updates = [
        ("runtime.model_api_url", runtime_config["model_api_url"], now_text()),
        ("runtime.model_api_key", row["api_key"], now_text()),
        ("runtime.model_api_model", row["model_name"], now_text()),
        ("runtime.model_provider_code", "yunwu", now_text()),
        ("runtime.require_real_ai", "true", now_text()),
    ]
    conn.executemany(
        """
        INSERT INTO app_config (config_key, config_value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(config_key) DO UPDATE SET config_value = excluded.config_value, updated_at = excluded.updated_at
        """,
        updates,
    )
    conn.execute(
        "UPDATE ai_prompts SET model_name = ?, provider_code = 'yunwu', updated_at = ? WHERE prompt_key = 'card_association_feedback'",
        (row["model_name"], now_text()),
    )
    conn.commit()
    return {"models": admin_models(conn), "runtime": admin_runtime_config()}


def validate_feedback_contract(raw_feedback, selected_cards=None, user_text="", attempt_no=1, previous_attempts=None):
    errors = []
    warnings = []
    selected_cards = selected_cards or [{"word": "自由"}, {"word": "代价"}]
    previous_attempts = previous_attempts or []
    if not isinstance(raw_feedback, dict):
        return {"ok": False, "errors": ["模型内容不是 JSON 对象"], "warnings": [], "normalizedFeedback": None}
    if "totalScore" not in raw_feedback and "total_score" in raw_feedback:
        raw_feedback = {**raw_feedback, "totalScore": raw_feedback.get("total_score")}
    if not isinstance(raw_feedback.get("totalScore"), (int, float)):
        errors.append("缺少 totalScore，或 totalScore 不是数字")
    details = raw_feedback.get("details")
    if not isinstance(details, list):
        errors.append("details 必须是数组")
    elif len(details) != 6:
        errors.append(f"details 需要 6 个维度，当前是 {len(details)} 个")
    else:
        for index, item in enumerate(details, start=1):
            if not isinstance(item, dict):
                errors.append(f"details 第 {index} 项不是对象")
                continue
            if item.get("score") is None:
                errors.append(f"details 第 {index} 项缺少 score")
            if not (item.get("label") or item.get("name")):
                warnings.append(f"details 第 {index} 项缺少 label/name")
    for key in ["summary", "improvement"]:
        if not str(raw_feedback.get(key) or "").strip():
            warnings.append(f"{key} 为空，C 端可展示但体验会弱")
    try:
        normalized = shape_feedback_payload(selected_cards, user_text, int(attempt_no or 1), previous_attempts, raw_feedback)
    except Exception as exc:
        errors.append(f"线上解析器归一化失败：{exc}")
        normalized = None
    return {"ok": not errors, "errors": errors, "warnings": warnings, "normalizedFeedback": normalized}


def test_admin_model_connection(conn, body):
    model_id = (body.get("id") or "").strip()
    row = conn.execute("SELECT * FROM ai_models WHERE id = ?", (model_id,)).fetchone()
    if not row:
        raise ValueError("模型不存在")
    prompt = {
        "system_prompt": "你只需要返回一个 JSON 对象。",
        "user_prompt_template": "请返回 {\"ok\": true, \"model\": \"{{selected_words}}\"}",
        "model_name": row["model_name"],
        "provider_code": "yunwu",
    }
    started = time.time()
    result = call_model_api(
        [{"word": "connection"}, {"word": "test"}],
        "连接测试",
        prompt,
        model_override={"model_name": row["model_name"], "api_key": row["api_key"], "provider_code": "yunwu"},
    )
    elapsed_ms = int((time.time() - started) * 1000)
    ok = bool(result and result.get("raw_response"))
    message = f"连接成功，耗时 {elapsed_ms}ms" if ok else "连接失败：没有拿到可解析响应"
    conn.execute(
        "UPDATE ai_models SET last_test_status = ?, last_test_message = ?, last_test_at = ?, updated_at = ? WHERE id = ?",
        ("success" if ok else "failed", message, now_text(), now_text(), model_id),
    )
    conn.commit()
    return {"ok": ok, "message": message, "elapsedMs": elapsed_ms, "rawResponse": result.get("raw_response") if result else None, "models": admin_models(conn)}


def test_admin_model_schema(conn, body):
    model_id = (body.get("id") or "").strip()
    row = conn.execute("SELECT * FROM ai_models WHERE id = ?", (model_id,)).fetchone()
    if not row:
        raise ValueError("模型不存在")
    prompt = conn.execute("SELECT * FROM ai_prompts WHERE prompt_key = 'card_association_feedback'").fetchone()
    if not prompt:
        raise ValueError("Prompt 不存在")
    selected_words = body.get("selectedWords") or ["自由", "代价"]
    if len(selected_words) < 2:
        raise ValueError("至少需要两个词")
    user_text = (body.get("userText") or "我觉得自由不是想做什么就做什么，它更像是愿意承担选择后果的能力。").strip()
    attempt_no = int(body.get("attemptNo") or 1)
    selected_cards = [{"word": selected_words[0]}, {"word": selected_words[1]}]
    result = call_model_api(
        selected_cards,
        user_text,
        prompt,
        attempt_no=attempt_no,
        previous_attempts_context="[]",
        model_override={"model_name": row["model_name"], "api_key": row["api_key"], "provider_code": "yunwu"},
    )
    if not result or not result.get("feedback"):
        raise ValueError("模型没有返回可解析 JSON，先看原始接口或 Prompt 输出格式")
    contract = validate_feedback_contract(result["feedback"], selected_cards, user_text, attempt_no, [])
    return {
        "ok": contract["ok"],
        "modelName": row["model_name"],
        "providerCode": "yunwu",
        "errors": contract["errors"],
        "warnings": contract["warnings"],
        "feedback": result["feedback"],
        "normalizedFeedback": contract["normalizedFeedback"],
        "rawResponse": result["raw_response"],
    }


def update_runtime_config(conn, body):
    model_api_url = (body.get("modelApiUrl") or "").strip()
    model_api_key = (body.get("modelApiKey") or "").strip()
    model_api_model = (body.get("modelApiModel") or "").strip() or "gpt-4o"
    model_provider_code = (body.get("modelProviderCode") or "").strip() or "yunwu"
    require_real_ai = bool(body.get("requireRealAi"))

    if require_real_ai and (not model_api_url or not model_api_key):
        raise ValueError("开启真实 AI 前，请先填写模型地址和 API Key")

    updates = [
        ("runtime.model_api_url", model_api_url, now_text()),
        ("runtime.model_api_key", model_api_key, now_text()),
        ("runtime.model_api_model", model_api_model, now_text()),
        ("runtime.model_provider_code", model_provider_code, now_text()),
        ("runtime.require_real_ai", "true" if require_real_ai else "false", now_text()),
    ]
    conn.executemany(
        """
        INSERT INTO app_config (config_key, config_value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(config_key) DO UPDATE SET
          config_value = excluded.config_value,
          updated_at = excluded.updated_at
        """,
        updates,
    )
    conn.execute(
        """
        UPDATE ai_prompts
        SET model_name = ?, provider_code = ?, updated_at = ?
        WHERE prompt_key = 'card_association_feedback'
        """,
        (model_api_model, model_provider_code, now_text()),
    )
    conn.commit()
    return admin_runtime_config()


def update_prompt(conn, prompt_key, system_prompt, user_prompt_template, model_name=None, provider_code=None, change_note=""):
    prompt_key = (prompt_key or "").strip()
    if not prompt_key:
        raise ValueError("缺少 promptKey")
    if not (system_prompt or "").strip():
        raise ValueError("System Prompt 不能为空")
    if not (user_prompt_template or "").strip():
        raise ValueError("User Prompt 不能为空")

    row = conn.execute("SELECT * FROM ai_prompts WHERE prompt_key = ?", (prompt_key,)).fetchone()
    if not row:
        raise ValueError("Prompt 不存在")

    next_version = int(row["version_no"]) + 1
    conn.execute(
        """
        UPDATE ai_prompts
        SET
          version_no = ?,
          system_prompt = ?,
          user_prompt_template = ?,
          model_name = ?,
          provider_code = ?,
          updated_at = ?
        WHERE prompt_key = ?
        """,
        (
            next_version,
            system_prompt.strip(),
            user_prompt_template.strip(),
            (model_name or row["model_name"]).strip(),
            (provider_code or row["provider_code"]).strip(),
            now_text(),
            prompt_key,
        ),
    )
    updated = conn.execute("SELECT * FROM ai_prompts WHERE prompt_key = ?", (prompt_key,)).fetchone()
    insert_prompt_version(conn, updated, "published", (change_note or "后台保存的新版本").strip())
    conn.commit()
    return admin_prompts(conn)


def rollback_prompt(conn, prompt_key, version_no):
    prompt_key = (prompt_key or "").strip()
    if not prompt_key:
        raise ValueError("缺少 promptKey")
    source = conn.execute(
        "SELECT * FROM ai_prompt_versions WHERE prompt_key = ? AND version_no = ?",
        (prompt_key, int(version_no)),
    ).fetchone()
    current = conn.execute("SELECT * FROM ai_prompts WHERE prompt_key = ?", (prompt_key,)).fetchone()
    if not source or not current:
        raise ValueError("要回退的版本不存在")

    next_version = int(current["version_no"]) + 1
    conn.execute(
        """
        UPDATE ai_prompts
        SET
          version_no = ?,
          system_prompt = ?,
          user_prompt_template = ?,
          model_name = ?,
          provider_code = ?,
          status = 'published',
          updated_at = ?
        WHERE prompt_key = ?
        """,
        (
            next_version,
            source["system_prompt"],
            source["user_prompt_template"],
            source["model_name"],
            source["provider_code"],
            now_text(),
            prompt_key,
        ),
    )
    updated = conn.execute("SELECT * FROM ai_prompts WHERE prompt_key = ?", (prompt_key,)).fetchone()
    insert_prompt_version(conn, updated, "published", f"从 v{int(version_no)} 回退生成")
    conn.commit()
    return {"prompts": admin_prompts(conn), "versions": admin_prompt_versions(conn, prompt_key)}


def admin_test_prompt(conn, body):
    prompt_key = (body.get("promptKey") or "card_association_feedback").strip()
    prompt = conn.execute("SELECT * FROM ai_prompts WHERE prompt_key = ?", (prompt_key,)).fetchone()
    if not prompt:
        raise ValueError("Prompt 不存在")

    selected_words = body.get("selectedWords") or ["自由", "束缚"]
    if len(selected_words) < 2:
        raise ValueError("至少需要两个词")
    user_text = (body.get("userText") or "").strip()
    if not user_text:
        raise ValueError("请先输入测试文本")
    test_context = {
        "attemptNo": body.get("attemptNo") or 1,
        "previousContext": body.get("previousContext") or "",
        "testGoal": body.get("testGoal") or "",
        "expectedFocus": body.get("expectedFocus") or "",
    }

    prompt_row = {
        "system_prompt": body.get("systemPrompt", prompt["system_prompt"]),
        "user_prompt_template": body.get("userPromptTemplate", prompt["user_prompt_template"]),
        "model_name": body.get("modelName", prompt["model_name"]),
        "provider_code": body.get("providerCode", prompt["provider_code"]),
        "prompt_key": prompt["prompt_key"],
        "version_no": prompt["version_no"],
    }

    previous_context = sanitize_freeform_previous_context(test_context["previousContext"])
    if test_context["testGoal"] or test_context["expectedFocus"]:
        previous_context = (
            f"{previous_context}\n"
            f"【本次测试重点】{test_context['testGoal'] or '无'}\n"
            f"【期望观察】{test_context['expectedFocus'] or '无'}"
        ).strip()

    model_result = call_model_api(
        [{"word": selected_words[0]}, {"word": selected_words[1]}],
        user_text,
        prompt_row,
        attempt_no=int(test_context["attemptNo"] or 1),
        previous_attempts_context=previous_context,
    )
    if not model_result or not model_result.get("feedback"):
        raise ValueError("真实 AI 试跑失败，请检查模型接口、Key 或 Prompt 输出格式")

    test_id = f"TEST{int(time.time() * 1000)}"
    conn.execute(
        """
        INSERT INTO ai_prompt_tests (id, prompt_key, version_no, provider_code, model_name, input_json, output_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            test_id,
            prompt_row["prompt_key"],
            prompt_row["version_no"],
            model_result["provider_code"],
            model_result["model_name"],
            json_dumps({**body, "testContext": test_context}),
            json_dumps(model_result["raw_response"]),
            now_text(),
        ),
    )
    conn.commit()
    return {
        "testId": test_id,
        "providerCode": model_result["provider_code"],
        "modelName": model_result["model_name"],
        "input": {**body, "testContext": test_context},
        "modelInput": {
            "selectedWords": selected_words,
            "attemptNo": int(test_context["attemptNo"] or 1),
            "previousAttempts": previous_context or "[]",
            "userText": user_text,
        },
        "feedback": model_result["feedback"],
        "rawResponse": model_result["raw_response"],
    }


def parse_eval_samples(raw_text):
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("请先粘贴评测样本")

    def split_words(value):
        return [part.strip() for part in re.split(r"[/,，+＋、\s]+", value or "") if part.strip()]

    def normalize_row(index, row):
        sample_id = row.get("sample_id") or row.get("sampleId") or row.get("编号") or row.get("样本编号") or f"S{index:03d}"
        words = row.get("selected_words") or row.get("selectedWords") or row.get("词组") or row.get("词语") or ""
        if not words:
            first = row.get("word_a") or row.get("A") or row.get("词语A") or row.get("词1") or ""
            second = row.get("word_b") or row.get("B") or row.get("词语B") or row.get("词2") or ""
            words = [first, second]
        if isinstance(words, str):
            words = split_words(words)
        user_text = (
            row.get("user_text")
            or row.get("userText")
            or row.get("表达文本")
            or row.get("用户表达")
            or row.get("转写文本")
            or row.get("文本")
            or ""
        )
        return {
            "sampleId": str(sample_id).strip() or f"S{index:03d}",
            "selectedWords": [str(item).strip() for item in words if str(item).strip()][:2],
            "attemptNo": int(row.get("attempt_no") or row.get("attemptNo") or row.get("轮次") or 1),
            "userText": str(user_text).strip(),
        }

    lines = [line for line in text.splitlines() if line.strip()]
    if lines and "\t" in lines[0]:
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")
        return [normalize_row(index, row) for index, row in enumerate(reader, start=1)]
    if lines and re.search(r"\s{2,}", lines[0]):
        headers = re.split(r"\s{2,}", lines[0].strip())
        rows = []
        for index, line in enumerate(lines[1:], start=1):
            cells = re.split(r"\s{2,}", line.strip(), maxsplit=len(headers) - 1)
            if len(cells) < len(headers):
                continue
            rows.append(normalize_row(index, dict(zip(headers, cells))))
        if rows:
            return rows

    try:
        parsed = json.loads(text)
        samples = parsed.get("samples", parsed) if isinstance(parsed, dict) else parsed
        if not isinstance(samples, list):
            raise ValueError
        normalized = []
        for index, item in enumerate(samples, start=1):
            normalized.append(normalize_row(index, item))
        return normalized
    except Exception:
        samples = []
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames:
            for index, row in enumerate(reader, start=1):
                samples.append(normalize_row(index, row))
            return samples
        raise ValueError("样本格式不对。请从表格复制列：样本编号、词语A、词语B、轮次、用户表达")


def dimension_scores(details):
    result = {}
    for item in details or []:
        label = item.get("label") or ""
        if label:
            result[label] = item.get("score")
    return result


def feedback_from_raw_response(raw_response):
    raw = raw_response or {}
    try:
        content = raw["choices"][0]["message"]["content"]
        content = content.strip()
        if content.startswith("```"):
            lines = [line for line in content.splitlines() if not line.strip().startswith("```")]
            content = "\n".join(lines).strip()
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def improvement_from_feedback(feedback):
    feedback = feedback or {}
    direct = (
        feedback.get("improvement")
        or feedback.get("nextTask")
        or feedback.get("next_task")
        or feedback.get("mainIssue")
        or feedback.get("main_issue")
    )
    if direct:
        return cleanup_feedback_text(direct)
    suggestions = feedback.get("suggestions") or []
    if isinstance(suggestions, list) and suggestions:
        return cleanup_feedback_text("；".join(str(item) for item in suggestions if str(item).strip()))
    details = feedback.get("details") or feedback.get("visibleDetails") or []
    if details:
        lowest = min(details, key=lambda item: float(item.get("score") or 999))
        label = lowest.get("label") or lowest.get("name") or "当前短板"
        note = lowest.get("note") or lowest.get("reason") or lowest.get("comment") or ""
        return cleanup_feedback_text(f"优先改进「{label}」：{note}")
    return ""


def admin_eval_batches(conn):
    rows = conn.execute(
        """
        SELECT * FROM prompt_eval_batches
        ORDER BY created_at DESC
        LIMIT 20
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "promptKey": row["prompt_key"],
            "versionNo": row["version_no"],
            "modelName": row["model_name"],
            "providerCode": row["provider_code"],
            "sampleCount": row["sample_count"],
            "successCount": row["success_count"],
            "errorCount": row["error_count"],
            "processedCount": int(row["success_count"] or 0) + int(row["error_count"] or 0),
            "status": row["status"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
        for row in rows
    ]


def admin_eval_batch_results(conn, batch_id):
    rows = conn.execute(
        """
        SELECT * FROM prompt_eval_results
        WHERE batch_id = ?
        ORDER BY sample_id ASC, created_at ASC
        """,
        (batch_id,),
    ).fetchall()
    results = []
    for row in rows:
        raw_response = json_loads(row["raw_response_json"], {})
        raw_feedback = feedback_from_raw_response(raw_response)
        stored_details = json_loads(row["details_json"], [])
        feedback_for_improvement = {
            **raw_feedback,
            "details": raw_feedback.get("details") or stored_details,
            "nextTask": row["next_task"],
        }
        results.append(
            {
            "id": row["id"],
            "batchId": row["batch_id"],
            "sampleId": row["sample_id"],
            "selectedWords": json_loads(row["selected_words_json"], []),
            "attemptNo": row["attempt_no"],
            "userText": row["user_text"],
            "promptVersion": row["prompt_version"],
            "providerCode": row["provider_code"],
            "modelName": row["model_name"],
            "totalScore": row["total_score"],
            "dimensionScores": json_loads(row["dimension_scores_json"], {}),
            "summary": row["summary"],
            "details": stored_details,
            "nextTask": row["next_task"],
            "improvement": improvement_from_feedback(feedback_for_improvement),
            "suggestions": raw_feedback.get("suggestions", []),
            "rewrite": row["rewrite"],
            "rawResponse": raw_response,
            "error": row["error"],
            "createdAt": row["created_at"],
        })
    return results


def insert_prompt_eval_result(conn, batch_id, sample, prompt, feedback=None, raw_response=None, error=""):
    feedback = feedback or {}
    raw_response = raw_response or {}
    details = feedback.get("details") or feedback.get("visibleDetails") or []
    improvement = improvement_from_feedback(feedback)
    conn.execute(
        """
        INSERT INTO prompt_eval_results
        (id, batch_id, sample_id, selected_words_json, attempt_no, user_text, prompt_version, provider_code, model_name, total_score, dimension_scores_json, summary, details_json, next_task, rewrite, raw_response_json, error, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"eval-result-{uuid.uuid4().hex[:10]}",
            batch_id,
            sample["sampleId"],
            json_dumps(sample["selectedWords"]),
            int(sample["attemptNo"] or 1),
            sample["userText"],
            int(prompt["version_no"]),
            feedback.get("providerCode") or prompt["provider_code"],
            feedback.get("modelName") or prompt["model_name"],
            feedback.get("totalScore") if feedback else None,
            json_dumps(dimension_scores(details)),
            feedback.get("summary", ""),
            json_dumps(details),
            feedback.get("nextTask") or feedback.get("next_task") or improvement,
            feedback.get("rewrite", ""),
            json_dumps(raw_response),
            error,
            now_text(),
        ),
    )


def run_prompt_eval_batch_worker(batch_id, prompt_key, samples, model_id=""):
    conn = db()
    try:
        prompt = conn.execute("SELECT * FROM ai_prompts WHERE prompt_key = ?", (prompt_key,)).fetchone()
        if not prompt:
            raise ValueError("Prompt 不存在")
        model_override = None
        if model_id:
            model_row = conn.execute("SELECT * FROM ai_models WHERE id = ?", (model_id,)).fetchone()
            if model_row:
                model_override = {
                    "model_name": model_row["model_name"],
                    "api_key": model_row["api_key"],
                    "provider_code": "yunwu",
                }

        success_count = 0
        error_count = 0
        for sample in samples:
            words = sample["selectedWords"]
            error = ""
            feedback = {}
            raw_response = {}
            if len(words) < 2 or not sample["userText"]:
                error = "样本缺少两个词语或用户表达"
                error_count += 1
            else:
                try:
                    model_result = call_model_api(
                        [{"word": words[0]}, {"word": words[1]}],
                        sample["userText"],
                        prompt,
                        attempt_no=int(sample["attemptNo"] or 1),
                        previous_attempts_context="[]",
                        model_override=model_override,
                    )
                    if not model_result or not model_result.get("feedback"):
                        raise ValueError("模型没有返回可解析 feedback")
                    feedback = {
                        **model_result["feedback"],
                        "modelName": model_result["model_name"],
                        "providerCode": model_result["provider_code"],
                    }
                    raw_response = model_result["raw_response"]
                    success_count += 1
                except Exception as exc:
                    error = str(exc)
                    error_count += 1

            insert_prompt_eval_result(conn, batch_id, sample, prompt, feedback, raw_response, error)
            conn.execute(
                """
                UPDATE prompt_eval_batches
                SET success_count = ?, error_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (success_count, error_count, now_text(), batch_id),
            )
            conn.commit()

        conn.execute(
            """
            UPDATE prompt_eval_batches
            SET success_count = ?, error_count = ?, status = 'completed', updated_at = ?
            WHERE id = ?
            """,
            (success_count, error_count, now_text(), batch_id),
        )
        conn.commit()
    except Exception as exc:
        conn.execute(
            """
            UPDATE prompt_eval_batches
            SET status = 'failed', updated_at = ?
            WHERE id = ?
            """,
            (now_text(), batch_id),
        )
        conn.commit()
        print(f"prompt eval batch {batch_id} failed: {exc}")
        traceback.print_exc()
    finally:
        conn.close()


def run_prompt_eval_batch(conn, body):
    prompt_key = (body.get("promptKey") or "card_association_feedback").strip()
    prompt = conn.execute("SELECT * FROM ai_prompts WHERE prompt_key = ?", (prompt_key,)).fetchone()
    if not prompt:
        raise ValueError("Prompt 不存在")
    samples = parse_eval_samples(body.get("samplesText") or "")
    max_count = min(max(1, int(body.get("maxCount") or 50)), 50)
    samples = samples[:max_count]
    if not samples:
        raise ValueError("没有可评测的样本")
    model_id = (body.get("modelId") or "").strip()
    model_row = conn.execute("SELECT * FROM ai_models WHERE id = ?", (model_id,)).fetchone() if model_id else None
    batch_model_name = model_row["model_name"] if model_row else prompt["model_name"]
    batch_provider_code = "yunwu" if model_row else prompt["provider_code"]

    batch_id = f"EVAL{int(time.time() * 1000)}"
    batch_name = (body.get("name") or f"Prompt v{prompt['version_no']} 批量评测").strip()
    conn.execute(
        """
        INSERT INTO prompt_eval_batches
        (id, name, prompt_key, version_no, model_name, provider_code, sample_count, success_count, error_count, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 'running', ?, ?)
        """,
        (
            batch_id,
            batch_name,
            prompt["prompt_key"],
            prompt["version_no"],
            batch_model_name,
            batch_provider_code,
            len(samples),
            now_text(),
            now_text(),
        ),
    )
    conn.commit()

    thread = threading.Thread(
        target=run_prompt_eval_batch_worker,
        args=(batch_id, prompt_key, samples, model_id),
        daemon=True,
    )
    thread.start()
    return {
        "batch": next(item for item in admin_eval_batches(conn) if item["id"] == batch_id),
        "results": [],
    }


def admin_jobs(conn):
    rows = conn.execute("SELECT * FROM ai_jobs ORDER BY created_at DESC LIMIT 20").fetchall()
    return [
        {
            "jobId": row["id"],
            "sessionId": row["session_id"],
            "promptKey": row["prompt_key"],
            "versionNo": row["version_no"],
            "providerCode": row["provider_code"],
            "modelName": row["model_name"],
            "status": row["status"],
            "selectedWords": json_loads(row["selected_words_json"], []),
            "transcriptText": row["transcript_text"],
            "requestJson": json_loads(row["request_json"], {}),
            "responseJson": json_loads(row["response_json"], {}),
            "createdAt": row["created_at"][:16],
            "updatedAt": row["updated_at"][:16],
        }
        for row in rows
    ]


def admin_redeem_codes(conn):
    rows = conn.execute("SELECT * FROM redeem_codes ORDER BY status ASC, code ASC").fetchall()
    return [
        {
            "code": row["code"],
            "planName": row["plan_name"],
            "status": row["status"],
            "usedBy": row["used_by"] or "-",
            "usedAt": row["used_at"] or "-",
        }
        for row in rows
    ]


def generate_redeem_codes(conn, quantity, plan_name, prefix="SPEAKOUT"):
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        raise ValueError("生成数量必须是数字")

    if quantity <= 0 or quantity > 100:
        raise ValueError("单次最多生成 100 个兑换码")

    plan_name = (plan_name or "").strip() or "高手会员"
    prefix = "".join(ch for ch in (prefix or "SPEAKOUT").upper() if ch.isalnum())[:12] or "SPEAKOUT"

    created = []
    for _ in range(quantity):
        while True:
            suffix = uuid.uuid4().hex[:8].upper()
            code = f"{prefix}-{suffix}"
            exists = conn.execute("SELECT 1 FROM redeem_codes WHERE code = ?", (code,)).fetchone()
            if not exists:
                break
        conn.execute(
            "INSERT INTO redeem_codes (code, plan_name, status, used_by, used_at) VALUES (?, ?, 'active', NULL, NULL)",
            (code, plan_name),
        )
        created.append(
            {
                "code": code,
                "planName": plan_name,
                "status": "active",
                "usedBy": "-",
                "usedAt": "-",
            }
        )

    conn.commit()
    return {
        "createdCount": len(created),
        "codes": created,
    }


def update_redeem_code_status(conn, code, status):
    code = (code or "").strip().upper()
    status = (status or "").strip().lower()
    if not code:
        raise ValueError("请先选择兑换码")
    if status not in ("active", "inactive"):
        raise ValueError("状态只支持 active 或 inactive")

    row = conn.execute("SELECT * FROM redeem_codes WHERE code = ?", (code,)).fetchone()
    if not row:
        raise ValueError("兑换码不存在")
    if row["status"] == "used":
        raise ValueError("已使用的兑换码不能再改状态")

    conn.execute(
        "UPDATE redeem_codes SET status = ? WHERE code = ?",
        (status, code),
    )
    conn.commit()
    return {
        "code": code,
        "status": status,
    }


class AppHandler(BaseHTTPRequestHandler):
    server_version = "ExpressMasterHTTP/0.1"

    def send_file(self, file_path: Path, content_type: str):
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if not os.getenv("RAILWAY_ENVIRONMENT"):
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_frontend_asset(self, request_path):
        relative_path = request_path.lstrip("/")
        file_path = (FRONTEND_DIR / relative_path).resolve()
        assets_root = (FRONTEND_DIR / "assets").resolve()
        if not str(file_path).startswith(str(assets_root)) or not file_path.is_file():
            self.fail("资源不存在", 404)
            return
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_file(file_path, content_type)

    def send_admin_file(self, request_path):
        relative_path = request_path.removeprefix(f"{ADMIN_ROUTE_PREFIX}/") or "index.html"
        file_path = (ADMIN_FRONTEND_DIR / relative_path).resolve()
        admin_root = ADMIN_FRONTEND_DIR.resolve()
        if not str(file_path).startswith(str(admin_root)) or not file_path.is_file():
            self.fail("资源不存在", 404)
            return
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_file(file_path, content_type)

    def _send(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Client-Id, X-Auth-Token, X-Payment-Demo-Token")
        self.end_headers()
        self.wfile.write(body)

    def ok(self, data):
        self._send(200, {"code": 0, "message": "success", "data": data})

    def text_ok(self, body_text):
        body = body_text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def csv_ok(self, filename, rows):
        output = io.StringIO()
        fieldnames = [
            "batch_id",
            "sample_id",
            "selected_words",
            "attempt_no",
            "user_text",
            "prompt_version",
            "model_name",
            "provider_code",
            "total_score",
            "dimension_scores",
            "summary",
            "details",
            "next_task",
            "improvement",
            "rewrite",
            "raw_response",
            "error",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for item in rows:
            writer.writerow(
                {
                    "batch_id": item["batchId"],
                    "sample_id": item["sampleId"],
                    "selected_words": " / ".join(item["selectedWords"]),
                    "attempt_no": item["attemptNo"],
                    "user_text": item["userText"],
                    "prompt_version": item["promptVersion"],
                    "model_name": item["modelName"],
                    "provider_code": item["providerCode"],
                    "total_score": item["totalScore"],
                    "dimension_scores": json_dumps(item["dimensionScores"]),
                    "summary": item["summary"],
                    "details": json_dumps(item["details"]),
                    "next_task": item["nextTask"],
                    "improvement": item.get("improvement") or item["nextTask"] or "；".join(item.get("suggestions", [])),
                    "rewrite": item["rewrite"],
                    "raw_response": json_dumps(item["rawResponse"]),
                    "error": item["error"],
                }
            )
        body = output.getvalue().encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def dashboard_csv_ok(self, filename, rows):
        output = io.StringIO()
        fieldnames = list(rows[0].keys()) if rows else ["date"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for item in rows:
            writer.writerow(item)
        body = output.getvalue().encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def fail(self, message, status_code=400):
        self._send(status_code, {"code": 1, "message": message, "data": None})

    def parse_body(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def current_client_id(self, parsed, body=None):
        query = parse_qs(parsed.query or "")
        return (
            (body or {}).get("clientId")
            or (query.get("clientId", [None])[0])
            or self.headers.get("X-Client-Id")
            or "legacy-demo-user"
        )

    def current_payment_demo_token(self, parsed, body=None):
        query = parse_qs(parsed.query or "")
        return (
            (body or {}).get("authToken")
            or (query.get("authToken", [None])[0])
            or self.headers.get("X-Payment-Demo-Token")
            or self.headers.get("X-Auth-Token")
            or ""
        )

    def current_auth_token(self, parsed, body=None):
        return self.current_payment_demo_token(parsed, body)

    def do_OPTIONS(self):
        self._send(200, {"code": 0, "message": "ok", "data": None})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/health":
            self.ok({"status": "ok", "service": "speakout-backend"})
            return
        if path in ("/admin", "/admin/"):
            self.send_response(302)
            self.send_header("Location", f"{ADMIN_ROUTE_PREFIX}/")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        if path == ADMIN_ROUTE_PREFIX:
            self.send_response(302)
            self.send_header("Location", f"{ADMIN_ROUTE_PREFIX}/")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        if path == f"{ADMIN_ROUTE_PREFIX}/":
            self.send_file(ADMIN_FRONTEND_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path.startswith(f"{ADMIN_ROUTE_PREFIX}/"):
            self.send_admin_file(path)
            return
        if not os.getenv("RAILWAY_ENVIRONMENT"):
            if path in ("/", "/index.html"):
                self.send_file(FRONTEND_DIR / "index.html", "text/html; charset=utf-8")
                return
            if path in ("/payment-demo", "/payment-demo.html"):
                self.send_file(FRONTEND_DIR / "payment-demo.html", "text/html; charset=utf-8")
                return
            if path in ("/agreement", "/agreement.html"):
                self.send_file(FRONTEND_DIR / "agreement.html", "text/html; charset=utf-8")
                return
            if path == "/app.js":
                self.send_file(FRONTEND_DIR / "app.js", "application/javascript; charset=utf-8")
                return
            if path == "/styles.css":
                self.send_file(FRONTEND_DIR / "styles.css", "text/css; charset=utf-8")
                return
            if path.startswith("/assets/"):
                self.send_frontend_asset(path)
                return

        conn = db()
        try:
            client_id = self.current_client_id(parsed)
            auth_token = self.current_auth_token(parsed)
            current_user = resolve_request_user(conn, client_id, auth_token)
            if path == "/api/user/home-summary":
                self.ok(home_summary(conn, current_user["id"], auth_token))
            elif path == "/api/user/profile":
                self.ok(profile_state(conn, current_user["id"], auth_token))
            elif path == "/api/account/state":
                self.ok(payment_demo_state(conn, client_id, auth_token))
            elif path == "/api/membership/status":
                self.ok(profile_state(conn, current_user["id"], auth_token))
            elif path == "/api/training/session/current":
                self.ok(serialize_session(conn, fetch_active_session(conn, current_user["id"]), current_user["id"], auth_token))
            elif path == "/api/training/session/current/feedback":
                state = serialize_session(conn, fetch_active_session(conn, current_user["id"]), current_user["id"], auth_token)
                self.ok(state["feedback"] if state else None)
            elif path == "/api/training/history":
                self.ok(history_list(conn, current_user["id"]))
            elif path.startswith("/api/training/history/"):
                record_id = path.split("/")[-1]
                record = next((item for item in history_list(conn, current_user["id"]) if item["id"] == record_id), None)
                if not record:
                    self.fail("记录不存在", 404)
                else:
                    self.ok(record)
            elif path == "/api/account/orders":
                ctx = account_context(conn, auth_token, client_id)
                user_row = ctx["paymentUser"]
                self.ok(payment_demo_orders_for_user(conn, user_row["id"]) if user_row else [])
            elif path == "/admin-api/dashboard/overview":
                self.ok(admin_dashboard(conn))
            elif path == "/admin-api/dashboard/export-today":
                self.dashboard_csv_ok(
                    f"speakout-dashboard-7days-{datetime.now().strftime('%Y%m%d')}.csv",
                    admin_seven_day_export_rows(conn),
                )
            elif path == "/admin-api/users":
                self.ok(admin_users(conn))
            elif path == "/admin-api/users/benefits-config":
                self.ok(admin_user_benefits_config(conn))
            elif path == "/admin-api/users/entitlement-history":
                self.ok(admin_entitlement_history(conn))
            elif path == "/admin-api/users/pending-entitlements":
                self.ok(admin_pending_entitlements(conn))
            elif path == "/admin-api/orders":
                self.ok(admin_orders(conn))
            elif path == "/admin-api/content/words":
                self.ok(admin_words(conn))
            elif path == "/admin-api/content/quotes":
                self.ok(admin_quotes(conn))
            elif path == "/admin-api/training-history":
                self.ok(admin_training_history(conn))
            elif path == "/admin-api/config/ai-prompts":
                self.ok(admin_prompts(conn))
            elif path == "/admin-api/config/ai-prompts/versions":
                prompt_key = parse_qs(parsed.query).get("promptKey", ["card_association_feedback"])[0]
                self.ok(admin_prompt_versions(conn, prompt_key))
            elif path == "/admin-api/config/runtime":
                self.ok(admin_runtime_config())
            elif path == "/admin-api/models":
                self.ok(admin_models(conn))
            elif path == "/admin-api/ai-feedback/jobs":
                self.ok(admin_jobs(conn))
            elif path == "/admin-api/prompt-evals/batches":
                self.ok(admin_eval_batches(conn))
            elif path.startswith("/admin-api/prompt-evals/batches/") and path.endswith("/results"):
                batch_id = path.split("/")[-2]
                self.ok(admin_eval_batch_results(conn, batch_id))
            elif path.startswith("/admin-api/prompt-evals/batches/") and path.endswith("/download"):
                batch_id = path.split("/")[-2]
                self.csv_ok(f"{batch_id}.csv", admin_eval_batch_results(conn, batch_id))
            elif path == "/admin-api/redeem-codes":
                self.ok(admin_redeem_codes(conn))
            elif path == "/api/payment-demo/state":
                self.ok(payment_demo_state(conn, client_id, self.current_payment_demo_token(parsed)))
            elif path == "/api/payment-demo/notify":
                callback_params = {key: values[0] for key, values in parse_qs(parsed.query).items()}
                payment_demo_complete_return(conn, callback_params)
                self.text_ok("success")
            else:
                self.fail("接口不存在", 404)
        finally:
            conn.close()

    def do_POST(self):
        conn = db()
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            body = self.parse_body()
            client_id = self.current_client_id(parsed, body)
            auth_token = self.current_auth_token(parsed, body)
            current_user = resolve_request_user(conn, client_id, auth_token)
            if path == "/api/training/session/create":
                self.ok(create_round(conn, current_user["id"], auth_token))
            elif path == "/api/training/session/refresh":
                result = refresh_round(conn, current_user["id"], auth_token)
                if result.get("error") == "daily_flip_limit_inactive":
                    self.fail("今天已经翻开不少词咯，明天再继续呀～或开通权益解锁更自由选词")
                elif result.get("error") in {"daily_flip_limit_gift", "daily_flip_limit_paid"}:
                    self.fail("今天已经探索很多词啦，先把已选词练一练吧～")
                else:
                    self.ok(result)
            elif path == "/api/training/session/current/cards/toggle":
                result = toggle_card(conn, current_user["id"], body.get("cardId", ""), auth_token)
                if result.get("error") == "selection_full":
                    self.fail("一次只能选 2 张卡")
                elif result.get("error") == "daily_flip_limit_inactive":
                    self.fail("今天已经翻开不少词咯，明天再继续呀～或开通权益解锁更自由选词")
                elif result.get("error") in {"daily_flip_limit_gift", "daily_flip_limit_paid"}:
                    self.fail("今天已经探索很多词啦，先把已选词练一练吧～")
                elif result.get("error"):
                    self.fail("卡片状态不可用")
                else:
                    self.ok(result)
            elif path == "/api/training/session/current/draft":
                self.ok(save_draft(conn, current_user["id"], body.get("draftText", ""), auth_token))
            elif path == "/api/training/session/current/submit":
                self.ok(
                    submit_training(
                        conn,
                        current_user["id"],
                        body.get("transcriptText", ""),
                        body.get("selectedWords") or [],
                        auth_token,
                    )
                )
            elif path == "/api/training/session/current/continue":
                self.ok(continue_after_feedback(conn, current_user["id"], auth_token))
            elif path == "/api/training/session/current/finish":
                self.ok(finish_current_feedback(conn, current_user["id"], auth_token))
            elif path == "/api/analytics/training-event":
                self.ok(track_training_event(conn, current_user["id"], body))
            elif path == "/api/user/register":
                self.ok(register_user(conn, current_user["id"], body.get("nickname", ""), body.get("contact", "")))
            elif path == "/api/account/register":
                self.ok(
                    payment_demo_register(
                        conn,
                        client_id,
                        body.get("phone", ""),
                        body.get("password", ""),
                        body.get("confirmPassword", ""),
                    )
                )
            elif path == "/api/account/login":
                self.ok(
                    payment_demo_login(
                        conn,
                        client_id,
                        body.get("phone", ""),
                        body.get("password", ""),
                    )
                )
            elif path == "/api/account/logout":
                self.ok(payment_demo_logout(conn, auth_token, client_id))
            elif path == "/api/account/order":
                self.ok(
                    payment_demo_create_order(
                        conn,
                        client_id,
                        auth_token,
                        body.get("planId", ""),
                        payment_demo_base_url(self),
                        self.client_address[0] if self.client_address else "127.0.0.1",
                        self.headers.get("User-Agent", ""),
                    )
                )
            elif path == "/api/account/verify-return":
                self.ok(
                    payment_demo_complete_return(
                        conn,
                        body.get("callbackParams", {}),
                        client_id=client_id,
                        auth_token=auth_token,
                    )
                )
            elif path == "/api/account/payment-status":
                self.ok(
                    payment_demo_refresh_order_status(
                        conn,
                        client_id,
                        auth_token,
                        body.get("orderNo", ""),
                    )
                )
            elif path == "/api/membership/activate":
                order_id = f"KK{int(time.time())}"
                conn.execute("UPDATE membership SET is_member = 1, plan_name = '高手会员' WHERE user_id = ?", (current_user["id"],))
                conn.execute(
                    "INSERT INTO membership_orders (id, user_id, amount, status, paid_at) VALUES (?, ?, 19, '已支付', ?)",
                    (order_id, current_user["id"], now_text()),
                )
                conn.commit()
                self.ok({"profile": profile_state(conn, current_user["id"]), "orderNo": order_id})
            elif path == "/api/membership/redeem":
                self.ok(redeem_membership(conn, current_user["id"], body.get("code", "")))
            elif path == "/api/payment-demo/order":
                self.ok(
                    payment_demo_create_order(
                        conn,
                        client_id,
                        self.current_payment_demo_token(parsed, body),
                        body.get("planId", ""),
                        payment_demo_base_url(self),
                        self.client_address[0] if self.client_address else "127.0.0.1",
                        self.headers.get("User-Agent", ""),
                    )
                )
            elif path == "/api/payment-demo/verify-return":
                self.ok(
                    payment_demo_complete_return(
                        conn,
                        body.get("callbackParams", {}),
                        client_id=client_id,
                        auth_token=self.current_payment_demo_token(parsed, body),
                    )
                )
            elif path == "/api/payment-demo/register":
                self.ok(
                    payment_demo_register(
                        conn,
                        client_id,
                        body.get("phone", ""),
                        body.get("password", ""),
                        body.get("confirmPassword", ""),
                    )
                )
            elif path == "/api/payment-demo/login":
                self.ok(
                    payment_demo_login(
                        conn,
                        client_id,
                        body.get("phone", ""),
                        body.get("password", ""),
                    )
                )
            elif path == "/api/payment-demo/logout":
                self.ok(payment_demo_logout(conn, self.current_payment_demo_token(parsed, body), client_id))
            elif path == "/api/payment-demo/reset":
                self.ok(payment_demo_reset(conn, client_id, self.current_payment_demo_token(parsed, body)))
            elif path == "/admin-api/config/ai-prompts/test":
                self.ok(admin_test_prompt(conn, body))
            elif path == "/admin-api/config/ai-prompts/update":
                self.ok(
                    update_prompt(
                        conn,
                        body.get("promptKey"),
                        body.get("systemPrompt"),
                        body.get("userPromptTemplate"),
                        body.get("modelName"),
                        body.get("providerCode"),
                        body.get("changeNote"),
                    )
                )
            elif path == "/admin-api/config/ai-prompts/rollback":
                self.ok(rollback_prompt(conn, body.get("promptKey"), body.get("versionNo")))
            elif path == "/admin-api/prompt-evals/run":
                self.ok(run_prompt_eval_batch(conn, body))
            elif path == "/admin-api/config/runtime/update":
                self.ok(update_runtime_config(conn, body))
            elif path == "/admin-api/models/save":
                self.ok(upsert_admin_model(conn, body))
            elif path == "/admin-api/models/set-active":
                self.ok(set_active_admin_model(conn, body))
            elif path == "/admin-api/models/test-connection":
                self.ok(test_admin_model_connection(conn, body))
            elif path == "/admin-api/models/test-schema":
                self.ok(test_admin_model_schema(conn, body))
            elif path == "/admin-api/users/benefits-config/update":
                self.ok(update_admin_user_benefits_config(conn, body))
            elif path == "/admin-api/users/grant-entitlement":
                self.ok(admin_grant_entitlement(conn, body))
            elif path == "/admin-api/users/set-expire-at":
                self.ok(admin_set_entitlement_expire_at(conn, body))
            elif path == "/admin-api/users/delete":
                self.ok(delete_admin_user(conn, body))
            elif path == "/admin-api/redeem-codes/generate":
                self.ok(
                    generate_redeem_codes(
                        conn,
                        body.get("quantity", 10),
                        body.get("planName", "高手会员"),
                        body.get("prefix", "SPEAKOUT"),
                    )
                )
            elif path == "/admin-api/redeem-codes/status":
                self.ok(update_redeem_code_status(conn, body.get("code", ""), body.get("status", "")))
            elif path == "/admin-api/content/quotes/create":
                self.ok(create_quote(conn, body))
            elif path == "/admin-api/content/quotes/status":
                self.ok(update_quote_status(conn, body))
            elif path == "/admin-api/content/quotes/delete":
                self.ok(delete_quote(conn, body))
            elif path == "/admin-api/content/words/delete":
                self.ok(delete_admin_word(conn, body))
            elif path == "/admin-api/orders/delete":
                self.ok(delete_admin_order(conn, body))
            elif path == "/admin-api/training-history/delete":
                self.ok(delete_admin_training_history(conn, body))
            else:
                self.fail("接口不存在", 404)
        except ValueError as error:
            self.fail(str(error), 400)
        except Exception as error:
            traceback.print_exc()
            self.fail(f"服务端异常：{error}", 500)
        finally:
            conn.close()


def main():
    init_db()
    cleanup_dirty_sessions()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Backend running on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
