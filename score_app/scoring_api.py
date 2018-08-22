from flask import Flask, jsonify, request
import json
import os
import io
import datetime

import redis

app = Flask(__name__)


##
# GET on '/inputs', '/outputs', and '/description' will describe the API 
# endpoints and model inputs / outputs
##
@app.route('/inputs/<key>', methods=['GET'])
def describe_model_inputs(key):
	# get from model metadata record in redis
    result = r.hget("metadata:"+key,"model_inputs")
    print(str(result))
    if result is None:
        return jsonify({"Result": "Model not found by ID: \'{}\'".format(key)}), 404
    return jsonify(result), 200

@app.route('/outputs/<key>', methods=['GET'])
def describe_model_outputs(key):
	# get from model metadata record in redis
    result = r.hget("metadata:"+key,"model_outputs")
    if result is None:
        return jsonify({"Result": "Model not found by ID: \'{}\'".format(key)}), 404
    return jsonify(result), 200
    
@app.route('/description/<key>', methods=['GET'])
def describe_model(key):
	# get from model metadata record in redis
    result = r.hgetall("metadata:"+key)
    # todo: this check doesn't work. redis-py is returning something other than None
    if result is None:
        return jsonify({"Result": "Model not found by ID: \'{}\'".format(key)}), 404
    return jsonify(result), 200

# default route "/" describes what to do
@app.route('/', methods=['GET'])
def get_endpoints():
    if DEBUG: 
        print(str(os.getenv("CF_INSTANCE_INDEX", 0)))
    result = {"Endpoints": {"GET:/description/<key>": "Describes a model with <key>", 
                "GET:/inputs/<key>": "Describes inputs for model  <key>", 
                "GET:/outputs/<key>": "Describes outputs for model <key>", 
                "POST:/score": "Scores a record based on an input JSON document"}, 
            "CF instance": str(os.getenv("CF_INSTANCE_INDEX", "not in CF"))
            }
    return jsonify(result), 200

# "/schema" returns an example of what the json document should look like for POST:/score
@app.route('/schema', methods=['GET'])
def get_schema():
    schema_example = {"model_key": "tree-67a9f783-8849-48a1-8753-920596347eee","model_inputs": { "CLAGE": 12, "YOJ": 15 }}
    return jsonify(schema_example),200


##
# PUT on '/' will not do anything
##
@app.route('/', methods=['POST'])
def score_root():
    return 'POST on "/" does nothing. Try /score instead.' + str(os.getenv("CF_INSTANCE_INDEX", 0))

##
# POST on '/score' will score a record
##
@app.route('/score', methods=['POST'])
def score_record():
    try:
        # 1. validate json doc in POST var
        input_data = request.get_json(force=True) 
        if DEBUG: print("POST:/score Input payload: " + str(input_data))
       

        # 2. parse doc for model input parameters
        if 'model_key' in input_data.keys():
            if DEBUG: print("model_key" + ": "+ str(input_data['model_key']))
            model_key = input_data['model_key']

        # does a model exist under that key? if so, get it's model_type  
        model_type = r.hget("metadata:"+input_data['model_key'], "model_type")
        if model_type is None:
            return {"Model not found": model_key}, 404

        # build a string of inputs and their values as ML.xxx.RUN requires
        input_str = io.StringIO()
        if 'model_inputs' in input_data.keys():
            if DEBUG: print("model_inputs" + ": "+ str(input_data['model_inputs']))
            for key in input_data['model_inputs'].keys():
                input_str.write(key + ":" + str(input_data['model_inputs'][key]) + ",")
            if DEBUG: print(input_str.getvalue())

        # 3. try to execute the redis command to score the data against the model
        runcommand = io.StringIO()
        runcommand.write("ML.FOREST.RUN "+ input_data['model_key'] + " " 
                        + input_str.getvalue() + " " 
                        + model_type.upper())
        if DEBUG: print(runcommand.getvalue())

        # execute the command in redis
        pre_time = datetime.datetime.now()
        return_value = r.execute_command(runcommand.getvalue())
        exec_duration = datetime.datetime.now() - pre_time 
        exec_duration_ms = int(exec_duration.total_seconds() * 1000) # time in ms

        if DEBUG: print("Model scored in {} ms".format(str(exec_duration_ms)))

        # 4. log the execution in Redis for future modelling use
        r.lpush("modelexecution:"+input_data['model_key'], 
            "{}:{}:{}:{}".format(str(datetime.datetime.now()),str(return_value), input_str.getvalue(),str(exec_duration_ms)))
        
        output = {"Model key": model_key, "Input string": input_str.getvalue(), 
                "Output Value": return_value, "Duration": exec_duration_ms}
        return jsonify(output)

    except ValueError as e:
        return "POST on /score with errors: {} {} \n".format(str(e),str(os.getenv("CF_INSTANCE_INDEX", 0))), 400
    

## 
# main app entry point
##
if __name__ == "__main__":
   
    if os.environ.get('VCAP_SERVICES') is None: 
    	# running locally, let's debug
        PORT = 9090
        DEBUG = True
        # get redis connection params from authinfo / similar
        redis_env = dict(host='localhost', port=12000, password='')
    else:    
        # running in cloudfoundry                             
        # Get Redis credentials from VCAP services
        services = json.loads(os.getenv('VCAP_SERVICES'))
        redis_env = services['redislabs'][0]['credentials']  
        DEBUG = False
        PORT = int(os.getenv("PORT"))
        redis_env['host'] = redis_env['hostname']  # or IP address?
        del redis_env['hostname']
        redis_env['port'] = int(redis_env['port'])


    # connect to redis with above params
    try:
        r = redis.StrictRedis(**redis_env, charset="utf-8", decode_responses=True)
        r.info()
    except redis.ConnectionError:
        if DEBUG: print("Could not connect to specified redis instance: {}".format(**redis_env))
        quit()
 
    
    if DEBUG:
    	# how do we get this in to loggregator?
        print("Let's do some debugging!")

    # run this flask app!
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
