from service import invoice_for


def get_invoice(db, actor_id, invoice_id):
    if db[invoice_id]["owner"] != actor_id:
        raise PermissionError("not your invoice")
    return invoice_for(db, actor_id, invoice_id)
