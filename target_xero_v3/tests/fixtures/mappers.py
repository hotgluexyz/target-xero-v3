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
