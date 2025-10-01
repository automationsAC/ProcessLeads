# Process Leads from Supabase to Instantly

This repository contains the automation pipeline for processing leads from Supabase through ZeroBounce email validation to Instantly outreach campaigns.

## Overview

The pipeline processes leads in the following stages:
1. **Lead Selection**: Select leads with `humanfit = true` and `added_to_instantly IS NULL`
2. **ZeroBounce Validation**: Validate emails using ZeroBounce API
3. **HubSpot Duplicate Check**: Check for existing contacts in HubSpot
4. **Instantly Integration**: Add valid leads to Instantly campaigns
5. **HubSpot Deal Creation**: Create deals for valid leads and invalid emails

## Features

- **Modular Design**: Each stage is implemented as a separate module
- **Batch Processing**: Processes leads in configurable batches (default: 100)
- **Priority System**: Processes leads by country priority (PL → DE → ES)
- **Status Tracking**: Comprehensive status tracking in Supabase
- **Error Handling**: Robust error handling and logging

## Setup

1. **Clone the repository**:
   ```bash
   git clone git@github.com:automationsAC/process-leads-from-supabase.git
   cd process-leads-from-supabase
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure credentials**:
   ```bash
   cp config_example.py config.py
   # Edit config.py with your actual credentials
   ```

## Configuration

Update `config.py` with your credentials:

```python
# Supabase Configuration
SUPABASE_URL = "your_supabase_url"
SUPABASE_ANON_KEY = "your_supabase_anon_key"

# ZeroBounce Configuration
ZEROBOUNCE_API_KEY = "your_zerobounce_api_key"

# Priority API Configuration
PRIORITY_API_KEY = "your_priority_api_key"
PRIORITY_API_URL = "https://your-app-domain/functions/getCurrentPriorities"
```

## Usage

### ZeroBounce Validation
```bash
python zerobounce_validator.py
```


## Database Schema

The pipeline uses the following Supabase fields:

- `humanfit`: Boolean flag for human-verified leads
- `added_to_instantly`: Boolean flag for leads already in Instantly
- `zerobounce_status`: Validation status ('valid', 'invalid', 'catch-all', 'do_not_mail')
- `zerobounce_sub_status`: Sub-status (e.g., 'role_based', 'spam_trap')
- `zerobounce_validated_at`: Timestamp of validation
- `zerobounce_processed`: Boolean flag for processing status

## Validation Logic

- **Valid**: Proceed to Instantly
- **Role-based**: Treated as valid for outreach
- **Invalid**: Skip (create HubSpot deal for sales)
- **Catch-all**: Treated as invalid

## Logging

All operations are logged to:
- Console output
- `zerobounce_validation.log`
- `instantly_merge.log`

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

Private repository for automationsAC.
