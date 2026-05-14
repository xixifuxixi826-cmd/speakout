#!/usr/bin/env python3
import json
import os
import sqlite3
import traceback
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
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
        "cards": [
            "自由", "束缚", "谎言", "成长", "安全感", "孤独", "欲望", "秩序",
            "体面", "野心", "痛苦", "亲密", "稳定", "选择", "焦虑", "边界"
        ],
    },
    {
        "id": "deck-b",
        "cards": [
            "公平", "偏见", "效率", "善良", "责任", "天赋", "代价", "服从",
            "尊严", "控制", "信任", "脆弱", "嫉妒", "共情", "失败", "原谅"
        ],
    },
    {
        "id": "deck-c",
        "cards": [
            "原生家庭", "自律", "自由意志", "比较", "内耗", "爱情", "婚姻", "工作",
            "意义", "身份", "标签", "羞耻", "愤怒", "妥协", "冒险", "现实"
        ],
    },
]

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
          time_label TEXT NOT NULL,
          pair_json TEXT NOT NULL,
          excerpt TEXT NOT NULL,
          score INTEGER NOT NULL,
          summary TEXT NOT NULL,
          details_json TEXT NOT NULL,
          suggestions_json TEXT NOT NULL,
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

        CREATE TABLE IF NOT EXISTS app_config (
          config_key TEXT PRIMARY KEY,
          config_value TEXT NOT NULL,
          updated_at TEXT NOT NULL
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

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_client_id ON users(client_id)")

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

    cur.execute("DELETE FROM words")
    for deck in WORD_DECKS:
        for index, word in enumerate(deck["cards"]):
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
            (id, title, time_label, pair_json, excerpt, score, summary, details_json, suggestions_json, created_at, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM history_records WHERE id = ?), ?), 1)
            """,
            (
                record["id"],
                record["title"],
                record["timeLabel"],
                json_dumps(record["pair"]),
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
                3,
                "你是一名严格但鼓励式的表达教练，任务是评估用户是否完成了一次有观点、有解释、有画面的中文口语表达。你必须返回严格 JSON，不要输出 Markdown，不要输出 JSON 之外的任何解释。评分时重点看六件事：1. 是否明确提出“A是B”或“A是一种B”的判断句；2. 判断句本身是否有张力、辨识度和讨论空间；3. 是否解释了这句话为什么成立，而不是只重复词语；4. 解释是否具体，是否落到场景、人物、动作、关系或代价；5. 结构是否顺，是否能让听的人跟上；6. 语言是否自然，是否像真实的人在说话而不是在背稿。请保持鼓励但不敷衍，既指出亮点，也指出最关键的短板。",
                "训练词语：{{selected_words}}\n用户表达：{{user_text}}\n请按 JSON 返回以下字段：totalScore、summary、details、suggestions、rewrite。details 必须是数组，至少包含六项，分别围绕：判断句成立度、观点张力、解释充分度、具体性与画面感、结构流畅度、语言自然度。每项都必须含 label、score、note。suggestions 请给 3 条可直接执行的修改建议。rewrite 请给一版更自然、更有画面感、但不脱离原观点的参考表达。",
                runtime_config["model_api_model"] or "gpt-4o",
                runtime_config["model_provider_code"] or "yunwu",
                now_text(),
            ),
        )
    else:
        cur.execute(
            """
            UPDATE ai_prompts
            SET
              system_prompt = ?,
              user_prompt_template = ?,
              model_name = ?,
              provider_code = ?,
              updated_at = ?
            WHERE prompt_key = 'card_association_feedback'
            """,
            (
                "你是一名严格但鼓励式的表达教练，任务是评估用户是否完成了一次有观点、有解释、有画面的中文口语表达。你必须返回严格 JSON，不要输出 Markdown，不要输出 JSON 之外的任何解释。评分时重点看六件事：1. 是否明确提出“A是B”或“A是一种B”的判断句；2. 判断句本身是否有张力、辨识度和讨论空间；3. 是否解释了这句话为什么成立，而不是只重复词语；4. 解释是否具体，是否落到场景、人物、动作、关系或代价；5. 结构是否顺，是否能让听的人跟上；6. 语言是否自然，是否像真实的人在说话而不是在背稿。请保持鼓励但不敷衍，既指出亮点，也指出最关键的短板。",
                "训练词语：{{selected_words}}\n用户表达：{{user_text}}\n请按 JSON 返回以下字段：totalScore、summary、details、suggestions、rewrite。details 必须是数组，至少包含六项，分别围绕：判断句成立度、观点张力、解释充分度、具体性与画面感、结构流畅度、语言自然度。每项都必须含 label、score、note。suggestions 请给 3 条可直接执行的修改建议。rewrite 请给一版更自然、更有画面感、但不脱离原观点的参考表达。",
                runtime_config["model_api_model"] or "gpt-4o",
                runtime_config["model_provider_code"] or "yunwu",
                now_text(),
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
        INSERT INTO users
        (nickname, started_rounds_today, current_round_index, client_id, contact, is_registered, registered_at, created_at)
        VALUES (?, 0, 0, ?, '', 0, NULL, ?)
        """,
        (guest_nickname(client_id), client_id, now_text()),
    )
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO membership (user_id, is_member, plan_name) VALUES (?, 0, '普通版')",
        (user_id,),
    )
    conn.commit()
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def fetch_user_state(conn, user_id):
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    membership = conn.execute("SELECT * FROM membership WHERE user_id = ?", (user_id,)).fetchone()
    return user, membership


def remaining_quota(user, membership):
    if membership["is_member"]:
        return float("inf")
    return max(0, 3 - user["started_rounds_today"])


def fetch_active_session(conn, user_id):
    return conn.execute(
        "SELECT * FROM sessions WHERE user_id = ? AND status IN ('active', 'feedback_ready') ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()


def session_cards(conn, session_id):
    rows = conn.execute(
        "SELECT * FROM session_cards WHERE session_id = ? ORDER BY position_index ASC",
        (session_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def expected_words_for_deck(deck_id):
    for deck in WORD_DECKS:
        if deck["id"] == deck_id:
            return deck["cards"]
    return []


def session_is_stale(conn, session_row):
    cards = session_cards(conn, session_row["id"])
    expected_words = expected_words_for_deck(session_row["source_deck_id"])
    actual_words = [card["word"] for card in cards]
    if not cards or not expected_words:
        return False
    return actual_words != expected_words


def serialize_session(conn, session_row, user_id):
    if not session_row:
        return None
    user, membership = fetch_user_state(conn, user_id)
    cards = session_cards(conn, session_row["id"])
    selected_ids = set(json_loads(session_row["selected_json"], []))
    selected_cards = [card for card in cards if card["id"] in selected_ids]
    used_count = len([card for card in cards if card["state"] == "used"])
    flipped_count = len([card for card in cards if card["state"] != "hidden"])

    for card in cards:
        card["isSelected"] = card["id"] in selected_ids

    return {
        "sessionId": session_row["id"],
        "roundNo": session_row["round_no"],
        "usedCount": used_count,
        "flippedCount": flipped_count,
        "totalCount": len(cards),
        "selectedCount": len(selected_cards),
        "isComplete": used_count == len(cards),
        "cards": cards,
        "selectedCards": selected_cards,
        "remainingQuota": -1 if membership["is_member"] else remaining_quota(user, membership),
        "draftText": session_row["draft_text"] or "",
        "feedback": json_loads(session_row["feedback_json"], None),
    }


def create_round(conn, user_id):
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
            state = serialize_session(conn, active, user_id)
            if not state["isComplete"]:
                return {"blocked": False, "state": state}

    if not membership["is_member"] and remaining_quota(user, membership) <= 0:
        return {"blocked": True}

    round_no = user["started_rounds_today"] + 1
    deck_index = user["current_round_index"] % len(WORD_DECKS)
    deck = WORD_DECKS[deck_index]
    session_id = f"session-{uuid.uuid4().hex[:10]}"
    timestamp = now_text()
    conn.execute(
        """
        INSERT INTO sessions (id, user_id, round_no, source_deck_id, status, selected_json, draft_text, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'active', '[]', '', ?, ?)
        """,
        (session_id, user_id, round_no, deck["id"], timestamp, timestamp),
    )

    for index, word in enumerate(deck["cards"]):
        conn.execute(
            """
            INSERT INTO session_cards (id, session_id, word, kind, position_index, state)
            VALUES (?, ?, ?, 'concept', ?, 'hidden')
            """,
            (f"{session_id}-card-{index + 1}", session_id, word, index),
        )

    conn.execute(
        "UPDATE users SET started_rounds_today = started_rounds_today + 1, current_round_index = current_round_index + 1 WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    return {"blocked": False, "state": serialize_session(conn, fetch_active_session(conn, user_id), user_id)}


def toggle_card(conn, user_id, card_id):
    active = fetch_active_session(conn, user_id)
    if not active:
        return {"error": "round_missing"}

    card = conn.execute(
        "SELECT * FROM session_cards WHERE id = ? AND session_id = ?",
        (card_id, active["id"]),
    ).fetchone()
    if not card or card["state"] == "used":
        return {"error": "card_locked"}

    selected_ids = json_loads(active["selected_json"], [])
    if card["state"] == "hidden":
        conn.execute(
            "UPDATE session_cards SET state = 'flipped' WHERE id = ?",
            (card_id,),
        )

    if card_id in selected_ids:
        selected_ids.remove(card_id)
    else:
        if len(selected_ids) >= 2:
            return {"error": "selection_full"}
        selected_ids.append(card_id)

    conn.execute(
        "UPDATE sessions SET selected_json = ?, updated_at = ? WHERE id = ?",
        (json_dumps(selected_ids), now_text(), active["id"]),
    )
    conn.commit()
    return {"ok": True, "state": serialize_session(conn, fetch_active_session(conn, user_id), user_id)}


def save_draft(conn, user_id, draft_text):
    active = fetch_active_session(conn, user_id)
    if not active:
        return None
    conn.execute(
        "UPDATE sessions SET draft_text = ?, updated_at = ? WHERE id = ?",
        (draft_text, now_text(), active["id"]),
    )
    conn.commit()
    return serialize_session(conn, fetch_active_session(conn, user_id), user_id)


def build_thinking_paths(first, second):
    return [
        f"先不要急着解释，先想这两个词在什么场景里会被同时看见。比如工作、亲密关系、集体生活、学校或工厂，这些地方最容易同时出现“{first}”和“{second}”。",
        f"再想一个具体人物。这个人为什么会一边承受“{second}”，一边又表现出“{first}”？他的动作、表情、说话方式、处境压力分别是什么？",
        f"最后补一层代价和结果：如果一直停留在“{second}”里，会发生什么；如果试图靠近“{first}”，又要承担什么代价？这样这句话就会更像真实的人生判断，而不是空概念。",
    ]


def build_reference_rewrite(first, second):
    return "\n\n".join(
        [
            f"我的观点是，{first}是一种{second}。这句话听上去有点矛盾，但我想说的是，很多时候我们以为{first}和{second}是对立的，可真正落到人的处境里，它们往往会一起出现。",
            f"比如在很多规规矩矩的工作场景里，一个人看上去特别守秩序，流程也一丝不苟，但你越靠近就越能感受到那种紧绷感。像流水线上的厂工厂妹、窗口岗位上必须分秒不差的人、或者每天在标准化表格里重复确认细节的职场人，他们表面上是在维持一种稳定和{second}，可那种稳定里常常包着巨大的{first}。因为越是规则细密、越是不能出错，人就越容易不断自我校正、自我压迫，最后形成一种带着制度感的焦虑。",
            f"如果把视角再放大一点，我们甚至会想到动物的刻板行为。一个被长期关在狭小空间里的动物，会反复走同一段路、做同一个动作。它看起来非常有秩序，可那个秩序本身并不意味着平静，反而可能暴露出内在极大的不安。人有时候也是一样，越是拼命把生活排得整整齐齐，越说明他害怕失控，害怕一旦松开，很多东西会立刻塌下来。",
            f"所以我会把{first}理解成一种被{second}长期压出来的状态。它不只是情绪上的慌张，也是一种被环境训练出来的警觉。也正因为这样，当我们看到一个人特别规矩、特别配合、特别没有差错的时候，未必意味着他真的轻松，反而可能意味着他正背着很重的心理负荷。这样一来，{first}是一种{second}，这句话就成立了。"
        ]
    )


def build_local_feedback(selected_cards, submission_text, is_member):
    first = selected_cards[0]["word"]
    second = selected_cards[1]["word"]
    text_length = len((submission_text or "").strip())
    dimension_scores = [
        min(96, 60 + text_length // 7),
        min(94, 64 + text_length // 8),
        min(95, 62 + text_length // 7),
        min(92, 58 + text_length // 9),
        min(93, 63 + text_length // 8),
        min(94, 66 + text_length // 9),
    ]
    total_score = round(sum(dimension_scores) / len(dimension_scores))
    summary = (
        "你已经建立了两个词之间的关系，表达方向是成立的。"
        if text_length > 50
        else "你已经开始建立词语联系，但还能再具体一些。"
    )
    details = [
        {
            "label": "判断句成立度",
            "score": dimension_scores[0],
            "note": "你已经在开头提出判断，下一步是更快把场景接上。"
        },
        {
            "label": "观点张力",
            "score": dimension_scores[1],
            "note": "如果判断句更反直觉、更有辨识度，听众会更想继续听。"
        },
        {
            "label": "解释充分度",
            "score": dimension_scores[2],
            "note": "解释方向是通的，但还可以补人物动作或情境细节。"
        },
        {
            "label": "具体性与画面感",
            "score": dimension_scores[3],
            "note": "如果能看到场景、人物和关系，这一维会明显更强。"
        },
        {
            "label": "结构流畅度",
            "score": dimension_scores[4],
            "note": "表达已经有顺序，再加强转折和收束会更稳。"
        },
        {
            "label": "语言自然度",
            "score": dimension_scores[5],
            "note": "整体像真实人在说话，但还可以更像你自己的口气。"
        },
    ]
    return {
        "pairTitle": f"{first} + {second}",
        "totalScore": total_score,
        "summary": summary,
        "thinkingPaths": build_thinking_paths(first, second),
        "rewrite": build_reference_rewrite(first, second),
        "suggestions": [
            "开头直接说出“ A 是 B ”或“ A 是一种 B ”这句判断。",
            "不要只解释概念，补进一个人、一段关系，或一个具体工作场景。",
            "结尾再补一句你为什么认同这句话，让表达收住。"
        ],
        "details": details,
        "visibleDetails": details if is_member else details,
        "freeModeNote": "" if is_member else "免费用户当前只展示精简版 AI 点评，高手会员可查看完整拆解。"
    }


def call_model_api(selected_cards, submission_text, prompt_row):
    runtime_config = load_runtime_config()
    api_url = runtime_config["model_api_url"]
    api_key = runtime_config["model_api_key"]
    model_name = runtime_config["model_api_model"] or prompt_row["model_name"]
    provider_code = runtime_config["model_provider_code"] or "yunwu"

    if not api_url or not api_key:
        return None

    selected_words = " / ".join(card["word"] for card in selected_cards)
    user_prompt = prompt_row["user_prompt_template"].replace("{{selected_words}}", selected_words).replace(
        "{{user_text}}", submission_text
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
        with urlopen(request, timeout=20) as response:
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
        return None


def score_submission(conn, session_row, submission_text):
    runtime_config = load_runtime_config()
    prompt = conn.execute("SELECT * FROM ai_prompts WHERE prompt_key = 'card_association_feedback'").fetchone()
    selected_ids = set(json_loads(session_row["selected_json"], []))
    cards = session_cards(conn, session_row["id"])
    selected_cards = [card for card in cards if card["id"] in selected_ids]
    membership = conn.execute("SELECT * FROM membership WHERE user_id = ?", (session_row["user_id"],)).fetchone()

    model_result = call_model_api(selected_cards, submission_text, prompt)
    if model_result and model_result.get("feedback"):
        feedback = model_result["feedback"]
        if not isinstance(feedback, dict) or "totalScore" not in feedback:
            model_result = None

    if model_result:
        feedback = model_result["feedback"]
        feedback.setdefault("details", [])
        feedback.setdefault("suggestions", [])
        feedback.setdefault("visibleDetails", feedback.get("details", []))
        if len(feedback["details"]) >= 1:
            total = round(sum(float(item.get("score", 0)) for item in feedback["details"]) / len(feedback["details"]))
            feedback["totalScore"] = max(0, min(100, total))
        feedback.setdefault(
            "thinkingPaths",
            build_thinking_paths(selected_cards[0]["word"], selected_cards[1]["word"])
        )
        feedback.setdefault(
            "rewrite",
            build_reference_rewrite(selected_cards[0]["word"], selected_cards[1]["word"])
        )
        feedback.setdefault("freeModeNote", "" if membership["is_member"] else "免费用户当前只展示精简版 AI 点评，高手会员可查看完整拆解。")
        provider_code = model_result["provider_code"]
        feedback["aiSource"] = provider_code
        model_name = model_result["model_name"]
        response_payload = model_result["raw_response"]
        status = "success"
    else:
        if runtime_config["require_real_ai"]:
            raise RuntimeError("真实 AI 调用失败：当前已开启严格真实 AI 模式，未回退本地评分。请检查云雾接口、API Key 或模型可用性。")
        feedback = build_local_feedback(selected_cards, submission_text, bool(membership["is_member"]))
        feedback["aiSource"] = "local-fallback"
        provider_code = "local"
        model_name = "local-scorer-v1"
        response_payload = feedback
        status = "fallback"

    job_id = f"JOB{int(time.time() * 1000)}"
    request_payload = {
        "selected_words": [card["word"] for card in selected_cards],
        "user_text": submission_text,
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


def submit_training(conn, user_id, transcript_text):
    session_row = fetch_active_session(conn, user_id)
    if not session_row:
        raise ValueError("当前没有进行中的训练")

    selected_ids = json_loads(session_row["selected_json"], [])
    if len(selected_ids) != 2:
        raise ValueError("当前必须先选中两张卡片")

    for card_id in selected_ids:
        conn.execute("UPDATE session_cards SET state = 'used' WHERE id = ?", (card_id,))
        word = conn.execute("SELECT word FROM session_cards WHERE id = ?", (card_id,)).fetchone()["word"]
        conn.execute("UPDATE words SET used_count = used_count + 1 WHERE word = ?", (word,))

    feedback = score_submission(conn, session_row, transcript_text)
    cards = session_cards(conn, session_row["id"])
    pair = [card["word"] for card in cards if card["id"] in selected_ids]
    record_id = f"history-{uuid.uuid4().hex[:10]}"
    record = {
        "id": record_id,
        "title": f"第{session_row['round_no']}轮｜{pair[0]} + {pair[1]}",
        "timeLabel": datetime.now().strftime("%m-%d %H:%M"),
        "pair": pair,
        "excerpt": transcript_text,
        "score": int(feedback["totalScore"]),
        "summary": feedback["summary"],
        "details": feedback["details"],
        "suggestions": feedback["suggestions"],
    }
    conn.execute(
        """
        INSERT INTO history_records
        (id, title, time_label, pair_json, excerpt, score, summary, details_json, suggestions_json, created_at, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["id"],
            record["title"],
            record["timeLabel"],
            json_dumps(record["pair"]),
            record["excerpt"],
            record["score"],
            record["summary"],
            json_dumps(record["details"]),
            json_dumps(record["suggestions"]),
            now_text(),
            user_id,
        ),
    )

    conn.execute(
        "UPDATE sessions SET selected_json = '[]', draft_text = '', feedback_json = ?, status = 'feedback_ready', updated_at = ? WHERE id = ?",
        (json_dumps(feedback), now_text(), session_row["id"]),
    )
    conn.commit()
    active = fetch_active_session(conn, user_id)
    state = serialize_session(conn, active, user_id)
    feedback["isRoundComplete"] = state["isComplete"]
    feedback["latestHistoryId"] = record["id"]
    feedback["selectedWords"] = pair
    return feedback


def continue_after_feedback(conn, user_id):
    active = fetch_active_session(conn, user_id)
    if not active:
        return {"route": "/pages/home/index"}

    state = serialize_session(conn, active, user_id)
    conn.execute(
        "UPDATE sessions SET feedback_json = NULL, status = 'active', updated_at = ? WHERE id = ?",
        (now_text(), active["id"]),
    )
    conn.execute(
        "UPDATE sessions SET selected_json = '[]' WHERE id = ?",
        (active["id"],),
    )
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
        user, membership = fetch_user_state(conn, user_id)
        if not membership["is_member"] and remaining_quota(user, membership) <= 0:
            return {"route": "/pages/membership/index?from=quota"}
        return {"route": "/pages/training/index?mode=next"}

    conn.commit()
    return {"route": "/pages/training/index"}


def home_summary(conn, user_id):
    user, membership = fetch_user_state(conn, user_id)
    latest = conn.execute(
        "SELECT * FROM history_records WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    active = fetch_active_session(conn, user_id)
    return {
        "nickname": user["nickname"],
        "isRegistered": bool(user["is_registered"]),
        "isMember": bool(membership["is_member"]),
        "planName": membership["plan_name"],
        "memberLabel": "高手会员" if membership["is_member"] else "免费用户",
        "remainingQuotaText": "无限次" if membership["is_member"] else f"{remaining_quota(user, membership)} / 3",
        "activeRoundText": "当前轮次进行中" if active else "今日可开新轮次",
        "startButtonText": f"开始第 {user['started_rounds_today'] + 1} 轮",
        "hasLatestHistory": latest is not None,
        "latestHistoryTitle": latest["title"] if latest else "",
        "latestHistoryScore": str(latest["score"]) if latest else "",
        "latestHistorySummary": latest["summary"] if latest else "",
    }


def profile_state(conn, user_id):
    user, membership = fetch_user_state(conn, user_id)
    quota = remaining_quota(user, membership)
    return {
        "nickname": user["nickname"],
        "contact": user["contact"] or "",
        "isRegistered": bool(user["is_registered"]),
        "registeredAt": user["registered_at"] or "",
        "isMember": bool(membership["is_member"]),
        "planName": membership["plan_name"],
        "usedFreeRounds": min(user["started_rounds_today"], 3),
        "remainingQuota": "无限次" if membership["is_member"] else quota,
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
            "score": row["score"],
            "summary": row["summary"],
            "details": json_loads(row["details_json"], []),
            "suggestions": json_loads(row["suggestions_json"], []),
        }
        for row in rows
    ]


def admin_dashboard(conn):
    users = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    paid_users = conn.execute("SELECT COUNT(*) AS count FROM membership WHERE is_member = 1").fetchone()["count"]
    training_volume = conn.execute("SELECT COUNT(*) AS count FROM history_records").fetchone()["count"]
    revenue_row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM membership_orders WHERE status = '已支付'"
    ).fetchone()
    return {
        "registeredUsers": users,
        "dailyActiveUsers": 126,
        "trainingVolume": training_volume,
        "paidUsers": paid_users,
        "revenue": f"¥{int(revenue_row['total'])}",
    }


def admin_users(conn):
    rows = conn.execute(
        """
        SELECT
          u.id,
          u.nickname,
          u.created_at,
          u.registered_at,
          u.is_registered,
          u.started_rounds_today,
          m.is_member
        FROM users u
        LEFT JOIN membership m ON m.user_id = u.id
        ORDER BY u.id DESC
        """
    ).fetchall()
    return [
        {
            "id": f"U{int(row['id']):04d}",
            "nickname": row["nickname"],
            "registeredAt": (row["registered_at"] or row["created_at"] or "-")[:16],
            "activityState": "已注册" if row["is_registered"] else "游客体验",
            "membershipStatus": "会员" if row["is_member"] else "免费",
            "trainingSummary": f"{row['started_rounds_today']} 轮 / {max(1, row['started_rounds_today'] * 2)} 次表达",
        }
        for row in rows
    ]


def admin_orders(conn):
    rows = conn.execute(
        """
        SELECT o.*, u.nickname
        FROM membership_orders o
        LEFT JOIN users u ON u.id = o.user_id
        ORDER BY o.paid_at DESC
        """
    ).fetchall()
    return [
        {
            "orderNo": row["id"],
            "user": row["nickname"] or "游客用户",
            "amount": f"¥{int(row['amount'])}" if row["amount"] else "兑换开通",
            "status": row["status"],
            "paidAt": row["paid_at"][:16],
        }
        for row in rows
    ]


def admin_words(conn):
    rows = conn.execute(
        "SELECT word, status, used_count FROM words ORDER BY used_count DESC, position_index ASC LIMIT 12"
    ).fetchall()
    return [
        {"word": row["word"], "status": "已发布" if row["status"] == "published" else "待审核", "usedCount": row["used_count"]}
        for row in rows
    ]


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


def admin_runtime_config():
    runtime_config = load_runtime_config()
    return {
        "modelApiUrl": runtime_config["model_api_url"],
        "modelApiKey": runtime_config["model_api_key"],
        "modelApiModel": runtime_config["model_api_model"],
        "modelProviderCode": runtime_config["model_provider_code"],
        "requireRealAi": runtime_config["require_real_ai"],
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


def update_prompt(conn, prompt_key, system_prompt, user_prompt_template, model_name=None, provider_code=None):
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
    conn.commit()
    return admin_prompts(conn)


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

    prompt_row = {
        "system_prompt": body.get("systemPrompt", prompt["system_prompt"]),
        "user_prompt_template": body.get("userPromptTemplate", prompt["user_prompt_template"]),
        "model_name": body.get("modelName", prompt["model_name"]),
        "provider_code": body.get("providerCode", prompt["provider_code"]),
        "prompt_key": prompt["prompt_key"],
        "version_no": prompt["version_no"],
    }

    model_result = call_model_api(
        [{"word": selected_words[0]}, {"word": selected_words[1]}],
        user_text,
        prompt_row,
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
            json_dumps(body),
            json_dumps(model_result["raw_response"]),
            now_text(),
        ),
    )
    conn.commit()
    return {
        "testId": test_id,
        "providerCode": model_result["provider_code"],
        "modelName": model_result["model_name"],
        "feedback": model_result["feedback"],
        "rawResponse": model_result["raw_response"],
    }


def admin_jobs(conn):
    rows = conn.execute("SELECT * FROM ai_jobs ORDER BY created_at DESC LIMIT 20").fetchall()
    return [
        {
            "jobId": row["id"],
            "sessionId": row["session_id"],
            "promptKey": row["prompt_key"],
            "versionNo": row["version_no"],
            "modelName": row["model_name"],
            "status": row["status"],
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
            "usedAt": row["used_at"] or "-",
        }
        for row in rows
    ]


class AppHandler(BaseHTTPRequestHandler):
    server_version = "ExpressMasterHTTP/0.1"

    def _send(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Client-Id")
        self.end_headers()
        self.wfile.write(body)

    def ok(self, data):
        self._send(200, {"code": 0, "message": "success", "data": data})

    def fail(self, message, status_code=400):
        self._send(status_code, {"code": 1, "message": message, "data": None})

    def parse_body(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def do_OPTIONS(self):
        self._send(200, {"code": 0, "message": "ok", "data": None})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/health":
            self.ok({"status": "ok"})
            return

        conn = db()
        try:
            client_id = self.headers.get("X-Client-Id", "legacy-demo-user")
            current_user = resolve_user(conn, client_id)
            if path == "/api/user/home-summary":
                self.ok(home_summary(conn, current_user["id"]))
            elif path == "/api/user/profile":
                self.ok(profile_state(conn, current_user["id"]))
            elif path == "/api/membership/status":
                self.ok(profile_state(conn, current_user["id"]))
            elif path == "/api/training/session/current":
                self.ok(serialize_session(conn, fetch_active_session(conn, current_user["id"]), current_user["id"]))
            elif path == "/api/training/session/current/feedback":
                state = serialize_session(conn, fetch_active_session(conn, current_user["id"]), current_user["id"])
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
            elif path == "/admin-api/dashboard/overview":
                self.ok(admin_dashboard(conn))
            elif path == "/admin-api/users":
                self.ok(admin_users(conn))
            elif path == "/admin-api/orders":
                self.ok(admin_orders(conn))
            elif path == "/admin-api/content/words":
                self.ok(admin_words(conn))
            elif path == "/admin-api/config/ai-prompts":
                self.ok(admin_prompts(conn))
            elif path == "/admin-api/config/runtime":
                self.ok(admin_runtime_config())
            elif path == "/admin-api/ai-feedback/jobs":
                self.ok(admin_jobs(conn))
            elif path == "/admin-api/redeem-codes":
                self.ok(admin_redeem_codes(conn))
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
            client_id = self.headers.get("X-Client-Id", "legacy-demo-user")
            current_user = resolve_user(conn, client_id)
            if path == "/api/training/session/create":
                self.ok(create_round(conn, current_user["id"]))
            elif path == "/api/training/session/current/cards/toggle":
                result = toggle_card(conn, current_user["id"], body.get("cardId", ""))
                if result.get("error") == "selection_full":
                    self.fail("一次只能选 2 张卡")
                elif result.get("error"):
                    self.fail("卡片状态不可用")
                else:
                    self.ok(result)
            elif path == "/api/training/session/current/draft":
                self.ok(save_draft(conn, current_user["id"], body.get("draftText", "")))
            elif path == "/api/training/session/current/submit":
                self.ok(submit_training(conn, current_user["id"], body.get("transcriptText", "")))
            elif path == "/api/training/session/current/continue":
                self.ok(continue_after_feedback(conn, current_user["id"]))
            elif path == "/api/user/register":
                self.ok(register_user(conn, current_user["id"], body.get("nickname", ""), body.get("contact", "")))
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
                    )
                )
            elif path == "/admin-api/config/runtime/update":
                self.ok(update_runtime_config(conn, body))
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
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Backend running on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
