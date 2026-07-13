from target_xero_v3.mappers.payment_schema_mapper import PaymentSchemaMapper


class InvoicePaymentSchemaMapper(PaymentSchemaMapper):
    parent_id_field = "invoiceId"
    parent_number_field = "invoiceNumber"
    parent_reference_key = "Invoices"
    required_invoice_type = "ACCREC"
