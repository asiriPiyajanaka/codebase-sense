from service import invoice_for


def export_invoice(db, requested_by, invoice_id):
    return invoice_for(db, requested_by, invoice_id)["amount"]
