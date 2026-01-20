import pytest

from src.fb_ads import extract_domain


def test_extract_domain_simple():
    assert extract_domain("https://glossybrand.com/shop") == "glossybrand.com"


def test_extract_domain_with_www():
    assert extract_domain("https://www.example.com/page") == "example.com"


def test_extract_domain_with_subdomain():
    assert extract_domain("https://shop.mystore.com/products") == "shop.mystore.com"


def test_extract_domain_invalid_url():
    assert extract_domain("not a url") is None
    assert extract_domain("") is None
