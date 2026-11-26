import pytest

from modellab.textnorm_vi import normalize, read_number


@pytest.mark.parametrize("n, dialect, expected", [
    (0, "north", "không"),
    (10, "north", "mười"),
    (11, "north", "mười một"),
    (15, "north", "mười lăm"),
    (21, "north", "hai mươi mốt"),
    (24, "north", "hai mươi tư"),
    (24, "south", "hai mươi bốn"),
    (25, "north", "hai mươi lăm"),
    (100, "north", "một trăm"),
    (105, "north", "một trăm linh năm"),
    (105, "south", "một trăm lẻ năm"),
    (110, "north", "một trăm mười"),
    (1000, "north", "một nghìn"),
    (1000, "south", "một ngàn"),
    (1005, "north", "một nghìn không trăm linh năm"),
    (2026, "north", "hai nghìn không trăm hai mươi sáu"),
    (1_500_000, "north", "một triệu năm trăm nghìn"),
    (1_005_000, "north", "một triệu không trăm linh năm nghìn"),
    (1_250_000_000, "north", "một tỷ hai trăm năm mươi triệu"),
])
def test_read_number(n, dialect, expected):
    assert read_number(n, dialect) == expected


@pytest.mark.parametrize("text, expected", [
    ("Giá 1.500.000đ", "Giá một triệu năm trăm nghìn đồng"),
    ("Tăng 12,5%", "Tăng mười hai phẩy năm phần trăm"),
    ("Lãi 3,05 tr", "Lãi ba phẩy không năm triệu"),
    ("Ở TP.HCM, 50k một ly", "Ở thành phố Hồ Chí Minh, năm mươi nghìn một ly"),
    ("Chỉ $20 thôi", "Chỉ hai mươi đô la thôi"),
    ("Mất 5-10 phút", "Mất năm đến mười phút"),
    ("Họp lúc 9:30", "Họp lúc chín giờ ba mươi phút"),
    ("Họp lúc 9:00", "Họp lúc chín giờ"),
    ("Ngày 1/4", "Ngày mùng một tháng tư"),
    ("Họp ngày 25/11/2026", "Họp ngày hai mươi lăm tháng mười một năm hai nghìn không trăm hai mươi sáu"),
    ("Doanh thu tháng 4", "Doanh thu tháng tư"),
    ("Sau 4 tháng", "Sau bốn tháng"),
    ("iPhone 15 và 3G", "iPhone mười lăm và 3G"),
])
def test_normalize_north(text, expected):
    assert normalize(text) == expected


def test_south_dialect_changes_readings():
    assert normalize("Giá 1.005 ngàn", "south") == "Giá một ngàn không trăm lẻ năm ngàn"


def test_bad_dialect_rejected():
    with pytest.raises(ValueError):
        normalize("1", dialect="central")
