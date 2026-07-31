import csv
import io

from ..models import ScanLog, User


def scans_to_csv(scans: list[ScanLog], include_username: bool) -> str:
    buffer = io.StringIO()
    fieldnames = ["id", "scan_type", "target", "status", "security_score", "detail", "created_at"]
    if include_username:
        fieldnames.insert(1, "username")

    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for scan in scans:
        row = {
            "id": scan.id,
            "scan_type": scan.scan_type,
            "target": scan.target,
            "status": scan.status,
            "security_score": scan.security_score,
            "detail": scan.detail,
            "created_at": scan.created_at.isoformat(),
        }
        if include_username:
            row["username"] = scan.user.username
        writer.writerow(row)
    return buffer.getvalue()


def users_to_csv(users: list[User]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "username", "email", "role", "is_active"])
    writer.writeheader()
    for user in users:
        writer.writerow({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        })
    return buffer.getvalue()
