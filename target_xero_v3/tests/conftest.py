import pytest

from target_xero_v3.tests.fixtures.mappers import (
    BILL_EXPENSE_RECORD,
    BILL_LINE_ITEM_RECORD,
    BILL_PAYMENT_RECORD,
    BILL_RECORD,
    CLASS_RECORD,
    CUSTOMER_RECORD,
    EXISTING_BILL_REFERENCE,
    EXISTING_CLASS_REFERENCE,
    EXISTING_CUSTOMER_REFERENCE,
    EXISTING_INVOICE_REFERENCE,
    EXISTING_ITEM_REFERENCE,
    EXISTING_JOURNAL_REFERENCE,
    EXISTING_VENDOR_REFERENCE,
    INVOICE_LINE_ITEM_RECORD,
    INVOICE_PAYMENT_RECORD,
    INVOICE_RECORD,
    ITEM_RECORD,
    JOURNAL_ENTRY_RECORD,
    LOCATION_TRACKING_CATEGORY_REFERENCE,
    PAYMENT_BANK_ACCOUNT,
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
def bill_record():
    return dict(BILL_RECORD)


@pytest.fixture
def bill_line_item_record():
    return dict(BILL_LINE_ITEM_RECORD)


@pytest.fixture
def bill_expense_record():
    return dict(BILL_EXPENSE_RECORD)


@pytest.fixture
def class_record():
    return dict(CLASS_RECORD)


@pytest.fixture
def invoice_record():
    return dict(INVOICE_RECORD)


@pytest.fixture
def invoice_line_item_record():
    return dict(INVOICE_LINE_ITEM_RECORD)


@pytest.fixture
def empty_reference_data():
    return {
        "Customers": [],
        "Vendors": [],
        "Items": [],
        "Classes": [],
        "Invoices": [],
        "Bills": [],
        "Accounts": [
            {"AccountID": "00000000-0000-4000-8000-0000000000a1", "Code": "200", "Name": "Sales"},
            {"AccountID": "00000000-0000-4000-8000-0000000000a2", "Code": "400", "Name": "Advertising"},
            dict(PAYMENT_BANK_ACCOUNT),
        ],
        "Currencies": [{"Code": "USD", "Description": "United States Dollar"}],
        "Organisation": [{"BaseCurrency": "USD"}],
        "tenant_config": {
            "xero": {
                "dimension_mappings": {
                    "class": "Classes",
                    "location": "Locations",
                }
            }
        },
        "TrackingCategories": [
            dict(TRACKING_CATEGORY_REFERENCE),
            dict(LOCATION_TRACKING_CATEGORY_REFERENCE),
        ],
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


@pytest.fixture
def invoice_reference_data(existing_invoice_reference, existing_customer_reference, existing_item_reference, empty_reference_data):
    return {
        **empty_reference_data,
        "Invoices": [existing_invoice_reference],
        "Customers": [existing_customer_reference],
        "Items": [existing_item_reference],
    }


@pytest.fixture
def existing_invoice_reference():
    return dict(EXISTING_INVOICE_REFERENCE)


@pytest.fixture
def bill_reference_data(existing_bill_reference, existing_vendor_reference, existing_item_reference, empty_reference_data):
    return {
        **empty_reference_data,
        "Bills": [existing_bill_reference],
        "Vendors": [existing_vendor_reference],
        "Items": [existing_item_reference],
    }


@pytest.fixture
def existing_bill_reference():
    return dict(EXISTING_BILL_REFERENCE)


@pytest.fixture
def invoice_payment_record():
    return dict(INVOICE_PAYMENT_RECORD)


@pytest.fixture
def bill_payment_record():
    return dict(BILL_PAYMENT_RECORD)


@pytest.fixture
def payment_bank_account():
    return dict(PAYMENT_BANK_ACCOUNT)


@pytest.fixture
def invoice_payment_reference_data(existing_invoice_reference, payment_bank_account, empty_reference_data):
    return {
        **empty_reference_data,
        "Invoices": [existing_invoice_reference],
        "Accounts": empty_reference_data["Accounts"],
    }


@pytest.fixture
def bill_payment_reference_data(existing_bill_reference, payment_bank_account, empty_reference_data):
    return {
        **empty_reference_data,
        "Bills": [existing_bill_reference],
        "Accounts": empty_reference_data["Accounts"],
    }


@pytest.fixture
def journal_entry_record():
    return dict(JOURNAL_ENTRY_RECORD)


@pytest.fixture
def existing_journal_reference():
    return dict(EXISTING_JOURNAL_REFERENCE)


@pytest.fixture
def journal_reference_data(existing_journal_reference, empty_reference_data):
    return {
        **empty_reference_data,
        "JournalEntries": [existing_journal_reference],
    }
