"""Read partner documents without losing spreadsheet rows or their source lines."""

import csv
import json
from pathlib import Path
import unicodedata
from zipfile import BadZipFile, ZipFile
from xml.etree.ElementTree import ParseError

from .errors import AuditError
from .placement_policy import flag, normalize_ads_document
from .document_structure import HEADER_ALIASES, map_structure


def _header_name(value):
    text = unicodedata.normalize('NFKD', value).replace('đ', 'd').replace('Đ', 'D')
    return ' '.join(''.join(char for char in text if not unicodedata.combining(char)).casefold().split())


def _column(header, *names):
    canonical = lambda value: HEADER_ALIASES.get(value, value)
    for name in names:
        matches = [index for index, value in enumerate(header) if canonical(value) == canonical(name)]
        if matches:
            return matches[0] if len(matches) == 1 else None
    return None


def _cell(row, index):
    return row[index].strip() if index is not None and index < len(row) else ''


def _matching_header(header, kind):
    if header == ['key', 'value']:
        return True
    if kind == 'ads_scripts':
        return all(_column(header, *names) is not None for names in (
            ('name', 'ten', 'placement', 'placement name'), ('ads type', 'ad type'), ('id', 'ad unit id')))
    return kind == 'checklist' and _column(header, 'task', 'content') is not None and _column(header, 'task detail', 'detail') is not None


def _colored_fill(fill):
    if not fill.patternType:
        return False
    color = fill.fgColor
    if color.type == 'rgb':
        return color.rgb[-6:].upper() != 'FFFFFF'
    if color.type == 'indexed':
        return color.indexed not in (9, 64)
    if color.type == 'theme':
        return color.theme != 0 or bool(color.tint)
    return False


def _open_workbook(path):
    from openpyxl import load_workbook
    from openpyxl.utils.exceptions import InvalidFileException

    with ZipFile(path) as archive:
        if sum(info.file_size for info in archive.infolist()) > 100 * 1024 * 1024:
            raise ValueError('XLSX vượt giới hạn 100 MiB sau giải nén')
    try:
        return load_workbook(path, data_only=False, keep_links=False)
    except InvalidFileException as exc:
        raise ValueError('File XLSX không hợp lệ') from exc

def _header_matches(sheets, kind):
    matches = []
    for sheet in sheets:
        for cells in sheet.iter_rows(min_row=1, max_row=min(sheet.max_row, 40), max_col=min(sheet.max_column, 256)):
            header = [_header_name(str(cell.value or '')) for cell in cells]
            while header and not header[-1]:
                header.pop()
            if _matching_header(header, kind):
                matches.append((sheet, cells[0].row, header))
                break
    return matches

def list_sheets(path, kind):
    """Sheets the user can pick: header matches first, else every visible sheet (AI mapping)."""
    if Path(path).suffix.lower() != '.xlsx':
        return []
    workbook = _open_workbook(path)
    try:
        visible = [sheet for sheet in workbook.worksheets if sheet.sheet_state == 'visible']
        matches = [sheet.title for sheet, _, _ in _header_matches(visible, kind)]
        return matches or [sheet.title for sheet in visible]
    finally:
        workbook.close()

def _xlsx_rows(path, kind, mapper=None, sheet_name=None):
    workbook = _open_workbook(path)
    try:
        visible = [sheet for sheet in workbook.worksheets if sheet.sheet_state == 'visible']
        if sheet_name is not None:
            visible = [sheet for sheet in visible if sheet.title == sheet_name]
            if not visible:
                raise ValueError(f'XLSX không có sheet hiển thị tên "{sheet_name}"')
        matches = _header_matches(visible, kind)
        method = 'deterministic'
        if not matches and mapper:
            if len(visible) > 1:
                raise ValueError('XLSX có nhiều sheet chưa nhận dạng; hãy chọn sheet của app cần kiểm trước khi AI ánh xạ cột')
            candidates = [(sheet.title, [(cells[0].row, [str(c.value or '') for c in cells])
                          for cells in sheet.iter_rows(max_row=min(sheet.max_row, 40),
                                                       max_col=min(sheet.max_column, 64))])
                          for sheet in visible]
            name, start, header = map_structure(candidates, kind, mapper)
            matches = [(workbook[name], start, header)]
            method = 'ai_mapping'
        if not matches:
            raise ValueError('XLSX không có sheet đúng mẫu ADS SCRIPTS/working file trong 40 dòng đầu')
        if len(matches) > 1:
            raise ValueError('XLSX có nhiều sheet cùng mẫu (' + ', '.join(m[0].title for m in matches)
                             + '); hãy chọn sheet cần kiểm tra')
        sheet, start, header = matches[0]
        if sheet.max_row > 20000 or sheet.max_column > 256:
            raise ValueError('Sheet XLSX vượt giới hạn 20000 dòng hoặc 256 cột')
        rows, marks = [], {}
        name_col = _column(header, 'name', 'ten', 'placement', 'placement name')
        id_col = _column(header, 'id', 'ad unit id')
        for cells in sheet.iter_rows(min_row=start):
            line = cells[0].row
            rows.append((line, header if line == start else
                         [str(cell.value) if cell.value is not None else '' for cell in cells]))
            if kind == 'ads_scripts' and id_col is not None and name_col is not None and line > start:
                name_cell, id_cell = cells[name_col], cells[id_col]
                fill = id_cell.fill
                if not fill.patternType:
                    fill = sheet.row_dimensions[line].fill
                if not fill.patternType:
                    fill = sheet.column_dimensions[id_cell.column_letter].fill
                marks[line] = {
                    'strikethrough': bool(name_cell.font.strike or id_cell.font.strike),
                    'highlighted': _colored_fill(fill),
                    'formula_id': id_cell.data_type == 'f',
                    'formatting_uncertain': any(id_cell.coordinate in rule.sqref or name_cell.coordinate in rule.sqref
                                                for rule in sheet.conditional_formatting),
                }
        return rows, marks, sheet.title, method
    finally:
        workbook.close()


def _csv_rows(path, kind):
    best, best_score = ',', -1
    for delimiter in (',', ';', '\t', '|'):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.reader(stream, delimiter=delimiter)
            score = 0
            for row in reader:
                if reader.line_num > 40:
                    break
                if _matching_header([_header_name(cell) for cell in row], kind):
                    best = delimiter
                    break
                score += len(row) if len(row) > 1 else 0
            else:
                row = None
            if row is not None and _matching_header([_header_name(cell) for cell in row], kind):
                break
            if score > best_score:
                best, best_score = delimiter, score
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, delimiter=best)
        rows = []
        while True:
            line = reader.line_num + 1
            try:
                row = next(reader)
            except StopIteration:
                break
            rows.append((line, row))
    return rows


def load_document(path, kind=None, *, mapper=None, sheet=None):
    if path is None:
        return None
    path = Path(path)
    try:
        if path.suffix.lower() == ".json":
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("JSON cần object")
            return normalize_ads_document(value) if kind == 'ads_scripts' else value
        marks, sheet_name, method = {}, None, 'deterministic'
        if path.suffix.lower() == '.xlsx':
            rows, marks, sheet_name, method = _xlsx_rows(path, kind, mapper, sheet)
        elif path.suffix.lower() == '.csv':
            rows = _csv_rows(path, kind)
            # Spreadsheet exports may keep a title/blank rows above the table.
            # Slice records, preserving their original physical source lines.
            for index, (line, row) in enumerate(rows):
                if line > 40:
                    break
                if _matching_header([_header_name(cell) for cell in row], kind):
                    rows = rows[index:]
                    break
            if rows and not _matching_header([_header_name(cell) for cell in rows[0][1]], kind) and mapper:
                _, start, header = map_structure([('CSV', rows)], kind, mapper)
                index = next(i for i, (line, _) in enumerate(rows) if line == start)
                rows = [(start, header), *rows[index+1:]]
                method = 'ai_mapping'
        else:
            raise ValueError("Tài liệu cần là .xlsx, .csv hoặc .json")
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
                                       "note": _cell(row, _column(header, 'note')), "line": line,
                                       "status": _cell(row, _column(header, 'status', 'trang thai')),
                                       "enabled": _cell(row, _column(header, 'enabled', 'isenable', 'is enabled')),
                                       **marks.get(line, {}),
                                       "strikethrough": flag(_cell(row, _column(header, 'strikethrough', 'gach ngang'))) is True or marks.get(line, {}).get('strikethrough', False),
                                       "highlighted": flag(_cell(row, _column(header, 'highlighted', 'boi mau'))) is True or marks.get(line, {}).get('highlighted', False)})
            if not placements:
                raise ValueError("ADS SCRIPTS không có placement hợp lệ")
            result = normalize_ads_document({"placements": placements, "app_id": app_id, "notes": notes}, csv_format=sheet_name is None)
            if sheet_name:
                result['sheet'] = sheet_name
            result['parsing'] = {'method': method, 'header_line': rows[0][0]}
            return result
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
            return {"checklist_rows": values, 'parsing': {'method': method, 'header_line': rows[0][0]},
                    **({'sheet': sheet_name} if sheet_name else {})}
        label = 'ADS SCRIPTS (cần Ads type, Name/Tên, ID)' if kind == 'ads_scripts' else 'working file (cần Task/Content, Task Detail/Detail)'
        raise ValueError(f"CSV không đúng mẫu {label} hoặc key,value; hãy kiểm tra chọn đúng ô tài liệu")
    except (OSError, ValueError, csv.Error, BadZipFile, ParseError, KeyError) as exc:
        raise AuditError(f"Không đọc được tài liệu: {exc}") from exc
