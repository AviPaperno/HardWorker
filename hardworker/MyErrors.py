# -*- coding: utf-8 -*-

class M_Exception(Exception):
    """Класс, в котором к обычным Exception, добавляется поле - ID."""
    def __init__(self, message, id):
        super(M_Exception, self).__init__(message)
        self.id = id
