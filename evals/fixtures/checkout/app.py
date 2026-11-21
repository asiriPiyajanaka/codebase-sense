from store import award_points, record_order


def checkout(db, request_id, customer, cents):
    if not request_id or not customer or type(cents) is not int or cents <= 0:
        raise ValueError("invalid checkout")
    order_id = record_order(db, request_id, customer, cents)
    award_points(db, order_id, cents)
    return {"order_id": order_id}
