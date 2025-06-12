from fastapi import FastAPI, HTTPException
import logging
from schema import Product, ProductResponse, ProductRestock, PurchaseRequest
from storage import auto_restock, load_inventory, save_inventory

app = FastAPI()

inventory = {}
# Configuring logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@app.post("/products")
async def add_product(product: Product):
    try:
        inventory = load_inventory()  # Load current inventory

        if product.priority == "high" and product.min_threshold < 10: #priortity hingh AND threshold < 10
            logger.info(f"Adjusting min_threshold for product {product.product_id} from {product.min_threshold} to 10")
            product.min_threshold = 10

        product.category = "high_volume" if product.restock_quantity > 50 else "low_volume" #auto assigning category 
        logger.debug(f"Assigned category {product.category} to product {product.product_id}")

        if product.product_id in inventory: #validating the product
            logger.warning(f"Duplicate product ID: {product.product_id}")
            raise HTTPException(status_code=400, detail="Product already exists")
        if product.stock_quantity < 0:
            logger.error(f"Invalid stock quantity {product.stock_quantity} for product {product.product_id}")
            raise HTTPException(status_code=400, detail="Stock cannot be negative")

        inventory[product.product_id] = product.dict() #adding product and save 
        save_inventory(inventory)
        logger.info(f"Added product {product.product_id} successfully")

        return {
            "message": "Product added successfully",
            "product": product,
            "inventory_count": len(inventory)
        }
    except Exception as e:
        logger.error(f"Error adding product: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/products/{product_id}", response_model=ProductResponse) #get status of a product
async def get_product_status(product_id: str):
    try:
        inventory = load_inventory()
        if product_id not in inventory:
            logger.warning(f"Product {product_id} not found")
            raise HTTPException(status_code=404, detail="Product not found")

        product = inventory[product_id]
        
        if product["stock_quantity"] == 0: #checking status
            status = "out_of_stock"
        elif product["stock_quantity"] < product["min_threshold"]:
            status = "below_threshold"
        else:
            status = "ok"

        logger.info(f"Retrieved status for product {product_id}: {status}")
        return {**product, "status": status}
    except Exception as e:
        logger.error(f"Error getting product status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/restock") # Restock all products based on their priority and stock levels
async def restock_all():
    try:
        inventory = load_inventory()
        restocked = {}
        
        for product_id, product_data in inventory.items():
            try:
                amount = auto_restock(product_data)
                if amount > 0:
                    updated_product = product_data.copy() #creating a copy of product data-avoid modification of first data
                    updated_product["stock_quantity"] += amount
                    inventory[product_id] = updated_product
                    restocked[product_id] = {
                        "added": amount,
                        "new_stock": updated_product["stock_quantity"]
                    }
            except ValueError as e:
                logger.error(f"Skipping product {product_id}: {str(e)}")
                continue

        if restocked:
            save_inventory(inventory)
        
        return {
            "message": "Restock completed",
            "restocked_products": restocked,
            "total_restocked": len(restocked),
            "skipped_products": len(inventory) - len(restocked)
        }
    except Exception as e:
        logger.error(f"Restock process failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    

@app.post("/products/{product_id}/purchase") #Purahasing a product by reducing its stock quantity
async def purchase_product(product_id: str, purchase: PurchaseRequest):

    try:
        inventory = load_inventory()
        
        if product_id not in inventory: #checking the product availability
            logger.warning(f"Purchase failed: Product {product_id} not found")
            raise HTTPException(status_code=404, detail="Product not found")

        product = inventory[product_id]
        
        if purchase.quantity <= 0: #validation of purchase quantuty 
            logger.error(f"Invalid purchase quantity {purchase.quantity} for product {product_id}")
            raise HTTPException(status_code=400, detail="Purchase quantity must be positive")
        
        if product["stock_quantity"] < purchase.quantity: #chacking stock availability
            logger.warning(f"Insufficient stock for product {product_id}. Requested: {purchase.quantity}, Available: {product['stock_quantity']}")
            raise HTTPException(
                status_code=400,
                detail=f"Only {product['stock_quantity']} units available"
            )

        # Process purchase
        product["stock_quantity"] -= purchase.quantity #purchaing
        inventory[product_id] = product
        save_inventory(inventory)
        
        logger.info(f"Purchased {purchase.quantity} units of {product_id}. Remaining stock: {product['stock_quantity']}")
        
        status = "out_of_stock" if product["stock_quantity"] == 0 else \
                 "below_threshold" if product["stock_quantity"] < product["min_threshold"] else \
                 "ok"
        #checking status after purchase
        return {
            "message": "Purchase successful",
            "product_id": product_id,
            "purchased_quantity": purchase.quantity,
            "remaining_stock": product["stock_quantity"],
            "new_status": status
        }
        
    except Exception as e:
        logger.error(f"Purchase failed for product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")