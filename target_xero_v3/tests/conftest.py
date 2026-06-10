import pytest

from target_xero_v3.tests.fixtures.mappers import (
    CUSTOMER_RECORD,
    EXISTING_CUSTOMER_REFERENCE,
    EXISTING_VENDOR_REFERENCE,
    VENDOR_RECORD,
)


@pytest.fixture
def customer_record():
    return dict(CUSTOMER_RECORD)


@pytest.fixture
def vendor_record():
    return dict(VENDOR_RECORD)


@pytest.fixture
def empty_reference_data():
    return {
        "Customers": [],
        "Vendors": [],
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
