
from typing import List
from pydantic import BaseModel, Field


def normalize_price(price_str: str) -> float:
    """
    Converts European and formatted price strings into floats.
    Handles '1.759,01', '€50.00', and '1,500.00'.
    """
    if not price_str:
        return 0.0
        
    price_str = str(price_str).replace('€', '').replace('EUR', '').strip()
    
    # Handle European format: 1.234,56 -> 1234.56
    if ',' in price_str and '.' in price_str:
        if price_str.rfind('.') < price_str.rfind(','):
            price_str = price_str.replace('.', '').replace(',', '.')
        else:
            price_str = price_str.replace(',', '')
    elif ',' in price_str:
        price_str = price_str.replace(',', '.')
    
    try:
        return float(price_str.replace(' ', ''))
    except ValueError:
        return 0.0


class OrderLine(BaseModel):
    """Structure for an individual line item in a procurement offer."""
    description: str = Field(..., description="Product description")
    unit_price: float = Field(..., description="Price per unit")
    amount: float = Field(..., description="Quantity ordered")
    unit: str = Field(..., description="Unit of measure (e.g., Stk)")
    total_price: float = Field(..., description="Line total (price * amount)")


class ProcurementData(BaseModel):
    """Complete structured output for a procurement request."""
    requestor_name: str = Field(default="Vladimir Keil")
    title: str = Field(..., description="Short summary of purchase")
    vendor_name: str = Field(..., description="Supplier name")
    vat_id: str = Field(..., description="Vendor VAT ID")
    total_cost: float = Field(..., description="Net/Gross total cost")
    department: str = Field(default="Operations")
    extracted_description_text: str = Field(..., description="Full text for classification")
    order_lines: List[OrderLine]