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


from build_moodboard_html import select_template, TEMPLATES


def test_anchor_left_selected_for_2_to_6():
    for n in [2, 3, 4, 5, 6]:
        assert select_template(n) == 'anchor-left', f"n={n}"


def test_collage_selected_for_7_plus():
    for n in [7, 8, 9, 10, 15]:
        assert select_template(n) == 'collage', f"n={n}"


def test_feature_top_override():
    assert select_template(5, override='feature-top') == 'feature-top'


def test_templates_have_required_keys():
    for name, tmpl in TEMPLATES.items():
        assert 'css_columns' in tmpl, name
        assert 'css_rows' in tmpl, name
        assert 'slots' in tmpl, name
        for slot in tmpl['slots']:
            assert 'col' in slot, f"{name} slot missing col"
            assert 'row' in slot, f"{name} slot missing row"
            assert 'size_rank' in slot, f"{name} slot missing size_rank"


def test_anchor_left_has_6_slots():
    assert len(TEMPLATES['anchor-left']['slots']) == 6


def test_collage_has_9_slots():
    assert len(TEMPLATES['collage']['slots']) == 9


def test_feature_top_has_5_slots():
    assert len(TEMPLATES['feature-top']['slots']) == 5
