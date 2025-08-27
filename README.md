# Referral MVP - Unified Matching System

A robust system for matching job descriptions to potential referral candidates from employee LinkedIn contacts.

## 🎯 Overview

This system addresses the core workflow:
1. **Employees** upload their LinkedIn contacts CSV → contacts get tagged and stored
2. **Recruiters/Hiring Managers** submit job descriptions → system returns top 10 referral candidates

## 🚀 Key Improvements (Addressing Previous Concerns)

### ✅ **Issue 1: Multiple .py Scripts** - RESOLVED
- **Before**: Separate scripts for each job type (`test_software_engineer.py`, `test_csm.py`, etc.)
- **After**: Single `unified_matcher.py` handles ALL job types
- **Benefit**: No more script proliferation, consistent behavior

### ✅ **Issue 2: Dynamic Scoring Scaling** - RESOLVED  
- **Before**: Scoring weights increased from 10 → 50 → 1000 with each test
- **After**: Fixed, consistent scoring weights defined once
- **Benefit**: Predictable results, no more waiting for scoring analysis

## 📁 Core Files

### Main System
- `unified_matcher.py` - **Main matching engine** (replaces all test scripts)
- `referral_api.py` - **API wrapper** for web applications
- `tag_contacts.py` - **Contact tagging system** (unchanged)

### Data Files
- `tagged_contacts2.csv` - Tagged LinkedIn contacts
- `role_enrichment.json` - Skills/platforms by role
- `title_aliases.json` - Job title variations
- `company_industry_tags_usev2.json` - Company industry tags

## 🛠️ Usage

### Quick Test
```bash
python test_unified_system.py
```

### Command Line
```bash
python unified_matcher.py
# Then paste job description when prompted
```

### Programmatic Usage
```python
from unified_matcher import UnifiedReferralMatcher

# Initialize
matcher = UnifiedReferralMatcher()

# Find candidates
candidates = matcher.find_top_candidates(job_description, top_n=10)

# Display results
matcher.display_results(candidates, job_reqs)
```

### API Usage
```python
from referral_api import ReferralAPI

api = ReferralAPI()
result = api.match_job(job_description, top_n=10)
print(result['candidates'])
```

## ⚖️ Scoring System (Fixed & Consistent)

The system uses **pre-defined weights** that never change:

```python
scoring_weights = {
    'skill_match': 3.0,      # Skills are most important
    'platform_match': 2.0,   # Platforms are very important  
    'role_match': 5.0,       # Role matching is critical
    'company_match': 2.0,    # Company matching is good
    'industry_match': 1.0,   # Industry matching is nice to have
    'seniority_bonus': 1.5,  # Seniority alignment bonus
    'exact_role_bonus': 3.0  # Bonus for exact role match
}
```

## 🎯 Matching Criteria

1. **Skills** - Technical skills from job description
2. **Platforms** - Tools and technologies used
3. **Role** - Job title/function matching
4. **Company** - Company name matching
5. **Industry** - Industry tag alignment
6. **Seniority** - Experience level matching

## ⚡ Performance

- **Processing Time**: < 1 minute for 2,400+ contacts
- **Memory Usage**: Efficient pandas operations
- **Scalability**: Linear scaling with contact count

## 🔧 System Architecture

```
Job Description → Extract Requirements → Score All Contacts → Return Top 10
     ↓                    ↓                    ↓                ↓
  Text Analysis    Skills/Platforms    Weighted Scoring    Ranked Results
```

## 📊 Output Format

### Console Output
```
🏆 TOP 10 REFERRAL CANDIDATES
========================================

#1: John Smith
   Position: Senior Software Engineer
   Company: Tech Corp
   Total Score: 15.5
   Breakdown:
     Skills: ['Python', 'React'] (score: 6.0)
     Platforms: ['AWS', 'Docker'] (score: 4.0)
     Role: Software Engineer (score: 5.0)
     Company match: 0.0
     Industry: ['SaaS'] (score: 1.0)
     Seniority bonus: 1.5
```

### CSV Output
- `referral_matches.csv` - Simple format
- `detailed_referral_matches.csv` - Full scoring breakdown

## 🚀 Web Application Integration

The `referral_api.py` provides a clean interface for web apps:

```python
# Flask example
@app.route('/match', methods=['POST'])
def match_job():
    data = request.get_json()
    result = api.match_job(data['job_description'])
    return jsonify(result)
```

## 🔄 Workflow Integration

### For Employees (Contact Upload)
1. Export LinkedIn contacts to CSV
2. Run `tag_contacts.py` to tag and enrich
3. Contacts are ready for matching

### For Recruiters (Job Matching)
1. Submit job description via API or command line
2. System returns top 10 candidates in < 1 minute
3. Results include detailed scoring breakdown

## 🎉 Benefits of Unified System

- ✅ **Single Script** - No more multiple test files
- ✅ **Consistent Scoring** - Fixed weights, predictable results  
- ✅ **Fast Processing** - < 1 minute response time
- ✅ **Detailed Analysis** - Full scoring breakdown
- ✅ **Web Ready** - Clean API interface
- ✅ **Maintainable** - Easy to extend and modify
- ✅ **Scalable** - Handles any job type

## 🔮 Future Enhancements

- Machine learning scoring improvements
- Real-time contact updates
- Advanced filtering options
- Integration with ATS systems
- Candidate outreach automation

## 📝 Requirements

```bash
pip install pandas rapidfuzz
```

## 🧪 Testing

Run the comprehensive test suite:
```bash
python test_unified_system.py
```

This tests both software engineer and CSM job matching to verify system robustness.


