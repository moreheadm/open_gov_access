# Example Data

This document describes the example data that can be loaded into the database for testing and demonstration purposes.

## Overview

The example data is based on a real San Francisco Board of Supervisors legislation:

**File #250804**: Amended and Restated Conditional Property Exchange Agreement - EQX Jackson SQ Holdco LLC - 530 Sansome Street and 447 Battery Street

Source: https://sfgov.legistar.com/LegislationDetail.aspx?ID=7501529&GUID=557EC678-D34A-49CD-AEA0-5E681ADD5806

## What's Included

The example data includes:

### 1. Officials (13 total)
- **Mayor**: Daniel Lurie
- **11 Supervisors** (Districts 1-11):
  - District 1: Connie Chan
  - District 2: Catherine Stefani
  - District 3: Aaron Peskin
  - District 4: Joel Engardio
  - District 5: Dean Preston
  - District 6: Matt Dorsey
  - District 7: Myrna Melgar
  - District 8: Rafael Mandelman
  - District 9: Hillary Ronen
  - District 10: Shamann Walton
  - District 11: Ahsha Safai
- **Additional**: Danny Sauter (co-sponsor)

### 2. Legislation (1 item)
- **File Number**: 250804
- **Type**: Ordinance
- **Status**: Approved
- **Category**: Real Estate
- **Title**: Amended and Restated Conditional Property Exchange Agreement - EQX Jackson SQ Holdco LLC - 530 Sansome Street and 447 Battery Street
- **Sponsors**: Mayor (Daniel Lurie), Danny Sauter (co-sponsor)
- **Metadata**: Includes dates, enactment number, related files, and attachments

### 3. Meetings (5 total)
Legislative history with meetings on:
- 2025-07-29: Regular Meeting - ASSIGNED UNDER 30 DAY RULE
- 2025-09-29: Committee Meeting - RECOMMENDED
- 2025-10-07: Regular Meeting - PASSED, ON FIRST READING
- 2025-10-21: Regular Meeting - FINALLY PASSED
- 2025-10-27: Regular Meeting - APPROVED

### 4. Actions (13 total)
- **2 Sponsor Actions**: Mayor (sponsor), Danny Sauter (co-sponsor)
- **11 Vote Actions**: All 11 supervisors voted on final passage (10/21/2025)
  - 9 YES votes
  - 1 NO vote (Rafael Mandelman)
  - 1 ABSTAIN (Ahsha Safai)
  - Result: 90% approval - PASSED

## Loading Example Data

### Method 1: Initialize Database with Examples

When initializing the database, use the `--with-examples` flag:

```bash
cd backend
uv run python main.py init --with-examples
```

This will:
1. Create all database tables
2. Seed the 12 current SF officials (mayor + 11 supervisors)
3. Load the example legislation with voting data

### Method 2: Run Demo Script

To see the example data without affecting your database, run the demo script:

```bash
cd backend
uv run python demo_example_data.py
```

This creates an in-memory SQLite database and displays:
- Legislation details
- Sponsors
- Legislative history
- Voting record with vote counts
- Database statistics

## Database Schema

The example data demonstrates the following relationships:

```
Official (13)
  ├─> Action (sponsor) ──> Legislation (1)
  └─> Action (vote) ──────> Legislation (1)
                              └─> Meeting (5)
```

### Key Tables

1. **officials**: Elected officials (mayor and supervisors)
2. **legislation**: Bills, ordinances, resolutions
3. **meetings**: Board meetings
4. **actions**: Votes and sponsorships linking officials to legislation

## Use Cases

This example data is useful for:

1. **Testing**: Verify API endpoints and database queries
2. **Development**: Test UI components with realistic data
3. **Demonstrations**: Show how the system works with real legislation
4. **Documentation**: Provide examples in API documentation

## Customization

To add more example data, edit the `seed_example_data()` function in `backend/models/database.py`.

The function demonstrates:
- Creating legislation with metadata
- Adding sponsors and co-sponsors
- Creating meetings
- Recording votes with different outcomes (YES, NO, ABSTAIN)
- Calculating vote counts and percentages

## Notes

- Example data is idempotent - running it multiple times won't create duplicates
- The legislation file number (250804) is checked before inserting
- Officials are seeded separately and can be used without example legislation
- All dates and names are based on real SF Board of Supervisors data as of 2025

