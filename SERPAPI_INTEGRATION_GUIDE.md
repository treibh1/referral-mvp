# SerpAPI Location Enrichment Integration Guide

## Overview

The SerpAPI integration enhances the referral matching system by automatically finding candidate locations using Google search results. This improves location-based matching and provides more accurate candidate recommendations.

## Features

- **Automatic Location Detection**: Uses SerpAPI to search for candidate locations based on name and company
- **Location-Based Scoring**: Calculates location match scores between candidates and job locations
- **Rate Limiting**: Respects API rate limits with built-in delays
- **Fallback Handling**: Gracefully handles cases where location data is unavailable
- **Web Interface Integration**: Seamlessly integrated into the Flask web application

## How It Works

### 1. Location Search Process

When location enrichment is enabled:

1. **Query Construction**: Creates search queries like "John Doe Google" or "Jane Smith Microsoft"
2. **SerpAPI Request**: Sends requests to SerpAPI's Google search endpoint
3. **Response Parsing**: Extracts location information from search results using multiple methods:
   - Rich snippet extensions (most reliable)
   - Snippet text pattern matching
   - Title text analysis
4. **Location Validation**: Validates extracted locations using pattern matching

### 2. Location Scoring

The system calculates location match scores (0.0 to 1.0) based on:

- **Exact Match** (1.0): "London, UK" vs "London, UK"
- **Contains Match** (0.8): "Greater London Area" vs "London, UK"
- **Same City/Region** (0.6): "Brighton, UK" vs "London, UK"
- **Same Country/State** (0.3-0.4): "New York, NY" vs "Texas, United States"
- **No Match** (0.0): "London, UK" vs "Tokyo, Japan"

### 3. Integration Points

- **Unified Matcher**: Location scores are added to the overall candidate scoring
- **Web API**: New parameters for job location and enrichment toggle
- **Frontend**: UI controls for enabling/disabling location enrichment

## Setup Instructions

### 1. Get SerpAPI Key

1. Visit [SerpAPI](https://serpapi.com/)
2. Sign up for a free account
3. Get your API key from the dashboard
4. Free tier includes 100 searches per month

### 2. Set Environment Variable

**Windows:**
```cmd
set SERPAPI_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export SERPAPI_KEY=your_api_key_here
```

**Permanent Setup (Windows):**
```cmd
setx SERPAPI_KEY "your_api_key_here"
```

**Permanent Setup (Linux/Mac):**
```bash
echo 'export SERPAPI_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Test the Integration

Run the test script to verify everything is working:

```bash
python test_serpapi_integration.py
```

## Usage

### Web Interface

1. **Start the Flask app:**
   ```bash
   python app.py
   ```

2. **Open the web interface:**
   - Navigate to http://localhost:5000
   - Enter a job description
   - Add job location (e.g., "London, UK")
   - Check "Enable Location Enrichment (SerpAPI)"
   - Click "Find Candidates"

3. **View Results:**
   - Candidates will show location information when found
   - Location scores are included in the score breakdown
   - Total scores are adjusted based on location matching

### API Usage

```python
from referral_api import ReferralAPI

api = ReferralAPI()

result = api.match_job(
    job_description="Senior Software Engineer at Synthesia in London, UK",
    top_n=10,
    preferred_companies=['Synthesia'],
    preferred_industries=['ai'],
    job_location='London, UK',
    enable_location_enrichment=True,
    serpapi_key='your_api_key_here'
)
```

### Direct Location Enricher Usage

```python
from location_enricher import LocationEnricher

enricher = LocationEnricher('your_api_key_here')

# Search for a specific contact's location
location = enricher.search_contact_location('John Doe', 'Google')
print(f"Location: {location}")

# Enrich multiple candidates
candidates = [
    {'First Name': 'John', 'Last Name': 'Doe', 'Company': 'Google'},
    {'First Name': 'Jane', 'Last Name': 'Smith', 'Company': 'Microsoft'}
]

enriched = enricher.enrich_top_candidates(candidates, max_candidates=20)

# Calculate location match score
score = enricher.calculate_location_score('London, UK', 'Greater London Area')
print(f"Location match score: {score}")
```

## Configuration

### Rate Limiting

The system includes built-in rate limiting to respect SerpAPI's limits:

```python
# In location_enricher.py
time.sleep(1)  # 1 second delay between requests
```

### Search Parameters

Customize search behavior in `location_enricher.py`:

```python
params = {
    'engine': 'google',
    'q': query,
    'api_key': self.serpapi_key,
    'num': 1,  # Number of results to fetch
    'gl': 'us',  # Geographic location for results
    'hl': 'en'   # Language
}
```

### Location Patterns

Add custom location extraction patterns:

```python
self.location_patterns = [
    r"Location:\s*([^·\n]+)",
    r"Based in\s*([^·\n]+)",
    r"Located in\s*([^·\n]+)",
    r"from\s*([^·\n]+)",
    r"in\s*([^·\n]+?)(?:\s*·|\s*$)",
    # Add your custom patterns here
]
```

## Testing

### Run All Tests

```bash
# Test location enricher logic (no API calls)
python test_serpapi_integration.py

# Test web integration
python test_web_integration.py

# Test location enrichment specifically
python test_location_enrichment.py
```

### Test Results

The tests will show:

- ✅ Location scoring logic working
- ✅ Response parsing working
- ✅ Unified matcher integration working
- ✅ Real SerpAPI testing (if key available)

## Cost Management

### SerpAPI Pricing

- **Free Tier**: 100 searches/month
- **Paid Plans**: Starting at $50/month for 5,000 searches
- **Pay-as-you-go**: $0.05 per search

### Optimization Tips

1. **Limit Candidates**: Only enrich top candidates (default: 20)
2. **Cache Results**: Store location data to avoid repeated searches
3. **Batch Processing**: Process multiple candidates in one session
4. **Selective Enrichment**: Only enable for high-priority searches

### Monitoring Usage

Track your SerpAPI usage:

```python
# Add to your code to monitor API calls
import time

class LocationEnricher:
    def __init__(self, serpapi_key: str):
        self.api_calls = 0
        self.last_call_time = 0
    
    def search_contact_location(self, full_name: str, company: str):
        self.api_calls += 1
        print(f"API call #{self.api_calls} for {full_name}")
        # ... rest of the method
```

## Troubleshooting

### Common Issues

1. **No SerpAPI Key Found**
   - Ensure environment variable is set correctly
   - Restart your terminal/IDE after setting the variable

2. **API Rate Limits**
   - The system includes automatic delays
   - Reduce the number of candidates being enriched

3. **No Location Found**
   - Some candidates may not have public location information
   - Try different search variations
   - Check if the candidate has a public profile

4. **Incorrect Locations**
   - Review the location patterns in `location_enricher.py`
   - Add custom patterns for your specific use case

### Debug Mode

Enable debug output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed API requests and responses
```

## Performance Considerations

### Processing Time

- **Without SerpAPI**: ~1-2 seconds for 10 candidates
- **With SerpAPI**: ~10-20 seconds for 10 candidates (due to rate limiting)
- **Large Datasets**: Consider processing in batches

### Memory Usage

- Location data is stored in memory during processing
- No persistent storage of location data (for privacy)
- Consider implementing a cache for repeated searches

## Privacy and Compliance

### Data Handling

- Only searches publicly available information
- No personal data is stored permanently
- Location data is not saved to the database
- Respects rate limits and terms of service

### GDPR Compliance

- Location enrichment uses publicly available data only
- No personal data is collected or stored
- Users can disable location enrichment
- All processing is done in real-time

## Future Enhancements

### Planned Features

1. **Location Caching**: Store location data to reduce API calls
2. **Multiple Search Engines**: Support for Bing, DuckDuckGo
3. **Geographic Clustering**: Group candidates by region
4. **Travel Time Calculation**: Calculate commute times
5. **Remote Work Detection**: Identify remote-friendly candidates

### Customization Options

1. **Custom Location Patterns**: Add industry-specific patterns
2. **Geographic Preferences**: Set preferred regions
3. **Company-Specific Logic**: Custom rules for specific companies
4. **Integration APIs**: Connect with other location services

## Support

### Getting Help

1. **Check the logs**: Look for error messages in the console
2. **Test the API**: Use the test scripts to isolate issues
3. **Verify setup**: Ensure environment variables are set correctly
4. **Check SerpAPI status**: Visit SerpAPI's status page

### Resources

- [SerpAPI Documentation](https://serpapi.com/docs)
- [Location Enricher Source Code](location_enricher.py)
- [Test Scripts](test_*.py)
- [Web Integration](app.py)

---

**Note**: This integration is designed to enhance the referral matching system while respecting privacy and API limits. Always test thoroughly before using in production environments.



