# Real Estate & Short-Term Rental Investment Analyzer

## Project Overview
This project is an end-to-end data analytics pipeline designed to evaluate the Toronto short-term rental market. Instead of using static datasets, I built an automated Python script to extract live property data via API, parsed the deeply nested JSON, and loaded the cleaned data into a cloud-hosted PostgreSQL database. Finally, I ran a Multiple Linear Regression model to identify the dollar value of specific property features and visualized the financial insights in an interactive geospatial dashboard.

[**View the Interactive Tableau Dashboard Here**](https://public.tableau.com/app/profile/danieal.ahmed/viz/TorontoShort-TermRentalInvestmentAnalyzer/TorontoShort-TermRentalInvestmentAnalyzer)

## Tools Used
* **Python (Requests, Pandas, JSON):** Live API extraction, pagination handling, regex string parsing, and nested JSON normalization.
* **Python (Statsmodels):** Conducted OLS Multiple Linear Regression to determine statistical significance (P-values) of property features.
* **SQL (PostgreSQL / Supabase):** Cloud database engineering and advanced querying (Window Functions).
* **Tableau:** Geospatial data visualization and interactive dashboard design.

## The Process

1. **Automated Data Extraction:** Used the `requests` library in Python to hit a live RapidAPI endpoint. Engineered a loop to handle API pagination, extracting hundreds of live Toronto property listings and saving them as a raw JSON file.
2. **Data Cleaning & Normalization:** Built a robust Python script to flatten the nested JSON architecture. Used `Regex` to extract numerical values from text strings (e.g., bedrooms, bathrooms) and built error-handling logic to bypass `null` values without breaking the pipeline.
3. **Data Storage & SQL Modeling:** Pushed the cleaned Pandas DataFrame into a cloud-hosted **Supabase PostgreSQL** database using `SQLAlchemy`. Wrote SQL queries using `RANK() OVER(PARTITION BY...)` Window Functions to compare individual property prices against moving category averages. 
4. **Statistical Analysis:** Brought the clean data back into Python to run an OLS Regression model. Discovered that adding a bedroom holds a highly statistically significant impact on nightly revenue (P < 0.001), while luxury ratings showed negligible impact on pricing power.

*Here is the terminal output of the OLS Regression Model, proving the statistical significance of bedroom count on pricing:*
```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                  price   R-squared:                       0.564
Model:                            OLS   Adj. R-squared:                  0.545
==============================================================================
                 coef    std err          t      P>|t|      [0.025      0.975]
------------------------------------------------------------------------------
const      -1028.6323   8025.786     -0.128      0.898    -1.7e+04     1.5e+04
bedrooms     524.8766    121.459      4.321      0.000     282.509     767.244
bathrooms    232.2898    238.686      0.973      0.334    -244.001     708.581
rating       224.5623   1612.843      0.139      0.890   -2993.816    3442.940
==============================================================================
```

6. **Data Visualization:** Built an executive-level geospatial dashboard in Tableau. Applied Edward Tufte's data-ink ratio principles to design a minimalist heatmap and interactive trend charts, allowing investors to filter real estate targets by expected ROI.
