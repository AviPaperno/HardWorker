# -*- coding: utf-8 -*-

import time
import datetime

from multiprocessing import Process, Queue
from threading import Thread

from jsonschema import validate
from sqlalchemy.orm import sessionmaker

from MyErrors import M_Exception
from db import engine, Tasks, Base
from decorators import current, BaseTask, validators
from mymail import Mail_Sender
import re
import os


class MyProcess(Process):
    """Класс процесса. Кроме стандартных полей и методов процесса, добавлены
    следующие поля:

    self.email - email отправителя задачи, для данного процесса
    self.type_of_task - тип задачи для данного процесса
    self.time - время создания процесса, необхадимо для упорядочивания
    """

    def __init__(self, target, args, email='', type_of_task=None):
        super(MyProcess, self).__init__(target=target, args=args)
        self.email = email
        self.type_of_task = type_of_task
        self.time = time.time()


class HardWorker():
    """Основной класс.

    Отвечает за создание задач, записи в БД, распределение выполнения
    задач.
    """

    def __init__(self):
        # Поле, отвечающее за максимальное количество запущенных задач
        self.max_globals = None
        # Поле, отвечающее за максимальное количество запущенных задач, в зависимости от типов
        self.max_types = None
        # Поле, хранящее в себе сколько задач, какого типа сейчас выполняется
        self.current_types = {}
        # Список задач, выполняемых в данный момент
        self.RunQueue = []
        # Словарь пар "тип задачи":функция
        self.tmp = {}
        # Типы задач, которые заведены в систему через декоратор или наследование класса
        self.types = []
        # Поток, отвечающий за запуски и завершения задач.
        self.checker = Thread(target=self.check)
        # Словарь, в котором хранятся задачи, в зависимости от типов, ключём является тип, а значением - список задач
        self.Queue = {}
        # Создатель сессии, для работы с БД
        self.DB = sessionmaker(bind=engine)
        # Словарь валидаторов, ключём является тип задачи, а значением - json_schema
        self.validators = validators
        # Конфигурационный файл
        self.config = {}

    def start(self):
        '''
        В данном методе происходит следующее:
            1. В экземпляр класса, подгружается информация о зарегистрированных типах задач, и функциях, связанных с ними
            2. Создаётся очередь выполнения задач, в зависимости от класса. (self.Queue)
            3. Заполняется ключами, словарь, в котором хранится количество задач каждого типа, выполняемого в данный момен
            4. Подгружается конфигурационный файл
            5. Подключается БД
            6. Запускается поток, отвечающий за запуски и завершения задач

        :return:
        '''
        self.tmp = current
        self.types = current.keys()
        self.load_classes()
        self.Queue = {type_of_task: [] for type_of_task in self.types}
        self.current_types = dict.fromkeys(self.types, 0)
        self.load_confg()
        self.reload_db()
        self.checker.start()

    def load_confg(self):
        """Метод, который отвечает за получение информации из конфигурационного
        файла.

        В конфигурационном файле задаётся следующаяя информация:
            1. Максимальное количество запущенных задач
            2. Максимальное количество запущенных задач, в зависимости от типов
            3. Информация, необходимая для отправки E-mail
        :return:
        """
        self.max_globals = self.config.get('MAX_COUNT', 5)
        self.max_types = self.config.get('MAX_TYPE_COUNT', {})
        self.email = Mail_Sender(self.config.get('MAIL_SERVER', 'smtp.yandex.ru:465'),
                                 self.config.get('MAIL_LOGIN', ''), self.config.get(
                'MAIL_PASSWORD', ''), self.config.get('MAIL_FROM', 'HardWorker'),
                                 self.config.get('MAIL_SUBJECT', 'Your task finished'))

    def load_classes(self):
        """Данный метод загружает информацию о всех задачах, созданных через
        наследование класса. Может генерировать исключение, если задача была
        задана несколько раз.

        :return:
        """
        for i in BaseTask.__subclasses__():
            if i.name not in self.types:
                self.tmp[i.name] = i().run
                self.types.append(i.name)
                try:
                    self.validators[i.name] = i.json_schema
                except Exception:
                    pass
            else:
                raise M_Exception(
                    'Function named {} duplicated'.format(i.name), 100)

    def resend_email(self):
        """Метод проверяет, есть ли выполненые задачи, результат которых не был отправлен на email,
        если находит - пытается выполнить повторную отправку

        :return:
        """
        session = self.DB()
        var = session.query(Tasks).filter(
            Tasks.status == 2).filter(Tasks.mailed == False).all()
        for i in var:
            try:
                self.email.send_message(i.email, str(i.result.encode("utf-8")), i.file_path)
                i.mailed = True
            except Exception:
                pass
        session.commit()
        session.close()

    def reload_db(self):
        """Метод отвечает за подключение к БД, её созданию, если файл с ней
        отсутствует в директории, а так же за перезапуск тех задач, которые на
        момент нештатного завершения работы системы были не завершены.

        :return:
        """
        if 'mydatabase.db' in os.listdir('.'):
            session = self.DB()
            var = session.query(Tasks).filter(
                Tasks.status != 2).filter(
                Tasks.status != 3).order_by(Tasks.id).all()
            for i in var:
                session.delete(i)
                session.commit()
            for i in var:
                self.add_task(i.type_of_task, eval(i.params), i.email)
            self.resend_email()
        else:
            Base.metadata.create_all(engine)

    def mytask(self, function, task_id, params):
        """Этот метод отвечает за выполнение функции, связанной с типом. Кроме
        этого производится записи в БД, такие как:

            1. Изменение статуса, 0 - ожидает очереди на выполнение, 1 - выполняется, 2 - выполнен
            2. Запись результата и пути к файлу, если он есть.
        :param function: функция, которая будет выполнятся
        :param task_id: id записи в БД
        :param params: параметры для функций
        :return:
        """
        session = self.DB()
        Task = session.query(Tasks).filter(Tasks.id == task_id).first()
        Task.status = 1
        Task.time_start = datetime.datetime.now()
        session.commit()
        try:
            tmp = function(params)
            if (type(tmp) == dict) and tmp.get('file_path', False) and tmp.get('result', False):
                Task.file_path = tmp['file_path']
                Task.result = tmp['result']
            else:
                Task.result = str(tmp)
            Task.status = 2
            Task.time_end = datetime.datetime.now()
        except Exception as e:
            Task.status = 3
            Task.result = "Not found parameter(s) named {} or it's not valid.".format(e.args)
        try:
            self.email.send_message(Task.email, str(Task.result), Task.file_path)
            Task.mailed = True
        except Exception:
            Task.mailed = False
        session.commit()
        session.close()

    def add_task(self, type_of_task, params, email):
        """
        В этом методе происходит следующее:
            1. Валидация e-mail, проверка зарегистрирован данный тип задачи, а так же валидация параметров, при наличии валидатора
            2. Создание записи в БД и процесса, для выполнения задачи
            3. Добавление созданного процесса в очередь
        :param type_of_task: тип задачи
        :param params: параметры для задачи
        :param email: email на который будет отправляться результат выполнения задачи
        :return:
        """

        if not email or not re.match(r"^([a-z0-9_-]+\.)*[a-z0-9_-]+@[a-z0-9_-]+(\.[a-z0-9_-]+)*\.[a-z]{2,6}$", email):
            raise M_Exception('No valid email', 600)
            return
        if type_of_task in self.types:
            try:
                if self.validators.get(type_of_task, False):
                    validate(params, self.validators.get(type_of_task))
            except Exception:
                raise M_Exception('Validate failed', 200)
                return
            session = self.DB()
            _id = session.query(Tasks).order_by(-Tasks.id).first()
            session.close()
            session = self.DB()
            if _id is not None:
                local_id = _id.id + 1
            else:
                local_id = 1
            td = Tasks(id=local_id, type_of_task=type_of_task, params=str(
                params), email=email)
            session.add(td)
            session.commit()
            session.close()
            curr_p = MyProcess(target=self.mytask, args=(
                self.tmp[type_of_task], local_id, params), email=email, type_of_task=type_of_task)
            self.Queue[type_of_task].append(curr_p)
        else:
            raise M_Exception('No this type of task', 300)

    def check_stat(self):
        """Метод, который проверяет, есть ли среди процессов, которые уже
        выполняются те, что уже завершили свою работу.

        :return: список процессов, завершивших свою работу
        """

        return [i for i in self.RunQueue if not i.is_alive()]

    def check_dict(self):
        """Метод, который проверяет, есть ли в очереди на выполнение хотя бы
        одна задача.

        :return:
        """

        for key, value in self.Queue.items():
            if value:
                return True
        return False

    def min_time(self):
        """Этот метод возвращает минимальное время в очереди для случайного
        типа задач.

        :return:
        """

        for key, value in self.Queue.items():
            if value:
                return value[0].time

    def check(self):
        """Это основной метод, который запускается в отдельном потоке. Он
        проверяет возможность переместить процессы из Очереди на
        ожидание(self.Queue) в Список на выполнение(self.RunQueue) А так же
        проверяет, есть ли процессы, завершившие свою работу и если да, то он
        удаляет их из Списка на выполнение.

        :return:
        """
        while True:
            if len(self.RunQueue) < self.max_globals and self.check_dict():
                add_process = None
                min_time = self.min_time()
                for i in self.Queue.keys():
                    if self.Queue.get(i, False):
                        if self.max_types.get(i, False):
                            if self.current_types.get(i) < self.max_types.get(i):
                                if self.Queue[i][0].time <= min_time:
                                    min_time = self.Queue[i][0].time
                                    add_process = i
                        else:
                            if self.Queue[i][0].time <= min_time:
                                min_time = self.Queue[i][0].time
                                add_process = i
                if add_process != None:
                    tmp = self.Queue[add_process].pop(0)
                    tmp.start()
                    self.RunQueue.append(tmp)
                    self.current_types[add_process] += 1
            if self.check_stat():
                for i in self.check_stat():
                    self.RunQueue.remove(i)
                    self.current_types[i.type_of_task] -= 1
            self.resend_email()
