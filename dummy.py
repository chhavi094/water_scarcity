import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
import pickle

# Load dataset
data = pd.read_csv('water_potability.csv')

# Handle missing values
data.fillna(data.mean(), inplace=True)

# Features for classification
X_class = data[['ph', 'Hardness', 'Turbidity']]
y_class = data['Potability']

# Features for regression
X_reg = X_class
y_reg = data[['Solids', 'Chloramines', 'Sulfate', 'Conductivity']]

# Split data
X_class_train, X_class_test, y_class_train, y_class_test = train_test_split(X_class, y_class, test_size=0.2, random_state=42)
X_reg_train, X_reg_test, y_reg_train, y_reg_test = train_test_split(X_reg, y_reg, test_size=0.2, random_state=42)

# Train classifier
clf = RandomForestClassifier(random_state=42, n_estimators=100)
clf.fit(X_class_train, y_class_train)
print(f"Classifier Accuracy: {accuracy_score(y_class_test, clf.predict(X_class_test)):.2f}")

# Train regressor
reg = RandomForestRegressor(random_state=42, n_estimators=100)
reg.fit(X_reg_train, y_reg_train)
print(f"Regressor RMSE: {mean_squared_error(y_reg_test, reg.predict(X_reg_test), squared=False):.2f}")

# Save models
with open('random_forest_classifier.pkl', 'wb') as f:
    pickle.dump(clf, f)

with open('random_forest_regressor.pkl', 'wb') as f:
    pickle.dump(reg, f)

print("Models saved.")
