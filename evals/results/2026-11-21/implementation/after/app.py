from store import complete_checkout


def checkout(db, request_id, customer, cents):
    if not request_id or not customer or type(cents) is not int or cents <= 0:
        raise ValueError("invalid checkout")
    order_id = complete_checkout(db, request_id, customer, cents)
    return {"order_id": order_id}
