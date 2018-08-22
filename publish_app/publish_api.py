from flask import Flask, jsonify, request
import json
import os
import redis
import time

app = Flask(__name__)


# app vars: 


# get model metadata from model with name <key>
@app.route('/description/<key>', methods=['GET'])
def describe_model(key):
    try: 
        # get from model metadata record in redis
        # if this returns a result set:
        redis_res = r.hgetall("metadata:"+key)
        if DEBUG: print(redis_res)
        return jsonify(redis_res), 200
    except NameError as e:
        return 'GET on /description/<key> with errors: ' + str(e) + ' ' + str(os.getenv("CF_INSTANCE_INDEX", 0)) + '\n', 400


# update to get from /get_all
@app.route('/get_all', methods=['GET'])
def describe_all_model():
    models = []
    for model in r.scan_iter("metadata:*"):
        models.append(r.hgetall(model))
    # if models.len == 0:
    #     result = {"No models yet!": "Hello, world!"}
    # else:
    #     # how do I pack the json document with the whole list?
    return jsonify(models), 200

##
# POST on '/store' will register a new model
#   important note: this will overwrite an existing model so see if there
#       is one already of that name using /description/<key> first
##
@app.route('/store', methods=['POST'])
def store_new_model():
    try:
        # 1. validate json doc in POST var
        # 2. parse doc for correct parameters
        # is there a better way to get json from the POST payload?
        model_info = request.get_json(force=True) 
        if DEBUG:
            print(model_info.keys())
            print("model_info['model_key']: "+ model_info['model_key'])
            print("model_info['redisml_add_str']: "+ model_info['redisml_add_str'])
            print("model_info['redisml_run_example']: "+ model_info['redisml_run_example'])
            print("model_info['model_inputs']: "+ str(model_info['model_inputs']))
            print("model_info['model_outputs']: "+ str(model_info['model_outputs']))
            print("model_info['model_type']: "+ model_info['model_type'])
            print("model_info['model_algorithm']: "+ model_info['model_algorithm'])
        # 3. execute the redis command to register a new model in redis-ml
        ### definately need a sanity check of this string if we're going to input it directly
        ### maybe a regex?
        if model_info['model_algorithm'] == 'RandomForest':
            for rmlstr in model_info['redisml_add_str'].split("\n"):
                if DEBUG: print("___" + rmlstr)
                r.execute_command(rmlstr)
        else: 
            r.execute_command(model_info['redisml_add_str'])

        # 5. log a successful new model creation with metadata and date
        # todo: should add date of addition
        
        r.hmset("metadata:"+model_info['model_key'], {**model_info, "creation_time":time.time()} )  # may need to {**model_info}

        return jsonify({"Model creation at /store":"success","model_key":model_info['model_key']}), 200
    except ValueError as e:
        return 'POST on /store with errors: ' + str(e) + ' ' + str(os.getenv("CF_INSTANCE_INDEX", 0)) + '\n', 400
    


## 
# main app entry point
##
if __name__ == "__main__":
    if os.environ.get('VCAP_SERVICES') is None: 
    	# running locally, let's debug
        PORT = 8989
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
        redis_env['port'] = int(redis_env['port'])


    # connect to redis with above determined params
    try:
        r = redis.StrictRedis(**redis_env, decode_responses=True)
    except redis.ConnectionError:
        r = None
    
    
    if DEBUG:
    	# how do we get this in to loggregator?
        print("We are live on Redis w/ port: " + str(r.info('server')['tcp_port']))


    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
