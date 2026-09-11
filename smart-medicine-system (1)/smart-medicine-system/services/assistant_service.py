"""
Controlled AI Assistant service.

STRICT BOUNDARY:
This assistant answers ONLY from the user's own stored database records.
It never diagnoses, prescribes, recommends medicines/dosages, or gives
any medical advice. Any question that looks like a request for medical
advice is intercepted BEFORE any database lookup and given a fixed,
safe refusal response.

Flow:  User Question -> Intent Detection -> (if MEDICAL_ADVICE_REQUEST:
       refuse immediately) -> Database Query -> Response built ONLY from
       retrieved rows. Nothing is invented.

If AI_API_KEY is configured, an external LLM MAY be used, but only to help
with the free-text -> intent classification step, and the safety refusal
list below is always checked first, in code, regardless of what any model
returns. The actual factual answer is ALWAYS assembled from the database,
never generated freely by an LLM - this prevents hallucinated medical
content even if an external API is used.
"""

import re
from datetime import date, datetime

from models.medicine import Medicine
from services import reminder_service, expiry_service
from services.reminder_service import get_next_medicine, get_current_scheduled_medicine, get_today_schedule
from services.expiry_service import get_expiring_medicines
from models.history import STATUS_MISSED, STATUS_PENDING

# ---------------------------------------------------------------------------
# 1. HARD SAFETY BOUNDARY - checked first, always, no exceptions.
# ---------------------------------------------------------------------------

MEDICAL_ADVICE_PATTERNS = [
    r"\bwhich medicine (should|do) i take\b",
    r"\bwhat (medicine|drug) (should|can) i take\b",
    r"\bshould i (take|start|stop|increase|decrease|change|switch)\b",
    r"\bcan i (take|combine|mix|stop|increase|decrease)\b",
    r"\brecommend.*(medicine|drug|dosage|dose)\b",
    r"\bsuggest.*(medicine|drug|dosage|dose)\b",
    r"\bwhat.*(good|best).*(for|to treat)\b",
    r"\bdiagnos",
    r"\bwhat('?s| is) wrong with me\b",
    r"\bi (have|feel|got) (a |an )?(headache|fever|pain|cold|flu|cough|nausea)\b",
    r"\bis it safe to\b",
    r"\bside effects?\b",
    r"\bwhat disease\b",
    r"\bcure\b",
    r"\btreat(ment)? for\b",
    r"\bincrease.*(dose|dosage)\b",
    r"\bdecrease.*(dose|dosage)\b",
    r"\bchange.*(dose|dosage|schedule|prescription)\b",
    r"\breplace.*(medicine|drug)\b",
    r"\bnew medicine\b",
    r"\bprescribe\b",
]

SAFE_REFUSAL = (
    "I can help you manage medicines and schedules saved in your account, "
    "but I can't diagnose conditions, recommend medicines, or advise on "
    "dosage changes. Please consult a qualified healthcare professional "
    "for medical advice."
)


def is_medical_advice_request(text: str) -> bool:
    lowered = text.lower().strip()
    return any(re.search(pattern, lowered) for pattern in MEDICAL_ADVICE_PATTERNS)


# ---------------------------------------------------------------------------
# 2. INTENT DETECTION (rule/keyword-based fallback - always available,
#    works fully offline with no external AI API required).
# ---------------------------------------------------------------------------

INTENT_NEXT_MEDICINE = "NEXT_MEDICINE"
INTENT_TODAY_MEDICINES = "TODAY_MEDICINES"
INTENT_CURRENT_MEDICINE = "CURRENT_MEDICINE"
INTENT_MEDICINE_SCHEDULE = "MEDICINE_SCHEDULE"
INTENT_EXPIRING_MEDICINES = "EXPIRING_MEDICINES"
INTENT_MISSED_MEDICINES = "MISSED_MEDICINES"
INTENT_MEDICINE_DETAILS = "MEDICINE_DETAILS"
INTENT_MEDICINE_HISTORY = "MEDICINE_HISTORY"
INTENT_GREETING = "GREETING"
INTENT_UNKNOWN = "UNKNOWN"
INTENT_MEDICAL_ADVICE_REQUEST = "MEDICAL_ADVICE_REQUEST"


def detect_intent(text: str) -> str:
    lowered = text.lower().strip()

    # Safety check always runs first.
    if is_medical_advice_request(lowered):
        return INTENT_MEDICAL_ADVICE_REQUEST

    if re.search(r"\b(hi|hello|hey)\b", lowered) and len(lowered) < 20:
        return INTENT_GREETING

    if re.search(r"\b(next medicine|next dose|what'?s next|upcoming medicine)\b", lowered):
        return INTENT_NEXT_MEDICINE

    if re.search(r"\b(today'?s? medicines?|medicine(s)? today|what.*today)\b", lowered):
        return INTENT_TODAY_MEDICINES

    if re.search(r"\b(scheduled now|current medicine|right now|due now)\b", lowered):
        return INTENT_CURRENT_MEDICINE

    if re.search(r"\b(expir(y|ing|e|es))\b", lowered):
        return INTENT_EXPIRING_MEDICINES

    if re.search(r"\bmissed\b", lowered):
        return INTENT_MISSED_MEDICINES

    if re.search(r"\b(history|past|previous)\b", lowered):
        return INTENT_MEDICINE_HISTORY

    if re.search(r"\bwhen (is|does)\b.*\bschedul", lowered) or re.search(r"\bschedule\b", lowered):
        return INTENT_MEDICINE_SCHEDULE

    if re.search(r"\b(dosage|details|about|show me)\b", lowered):
        return INTENT_MEDICINE_DETAILS

    return INTENT_UNKNOWN


def _extract_medicine_name(text: str, user_id: int):
    """Try to match a known medicine name mentioned in the free text."""
    medicines = Medicine.query.filter_by(user_id=user_id, is_active=True).all()
    lowered = text.lower()
    for m in medicines:
        if m.name.lower() in lowered:
            return m
    return None


# ---------------------------------------------------------------------------
# 3. RESPONSE BUILDERS - each pulls ONLY from the database. No invented text.
# ---------------------------------------------------------------------------

def _respond_next_medicine(user_id):
    row = get_next_medicine(user_id)
    if not row:
        return "You have no upcoming scheduled medicines in your saved records."
    medicine = Medicine.query.get(row.medicine_id)
    when = "today" if row.date == date.today() else row.date.strftime("%A, %b %d")
    return f"Your next scheduled medicine is {medicine.name} at {row.scheduled_time.strftime('%I:%M %p')} ({when})."


def _respond_today_medicines(user_id):
    rows = get_today_schedule(user_id)
    if not rows:
        return "You have no medicines scheduled for today in your saved records."
    lines = []
    for r in rows:
        medicine = Medicine.query.get(r.medicine_id)
        lines.append(f"- {medicine.name} at {r.scheduled_time.strftime('%I:%M %p')} ({r.status})")
    return "Here is your schedule for today:\n" + "\n".join(lines)


def _respond_current_medicine(user_id):
    rows = get_current_scheduled_medicine(user_id)
    if not rows:
        return "I don't have any medicine scheduled around the current time in your saved records."
    lines = []
    for r in rows:
        medicine = Medicine.query.get(r.medicine_id)
        lines.append(f"- {medicine.name} at {r.scheduled_time.strftime('%I:%M %p')}")
    return "Currently scheduled:\n" + "\n".join(lines)


def _respond_expiring_medicines(user_id):
    meds = get_expiring_medicines(user_id, within_days=30)
    if not meds:
        return "No medicines in your saved records are expiring within the next 30 days."
    lines = []
    for m in meds:
        days = m.days_until_expiry
        if days < 0:
            status = f"expired {abs(days)} day(s) ago"
        elif days == 0:
            status = "expires today"
        else:
            status = f"expires in {days} day(s)"
        lines.append(f"- {m.name}: {status} ({m.expiry_date.strftime('%b %d, %Y')})")
    return "Here are your expiring/expired medicines:\n" + "\n".join(lines)


def _respond_missed_medicines(user_id):
    rows = reminder_service.get_missed_today(user_id)
    if not rows:
        return "You have no missed scheduled medicines today in your saved records."
    lines = []
    for r in rows:
        medicine = Medicine.query.get(r.medicine_id)
        lines.append(f"- {medicine.name} was scheduled at {r.scheduled_time.strftime('%I:%M %p')}")
    return "Missed medicines today:\n" + "\n".join(lines)


def _respond_medicine_schedule(user_id, text):
    medicine = _extract_medicine_name(text, user_id)
    if not medicine:
        return ("I couldn't find that medicine in your saved medicine records. "
                "Please check the exact name you used when adding it.")
    if not medicine.schedules:
        return f"No scheduled times have been saved for {medicine.name}."
    lines = [f"- {s.scheduled_time.strftime('%I:%M %p')} ({s.frequency})" for s in medicine.schedules]
    return f"Saved schedule for {medicine.name}:\n" + "\n".join(lines)


def _respond_medicine_details(user_id, text):
    medicine = _extract_medicine_name(text, user_id)
    if not medicine:
        return "I couldn't find that medicine in your saved medicine records."
    dosage = medicine.dosage or "No dosage information has been saved for this medicine."
    return (
        f"{medicine.name}\n"
        f"- Dosage: {dosage}\n"
        f"- Type: {medicine.medicine_type or 'Not specified'}\n"
        f"- Food instruction: {medicine.food_instruction}\n"
        f"- Expiry: {medicine.expiry_date.strftime('%b %d, %Y')}\n"
        f"- Quantity: {medicine.quantity if medicine.quantity is not None else 'Not specified'}"
    )


def _respond_medicine_history(user_id, text):
    medicine = _extract_medicine_name(text, user_id)
    from models.history import MedicineHistory
    query = MedicineHistory.query.filter_by(user_id=user_id)
    if medicine:
        query = query.filter_by(medicine_id=medicine.id)
    rows = query.order_by(MedicineHistory.date.desc()).limit(10).all()
    if not rows:
        return "No history records were found in your saved data."
    lines = []
    for r in rows:
        m = Medicine.query.get(r.medicine_id)
        lines.append(f"- {r.date.strftime('%b %d')}: {m.name} at {r.scheduled_time.strftime('%I:%M %p')} - {r.status}")
    return "Recent history:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def get_assistant_response(user_id: int, message: str) -> dict:
    """
    Returns {"intent": str, "response": str}.
    This is the single entry point routes/assistant.py should call.
    """
    if not message or not message.strip():
        return {"intent": INTENT_UNKNOWN, "response": "Please type a question about your medicines or schedule."}

    intent = detect_intent(message)

    if intent == INTENT_MEDICAL_ADVICE_REQUEST:
        return {"intent": intent, "response": SAFE_REFUSAL}

    if intent == INTENT_GREETING:
        return {"intent": intent, "response": "Hello! I can help you check your medicine schedule, "
                                               "expiring medicines, or missed doses. What would you like to know?"}

    if intent == INTENT_NEXT_MEDICINE:
        return {"intent": intent, "response": _respond_next_medicine(user_id)}

    if intent == INTENT_TODAY_MEDICINES:
        return {"intent": intent, "response": _respond_today_medicines(user_id)}

    if intent == INTENT_CURRENT_MEDICINE:
        return {"intent": intent, "response": _respond_current_medicine(user_id)}

    if intent == INTENT_EXPIRING_MEDICINES:
        return {"intent": intent, "response": _respond_expiring_medicines(user_id)}

    if intent == INTENT_MISSED_MEDICINES:
        return {"intent": intent, "response": _respond_missed_medicines(user_id)}

    if intent == INTENT_MEDICINE_SCHEDULE:
        return {"intent": intent, "response": _respond_medicine_schedule(user_id, message)}

    if intent == INTENT_MEDICINE_DETAILS:
        return {"intent": intent, "response": _respond_medicine_details(user_id, message)}

    if intent == INTENT_MEDICINE_HISTORY:
        return {"intent": intent, "response": _respond_medicine_history(user_id, message)}

    # UNKNOWN - try a last-resort medicine-name match before giving up
    medicine = _extract_medicine_name(message, user_id)
    if medicine:
        return {"intent": INTENT_MEDICINE_DETAILS, "response": _respond_medicine_details(user_id, message)}

    return {
        "intent": INTENT_UNKNOWN,
        "response": (
            "I'm not sure I understood that. You can ask me things like "
            "\"What's my next medicine?\", \"What medicines do I have today?\", "
            "\"Which medicines are expiring soon?\", or \"Show my missed medicines.\""
        ),
    }
