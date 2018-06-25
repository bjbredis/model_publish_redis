# model_publish_redis
Integrate Redis-ML in to your data pipeline. Publish models from Sci-kit learn in to Redis and serve them via Redis-ML to your end-use applications.

* py-redisml-connector.py: used by a data scientist/modeller to generate the model metadata that is needed to eventually store and server the model.
* publish_api.py: an application that allows a user to publish a model to Redis-ML via REST. Some example JSON inputs are store_model_rf.json and store_model.json
* scoring_api.py: an application that scores new records against a stored model. Example JSON inputs in score_data.json

More details to follow.

