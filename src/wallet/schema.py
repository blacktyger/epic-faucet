from ninja import Schema


class Payload(Schema):
    address: str


class TxSchema(Schema):
    data: str

class BalanceSchema(Schema):
    data: str