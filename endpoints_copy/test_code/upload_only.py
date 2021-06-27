from flask import jsonify # <- `jsonify` instead of `json`
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import request, render_template, url_for, redirect, send_from_directory, flash, Response, make_response, copy_current_request_context, abort
from flask import session as dropzone_session

from werkzeug.utils import secure_filename
from werkzeug.exceptions import Unauthorized

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import sessionmaker
from sqlalchemy.inspection import inspect

from routetest1_InsertValuesIntoDB_customer import Customer
from routetest1_InsertValuesIntoDB_models import Models
from routetest1_InsertValuesIntoDB_execution import Execution
from routetest1_InsertValuesIntoDB_datasets import Datasets
from routetest1_InsertValuesIntoDB_supplier import Supplier
#from routetest1_InsertValuesIntoDB_api_keys import Api_keys

import json, zipfile, importlib
import sys, os, shutil
from os import path
import decimal, datetime
import threading
import time
from time import sleep, strftime
#from time import *             WHY??? # meaning from time import EVERYTHING

import docker
from docker import client, APIClient
client = docker.from_env()
client = docker.APIClient(base_url='unix://var/run/docker.sock')

#imports for logging feature inFlask App
import logging
from logging.handlers import RotatingFileHandler
import logging.handlers
import traceback
import requests


@app.route('/api/v1.0/model/upload_mdc', methods=['POST', 'GET'])
def newupload_mdc():
	@copy_current_request_context
	def save_file(closeAfterWrite):
		print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " i am doing")
		fileB = request.files['zipped_model_folder']
		filenameB = secure_filename(fileB.filename)
		if fileB and allowed_file(filenameB):
			executor_dir = "/home/chiefai/production/members/supplier_" + str(var4) + "/executorFolder/" # check if model folder exist #
			executorPath = os.path.join(executor_dir, filenameB) # path to zipped model folder
			if os.path.exists(executorPath):
				raise Exception('An error occurred Executor Path exists')
			else:
				os.makedirs(executor_dir, exist_ok=True) # In this line os.makedirs("path/to/directory", exist_ok=bool) makes it accept multiple files in the same directory or folder
				fileB.save(executorPath)
				print ("file saved")
				zip_ref = zipfile.ZipFile(os.path.join(executor_dir, filenameB), 'r')
				zip_ref.extractall(executor_dir)
				zip_ref.close()
				print ("file unzipped")
				os.remove(executorPath)
				print ("original zipped file removed")

		else: raise Exception('An error occurred Executor Dir exists or . filename extension is WRONG....!!!!')

		closeAfterWrite()
		print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " write done! and now docker process started")

		unzip_filename = filenameB.split('.')[0]
		unzip_dir = os.path.join(executor_dir, unzip_filename)

		dockerfile = request.form['dockerfile']
		tag = request.form['tag']
		
		cli = docker.from_env()
		cli = APIClient(base_url='unix://var/run/docker.sock')
		response = [line for line in cli.build(path=unzip_dir, dockerfile=dockerfile, rm=True, tag=tag)]
		#response = [line for line in cli.build(fileobj=f, rm=True, tag=tag)]
		cli.push(docker_repo_name, tag=tag, stream=False, auth_config=None, decode=False)

		print (response)
		print (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " Docker Image Building Process Finished")

	def passExit():
		pass

	if request.method == 'POST':
		starttime = time.time()
		
		# request form variables
		model_name = request.form['modelname'] # var2 must be the name of the original model
		model_id = Models.query.order_by(Models.model_id.desc()).first().model_id + 1 #var1
		supplier_name = request.form['membername'] #var9
		supplier_id = Supplier.query.filter_by(suppliername=supplier_name).first().member_id  # var4
		created_on = 'NOW()' #var6
		price = request.form['price'] #var7
		docker_tag = request.form['tag'] #var8 - this should be a version number

		docker_repo_name = os.path.join("chiefai", "models", supplier_name, model_name)
		full_docker_tag = docker_repo_name + ":" + docker_tag

		# API key verification
		var_api_key = Members.query.filter_by(membername=supplier_name).first().api_key
		headers = request.headers
		auth = headers.get("x-api-key")

		print ("received form data and api key!")
		
		if auth != var_api_key :
			return jsonify({"Message": "ERROR: Unauthorized - Authorization Information - API Key is Missing or Invalid"}), 401
			#return make_response(jsonify({"message": "ERROR: Unauthorized"}), 401)
			#return custom_401()
			#abort(401)
		else:
			print (jsonify({"message": "OK: Authorized"}), 200)

			executor_dir = "/home/chiefai/production/members/supplier_" + str(supplier_id) + "/executorFolder/" # check if model folder exist #          
			fileB = request.files['zipped_model_folder']
			# fileA variable defined in save_file function
			filenameB = secure_filename(fileB.filename)
			executorPath = os.path.join(executor_dir, filenameB) # path to zipped model folder
			normalExit = fileB.stream.close
			fileB.stream.close = passExit
			t = threading.Thread(target=save_file,args=(normalExit,))
			t.start()
			print ("i am here where i started the threading")

			##################################################
			# UNZIPPED File Without Extension (filename.zip) #
			##################################################
			unzip_filename = filenameB.split('.')[0]
			unzip_dir = os.path.join(executor_dir, unzip_filename)

			#exec_file_path = os.path.join(unzip_dir, "executor.py") # path to executor file
			config_file_path = os.path.join(unzip_dir, "config.yml") # path to YAML config file

			models_table = Models(model_id, model_name, full_docker_tag, supplier_id, created_on, price, full_docker_tag, config_file_path)
			db.session.add(models_table)
			db.session.commit()

			endtime = time.time()
			#sleep(75)
			executiontime = (endtime - starttime)

			a_dict = {}

			buildtime = executiontime
			modelid = model_id

			for variable in ["buildtime", "modelid"]:
				a_dict[variable] = eval(variable)

	#jsonresult = "{\"diagnosis\":" + str(result) + "}" +  "{\"Model Execution Time\":" + str(executiontime) + "}";
	#jsonresult = "{" "'time'" ':' + str(executiontime) + "," + "'modelid'" ':' + str(current_uploaded_model_id) + "}";
	#return str([jsonresult, jsonify({"Message": "Success"}), 200])
	#return str([jsonresult, jsonify({"message": "OK: Authorized"}), 200])
	#return jsonify(jsonresult)

	return jsonify(a_dict)