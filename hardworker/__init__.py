# -*- coding: utf-8 -*-

from flask import Flask, render_template
from flask import request
from tmo import HardWorker
from MyErrors import M_Exceptioin
from sqlalchemy.orm import sessionmaker
from db import engine,Tasks
from decorators import task,BaseTask

# Инициализация приложений, для запуска Flask и нашего приложения
app = Flask(__name__)
hardworkerapp = HardWorker()

# Метод для обработки POST запросов


@app.route('/', methods=['POST'])
def postJsonHandler():
    content = request.get_json()
    try:
        hardworkerapp.add_task(
            str(content[u'name']), content[u'params'], str(content[u'email']))
        return '{"status": "OK"}'
    except M_Exceptioin as e:
        t = {'status': 'ERROR',
             'error_code': e.id,
             'error_msg': e.message,
             }
        return str(t)
    except Exception as e:
        t = {'status': 'ERROR',
             'error_code': '500',
             'error_msg': 'Field named {} not found in your POST'.format(e.message),
             }
        return str(t)

