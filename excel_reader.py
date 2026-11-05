from datetime import date, datetime, time
from openpyxl import load_workbook


def cell_text(value):
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y' if value.time() == time() else '%d/%m/%Y %H:%M')
    if isinstance(value, date):
        return value.strftime('%d/%m/%Y')
    if isinstance(value, time):
        return value.strftime('%H:%M')
    return str(value).strip()


def read_participants(file_path):
    from email_templates import variable_key

    workbook = load_workbook(file_path, data_only=True)
    try:
        worksheet = workbook.active
        headers = {}
        for cell in worksheet[1]:
            if cell.value is not None and str(cell.value).strip():
                key = variable_key(str(cell.value))
                if key in headers:
                    raise ValueError(f"Duplicate Excel column: {cell.value}")
                headers[key] = cell.column
        for required in ('name', 'email'):
            if required not in headers:
                raise ValueError(f"Excel file does not contain a '{required.title()}' column.")
        participants = []
        for row in range(2, worksheet.max_row + 1):
            values = {key: cell_text(worksheet.cell(row, column).value)
                      for key, column in headers.items()}
            if not values['name'] and not values['email']:
                continue
            participants.append({'name': values['name'], 'email': values['email'],
                                 'variables': values})
        return participants
    finally:
        workbook.close()
