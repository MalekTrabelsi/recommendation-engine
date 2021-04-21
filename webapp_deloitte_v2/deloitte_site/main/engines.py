import numpy as np
import pandas as pd
from abc import ABC

# Recommandation Engines Models
class Engine(ABC):
    def fit(self, train_set, val_set):
        pass
    def top_K(self, user, K):
        pass

class popularity_model(Engine):
    def __init__(self, pop_apps=[]):
        self.pop_apps = pop_apps

    def fit(self, train_set, val_set):
        '''
        This model does not include an optimization process
        So the val_set is used in the training
        '''

        df = pd.concat([train_set, val_set])
        try:
            self.pop_apps = df['Advertiser_ID'].value_counts().index.to_list()
            print("The model is trained successfully ! ")
        except:
            print("Oops ! a problem happened during fitting !")

    def top_K(self, K=5):
        try:
            result = self.pop_apps[:K]
        except:
            print("Oops ! your model is not well trained or not enough items")

        return result