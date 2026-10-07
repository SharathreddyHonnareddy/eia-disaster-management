# EIA-Assist V2

A student-friendly Flask EIA demonstration system.

## What changed

- Removed the repeated 17-factor manual forms.
- Student selects the actual project activities.
- Impacts are generated from activity-specific profiles.
- Mitigation measures are linked to the selected activity.
- Shows inherent risk and residual risk after controls.
- Adds an air-quality demonstration page.
- Supports manual PM2.5/PM10 readings.
- Supports clearly labelled simulated sensor readings for classroom demonstrations.
- Uses CPCB Indian AQI PM breakpoints for the PM-based demonstration calculation.
- Reuses the existing `database.db` and automatically creates the new V2 tables.

## Run

1. Keep `app.py` and your existing `database.db` in the same folder.
2. Install Flask:

   `pip install -r requirements.txt`

3. Run:

   `python app.py`

4. Open:

   `http://127.0.0.1:5000`

## Important

The simulated sensor is only for demonstration. It does not represent actual site air quality.

A full CPCB AQI requires sufficient pollutant data and the appropriate averaging period. The student version therefore labels PM2.5/PM10-only output as a PM-based demonstration index.

The impact scores and mitigation effectiveness values are screening values for an academic prototype, not professional/statutory EIA results.
