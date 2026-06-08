"""
excel_filler.py
Single consumer solar quotation filler.
"""

import shutil
import os
from datetime import datetime
from openpyxl import load_workbook


def fill_excel(data: dict, template_path: str, output_path: str) -> str:

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")

    shutil.copy(template_path, output_path)

    try:
        wb = load_workbook(output_path)
        ws = wb.active
    except Exception as e:
        raise ValueError(f"Could not open template: {str(e)}")

    # Consumer Details
    ws["D6"] = data.get("consumer_name", "")

    consumer_no = str(data.get("consumer_no", "")).strip()
    cell = ws["D7"]
    cell.value = consumer_no
    cell.number_format = "@"

    ws["D8"] = float(data.get("fixed_charges") or 130)
    ws["D9"] = data.get("sanctioned_load", "")
    ws["D10"] = data.get("connection_type", "")

    # Monthly Units + Month Names
    monthly = data.get("monthly_units", [])
    if not monthly:
        raise ValueError("No monthly unit data found.")

    fixed_charges = float(data.get("fixed_charges") or 130)
    bill_amount = float(data.get("bill_amount") or 0)
    units_list = [float(m.get("units", 0)) for m in monthly]

    start_row = 15
    for i, entry in enumerate(monthly[:12]):
        row = start_row + i
        try:
            units = float(entry.get("units", 0))
            ws.cell(row=row, column=4, value=units)

            month_str = entry.get("month", "")
            if month_str:
                try:
                    dt = datetime.strptime(month_str[:10], "%Y-%m-%d")
                    ws.cell(row=row, column=3, value=dt.strftime("%b %Y"))
                except:
                    ws.cell(row=row, column=3, value=month_str)
        except Exception as e:
            print(f"Warning: could not fill row {row}: {str(e)}")
            continue

    # Bill Amount + Unit Cost in last month row
    if bill_amount and monthly:
        last_row = start_row + len(monthly) - 1
        last_units = units_list[-1] if units_list[-1] > 0 else 1
        unit_cost = round((bill_amount - fixed_charges) / last_units, 2)
        ws.cell(row=last_row, column=5, value=float(bill_amount))
        ws.cell(row=last_row, column=6, value=float(unit_cost))

    # Row 27 = Average units (formulas in 31-34 depend on this)
    if units_list:
        avg_units = round(sum(units_list) / len(units_list), 2)
        ws["D27"] = avg_units

    try:
        wb.save(output_path)
    except Exception as e:
        raise IOError(f"Could not save file: {str(e)}")

    return output_path


def get_summary_from_excel(data: dict) -> dict:
    try:
        monthly = data.get("monthly_units", [])
        if not monthly:
            return {}

        units_list = [float(m.get("units", 0)) for m in monthly]
        avg_units = sum(units_list) / len(units_list)

        fixed_charges = float(data.get("fixed_charges") or 130)
        bill_amount = float(data.get("bill_amount") or 0)

        kw_required = (avg_units * 12 * 1.1) / 1400
        solar_panels_raw = kw_required / 600 * 1000
        solar_capacity = round(solar_panels_raw, 0) * 600 / 1000
        number_of_panels = int(round(solar_capacity / 600 * 1000, 0))

        last_units = units_list[-1] if units_list[-1] > 0 else avg_units
        unit_cost = 0
        if bill_amount and last_units > 0:
            unit_cost = round((bill_amount - fixed_charges) / last_units, 2)

        yearly_savings = round(avg_units * 12 * unit_cost * 0.9, 0)
        installation_cost = solar_capacity * 45000
        payback_years = round(installation_cost / yearly_savings, 1) if yearly_savings > 0 else 0

        return {
            "avg_units":         round(avg_units, 2),
            "kw_required":       round(kw_required, 3),
            "solar_capacity":    solar_capacity,
            "panels_required":   number_of_panels,
            "bill_amount":       bill_amount,
            "unit_cost":         unit_cost,
            "yearly_savings":    int(yearly_savings),
            "installation_cost": int(installation_cost),
            "payback_years":     payback_years,
        }

    except Exception as e:
        print(f"Warning: summary calculation failed: {str(e)}")
        return {}
