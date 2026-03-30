#coding:utf-8
import os, time, json
from flask import Flask, jsonify
from flask_cors       import CORS
from flask_wtf.csrf   import CSRFProtect
from flask_sqlalchemy import SQLAlchemy

class Config(object):
    SECRET_KEY = 'uvd/dktgmx#mdb3veg9@b5wkgixci61)7hnn3t4f!fwv9'
    JSON_SORT_KEYS = False

    JIEBA_STOPWORD_FILEPATH = '/app/controller/word_cloud/stop.dic'
    JIEBA_DICTIONARY_FILEPATH = '/app/controller/word_cloud/tags.dic'

class Development(Config):
    DEBUG      = True
    TESTING    = True

    WTF_CSRF_ENABLED    = False
    WTF_CSRF_SSL_STRICT = False

    #flask-sqlalchmy extension configuration
    SQLALCHEMY_ECHO                = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class Production(Config):
    DEBUG      = False
    TESTING    = False

    WTF_CSRF_ENABLED    = False
    WTF_CSRF_SSL_STRICT = False

    #flask-sqlalchmy extension configuration
    SQLALCHEMY_ECHO                = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False


app = Flask(__name__)
csrf = CSRFProtect()
csrf.init_app(app)
CORS(app)
app.url_map.strict_slashes = False
APP_VERSION = 'Production'
app.config.from_object('settings.environment.%s' % APP_VERSION)
db = SQLAlchemy(app)

def error_return(message, status_code):
    error = jsonify({'status': 'error', 'message': message})
    error.status_code = status_code
    return error

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS, GET, PATCH, DELETE, PUT')
    return(response)

@app.teardown_request
def teardown_request(exception):
    if exception:
        db.session.rollback()
    db.session.remove()

