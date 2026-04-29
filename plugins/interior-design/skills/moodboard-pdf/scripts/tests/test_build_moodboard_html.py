import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from build_moodboard_html import detect_category


def test_explicit_category_field_wins():
    prod = {'category': 'lighting', 'title': 'Restoration Hardware Sofa'}
    assert detect_category(prod) == 'lighting'


def test_furniture_inferred_from_title():
    for title in ['Porto Sectional', 'Walnut Dining Table', 'Linen Armchair', 'Oak Cabinet']:
        assert detect_category({'title': title}) == 'furniture', title


def test_lighting_inferred_from_title():
    for title in ['Woven Pendant', 'Brass Sconce', 'Arc Floor Lamp', 'Chandelier']:
        assert detect_category({'title': title}) == 'lighting', title


def test_textile_inferred_from_title():
    for title in ['Moroccan Rug', 'Linen Curtain', 'Velvet Pillow', 'Wool Throw']:
        assert detect_category({'title': title}) == 'textile', title


def test_accessory_inferred_from_title():
    for title in ['Ceramic Vase', 'Wooden Bowl', 'Woven Basket', 'Candle']:
        assert detect_category({'title': title}) == 'accessory', title


def test_unknown_title_returns_accessory():
    assert detect_category({'title': 'XYZ-9000'}) == 'accessory'


def test_case_insensitive():
    assert detect_category({'title': 'LINEN SOFA'}) == 'furniture'
