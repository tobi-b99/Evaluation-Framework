import csv
from collections import defaultdict
import os
import pandas as pd

from evaluation_framework.Classification.classification_model import (
    ClassificationModel as Model,
)
from evaluation_framework.abstract_taskManager import AbstractTaskManager
from numpy import mean
from typing import List

task_name = "Classification"

"""
Manager of the Classification task
"""


class ClassificationManager(AbstractTaskManager):
    def __init__(self, data_manager, debugging_mode: bool, datasets: List[str] = None):
        """Constructor

        Parameters
        ----------
        data_manager
            The data manager to read the dataset(s) and the input file with the vectors to evaluate.
        debugging_mode: bool
            {TRUE, FALSE}, TRUE to run the model by reporting all the errors and information; FALSE otherwise
        datasets: List[str] or None
            None if all datasets shall be evaluated. Specific datasets can also be named using this parameter.
        """
        super().__init__()
        self.debugging_mode = debugging_mode
        self.data_manager = data_manager
        self.datasets = datasets
        if self.debugging_mode:
            print("Classification task manager initialized.")

    """
    It returns the task name.
    """

    @staticmethod
    def get_task_name():
        return task_name

    """
    It evaluates the Classification task.
    
    vectors: dataframe which contains the vectors data
    vector_file: path of the vector file
    vector_size: size of the vectors
    results_folder: directory where the results must be stored
    log_dictionary: dictionary to store all the information to store in the log file
    scores_dictionary: dictionary to store all the scores which will be used in the comparison phase
    """

    def evaluate(
        self,
        vectors: pd.DataFrame,
        vector_file: str,
        vector_size,
        results_folder,
        log_dictionary,
        scores_dictionary,
    ):
        log_errors = ""

        totalscores = defaultdict(dict)

        # check whether gold standard datasets have been passed through the constructor
        if self.datasets is not None:
            gold_standard_filenames = self.datasets
        else:
            gold_standard_filenames = self.get_gold_standard_file()

        for gold_standard_filename in gold_standard_filenames:
            gold_standard_file = ClassificationManager.get_file_for_dataset(
                gold_standard_filename
            )

            classification_model_names = ["NB", "KNN", "C45"]
            SVM_configurations = [
                pow(10, -3),
                pow(10, -2),
                0.1,
                1.0,
                10.0,
                pow(10, 2),
                pow(10, 3),
            ]

            scores = defaultdict(list)
            totalscores_element = defaultdict(list)

            data, ignored = self.data_manager.intersect_vectors_goldStandard(
                vectors=vectors,
                vector_filename=vector_file,
                vector_size=vector_size,
                goldStandard_filename=gold_standard_file,
            )
            data_coverage = len(data) / (len(data) + len(ignored))

            self.storeIgnored(results_folder, gold_standard_filename, ignored)

            if data.size == 0:
                log_errors += (
                    "Classification : Problems in merging vector with gold standard "
                    + gold_standard_file
                    + "\n"
                )
                if self.debugging_mode:
                    print(
                        "Classification : Problems in merging vector with gold standard "
                        + gold_standard_file
                    )
            else:
                for i in range(10):
                    data = data.sample(frac=1, random_state=i).reset_index(drop=True)
                    for model_name in classification_model_names:
                        # initialize the model
                        model = Model(task_name, model_name, self.debugging_mode)
                        # train and print score
                        try:
                            result = model.train(data)
                            result["gold_standard_file"] = gold_standard_filename
                            result["coverage"] = data_coverage
                            scores[model_name].append(result)
                            totalscores_element[model_name].append(result)
                        except Exception as e:
                            log_errors += (
                                "File used as gold standard: "
                                + gold_standard_filename
                                + "\n"
                            )
                            log_errors += "Classification method: " + model_name + "\n"
                            log_errors += str(e) + "\n"

                    for conf in SVM_configurations:
                        # initialize the model
                        model = Model(task_name, "SVM", self.debugging_mode, conf)
                        # train and print score
                        try:
                            result = model.train(data)
                            result["gold_standard_file"] = gold_standard_filename
                            result["coverage"] = data_coverage
                            scores["SVM"].append(result)
                            totalscores_element["SVM_" + str(conf)].append(result)
                        except Exception as e:
                            log_errors += (
                                "File used as gold standard: "
                                + gold_standard_filename
                                + "\n"
                            )
                            log_errors += (
                                "Classification method: SVM " + str(conf) + "\n"
                            )
                            log_errors += str(e) + "\n"

                self.storeResults(results_folder, gold_standard_filename, scores)
                totalscores[gold_standard_filename] = totalscores_element

        results_df = self.resultsAsDataFrame(totalscores)
        scores_dictionary[task_name] = results_df

        log_dictionary[task_name] = log_errors

    """
    It stores the entities which are in the dataset used as gold standard, but not in the input file.
    
    results_folder: directory where the results must be stored
    gold_standard_filename: the current dataset used as gold standard
    ignored: dataframe containing the ignored entities in the column NAME
    """

    def storeIgnored(self, results_folder, gold_standard_filename, ignored):
        if self.debugging_mode:
            print("Classification : Ignored data: " + str(len(ignored)))

        ignored_filepath = (
            results_folder
            + "/classification_"
            + gold_standard_filename
            + "_ignoredData.txt"
        )
        ignored["name"].to_csv(ignored_filepath, index=False, header=False)
        if self.debugging_mode:
            print(f'Classification : Ignored data: {ignored["name"].tolist()}')

    """
    It stores the results of the Classification task.
    
    results_folder: directory where the results must be stored
    gold_standard_filename: the current dataset used as gold standard
    scores: dictionary with the model_name as key and the list of all the results returned by the model for the same model_name
    """

    def storeResults(self, results_folder, gold_standard_filename, scores):
        with open(
            results_folder
            + "/classification_"
            + gold_standard_filename
            + "_results.csv",
            "w",
        ) as csv_file:
            fieldnames = [
                "task_name",
                "gold_standard_file",
                "coverage",
                "model_name",
                "model_configuration",
                "accuracy",
            ]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            for (method, scoresForMethod) in scores.items():
                for score in scoresForMethod:
                    writer.writerow(score)
                    if self.debugging_mode:
                        print("Classification " + method + " score", score)

    """
    It converts the scores dictionary into a dataframe
    
    scores: dictionary containing the gold_standard_filename as key and 
        as value a dictionary containing the model_name as key and 
            as value the list of all the results returned by the model for the same model_name
    """

    def resultsAsDataFrame(self, scores):
        data_dict = dict()
        data_dict["task_name"] = list()
        data_dict["gold_standard_file"] = list()
        data_dict["coverage"] = list()
        data_dict["model"] = list()
        data_dict["model_configuration"] = list()
        data_dict["metric"] = list()
        data_dict["score_value"] = list()

        metrics = self.get_metric_list()

        for (gold_standard_filename, gold_standard_scores) in scores.items():
            for (method, scoresForMethod) in gold_standard_scores.items():
                for metric in metrics:
                    metric_scores = list()
                    for score in scoresForMethod:
                        metric_scores.append(score[metric])
                    metric_score = mean(metric_scores)

                    score = scoresForMethod[0]
                    configuration = score["model_configuration"]
                    if configuration is None:
                        configuration = "-"

                    data_dict["task_name"].append(score["task_name"])
                    data_dict["gold_standard_file"].append(score["gold_standard_file"])
                    data_dict["coverage"].append(score["coverage"])
                    data_dict["model"].append(score["model_name"])
                    data_dict["model_configuration"].append(configuration)
                    data_dict["metric"].append(metric)
                    data_dict["score_value"].append(metric_score)

        results_df = pd.DataFrame(
            data_dict,
            columns=[
                "task_name",
                "gold_standard_file",
                "coverage",
                "model",
                "model_configuration",
                "metric",
                "score_value",
            ],
        )
        return results_df

    @staticmethod
    def get_gold_standard_file() -> List[str]:
        """It returns the dataset used as gold standard.

        Returns
        -------
            It returns the dataset used as gold standard.
        """
        return ["Cities", "MetacriticMovies", "MetacriticAlbums", "AAUP", "Forbes"]

    @staticmethod
    def get_file_for_dataset(dataset: str) -> str:
        """This method returns the absolute file path of a dataset.

        Parameters
        ----------
        dataset : str
            The dataset name for which the underlying file path shall be obtained.

        Returns
        -------
            The full path to the dataset file.
        """
        script_dir = os.path.dirname(__file__)
        rel_path = "data/" + dataset + ".tsv"
        gold_standard_file = os.path.join(script_dir, rel_path)
        return gold_standard_file

    @staticmethod
    def get_metric_list() -> List[str]:
        """It returns the metrics used in the evaluation of the classification task.

        Returns
        -------
            Metrics in a list. A metric is represented by a string.
        """
        return ["accuracy"]
