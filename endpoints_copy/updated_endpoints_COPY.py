import flask
from flask import jsonify # <- `jsonify` instead of `json`
from flask import Flask

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import update, func, create_engine
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import sessionmaker
from sqlalchemy.inspection import inspect
import sqlalchemy.types as types

from flask import request, render_template, url_for, redirect, send_from_directory, flash
from flask import Response, make_response
from flask import session as dropzone_session

from routetest1_InsertValuesIntoDB_customer import Customer
from routetest1_InsertValuesIntoDB_models import Models
from routetest1_InsertValuesIntoDB_execution import Execution
from routetest1_InsertValuesIntoDB_datasets import Datasets
from routetest1_InsertValuesIntoDB_supplier import Supplier
from routetest1_InsertValuesIntoDB_api_keys import Api_keys
from werkzeug.utils import secure_filename

import flask
import decimal, datetime
import json
import pprint
import sys
import importlib
import os
import errno
import numpy as np

import zipfile
from flask_uploads import UploadSet, configure_uploads, IMAGES
from werkzeug.serving import run_simple
import docker
from docker import client
import dockerpty

from io import BytesIO
from docker import APIClient
from os import path
from pathlib import Path
from time import time
import shutil
import boto3 # communicate with AWS Python SDK

from time import sleep
from time import *             #meaning from time import EVERYTHING
import time
import random

#### NEW IMPORTS ####
from time import sleep
from flask import copy_current_request_context
import threading
import datetime
#####################

from werkzeug.exceptions import HTTPException
from flask import abort
from werkzeug.exceptions import Unauthorized

############## Demonstration of logging feature for a Flask App. ##############
import logging
from logging.handlers import RotatingFileHandler
from time import strftime
import logging.handlers
import traceback
import requests
####################

client = docker.from_env()
client = docker.APIClient(base_url='unix://var/run/docker.sock')

##################################################################################################################################################
UPLOAD_FOLDER = "/home/chiefai/production/data"
#ALLOWED_EXTENSIONS = set(['txt', 'csv', 'pdf', 'png', 'jpg', 'jpeg', 'tif', 'tiff', 'gif', 'h5', 'pkl', 'py', 'joblib', 'zip', '7z'])
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'tif', 'tiff', 'zip'])

# Initialise the Flask app
#app = flask.Flask(__name__, template_folder='templates')
app = Flask(__name__)
#app.config['SECRET_KEY'] = 'supersecretkeygoeshere'

if __name__ != '__main__':
	handler = RotatingFileHandler('production-error.log', maxBytes=10000, backupCount=3)
	#handler = logging.handlers.RotatingFileHandler('production-error.log', maxBytes=1024 * 1024, backupCount=3)
	####
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.ERROR)
	logger.addHandler(handler)
	####
	logging.getLogger('werkzeug').setLevel(logging.DEBUG)
	logging.getLogger('werkzeug').addHandler(handler)
	app.logger.setLevel(logging.WARNING)
	app.logger.addHandler(handler)
	logging.getLogger('apscheduler.scheduler').setLevel(logging.DEBUG)
	logging.getLogger('apscheduler.scheduler').addHandler(handler)
	####
	gunicorn_logger = logging.getLogger('gunicorn.error')
	app.logger.handlers = gunicorn_logger.handlers
	app.logger.setLevel(gunicorn_logger.level)

'''
handler = logging.handlers.RotatingFileHandler('production-log.txt', maxBytes=1024 * 1024, backupCount=3)
logging.getLogger('werkzeug').setLevel(logging.DEBUG)
logging.getLogger('werkzeug').addHandler(handler)
app.logger.setLevel(logging.WARNING)
app.logger.addHandler(handler)
logging.getLogger('apscheduler.scheduler').setLevel(logging.DEBUG)
logging.getLogger('apscheduler.scheduler').addHandler(handler)
'''


####################### FOR ERROR LOGGING ############################


@app.after_request
def after_request(response):
	### Logging after every request. ###
	# This avoids the duplication of registry in the log,
	# since that 500 is already logged via @app.errorhandler.
	if response.status_code != 500:
		ts = strftime('[%Y-%b-%d %H:%M]')
		logger.error('%s %s %s %s %s %s', ts, request.remote_addr, request.method, request.scheme, request.full_path, response.status)
	return response


@app.errorhandler(Exception)
def exceptions(e):
	### Logging after every Exception ###
	ts = strftime('[%Y-%b-%d %H:%M]')
	tb = traceback.format_exc().splitlines()

	logger.error('%s %s %s %s %s 5xx INTERNAL SERVER ERROR\n%s',
						ts,
						request.remote_addr,
						request.method,
						request.scheme,
						request.full_path,
						tb)

	return jsonify(
		{"response" : "Internal Server Error", 
		"traceback": tb
		}), 500

####################### END FOR ERROR LOGGING ############################

def add_cors_headers(response):
	response.headers['Access-Control-Allow-Origin'] = '*'
	if request.method == 'OPTIONS':
		response.headers['Access-Control-Allow-Methods'] = 'DELETE, GET, POST, PUT'
		headers = request.headers.get('Access-Control-Request-Headers')
		if headers:
			response.headers['Access-Control-Allow-Headers'] = headers
	return response
app.after_request(add_cors_headers)


class DecimalEncoder(json.JSONEncoder):
	def default(self, obj):
		"""JSON encoder function for SQLAlchemy special classes."""
		if isinstance(obj, datetime.date):
			return obj.isoformat()
		elif isinstance(obj, decimal.Decimal):
			return float(obj)
		return super(DecimalEncoder, self).default(obj)


class AlchemyEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj.__class__, DeclarativeMeta):
			# an SQLAlchemy class
			fields = {}
			for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
				data = obj.__getattribute__(field)
				try:
					json.dumps(data) # this will fail on non-encodable values, like other classes
					fields[field] = data
				except TypeError:
					fields[field] = None
					# a json-encodable dict
			return fields
		return json.JSONEncoder.default(self, obj)


def allowed_file(filename):
	return '.' in filename and \
					filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = 'postgresql://chiefai:123456@localhost:5433/chiefai2'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
engine = create_engine("postgresql://chiefai:123456@localhost:5433/chiefai2")
Session = sessionmaker(bind=engine)
session=Session()
db = SQLAlchemy(app)
app.json_encoder = DecimalEncoder
############################################################

############################################################

class Serializer(object):

	def serialize(self):
		return {c: getattr(self, c) for c in inspect(self).attrs.keys()}

	@staticmethod
	def serialize_list(l):
		return [m.serialize() for m in l]


class Customer(db.Model, Serializer):
	member_id = db.Column(db.Integer, primary_key=True)
	customername = db.Column(db.String(100))
	credits = db.Column(db.Integer)
	created_on = db.Column(db.DateTime, default=db.func.now())

	def __init__(self, member_id, customername, credits, created_on):
		self.member_id = member_id
		self.customername = customername
		self.credits = credits
		self.created_on = created_on

	def serialize(self):
		d = Serializer.serialize(self)
		return d


class Models(db.Model, Serializer):
	model_id = db.Column(db.Integer, primary_key=True)
	modelname = db.Column(db.String(100))
	modelpath = db.Column(db.String(100))
	member_id = db.Column(db.Integer)
	created_on = db.Column(db.DateTime, default=db.func.now())
	price = db.Column(db.Integer)
	tag = db.Column(db.String(100))


	def __init__(self, model_id, modelname, modelpath, member_id, created_on, price, tag):
		self.model_id = model_id
		self.modelname = modelname
		self.modelpath = modelpath
		self.member_id = member_id
		self.created_on = created_on
		self.price = price
		self.tag = tag


	def serialize(self):
		d = Serializer.serialize(self)
		return d


class Execution(db.Model, Serializer):
	execution_id = db.Column(db.Integer, primary_key=True)
	model_id = db.Column(db.Integer)
	member_id = db.Column(db.Integer)
	created_on = db.Column(db.DateTime, default=db.func.now())
	charged_credits = db.Column(db.Numeric)
	revenue_earned_chiefai = db.Column(db.Numeric)
	execution_time = db.Column(db.Numeric)

	def __init__(self, execution_id, model_id, member_id, created_on, charged_credits, revenue_earned_chiefai, execution_time):
		self.execution_id = execution_id
		self.model_id = model_id
		self.member_id = member_id
		self.created_on = created_on
		self.charged_credits = charged_credits
		self.revenue_earned_chiefai = revenue_earned_chiefai
		self.execution_time = execution_time

	def serialize(self):
		d = Serializer.serialize(self)
		return d


class Result(db.Model, Serializer):
	result_id = db.Column(db.Integer, primary_key=True)
	execution_id = db.Column(db.Integer)
	imagename = db.Column(db.String(500))
	prediction = db.Column(db.String(500))
	probability = db.Column(db.Numeric)

	def __init__(self, result_id, execution_id, imagename, prediction, probability):
		self.result_id = result_id
		self.execution_id = execution_id
		self.imagename = imagename
		self.prediction = prediction
		self.probability = probability

	def serialize(self):
		d = Serializer.serialize(self)
		return d


class Datasets(db.Model, Serializer):
	datasets_id = db.Column(db.Integer, primary_key=True)
	member_id = db.Column(db.Integer)
	datasetsfilepath = db.Column(db.String(100))
	created_on = db.Column(db.DateTime, default=db.func.now())

	def __init__(self, datasets_id, member_id, datasetsfilepath, created_on):
		self.datasets_id = datasets_id
		self.member_id = member_id
		self.datasetsfilepath = datasetsfilepath
		self.created_on = created_on

	def serialize(self):
		d = Serializer.serialize(self)
		return d


class Supplier(db.Model, Serializer):
	member_id = db.Column(db.Integer, primary_key=True)
	suppliername = db.Column(db.String(100))
	commission = db.Column(db.Integer)
	created_on = db.Column(db.DateTime, default=db.func.now())

	def __init__(self, member_id, suppliername, commission, created_on):
		self.member_id = member_id
		self.suppliername = suppliername
		self.commission = commission
		self.created_on = created_on

	def serialize(self):
		d = Serializer.serialize(self)
		return d


class Members(db.Model, Serializer):
	member_id = db.Column(db.Integer, primary_key=True)
	membername = db.Column(db.String(100))
	role = db.Column(db.String(2))
	api_key = db.Column(db.String(100))
	created_on = db.Column(db.DateTime, default=db.func.now())

	def __init__(self, member_id, membername, role, api_key, created_on):
		self.member_id = member_id
		self.membername = membername
		self.role = role
		self.api_key = api_key
		self.created_on = created_on

	def serialize(self):
		d = Serializer.serialize(self)
		return d


def serve(cwd, app, port):
	sys.path.insert(0, cwd)

	wsgi_fqn = app.rsplit('.', 1)
	wsgi_fqn_parts = wsgi_fqn[0].rsplit('/', 1)
	if len(wsgi_fqn_parts) == 2:
		sys.path.insert(0, os.path.join(cwd, wsgi_fqn_parts[0]))
	wsgi_module = importlib.import_module(wsgi_fqn_parts[-1])
	wsgi_app = getattr(wsgi_module, wsgi_fqn[1])

	# Attempt to force Flask into debug mode
	try:
		wsgi_app.debug = True
	except:  # noqa: E722
		pass

	os.environ['IS_OFFLINE'] = 'True'

	serving.run_simple(
		'localhost', int(port), wsgi_app,
		use_debugger=True, use_reloader=True, use_evalex=True)


class MyUnauthorized(Unauthorized):
	description = '<Why access is denied string goes here...>'
	def get_headers(self, environ):
		"""Get a list of headers."""
		return [('Content-Type', 'text/html'),
			('WWW-Authenticate', 'Basic realm="Login required"')]

#@app.errorhandler(401)
def custom_401():
	return Response('<message: "ERROR: Unauthorized! Please provide a valid API KEY>', 401, {'WWW-Authenticate':'Basic realm="Login Required"'})



# ###############################               ##################################
# ###############################   CUSTOMERS   ##################################
# ###############################               ##################################

# 1 - LIST A SPECIFIC CUSTOMER RECORD
# PROTECTED PUBLIC API 

@app.route('/api/v1.0/customers/<member_id>', methods=['GET'])
def DisplaySpecficCustomer(member_id):
	headers = request.headers
	auth = headers.get("x-api-key")	
	if auth:
		var_api_key = Members.query.filter_by(member_id=member_id).first().api_key
		if auth != var_api_key :
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key mismatch"}), 401
		else: print (jsonify({"message": "OK: Authorized"}), 200)
	else: return jsonify({"error": "API key missing"}), 401
	
	allCustomer = Customer.query.filter_by(member_id=member_id).first()
	
	return jsonify(
		Member_id=allCustomer.member_id, 
		CustomerName=allCustomer.customername,
		Credits=allCustomer.credits, 
		Created_On=allCustomer.created_on)


# ###############################                      ####################################
# ###############################   CUSTOMER CREDITS   ####################################
# ###############################                      ####################################

# 1 - Topup Credits in Customer
# PROTECTED ADMIN API
# HOW TO PROTECT???

#@app.route('/api/v1.0/customers/credits/topup', methods=['POST'])
@app.route('/api/v1.0/customers/credits/t', methods=['POST'])
def AddCredits():
	if request.method == 'POST':
		var1 = request.form['credits']
		var2 = request.form['member_id']
		MemberID = var2
		A = Customer.query.filter_by(member_id=var2).first().credits
		B = int(var1)
		AddCredits = A + B
		customerName = Customer.query.filter_by(member_id=var2).first().customername
		updatedBalance = Customer(MemberID, customerName, AddCredits, 'NOW()')
		db.session.merge(updatedBalance)
		db.session.commit()
	return str(AddCredits)


# 2 - Deduct Credits in Customer
# PROTECTED ADMIN API
# HOW TO PROTECT???
# is this used???

#@app.route('/api/v1.0/customers/credits/deduct', methods=['POST'])
app.route('/api/v1.0/customers/credits/d', methods=['POST'])
def DeductCredits():
	if request.method == 'POST':
		var1 = request.form['credits']
		var2 = request.form['member_id']
		MemberID = var2
		A = Customer.query.filter_by(member_id=var2).first().credits
		B = int(var1)
		DeductCredits = A - B
		customerName = Customer.query.filter_by(member_id=var2).first().customername
		updatedBalance = Customer(MemberID, customerName, DeductCredits, 'NOW()')
		db.session.merge(updatedBalance)
		db.session.commit()
	return str(DeductCredits)


# 3 - Retreive Credits for specific Customer
# PROTECTED PUBLIC API

@app.route('/api/v1.0/customers/credits', methods=['POST', 'GET'])
def RetrieveCredits():
	if request.method == 'POST':
		var1 = request.form['member_id']
		headers = request.headers
		auth = headers.get("x-api-key")
		if auth:
			var_api_key = Members.query.filter_by(member_id=var1).first().api_key
			if auth != var_api_key :
				return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key mismatch"}), 401
			else: print (jsonify({"message": "OK: Authorized"}), 200)
		else: return jsonify({"error": "API key missing"}), 401

		RetrieveBalance = Customer.query.filter_by(member_id=var1).first()
	return jsonify(MemberID=RetrieveBalance.member_id,
							CustomerName=RetrieveBalance.customername,
							Current_Balance_Credits=RetrieveBalance.credits,
							Created_On=RetrieveBalance.created_on)


# ############################               ###############################
# ############################   SUPPLIERS   ###############################
# ############################               ###############################

# 3 - List specific Supplier record
# PROTECTED PUBLIC API

@app.route('/api/v1.0/suppliers/<member_id>', methods=['GET'])
def DisplaySpecficSupplier(member_id):
	headers = request.headers
	auth = headers.get("x-api-key")
	if auth:
		var_api_key = Members.query.filter_by(member_id=member_id).first().api_key
		if auth != var_api_key :
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key mismatch"}), 401
		else: print (jsonify({"message": "OK: Authorized"}), 200)
	else: return jsonify({"error": "API key missing"}), 401
	allSupplier = Supplier.query.filter_by(member_id=member_id).first()
	return jsonify(Member_id=allSupplier.member_id,
							SupplierName=allSupplier.suppliername,
							Commission=allSupplier.commission,
							Created_On=allSupplier.created_on)


# #####################                         #####################
# #####################   SUPPLIER COMMISSION   #####################
# #####################                         #####################

# 1 - Topup Commission for specific Supplier
# PROTECTED ADMIN API
# HOW TO PROTECT???

#@app.route('/api/v1.0/suppliers/commission/topup', methods=['POST'])
@app.route('/api/v1.0/suppliers/commission/tp', methods=['POST'])
def AddCommission():
	if request.method == 'POST':
		var1 = request.form['commission']
		var2 = request.form['member_id']
		MemberID = var2
		A = Supplier.query.filter_by(member_id=var2).first().commission
		B = int(var1)
		AddCommission = A + B
		supplierName = Supplier.query.filter_by(member_id=var2).first().suppliername
		updatedBalance = Supplier(MemberID, supplierName, AddCommission, 'NOW()')
		db.session.merge(updatedBalance)
		db.session.commit()
	return str(AddCommission)


# 2 - Deduct Commission for specific Supplier
# PROTECTED ADMIN API
# HOW TO PROTECT???

#@app.route('/api/v1.0/suppliers/commission/deduct', methods=['POST'])
@app.route('/api/v1.0/suppliers/commission/dt', methods=['POST'])
def DeductCommission():
	if request.method == 'POST':
		var1 = request.form['commission']
		var2 = request.form['member_id']
		MemberID = var2
		A = Supplier.query.filter_by(member_id=var2).first().commission
		B = int(var1)
		DeductCommission = A - B
		supplierName = Supplier.query.filter_by(member_id=var2).first().suppliername
		updatedBalance = Supplier(MemberID, supplierName, DeductCommission, 'NOW()')
		db.session.merge(updatedBalance)
		db.session.commit()
	return str(DeductCommission)


# 3 - Retrieve Commission for specific Supplier
# PROTECTED PUBLIC API

@app.route('/api/v1.0/suppliers/commission', methods=['POST'])
def RetrieveCommission():
	var1 = request.form['member_id']
	headers = request.headers
	auth = headers.get("x-api-key")
	if auth:
		var_api_key = Members.query.filter_by(member_id=var1).first().api_key
		if auth != var_api_key :
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key mismatch"}), 401
		else: print (jsonify({"message": "OK: Authorized"}), 200)
	else: return jsonify({"error": "API key missing"}), 401

	RetrieveBalance = Supplier.query.filter_by(member_id=var1).first()
	return jsonify(MemberID=RetrieveBalance.member_id,
							SupplierName=RetrieveBalance.suppliername,
							Current_Balance_Commission=RetrieveBalance.commission,
							Created_On=RetrieveBalance.created_on)


# ###############################            ####################################
# ###############################   MODELS   ####################################
# ###############################            ####################################

# 1 - LIST ALL MODELS
# PROTECTED ADMIN API
# HOW TO PROTECT???

#@app.route('/api/v1.0/models', methods=['GET'])
@app.route('/api/v1.0/ms', methods=['GET'])
def DisplayAllModels():
	allModels = Models.query.all()
	return jsonify(allModels = Models.serialize_list(allModels))


# 2 - LIST ALL MODELS, BUT ONLY NAMES!
# PUBLIC UNPROTECTED API

@app.route('/api/v1.0/model_names', methods=['GET'])
def DisplayAllModelNames():
	allModels = Models.query.all()
	q = engine.execute('''SELECT modelname FROM models''')
	return jsonify({'modelnames': [row.values()[0] for row in q]})


# 3 - LIST RECORD
# PROTECTED ADMIN API
# HOW TO PROTECT???

#@app.route('/api/v1.0/models/<model_id>', methods=['GET'])
@app.route('/api/v1.0/ms/<model_id>', methods=['GET'])
def SpecificModel(model_id):
	model = Models.query.filter_by(model_id=model_id).first()
	return jsonify(Model_ID=model.model_id,
							ModelName=model.modelname,
							ModelPath=model.modelpath,
							Member_id=model.member_id,
							Created_On=model.created_on,
							Price=model.price,
							Tag=model.tag)



# 4 - EDIT RECORD
# PROTECTED PUBLIC API
@app.route('/api/v1.0/models/<model_id>/update', methods=['PUT', 'POST'])
def UpdateModels(model_id):
	# get models record
	models = Models.query.filter_by(model_id=model_id).first()
	newmodelname = request.form['modelname']
	newmodelpath = request.form['model_path']
	newmember_id = request.form['member_id']
	newcreated_on = request.form['created_on']
	newprice = request.form['price']
	newtag = request.form['tag']
	# skip empty variables, only change non-empty input from form
	if newmodelname == 'None':
		pass
	else: models.modelname = newmodelname
	if newmodelpath == 'None':
		pass
	else: models.model_path = newmodelpath
	if newmember_id == 'None':
		pass
	else: models.member_id = newmember_id
	if newcreated_on == 'None':
		pass
	else: models.created_on = newcreated_on
	if newprice == 'None':
		pass
	else: models.price = newprice
	if newtag == 'None':
		pass
	else: models.tag = newtag

	# verify user
	headers = request.headers
	auth = headers.get("x-api-key")
	if auth:
		var_api_key = Members.query.filter_by(member_id=newmember_id).first().api_key
		if auth != var_api_key :
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
		else:
			print (jsonify({"message": "OK: Authorized"}), 200)
	else: 
		return jsonify({"error": "API key missing"}), 401

	# update record
	db.session.commit()
	print ("Record UPDATED Successfully!")
	ModelsRecords = Models.query.filter_by(model_id=model_id).first()
	return jsonify(Model_ID=ModelsRecords.model_id,
							ModelName=ModelsRecords.modelname,
							ModelPath=ModelsRecords.modelpath,
							Member_id=ModelsRecords.member_id,
							Created_On=ModelsRecords.created_on,
							Price=ModelsRecords.price,
							Tag=ModelsRecords.tag)



# 5 - DELETE RECORD
# PROTECTED PUBLIC API
@app.route('/api/v1.0/models/<model_id>/delete', methods=['DELETE'])
def DeleteRecordModels(model_id):
	memberid = Models.query.filter_by(model_id=model_id).first().member_id
	headers = request.headers
	auth = headers.get("x-api-key")
	if auth:
		var_api_key = Members.query.filter_by(member_id=memberid).first().api_key
		if auth != var_api_key :
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
		else:
			print (jsonify({"message": "OK: Authorized"}), 200)
	else: 
		return jsonify({"error": "API key missing"}), 401
	DeleteRecord = Models.query.filter_by(model_id=model_id).first()
	db.session.delete(DeleteRecord)
	db.session.commit()
	print ("Record DELETED Successfully!")
	ModelsRecords = Models.query.all()
	return jsonify(ModelsRecords = Models.serialize_list(ModelsRecords))



# 7 - RETRIEVE RECORD by Member_id
# PROTECTED PUBLIC API

@app.route('/api/v1.0/models/retrievebymemberid', methods=['GET', 'POST'])
def RetrieveModelsbymember_id():
	var1 = request.form['member_id']
	headers = request.headers
	auth = headers.get("x-api-key")
	if auth:
		var_api_key = Members.query.filter_by(member_id=var1).first().api_key
		if auth != var_api_key :
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
		else:
			print (jsonify({"message": "OK: Authorized"}), 200)
	else: 
		return jsonify({"error": "API key missing"}), 401
	
	if Models.query.filter_by(member_id=var1):
		allModels = Models.query.filter_by(member_id=var1).all()
		return jsonify(allModels = Models.serialize_list(allModels))

	else: # if the supplier has no associated models, return None
		return jsonify(
			Model_ID=None, 
			ModelName=None,
			ModelPath=None,
			MemberID=None, 
			Created_On=None,
			Price=None, 
			Tag=None)


# ###############################  				 ####################################
# ###############################   EXECUTIONS   ####################################
# ###############################                ####################################


# 1 - DELETE RECORD
# PROTECTED PUBLIC API

@app.route('/api/v1.0/executions/<execution_id>/delete', methods=['DELETE'])
def DeleteRecordExecution(execution_id):
	var1 = request.form['member_id']
	# verify user
	headers = request.headers
	auth = headers.get("x-api-key")
	if auth:
		var_api_key = Members.query.filter_by(member_id=memberid).first().api_key
		if auth != var_api_key:
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
		else:
			print (jsonify({"message": "OK: Authorized"}), 200)
	else: 
		return jsonify({"error": "API key missing"}), 401

	DeleteRecord = Execution.query.filter_by(execution_id=execution_id).first()
	db.session.delete(DeleteRecord)
	db.session.commit()
	print ("Record DELETED Successfully!")
	ExecutionRecord = Execution.query.all()
	return jsonify(ExecutionRecord = Execution.serialize_list(ExecutionRecord))


# 2 - QUERY RECORD BY CUSTOMER ID FROM WEB FORM/POSTMAN
# SHOULD BE PROTECTED API
# MAKING PUBLIC API for WAQAR

@app.route('/api/v1.0/executions/retrieve', methods=['GET', 'POST'])
def RetrieveExecutions():
	var1 = request.form['member_id']
	# verify user
	#headers = request.headers
	#auth = headers.get("x-api-key")
	#if auth:
	#	var_api_key = Members.query.filter_by(member_id=memberid).first().api_key
	#	if auth != var_api_key:
	#		return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
	#	else:
	#		print (jsonify({"message": "OK: Authorized"}), 200)
	#else: 
	#	return jsonify({"error": "API key missing"}), 401
	Executions = Execution.query.filter_by(member_id=var1).all()
	return jsonify(Executions = Execution.serialize_list(Executions))


# 3 - RETRIEVE DATA DUMP OF ALL EXECUTIONS FOR SINGLE USER
# SHOULD BE PROTECTED API
# MAKING PUBLIC API for WAQAR

@app.route('/api/v1.0/executions/<member_id>/retrieveDict', methods=['GET', 'POST'])
def DisplayAllExecutionsInJasonifyModeUsingRawSQL():
	# verify user
	#headers = request.headers
	#auth = headers.get("x-api-key")
	#if auth:
	#	var_api_key = Members.query.filter_by(member_id=member_id).first().api_key
	#	if auth != var_api_key:
	#		return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
	#	else:
	#		print (jsonify({"message": "OK: Authorized"}), 200)
	#else: 
	#	return jsonify({"error": "API key missing"}), 401
	with engine.connect() as con:
		rs = con.execute("SELECT * FROM execution WHERE memberid=%(memberid)s", memberid=member_id)
		return json.dumps([dict(r) for r in rs], cls=DecimalEncoder)
		fo = open("/home/chiefai/production/results/JsonDumpFile.json", 'w')
		filebuffer = JsonDumpFile
		fo.writelines(filebuffer)
		SaveTextFile = filebuffer
		fo.close()



# ###############################                  #####################################
# ###############################   Result table   #####################################
# ###############################                  #####################################

# 1 - LIST A SPECIFIC RECORD
# SHOULD BE PROTECTED API
# MAKING PUBLIC API for WAQAR

@app.route('/api/v1.0/result/<execution_id>', methods=['GET'])
def DisplaySpecficResult(execution_id):
		# verify user
		#headers = request.headers
		#auth = headers.get("x-api-key")
		#if auth:
		#	member_id = Execution.query.filter_by(execution_id=execution_id).first().member_id
		#	var_api_key = Members.query.filter_by(member_id=member_id).first().api_key
		#	if auth != var_api_key:
		#		return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
		#	else:
		#		print (jsonify({"message": "OK: Authorized"}), 200)
		#else: 
		#	return jsonify({"error": "API key missing"}), 401

		allResults = Result.query.filter_by(execution_id=execution_id).all()
		return jsonify(allResults = Result.serialize_list(allResults))


@app.route('/api/v1.0/result/retrieve', methods=['POST'])
def DisplaySpecficResultbyExecutionID():
		var1 = request.form['execution_id']
		# verify user
		#headers = request.headers
		#auth = headers.get("x-api-key")
		#if auth:
		#	member_id = Execution.query.filter_by(execution_id=execution_id).first().member_id
		#	var_api_key = Members.query.filter_by(member_id=member_id).first().api_key
		#	if auth != var_api_key:
		#		return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
		#	else:
		#		print (jsonify({"message": "OK: Authorized"}), 200)
		#else: 
		#	return jsonify({"error": "API key missing"}), 401
		allResults = Result.query.filter_by(execution_id=var1) .all()
		return jsonify(allResults = Result.serialize_list(allResults))
		#return jsonify(ResultID=ResultsRecords.result_id, 
		#	ExecutionID=ResultsRecords.execution_id, 
		#	Probability=ResultsRecords.probability, 
		#	Imagename=ResultsRecords.imagename,
		#	Prediction=ResultsRecords.prediction)


# ###############################                    ####################################
# ################################   MEMBERS TABLE   ####################################
# ################################                   ####################################

#2 - FUll LIST of RECORD
@app.route('/api/v1.0/mb', methods=['GET'])
def DisplayAllMember():
	MembersRecord = Members.query.all()
	return jsonify(MembersRecord = Members.serialize_list(MembersRecord))


# 1 - INSERT/CREATE NEW RECORD
# PROTECTED ADMIN API
# HOW to PROTECT???
# ??????????????????????????????????????????

#@app.route('/api/v1.0/members/add', methods=['POST'])
@app.route('/api/v1.0/mb/add', methods=['POST'])
def insertMembers():
	newmember_id = request.form['member_id']
	newmembername = request.form['membername']
	newrole = request.form['role']
	newapi_key = request.form['api_key']
	newcreated_on = request.form['created_on']
	members = Members(newmember_id, newmembername, newrole, newapi_key, newcreated_on)
	db.session.add(members)
	db.session.commit()
	print ("A NEW MEMBERS Record ADDED Successfully!")
	varRole = newrole
	if newrole == 'C' :
		var1 = newmember_id
		print(var1)
		var2 = newmembername
		var3 = '100'
		var4 = 'NOW()'
		customer = Customer(var1, var2, var3, var4)
		db.session.add(customer)
		db.session.commit()
		print ("Record ADDED CUSTOMER RECORD Successfully!")
		CustomerRecords = Customer.query.all()
		print (jsonify(CustomerRecords = Customer.serialize_list(CustomerRecords)))
		#members = Members(var1, newmembername, newrole, newapi_key, newcreated_on)
		#db.session.add(members)
		#db.session.commit()
		#print ("A NEW MEMBERS Record ADDED Successfully!")
		MembersRecord = Members.query.all()
		return jsonify(MembersRecord = Members.serialize_list(MembersRecord))
	elif newrole == 'S' :
		var1 = newmember_id
		print (var1)
		var2 = newmembername
		var3 = '100'
		var4 = 'NOW()'
		supplier = Supplier(var1, var2, var3, var4)
		db.session.add(supplier)
		db.session.commit()
		print ("Record ADDED SUPPLIER RECORD Successfully!")
		SupplierRecords = Supplier.query.all()
		print (jsonify(SupplierRecords = Supplier.serialize_list(SupplierRecords)))
		#members = Members(var1, newmembername, newrole, newapi_key, newcreated_on)
		#db.session.add(members)
		#db.session.commit()
		#print ("A NEW MEMBERS Record ADDED Successfully!")
		MembersRecord = Members.query.all()
		return jsonify(MembersRecord = Members.serialize_list(MembersRecord))
	elif newrole == 'CS':
		var1 = newmember_id
		print(var1)
		var2 = newmembername
		var3 = '100'
		var4 = 'NOW()'
		customer = Customer(var1, var2, var3, var4)
		db.session.add(customer)
		db.session.commit()
		print ("A NEW MEMBERS Record ADDED Successfully!")
		print ("Record ADDED CUSTOMER RECORD Successfully!")
		CustomerRecords = Customer.query.all()
		print (jsonify(CustomerRecords = Customer.serialize_list(CustomerRecords)))
		var1 = str(newmember_id)
		print (var1)
		var2 = newmembername
		var3 = '100'
		var4 = 'NOW()'
		supplier = Supplier(var1, var2, var3, var4)
		db.session.add(supplier)
		db.session.commit()
		print ("Record ADDED SUPPLIER RECORD Successfully!")
		SupplierRecords = Supplier.query.all()
		print (jsonify(SupplierRecords = Supplier.serialize_list(SupplierRecords)))
		#members = Members(var1, newmembername, newrole, newapi_key, newcreated_on)
		#db.session.add(members)
		#db.session.commit()
		#print ("A NEW MEMBERS Record ADDED Successfully!")
		MembersRecord = Members.query.all()
		return jsonify(MembersRecord = Members.serialize_list(MembersRecord))
	else:
		return ("Either RECORD ALREADY EXISTS or Please check the ROLE entered (It can only be 'C' for Customers, 'S' for Supplier or 'CS' for Customer/Supplier roles)")
		MembersRecord = Members.query.all()
		return jsonify(MembersRecord = Members.serialize_list(MembersRecord))



# 2 - LIST A SPECIFIC RECORD
# PROTECTED PUBLIC API
### do we need this?????????

@app.route('/api/v1.0/mb/<member_id>', methods=['GET'])
def DisplaySpecficMember(member_id):
	# verify user
	headers = request.headers
	auth = headers.get("x-api-key")
	if auth:
		var_api_key = Members.query.filter_by(member_id=member_id).first().api_key
		if auth != var_api_key:
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
		else:
			print (jsonify({"message": "OK: Authorized"}), 200)
	else: 
		return jsonify({"error": "API key missing"}), 401

	allMembers = Members.query.filter_by(member_id=member_id).first()
	return jsonify(Member_ID = allMembers.member_id,
							MemberName = allMembers.membername,
							Role = allMembers.role,
							Api_KeysName = allMembers.api_key,
							Created_On = allMembers.created_on)


# 4 - EDIT RECORD
# PROTECTED PUBLIC API

@app.route('/api/v1.0/members/<member_id>/update', methods=['PUT', 'POST'])
def UpdateMembers(member_id):
	# verify user
	headers = request.headers
	auth = headers.get("x-api-key")
	if auth:
		var_api_key = Members.query.filter_by(member_id=member_id).first().api_key
		if auth != var_api_key:
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
		else:
			print (jsonify({"message": "OK: Authorized"}), 200)
	else: 
		return jsonify({"error": "API key missing"}), 401

	# get customer record
	members = Members.query.filter_by(member_id=member_id).first()
	# request variables
	newmembername = request.form['membername']
	newrole = request.form['role']
	newapi_key = 'None'
	newcreated_on = request.form['created_on']

	# skip empty variables, only change non-empty input from form
	if newmembername == 'None':
		pass
	else: members.membername = newmembername
	if newrole == 'None':
		pass
	else: members.role = newrole
	if newapi_key == 'None':
		pass
	if newcreated_on == 'None':
		pass
	else: members.created_on = newcreated_on
	# update record
	db.session.commit()
	print ("Record UPDATED Successfully!")
	MembersRecords = Members.query.filter_by(member_id=member_id).first()
	return jsonify(Member_ID = MembersRecords.member_id,
							MemberName = MembersRecords.membername,
							Role = MembersRecords.role,
							Api_Key = MembersRecords.api_key,
							Created_On = MembersRecords.created_on)


# 5 - DELETE RECORD
# PROTECTED PUBLIC API

@app.route('/api/v1.0/members/<member_id>/delete', methods=['DELETE'])
def DeleteRecordMembers(member_id):

	# verify user
	headers = request.headers
	auth = headers.get("x-api-key")
	if auth:
		var_api_key = Members.query.filter_by(member_id=member_id).first().api_key
		if auth != var_api_key:
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
		else:
			print (jsonify({"message": "OK: Authorized"}), 200)
	else: 
		return jsonify({"error": "API key missing"}), 401

	DeleteRecord = Members.query.filter_by(member_id=member_id).first()
	db.session.delete(DeleteRecord)
	db.session.commit()
	print ("Record DELETED Successfully!")
	DeleteRecord = Members.query.all()
	return jsonify(DeleteRecord = Members.serialize_list(DeleteRecord))



#########################################################################################
##### NEW UPLOAD With API KEY TESTING - Docker BUILD Phase - Threading / Stream Way #####
#########################################################################################

# 1 - UPLOAD NEW MODEL
# PROTECTED PUBLIC API

@app.route('/api/v2.0/model/upload', methods=['POST', 'GET'])
def singlethread_upload():
	if request.method == 'POST':
		starttime = time.time()

		# receive variables
		var2 = request.form['modelname'] ###### var2 must be the name of the original modelname ######

		try: var1 = Models.query.order_by(Models.model_id.desc()).first().model_id + 1
		except: var1 = 1
		print (var1)
		
		var9 = request.form['membername']
		suppliername = var9

		supplierid = Supplier.query.filter_by(suppliername=var9).first().member_id  # only being used for querying purpose
		var4 = supplierid
		print (var4)

		var6 = 'NOW()'
		print (var6)

		var7 = request.form['price']
		print (var7)

		var8 = request.form['tag']
		print (var8)

		print ("i am here")

		model_tag = var2 + "_" + var8
		full_docker_repo = "chiefaidocker/models" + ":" + str.lower(model_tag)

		# API verification
		var_api_key = Members.query.filter_by(membername=var9).first().api_key
		print (var_api_key)

		headers = request.headers
		auth = headers.get("x-api-key")
		print (auth)

		if auth:
			var_api_key = Members.query.filter_by(member_id=supplierid).first().api_key
			if auth != var_api_key:
				return jsonify({"error": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
			else:
				print (jsonify({"message": "OK: Authorized"}), 200)
		else: 
			return jsonify({"error": "API key missing"}), 401


		# check model name is unique or belongs to supplier
		if Models.query.filter_by(modelname=var2).first(): # check if model exists for any user

			if Models.query.filter_by(modelname = var2, member_id = var4).count() == 0: # is it associated with the logged in user
				return jsonify({"error": "this model name already exists and does not belong to the current user"})

			elif Models.query.filter_by(modelname = var2, member_id = var4, tag=var8).first(): # does this version already exist
				return jsonify({"error": "this version of the chosen model already exists, please choose a different version number"})

			elif Models.query.filter_by(modelname = var2, member_id = var4, tag=var8).first(): # the model name is associated to the user, and the propsed version doesn't exist
				pass
		else: pass

		# upload file
		fileB = request.files['zipped_model_folder']
		filenameB = secure_filename(fileB.filename)
		
		if fileB and allowed_file(filenameB):
			executor_dir = "/home/chiefai/production/members/supplier_" + str(var4)  # check if model folder exist #
			executorPath = os.path.join(executor_dir, filenameB) # path to zipped model folder
			print("executor dir: ", executor_dir)
			print("executor path: ", executorPath)
			print("filenameB: ", filenameB)
		
			if os.path.exists(executor_dir):
				print('removing existing customer data path')
				shutil.rmtree(executor_dir)

			print('creating new customer data path')
			os.makedirs(executor_dir, exist_ok=True) # In this line os.makedirs("path/to/directory", exist_ok=bool) makes it accept multiple files in the same directory or folder
			fileB.save(executorPath) # save fileB
			
			# unzipping file
			if zipfile.is_zipfile(executorPath):
				print("unzipping folder")

				with zipfile.ZipFile(executorPath) as zip_file:
					for member in zip_file.namelist():
						filename = os.path.basename(member)

						# skip directories
						if not filename:
							continue

						# copy file (taken from zipfile's extract)
						source = zip_file.open(member)
						target = open(os.path.join(executor_dir, filename), "wb")
						with source, target:
							shutil.copyfileobj(source, target)
							print(target, " :unzipped successfully!")
		
				print("removing zip archive: ", executorPath)			
				os.remove(executorPath)
				print("...removed!")

		else: raise ("ERROR: Filename extension is incorrect - it must be a ZIP archive")


		print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " upload done! and now docker process started")

		try:
			cli = docker.from_env()
			cli = APIClient(base_url='unix://var/run/docker.sock')
			response = [line for line in cli.build(path=executor_dir, dockerfile="Dockerfile", rm=True, tag=full_docker_repo, nocache=True)]
			cli.push(full_docker_repo, tag=None, stream=False, auth_config=None, decode=False)

			print (response)
			print (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " Docker Image Building Process Finished")

			print("docker build complete... \n removing customer files...")

			try: shutil.rmtree(executor_dir)
			except: pass

		except docker.errors.APIError as error:
			raise error

		##################################################
		# UNZIPPED File Without Extension (filename.zip) #
		##################################################
	
		models_table = Models(var1, var2, full_docker_repo, var4, var6, var7, var8)

		db.session.add(models_table)
		db.session.commit()


		endtime = time.time()
		#sleep(75)
		executiontime = (endtime - starttime)

		current_uploaded_model_id = var1
		print (current_uploaded_model_id)

		a_dict = {}
		buildtime = executiontime
		modelid = current_uploaded_model_id
		docker_logging = str(response)

		for variable in ["buildtime", "modelid", "docker_logging"]:
			a_dict[variable] = eval(variable)

	return jsonify(a_dict)


#########################################
###### EXECUTE - Docker RUN Phase #######
#########################################

# 1 - EXECUTE MODEL
# PROTECTED PUBLIC API

@app.route('/api/v1.0/model/execute', methods=['POST'])
def newexecutapi_dockerrun_mdc():
	if request.method == 'POST':
		
		starttime = time.time()
		
		var1 = request.form['modelname']
		version = request.form['tag']
		
		# check modelname and tag link to an existed model record
		if Models.query.filter_by(modelname=var1,tag=version).first():
			
			chosen_model = Models.query.filter_by(modelname=var1,tag=version).first()
			dockerimagename = chosen_model.modelpath
			var2 = chosen_model.model_id

		else: raise RuntimeError("the chosen model and version does not exist")
	
		var5 = request.form['membername']
		memberid = Members.query.filter_by(membername=var5).first().member_id
		
		print (var5)
		print ("i am here")

		var_api_key = Members.query.filter_by(member_id=memberid).first().api_key
		print (var_api_key)
		headers = request.headers
		auth = headers.get("x-api-key")
		print (auth)

		if auth:
			if auth != var_api_key :
				return jsonify({"ERROR": "Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
			else:
				print  (jsonify({"message": "OK: Authorized"}), 200)
		else: 
			return jsonify({"error": "API key missing"}), 401


		#### NEW CODE HERE ####
		# check if the post request has the file part
		if 'zipped_test_image' not in request.files:
			flash('No file part')
			return redirect(request.url)

		fileA = request.files['zipped_test_image']

		# if user does not select file, browser also

		# submit a empty part without filename
		# if fileA.filename == '':
		#   flash('No selected file')
		#   return redirect(request.url)

		filenameA = secure_filename(fileA.filename)

		if fileA and allowed_file(filenameA):
			customer_dir = "/home/chiefai/production/members/customer_" + str(memberid) + "/"
			if os.path.exists(customer_dir):
				num_existing_files = len([f for f in os.listdir(customer_dir)]) + 1
			else: num_existing_files = 0
			Data_dir = "/home/chiefai/production/members/customer_" + str(memberid) + "/data" + str(num_existing_files) # check if model folder exist#
			DataPath = os.path.join(Data_dir, filenameA)
			
			try: os.makedirs(Data_dir, exist_ok=False) # In this line os.makedirs("path/to/directory", exist_ok=bool) makes it accept multiple files in the same directory or folder
			except:
				#OSError as error: raise error
				num_existing_files = num_existing_files * random.randint(0,99) * random.randint(0,99) - random.randint(0,99)
 
				Data_dir = "/home/chiefai/production/members/customer_" + str(memberid) + "/data" + str(num_existing_files) # check if model folder exist#
				os.makedirs(Data_dir, exist_ok=False) 

			# save file
			fileA.save(DataPath)
			
			num_of_images = 1 # if it's not a ZIP file, we assume the customer has uploaded a single image

			if zipfile.is_zipfile(DataPath):
				print("unzipping folder")
				
				list_of_names = zipfile.ZipFile(DataPath).namelist()
				num_of_images = 0 # count number of images submitted
				for name in list_of_names:
					if allowed_file(name): num_of_images = num_of_images+1

				print("number ", num_of_images)
				
				with zipfile.ZipFile(DataPath) as zip_file:
					
					
					for member in zip_file.namelist():
						filename = os.path.basename(member)

						# skip directories
						if not filename:
							continue

						# copy file (taken from zipfile's extract)
						source = zip_file.open(member)
						target = open(os.path.join(Data_dir, filename), "wb")
						with source, target:
							shutil.copyfileobj(source, target)
							print(target, " :unzipped successfully!")
		
				print("remove zip archive: ", DataPath)			
				os.remove(DataPath)

		else: return jsonify({"traceback": "Filename extension is incorrect - it must be a ZIP archive or other supported image format"}), 401

		# check if customer has enough credits
		A = Customer.query.filter_by(member_id=memberid).first().credits
		B = Models.query.filter_by(modelname=var1).first().price

		total_cost = B*num_of_images

		if A >= total_cost: pass
		else: raise RuntimeError("Customer does not have sufficient credits to execute this model")

		##########################
		# DOCKER MODEL EXECUTION #
		##########################

		####Docker Container Variables####

		try:
			volumepathinsidecontainer = '/data/'
			localpathtofoldertomounton = Data_dir + '/'


			# low-level pydocker API
			cli = docker.APIClient(base_url='unix://var/run/docker.sock')
			pred_container = cli.create_container(
			image = dockerimagename,
			stdin_open = True,
			tty = True,
			command = 'python3' + ' ' + 'run_classification.py' + ' ' + '--imageDir' + ' ' + '/data/',
			volumes = localpathtofoldertomounton,
			host_config = cli.create_host_config(
			binds = {localpathtofoldertomounton: {
			'bind': volumepathinsidecontainer,
			'mode': 'rw',}
				}
			)
			)

			containername = pred_container['Id']

			cli.start(containername)
			cli.wait(containername)

			docker_logs = cli.logs(containername)
			
			print("logs:", docker_logs)
			print ("container ID:", containername)
			print (localpathtofoldertomounton)
			print (volumepathinsidecontainer)

			cli.remove_container(pred_container, v=False, link=False, force=False)

		except docker.errors.APIError as error:
			cli.remove_container(containername, v=False, link=False, force=False)
			raise error
		except docker.errors.ContainerError as error:
			cli.remove_container(containername, v=False, link=False, force=False)
			raise error
		except docker.errors.ImageNotFound as error:
			cli.remove_container(containername, v=False, link=False, force=False)
			raise error

		########################
		# Credit System UPDATE #
		########################
		A = Customer.query.filter_by(member_id=memberid).first().credits
		tempvar = Models.query.filter_by(modelname=var1).first().member_id
		C = Supplier.query.filter_by(member_id=tempvar).first().commission
		D = A - total_cost

		E = (70*total_cost)/100 #### Percentage calculation - 70% goes to Supplier, so 14 credits (which is 70% of 20 credits) is added to the Supplier Table ####
		F = (30*total_cost)/100 #### Percentage calculation - 30% goes to Chief AI, so  7 credits (which is 30% of 20 credits) is added to the Execution Table ####

		G = C + E #### G contains the ADDED commission in percentage converted to credits to the Supplier Credits Earned ####

		balanceMinusCustomer = D
		balanceAddSupplier = G

		customerID = memberid
		supplierID = tempvar

		customerName = Customer.query.filter_by(member_id=memberid).first().customername
		updatedBalanceCustomer = Customer(customerID, customerName, balanceMinusCustomer, 'NOW()')
		db.session.merge(updatedBalanceCustomer)
		db.session.commit()

		supplierName = Supplier.query.filter_by(member_id=tempvar).first().suppliername
		updatedBalanceSupplier = Supplier(supplierID, supplierName, balanceAddSupplier, 'NOW()')
		db.session.merge(updatedBalanceSupplier)
		db.session.commit()

		datasetsID = Datasets.query.order_by(Datasets.datasets_id.desc()).first().datasets_id + 1
		#datasetsID = Datasets.query.order_by(Datasets.datasets_id.desc()).first() #### ONLY UNCOMMENT THIS CODE FOR FIRST TIME DATASETS RECORD ####
		datasets_table = Datasets(datasetsID, customerID, DataPath , 'NOW()')
		db.session.add(datasets_table)
		db.session.commit()


		# create record for execution table 
		model_id = Models.query.filter_by(modelname=var1).first().model_id
		member_id = Customer.query.filter_by(member_id=memberid).first().member_id

		try: execute_id = Execution.query.order_by(Execution.execution_id.desc()).first().execution_id + 1
		except: execute_id = 1 #if execution table is empty, set execute id to 1
		
		endtime = time.time()
		executionstime = (endtime - starttime)

		chargedCredits = total_cost
		revenue_Earned_Chiefai = F
		execution_time = int(executionstime)
		print (F)
		
		# add record to execution table
		saveIntoExecutionTable = Execution(execute_id, model_id, customerID, 'NOW()', chargedCredits, revenue_Earned_Chiefai, execution_time)
		db.session.add(saveIntoExecutionTable)	


		try:
			# parse customer result JSON
			with open(localpathtofoldertomounton + "result.json", 'r') as read_file:
				json_result = json.load(read_file)
				print (json_result)

			try: result_id = Result.query.order_by(Result.result_id.desc()).first().result_id + 1
			except: result_id = 1

			# add records to result table for multi or single file execution
			for i, result in enumerate(json_result['result']):

				if not result['probability']: predict_proba = None
				else: predict_proba = result['probability'] 

				newrecord_resultstable = Result(
					result_id=result_id + i,
					execution_id=execute_id, 
					imagename=result['imagename'].split('/')[-1], 
					prediction=result['prediction'], 
					probability=predict_proba)

				db.session.add(newrecord_resultstable)
				print (result)
			
			db.session.commit()

			# remove data directory after execution is complete
			print('removing existing customer data path')
			shutil.rmtree(Data_dir)

		except Exception as err:
			raise err

		a_dict = {}
		executiontime = execution_time
		resultoutput = json_result['result']
		docker_logging = str(docker_logs)
		for variable in ["executiontime", "resultoutput", "docker_logging"]:
			a_dict[variable] = eval(variable)

	return jsonify(a_dict)


##################################################################################################################################
if __name__ == '__main__':
	handler = RotatingFileHandler('development-error.log', maxBytes=10000, backupCount=3)
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.ERROR)
	logger.addHandler(handler)
	app.run(host='0.0.0.0', port=5000, debug=True)
