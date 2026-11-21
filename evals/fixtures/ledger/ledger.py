class Ledger:
    def __init__(self, adapter):
        self._adapter = adapter

    def transfer(self, request_id, sender, receiver, amount):
        if not request_id or not sender or not receiver or sender == receiver:
            raise ValueError("invalid identity")
        if type(amount) is not int or amount <= 0:
            raise ValueError("amount must be a positive integer")
        return self._adapter.transfer(request_id, sender, receiver, amount)
