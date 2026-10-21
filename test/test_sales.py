# tests/test_sales.py
from pathlib import Path
from sales import Sale, read_sales
 
 
def test_total():
    assert Sale("Bút", 2, 10.0).total == 20.0
 
 
def test_skip_invalid_row(tmp_path: Path):
    f = tmp_path / "data.csv"
    f.write_text("product,quantity,price\nBút,2,10\nVở,abc,5\n", encoding="utf-8")
    assert len(read_sales(f)) == 1
 
