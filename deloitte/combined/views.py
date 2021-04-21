from django.shortcuts import render
from django.http import HttpResponse

import pandas as pd
import random

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def get_top_category_apps (l):
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
	
	output = merged_df.merge(apps, left_on="app", right_on="bundleId", how="left")
	output = output[["bundleId", "score", "name", "genres"]]

	return (output)


def get_custom_random_apps (n):

	apps = pd.read_parquet("data_files/apps.parquet", engine="pyarrow")
	list_ind = random.sample(range(len(apps)), n)
	random_apps = {}
	for ind in list_ind:
		random_apps[apps["bundleId"].loc[ind]] = apps["name"].loc[ind]

	return (random_apps)


def content_based (bundleid):
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

	sorted_recommendations = similarity_matrix.loc[bundleid, :]

	output = sorted_recommendations.to_frame()
	output["bundleId"] = output.index
	output = output.merge(apps, on="bundleId", how="left")
	output["score"] = output[bundleid]
	output = output[["bundleId", "score"]]

	return (output)


def collaborative (age, country):
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

	output = funnel_matrix.merge(apps, left_on="source_id", right_on="bundleId", how="left")
	output = output[["source_id", "score"]]

	return (output)


def combination(n, l, bundleid, age, country):
	category_based_df = get_top_category_apps (l)
	content_based_df = content_based (bundleid)
	collaborative_df = collaborative (age, country)

	merged_df = category_based_df.merge(content_based_df, on="bundleId", how="left")
	merged_df = merged_df.merge(collaborative_df, left_on="bundleId", right_on="source_id", how="left")

	merged_df["final_score"] = (merged_df["score"] + merged_df["score_x"] + merged_df["score_y"])/3
	merged_df = merged_df.sort_values(ascending=False, by=["final_score"]).reset_index(drop=True)
	return(merged_df.iloc[:n])


def main(request):

	users = pd.read_parquet("data_files/users.parquet", engine="pyarrow")
	apps = pd.read_parquet("data_files/apps.parquet", engine="pyarrow")

	selected_categories = request.POST.getlist("selected_categories")
	bundleid = request.POST.get("random_apps_radio")
	age = request.POST.get("age_input_field")
	gender = request.POST.get("gender_input_field")
	country = request.POST.get("country_input_field")

	recommendations = {}

	custom_random_apps = get_custom_random_apps (8)

	if(len(selected_categories) == 0 or bundleid is None or age is None or country is None):
		all_selections_done = False
		recommendations = {}
	
	else:
		all_selections_done = True
		recommendations_df = combination(5, selected_categories, bundleid, int(age), country)

		for i in range(len(recommendations_df)):
			recommendations[recommendations_df["bundleId"][i]] = {"name" : recommendations_df["name"][i],
																  "categories" : " | ".join(recommendations_df["genres"][i]),
																  "score" : "{:.2f}%".format(recommendations_df["score"][i]*100)}


	return render(request, "combined.html", {"categories_selected" : ", ".join(selected_categories),
										     "custom_random_apps" : custom_random_apps,
										     "selected_app" : bundleid,
										     "all_countries" : sorted(users["country_code"].unique()),
										     "all_selections_done" : all_selections_done,
										     "combined_recommendations" : recommendations})
