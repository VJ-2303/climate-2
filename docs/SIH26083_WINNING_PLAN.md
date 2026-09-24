# SIH26083: "Extreme Heatwave Early Warning" Final Winning Plan

This document outlines the final architectural alignment of the existing HeatViz (Kibera) project to perfectly fulfill the Ministry of Earth Sciences (MoES) **SIH26083** problem statement for the Smart India Hackathon.

## 1. The Core Objective
Shift from "What the weather will be" to "What the weather will do." We are transforming our spatial microclimate mapping tool into a **3-5 day predictive health risk early warning system**, using Kibera as the high-resolution proof-of-concept.

## 2. Advanced Physiological Metric: WBGT
- **Requirement:** SIH26083 demands advanced metrics like WBGT, UTCI, or HI instead of just ambient temperature.
- **Implementation:** We will fetch a real 3-5 day forecast (Temperature, Relative Humidity, Wind Speed, Solar Radiation) via the Open-Meteo API. We will use these to calculate a baseline **Wet-Bulb Globe Temperature (WBGT)**, the global standard for heat stress.

## 3. Hyper-Local Downscaling (The ML Innovation)
- **Requirement:** GIS-mapped, hyper-local alerts (Zone/Ward level).
- **Implementation:** We retain our core innovation—the XGBoost + Graph Attention Network (GAT) pipeline. Instead of just mapping current LST, we apply the 50m spatial `temp_anomaly_celsius` (derived from our AI model) to the forecasted macro-WBGT. This yields a **Hyper-local 50m WBGT forecast** for every block in the settlement.

## 4. Explainable AI (SHAP)
- **Requirement:** Actionable intelligence and understanding of root causes.
- **Implementation:** We will integrate **SHAP** (SHapley Additive exPlanations) into the XGBoost spatial model. This provides mathematical explainability for *why* a specific block is hotter than the baseline (e.g., "+1.5°C due to dense metal roofs (NDBI), +0.8°C due to lack of trees (NDVI)").

## 5. Predictive Health Risk Engine
- **Requirement:** Predict mortality and hospitalization risks 3-5 days in advance.
- **Implementation:** Since we lack historical mortality data, we will use a **Deterministic Rules Engine** rather than ML for the health outcome. The engine will combine the 3-5 day hyper-local WBGT forecast with our spatial vulnerability layers (Population Density, Social Sensitivity, Cooling Deficit) to classify blocks into Health Risk Tiers (e.g., Elevated, High, Dangerous Hospitalization Risk).

## 6. Role-Based Dashboards & Automated Advisories
- **Requirement:** Dashboards for authorities to deploy interventions, and automated public health advisories.
- **Implementation:** 
  - **Officer Dashboard (`officer.html`):** A command-and-control GIS map showing 3-5 day risk forecasts, filtering, and aggregate zone analytics.
  - **Public Dashboard (`public.html`):** A simplified, mobile-friendly interface for citizens.
  - **Automated Advisories:** We will use the deterministic rules engine + SHAP outputs to populate **dynamic text templates**. Example: *"Alert for Sector KIB-0234: Dangerous WBGT of 34°C expected Thursday. High risk due to dense metal roofs and no shade. Drink water and avoid outdoor labor."*
