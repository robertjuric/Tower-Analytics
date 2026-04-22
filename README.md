# Tower Analytics

Analyze tower battle reports visualize your runs. Analyze changes in your strategy, see the progress of your upgrades, and hopefully gain some insight into what is working or not working for you. 

## Basic Concept
* Battle history files saved as .txt files
* Tags added automatically based on the tier and anything put into `[]` brackets in the filename.
* A basic web interface to sanity check your reports, manage tags, or add a note.

## 🚧 Current State 🚧

This is an early version focused on:

* Basic functionality
* Database structure
* Visualization experimentation

Improvements are currently in the works:

* Prebuilt dashboards
* Automatic Grafana setup
* Improved UI

---

## System Requirements

* **Windows PC**
* **Docker Desktop** (installed and running)

Download: https://www.docker.com/products/docker-desktop/

---

## Quick Start

### 0. Save Your Battle Reports

The first step is to save all of the battle reports from your battle history.

1. Open your battle history.
2. Open a report and click the copy button.
3. Paste the report and save it as a `.txt` file.
* You can set tags via the file name by including the tag name in `[]` brackets.
* Example `BattleReport4-20[tournament].txt`
* The exact filename does not matter.
* When processed, .
* At this point I recommend manually adding `[tournament]` and `[dissonance]` tags via the filename.

---

### 1. Clone the Repository (aka download a copy)

Using GitHub Desktop:

* Click **Code → Download ZIP**
* Choose a local folder

Download the ZIP and extract.

---

### 2. Start the Application

You have two options:

#### Option A (Easiest)

Double-click:

```
start.bat
```

#### Option B (Manual)

Open a terminal in the project folder and run:

```
docker compose up --build
```

---

### 3. Add the Battle Reports

1. Open this folder in File Explorer:

```
tower-pipeline\reports\
```

2. Copy your `.txt` battle report files into this folder

Files will be **automatically processed within a few seconds**

---

### 4. Open the web interface

Go to:

```
http://localhost:8000
```

You should see all of your battle reports along with basic funcationality to add tags or notes. If you see the battle reports here then everything was parsed and added to the database correctly.

---

### 5. Open Grafana

Go to:

```
http://localhost:3000
```

Login:

* **Username:** admin
* **Password:** admin

After logging in the first time Grafana will require you to change the password.

---

## ⚙️ Grafana Setup (One-Time Step)

1. Click **Connections → Data Sources**
2. Click **Add data source**
3. Select **PostgreSQL**

Enter the following:

* **Host:** `db:5432`
* **Database:** `towerdb`
* **User:** `tower`
* **Password:** `towerpass`

Click **Save & Test**

## Known issues and development tips
1. The date and time within the battle reports have no indication of timezone. This isn't a problem for the web interface as it just displays the date. However grafana assumes all date/time entries are UTC time. If you create a dashboard it is likely set to use the Browser timezone. So grafana will adjust the displayed date (UTC-5 for example).  
The Fix: Set all dashboard timezones to UTC to view the actual date/time

2. When including multiple metrics in a panel, some similar metrics might not scale the same. You may need to set some values axis placement to the right to get 2 different scaling in one panel.

3. For the dates use a custom unit to shorten them to MM/DD. The unit would look like custom: time:MM\/DD

4. The numbers are very large when written out fully, use the short unit to get the abbreviations.

## Feedback

If something is confusing or doesn’t work, open an issue or share feedback.

---


