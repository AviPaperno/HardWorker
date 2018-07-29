# -*- coding: utf-8 -*-

"""В данном модуле описывается декоратор @task.

Для того, что бы можно было из другого модуля получить информацию обо
всех функциях, продекорированных им, причём необходимо передавать не
только функцию, но и имя задачи, а так же схему для валидирования
параметров, мною были использованы две глобальные переменные.
"""

# Словарь пар "тип задачи":функция
current = {}
validators = {}

# Декоратор с параметрами


def task(name, json_schema=None):
    global current
    global validators

    def _task(real_function):
        global current
        global validators

        def _wrapped_function(params):
            global current
            global validators
            return real_function(params)
        if json_schema:
            validators[name] = json_schema
        current[name] = real_function
        return _wrapped_function
    return _task

# Базовый класс, для создания задач через наследование


class BaseTask(object):

    def __init__(self):
        pass

    def run(self, params):
        pass
