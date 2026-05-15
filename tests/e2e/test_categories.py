"""
E2E tests for child category display in trader-cms.

Verifies that categories created as children in tradeops appear correctly:
  - Settings page: child categories are indented under their parents
  - Browse page: category dropdown groups children under parent optgroups
  - Browse page: products assigned to child categories are visible
"""
import pytest
from playwright.sync_api import Page, expect


def test_settings_shows_parent_categories(logged_in_page: Page, cms_url: str):
    """Root categories appear on the settings/categories page."""
    logged_in_page.goto(f"{cms_url}/settings/categories")
    expect(logged_in_page.locator('label:has-text("Electronics")')).to_be_visible()
    expect(logged_in_page.locator('label:has-text("Clothing")')).to_be_visible()


def test_settings_shows_child_categories(logged_in_page: Page, cms_url: str):
    """Child categories appear on the settings/categories page (previously missing)."""
    logged_in_page.goto(f"{cms_url}/settings/categories")
    expect(logged_in_page.locator('label:has-text("Phones")')).to_be_visible()
    expect(logged_in_page.locator('label:has-text("Laptops")')).to_be_visible()
    expect(logged_in_page.locator('label:has-text("T-Shirts")')).to_be_visible()


def test_settings_child_categories_are_indented(logged_in_page: Page, cms_url: str):
    """Child category checkboxes are indented (ms-4 class) relative to their parent."""
    logged_in_page.goto(f"{cms_url}/settings/categories")
    phones = logged_in_page.locator('.form-check.ms-4:has(label:has-text("Phones"))')
    expect(phones).to_be_visible()

    laptops = logged_in_page.locator('.form-check.ms-4:has(label:has-text("Laptops"))')
    expect(laptops).to_be_visible()

    # Root categories must NOT be indented
    electronics = logged_in_page.locator('.form-check:not(.ms-4):has(label:has-text("Electronics"))')
    expect(electronics).to_be_visible()


def test_settings_child_categories_have_arrow_prefix(logged_in_page: Page, cms_url: str):
    """Child category labels are prefixed with ↳ to signal hierarchy."""
    logged_in_page.goto(f"{cms_url}/settings/categories")
    phones_label = logged_in_page.locator('.form-check.ms-4 label:has-text("Phones")')
    expect(phones_label).to_contain_text("↳")


def test_browse_category_dropdown_has_optgroups(logged_in_page: Page, cms_url: str):
    """Browse page category dropdown groups child categories under parent optgroups."""
    logged_in_page.goto(f"{cms_url}/products/browse")
    select = logged_in_page.locator('#category-filter')
    expect(select).to_be_visible()

    # Wait for JS to populate the dropdown
    logged_in_page.wait_for_function(
        "document.querySelector('#category-filter optgroup') !== null",
        timeout=10_000,
    )

    electronics_group = logged_in_page.locator('optgroup[label="Electronics"]')
    expect(electronics_group).to_be_visible()

    clothing_group = logged_in_page.locator('optgroup[label="Clothing"]')
    expect(clothing_group).to_be_visible()


def test_browse_child_categories_inside_optgroup(logged_in_page: Page, cms_url: str):
    """Phones and Laptops appear as options inside the Electronics optgroup."""
    logged_in_page.goto(f"{cms_url}/products/browse")
    logged_in_page.wait_for_function(
        "document.querySelector('#category-filter optgroup') !== null",
        timeout=10_000,
    )

    phones = logged_in_page.locator('optgroup[label="Electronics"] option:has-text("Phones")')
    expect(phones).to_have_count(1)

    laptops = logged_in_page.locator('optgroup[label="Electronics"] option:has-text("Laptops")')
    expect(laptops).to_have_count(1)


def test_browse_products_in_child_categories_are_shown(logged_in_page: Page, cms_url: str):
    """Products assigned to child categories appear in the browse grid."""
    logged_in_page.goto(f"{cms_url}/products/browse")

    # Wait for product cards to load (spinner disappears)
    logged_in_page.wait_for_selector('.product-card', timeout=15_000)

    expect(logged_in_page.locator('.product-card:has-text("iPhone 15")')).to_be_visible()
    expect(logged_in_page.locator('.product-card:has-text("MacBook Pro")')).to_be_visible()
    expect(logged_in_page.locator('.product-card:has-text("Basic Tee")')).to_be_visible()


def test_browse_product_shows_child_category_name(logged_in_page: Page, cms_url: str):
    """Product cards display the child category name, not a raw ID."""
    logged_in_page.goto(f"{cms_url}/products/browse")
    logged_in_page.wait_for_selector('.product-card', timeout=15_000)

    iphone_card = logged_in_page.locator('.product-card:has-text("iPhone 15")')
    expect(iphone_card).to_contain_text("Phones")
