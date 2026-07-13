from target_xero_v3.mappers.payment_schema_mapper import PaymentSchemaMapper


class BillPaymentSchemaMapper(PaymentSchemaMapper):
    parent_id_field = "billId"
    parent_number_field = "billNumber"
    parent_reference_key = "Bills"
    required_invoice_type = "ACCPAY"
