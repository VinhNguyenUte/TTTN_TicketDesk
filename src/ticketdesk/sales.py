import csv
import logging
from dataclasses import dataclass
from pathlib import Path
 
logger = logging.getLogger(__name__)
 
 
@dataclass
class Sale:
    product: str
    quantity: int
    price: float
 
    @property
    def total(self) -> float:
        return self.quantity * self.price
 
 
def read_sales(path: Path) -> list[Sale]:
    sales: list[Sale] = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                sales.append(Sale(row["product"], int(row["quantity"]), float(row["price"])))
            except (KeyError, ValueError) as exc:
                logger.warning("Bỏ qua dòng lỗi %s: %s", row, exc)
    return sales
