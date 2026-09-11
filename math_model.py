import pandas as pd
import statsmodels.api as sm

# 1. Load our data (we can use the CSV for fast analysis)
print("Loading data for statistical analysis...")
df = pd.read_csv('cleaned_airbnb_data.csv')

# 2. Define our variables
Y = df['price']
X = df[['bedrooms', 'bathrooms', 'rating']]

# 3. Add a constant.
X = sm.add_constant(X)

# 4. Fit the Multiple Linear Regression Model
print("Running Multiple Linear Regression OLS Model...\n")
model = sm.OLS(Y, X).fit()

# 5. Print the professional statistical summary
print(model.summary())