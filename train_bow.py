# Bag of words classifier with SVM

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, median_absolute_error
from sklearn.externals import joblib
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import FeatureUnion
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.model_selection import train_test_split


import pandas as pd
import trident
import pickle
import numpy as np
import nltk
from collections import defaultdict
from operator import itemgetter
import scipy.sparse as sp
import random
TRAINING_SET_PERCENTAGE = 0.9

# IDEA:
# Currently I have descriptions for each entity in my slice of fb

# Make function that:
# 	- Takes a set of sentences (use 1st sentence of descriptions)
# 	- Creates a feature vector from n most common words (maybe sklearn has function for this)
# 	- Train using these feature-vectors. Also need to provide negative examples. To do this,
# pick random triples, check that they do not in fact exist, and feed to model
#	- Apply, to rankings generated by TransE, merge.

# What are the implementation details to this model?
# - Include relId into feature model?
# - This would be instead of making a model for each rel
# - Does this work in combination with one-hot?
# - What can I do to lessen training time?
# - How long should the thesis be?
# - Should I only do fb15k, or try to generalize to whole fb?
# - How to make model that chooses weights for combining?

# - Send email to Jacopo about results of combining rankings in the next 2 days.

# Technique for identifying useful features, remove as many features
# Focus on combining with TransE first


with open("entity_labels.txt", "rb") as f:
	labels = pickle.load(f)

with open("entity_descriptions.txt", "rb") as f:
	desc = pickle.load(f)

with open("short_descriptions.txt", "rb") as f:
	short_desc = pickle.load(f)

fb = trident.Db("fb15k")
d_get = np.vectorize(lambda index: short_desc[fb.lookup_str(index)])

class TripleTransformer(BaseEstimator, TransformerMixin):

	def __init__(self, min_df=1, max_df=1.0):
		self.vec = TfidfVectorizer(min_df=min_df, max_df=max_df)

	def fit(self, x, y=None):

		if x.shape[1] != 3:
			raise ValueError("The input matrix does not contain 3 columns, and thus it is not a triple.")

		self.vec.fit(np.unique(np.concatenate((x[:,0], x[:,2]))))
		return self

	def transform(self, x):

		if x.shape[1] != 3:
			raise ValueError("The input matrix does not contain 3 columns, and thus it is not a triple.")

		return sp.hstack((self.vec.transform(x[:,0]), self.vec.transform(x[:,2])), format='csr')

	def get_vectorizer(self):
		return self.vec

	# def fit_transform(self, x):
	# 	return self.vec.fit(x).transform(x)




def feature_vector(vectorizer, h, r, t):

	return sp.hstack((vectorizer.transform(d_get(h)), vectorizer.transform(d_get(t))), format='csr')

def get_model():
	return joblib.load("model_svr.pkl"), joblib.load("vectorizer.pkl")

# Creates a model based on triples received, attempts to make predictions
def train(rel_id):


	# triples, negative_triples = generate_sets(rel_id)

	# train_pos = triples[:int(len(triples)*TRAINING_SET_PERCENTAGE)]
	# train_neg = negative_triples[:int(len(negative_triples)*TRAINING_SET_PERCENTAGE)]

	# test_pos = triples[int(len(triples)*TRAINING_SET_PERCENTAGE):]
	# test_neg = negative_triples[int(len(negative_triples)*TRAINING_SET_PERCENTAGE):]


	# s = np.concatenate((train_pos[:,0], train_neg[:,0]), axis=0)
	# s_test = np.concatenate((test_pos[:,0], test_neg[:,0]), axis=0)

	# o = np.concatenate((train_pos[:,2], train_neg[:,2]), axis=0)
	# o_test = np.concatenate((test_pos[:,2], test_neg[:,2]), axis=0)

	# y = np.append(np.ones(len(train_pos)), np.zeros(len(train_neg)))
	# y_test = np.append(np.ones(len(test_pos)), np.zeros(len(test_neg)))

	X, y = generate_sets(rel_id=0)

	X_train, X_test, y_train, y_test = train_test_split(d_get(X), y, test_size=0.1)

	X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.1)



	# X = d_get(np.stack((s, o), axis=1))
	# X_test = d_get(np.stack((s_test, o_test), axis=1))

	print(X_train.shape, X_test.shape, X_val.shape)

	# vec = TripleTransformer()

	# vec.fit(X)

	# X_train = vec.transform(X_train)

	pipe = Pipeline([('vectorizer', TripleTransformer(min_df=5)), ('estimator', SVR(gamma='auto'))])


	pipe.fit(X_train, y_train)

	y_pred = pipe.predict(X_test)

	get_accuracy(y_test, y_pred)




	# # Maybe don't use unique cause that fucks with the tfidf weighing?
	# ents = d_get(np.unique(np.append(s, o)))

	# # # This would be fine but only using unique entities like above
	# # # yields better results.

	# # ct = ColumnTransformer([
	# # 	("tfidf0", TfidfVectorizer(min_df = 5), 0),
	# # 	("tfidf1", TfidfVectorizer(min_df = 5), 1)
	# # 	])

	# # print(ct.fit_transform(d_get(np.stack((s, o), axis=1))).shape)
	# # # features_test = c

	# s = d_get(s)
	# s_test = d_get(s_test)

	# o = d_get(o)
	# o_test = d_get(o_test)

	# features = sp.hstack((vectorizer.transform(s), vectorizer.transform(o)), format='csr')
	# features_test = sp.hstack((vectorizer.transform(s_test), vectorizer.transform(o_test)), format='csr')

	# print(features.shape)

	# svr = SVR().fit(features, y)

	# y_pred = svr.predict(features_test)

	# with open("vectorizer.pkl", "wb") as f:
	# 	joblib.dump(vectorizer, f)

	# with open("model_svr.pkl", "wb") as f:
	# 	joblib.dump(svr, f)


	# return mean_squared_error(y_test, y_pred), mean_squared_error(y_test, np.random.rand(len(y_pred), 1))

	
def get_accuracy(y_test, y_pred):

	y_guess = np.random.rand(len(y_test))

	print("\nEstimator r2:", r2_score(y_test, y_pred))
	print("Baseline  r2:", r2_score(y_test, y_guess))

	print("\nEstimator MAE:", mean_absolute_error(y_test, y_pred))
	print("Baseline  MAE:", mean_absolute_error(y_test, y_guess))

	print("\nEstimator MSE:", mean_squared_error(y_test, y_pred))
	print("Baseline  MSE:", mean_squared_error(y_test, y_guess))

	print("\nEstimator Median Absolute Error", median_absolute_error(y_test, y_pred))
	print("Baseline  Median Absolute Error", median_absolute_error(y_test, y_guess))

def generate_sets(rel_id):
	positive = [(tup[0], rel_id, tup[1]) for tup in fb.os(rel_id)]

	all_set = set(fb.all())
	diff_set = all_set.difference(set(positive))

	# negative = np.empty([len(positive),3])

	negative = random.sample(diff_set, len(positive))

	for i in range(len(negative)):
		while fb.exists(negative[i][0], rel_id, negative[i][2]):
			negative[i] = random.sample(diff_set, 1)[0]

	# for i in range(len(positive)):

	# 	print(i)
	# 	sample = random.sample(diff_set, 1)[0]
	# 	if not fb.exists(sample[0], rel_id, sample[2]):
	# 		negative[i] = sample


	# # while i < len(positive):

	# # 	print(len(negative))
	# # 	sample = random.sample(diff_set, 1)[0]

	# # 	if not fb.exists(sample[0], rel_id, sample[2]):
	# # 		negative.append(sample)

	# positive = np.concatenate((np.asarray(positive), np.ones((len(positive), 1), np.int64)), axis=1)
	# negative = np.concatenate((np.asarray(negative), np.zeros((len(negative), 1), np.int64)), axis=1)

	# pos_neg = np.concatenate((positive, negative))

	# np.random.shuffle(pos_neg)

	return np.concatenate((positive, negative)), np.append(np.ones(len(positive)), np.zeros(len(negative)))


	# print(pos_neg)
	# Return X, y
	# return pos_neg[:,:3], pos_neg[:,3:]

def tuples_consistent(rel_id, tuples, answers):
	for i in range(len(tuples)):
		if not fb.exists(tuples[i][0], rel_id, tuples[i][2]) == bool(answers[i]):
			return False

	return True


train(0)
# real, baseline = train(0)

# print("The mean squared error for our estimator:", real)
# print("The baseline mean squared error for a guessing estimator:", baseline)

