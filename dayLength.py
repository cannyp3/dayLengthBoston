import requests
from datetime import datetime, timedelta

class DaylightData:
    def __init__(self, lat=42.3601, lng=-71.0589):  # Boston coordinates
        self.lat = lat
        self.lng = lng
        
    def get_day_data(self, date):
        """Fetch sunrise/sunset data for a specific date"""
        url = f"https://api.sunrisesunset.io/json?lat={self.lat}&lng={self.lng}&date={date.strftime('%Y-%m-%d')}"
        try:
            response = requests.get(url)
            return response.json()['results']
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
            
    def minutes_of_daylight(self, day_length):
        """Convert HH:MM:SS format to total minutes"""
        h, m, s = map(int, day_length.split(':'))
        return h * 60 + m + (1 if s >= 30 else 0)
        
    def find_similar_day(self):
        """Find a day in past 3-9 months with similar daylight length"""
        today = datetime.now()
        today_data = self.get_day_data(today)
        if not today_data:
            return None, None
            
        today_minutes = self.minutes_of_daylight(today_data['day_length'])
        
        best_match = None
        best_match_data = None
        smallest_diff = float('inf')
        
        # Search past 90-270 days
        for days_ago in range(90, 271):
            past_date = today - timedelta(days=days_ago)
            past_data = self.get_day_data(past_date)
            
            if not past_data:
                continue
                
            past_minutes = self.minutes_of_daylight(past_data['day_length'])
            diff = abs(past_minutes - today_minutes)
            
            if diff <= 10 and diff < smallest_diff:
                smallest_diff = diff
                best_match = past_date
                best_match_data = past_data
        
        return today_data, best_match_data, best_match

def generate_html(today_data, similar_data, similar_date):
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>Daylight Comparison for Boston</title>
    <link rel="stylesheet" href="styles.css" type="text/css">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <h1>Daylight Comparison for Boston</h1>
    
    <div class="card">
        <h2>Today's Information ({datetime.now().strftime('%B %d, %Y')})</h2>
        <div class="data-row">
            <span>Sunrise</span>
            <span>{today_data['sunrise']}</span>
        </div>
        <div class="data-row">
            <span>Sunset</span>
            <span>{today_data['sunset']}</span>
        </div>
        <div class="data-row">
            <span>Day Length</span>
            <span>{today_data['day_length']}</span>
        </div>
    </div>
    
    {'<div class="card">' if similar_date else '<div class="card no-match">'}
        <h2>{'Similar Day' if similar_date else 'No Match Found'}</h2>
        {f"""
        <div class="data-row">
            <span>Date</span>
            <span>{similar_date.strftime('%B %d, %Y')}</span>
        </div>
        <div class="data-row">
            <span>Sunrise</span>
            <span>{similar_data['sunrise']}</span>
        </div>
        <div class="data-row">
            <span>Sunset</span>
            <span>{similar_data['sunset']}</span>
        </div>
        <div class="data-row">
            <span>Day Length</span>
            <span>{similar_data['day_length']}</span>
        </div>
        """ if similar_date else '<p>No date found with similar daylight length in the past 3-9 months.</p>'}
    </div>
</body>
</html>'''

    with open('index.html', 'w') as f:
        f.write(html_content)

def main():
    daylight = DaylightData()
    today_data, similar_data, similar_date = daylight.find_similar_day()
    
    if today_data:
        generate_html(today_data, similar_data, similar_date)
        print("Report generated successfully!")
    else:
        print("Error: Could not fetch daylight data")

if __name__ == "__main__":
    main()
