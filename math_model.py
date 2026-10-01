"""Describe associations with advertised stay prices in the saved sample."""

from pathlib import Path

import pandas as pd
import statsmodels.api as sm


CSV_PATH = Path(__file__).resolve().parent / "cleaned_airbnb_data.csv"
MODEL_COLUMNS = ["price", "bedrooms", "bathrooms", "rating"]


def fit_model(path=CSV_PATH):
    data = pd.read_csv(path, usecols=MODEL_COLUMNS)
    for column in MODEL_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="raise")
    observations = data.dropna(subset=MODEL_COLUMNS)
    if len(observations) <= len(MODEL_COLUMNS):
        raise ValueError("Not enough complete observations to fit the model")
    predictors = sm.add_constant(observations[["bedrooms", "bathrooms", "rating"]])
    result = sm.OLS(observations["price"], predictors).fit(cov_type="HC3")
    return result, len(data), len(observations)


def main():
    result, total, used = fit_model()
    bounds = result.conf_int()
    summary = pd.DataFrame({
        "coefficient": result.params,
        "ci_lower": bounds[0],
        "ci_upper": bounds[1],
        "p_value": result.pvalues,
    })
    print("Outcome: advertised stay price; associations from OLS with HC3 standard errors")
    print(f"Observations used: {used} of {total} listings")
    print(f"R-squared: {result.rsquared:.3f}")
    print(summary.round(4).to_string())


if __name__ == "__main__":
    main()
