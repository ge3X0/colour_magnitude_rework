import numpy as np


a = np.arange(30).reshape((3, 2, 5))

print(a)
b = a[:, 1, 0]
print(b)
