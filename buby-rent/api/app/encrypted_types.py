from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from .crypto import cifra, decifra


class StringaCifrata(TypeDecorator):
    """Colonna testuale cifrata: nel database c'e il testo cifrato, nel codice il valore in chiaro."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else cifra(value)

    def process_result_value(self, value, dialect):
        return None if value is None else decifra(value)
