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


# ###############################  COMPLEX DOCKER EXECUTIONS for running model  ####################################
# ###############################                                        	    ####################################


#### RUN DOCKER USING FLASK ####
@app.route('/api/v1.0/startdockerhelloworld', methods=['POST'])
def dockerhellowworld():
	dockerimage = request.form['dockerimage']
	commands = request.form['commands']
	client = docker.from_env()
	return client.containers.run(dockerimage, commands)
####

#### PULL DOCKER USING FLASK ####
@app.route('/api/v1.0/dockerpull', methods=['POST'])
def dockerpull():
	client = docker.from_env()
	image = client.images.pull('alpine:latest')
	#sleep(5)
	output = client.images.list()
	print (*output, sep = "\n")
	#return str(output)
	return str(print (*output, sep = "\n"))
####

#### List Docker Images ####
@app.route('/api/v1.0/dockerlistimages', methods=['POST'])
def dockerlistimages():
	import docker
	client = docker.from_env()
	output = client.images.list()
	print (*output, sep = "\n")
	return str(output)
####

#### List Docker Containers ####
@app.route('/api/v1.0/dockerlistcontainers', methods=['POST'])
def dockerlistcontainers():
	client = docker.from_env()
	output = client.containers.list()
	print (output)
	return str(output)
####

#### Build Docker Image ####
@app.route('/api/v1.0/dockerbuild', methods=['POST'])
def dockerbuild():
	dockerfile = request.form['Dockerfile']
	path = request.form['imagepath']
	tag = request.form['tag']
	cli = docker.from_env()
	cli = APIClient(base_url='unix://var/run/docker.sock')
	response = [line for line in cli.build(path=path, dockerfile=dockerfile, rm=True, tag=tag)]
	print (response)
	return str(response)
###

#### Run Docker Container ####
@app.route('/api/v1.0/dockerrun', methods=['POST'])
def dockerrun():
	dockermodel = request.form['dockermodel']
	client = docker.from_env()
	client = docker.DockerClient(base_url='unix://var/run/docker.sock')
	output = client.containers.run(dockermodel, detach=False)
	print (output)
	return str(output)
###

#### Run Docker Container ####
@app.route('/api/v1.0/dockercreatecontainer', methods=['POST'])
def dockercreatecontainer():
	cli = docker.from_env()
	cli = APIClient(base_url='unix://var/run/docker.sock')
	container_id = cli.create_container('chiefaidocker/models:histo_ai', volumes=['/mnt/vol1', '/mnt/vol2'],
	host_config=cli.create_host_config(binds=[
		'/home/chiefai/histo_ai/:/mnt/vol2:rw',
		'/histo_ai:/mnt/vol1:rw',])
	)
	cli.start(container_id)
	print(container_id)
	return str(container_id)

#### CREATE DOCKER CONTAINER ####
@app.route('/api/v1.0/dockercreatecontainerv1', methods=['POST'])
def dockercreatecontainerv1():
	cli = docker.from_env()
	cli = APIClient(base_url='unix://var/run/docker.sock')
	cli.create_container(
	image='ubuntu:18.04',
	stdin_open=True,
	tty=True,
	command=['/bin/bash'],
	volumes=['/histo_ai'],
	host_config=cli.create_host_config(
			binds={ os.getcwd(): {
					'bind': '/histo_ai_draft',
					'mode': 'rw',
					}
				}
			),
	name='histo_ai',
	working_dir='/histo_ai_draft'
	)
	cli.start('histo_ai')
	cli.wait('histo_ai')
	output = cli.logs('histo_ai')
	print('histo_ai')
	return str('histo_ai')
##########################

#### CREATE DOCKER CONTAINER ####
@app.route('/api/v1.0/dockercreatecontainerv2', methods=['GET', 'POST'])
def dockercreatecontainerv2():
	cli = docker.from_env()
	cli = APIClient(base_url='unix://var/run/docker.sock')
	start = time()
	cli.create_container(
	image='chiefaidocker/models:histo_ai',
	stdin_open=True,
	tty=True,
	command=['/bin/bash'],
	#'python3 h5_histo_executor.py test0.tiff'],
	volumes=['/histo_ai'],
	host_config=cli.create_host_config(
			binds={ '/home/chiefai/histo_ai_draft/': {
					'bind': '/histo_ai_draft',
					'mode': 'rw',
					}
				}
			),
	name='histo_ai',
	working_dir='/histo_ai_draft'
	)
	cli.start('histo_ai')
	cli.wait('histo_ai')
	output = cli.logs('histo_ai')
	print('Container Started : {}'.format(cli.status))
	#exec_log = container.exec_run("/bin/bash -c 'for i in `seq 1 10`; do echo $i; sleep 1;done;'",
	#                              stdout=True,
	#                              stderr=True,
	#                              stream=True)

	#for line in exec_log[1]:
	#    print(line, end='')

	print('Container Finished outputting log : {}'.format(time() - start))
	container.stop()
	return str(exec_log)

###################################################################################################################################

# ###############################               #####################################
# ###############################   CUSTOMERS   #####################################
# ###############################               #####################################


# 1 - INSERT/CREATE NEW RECORD #### 
# PRIVATE ENDPOINT TO CHIEF #######
@app.route('/api/v1.0/customers/add', methods=['POST'])
#@app.route('/AddRecordCustomer', methods=['GET', 'POST'])
def AddRecordCustomer():
	if request.method == 'POST':
		newmember_id = request.form['member_id']
		newcustomername = request.form['customername']
		newcredits = request.form['credits']
		newcreated_on = request.form['created_on']
		customer = Customer(newmember_id, newcustomername, newcredits, newcreated_on)
		db.session.add(customer)
		db.session.commit()
		print ("Record ADDED Successfully!")
		CustomerRecords = Customer.query.all()
		return jsonify(CustomerRecords = Customer.serialize_list(CustomerRecords))


# 2 - LIST ALL RECORDS
# PRIVATE ENDPOINT TO CHIEF or Do we need it? Decide #######
@app.route('/api/v1.0/customers', methods=['GET'])
#@app.route('/execute/AllCustomersJsonify.json', methods=['GET', 'POST'])
def DisplayAllCustomers():
	allCustomer = Customer.query.all()
	return jsonify(allCustomer = Customer.serialize_list(allCustomer))


# 2 - EDIT RECORD
# PROTECTED PUBLIC API

@app.route('/api/v1.0/customers/<member_id>/update', methods=['PUT'])
def UpdateCustomer(member_id):
	headers = request.headers
	auth = headers.get("x-api-key")	
	if auth:
		var_api_key = Members.query.filter_by(member_id=member_id).first().api_key
		if auth != var_api_key :
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key mismatch"}), 401
		else: print (jsonify({"message": "OK: Authorized"}), 200)
	else: return jsonify({"error": "API key missing"}), 401
	# get customer record
	customer = Customer.query.filter_by(member_id=member_id).first()
	# request variables
	newcustomername = request.form['customername']
	newcredits = request.form['credits']
	newcreated_on = request.form['created_on']
	# skip empty variables, only change non-empty input from form
	if newcustomername == 'None':
		pass
	else: customer.customername = newcustomername
	if newcredits == 'None':
		pass
	else: 
		customer.credits = newcredits
	if newcreated_on == 'None':
		pass
	else: 
		customer.created_on = newcreated_on
	# update record
	db.session.commit()
	print ("Record UPDATED Successfully!")
	CustomerRecords = Customer.query.filter_by(member_id=member_id).first()
	return jsonify(Member_id=CustomerRecords.member_id,
							CustomerName=CustomerRecords.customername,
							Credits=CustomerRecords.credits,
							Created_On=CustomerRecords.created_on)


# 5 - DELETE RECORD
# PROTECTED PUBLIC API

@app.route('/api/v1.0/customers/<member_id>/delete', methods=['DELETE'])
def DeleteRecordCustomer(member_id):
	headers = request.headers
	auth = headers.get("x-api-key")
	if auth:
		var_api_key = Members.query.filter_by(member_id=member_id).first().api_key
		if auth != var_api_key :
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key mismatch"}), 401
		else: print (jsonify({"message": "OK: Authorized"}), 200)
	else: return jsonify({"error": "API key missing"}), 401

	DeleteRecord = Customer.query.filter_by(member_id=member_id).first()
	db.session.delete(DeleteRecord)
	db.session.commit()
	print ("Record DELETED Successfully!")
	CustomerRecords = Customer.query.all()
	return jsonify(CustomerRecords = Customer.serialize_list(CustomerRecords))


# ###############################               ###############################$
# ###############################   SUPPLIERS   ###############################$
# ###############################               ###############################$


# 1 - INSERT/CREATE RECORD
@app.route('/api/v1.0/suppliers/add', methods=['POST'])
#@app.route('/AddRecordSupplier', methods=['GET', 'POST'])
def AddRecordSupplier():
	if request.method == 'POST':
		newmember_id = request.form['member_id']
		newsuppliername = request.form['suppliername']
		newcommission = request.form['commission']
		newcreated_on = request.form['created_on']
		supplier = Supplier(newmember_id, newsuppliername, newcommission, newcreated_on)
		db.session.add(supplier)
		db.session.commit()
		print ("Record ADDED Successfully!")
		SupplierRecords = Supplier.query.all()
	return jsonify(SupplierRecords = Supplier.serialize_list(SupplierRecords))



# 2 - LIST ALL RECORDS
@app.route('/api/v1.0/suppliers', methods=['GET'])
#@app.route('/execute/AllSuppliersJsonify.json', methods=['GET', 'POST'])
def DisplayAllSuppliers():
	allSuppliers = Supplier.query.all()
	return jsonify(allSuppliers = Supplier.serialize_list(allSuppliers))


# 4 - EDIT RECORD
@app.route('/api/v1.0/suppliers/<member_id>/update', methods=['PUT', 'POST'])
def UpdateSupplier(member_id):
	# get supplier record
	supplier = Supplier.query.filter_by(member_id=member_id).first()
	# request variables
	newsuppliername = request.form['suppliername']
	newcommission = request.form['commission']
	newcreated_on = request.form['created_on']
	# skip empty variables, only change non-empty input from form
	if newsuppliername == 'None':
		pass
	else: supplier.suppliername = newsuppliername
	if newcommission == 'None':
		pass
	else: supplier.commission = newcommission
	if newcreated_on == 'None':
		pass
	else: supplier.created_on = newcreated_on
	# update record
	db.session.commit()
	print ("Record UPDATED Successfully!")
	SupplierRecords = Supplier.query.filter_by(member_id=member_id).first()
	return jsonify(Member_id=SupplierRecords.member_id,
							SupplierName=SupplierRecords.suppliername,
							Commission=SupplierRecords.commission,
							Created_On=SupplierRecords.created_on)


# 5 - DELETE RECORD
@app.route('/api/v1.0/suppliers/<member_id>/delete', methods=['DELETE'])
def DeleteRecordSupplier(member_id):
	DeleteRecord = Supplier.query.filter_by(member_id=member_id).first()
	db.session.delete(DeleteRecord)
	db.session.commit()
	print ("Record DELETED Successfully!")
	SupplierRecords = Supplier.query.all()
	return jsonify(SupplierRecords = Supplier.serialize_list(SupplierRecords))

# ###############################            ########################################
# ###############################   MODELS   ########################################
# ###############################            ########################################

# 1 - INSERT/CREATE NEW MODEL
@app.route('/api/v1.0/models/add', methods=['POST'])
def insertModel():
	newmodel_id = request.form['model_id']
	newmodelname = request.form['modelname']
	newmodelpath = request.form['model_path']
	newmember_id = request.form['member_id']
	newcreated_on = request.form['created_on']
	newprice = request.form['price']
	newtag = request.form['tag']
	
	Model = Models(newmodel_id, newmodelname, newmodelpath, newmember_id, newcreated_on, newprice, newtag)
	db.session.add(Model)
	db.session.commit()
	print ("Record ADDED Successfully!")
	ModelsRecords = Models.query.all()
	return jsonify(ModelsRecords = Models.serialize_list(ModelsRecords))

# 6 - RETRIEVE RECORD by Model_id
@app.route('/api/v1.0/models/retrievebymodelid', methods=['GET', 'POST'])
def RetrieveModelsbymodel_id():
	var1 = request.form['model_id']
	ModelsID = var1
	allModels = Models.query.filter_by(model_id=var1).first()
	return jsonify(Model_ID=allModels.model_id, ModelName=allModels.modelname,
							ModelPath=allModels.modelpath,
							MemberID=allModels.member_id, Created_On=allModels.created_on,
							Price=allModels.price, Tag=allModels.tag)


# 8 - Extras
@app.route('/api/v1.0/models/list_all_models', methods=['GET', 'POST'])
def listAllModels():
	models = Models.query.all()
	return render_template('list_all_models.html', myModels=models)



# ###############################   DATASETS    #####################################
# ###############################               #####################################

# 1 - ADD RECORD
@app.route('/api/v1.0/datasets/add', methods=['POST'])
def AddRecordDatasets():
	if request.method == 'POST':
		newdatasets_id = request.form['datasets_id']
		newmember_id = request.form['member_id']
		newdatasetsfilepath = request.form['datasetsfilepath']
		newcreated_on = request.form['created_on']
		datasets = Datasets(newdatasets_id, newmember_id, newdatasetsfilepath, newcreated_on)
		db.session.add(datasets)
		db.session.commit()
		print ("Record ADDED Successfully!")
		DatasetsRecord = Datasets.query.all()
	return jsonify(DatasetsRecord = Datasets.serialize_list(DatasetsRecord))


# 2 - LIST ALL RECORDS
@app.route('/api/v1.0/datasets', methods=['GET'])
def DisplayAllDatasets():
	allDatasets = Datasets.query.all()
	return jsonify(allDatasets = Datasets.serialize_list(allDatasets))


# 3 - LIST RECORD
@app.route('/api/v1.0/datasets/<datasets_id>', methods=['GET'])
def DisplaySpecificDatasets(datasets_id):
	allDatasets = Datasets.query.filter_by(datasets_id=datasets_id).first()
	return jsonify(Datasets_ID_Id=allDatasets.datasets_id, member_id=allDatasets.member_id,
							DatasetsFilePath=allDatasets.datasetsfilepath, Created_On=allDatasets.created_on)

# 4 - EDIT RECORD
@app.route('/api/v1.0/datasets/<datasets_id>/update', methods=['PUT', 'POST'])
def UpdateDatasets(datasets_id):
	# get datasets record
	datasets = Datasets.query.filter_by(datasets_id=datasets_id).first()
	# request variables
	newmember_id = request.form['member_id']
	newdatasetsfilepath = request.form['datasetsfilepath']
	newcreated_on = request.form['created_on']
	# skip empty variables, only change non-empty input from form
	if newmember_id == 'None':
		pass
	else: datasets.member_id = newmember_id
	if newdatasetsfilepath == 'None':
		pass
	else: datasets.datasetsfilepath = newdatasetsfilepath
	if newcreated_on == 'None':
		pass
	else: datasets.created_on = newcreated_on
	# update record
	db.session.commit()
	print ("Record UPDATED Successfully!")
	DatasetsRecords = Datasets.query.filter_by(datasets_id=datasets_id).first()
	return jsonify(Datasets_ID=DatasetsRecords.datasets_id,
							Member_id=DatasetsRecords.member_id,
							DatasetsFilePath=DatasetsRecords.datasetsfilepath,
							Created_On=DatasetsRecords.created_on)


# 5 - DELETE RECORD
@app.route('/api/v1.0/datasets/<datasets_id>/delete', methods=['DELETE'])
#@app.route('/DeleteRecordDatasets', methods=['GET', 'POST'])
def DeleteRecordDatasets(datasets_id):
#    var1 = request.form['datasets_id']
#    datasetsID = var1
	DeleteRecord = Datasets.query.filter_by(datasets_id=datasets_id).first()
	db.session.delete(DeleteRecord)
	db.session.commit()
	print ("Record DELETED Successfully!")
	DatasetsRecord = Datasets.query.all()
	return jsonify(DatasetsRecord = Datasets.serialize_list(DatasetsRecord))


# - EXTRA
## 5.5 - QUERY RECORD BY CUSTOMER ID FROM WEB FORM/POSTMAN
@app.route('/api/v1.0/datasets/retrieve', methods=['POST'])
#@app.route('/execute/DisplayQueryDatasetsJsonify.json', methods=['GET', 'POST'])
def RetreieveDatasets():
	var1 = request.form['member_id']
	allDatasets = Datasets.query.filter_by(member_id=var1).all()
	return jsonify(allDatasets = Datasets.serialize_list(allDatasets))
#################################################################################################################################


# ###############################   EXECUTIONS   ####################################
# ###############################                ####################################

# 1 - INSERT/CREATE NEW RECORD
@app.route('/api/v1.0/executions/add', methods=['POST'])
#@app.route('/AddRecordExecution', methods=['GET', 'POST'])
def AddRecordExecution():
	newexecution_id = request.form['execution_id']
	newmodel_id = request.form['model_id']
	newmember_id = request.form['member_id']
	newcreated_on = request.form['created_on']
	newcharged_credits = request.form['charged_credits']
	newrevenue_earned_chiefai = request.form['revenue_earned_chiefai']
	newexecution_time = request.form['execution_time']
	execution = Execution(newexecution_id, newmodel_id, newmember_id, newcreated_on, newcharged_credits, newrevenue_earned_chiefai, newexecution_time)
	db.session.add(execution)
	db.session.commit()
	print ("Record ADDED Successfully!")
	ExecutionsRecord = Execution.query.all()
	return jsonify(ExecutionsRecord = Execution.serialize_list(ExecutionsRecord))


# 2 - LIST RECORD
@app.route('/api/v1.0/executions/<execution_id>', methods=['GET'])
def DisplaySpecificExecution(execution_id):
	ExecutionID = Execution.query.filter_by(execution_id=execution_id).first().execution_id
	ModelID = Execution.query.filter_by(execution_id=execution_id).first().model_id
	MemberID = Execution.query.filter_by(execution_id=execution_id).first().member_id
	TimeStamp = Execution.query.filter_by(execution_id=execution_id).first().created_on
	ChargedCredits = Execution.query.filter_by(execution_id=execution_id).first().charged_credits
	RevenueEarnedChiefai = Execution.query.filter_by(execution_id=execution_id).first().commission_earned_chiefai
	ExecutionTime = Execution.query.filter_by(execution_id=execution_id).first().execution_time
	allExecutions = Execution(ExecutionID, ModelID, MemberID, TimeStamp, ChargedCredits, RevenueEarnedChiefai, ExecutionTime)
	return jsonify(Execution_ID=allExecutions.execution_id,
							Model_ID=allExecutions.model_id,
							Member_id=allExecutions.member_id,
							Created_On=allExecutions.created_on,
							ChargedCredits=allExecutions.charged_credits,
								RevenueEarnedChiefai=allExecutions.revenue_earned_chiefai,
														ExecutionTime=allExecutions.execution_time)

# 3 - LIST ALL RECORDS
@app.route('/api/v1.0/executions', methods=['GET'])
#@app.route('/execute/AllExecutionsJsonify.json', methods=['GET', 'POST'])
def DisplayAllExecutions():
	allExecutions = Execution.query.all()
	return jsonify(allExecutions=Execution.serialize_list(
		allExecutions))  #### Here in the Execution Table the result column has a decimal point therefore we had to def an ENCODER as a global setting at the top ###



# 4 - EDIT RECORD
@app.route('/api/v1.0/executions/<execution_id>/update', methods=['PUT', 'POST'])
def UpdateExecutions(execution_id):
	# get datasets record
	executions = Execution.query.filter_by(execution_id=execution_id).first()
	# request variables
	newmodel_id = request.form['model_id']
	newmember_id = request.form['member_id']
	newcreated_on = request.form['created_on']
	newcharged_credits = request.form['charged_credits']
	newrevenue_earned_chiefai = request.form['revenue_earned_chiefai']
	newexecution_time = request.form['execution_time']
	# skip empty variables, only chane non-empty input from form
	if newmodel_id == 'None':
		pass
	else: executions.model_id  = newmodel_id
	if newmember_id == 'None':
		pass
	else: executions.member_id = newmember_id
	if newcreated_on == 'None':
		pass
	else: executions.created_on = newcreated_on
	if newcharged_credits == 'None':
		pass
	else: executions.charged_credits = newcharged_credits
	if newrevenue_earned_chiefai == 'None':
		pass
	else: executions.revenue_earned_chiefai = newrevenue_earned_chiefai
	if newexecution_time == 'None':
		pass
	else: executions.execution_time = newexecution_time
	# update record
	db.session.commit()
	print ("Record UPDATED Successfully!")
	ExecutionsRecords = Execution.query.filter_by(execution_id=execution_id).first()
	return jsonify(Execution_ID=ExecutionsRecords.execution_id,
							Model_ID=ExecutionsRecords.model_id,
							Member_id=ExecutionsRecords.member_id,
							Created_On=ExecutionsRecords.created_on,
							ChargedCredits=ExecutionsRecords.charged_credits,
							RevenueEarnedChiefai=ExecutionsRecords.revenue_earned_chiefai,
														ExecutionTime=ExecutionRecords.execution_time)

# 5 - RETRIEVE DATA DUMP OF ALL EXECUTIONS

@app.route('/api/v1.0/executions/retrieveDict', methods=['GET', 'POST'])
#@app.route('/ExecutionsJsonify', methods=['GET', 'POST'])
def DisplayAllExecutionsInJasonifyModeUsingRawSQL():
	with engine.connect() as con:
		rs = con.execute("SELECT * FROM execution")
		return json.dumps([dict(r) for r in rs], cls=DecimalEncoder)
		fo = open("/home/chiefai/production/results/JsonDumpFile.json", 'w')
		filebuffer = JsonDumpFile
		fo.writelines(filebuffer)
		SaveTextFile = filebuffer
		fo.close()


# ###############################   Result table   #####################################
# ###############################                  #####################################

# 1 - LIST ALL RECORDS
@app.route('/api/v1.0/result', methods=['GET'])
def displayallresults():
	allresult = Result.query.all()
	return jsonify(allResult = Result.serialize_list(allresult))


# 2 - DELETE RECORD
# PROTECTED PUBLIC API

@app.route('/api/v1.0/result/<result_id>/delete', methods=['DELETE'])
def DeleteRecordResult(result_id):
	# verify user
	headers = request.headers
	auth = headers.get("x-api-key")
	if auth:
		member_id = Execution.query.filter_by(execution_id=execution_id).first().member_id
		var_api_key = Members.query.filter_by(member_id=member_id).first().api_key
		if auth != var_api_key:
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
		else:
			print (jsonify({"message": "OK: Authorized"}), 200)
	else: 
		return jsonify({"error": "API key missing"}), 401

	DeleteRecord = Result.query.filter_by(result_id=result_id).first()
	db.session.delete(DeleteRecord)
	db.session.commit()
	print ("Record DELETED Successfully!")
	ResultRecord = Result.query.all()
	return jsonify(ResultRecord = Result.serialize_list(ResultRecord))


# ###############################                   ####################################
# ###############################   MEMBERS TABLE   ####################################
# ###############################                   ####################################

# 1 - CHECK A RECORD EXISTS OR NOT
@app.route('/api/v1.0/members/checkmembers', methods=['POST'])
def checkMembers():
	varMembernameExistingFromTable = 'red'
	newmembername = request.form['membername']
	varMembernameFromPassingVar = newmembername
	print (varMembernameFromPassingVar)
	varMembernameExistingFromTable = db.session.query(Members.membername).filter_by(membername=newmembername).scalar()
	print (varMembernameExistingFromTable)
	if varMembernameExistingFromTable == varMembernameFromPassingVar:
		return ("yes")
	else:
		return ("no")

#2 - FUll LIST of RECORD
@app.route('/api/v1.0/members', methods=['GET'])
def DisplayAllMember():
	MembersRecord = Members.query.all()
	return jsonify(MembersRecord = Members.serialize_list(MembersRecord))


###########################################################################################
###### NEW UPLOAD With API KEY TESTING - Docker BUILD Phase - Threading / Stream Way ######
###########################################################################################


@app.route('/api/v1.0/model/upload_mdc', methods=['POST', 'GET'])
def newupload_mdc():
	@copy_current_request_context
	def save_file(closeAfterWrite):
		print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " i am doing")
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
		
			else:
				os.makedirs(executor_dir, exist_ok=True) # In this line os.makedirs("path/to/directory", exist_ok=bool) makes it accept multiple files in the same directory or folder
				fileB.save(executorPath) # save fileB
				
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

		else: raise Exception('An error occurred Executor Dir exists or . filename extension is WRONG....!!!!')

		closeAfterWrite()
		print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " write done! and now docker process started")

		tag = request.form['tag'] #model version number
		var2 = request.form['modelname']
		model_tag = var2 + "_" + tag

		full_docker_repo = "chiefaidocker/models" + ":" + str.lower(model_tag)

		cli = docker.from_env()
		cli = APIClient(base_url='unix://var/run/docker.sock')
		response = [line for line in cli.build(path=executor_dir, dockerfile="Dockerfile", rm=True, tag=full_docker_repo, nocache=True)]
		cli.push(full_docker_repo, tag=None, stream=False, auth_config=None, decode=False)
		print (response)
		print (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " Docker Image Building Process Finished")

		print("docker build complete... \n removing customer files...")
		shutil.rmtree(executor_dir)
		
	def passExit():
		pass

	if request.method == 'POST':
		starttime = time.time()
		var2 = request.form['modelname'] ########## var2 must be the name of the original modelname ######
		#var1 = request.form['model_id']
		var1 = Models.query.order_by(Models.model_id.desc()).first().model_id + 1
		print (var1)
		var9 = request.form['membername']
		#supplierid = Supplier.query.order_by(Supplier.member_id.desc()).first().member_id  # only being used for querying purpose
		suppliername = var9
		supplierid = Supplier.query.filter_by(suppliername=var9).first().member_id  # only being used for querying purpose
		#suppliername = Supplier.query.filter_by(member_id=supplierid).first().suppliername
		print (suppliername)
		var4 = supplierid
		print (var4)
		#var6 = request.form['created_on']
		var6 = 'NOW()'
		print (var6)
		var7 = request.form['price']
		#var7 = '20'
		print (var7)
		var8 = request.form['tag']
		print (var8)
		print ("i am here")

		model_tag = var2 + "_" + var8
		full_docker_repo = "chiefaidocker/models" + ":" + str.lower(model_tag)

		var_api_key = Members.query.filter_by(membername=var9).first().api_key
		print (var_api_key)
		headers = request.headers
		auth = headers.get("x-api-key")
		print (auth)
		#var9 = var_api_key
		#auth = 'None'
		#auth = var_api_key     # auth needs to be linked from the front end
		if auth != var_api_key :
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
			#return make_response(jsonify({"message": "ERROR: Unauthorized"}), 401)
			#return custom_401()
			#abort(401)
		else:
			print (jsonify({"message": "OK: Authorized"}), 200)

			#executor_dir = "/home/chiefai/production/members/supplier_" + str(var4) + "/executorFolder/" # check if model folder exist #          fileB = request.files['zipped_model_folder']
			fileB = request.files['zipped_model_folder']
			# fileA variable defined in save_file function
			filenameB = secure_filename(fileB.filename)
			#executorPath = os.path.join(executor_dir, filenameB) # path to zipped model folder
			normalExit = fileB.stream.close
			fileB.stream.close = passExit
			t = threading.Thread(target=save_file,args=(normalExit,))
			t.start()
			print ("i am here where i started the threading")

			##################################################
			# UNZIPPED File Without Extension (filename.zip) #
			##################################################
			#unzip_filename = filenameB.split('.')[0]
			#unzip_dir = os.path.join(executor_dir, unzip_filename)
			
			models_table = Models(var1, var2, full_docker_repo, var4, var6, var7, full_docker_repo)

			db.session.add(models_table)
			db.session.commit()
			endtime = time.time()
			#sleep(75)
			executiontime = (endtime - starttime)

			current_uploaded_model_id = Models.query.filter_by(modelname=var2).first().model_id
			print (current_uploaded_model_id)
			a_dict = {}
			buildtime = executiontime
			modelid = current_uploaded_model_id
			for variable in ["buildtime", "modelid"]:
				a_dict[variable] = eval(variable)
	
	return jsonify(a_dict)

	


###########################################################################################
################# UPDATED UPLOAD COMMANDS - AWS ECR DOCKER REGISTRY #######################
###########################################################################################

############################### TRY OUT CODE ########################################


@app.route('/api/v2.3/models/docker_push', methods=['POST', 'GET'])
def docker_push_v2_3():
	if request.method == 'POST':

		starttime = time.time()

		# initiate Docker client
		cli = docker.from_env()
		cli = APIClient(base_url='unix://var/run/docker.sock')

		# request form variables
		model_name = request.form['modelname'] # var2 must be the name of the original model
		model_id = Models.query.order_by(Models.model_id.desc()).first().model_id + 1 #var1
		supplier_name = request.form['membername'] #var9
		supplier_id = Supplier.query.filter_by(suppliername=supplier_name).first().member_id  # var4
		created_on = 'NOW()' #var6
		price = request.form['price'] #var7
		docker_tag = request.form['tag'] #var8 - this should be a version number

		docker_repo_name = os.path.join("chiefai", supplier_name, model_name)
		full_docker_tag = docker_repo_name + ":" + docker_tag

		# API key verification
		var_api_key = Members.query.filter_by(membername=supplier_name).first().api_key
		headers = request.headers
		auth = headers.get("x-api-key")

		print ("received form data and api key!")

		if auth != var_api_key :
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401

		else:
			print (jsonify({"message": "OK: Authorized"}), 200)

		# start file download from S3 bucket
		download_url = request.form['download-url']
		try:  
			docker_image = cli.import_image_from_url(
				download_url, 
				repository=docker_repo_name, 
				tag=docker_tag,
				changes=None)

		except docker.errors.APIError as error:
			raise error
		
		uploadtime = time.time() - starttime

		# Add record to models table

		models_table = Models(model_id, model_name, full_docker_tag, supplier_id, created_on, price, full_docker_tag)
		db.session.add(models_table)
		db.session.commit()
		
		# random stuff for the front end
		endtime = time.time()
		uploadtime = endtime - starttime

		modelid = model_id
		a_dict = {}

		for variable in ["uploadtime", "modelid"]:
			a_dict[variable] = eval(variable)

	return ("success")


# 1) Upload file as stream to a file.
@app.route("/upload", methods=["POST"])
def upload():
	if request.method == 'POST':
		with open("/home/chiefai/python_flask_file_streaming/output_filev3.txt", "bw") as f:
			#chunk_size = 40960000000
			chunk_size = 1024
			while True:
				chunk = request.stream.read(chunk_size)
				if len(chunk) == 0:
					return 'SUCCESS!'
				f.write(chunk)

@app.route("/print", methods=["POST"])
def print_endpoint():
	var1 = request.args.get('var1')
	var2 = request.args.get('var2')
	#output = str(r)
	print(var1, var2)
	return "Success"
	#print(var1, var2, var3, va4)

# 2) Download from provided URL.
@app.route('/<path:url>')
def download(url):
	req = requests.get(url, stream=True)
	return Response(stream_with_context(req.iter_content()), content_type=req.headers['content-type'])

# 3) Proxy uploaded files as stream to another web API without saving them to disk or holding them in memory.
#    This example uses multipart form data upload for both this API and destination API.
#    Test this endpoint with: curl -F "file=@some_binary_file.pdf" http://127.0.0.1:5000/proxy
@app.route("/proxy", methods=["POST"])
def proxy():
	var1 = request.args.get('var1')
	var2 = request.args.get('var2')
	resp1 = requests.post('https://api.chief.ai/upload', files={'file': request.stream})
	#resp2 = requests.post('https://api.chief.ai/print', data={'var1':'A' , 'var2': 'R'})
	#resp3 = requests.get('https://api.chief.ai/api/v1.0/customers')
	#resp = requests.get('https://api.chief.ai/print')
	# use data=... or files=..., etc in the call below - this affects the way data is POSTed: form-encoded for `data`,
	# multipart encoding for `files`. See the code/docs for more details here:
	# https://github.com/requests/requests/blob/master/requests/api.py#L16
	#resp = requests.post('http://destination_host/upload_api', files={'file': request.stream})
	print(var1, var2)
	#resp = "resp1" + "resp2"
	return resp1.text, resp1.status_code

@app.route('/verify_model_name', methods=['POST'])
def verifyModel():

	modelname = request.form['modelname']
	member_id = request.form['member_id']
	version = request.form['tag']

	if Models.query.filter_by(modelname=modelname,tag=version).first():
		print("its working")
	else: print("its not working")

	#model = Models.query.filter_by(modelname=modelname,tag=version).first()
	#print (model.model_id, model.modelpath)

	#q = engine.execute('''SELECT member_id FROM models WHERE modelname=%(name)s''', name=modelname)

	# upload logic
	# if model exists...
	# check if associated member id matches the logged in supplier
	# else error

	if Models.query.filter_by(modelname=modelname).first(): # check if model exists for any user
		print("model exists")
		if Models.query.filter_by(modelname = modelname, member_id = member_id).count() == 0: # is it associated with the logged in user
			print ("this model name already exists")

		elif Models.query.filter_by(modelname = modelname, member_id = member_id, tag=version).first(): # does this version already exist
			print("version already exists")

		elif not Models.query.filter_by(modelname = modelname, member_id = member_id, tag=version).first(): # the model name is associated to the user, and the propsed version doesn't exist
			print("go ahead and upload")

	else: print("youre the first one to use this name")#continue with upload

	#q = engine.execute('''SELECT modelpath, model_id FROM models WHERE modelname = %(modelname)s AND tag=%(tagname)s''', modelname = var1, tagname = version)
	"""if q == None:
		print("passing!")
		pass

	else:
		id_list = []

		for p in q:
			id_list.append(p.member_id)

		unique_id = np.unique(id_list)
		print("unique_id:", unique_id)
		
		if len(unique_id) > 1: 
			return ("duplicate model name error")

		elif len(unique_id) == 1:
			if int(member_id) == unique_id[0]:
				print("okay - add a new version!")

			else: 
				print("change your model name fool")"""

	return 'good'

############################# END OF TRY OUT CODE ###############################################################################

########## TEST CODE BLOCK ###########

@app.route('/test_verify_apikey', methods=['POST'])
def test_verify_apikey():
	if request.method == 'POST':
		memberID = request.form['member_id']
		verification = verify_api_key(memberid = memberID)	
	return verification

####### END OF TEST CODE BLOCK ##########