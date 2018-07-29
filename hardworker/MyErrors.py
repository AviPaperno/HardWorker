# -*- coding: utf-8 -*-

class M_Exceptioin(Exception):
    """Класс, в котором к обычным Exception, добавляется поле - ID."""
    def __init__(self, message, id):
        super(M_Exceptioin, self).__init__(message)
        self.id = id
