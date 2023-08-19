import pandas as pd
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import (
    confusion_matrix,
    precision_score,
    recall_score,
    fbeta_score,
    make_scorer,
    cohen_kappa_score,
    balanced_accuracy_score,
    average_precision_score,
)
from joblib import dump
import optuna
from functools import partial
import numpy as np

# Import dataset creation functions
from experiment_dataset_creators import (
    create_experiment1_dataset,
    create_experiment2_dataset,
    create_experiment3_dataset,
    create_experiment4_dataset,
)


def load_data(filepath):
    df = pd.read_csv(filepath)
    return df


def save_model(model, filename):
    dump(model, filename)


def objective(trial, X, y, beta):
    # Define hyperparameters for the decision tree
    max_depth = trial.suggest_int("max_depth", 1, 50)
    min_samples_split = trial.suggest_float("min_samples_split", 0.001, 1)
    min_samples_leaf = trial.suggest_float("min_samples_leaf", 0.001, 0.5)
    class_weight = trial.suggest_categorical("class_weight", [None, "balanced"])

    model = make_pipeline(
        StandardScaler(),
        DecisionTreeClassifier(
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            class_weight=class_weight,
        ),
    )

    score = cross_val_score(
        model, X, y, cv=5, scoring=make_scorer(fbeta_score, beta=beta)
    ).mean()
    return score


# Defining a function to compute metrics and save them to a CSV file
def compute_and_save_metrics(y_true, y_pred, beta=1, save_path=""):
    """
    Function to compute metrics and save them in a CSV file

    Parameters:
    y_true : array-like of shape (n_samples,)
        Ground truth (correct) target values.
    y_pred : array-like of shape (n_samples,)
        Estimated targets as returned by a classifier.
    model_name : string
        The name of the model for which metrics are being computed.
    beta : float, default=1
        The strength of recall versus precision in the F-beta score.

    Returns:
    None
    """

    # Computing metrics
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    fbeta = fbeta_score(y_true, y_pred, beta=beta)
    kappa = cohen_kappa_score(y_true, y_pred)
    balanced_accuracy = balanced_accuracy_score(y_true, y_pred)
    average_precision = average_precision_score(y_true, y_pred)

    # Storing metrics in a dictionary
    metrics = {}
    metrics["Precision"] = precision
    metrics["Recall"] = recall
    metrics["Fbeta Score"] = fbeta
    metrics["Cohen Kappa"] = kappa
    metrics["Balanced Accuracy"] = balanced_accuracy
    metrics["Average Precision"] = average_precision

    # Converting dictionary to DataFrame
    metrics_df = pd.DataFrame([metrics])

    # Writing DataFrame to CSV file
    file_name = save_path
    metrics_df.to_csv(file_name, index=False)


def calculate_and_save_feature_importances(model, feature_names, save_path):
    # Extract the decision tree classifier from the pipeline
    tree = model.named_steps["decisiontreeclassifier"]

    # Get the feature importances
    importances = tree.feature_importances_

    # Map the feature importances to the corresponding feature names
    feature_importances = pd.DataFrame(
        {"Feature": feature_names, "Importance": importances}
    )

    # Sort by the importance of the feature
    feature_importances = feature_importances.sort_values("Importance", ascending=False)

    feature_importances.to_csv(save_path, index=False)


def save_confusion_matrix(y_true, y_pred, filename):
    cm = confusion_matrix(y_true, y_pred)
    np.savetxt(filename, cm)


def decision_tree_experiment(
    X_train,
    y_train,
    X_test,
    y_test,
    beta,
    experiment_dictionary,
    model_directory,
    experiment_number,
):
    # Search for the hyperparameters
    study = optuna.create_study(direction="maximize")
    study.optimize(partial(objective, X=X_train, y=y_train, beta=beta), n_trials=100)

    print(
        f"Best trial recall: {study.best_trial.value}, Params: {study.best_trial.params}"
    )

    # Retrain the model with the best parameters and evaluate on the test set
    best_params = study.best_params

    best_hyperparameters = {}
    best_hyperparameters["max_depth"] = best_params["max_depth"]
    best_hyperparameters["min_samples_split"] = best_params["min_samples_split"]
    best_hyperparameters["min_samples_leaf"] = best_params["min_samples_leaf"]
    best_hyperparameters["class_weight"] = best_params["class_weight"]

    # Save hyper parameters
    hyperparameters_df = pd.DataFrame([best_hyperparameters])
    file_name = f"results/{experiment_dictionary}/hyperparameters.csv"
    hyperparameters_df.to_csv(file_name, index=False)

    model = make_pipeline(
        StandardScaler(),
        DecisionTreeClassifier(
            max_depth=best_params["max_depth"],
            min_samples_split=best_params["min_samples_split"],
            min_samples_leaf=best_params["min_samples_leaf"],
            class_weight=best_params["class_weight"],
        ),
    )

    # Train the model with best hyperparameters
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    # Compute and record the evaluation metrics
    compute_and_save_metrics(
        y_true=y_test,
        y_pred=y_pred,
        beta=beta,
        save_path=f"results/{experiment_dictionary}/metrics.csv",
    )

    # Calculate and save the feature importances
    calculate_and_save_feature_importances(
        model,
        feature_names=X_train.columns,
        save_path=f"results/{experiment_dictionary}/feature_importances.csv",
    )

    # Calculate and save the confusion matrix
    save_confusion_matrix(
        y_true=y_test,
        y_pred=y_pred,
        filename=f"results/{experiment_dictionary}/confusion_matrix.txt",
    )

    # Save the best model
    model_save_filepath = f"models/{model_directory}/{experiment_number}.joblib"

    save_model(model, model_save_filepath)


def run_decision_tree(filepath):
    # Load data
    df = load_data(filepath)

    # Create datasets for all the experiments
    X1_train, X1_test, y1_train, y1_test = create_experiment1_dataset(df)
    X2_train, X2_test, y2_train, y2_test = create_experiment2_dataset(df)
    X3_train, X3_test, y3_train, y3_test = create_experiment3_dataset(df)
    X4_train, X4_test, y4_train, y4_test = create_experiment4_dataset(df)

    # Experiment 1
    decision_tree_experiment(
        X1_train,
        y1_train,
        X1_test,
        y1_test,
        beta=2,
        experiment_dictionary="decision_tree_experiment1",
        model_directory="decision_tree",
        experiment_number="1",
    )

    # Experiment 2
    decision_tree_experiment(
        X2_train,
        y2_train,
        X2_test,
        y2_test,
        beta=2,
        experiment_dictionary="decision_tree_experiment2",
        model_directory="decision_tree",
        experiment_number="2",
    )

    # Experiment 3
    decision_tree_experiment(
        X3_train,
        y3_train,
        X3_test,
        y3_test,
        beta=2,
        experiment_dictionary="decision_tree_experiment3",
        model_directory="decision_tree",
        experiment_number="3",
    )

    # Experiment 4
    decision_tree_experiment(
        X4_train,
        y4_train,
        X4_test,
        y4_test,
        beta=2,
        experiment_dictionary="decision_tree_experiment4",
        model_directory="decision_tree",
        experiment_number="4",
    )


if __name__ == "__main__":
    run_decision_tree("data/ai4i2020.csv")
