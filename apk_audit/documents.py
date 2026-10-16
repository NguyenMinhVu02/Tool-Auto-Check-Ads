"""Read partner documents without losing spreadsheet rows or their source lines."""

import csv
import json
from pathlib import Path
import unicodedata

from .errors import AuditError


def _header_name(value):
    text = unicodedata.normalize('NFKD', value).replace('đ', 'd').replace('Đ', 'D')
    return ' '.join(''.join(char for char in text if not unicodedata.combining(char)).casefold().split())


def _column(header, *names):
    return next((header.index(name) for name in names if name in header), None)


def _cell(row, index):
    return row[index].strip() if index is not None and index < len(row) else ''


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
        header = [_header_name(cell) for cell in rows[0][1]]
        if header == ["key", "value"]:
            result = {}
            for line, row in rows[1:]:
                if not any(cell.strip() for cell in row):
                    continue
                if len(row) != 2 or not row[0].strip() or row[0].strip() in result:
                    raise ValueError(f"CSV key,value có key rỗng/trùng hoặc sai số cột ở dòng {line}")
                result[row[0].strip()] = row[1].strip()
            return result
        name_column = _column(header, 'name', 'ten', 'placement', 'placement name')
        type_column = _column(header, 'ads type', 'ad type')
        id_column = _column(header, 'id', 'ad unit id')
        if kind == "ads_scripts" and all(index is not None for index in (name_column, type_column, id_column)):
            placements = []
            names = set()
            app_id = None
            notes = []
            for line, row in rows[1:]:
                ad_type, name, ad_id = (_cell(row, index) for index in (type_column, name_column, id_column))
                label = _header_name(name).rstrip(':')
                if label == "app id":
                    app_id = ad_id or None
                elif label == "note" or (not ad_type and not ad_id):
                    notes.extend(value.strip() for index, value in enumerate(row)
                                 if index != _column(header, 'stt') and value.strip() and _header_name(value).rstrip(':') != 'note')
                elif name and ad_type.lower() in {"native", "banner", "inter", "interstitial", "open", "reward", "rewarded"}:
                    if name in names:
                        raise ValueError(f"ADS SCRIPTS có placement trùng ở dòng {line}: {name}")
                    names.add(name)
                    placements.append({"name": name, "ad_type": "interstitial" if ad_type.lower() == "inter" else ad_type.lower(),
                                       "id": ad_id, "description": _cell(row, _column(header, 'mo ta', 'mo ta tv', 'description')),
                                       "description_en": _cell(row, _column(header, 'mo ta ta', 'description')),
                                       "format": _cell(row, _column(header, 'format', 'layout')),
                                       "note": _cell(row, _column(header, 'note')), "line": line})
            if not placements:
                raise ValueError("ADS SCRIPTS không có placement hợp lệ")
            return {"placements": placements, "app_id": app_id, "notes": notes}
        task_column = _column(header, 'task', 'content')
        detail_column = _column(header, 'task detail', 'detail')
        if kind == "checklist" and task_column is not None and detail_column is not None:
            values = []
            for line, row in rows[1:]:
                if any(value.strip() for value in row):
                    values.append({"line": line, "phase": _cell(row, _column(header, 'phase 2', 'phase')),
                                   "task": _cell(row, task_column), "detail": _cell(row, detail_column),
                                   "document": _cell(row, _column(header, 'document')),
                                   "pic": _cell(row, _column(header, 'pic')), "deadline": _cell(row, _column(header, 'deadline')),
                                   "status": _cell(row, _column(header, 'status', 'status (mark when done)'))})
            if not values:
                raise ValueError("Working file không có dòng dữ liệu")
            return {"checklist_rows": values}
        label = 'ADS SCRIPTS (cần Ads type, Name/Tên, ID)' if kind == 'ads_scripts' else 'working file (cần Task/Content, Task Detail/Detail)'
        raise ValueError(f"CSV không đúng mẫu {label} hoặc key,value; hãy kiểm tra chọn đúng ô tài liệu")
    except (OSError, ValueError, csv.Error) as exc:
        raise AuditError(f"Không đọc được tài liệu: {exc}") from exc
