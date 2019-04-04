from collections import defaultdict
from clustering_model import ClusteringModel as Model
import csv
import os
import pandas as pd
import sys
from numpy import mean

from code.abstract_taskManager import AbstractTaskManager

task_name = 'Clustering'

class ClusteringManager (AbstractTaskManager):
    def __init__(self, data_manager, distance_metric, debugging_mode):
        self.debugging_mode = debugging_mode
        self.data_manager = data_manager
        self.distance_metric = distance_metric
        if self.debugging_mode:
            print("Clustering task manager initialized")
            
    @staticmethod
    def get_task_name():
        return task_name

    def evaluate(self, vectors, vector_file, vector_size, results_folder, log_dictionary, scores_dictionary):
        log_errors = ""
        
        gold_standard_filenames = self.get_gold_standard_file()
        
        totalscores = defaultdict(dict)
        
        n_clusters_list = [2, 2, 5, 2]

        for i in range(len(gold_standard_filenames)):
            gold_standard_filename = gold_standard_filenames[i]
            
            script_dir = os.path.dirname(__file__)
            rel_path = "data/"+gold_standard_filename+'.tsv'
            gold_standard_file = os.path.join(script_dir, rel_path)
            
            n_clusters = n_clusters_list[i]

            clustering_models = ["DB", "KMeans", "AC", "WHC"]

            scores = defaultdict(list)
            totalscores_element = defaultdict(list)

            data, ignored = self.data_manager.intersect_vectors_goldStandard(vectors, vector_file, vector_size, gold_standard_file)
            
            self.storeIgnored(results_folder, gold_standard_filename, ignored)

            if data.size == 0:
                log_errors += 'Clustering : Problems in merging vector with gold standard ' + gold_standard_file + '\n'
                if self.debugging_mode:
                    print('Clustering : Problems in merging vector with gold standard ' + gold_standard_file)
            else:               
                for model_name in clustering_models:
                    model = Model(model_name, self.distance_metric, n_clusters, self.debugging_mode)

                    try:                    
                        result = model.train(data, ignored)
                        result['gold_standard_file'] = gold_standard_filename
                        scores[model_name].append(result)
                        totalscores_element[model_name].append(result) 
                    except Exception as e:
                        log_errors += 'File used as gold standard: ' + gold_standard_filename + '\n'
                        log_errors += 'Clustering method: ' + model_name + '\n'
                        log_errors += str(e) +'\n'
                        '''
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        log_errors += str(e) + fname + ", "+ str(exc_tb.tb_lineno) +'\n'
                        '''
                self.storeResults(results_folder, gold_standard_filename, scores) 
                totalscores[gold_standard_filename] = totalscores_element   
        
        results_df = self.resultsAsDataFrame(totalscores)
        scores_dictionary[task_name] = results_df
        
        log_dictionary['Clustering'] = log_errors
    
    def storeIgnored(self, results_folder, gold_standard_filename, ignored):
        if self.debugging_mode:
            print('Clustering: Ignored data : ' + str(len(ignored)))

        file_ignored = open(results_folder+'/clustering_'+gold_standard_filename+'_ignoredData.txt',"w") 
        for ignored_tuple in ignored.itertuples():
            if self.debugging_mode:
                print('Clustering : Ignored data: ' + getattr(ignored_tuple,'name'))
            file_ignored.write(getattr(ignored_tuple,'name').encode('utf-8')+'\n')
        file_ignored.close()

    def storeResults(self, results_folder, gold_standard_filename, scores):
        
        columns = ['task_name', 'gold_standard_file', 
        'model_name', 'model_configuration', 'num_clusters', 
        'adjusted_rand_index', 'adjusted_mutual_info_score', 
        'homogeneity_score', 'completeness_score', 'v_measure_score'] #'fowlkes_mallows_score', 
        
        with open(results_folder+'/clustering_'+gold_standard_filename+'_results.csv', "wb") as csv_file:
            fieldnames = columns 
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            for (method, scoresForMethod) in scores.items():
                for score in scoresForMethod:
                    writer.writerow(score)
                    if self.debugging_mode:
                        print('Clustering ' + method + ' score: ' +   score)      
                        
    def resultsAsDataFrame(self, scores):
        data_dict = dict()
        data_dict['task_name'] = list()
        data_dict['gold_standard_file'] = list()
        data_dict['model'] = list()
        data_dict['model_configuration'] = list()
        data_dict['metric'] = list()
        data_dict['score_value'] = list()
                
        metrics = self.get_metric_list()
        
        for (gold_standard_filename, gold_standard_scores) in scores.items():
            for (method, scoresForMethod) in gold_standard_scores.items():  
                for metric in metrics:
                    metric_scores = list()
                    for score in scoresForMethod:
                        metric_scores.append(score[metric])
                    metric_score = mean(metric_scores)
                    
                    score = scoresForMethod[0]
                    configuration = score['model_configuration']
                    if configuration is None:
                        configuration='-'
                        
                    data_dict['task_name'].append(score['task_name'])
                    data_dict['gold_standard_file'].append(score['gold_standard_file'])
                    data_dict['model'].append(score['model_name'])
                    data_dict['model_configuration'].append(configuration)
                    data_dict['metric'].append(metric)
                    data_dict['score_value'].append(metric_score)

        results_df = pd.DataFrame(data_dict, columns = ['task_name', 'gold_standard_file', 'model', 'model_configuration', 'metric', 'score_value'])
        return results_df
    
    @staticmethod
    def get_gold_standard_file():
        return ['citiesAndCountries_cluster', 'cities2000AndCountries_cluster', 'citiesMoviesAlbumsCompaniesUni_cluster', 'teams_cluster']
    
    @staticmethod
    def get_metric_list():
        return ['adjusted_rand_index', 'adjusted_mutual_info_score', 
        'homogeneity_score', 'completeness_score', 'v_measure_score']