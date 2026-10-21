from pathlib import Path
import pytest
from ticketdesk.sales import Sale, read_sales, summarize_sales, generate_report

def test_total():
    assert Sale("Bút", 2, 10.0).total == 20.0


def test_skip_invalid_row(tmp_path: Path):
    f = tmp_path / "data.csv"
    f.write_text("product,quantity,price\nBút,2,10\nVở,abc,5\nTẩy,3,invalid\n", encoding="utf-8")
    sales = read_sales(f)
    assert len(sales) == 1
    assert sales[0].product == "Bút"


def test_summarize_sales():
    sales = [
        Sale("Bút", 2, 10.0),
        Sale("Bút", 3, 10.0),
        Sale("Vở", 1, 15.0),
    ]
    summary = summarize_sales(sales)
    
    assert summary["Bút"]["total_quantity"] == 5
    assert summary["Bút"]["total_revenue"] == 50.0
    assert summary["Vở"]["total_revenue"] == 15.0


def test_generate_report():
    sales = [Sale("Bút", 2, 10.0)]
    report = generate_report(sales)
    assert "BÁO CÁO DOANH THU" in report
    assert "Bút" in report
    assert "20.00" in report