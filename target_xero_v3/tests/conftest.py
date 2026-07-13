import pytest

from target_xero_v3.tests.fixtures.mappers import (
    CLASS_RECORD,
    CUSTOMER_RECORD,
    EXISTING_CLASS_REFERENCE,
    EXISTING_CUSTOMER_REFERENCE,
    EXISTING_ITEM_REFERENCE,
    EXISTING_VENDOR_REFERENCE,
    ITEM_RECORD,
    TRACKING_CATEGORY_REFERENCE,
    VENDOR_RECORD,
)


@pytest.fixture
def customer_record():
    return dict(CUSTOMER_RECORD)


@pytest.fixture
def vendor_record():
    return dict(VENDOR_RECORD)


@pytest.fixture
def item_record():
    return dict(ITEM_RECORD)


@pytest.fixture
def class_record():
    return dict(CLASS_RECORD)


@pytest.fixture
def empty_reference_data():
    return {
        "Customers": [],
        "Vendors": [],
        "Items": [],
        "Classes": [],
        "Accounts": [
            {"AccountID": "00000000-0000-4000-8000-0000000000a1", "Code": "200", "Name": "Sales"},
            {"AccountID": "00000000-0000-4000-8000-0000000000a2", "Code": "400", "Name": "Advertising"},
        ],
        "Currencies": [{"Code": "USD", "Description": "United States Dollar"}],
        "Organisation": [{"BaseCurrency": "USD"}],
    }


@pytest.fixture
def customer_reference_data(existing_customer_reference, empty_reference_data):
    return {**empty_reference_data, "Customers": [existing_customer_reference]}


@pytest.fixture
def vendor_reference_data(existing_vendor_reference, empty_reference_data):
    return {**empty_reference_data, "Vendors": [existing_vendor_reference]}


@pytest.fixture
def existing_customer_reference():
    return dict(EXISTING_CUSTOMER_REFERENCE)


@pytest.fixture
def existing_vendor_reference():
    return dict(EXISTING_VENDOR_REFERENCE)


@pytest.fixture
def item_reference_data(existing_item_reference, empty_reference_data):
    return {**empty_reference_data, "Items": [existing_item_reference]}


@pytest.fixture
def existing_item_reference():
    return dict(EXISTING_ITEM_REFERENCE)


@pytest.fixture
def class_reference_data(existing_class_reference, empty_reference_data):
    return {
        **empty_reference_data,
        "Classes": [existing_class_reference],
        "TrackingCategory": dict(TRACKING_CATEGORY_REFERENCE),
    }


@pytest.fixture
def existing_class_reference():
    return dict(EXISTING_CLASS_REFERENCE)
