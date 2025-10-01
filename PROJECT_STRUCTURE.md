# 📁 Project Structure

## Core Scripts (Run on Render)
```
zerobounce_validator.py          - Email validation pipeline
hubspot_duplicate_checker.py     - Duplicate checking pipeline  
parse_scrap_data.py              - Scrap data parsing pipeline
```

## Configuration
```
config.py                        - Local config (not in git)
config_example.py                - Template for config.py
render.yaml                      - Render deployment blueprint
requirements.txt                 - Python dependencies
.gitignore                       - Git ignore rules
```

## Directories

### 📚 documentation/
```
DEPLOYMENT.md                    - Full deployment guide
RENDER_SETUP_GUIDE.md           - Detailed Render setup
RENDER_QUICK_START.md           - 5-minute setup guide
RENDER_DEPLOYMENT_SUMMARY.md    - Deployment summary
READY_FOR_DEPLOYMENT.md         - Deployment checklist
SCRAP_DATA_PARSING.md           - Parser documentation
RECORD_FETCHING_REQUIREMENTS.md - Fetching logic docs
```

### 🗄️ sql/
```
add_hubspot_check_2_completed_field.sql  - HubSpot tracking field
add_parsing_fields.sql                   - Parsing fields migration
create_parsing_index.sql                 - Parsing performance index
monitoring_queries.sql                   - Progress monitoring queries
```

### 📦 archive/
```
*.log files                      - Old log files
*.csv files                      - Merged CSV data
*.json files                     - Old reports
```

### 🔧 venv/
```
Python virtual environment (not in git)
```

---

## What You Need to Know

### Production Files (On Render):
- ✅ `zerobounce_validator.py`
- ✅ `hubspot_duplicate_checker.py`
- ✅ `parse_scrap_data.py`
- ✅ `requirements.txt`
- ✅ `render.yaml`

### Setup Files:
- 📋 `documentation/` - Read these for setup
- 🗄️ `sql/` - Run these in Supabase
- 🔧 `config_example.py` - Template for local dev

### Not Needed for Deployment:
- 📦 `archive/` - Old data
- 🔧 `venv/` - Local only
- 📝 `config.py` - Local only (use env vars on Render)

---

## Quick Navigation

**Setting up Render?** → `documentation/RENDER_QUICK_START.md`
**Need environment variables?** → See above in chat
**Want to monitor progress?** → `sql/monitoring_queries.sql`
**Understanding the workflow?** → `documentation/DEPLOYMENT.md`

---

Clean and organized! 🎯
