from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from services.assistant_service import get_assistant_response

assistant_bp = Blueprint("assistant", __name__, url_prefix="/assistant")

SUGGESTED_QUESTIONS = [
    "What is my next medicine?",
    "What medicines do I have today?",
    "Which medicines are expiring soon?",
    "Which medicine is scheduled now?",
    "Show my missed medicines.",
]


@assistant_bp.route("/")
@login_required
def index():
    return render_template("assistant.html", suggested_questions=SUGGESTED_QUESTIONS)


@assistant_bp.route("/query", methods=["POST"])
@login_required
def query():
    """
    JSON endpoint used by static/js/assistant.js.
    Every response is generated ONLY from the get_assistant_response()
    pipeline - see services/assistant_service.py for the enforced safety
    boundary (medical-advice requests are refused before any DB lookup;
    all factual answers are assembled strictly from stored DB records).
    """
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    result = get_assistant_response(current_user.id, message)

    return jsonify({
        "intent": result["intent"],
        "response": result["response"],
    })
