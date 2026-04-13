import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# 設定混淆矩陣的數據
labels = ["Normal", "engine_coolant_temp"]
cm = np.array([[1366, 0], [7, 21]])

# 計算準確度
accuracy = (cm[0, 0] + cm[1, 1]) / np.sum(cm)

# 繪製混淆矩陣
plt.figure(figsize=(6, 5))
ax = sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels, cbar=False, annot_kws={"size": 14})

# 添加標題和標籤
plt.title("Confusion Matrix for engine_coolant_temp", fontsize=14)
plt.xlabel("Predicted Label", fontsize=12)
plt.ylabel("True Label", fontsize=12)

# 在底部顯示準確率
plt.figtext(0.5, -0.05, f"Accuracy: {accuracy:.4f}", ha="center", fontsize=12)

# 顯示圖表
plt.show()
