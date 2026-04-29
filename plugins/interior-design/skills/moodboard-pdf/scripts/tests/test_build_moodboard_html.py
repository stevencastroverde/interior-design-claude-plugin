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


from build_moodboard_html import assign_products_to_slots


def _make_products(specs):
    """specs: list of (title, category_or_None)"""
    return [{'title': t, 'category': c} for t, c in specs]


def test_furniture_lands_in_size_rank_1_slot():
    products = _make_products([
        ('Porto Sofa', 'furniture'),
        ('Ceramic Vase', 'accessory'),
        ('Woven Pendant', 'lighting'),
        ('Marble Table', 'furniture'),
    ])
    assignments = assign_products_to_slots(products, 'anchor-left')
    # slot index 0 is size_rank=1 (hero) — should hold a furniture product
    hero_title = assignments[0]['title']
    assert hero_title in ('Porto Sofa', 'Marble Table')


def test_dark_slots_receive_no_product():
    products = _make_products([('Sofa', 'furniture')] * 5)
    assignments = assign_products_to_slots(products, 'anchor-left')
    # slot index 1 is dark=True in anchor-left — should be None
    assert assignments[1] is None


def test_fewer_products_than_slots_pads_with_none():
    products = _make_products([('Sofa', 'furniture'), ('Vase', 'accessory')])
    assignments = assign_products_to_slots(products, 'anchor-left')
    assert len(assignments) == 6  # anchor-left has 6 slots
    none_count = sum(1 for a in assignments if a is None)
    assert none_count >= 4  # at least 4 empty (1 dark + 3 unfilled)


def test_returns_one_entry_per_slot():
    products = _make_products([('Sofa', 'furniture')] * 9)
    assignments = assign_products_to_slots(products, 'collage')
    assert len(assignments) == 9


import tempfile, os
from PIL import Image as PILImage
from build_moodboard_html import image_to_data_uri


def test_returns_data_uri_for_valid_image(tmp_path):
    img = PILImage.new('RGB', (10, 10), color=(200, 180, 160))
    p = tmp_path / 'test.jpg'
    img.save(str(p), 'JPEG')
    uri = image_to_data_uri(str(p))
    assert uri.startswith('data:image/jpeg;base64,')


def test_returns_placeholder_for_missing_file():
    uri = image_to_data_uri('/nonexistent/path/img.jpg')
    assert uri == ''


def test_returns_empty_string_for_none():
    assert image_to_data_uri(None) == ''


from build_moodboard_html import render_moodboard_html


def _sample_room():
    return {
        'name': 'LIVING ROOM',
        'subtitle': 'living room',
        'products': [
            {'title': 'Porto Sectional', 'category': 'furniture', 'img': None},
            {'title': 'Brass Pendant',   'category': 'lighting',  'img': None},
            {'title': 'Ceramic Vase',    'category': 'accessory', 'img': None},
            {'title': 'Wool Rug',        'category': 'textile',   'img': None},
        ],
    }


def test_render_returns_html_string():
    html = render_moodboard_html(_sample_room(), template_name='anchor-left')
    assert isinstance(html, str)
    assert '<html' in html


def test_render_includes_room_heading():
    html = render_moodboard_html(_sample_room(), template_name='anchor-left')
    assert 'living room' in html.lower()


def test_render_includes_css_grid():
    html = render_moodboard_html(_sample_room(), template_name='anchor-left')
    assert 'display: grid' in html or 'display:grid' in html


def test_render_includes_palette_strip_when_palette_given():
    html = render_moodboard_html(
        _sample_room(), template_name='anchor-left',
        palette=['#3D3530', '#EAE5DC', '#C07C60']
    )
    assert '#3D3530' in html
    assert 'palette-strip' in html


def test_render_no_palette_strip_when_not_given():
    html = render_moodboard_html(_sample_room(), template_name='anchor-left')
    assert 'palette-strip' not in html


def test_render_dark_slot_uses_dark_bg():
    html = render_moodboard_html(_sample_room(), template_name='anchor-left')
    assert '#1C1E18' in html or '1c1e18' in html.lower()
