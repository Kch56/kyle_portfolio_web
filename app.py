import os
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_mail import Mail, Message
from werkzeug.security import check_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("BLOG_DB_PATH", BASE_DIR / "data" / "blog.db"))

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", secrets.token_hex(32)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "465")),
    MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "false").lower() == "true",
    MAIL_USE_SSL=os.getenv("MAIL_USE_SSL", "true").lower() == "true",
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME")),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",
)
mail = Mail(app)


CURRENT_PROJECTS = {
    "charlotte-neighborhood-change": {
        "title": "Under Pressure: Housing Affordability and Displacement Vulnerability",
        "status": "Completed",
        "summary": "An exploratory data science study of housing affordability pressure and displacement vulnerability across Mecklenburg County census tracts and Charlotte neighborhoods.",
        "overview": "This project began with a broad question about displacement risk and gentrification. After reviewing the available data, I narrowed the analysis to outcomes the datasets could support: characteristics associated with rent burden across Mecklenburg County census tracts and a separate description of the City of Charlotte's displacement-vulnerability classification. Keeping those analyses separate prevented the project from treating a constructed vulnerability score as proof that displacement occurred.",
        "original_question": "What housing, demographic, and economic factors are most strongly associated with displacement risk in Charlotte neighborhoods, and to what extent can changes in affordable housing, income, and housing costs identify communities experiencing gentrification?",
        "question": "Which housing, demographic, and economic characteristics are associated with rent burden across Mecklenburg County census tracts, and what patterns of neighborhood displacement vulnerability appear in City of Charlotte data?",
        "final_finding": "Income and educational attainment were the factors most strongly associated with renter affordability pressure. These conditions may increase vulnerability to displacement because financially burdened households have less ability to absorb rent increases or income losses. However, the data does not prove that displacement or gentrification occurred because it does not directly measure forced moves or consistent neighborhood changes over time.",
        "contribution": "I collected public data through the U.S. Census Bureau and City of Charlotte APIs, cleaned and merged tract-level measurements, handled missing observations, explored housing and demographic variables, and created visualizations to compare affordability patterns. I also documented the limits of the analysis so associations would not be presented as causal findings.",
        "impact": "The question remains relevant to residents, housing organizations, and local planners because affordability pressure may leave households less able to absorb a rent increase or income loss. The analysis identifies patterns worth investigating, but it does not estimate a household's probability of displacement or identify neighborhoods that have gentrified.",
        "tools": ["Python", "Pandas", "Census API", "ArcGIS REST API", "Data Visualization", "Statistical Analysis"],
        "repository_url": "https://github.com/Kch56/Under-Pressure-Housing-Affordability-and-Displacement-Vulnerability/tree/main",
        "data_notes": [
            "The ACS figures summarize estimates collected across 2020–2024, not measurements from one moment in 2024. The July 2025 label in the Housing Locational Tool identifies a snapshot and does not confirm that every underlying City measure was observed in 2025.",
            "Census tracts and Neighborhood Profile Areas are different geographic units. Census tables were joined by state, county, and tract codes, while City tables were joined by NPA identifiers. I analyzed the two geographies separately and did not directly merge NPAs with census tracts. Mecklenburg County also includes places outside Charlotte's municipal limits.",
            "The merged ACS data contained 305 tract records. The final comparison used 296 tracts after excluding nine records missing a required measurement.",
        ],
        "cleaning_notes": [
            "I converted Census fields into usable numeric values and treated negative placeholder codes as missing instead of real incomes, rents, or counts. This let me keep the other valid measurements from a tract rather than removing the entire record. City percentage fields were cleaned by removing percent symbols, while legitimate zero counts were preserved.",
            "Rent burden was calculated from ACS table B25070 after removing households whose burden could not be computed. I combined the categories spending 30% or more of income on rent and used checks that prevented incomplete counts or invalid denominators from producing misleading percentages.",
            "I required one-to-one identifier matches so duplicate records would cause an error instead of silently multiplying rows. The City API was downloaded in pages, and fields with unclear or implausible values, including the available sales-price summaries, were excluded from the conclusions. The final correlation comparison used the same 296 complete tracts for every characteristic.",
        ],
        "definitions": [
            {
                "concept": "Rent burden",
                "definition": "Cash-rent renter households spending at least 30% of household income on gross rent, divided by renter households with computable burden.",
                "source": "ACS B25070",
                "url": "https://api.census.gov/data/2024/acs/acs5/groups/B25070.html",
            },
            {
                "concept": "Severe rent burden",
                "definition": "The same renter-household denominator, but spending at least 50% of income on gross rent. This group is already included in the 30% or more measure.",
                "source": "ACS B25070",
                "url": "https://api.census.gov/data/2024/acs/acs5/groups/B25070.html",
            },
            {
                "concept": "Income and housing costs",
                "definition": "Median annual household income for all households and median monthly gross rent, including applicable utilities.",
                "source": "ACS B19013 and B25064",
                "url": "https://api.census.gov/data/2024/acs/acs5/groups/B19013.html",
            },
            {
                "concept": "Unemployment",
                "definition": "Unemployed civilians divided by the civilian labor force, multiplied by 100.",
                "source": "ACS B23025",
                "url": "https://api.census.gov/data/2024/acs/acs5/groups/B23025.html",
            },
            {
                "concept": "Educational attainment",
                "definition": "Adults age 25 or older with a bachelor's, master's, professional, or doctoral degree as a percentage of all adults age 25 or older.",
                "source": "ACS B15003",
                "url": "https://api.census.gov/data/2024/acs/acs5/groups/B15003.html",
            },
            {
                "concept": "Racial and ethnic composition",
                "definition": "Population shares for seven non-Hispanic racial categories and Hispanic or Latino residents of any race.",
                "source": "ACS B03002",
                "url": "https://api.census.gov/data/2024/acs/acs5/groups/B03002.html",
            },
            {
                "concept": "Renter share",
                "definition": "Renter-occupied housing units divided by all occupied housing units, multiplied by 100.",
                "source": "ACS B25003",
                "url": "https://api.census.gov/data/2024/acs/acs5/groups/B25003.html",
            },
            {
                "concept": "Displacement vulnerability",
                "definition": "The City's existing 0–5 score and Yes or No classification. These are classifications, not observed displacement or calibrated probabilities.",
                "source": "City displacement layer",
                "url": "https://gis.charlottenc.gov/arcgis/rest/services/ODP/City_Space_ODP_Data/MapServer/1",
            },
        ],
        "findings": [
            {
                "title": "Housing costs provide context, but do not describe affordability by themselves",
                "body": "Most tract median rents fall between about $1,200 and $2,200 per month, with fewer tracts at the extremes. This describes neighborhood medians, not the rents paid by every household or the number of units available at each price.",
                "image": "images/charlotte-housing/median-rent-distribution.png",
                "alt": "Histogram showing median monthly gross rents across Mecklenburg County census tracts, with most tracts between roughly $1,200 and $2,200",
                "caption": "Figure 1. Distribution of median monthly gross rents. Source: 2020–2024 ACS, author analysis.",
            },
            {
                "title": "Similar rent levels can come with very different affordability pressure",
                "body": "Tracts with similar median rents show very different rent-burden rates. The income color scale adds context, but it represents all households rather than renter households specifically. A higher neighborhood median rent does not automatically mean a larger share of renters is burdened.",
                "image": "images/charlotte-housing/rent-and-burden.png",
                "alt": "Scatterplot of median gross rent and rent burden across Mecklenburg County census tracts, colored by median household income",
                "caption": "Figure 2. Median gross rent and estimated rent burden, colored by median annual household income. Source: 2020–2024 ACS, author analysis.",
            },
            {
                "title": "Income and education show the strongest observed associations",
                "body": "Median household income has the largest absolute Spearman correlation with rent burden at −0.388, followed by the share of adults with a bachelor's degree or higher at −0.329. Median rent is −0.253, unemployment is 0.167, and renter share is close to zero at 0.036. These coefficients show direction and strength of association, not how much hardship each characteristic causes.",
                "image": "images/charlotte-housing/characteristics-correlation.png",
                "alt": "Horizontal bar chart of Spearman correlations between neighborhood characteristics and rent burden for 296 census tracts",
                "caption": "Figure 3. Separate Spearman correlations with rent burden for 296 tracts. Source: 2020–2024 ACS, author analysis.",
            },
            {
                "title": "Race and ethnicity results describe places, not individual experiences",
                "body": "The Hispanic or Latino population share has a correlation of 0.220 with rent burden, while the non-Hispanic Black share is 0.214 and the non-Hispanic White share is −0.262. These tract-level relationships cannot show the burden experienced by individual racial or ethnic groups. Income, wealth, housing access, and historical segregation are important context for future research, not mechanisms proven by this study.",
            },
            {
                "title": "The highest estimates are not precise neighborhood rankings",
                "body": "Several tracts with high point estimates also have very wide approximate 90% uncertainty ranges. For example, the displayed range for tract 005721 spans 0%–100%. The chart helps identify places worth examining, but it does not justify declaring one tract definitively more affected than another.",
                "image": "images/charlotte-housing/rent-burden-uncertainty.png",
                "alt": "Chart of the ten highest estimated rent-burden rates with wide approximate 90 percent uncertainty ranges",
                "caption": "Figure 4. Ten highest estimated rent-burden rates with approximate 90% uncertainty ranges. Source: 2020–2024 ACS, author analysis.",
            },
            {
                "title": "City data provides a separate neighborhood perspective",
                "body": "Higher City vulnerability scores appear more often among lower-income NPAs. This is descriptive rather than a synchronized test because the vulnerability layer and July 2025 income snapshot do not have a verified common observation period.",
                "image": "images/charlotte-housing/income-and-vulnerability.png",
                "alt": "Scatterplot comparing City displacement vulnerability scores with median household income from the July 2025 housing snapshot",
                "caption": "Figure 5. City vulnerability score compared with income from the July 2025 housing snapshot. Source: City of Charlotte APIs, author analysis.",
            },
            {
                "title": "The City classification reflects some of its own inputs",
                "body": "Many NPAs classified as vulnerable appear in areas with higher poverty and lower homeownership. Poverty and homeownership already contribute to the City's score, so part of this pattern follows from how the classification is built. It should not be treated as independent confirmation of displacement.",
                "image": "images/charlotte-housing/poverty-and-homeownership.png",
                "alt": "Scatterplot of poverty and homeownership across Charlotte Neighborhood Profile Areas, colored by displacement vulnerability classification",
                "caption": "Figure 6. Poverty and homeownership by City vulnerability classification. Source: City displacement layer, author analysis.",
            },
        ],
        "limitations": [
            "This study measures affordability pressure and vulnerability, not whether a household was forced to move. The original questions about confirmed gentrification and changes in affordable housing remain unanswered because the project does not include valid longitudinal measures of those outcomes.",
            "ACS estimates include sampling uncertainty, especially for smaller groups. The correlation comparison does not carry that uncertainty into the coefficients, and excluding nine incomplete tracts may affect how representative the final sample is.",
            "The measures describe different populations. Median income includes owners and renters, rent burden covers cash-rent renter households, education covers adults 25 and older, and racial composition covers the entire tract. Tract-level correlations cannot be used to make claims about individuals.",
            "Each tract receives equal weight, nearby housing-market conditions are not modeled, and the analysis shows association rather than cause. Race is included to examine how housing pressure is distributed, not to label residents or neighborhoods as responsible for that pressure.",
            "A stronger follow-up would use renter-specific income, comparable time periods with harmonized boundaries, inflation-adjusted costs, dated affordable-housing additions and losses, and direct evidence such as longitudinal household data or resident surveys.",
        ],
        "sources": [
            {
                "name": "U.S. Census Bureau, 2024 ACS Five-Year API",
                "url": "https://api.census.gov/data/2024/acs/acs5.html",
                "role": "Provided 2020–2024 estimates of income, rent, population, rent burden, employment, education, racial and ethnic composition, and housing tenure.",
            },
            {
                "name": "City of Charlotte, Vulnerability to Displacement by NPA",
                "url": "https://gis.charlottenc.gov/arcgis/rest/services/ODP/City_Space_ODP_Data/MapServer/1",
                "role": "Provided the City vulnerability score and classification, along with poverty, homeownership, education, age, and demographic fields.",
            },
            {
                "name": "City of Charlotte, Housing Locational Tool",
                "url": "https://gis.charlottenc.gov/arcgis/rest/services/HNS/NPA_HLT/FeatureServer/0",
                "role": "Provided July 2025 neighborhood income for a separate NPA comparison. Sales-price fields were investigated but not used for conclusions.",
            },
        ],
    },
    "charlotte-crash-forecasting": {
        "title": "Where Will Charlotte Crashes Cluster Next Month?",
        "status": "Completed",
        "summary": "A machine-learning study that forecasts monthly reported crash counts across 500-meter Charlotte grid cells and identifies areas that may deserve closer transportation-safety review.",
        "overview": "Reported crashes are not distributed evenly across Charlotte. This project tests whether recent crash history can help identify the small set of areas likely to contain a larger share of next month's reported crashes. Each prediction is a count for one 500-meter grid cell and one calendar month. The cells are then ranked to support closer review. The model does not predict the exact location or time of an individual crash.",
        "question": "Can past crash patterns predict which 500-meter areas of Charlotte will have higher reported crash counts next month, and do separate morning and afternoon forecasts improve the hotspot picture?",
        "final_finding": "Past crash counts helped identify where future reported crashes clustered, but the improvement over a straightforward history-based baseline was modest. In December 2024, the top-ranked 5% of cells captured 41.5% of all-day reported crashes. Separate morning and afternoon models did not meaningfully improve the hotspot rankings, so the all-day monthly model remained the main result.",
        "contribution": "I cleaned and prepared public crash records, converted locations into 500-meter spatial cells, created time-based lag features, built chronological training and evaluation periods, compared a baseline with decision-tree and linear-regression models, and evaluated both prediction error and hotspot capture. I also examined weather, time-of-day patterns, model interpretation, and responsible-use limitations.",
        "impact": "A ranked list of areas could help transportation analysts decide where to begin a closer safety review. It should be combined with traffic volume, road design, field observations, and community input. It is an exploratory screening tool, not a recommendation for enforcement or resource allocation by itself.",
        "tools": ["Python", "Pandas", "Scikit-learn", "Spatial Analysis", "Time-based Validation", "Data Visualization"],
        "repository_url": "https://github.com/Kch56/Where-Will-Charlotte-Crashes-Cluster-Next-Month-",
        "metrics": [
            {"value": "41.5%", "label": "All-day crashes captured", "note": "1,604 of 3,864 December crashes in the predicted top 5% of cells"},
            {"value": "38.4%", "label": "Morning crashes captured", "note": "406 of 1,058 December morning crashes"},
            {"value": "42.6%", "label": "Afternoon crashes captured", "note": "855 of 2,009 December afternoon crashes"},
        ],
        "data_notes": [
            "The main source contained 540,865 crash records covering 2010 through 2026 at the time of analysis. The modeling period uses 2018 through 2024. After the year and location checks, 276,118 crash records remained.",
            "Each modeling row represents one 500-meter grid cell in one calendar month. The fixed study area contains 4,146 cells observed by the end of 2022 and 348,264 cell-month rows from January 2018 through December 2024. About 69% of those rows contain zero crashes.",
            "The training period runs from April 2018 through December 2022. The year 2023 is used to compare models and settings, and 2024 is used for evaluation. Forecasts roll forward one month at a time, so a December forecast can use observed information through November.",
        ],
        "cleaning_notes": [
            "I converted crash timestamps to Charlotte local dates, checked crash identifiers, removed records with missing or implausible Charlotte-area coordinates, and assigned each retained point to a 500-meter square using projected coordinates.",
            "I added zero-crash rows for every month in each selected cell so the model would learn from both active and quiet locations. Previous-month features were shifted by one month to prevent the model from seeing the outcome it was trying to predict.",
            "The final predictors were grid location, calendar month, last month's crash count, the prior three-month average, and the prior 12-month average. Negative linear predictions were set to zero because a crash count cannot be negative.",
            "Daily airport weather was explored, but observed weather from the forecast month was not used as an input because it would not be known when the forecast was created.",
        ],
        "model_results": [
            {"method": "Prior three-month average", "validation": "0.585", "evaluation": "0.588", "share": "40.0%"},
            {"method": "Decision tree", "validation": "0.571", "evaluation": "0.568", "share": "41.0%"},
            {"method": "Linear regression", "validation": "0.565", "evaluation": "0.564", "share": "41.1%"},
        ],
        "findings": [
            {
                "title": "Reported crashes changed over the study period",
                "body": "The yearly totals show a clear decline in 2020 followed by later changes. The chart is descriptive and the study does not assign a cause to those changes.",
                "image": "images/charlotte-crash-forecast/crashes-by-year.png",
                "alt": "Bar chart of yearly reported crash counts in the selected Charlotte crash data",
                "caption": "Reported crash totals by year in the cleaned 2018–2024 data. Source: City of Charlotte crash layer, author analysis.",
            },
            {
                "title": "Afternoon hours contain many of the reported crashes",
                "body": "The day-and-hour pattern shows particularly high counts on weekday afternoons. Because the data does not include traffic exposure, this describes when crashes were reported rather than a driver's per-trip risk.",
                "image": "images/charlotte-crash-forecast/crashes-by-day-and-hour.png",
                "alt": "Heatmap of reported crash counts by day of week and hour",
                "caption": "Reported crash counts by local day of week and hour. Source: City of Charlotte crash layer, author analysis.",
            },
            {
                "title": "Weather was useful context but not a forecast input",
                "body": "The data averaged 107.2 reported crashes on dry days and 109.6 on wet days. This small descriptive difference does not establish that rain caused more crashes. Airport weather also does not represent conditions at every road and hour.",
                "image": "images/charlotte-crash-forecast/weather-and-daily-crashes.png",
                "alt": "Chart comparing daily precipitation with reported crash counts",
                "caption": "Exploratory comparison using observed airport conditions and daily crash totals. Source: NOAA and City of Charlotte data, author analysis.",
            },
            {
                "title": "Recent yearly history was the model's strongest feature",
                "body": "The previous 12-month average was the most useful feature in the permutation test. The three-month average and last month's count also helped. Calendar month and grid coordinates added little once recent crash history was included. These overlapping features should not be interpreted as independent causes.",
                "image": "images/charlotte-crash-forecast/feature-importance.png",
                "alt": "Permutation feature importance chart for the 2024 linear regression model",
                "caption": "Increase in prediction error after each feature is shuffled. Source: author analysis.",
            },
            {
                "title": "The model underpredicted the busiest cell-months",
                "body": "For cell-months with at least five crashes, the average observed count was 7.84 while the average prediction was 6.38. The overall error looks smaller partly because most cell-months have zero or very few crashes.",
                "image": "images/charlotte-crash-forecast/prediction-error-by-activity.png",
                "alt": "Chart comparing average actual and predicted crashes for groups of cell-months",
                "caption": "Average actual and predicted counts grouped by observed crash activity. Source: author analysis.",
            },
            {
                "title": "The top-ranked cells captured a large share of December crashes",
                "body": "The all-day model's predicted top 5% of cells contained 1,604 of 3,864 reported December crashes. The morning and afternoon maps show how the shortlist changes by time period.",
                "image": "images/charlotte-crash-forecast/december-forecast-hotspots.png",
                "alt": "Maps of predicted top five percent crash hotspot cells for all-day, morning, and afternoon in December 2024",
                "caption": "December 2024 retrospective predictions. Grid indices represent projected map cells, not street names. Source: author analysis.",
            },
            {
                "title": "Observed busy cells were more dispersed than the main predicted cluster",
                "body": "Several of the cells with the largest recorded December counts align with the central predicted cluster, while other busy cells are scattered more widely. Ties among low-count cells can affect exact top-5% membership.",
                "image": "images/charlotte-crash-forecast/december-observed-hotspots.png",
                "alt": "Maps of observed top five percent crash cells for all-day, morning, and afternoon in December 2024",
                "caption": "Cells with the largest recorded December counts. Source: City of Charlotte crash layer, author analysis.",
            },
        ],
        "limitations": [
            "A high crash count can reflect a busy road rather than a higher crash rate per driver. Without traffic-volume data, the study cannot compare personal driving risk across locations.",
            "The coordinate filter is a practical Charlotte-area rectangle rather than an official municipal boundary, and the fixed study area excludes cells first observed after 2022.",
            "The linear model performs less accurately in the busiest cells and tends to underpredict their counts. A low-ranked cell that later experiences many crashes could be missed during screening.",
            "Crash reports may reflect differences in recording practices or location accuracy. The results should not be used to label residents or neighborhoods as unsafe or to guide enforcement on their own.",
            "A stronger follow-up would add roadway characteristics, traffic exposure, archived weather forecasts, and later untouched evaluation years.",
        ],
        "sources": [
            {
                "name": "City of Charlotte, Crashes",
                "url": "https://gis.charlottenc.gov/arcgis/rest/services/CDOT/TCLS_Crashes/MapServer/0",
                "role": "Provided crash identifiers, dates, times, and coordinates used to create spatial cells, lagged counts, and evaluation results.",
            },
            {
                "name": "NOAA NCEI, Charlotte Douglas Airport",
                "url": "https://www.ncei.noaa.gov/cdo-web/datasets/LCD/stations/WBAN%3A13881/detail",
                "role": "Provided daily precipitation and temperature observations for the exploratory weather comparison.",
            },
            {
                "name": "Federal Highway Administration, Network Screening",
                "url": "https://highways.dot.gov/safety/data-analysis-tools/systemic/screening-your-network-improve-roadway-safety-performance",
                "role": "Provided background on using crash history and roadway information to identify locations for closer safety investigation.",
            },
            {
                "name": "Federal Highway Administration, Rain and Flooding",
                "url": "https://ops.fhwa.dot.gov/weather/weather_events/rain_flooding.htm",
                "role": "Provided context for exploring the relationship between wet conditions and roadway safety.",
            },
        ],
    },
    "emergency-response-modeling": {
        "title": "Emergency Response Modeling",
        "status": "Ongoing",
        "summary": "Spatial analysis tools for studying response coverage, travel patterns, and planning scenarios.",
        "overview": "This work uses historical and geographic information to study how emergency resources move through a growing city. It replaces broad assumptions with patterns grounded in actual operating conditions while keeping the results understandable for nontechnical users.",
        "question": "How can historical travel information and spatial modeling support more realistic response-planning scenarios?",
        "contribution": "I prepare and validate location-based data, build analysis workflows in Python, compare travel patterns across time and geography, and turn the results into maps and planning outputs.",
        "impact": "The project gives planners another evidence-based way to explore coverage, compare scenarios, and discuss where further investigation may be useful.",
        "tools": ["Python", "GIS", "GeoPandas", "Spatial Analysis", "Data Preparation"],
    },
    "risk-informed-planning": {
        "title": "Risk-Informed Planning",
        "status": "Ongoing",
        "summary": "Clear and explainable ways to combine location-based information with operational planning.",
        "overview": "This project explores how several indicators can be organized into a consistent planning framework. The focus is on making every classification traceable so users can understand why an area receives a result instead of seeing a score with no explanation.",
        "question": "How can location-based indicators support planning while preserving transparency and human review?",
        "contribution": "I research possible indicators, prepare spatial datasets, document assumptions, compare classification approaches, and design outputs that allow users to review the information behind each result.",
        "impact": "The work supports more consistent scenario analysis while keeping professional judgment and review at the center of the process.",
        "tools": ["GIS", "Data Architecture", "Research", "Process Design", "Data Visualization"],
    },
    "grant-research-tool": {
        "title": "Grant Research Tool",
        "status": "In Development",
        "summary": "A tool that helps teams search, organize, and review funding opportunities more efficiently.",
        "overview": "Grant research often means reviewing information spread across many websites and documents. This application concept brings the most useful details into one place so users can spend less time sorting through unrelated opportunities.",
        "question": "How can a lightweight application make grant discovery and review faster without removing human decision-making?",
        "contribution": "I am designing the search workflow, organizing grant fields, building the Flask interface, and testing ways to filter results by eligibility, topic, deadline, and organizational need.",
        "impact": "The tool is intended to reduce repetitive searching and give teams a clearer starting point for deciding which opportunities deserve a closer review.",
        "tools": ["Flask", "Python", "Search", "Data Organization", "UI/UX"],
    },
    "mapbook-automation": {
        "title": "Mapbook Automation",
        "status": "Ongoing",
        "summary": "Repeatable workflows for producing consistent maps and planning materials as data changes.",
        "overview": "Mapbooks can become time-consuming when each update requires the same manual preparation. This project turns recurring map-production steps into a repeatable workflow while keeping layouts and labels consistent.",
        "question": "How can map production be automated without losing the quality checks needed for useful planning documents?",
        "contribution": "I organize geographic data, build automated processing steps, create consistent layouts, and review the generated maps for missing features, labeling issues, and other quality problems.",
        "impact": "The workflow reduces repetitive work and makes it easier to produce updated planning materials when source data changes.",
        "tools": ["Python", "GIS", "Automation", "Mapping", "Documentation"],
    },
    "internal-request-routing": {
        "title": "Internal Request Routing",
        "status": "In Development",
        "summary": "A simpler way for staff to find the correct process, resource, or team for common requests.",
        "overview": "Internal services can be hard to navigate when guidance is scattered across documents and systems. This project organizes common request types into a clearer path from the user's question to the right next step.",
        "question": "How can an internal tool reduce confusion and route users to the right resource more consistently?",
        "contribution": "I map existing workflows, identify common decision points, organize guidance, and design an interface that asks users only for the information needed to direct their request.",
        "impact": "The concept can reduce misrouted requests, save staff time, and make internal processes easier to understand.",
        "tools": ["Workflow Design", "Application Development", "Process Mapping", "UI/UX"],
    },
    "department-mobile-app": {
        "title": "Department Mobile App Concept",
        "status": "Planning",
        "summary": "A mobile-friendly resource hub for guidance, references, and common workflows.",
        "overview": "This concept explores how frequently used information could be organized for quick access from a phone. The emphasis is on simple navigation, readable content, and features that solve common day-to-day needs.",
        "question": "What information and workflows would be most useful in a secure, mobile-friendly internal resource hub?",
        "contribution": "I am gathering requirements, organizing possible features, sketching user flows, and evaluating how the experience should change across phone and desktop screens.",
        "impact": "The project provides a practical starting point for discussing user needs, technical requirements, and the value of a department-focused mobile experience.",
        "tools": ["Product Design", "Mobile UX", "Requirements Gathering", "Internal Tools"],
    },
    "snowflake-data-integration": {
        "title": "Snowflake Data Integration & Analytics",
        "status": "Ongoing",
        "summary": "Reliable data workflows that support reporting, analysis, and system integration.",
        "overview": "This work connects cloud data with downstream reporting and business processes. The focus is not only moving records between systems, but also preserving data types, handling missing values, validating results, and documenting how each field should be used.",
        "question": "How can data move between systems accurately and repeatedly while remaining useful to both technical and operational teams?",
        "contribution": "I write SQL and Python workflows, map fields between source and destination structures, apply validation rules, investigate errors, and compare outputs against business requirements.",
        "impact": "These workflows reduce manual preparation, improve consistency, and give teams more confidence that the information used in reports and other processes matches the source.",
        "tools": ["Snowflake", "SQL", "Python", "Pandas", "Data Validation", "Data Integration"],
    },
}


def get_db():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                excerpt TEXT NOT NULL,
                body TEXT NOT NULL,
                published INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


def validate_csrf():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    if not expected or not secrets.compare_digest(submitted, expected):
        abort(400)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("blog_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def valid_admin_password(password):
    password_hash = os.getenv("BLOG_PASSWORD_HASH")
    plain_password = os.getenv("BLOG_ADMIN_PASSWORD")
    if password_hash:
        return check_password_hash(password_hash, password)
    if plain_password:
        return secrets.compare_digest(password, plain_password)
    return False


def slugify(value):
    safe = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in safe.split("-") if part)[:80]


@app.before_request
def ensure_database():
    init_db()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/projects")
def projects():
    return render_template("projects.html")


@app.route("/current-projects")
def current_projects():
    return render_template("current_projects.html")


@app.route("/current-projects/<slug>")
def current_project_detail(slug):
    project = CURRENT_PROJECTS.get(slug)
    if project is None:
        abort(404)
    return render_template("current_project_detail.html", project=project)


@app.route("/research")
def research():
    return render_template("research.html")


@app.route("/articles")
@app.route("/press")
def articles():
    return render_template("articles.html")


@app.route("/resume")
def resume():
    return render_template("resume.html")


@app.route("/blog")
def blog():
    with get_db() as connection:
        posts = connection.execute(
            "SELECT * FROM posts WHERE published = 1 ORDER BY created_at DESC"
        ).fetchall()
    return render_template("blog.html", posts=posts)


@app.route("/blog/<slug>")
def blog_post(slug):
    with get_db() as connection:
        post = connection.execute(
            "SELECT * FROM posts WHERE slug = ? AND published = 1", (slug,)
        ).fetchone()
    if post is None:
        abort(404)
    return render_template("blog_post.html", post=post)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        validate_csrf()
        if valid_admin_password(request.form.get("password", "")):
            session.clear()
            session["blog_admin"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("admin_posts"))
        flash("That password was not accepted.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    validate_csrf()
    session.clear()
    return redirect(url_for("blog"))


@app.route("/admin/posts")
@admin_required
def admin_posts():
    with get_db() as connection:
        posts = connection.execute("SELECT * FROM posts ORDER BY created_at DESC").fetchall()
    return render_template("admin_posts.html", posts=posts)


@app.route("/admin/posts/new", methods=["GET", "POST"])
@admin_required
def admin_post_new():
    if request.method == "POST":
        validate_csrf()
        now = datetime.now(timezone.utc).isoformat()
        title = request.form["title"].strip()
        slug = slugify(request.form.get("slug") or title)
        with get_db() as connection:
            connection.execute(
                "INSERT INTO posts (title, slug, excerpt, body, published, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, slug, request.form["excerpt"].strip(), request.form["body"].strip(), 1 if request.form.get("published") else 0, now, now),
            )
        flash("Post created.", "success")
        return redirect(url_for("admin_posts"))
    return render_template("admin_post_form.html", post=None)


@app.route("/admin/posts/<int:post_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_post_edit(post_id):
    with get_db() as connection:
        post = connection.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post is None:
            abort(404)
        if request.method == "POST":
            validate_csrf()
            title = request.form["title"].strip()
            connection.execute(
                "UPDATE posts SET title = ?, slug = ?, excerpt = ?, body = ?, published = ?, updated_at = ? WHERE id = ?",
                (title, slugify(request.form.get("slug") or title), request.form["excerpt"].strip(), request.form["body"].strip(), 1 if request.form.get("published") else 0, datetime.now(timezone.utc).isoformat(), post_id),
            )
            flash("Post updated.", "success")
            return redirect(url_for("admin_posts"))
    return render_template("admin_post_form.html", post=post)


@app.route("/admin/posts/<int:post_id>/delete", methods=["POST"])
@admin_required
def admin_post_delete(post_id):
    validate_csrf()
    with get_db() as connection:
        connection.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    flash("Post deleted.", "success")
    return redirect(url_for("admin_posts"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        validate_csrf()
        if not app.config.get("MAIL_USERNAME") or not app.config.get("MAIL_PASSWORD"):
            flash("Email delivery is being configured. Please use the email link instead.", "error")
            return redirect(url_for("contact"))
        message = Message(
            f"Portfolio message from {request.form['name']}",
            recipients=[os.getenv("CONTACT_RECIPIENT", "kylehampton949@gmail.com")],
        )
        message.body = f"From: {request.form['name']} ({request.form['email']})\n\n{request.form['message']}"
        mail.send(message)
        flash("Thanks. Your message was sent.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
