

{
	"allModels": [
		{
			"created_on": "2019-07-22T12:02:01.823086",
			"member_id": 0,
			"model_id": 1,
			"modelname": "tensorflowA",
			"modelpath": "/home/chiefai/production/models/trained/pickle/bike_model_xgboost.pkl",
			"price": 20,
			"tag": "No text"
		},
		{
			"created_on": "2021-04-29T10:23:23.968429",
			"member_id": 82,
			"model_id": 2,
			"modelname": "new_western_blot",
			"modelpath": "chiefaidocker/models:new_western_blot_v1",
			"price": 100,
			"tag": "chiefaidocker/models:new_western_blot_v1"
		},
		{
			"created_on": "2021-04-29T12:04:13.585171",
			"member_id": 82,
			"model_id": 21,
			"modelname (UNIQUE)": "dan_random6/v1.0",
			"modelpath": "chiefaidocker/models:dan_random6_v6",
			"price": 25,
			"version (UNIQUE)": "v1"
			"MODEL_TYPE??? (UNKNOWN)"
		}
	]
}
   


{
	"Executions": [
		{
			"charged_credits": 20.0,
			"created_on": "2020-05-19T11:39:11.071553",
			"execution_id": 1,
			"execution_time": 0.0,
			"member_id": 3,
			"model_id": 1,
			"revenue_earned_chiefai": 6.0
		}
	]
}

{
	"Results": [

		{
			"result_id"
			"execution_id": 1,
			"image_name": "test1.jpg",
			"prediction": "healthy"
			"probability": 0.879
		},

		{
			"execution_id": 1,
			"image_name": "test2.jpg",
			"prediction": "0"
			"probability": 0.748329479
		}

	]
}


CREATE TABLE result (result_id serial PRIMARY KEY, execution_id PRIMARY KEY, imagename VARCHAR(500) NOT NULL, prediction VARCHAR(100) NOT NULL, probability NUMERIC NULL, 




---
# IMAGE CLASSIFICATION

{
	"result": 

	[

		{
			"image_name": "test1.jpg",
			"prediction": "0"
			"probability": 0.879
		},

		{
			"image_name": "test2.jpg",
			"prediction": "0",
			"probability": 0.787
		}
	]
}

# SEGMENTATION

{
	"result": 

	[

		{
			"image_name": "test1.jpg",
			"predicted label": ""
			"probability": 0.879
		},

		{
			"image_name": "test2.jpg",
			"predicted label": "0",
			"probability": 0.879
		}
	]
}


# REGRESSION


{
	"result": 

	[

		{
			"image_name": "test1.jpg",
			"predicted label": [1,2,3,4,5,6]
			"probability": 0.879
		}
	]
}


