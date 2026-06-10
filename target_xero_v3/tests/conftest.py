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
    return {"Customers": [], "Vendors": []}


@pytest.fixture
def customer_reference_data(existing_customer_reference):
    return {"Customers": [existing_customer_reference], "Vendors": []}


@pytest.fixture
def vendor_reference_data(existing_vendor_reference):
    return {"Customers": [], "Vendors": [existing_vendor_reference]}


@pytest.fixture
def existing_customer_reference():
    return dict(EXISTING_CUSTOMER_REFERENCE)


@pytest.fixture
def existing_vendor_reference():
    return dict(EXISTING_VENDOR_REFERENCE)
