import logging
import time
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Optional, Tuple, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DaylightResult:
    sunrise: str
    sunset: str
    day_length: str
    date_obj: date

class DaylightData:
    def __init__(self, lat: float = 42.3601, lng: float = -71.0589):
        self.lat = lat
        self.lng = lng
        self.session = self._setup_session()
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _setup_session(self) -> requests.Session:
        """Configure requests session with retries for better robustness"""
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session

    def get_day_data(self, target_date: date) -> Optional[DaylightResult]:
        """Fetch sunrise/sunset data for a specific date with caching and error handling"""
        date_str = target_date.strftime('%Y-%m-%d')
        
        if date_str in self._cache:
            data = self._cache[date_str]
            return DaylightResult(**data, date_obj=target_date)

        url = f"https://api.sunrisesunset.io/json?lat={self.lat}&lng={self.lng}&date={date_str}"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            results = response.json().get('results')
            
            if results:
                self._cache[date_str] = results
                return DaylightResult(
                    sunrise=results['sunrise'],
                    sunset=results['sunset'],
                    day_length=results['day_length'],
                    date_obj=target_date
                )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch data for {date_str}: {e}")
        
        return None
            
    def minutes_of_daylight(self, day_length: str) -> int:
        """Convert HH:MM:SS format to total minutes"""
        try:
            h, m, s = map(int, day_length.split(':'))
            return h * 60 + m + (1 if s >= 30 else 0)
        except (ValueError, AttributeError):
            logger.warning(f"Malformed day_length string: {day_length}")
            return 0
        
    def find_similar_day(self) -> Tuple[Optional[DaylightResult], Optional[DaylightResult]]:
        """Find a day in past 3-9 months with similar daylight length"""
        today = datetime.now().date()
        today_data = self.get_day_data(today)
        
        if not today_data:
            return None, None
            
        today_minutes = self.minutes_of_daylight(today_data.day_length)
        logger.info(f"Today's daylight: {today_minutes} minutes")
        
        best_match: Optional[DaylightResult] = None
        smallest_diff = float('inf')
        
        # Search past 90-270 days
        logger.info("Searching for a similar day in the past 3-9 months...")
        for days_ago in range(90, 271):
            past_date = today - timedelta(days=days_ago)
            past_data = self.get_day_data(past_date)
            
            if not past_data:
                continue
                
            past_minutes = self.minutes_of_daylight(past_data.day_length)
            diff = abs(past_minutes - today_minutes)
            
            if diff < smallest_diff:
                smallest_diff = diff
                best_match = past_data
                
            # Exit early if we find a very close match (within 1 minute)
            if diff <= 1:
                break
        
        if best_match:
            logger.info(f"Found best match from {best_match.date_obj} with {smallest_diff} min difference")
        
        return today_data, best_match

def generate_html(today_data: DaylightResult, similar_data: Optional[DaylightResult]):
    """Generate the comparison HTML report"""
    
    similar_day_html = ""
    if similar_data:
        similar_day_html = f"""
        <div class="data-row">
            <span>Date</span>
            <span>{similar_data.date_obj.strftime('%B %d, %Y')}</span>
        </div>
        <div class="data-row">
            <span>Sunrise</span>
            <span>{similar_data.sunrise}</span>
        </div>
        <div class="data-row">
            <span>Sunset</span>
            <span>{similar_data.sunset}</span>
        </div>
        <div class="data-row">
            <span>Day Length</span>
            <span>{similar_data.day_length}</span>
        </div>
        """
    else:
        similar_day_html = '<p>No date found with similar daylight length in the past 3-9 months.</p>'

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <title>Daylight Comparison for Boston</title>
    <link rel="stylesheet" href="styles.css" type="text/css">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <h1>Daylight Comparison for Boston</h1>
    
    <div class="card">
        <h2>Today's Information ({today_data.date_obj.strftime('%B %d, %Y')})</h2>
        <div class="data-row">
            <span>Sunrise</span>
            <span>{today_data.sunrise}</span>
        </div>
        <div class="data-row">
            <span>Sunset</span>
            <span>{today_data.sunset}</span>
        </div>
        <div class="data-row">
            <span>Day Length</span>
            <span>{today_data.day_length}</span>
        </div>
    </div>
    
    <div class="card {'no-match' if not similar_data else ''}">
        <h2>{'Similar Day' if similar_data else 'No Match Found'}</h2>
        {similar_day_html}
    </div>
</body>
</html>'''

    try:
        with open('index.html', 'w') as f:
            f.write(html_content)
        logger.info("Report generated successfully: index.html")
    except IOError as e:
        logger.error(f"Failed to write HTML report: {e}")

def main():
    daylight = DaylightData()
    today_data, similar_data = daylight.find_similar_day()
    
    if today_data:
        generate_html(today_data, similar_data)
    else:
        logger.error("Could not fetch today's daylight data. Exiting.")

if __name__ == "__main__":
    main()