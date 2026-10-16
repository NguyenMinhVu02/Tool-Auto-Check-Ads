"""Read partner documents without losing spreadsheet rows or their source lines."""

import csv
import json
from pathlib import Path

from .errors import AuditError


def load_document(path, kind=None):
    if path is None:
        return None
    path = Path(path)
    try:
        if path.suffix.lower() == ".json":
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("JSON cần object")
            return value
        if path.suffix.lower() != ".csv":
            raise ValueError("Tài liệu cần là .csv hoặc .json")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            rows = []
            while True:
                line = reader.line_num + 1
                try:
                    row = next(reader)
                except StopIteration:
                    break
                rows.append((line, row))
        if not rows:
            raise ValueError("CSV rỗng")
        header = [cell.strip() for cell in rows[0][1]]
        if header == ["key", "value"]:
            result = {}
            for line, row in rows[1:]:
                if not any(cell.strip() for cell in row):
                    continue
                if len(row) != 2 or not row[0].strip() or row[0].strip() in result:
                    raise ValueError(f"CSV key,value có key rỗng/trùng hoặc sai số cột ở dòng {line}")
                result[row[0].strip()] = row[1].strip()
            return result
        if kind == "ads_scripts" and header[:4] == ["STT", "Ads type", "Name", "ID"]:
            placements = []
            names = set()
            app_id = None
            notes = []
            for line, row in rows[1:]:
                row = (row + [""] * len(header))[:len(header)]
                number, ad_type, name, ad_id = (value.strip() for value in row[:4])
                if name == "App ID":
                    app_id = ad_id or None
                elif name == "Note" or (not number and not ad_type and not ad_id):
                    notes.extend(value.strip() for value in row[2:8] if value.strip() and value.strip() != "Note")
                elif name and ad_type.lower() in {"native", "banner", "inter", "interstitial", "open", "reward", "rewarded"}:
                    if name in names:
                        raise ValueError(f"ADS SCRIPTS có placement trùng ở dòng {line}: {name}")
                    names.add(name)
                    placements.append({"name": name, "ad_type": "interstitial" if ad_type.lower() == "inter" else ad_type.lower(),
                                       "id": ad_id, "description": row[4].strip(), "format": row[6].strip(),
                                       "note": row[7].strip(), "line": line})
            if not placements:
                raise ValueError("ADS SCRIPTS không có placement hợp lệ")
            return {"placements": placements, "app_id": app_id, "notes": notes}
        if kind == "checklist" and header[:4] == ["Phase 2", "Task", "Task Detail", "Document"]:
            values = []
            for line, row in rows[1:]:
                row = (row + [""] * len(header))[:len(header)]
                if any(value.strip() for value in row):
                    values.append({"line": line, "phase": row[0].strip(), "task": row[1].strip(),
                                   "detail": row[2].strip(), "document": row[3].strip(),
                                   "pic": row[4].strip(), "deadline": row[5].strip(),
                                   "status": row[6].strip()})
            if not values:
                raise ValueError("Working file không có dòng dữ liệu")
            return {"checklist_rows": values}
        raise ValueError("CSV không đúng mẫu key,value hoặc mẫu ADS SCRIPTS/working file đã hỗ trợ")
    except (OSError, ValueError, csv.Error) as exc:
        raise AuditError(f"Không đọc được tài liệu: {exc}") from exc
