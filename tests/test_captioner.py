from sitemap.captioner import generate_caption
from sitemap.crawler import should_exclude
from sitemap.gsc_enricher import derive_priority


def test_homepage_banner():
    assert generate_caption(
        'https://www.salasarservices.com/assets/upload/Banner-Image/abc.jpg', '/'
    ) == 'Salasar Services Insurance Brokers - Pan-India Insurance Brokerage Solutions'


def test_aviation_product():
    assert generate_caption(
        'https://www.salasarservices.com/assets/upload/product-image/xyz.jpg',
        '/corporate/aviation-aerospace-insurance'
    ) == 'Aviation & Aerospace Insurance - Aircraft Hull, Liability & Spares | Salasar Services'


def test_client_image_fallback():
    result = generate_caption(
        'https://www.salasarservices.com/assets/upload/client-image/abc.jpg',
        '/some/unknown/page'
    )
    assert 'Salasar Services' in result


def test_blog_image_uses_filename():
    result = generate_caption(
        'https://www.salasarservices.com/blog/wp-content/uploads/2025/07/next-gen-insurtech-ai-agent-in-insurance.png',
        '/'
    )
    assert 'Next Gen Insurtech Ai Agent In Insurance' in result


def test_exclusions():
    assert should_exclude('https://www.salasarservices.com/assets/upload/client-image/-') is True
    assert should_exclude('https://www.salasarservices.com/assets/Frontend/images/upload-notes.png') is True
    assert should_exclude('https://www.salasarservices.com/linkedin.com/in/someone') is True
    assert should_exclude('https://www.salasarservices.com/corporate/aviation-aerospace-insurance') is False


def test_priority_logic():
    assert derive_priority(0,    is_homepage=True)  == 1.0
    assert derive_priority(6000, is_homepage=False) == 0.9
    assert derive_priority(1500, is_homepage=False) == 0.8
    assert derive_priority(300,  is_homepage=False) == 0.7
    assert derive_priority(75,   is_homepage=False) == 0.6
    assert derive_priority(10,   is_homepage=False) == 0.5
