import io   
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier  
from uuid import uuid4
import numpy as np

#
# redisml_tree_string
# 
# inputs: 
# . forest - pass in the identifer of an already trained DecisionTreeClassifier object which has just one tree
# . feature_names - an array of values of the column names. <df>.columns.values. 
# . verbose - this prints a verbose output for debugging purposes
# returns:
# . string value of the Redis-ML ML.FOREST.ADD command that you need to add the model to redis
# . the unique name for the model that was generated
#
# mostly from Tague Griffith and http://scikit-learn.org/stable/auto_examples/tree/plot_unveil_tree_structure.html
#
'''
# example use of the above
redis_ml_string, redis_key_name = redisml_tree_string(
    forest = dectree_basic, # a trained Decision tree model
    feature_names = x_basic.columns.values,  # column names from the originating data set
    verbose = False)
print(redis_key_name)
print(redis_ml_string)
output:
tree-67a9f783-8849-48a1-8753-920596347eee
ML.FOREST.ADD tree-67a9f783-8849-48a1-8753-920596347eee 0 . NUMERIC DEBTINC 33.776611328125 .l LEAF 0 .r NUMERIC DEBTINC 33.784217834472656 .rl LEAF 1 .rr NUMERIC DEBTINC 43.99281311035156 .rrl LEAF 0 .rrr LEAF 1 
'''
def redisml_tree_string (forest, feature_names, verbose = False):

    # sanity check the input variables
    if (not isinstance(forest, DecisionTreeClassifier)):
        print("Input variable \'forest\' must be DecisionTreeClassifier.\n" + 
              "You passed in the type: " + str(type(tree)))
        return None
    if len(feature_names) == 0:
        print("Input variable \'feature_names\' cannot be zero length.")
        return None
    

    # create a buffer to build up our command
    forest_cmd = io.StringIO()

    #get a unique name for this forest
    key_uuid = "tree-" + str(uuid4())
    forest_cmd.write("ML.FOREST.ADD " + key_uuid + " 0 ")
    used_features = set() # keep a set of unique input values for later use

    forest_cmd, feature_names, used_features = tree_to_redisml_string(forest, forest_cmd, feature_names, used_features)

    if verbose == True: 
        print("Creating Redis ML string for a forest with a single tree")
        print("------")
        print("Here are the input forest's parameters: ")
        print(str(forest.get_params(deep=True)))
        print("------")
        print("Here is the output string: ")        
        print(forest_cmd.getvalue())
        print("------")
        print("Here are the used input vars: ")
        print(used_features)
        print("------")
        
    return forest_cmd.getvalue(), key_uuid




#
# redisml_forest_string
# 
# inputs: 
# . forest - pass in the identifer of an already trained RandomForestClassifier object
# . feature_names - an array of values of the column names. <df>.columns.values. 
# . verbose - this prints a verbose output for debugging purposes
# returns:
# . string value of the Redis-ML ML.FOREST.ADD command that you need to add the model to redis
# . the unique name for the model that was generated
#
# mostly from Tague Griffith and http://scikit-learn.org/stable/auto_examples/tree/plot_unveil_tree_structure.html
#
'''
# example use of the above
redis_ml_strings, redis_key_name = redisml_forest_string(
    forest = rf_basic, 
    feature_names = x_basic.columns.values,
    verbose = False)
print(redis_key_name)
for cmd in redis_ml_strings:
    print(cmd)
output:
forest-c38fa7a6-1230-4413-8f69-1eaa094f9383
ML.FOREST.ADD forest-c38fa7a6-1230-4413-8f69-1eaa094f9383 0 . NUMERIC DELINQ 1.5 .l NUMERIC DEBTINC 45.57856369018555 .ll NUMERIC LOAN 4100.0 .lll LEAF 1 .llr LEAF 0 .lr LEAF 1 .r LEAF 1 
ML.FOREST.ADD forest-c38fa7a6-1230-4413-8f69-1eaa094f9383 1 . NUMERIC NINQ 2.5 .l NUMERIC DEROG 1.5 .ll LEAF 0 .lr LEAF 1 .r NUMERIC DEROG 1.5 .rl LEAF 0 .rr LEAF 1 
ML.FOREST.ADD forest-c38fa7a6-1230-4413-8f69-1eaa094f9383 2 . NUMERIC DELINQ 1.5 .l NUMERIC CLAGE 179.80657958984375 .ll NUMERIC DEBTINC 33.77537155151367 .lll LEAF 0 .llr LEAF 0 .lr LEAF 0 .r LEAF 1 
ML.FOREST.ADD forest-c38fa7a6-1230-4413-8f69-1eaa094f9383 3 . NUMERIC DELINQ 1.5 .l NUMERIC DEBTINC 33.67848587036133 .ll LEAF 0 .lr NUMERIC DEROG 0.5 .lrl LEAF 0 .lrr LEAF 1 .r LEAF 1 
'''
def redisml_forest_string (forest, feature_names, verbose = False):

    # sanity check the input variables
    if (not isinstance(forest, RandomForestClassifier)):
        print("Input variable \'forest\' must be RandomForestClassifier.\n" + 
              "You passed in the type: " + str(type(tree)))
        return None
    if len(feature_names) == 0:
        print("Input variable \'feature_names\' cannot be zero length.")
        return None

    # get a unique name for this forest
    key_uuid = "forest-" + str(uuid4())
    n_estimator = 0
    forest_cmds = []
    used_features = set() # keep a set of unique input values for later use

    for tree in forest.estimators_:
        forest_cmd = io.StringIO() # create a buffer to build up our command
        forest_cmd.write("ML.FOREST.ADD " + key_uuid + " " + str(n_estimator) + " ")
        n_estimator = n_estimator + 1 # set for next time
        
        forest_cmd, feature_names, used_features = tree_to_redisml_string(tree, forest_cmd, feature_names, used_features)

        forest_cmds.append(forest_cmd.getvalue())


    if verbose == True: 
        print("Creating Redis ML string for a forest with [" + str(n_estimator) + "] trees")
        print("------")
        print("Here are the input forest's parameters: ")
        print(str(forest.get_params(deep=True)))
        print("------")
        print("Here is the output string: ")        
        for cmd in forest_cmds:
            print(cmd)
        print("------")
        print("Here are the used input vars: ")
        print(used_features)
        print("------")

    return forest_cmds, key_uuid

# 
# Convert a tree object to  a redisml string, 
# input: 
#   forest_string: StringIO object already initialized and written to
#   feature_names: of all the input columns
#   used_features: a set containing features actually used
#
def tree_to_redisml_string(tree, forest_string, feature_names, used_features):
    # get some values / flags out of the tree var
    t_nodes = tree.tree_.node_count
    t_left = tree.tree_.children_left
    t_right = tree.tree_.children_right
    t_feature = tree.tree_.feature
    t_threshold = tree.tree_.threshold
    t_value = tree.tree_.value

    
    # Traverse the tree starting with the root and a path of “.”
    stack = [ (0, ".") ]

    while len(stack) > 0:
        node_id, path = stack.pop()

        # splitter node -- must have 2 children (pre-order traversal)
        if (t_left[node_id] != t_right[node_id]):
            stack.append((t_right[node_id], path + "r")) 
            stack.append((t_left[node_id], path + "l"))
            cmd = "{} NUMERIC {} {} ".format(path, feature_names[t_feature[node_id]], t_threshold[node_id])
            forest_string.write(cmd)
            used_features.add(feature_names[t_feature[node_id]])    
        else:
            cmd = "{} LEAF {} ".format(path, np.argmax(t_value[node_id]))
            forest_string.write(cmd)

    return forest_string, feature_names, used_features

# todo:
# 
# function that can publish a redis-ML model string to anexisting redis connection
# blah blah
#
def redisml_string_to_redis(redis_object, model_string):
    
    return True 