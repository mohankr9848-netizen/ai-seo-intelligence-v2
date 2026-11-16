from modules.crawler import extract_page

def test_nested_svg_image_does_not_crash():
    html = '<html><head><title>Test</title></head><body><svg><image/><img alt=""/></svg><img alt="Good"><img></body></html>'
    page = extract_page("https://example.com/", html, 200)
    assert page["image_count"] == 3
    assert page["missing_alt"] == 2

def test_regular_images_and_empty_alt():
    html = '<html><body><img alt=""><img alt="Descriptive"><img></body></html>'
    page = extract_page("https://example.com/", html, 200)
    assert page["image_count"] == 3
    assert page["missing_alt"] == 2
