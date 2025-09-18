from pydantic import BaseModel
from typing import Optional

# Base para la creación y actualización de productos.
class ProductBase(BaseModel):
    name: str
    price: float
    stock: int

# Schema para la creación de un nuevo producto.
class ProductCreate(ProductBase):
    pass

# Schema para la actualización de un producto (campos opcionales).
class ProductUpdate(ProductBase):
    name: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None

# Schema para la representación de un producto en la API.
class Product(ProductBase):
    id: int
    
    # Esto es necesario para que Pydantic pueda leer los datos
    # de los objetos de SQLAlchemy.
    class Config:
        from_attributes = True