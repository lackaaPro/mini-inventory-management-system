from pydantic import BaseModel
from typing import Literal
from datetime import datetime, timedelta
import logging

class Product(BaseModel):
    product_id: str
    name: str
    stock_quantity: int
    min_threshold: int
    restock_quantity: int
    priority: Literal["low", "medium", "high"]
    category: str | None = None  # Auto
    

class ProductResponse(BaseModel):
    product_id: str
    #name: str
    stock_quantity: int
    #min_threshold: int
    #restock_quantity: int
    status: Literal["ok", "below_threshold", "out_of_stock"]  # Dynamic 
    priority: Literal["low", "medium", "high"]
    #category: str | None = None  # Auto
 
class ProductRestock(BaseModel):
    product_id: str
    name: str
    stock_quantity: int
    min_threshold: int      # Minimum stock level before restocking
    restock_quantity: int   # Default units to add
    priority: Literal["low", "medium", "high"]

class PurchaseRequest(BaseModel):
    quantity: int # Quantity to purchase