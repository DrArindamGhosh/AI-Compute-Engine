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
		config_file_path = "/home/chiefai/" # path to YAML config file - NO LONGER NEEDED!!!!!

		models_table = Models(model_id, model_name, full_docker_tag, supplier_id, created_on, price, full_docker_tag, config_file_path)
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