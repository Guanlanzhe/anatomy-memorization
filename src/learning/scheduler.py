"""
FSRS 调度 + Supabase 持久化。
每个用户的数据存在 Supabase 的 learning_state 表里，按 user_id 隔离。
"""

from datetime import datetime, timezone
from fsrs import Scheduler, Card, Rating, State

from src.supabase_client import get_supabase, get_current_user_id

scheduler = Scheduler()

RATING_MAP = {
    "again": Rating.Again,
    "hard": Rating.Hard,
    "good": Rating.Good,
    "easy": Rating.Easy,
}


def _row_to_dict(row: dict) -> dict:
    return {
        "card_id": row["card_id"],
        "state": row["state"],
        "due": row["due"],
        "stability": row["stability"],
        "difficulty": row["difficulty"],
        "step": row["step"],
        "last_review": row["last_review"],
        "total_attempts": row["total_attempts"],
        "total_correct": row["total_correct"],
    }


def get_or_create_card(card_id: str) -> dict:
    """从 Supabase 拿卡片，不存在则创建。"""
    user_id = get_current_user_id()
    if not user_id:
        return {}

    sb = get_supabase()
    res = sb.table("learning_state").select("*").eq("user_id", user_id).eq("card_id", card_id).execute()

    if res.data:
        return _row_to_dict(res.data[0])

    # 不存在，创建
    card = Card()
    s = card.state
    state_value = s.value if isinstance(s, State) else int(s)

    new_row = {
        "user_id": user_id,
        "card_id": card_id,
        "state": state_value,
        "due": card.due.isoformat() if card.due else None,
        "stability": card.stability,
        "difficulty": card.difficulty,
        "step": card.step,
        "last_review": card.last_review.isoformat() if card.last_review else None,
        "total_attempts": 0,
        "total_correct": 0,
    }

    sb.table("learning_state").insert(new_row).execute()
    return _row_to_dict(new_row)


def review_card(card_id: str, rating: str = "good", correct: bool = True) -> dict:
    """评分 + 更新统计，写回 Supabase。"""
    user_id = get_current_user_id()
    if not user_id:
        return {}

    sb = get_supabase()
    res = sb.table("learning_state").select("*").eq("user_id", user_id).eq("card_id", card_id).execute()
    if not res.data:
        return {}

    row = res.data[0]

    # 还原 Card
    state_raw = row["state"]
    try:
        state = State(state_raw) if not isinstance(state_raw, State) else state_raw
    except Exception:
        state = State.New

    last_review = row.get("last_review")
    last_review_dt = datetime.fromisoformat(last_review) if last_review else None

    due = row.get("due")
    due_dt = datetime.fromisoformat(due) if due else datetime.now(timezone.utc)

    card = Card(
        card_id=row["card_id"],
        state=state,
        due=due_dt,
        stability=row.get("stability", 0.0),
        difficulty=row.get("difficulty", 0.0),
        step=row.get("step", 0),
        last_review=last_review_dt,
    )

    r = RATING_MAP.get(rating, Rating.Good)
    card, _log = scheduler.review_card(card, r)

    s = card.state
    state_value = s.value if isinstance(s, State) else int(s)

    update_data = {
        "state": state_value,
        "due": card.due.isoformat() if card.due else None,
        "stability": card.stability,
        "difficulty": card.difficulty,
        "step": card.step,
        "last_review": card.last_review.isoformat() if card.last_review else None,
        "total_attempts": row.get("total_attempts", 0) + 1,
        "total_correct": row.get("total_correct", 0) + (1 if correct else 0),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    sb.table("learning_state").update(update_data).eq("user_id", user_id).eq("card_id", card_id).execute()

    return {**row, **update_data}


def get_stats() -> dict:
    """整体统计（主页用）。"""
    user_id = get_current_user_id()
    if not user_id:
        return {"total": 0, "due": 0, "learning": 0, "review": 0, "new": 0}

    sb = get_supabase()
    res = sb.table("learning_state").select("*").eq("user_id", user_id).execute()

    now = datetime.now(timezone.utc)
    total = len(res.data)
    due = 0
    learning = 0
    review = 0
    new = 0

    for row in res.data:
        s = row.get("state", 0)
        if s == 0:
            new += 1
        elif s in (1, 3):
            learning += 1
        elif s == 2:
            review += 1

        due_str = row.get("due")
        if due_str:
            try:
                due_dt = datetime.fromisoformat(due_str)
                if due_dt.tzinfo is None:
                    due_dt = due_dt.replace(tzinfo=timezone.utc)
                if due_dt <= now:
                    due += 1
            except Exception:
                pass

    return {"total": total, "due": due, "learning": learning, "review": review, "new": new}


def get_card_stats() -> dict:
    """给统计页用的详细数据。"""
    from src.learning.question import ALL_MODES

    user_id = get_current_user_id()
    if not user_id:
        return {
            "need_review": 0, "mastered": 0, "not_done": 0,
            "total_attempts": 0, "total_correct": 0, "overall_rate": 0.0,
            "by_mode": {m: {"attempts": 0, "correct": 0, "rate": 0.0} for m in ALL_MODES},
        }

    sb = get_supabase()
    res = sb.table("learning_state").select("*").eq("user_id", user_id).execute()

    need_review = 0
    mastered = 0
    not_done = 0
    total_attempts = 0
    total_correct = 0

    by_mode_attempts = {m: 0 for m in ALL_MODES}
    by_mode_correct = {m: 0 for m in ALL_MODES}

    for row in res.data:
        attempts = row.get("total_attempts", 0)
        correct = row.get("total_correct", 0)

        if attempts == 0:
            not_done += 1
        else:
            rate = correct / attempts
            if rate < 0.5:
                need_review += 1
            else:
                mastered += 1

        total_attempts += attempts
        total_correct += correct

        parts = row["card_id"].split(":")
        mode = parts[1] if len(parts) > 1 else None
        if mode in by_mode_attempts:
            by_mode_attempts[mode] += attempts
            by_mode_correct[mode] += correct

    overall_rate = (total_correct / total_attempts) if total_attempts > 0 else 0.0

    by_mode = {}
    for m in ALL_MODES:
        a = by_mode_attempts[m]
        c = by_mode_correct[m]
        by_mode[m] = {"attempts": a, "correct": c, "rate": (c / a) if a > 0 else 0.0}

    return {
        "need_review": need_review,
        "mastered": mastered,
        "not_done": not_done,
        "total_attempts": total_attempts,
        "total_correct": total_correct,
        "overall_rate": overall_rate,
        "by_mode": by_mode,
    }


def get_need_review_cards() -> list:
    """返回所有需要复习的卡片 ID 列表。"""
    user_id = get_current_user_id()
    if not user_id:
        return []

    sb = get_supabase()
    res = sb.table("learning_state").select("card_id, total_attempts, total_correct").eq("user_id", user_id).execute()

    result = []
    for row in res.data:
        attempts = row.get("total_attempts", 0)
        correct = row.get("total_correct", 0)
        if attempts == 0:
            continue
        if correct / attempts < 0.5:
            result.append(row["card_id"])
    return result