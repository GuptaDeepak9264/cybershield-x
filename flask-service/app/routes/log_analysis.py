from flask import Blueprint, jsonify

from .. import get_db
from ..auth import admin_required
from ..services.log_analysis_service import detect_malicious_rate_anomaly, keyword_frequency

log_analysis_bp = Blueprint("log_analysis", __name__, url_prefix="/api/v1/logs")


@log_analysis_bp.get("/keyword-frequency")
@admin_required
def get_keyword_frequency():
    return jsonify(keyword_frequency(get_db()))


@log_analysis_bp.get("/anomalies")
@admin_required
def get_anomalies():
    return jsonify(detect_malicious_rate_anomaly(get_db()))
