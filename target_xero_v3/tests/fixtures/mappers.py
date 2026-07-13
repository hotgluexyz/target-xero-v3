"""Fixtures for mapper unit tests."""

CUSTOMER_RECORD = {
    "externalId": "FAKE-CUSTOMER-EXT-001",
    "customerNumber": "FAKE-CUST-NUM-001",
    "companyName": "Fake Customer Co (Sample)",
    "email": "fake.customer@example.invalid",
    "phoneNumbers": [
        {"type": "mobile", "phoneNumber": "+15555550100"},
        {"type": "unknown", "phoneNumber": "+15555550101"},
    ],
    "subsidiaryId": "00000000-0000-4000-8000-000000000001",
    "addresses": [
        {
            "addressType": "shipping",
            "line1": "123 Fake Shipping Lane",
            "line2": "Suite FAKE",
            "line3": "Floor 9",
            "city": "Faketown",
            "state": "FK",
            "postalCode": "00001",
            "country": "US",
        },
        {
            "addressType": "billing",
            "line1": "456 Fake Billing Road",
            "line2": "Unit TEST",
            "line3": "Floor 1",
            "city": "Faketown",
            "state": "FK",
            "postalCode": "00002",
            "country": "US",
        },
    ],
    "currency": "USD",
}

VENDOR_RECORD = {
    "externalId": "FAKE-VENDOR-EXT-001",
    "vendorNumber": "FAKE-VEND-NUM-001",
    "vendorName": "Fake Vendor LLC (Sample)",
    "email": "fake.vendor@example.invalid",
    "subsidiaryId": "00000000-0000-4000-8000-000000000002",
    "phoneNumbers": [{"type": "unknown", "phoneNumber": "+15555550200"}],
    "addresses": [
        {
            "addressType": "billing",
            "line1": "789 Not A Real Avenue",
            "line2": None,
            "city": "Fakeville",
            "state": "FK",
            "postalCode": "00003",
            "country": "US",
        },
        {
            "addressType": "shipping",
            "line1": "789 Not A Real Avenue",
            "line2": None,
            "city": "Fakeville",
            "state": "FK",
            "postalCode": "00003",
            "country": "US",
        },
    ],
    "currency": "USD",
}

EXISTING_CUSTOMER_REFERENCE = {
    "ContactID": "00000000-0000-4000-8000-0000000000c1",
    "Name": "Fake Customer Co (Sample)",
}

EXISTING_VENDOR_REFERENCE = {
    "ContactID": "00000000-0000-4000-8000-0000000000v1",
    "Name": "Fake Vendor LLC (Sample)",
}

ITEM_RECORD = {
    "externalId": "FAKE-ITEM-EXT-001",
    "itemNumber": "FAKE-ITEM-CODE-001",
    "name": "Fake Item (Sample)",
    "displayName": "Fake Item Display (Sample)",
    "isBillItem": True,
    "isInvoiceItem": True,
    "accounts": [
        {"accountType": "income", "accountNumber": "200"},
        {"accountType": "expense", "accountNumber": "400"},
    ],
}

EXISTING_ITEM_REFERENCE = {
    "ItemID": "00000000-0000-4000-8000-0000000000i1",
    "Code": "FAKE-ITEM-CODE-001",
    "Name": "Fake Item (Sample)",
}

CLASS_RECORD = {
    "externalId": "FAKE-CLASS-EXT-001",
    "name": "Fake Class (Sample)",
    "fullname": "Fake Class Fullname (Sample)",
    "isActive": True,
}

EXISTING_CLASS_REFERENCE = {
    "TrackingOptionID": "00000000-0000-4000-8000-0000000000cl1",
    "Name": "Fake Class (Sample)",
}

TRACKING_CATEGORY_REFERENCE = {
    "TrackingCategoryID": "00000000-0000-4000-8000-0000000000tc1",
    "Name": "Classes",
    "Options": [EXISTING_CLASS_REFERENCE],
}

LOCATION_TRACKING_CATEGORY_REFERENCE = {
    "TrackingCategoryID": "00000000-0000-4000-8000-0000000000tc2",
    "Name": "Locations",
    "Options": [
        {
            "TrackingOptionID": "00000000-0000-4000-8000-0000000000lo1",
            "Name": "East Coast",
        }
    ],
}

INVOICE_RECORD = {
    "externalId": "FAKE-INVOICE-EXT-001",
    "invoiceNumber": "HG-INV-001",
    "customerId": "00000000-0000-4000-8000-0000000000c1",
    "customerName": "Fake Customer Co (Sample)",
    "description": "Fake invoice reference",
    "currency": "USD",
    "exchangeRate": 1.0,
    "status": "DRAFT",
    "issueDate": "2026-07-01",
    "dueDate": "2026-07-31",
    "lineItems": [
        {
            "description": "Consulting services",
            "itemNumber": "FAKE-ITEM-CODE-001",
            "quantity": 2,
            "unitPrice": 100.0,
            "accountNumber": "200",
            "taxCode": "OUTPUT",
            "className": "Fake Class (Sample)",
        }
    ],
}

EXISTING_INVOICE_REFERENCE = {
    "InvoiceID": "00000000-0000-4000-8000-0000000000inv1",
    "InvoiceNumber": "HG-INV-EXISTING",
    "Type": "ACCREC",
}

INVOICE_LINE_ITEM_RECORD = {
    "description": "Line item only",
    "itemNumber": "FAKE-ITEM-CODE-001",
    "quantity": 1,
    "unitPrice": 50.0,
    "accountNumber": "200",
    "taxCode": "OUTPUT",
    "classId": "00000000-0000-4000-8000-0000000000cl1",
}

BILL_RECORD = {
    "externalId": "FAKE-BILL-EXT-001",
    "billNumber": "HG-BILL-001",
    "vendorId": "00000000-0000-4000-8000-0000000000v1",
    "vendorName": "Fake Vendor LLC (Sample)",
    "description": "Fake bill reference",
    "currency": "USD",
    "exchangeRate": 1.0,
    "isDraft": True,
    "taxIncluded": False,
    "issueDate": "2026-07-01",
    "dueDate": "2026-07-31",
    "lineItems": [
        {
            "description": "Inventory purchase",
            "itemNumber": "FAKE-ITEM-CODE-001",
            "quantity": 1,
            "unitPrice": 75.0,
            "accountNumber": "400",
            "taxCode": "INPUT",
        }
    ],
    "expenses": [
        {
            "description": "Office supplies",
            "accountNumber": "400",
            "amount": 25.0,
            "taxCode": "INPUT",
        }
    ],
}

EXISTING_BILL_REFERENCE = {
    "InvoiceID": "00000000-0000-4000-8000-0000000000bill1",
    "InvoiceNumber": "HG-BILL-EXISTING",
    "Type": "ACCPAY",
}

BILL_LINE_ITEM_RECORD = {
    "description": "Bill line only",
    "accountNumber": "400",
    "quantity": 2,
    "unitPrice": 30.0,
    "taxCode": "INPUT",
    "className": "Fake Class (Sample)",
}

BILL_EXPENSE_RECORD = {
    "description": "Expense line only",
    "accountNumber": "400",
    "amount": 15.0,
    "taxCode": "INPUT",
}

INVOICE_PAYMENT_RECORD = {
    "externalId": "FAKE-INVOICE-PAYMENT-EXT-001",
    "invoiceNumber": "HG-INV-EXISTING",
    "accountName": "Business Bank",
    "amount": 50.0,
    "paymentDate": "2026-07-15",
    "exchangeRate": 1.0,
    "paymentNumber": "PAY-001",
}

BILL_PAYMENT_RECORD = {
    "externalId": "FAKE-BILL-PAYMENT-EXT-001",
    "billNumber": "HG-BILL-EXISTING",
    "accountId": "00000000-0000-4000-8000-0000000000b1",
    "amount": 25.0,
    "paymentDate": "2026-07-15",
}

PAYMENT_BANK_ACCOUNT = {
    "AccountID": "00000000-0000-4000-8000-0000000000b1",
    "Name": "Business Bank",
    "Type": "BANK",
}
