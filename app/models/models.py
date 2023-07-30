from pydantic import BaseModel
from datetime import date

class Transaction(BaseModel):
    date: date
    amount: float
    notes: str = None

    def to_dict(self):
        return {
            'date': self.date,
            'amount': self.amount,
            'notes' :self.notes
        }
