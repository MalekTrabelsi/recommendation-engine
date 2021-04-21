from django.shortcuts import render
from django.http import HttpResponse

import pandas as pd
import random

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def get_top_category_apps (n, l):
	apps = pd.read_parquet("data_files/apps.parquet", engine="pyarrow")

	list_of_genres = set().union(*apps["genres"])
	list_of_apps = apps["bundleId"].unique()
	jaccard = {}

	for a in list_of_apps:
		app_categories = apps.loc[apps["bundleId"] == a].reset_index().at[0,"genres"]
		similarity = len(set(app_categories) & set(l)) / len(set(app_categories) | set(l))
		jaccard[a] = similarity

	jaccard_matrix = pd.DataFrame(jaccard.items(), columns=["app", "score_jaccard"])

	impressions = pd.read_parquet("data_files/impressions.parquet", engine="pyarrow")
	clicks = pd.read_parquet("data_files/clicks.parquet", engine="pyarrow")
	opens = pd.read_parquet("data_files/appopens.parquet", engine="pyarrow")
	installs = pd.read_parquet("data_files/installs.parquet", engine="pyarrow")

	impressions_per_app = impressions.groupby("source_id", as_index=False).count()
	impressions_per_app.columns = ["source_id", "impressions_count"]

	clicks_per_app = clicks.groupby("source_id", as_index=False).count()
	clicks_per_app.columns = ["source_id", "clicks_count"]

	opens_per_app = opens.groupby("source_id", as_index=False).count()
	opens_per_app.columns = ["source_id", "opens_count"]

	installs_per_app = installs.groupby("source_id", as_index=False).count()
	installs_per_app.columns = ["source_id", "installs_count"]

	funnel_matrix = pd.merge(impressions_per_app, clicks_per_app, on="source_id", how="left")
	funnel_matrix = pd.merge(funnel_matrix, opens_per_app, on="source_id", how="left")
	funnel_matrix = pd.merge(funnel_matrix, installs_per_app, on="source_id", how="left")

	funnel_matrix["impressions_count"] = funnel_matrix["impressions_count"].fillna(0).astype(int)
	funnel_matrix["clicks_count"] = funnel_matrix["clicks_count"].fillna(0).astype(int)
	funnel_matrix["opens_count"] = funnel_matrix["opens_count"].fillna(0).astype(int)
	funnel_matrix["installs_count"] = funnel_matrix["installs_count"].fillna(0).astype(int)

	funnel_matrix["score_funnel"] = (funnel_matrix["impressions_count"] + 2*funnel_matrix["clicks_count"] + 3*funnel_matrix["opens_count"] + 4*funnel_matrix["installs_count"])/10
	funnel_matrix["score_funnel"] = (funnel_matrix["score_funnel"] - funnel_matrix["score_funnel"].min())/(funnel_matrix["score_funnel"].max() - funnel_matrix["score_funnel"].min())

	merged_df = pd.merge(jaccard_matrix, funnel_matrix[["source_id", "score_funnel"]], left_on="app", right_on="source_id", how="left")
	merged_df["score"] = (merged_df["score_jaccard"] + merged_df["score_funnel"])/2

	sorted_recommendations = merged_df.sort_values(ascending=False, by=["score"]).reset_index(drop=True)
	
	output = sorted_recommendations.iloc[:n]
	output = output.merge(apps, left_on="app", right_on="bundleId", how="left")

	return (output)


def get_custom_random_apps (n):

	apps = pd.read_parquet("data_files/apps.parquet", engine="pyarrow")
	list_ind = random.sample(range(len(apps)), n)
	random_apps = {}
	for ind in list_ind:
		random_apps[apps["bundleId"].loc[ind]] = apps["name"].loc[ind]

	return (random_apps)


def content_based (n, bundleid):
	apps = pd.read_parquet("data_files/apps.parquet", engine="pyarrow")
	list_of_genres = set().union(*apps["genres"])
	list_of_apps = apps["bundleId"].unique()
	jaccard = {}

	for a1 in list_of_apps:
	    app_a1_similarities = []
	    for a2 in list_of_apps:
	        genres_a1 = apps.loc[apps["bundleId"] == a1].reset_index().at[0,"genres"]
	        genres_a2 = apps.loc[apps["bundleId"] == a2].reset_index().at[0,"genres"]
	        similarity = len(set(genres_a1) & set(genres_a2)) / len(set(genres_a1) | set(genres_a2))
	        
	        app_a1_similarities.append(similarity)
	        
	    jaccard[a1] = app_a1_similarities

	genres_matrix = pd.DataFrame(jaccard, index=list_of_apps, columns=list_of_apps) 

	tf = TfidfVectorizer(analyzer="word", ngram_range=(1,3), min_df=0, stop_words="english")
	tfidf_matrix = tf.fit_transform(apps["description"])
	cosine_similarities = linear_kernel(tfidf_matrix, tfidf_matrix)

	description_matrix = pd.DataFrame(cosine_similarities, index=list_of_apps, columns=list_of_apps)
	similarity_matrix = (genres_matrix + description_matrix)/2

	sorted_recommendations = similarity_matrix.loc[bundleid, :].sort_values(ascending=False)

	output = sorted_recommendations[1:n+1].to_frame()
	output["bundleId"] = output.index
	output = output.merge(apps, on="bundleId", how="left")
	output["score"] = output[bundleid]

	return (output)


def collaborative (age, country, n):
	apps = pd.read_parquet("data_files/apps.parquet", engine="pyarrow")
	users = pd.read_parquet("data_files/users.parquet", engine="pyarrow")

	impressions = pd.read_parquet("data_files/impressions.parquet", engine="pyarrow")
	clicks = pd.read_parquet("data_files/clicks.parquet", engine="pyarrow")
	opens = pd.read_parquet("data_files/appopens.parquet", engine="pyarrow")
	installs = pd.read_parquet("data_files/installs.parquet", engine="pyarrow")

	apps["contentAdvisoryRating"] = apps["contentAdvisoryRating"].apply(lambda x: int(x.replace("+","")))
	apps["minAge"] = apps["contentAdvisoryRating"].apply(lambda x: 0 if x<age else 1)
	apps_filter = apps[apps["minAge"] == 1]
	
	users_filtered = users[users["country_code"] == country]

	impressions_filtered = impressions[impressions["advertising_id"].isin(users_filtered["advertising_id"].unique())]
	clicks_filtered = clicks[clicks["advertising_id"].isin(users_filtered["advertising_id"].unique())]
	opens_filtered = opens[opens["advertising_id"].isin(users_filtered["advertising_id"].unique())]
	installs_filtered = installs[installs["advertising_id"].isin(users_filtered["advertising_id"].unique())]

	impressions_per_app = impressions_filtered.groupby("source_id", as_index=False).count()
	impressions_per_app.columns = ["source_id", "impressions_count"]

	clicks_per_app = clicks_filtered.groupby("source_id", as_index=False).count()
	clicks_per_app.columns = ["source_id", "clicks_count"]

	opens_per_app = opens_filtered.groupby("source_id", as_index=False).count()
	opens_per_app.columns = ["source_id", "opens_count"]

	installs_per_app = installs_filtered.groupby("source_id", as_index=False).count()
	installs_per_app.columns = ["source_id", "installs_count"]

	funnel_matrix = pd.merge(impressions_per_app, clicks_per_app, on="source_id", how="left")
	funnel_matrix = pd.merge(funnel_matrix, opens_per_app, on="source_id", how="left")
	funnel_matrix = pd.merge(funnel_matrix, installs_per_app, on="source_id", how="left")

	funnel_matrix["impressions_count"] = funnel_matrix["impressions_count"].fillna(0).astype(int)
	funnel_matrix["clicks_count"] = funnel_matrix["clicks_count"].fillna(0).astype(int)
	funnel_matrix["opens_count"] = funnel_matrix["opens_count"].fillna(0).astype(int)
	funnel_matrix["installs_count"] = funnel_matrix["installs_count"].fillna(0).astype(int)

	funnel_matrix["score"] = (funnel_matrix["impressions_count"] + 2*funnel_matrix["clicks_count"] + 3*funnel_matrix["opens_count"] + 4*funnel_matrix["installs_count"])/10
	funnel_matrix["score"] = (funnel_matrix["score"] - funnel_matrix["score"].min())/(funnel_matrix["score"].max() - funnel_matrix["score"].min())
	funnel_matrix = funnel_matrix.sort_values(ascending=False, by=["score"]).reset_index(drop=True)

	output = funnel_matrix.merge(apps, left_on="source_id", right_on="bundleId", how="left")

	return (output.iloc[:n])



def main(request):

	users = pd.read_parquet("data_files/users.parquet", engine="pyarrow")
	apps = pd.read_parquet("data_files/apps.parquet", engine="pyarrow")

	# Top Categories

	categories_selected_bool = True

	try:
		top_category_apps = {}
		selected_categories = request.POST.getlist("selected_categories")

		if(len(selected_categories) == 0):
			categories_selected_bool = False
			top_category_apps = {}
		
		else:
			category_based_recommendations = get_top_category_apps (5, selected_categories)

			for i in range(len(category_based_recommendations)):
				top_category_apps[category_based_recommendations["app"][i]] = {"name" : category_based_recommendations["name"][i],
																			   "categories" : " | ".join(category_based_recommendations["genres"][i]),
																			   "score" : "{:.2f}%".format(category_based_recommendations["score"][i]*100)}

	except Exception as err:
	 	categories_selected_bool = False
	 	top_category_apps = {}

	# Favorite Apps

	custom_random_apps = get_custom_random_apps (8)
	bundleid_selected = True

	try:
		content_based_output = {}
		output_selected_app = {}

		bundleid = request.POST.get("random_apps_radio")
		output_selected_app["bundleid"] = bundleid
		output_selected_app["name"] = apps[apps["bundleId"] == bundleid]["name"].item()
		output_selected_app["description"] = apps[apps["bundleId"] == bundleid]["description"].item()
		output_selected_app["categories"] = ", ".join(apps[apps["bundleId"] == bundleid]["genres"].item())

		content_based_recommendations = content_based(5, bundleid)
		content_based_recommendations.reset_index(inplace=True)

		for i in range(len(content_based_recommendations)):
			content_based_output[content_based_recommendations["bundleId"][i]] = {"score" : "{:.2f}%".format(content_based_recommendations["score"][i]*100),
													  							  "name" : content_based_recommendations["name"][i],
													  							  "genre" : ", ".join(content_based_recommendations["genres"][i]),
													  							  "description" : content_based_recommendations["description"][i]}

	except Exception as err:
	 	bundleid_selected = False
	 	content_based_output = {}


	# Collaborative

	age = request.POST.get("age_input_field")
	gender = request.POST.get("gender_input_field")
	country = request.POST.get("country_input_field")

	collaborative_recommendations = {}

	if(age is None or country is None):
		collaborative_selected = False

	else:
		collaborative_selected = True
		collaborative_output = collaborative (int(age), country, 5)

		for i in range(len(collaborative_output)):
			collaborative_recommendations[collaborative_output["source_id"][i]] = {"name" : collaborative_output["name"][i],
																	   "categories" : " | ".join(collaborative_output["genres"][i]),
																	   "score" : "{:.2f}%".format(collaborative_output["score"][i]*100)}


	return render(request, "custom.html", {"categories_selected_bool" : categories_selected_bool,
										   "top_category_apps" : top_category_apps,
										   "categories_selected" : ", ".join(selected_categories),
										   "custom_random_apps" : custom_random_apps,
										   "bundleid_selected" : bundleid_selected,
										   "selected_app" : output_selected_app,
										   "content_based_recommendations" : content_based_output,
										   "collaborative_recommendations" : collaborative_recommendations,
										   "collaborative_selected" : collaborative_selected,
										   "all_countries" : sorted(users["country_code"].unique())})

