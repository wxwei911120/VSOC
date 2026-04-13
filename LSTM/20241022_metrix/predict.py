# Add necessary imports
from sklearn.metrics import confusion_matrix
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

# Load the data with anomalies to evaluate
csv_file_path = 'datawithanomaly.csv'  # Update this path if necessary
df_anomaly = pd.read_csv(csv_file_path, encoding='utf-8')

# Define time steps for LSTM prediction, assumed from the context
time_steps = 10  # Example value, replace with your actual time steps

# Specify the columns you want to predict (the seven models)
columns_to_predict = [
    'vehicle_speed', 
    'engine_rpm', 
    'engine_coolant_temp', 
    'air_flow_rate_maf', 
    'battery', 
    'intake_air_temp', 
    'throttle_position'
]

predicted_results = {}
anomalies_by_column = {}

for column in columns_to_predict:
    # Load the scaler and model (the code assumes these are named based on the column names)
    model_filename = f"{column}_model.h5"
    scaler = MinMaxScaler()  # Replace with actual loading if necessary
    model = load_model(model_filename)
    
    # Prepare the data for prediction
    scaled_data = scaler.fit_transform(df_anomaly[[column]].values)
    X_test = [scaled_data[i - time_steps:i] for i in range(time_steps, len(scaled_data))]
    X_test = np.array(X_test)
    
    # Perform predictions
    predictions = model.predict(X_test)
    predicted_values = scaler.inverse_transform(predictions)
    predicted_results[column] = predicted_values
    
    # Calculate MAE for anomaly detection
    true_values = scaler.inverse_transform(scaled_data[time_steps:])
    mae_per_sample = np.mean(np.abs(predicted_values - true_values), axis=1)
    mae_mean = np.mean(mae_per_sample)
    std_dev = np.std(mae_per_sample)
    
    # Set the anomaly detection threshold
    upper_threshold = mae_mean + 3 * std_dev  # Adjust sensitivity as needed
    lower_threshold = mae_mean - 3 * std_dev
    anomalies = (mae_per_sample > upper_threshold) | (mae_per_sample < lower_threshold)
    anomalies_indices = np.where(anomalies)[0]
    anomalies_by_column[column] = anomalies_indices
    
    # Save anomaly results back to the dataframe
    for idx in anomalies_indices:
        csv_idx = idx + time_steps
        if pd.isna(df_anomaly.at[csv_idx, 'anomaly']):
            df_anomaly.at[csv_idx, 'anomaly'] = column
        else:
            df_anomaly.at[csv_idx, 'anomaly'] += f",{column}"
    
    # Visualization part (for prediction vs true values)
    plt.figure(figsize=(10, 5))
    plt.plot(range(len(true_values)), true_values, label='True Value', color='dodgerblue', alpha=1)  # Lighter blue
    plt.plot(range(len(predicted_values)), predicted_values, label='Predicted Value', color='orange', alpha=1)
    plt.title(f'{column} Prediction')
    plt.xlabel('Sample')
    plt.ylabel(column)
    plt.legend()
    plt.tight_layout()
    plt.show()

# Save the updated dataframe with anomaly detection results
df_anomaly.to_csv('datawithanomaly.csv', index=False, encoding='utf-8-sig')

# Generate and display confusion matrix for each column in the console
df_anomaly['anomaly'] = df_anomaly['anomaly'].fillna('Normal')  # Consider 'Normal' for non-anomalous cases
df_anomaly['predicted_anomaly'] = ['Normal'] * len(df_anomaly)  # Initialize with 'Normal'

# Update 'predicted_anomaly' based on the detected anomalies
for column, indices in anomalies_by_column.items():
    for idx in indices:
        df_anomaly.at[idx + time_steps, 'predicted_anomaly'] = column

# Create and print confusion matrix and accuracy for each column
for column in columns_to_predict:
    # Create binary true and predicted labels for this column
    true_labels = df_anomaly['anomaly'].apply(lambda x: column if column in x else 'Normal')
    predicted_labels = df_anomaly['predicted_anomaly'].apply(lambda x: column if column in x else 'Normal')

    # Generate confusion matrix
    conf_matrix = confusion_matrix(true_labels, predicted_labels, labels=['Normal', column])
    conf_matrix_df = pd.DataFrame(conf_matrix, index=['Normal', column], columns=['Normal', column])

    # Calculate accuracy
    TP = conf_matrix[1, 1]  # True Positive
    TN = conf_matrix[0, 0]  # True Negative
    FP = conf_matrix[0, 1]  # False Positive
    FN = conf_matrix[1, 0]  # False Negative
    total = TP + TN + FP + FN
    accuracy = (TP + TN) / total if total > 0 else 0

    # Print the confusion matrix and accuracy in the console
    print(f"\nConfusion Matrix for {column}:")
    print(conf_matrix_df)
    print(f"True Positive (TP): {TP}")
    print(f"True Negative (TN): {TN}")
    print(f"False Positive (FP): {FP}")
    print(f"False Negative (FN): {FN}")
    print(f"Accuracy: {accuracy:.4f}")

print("\nConfusion matrices and accuracies calculated and displayed in the console for each column.")
