import argparse
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
    """Đọc và phân tích file CSV chứa dữ liệu bán hàng."""
    sales: list[Sale] = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                sales.append(
                    Sale(
                        product=row["product"],
                        quantity=int(row["quantity"]),
                        price=float(row["price"]),
                    )
                )
            except (KeyError, ValueError) as exc:
                logger.warning("Bỏ qua dòng lỗi %s: %s", row, exc)
    return sales


def summarize_sales(sales: list[Sale]) -> dict[str, dict[str, float | int]]:
    """Tổng hợp số lượng và doanh thu theo từng sản phẩm."""
    summary: dict[str, dict[str, float | int]] = {}
    for sale in sales:
        if sale.product not in summary:
            summary[sale.product] = {"total_quantity": 0, "total_revenue": 0.0}
        summary[sale.product]["total_quantity"] = int(summary[sale.product]["total_quantity"]) + sale.quantity
        summary[sale.product]["total_revenue"] = float(summary[sale.product]["total_revenue"]) + sale.total
    return summary


def generate_report(sales: list[Sale]) -> str:
    """Tạo báo cáo dạng văn bản từ danh sách giao dịch."""
    summary = summarize_sales(sales)
    
    lines = [
        "========================================",
        "          BÁO CÁO DOANH THU BÁN HÀNG      ",
        "========================================",
        f"{'Sản phẩm':<20} | {'SL':<6} | {'Doanh thu':<10}",
        "-" * 42,
    ]
    
    grand_total = 0.0
    for product, data in summary.items():
        qty = data["total_quantity"]
        revenue = data["total_revenue"]
        grand_total += float(revenue)
        lines.append(f"{product:<20} | {qty:<6} | {revenue:<10.2f}")
        
    lines.append("-" * 42)
    lines.append(f"Tổng doanh thu toàn hệ thống: {grand_total:.2f}")
    lines.append("========================================")
    
    return "\n".join(lines)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    parser = argparse.ArgumentParser(description="CLI phân tích và báo cáo doanh thu từ file CSV.")
    parser.add_argument("file", type=Path, help="Đường dẫn tới file CSV dữ liệu bán hàng")
    args = parser.parse_args()

    if not args.file.exists():
        logger.error("Không tìm thấy file tại đường dẫn: %s", args.file)
        return

    sales = read_sales(args.file)
    if not sales:
        logger.warning("Không có dữ liệu hợp lệ nào được tải.")
        return

    report = generate_report(sales)
    print(report)


if __name__ == "__main__":
    main()