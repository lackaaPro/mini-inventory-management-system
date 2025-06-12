from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional
import json
import os
from pathlib import Path
import logging
from typing import Dict

from schema import ProductRestock,Product

app = FastAPI()

inventory = {}

JSON_FILE = "inventory.json"

def load_inventory() -> dict: #Load inventory data from JSON file and Return empty dict if file doesn't exist.
    if not Path(JSON_FILE).exists():
        return {}
    with open(JSON_FILE, "r") as file:
        return json.load(file)

def save_inventory(data: dict) -> None:# Save inventory --> JSON file.

    with open(JSON_FILE, "w") as file:
        json.dump(data, file, indent=4)


def auto_restock(product: dict) -> int:

    try:
        required_fields = ['priority', 'stock_quantity', 'min_threshold', 'restock_quantity'] # Validate required fields
        if not all(field in product for field in required_fields):
            missing = [f for f in required_fields if f not in product]
            raise ValueError(f"Missing fields in product data: {missing}")

        
        if product["priority"] == "high" and product["stock_quantity"] < product["min_threshold"]: #50% extra if below threshold
            return int(product["restock_quantity"] * 1.5)
        
        elif product["priority"] == "medium" and product["stock_quantity"] < (product["min_threshold"] * 0.7):# below 70% of threshold
            return product["restock_quantity"]
        
        # Low-priority: Restock only when empty (max 10 units)
        elif product["priority"] == "low" and product["stock_quantity"] == 0:#when empty and max 
            return min(product["restock_quantity"], 10)
        
        return 0  # No restock needed

    except KeyError as e:
        raise ValueError(f"Invalid product data structure: {str(e)}")
    except Exception as e:
        raise ValueError(f"Restock calculation failed: {str(e)}")
    
def validate_product(product: dict) -> bool:
    required_fields = { #feilds with vaild types
        'product_id': str,
        'name': str,
        'stock_quantity': int,
        'min_threshold': int,
        'restock_quantity': int,
        'priority': str,
        'category': str
    }
    
    
    if not all(field in product for field in required_fields):
        return False
        
    
    if product['priority'] not in ['low', 'medium', 'high']:
        return False
        
    if product['stock_quantity'] < 0 or product['min_threshold'] < 0 or product['restock_quantity'] < 0: #for positive values
        return False
        
    return True