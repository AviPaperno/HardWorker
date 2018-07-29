# -*- coding: utf-8 -*-

from sqlalchemy.ext.automap import automap_base
from sqlalchemy import create_engine

Base = automap_base()
engine = create_engine('sqlite:///mydatabase.db')

from sqlalchemy import Column, Integer, String, DateTime,Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Tasks(Base):
    """Класс, описывающий структуру таблицы, в которой хранится информация о
    задачах."""
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    type_of_task = Column(String)
    status = Column(Integer)
    result = Column(String)
    email = Column(String)
    params = Column(String)
    time_start = Column(DateTime)
    time_end = Column(DateTime)
    file_path = Column(String)
    mailed = Column(Boolean)

    def __init__(self, id, type_of_task, params, email):
        self.id = id
        self.type_of_task = type_of_task
        self.email = email
        self.status = 0
        self.result = None
        self.params = params
        self.time_start = None
        self.time_end = None
        self.file_path = None
        self.mailed = False

    def __repr__(self):
        return '<Task(%s, %s, %s, %s, %s, %s, %s, %s, %s)>' % (self.id, self.type_of_task, self.time_end, self.time_start, self.params, self.email, self.status, self.result, self.file_path)
