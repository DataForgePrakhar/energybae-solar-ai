"""
customers.py
Stores customer data persistently in JSON.
Supports save, load, update, delete.
"""

import json
import os
from datetime import datetime

CUSTOMERS_FILE = "customers.json"


def save_customer(data: dict, summary: dict, filename: str) -> str:
    """Save or update customer record. Returns customer ID."""
    try:
        customers = load_all_customers()

        # Use consumer_no as unique ID
        customer_id = str(data.get("consumer_no", "")).strip()
        if not customer_id:
            customer_id = datetime.now().strftime("%Y%m%d%H%M%S")

        record = {
            "id":              customer_id,
            "consumer_name":   data.get("consumer_name", ""),
            "consumer_no":     str(data.get("consumer_no", "")),
            "fixed_charges":   data.get("fixed_charges", 130),
            "sanctioned_load": data.get("sanctioned_load", ""),
            "connection_type": data.get("connection_type", ""),
            "bill_amount":     data.get("bill_amount", 0),
            "monthly_units":   data.get("monthly_units", []),
            "solar_capacity":  summary.get("solar_capacity", 0),
            "panels_required": summary.get("panels_required", 0),
            "avg_units":       summary.get("avg_units", 0),
            "yearly_savings":  summary.get("yearly_savings", 0),
            "payback_years":   summary.get("payback_years", 0),
            "latest_file":     filename,
            "last_updated":    datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "created_at":      datetime.now().strftime("%d %b %Y, %I:%M %p"),
        }

        # Update if exists, else add new
        existing = next((i for i, c in enumerate(customers)
                        if c.get("id") == customer_id), None)
        if existing is not None:
            record["created_at"] = customers[existing].get("created_at", record["created_at"])
            customers[existing] = record
        else:
            customers.insert(0, record)

        with open(CUSTOMERS_FILE, "w") as f:
            json.dump(customers, f, indent=2)

        return customer_id

    except Exception as e:
        print(f"Warning: Could not save customer: {str(e)}")
        return ""


def load_all_customers() -> list:
    """Load all customers."""
    try:
        if not os.path.exists(CUSTOMERS_FILE):
            return []
        with open(CUSTOMERS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def load_customer(customer_id: str) -> dict:
    """Load single customer by ID."""
    customers = load_all_customers()
    return next((c for c in customers if c.get("id") == customer_id), None)


def update_customer(customer_id: str, updated_data: dict) -> bool:
    """Update customer fields."""
    try:
        customers = load_all_customers()
        for i, c in enumerate(customers):
            if c.get("id") == customer_id:
                customers[i].update(updated_data)
                customers[i]["last_updated"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
                with open(CUSTOMERS_FILE, "w") as f:
                    json.dump(customers, f, indent=2)
                return True
        return False
    except Exception as e:
        print(f"Warning: Could not update customer: {str(e)}")
        return False


def delete_customer(customer_id: str) -> bool:
    """Delete customer record."""
    try:
        customers = load_all_customers()
        customers = [c for c in customers if c.get("id") != customer_id]
        with open(CUSTOMERS_FILE, "w") as f:
            json.dump(customers, f, indent=2)
        return True
    except Exception as e:
        print(f"Warning: Could not delete customer: {str(e)}")
        return False