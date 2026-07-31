from flask import Blueprint, jsonify

from .. import get_db
from ..auth import admin_required
from ..services.analytics_service import daily_trend, summary

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/v1/analytics")


@analytics_bp.get("/summary")
@admin_required
def get_summary():
    return jsonify(summary(get_db()))


@analytics_bp.get("/daily-trend")
@admin_required
def get_daily_trend():
    return jsonify(daily_trend(get_db()))
