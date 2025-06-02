import matplotlib
matplotlib.use('Agg')

import warnings
from pytrends.request import TrendReq
from fake_useragent import UserAgent
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import time
from flask import Flask, request, render_template, redirect, url_for, jsonify # Added jsonify
from flask_cors import CORS
import os
from pytrends.exceptions import TooManyRequestsError
import random
import json # Moved import json to top level

# Removed unused imports: argparse, requests, sys

# Suppress FutureWarnings related to fillna downcasting behavior
# This must be after `import warnings`
warnings.simplefilter(action='ignore', category=FutureWarning)

# Initialize Flask app and enable CORS
app = Flask(__name__)
CORS(app)

# Optional: Configure a proxy for Google Trends requests
# Set the HTTP_PROXY and HTTPS_PROXY environment variables if you want to use a proxy.
# For example:
# HTTP_PROXY="http://your_proxy_address:port"
# HTTPS_PROXY="https://your_proxy_address:port"
# pytrends will use these proxies for its requests.

# Define a custom TrendReq class to handle retries ourselves
ua = UserAgent()  # Added

def get_pytrends_instance(proxy_arg=None):  # Renamed for clarity
    """
    Create a PyTrends instance with compatibility for different versions of requests.
    Allows specifying a proxy directly or via environment variables.
    """
    # Create a randomized user agent to avoid detection
    user_agent = ua.random  # Changed
    
    requests_args = {'headers': {'User-Agent': user_agent}}
    
    proxies_to_use = proxy_arg  # Prioritize arg
    
    if not proxies_to_use:  # Fallback to env vars
        env_http_proxy = os.environ.get('HTTP_PROXY')
        env_https_proxy = os.environ.get('HTTPS_PROXY')
        
        if env_http_proxy or env_https_proxy:
            proxies_to_use = {}
            if env_http_proxy:
                proxies_to_use['http'] = env_http_proxy
            if env_https_proxy:
                proxies_to_use['https'] = env_https_proxy
                
    if proxies_to_use:
        requests_args['proxies'] = proxies_to_use
    
    # Initialize pytrends with basic settings, no retries (we'll handle that ourselves)
    return TrendReq(
        hl='en-US', 
        tz=360,
        timeout=(10, 25),  # (connect, read) timeouts
        requests_args=requests_args  # Updated
    )

# Core function to fetch trends data
def fetch_trends_data(keywords, timeframe='today 12-m', max_retries=3, initial_delay=5):
    """
    Fetches Google Trends data using pytrends, handles retries, and returns a pandas DataFrame.
    """
    retry_count = 0
    retry_delay = initial_delay

    while retry_count < max_retries:
        try:
            pytrends = get_pytrends_instance()
            time.sleep(retry_delay)  # Initial or subsequent delay

            pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo='', gprop='')
            trends_data_df = pytrends.interest_over_time()

            if trends_data_df.empty:
                return None  # Or raise an error, TBD by how compare_google_trends uses it

            trends_data_df = trends_data_df.drop(labels=['isPartial'], axis='columns', errors='ignore')
            return trends_data_df

        except TooManyRequestsError as e:
            retry_count += 1
            if retry_count < max_retries:
                jitter = random.uniform(0.5, 1.5)
                retry_delay = min(retry_delay * 2 * jitter, 120)
                print(f"Rate limit exceeded. Retrying in {retry_delay:.1f} seconds... "
                      f"(Attempt {retry_count} of {max_retries})")
                time.sleep(retry_delay)
            else:
                error_message = (
                    f"Failed to fetch Google Trends data after {max_retries} attempts. "
                    "This might be due to Google's rate limiting or network issues. "
                    "If this problem persists, consider using a dedicated proxy service. "
                    "You can configure this in the application if you have proxy access."
                )
                raise Exception(error_message) # Raise to be caught by calling route
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                jitter = random.uniform(0.5, 1.5)
                retry_delay = min(retry_delay * 2 * jitter, 60)
                print(f"Error occurred: {str(e)}. Retrying in {retry_delay:.1f} seconds... "
                      f"(Attempt {retry_count} of {max_retries})")
                time.sleep(retry_delay)
            else:
                error_message = (
                    f"An error occurred while fetching Google Trends data after {max_retries} "
                    f"attempts: {str(e)}. If this problem persists, ensure your network is "
                    "stable or consider using a dedicated proxy service."
                )
                raise Exception(error_message) # Raise to be caught by calling route
    return None # Should be unreachable if retries exhausted and exception raised

# Function to generate plot from trends data (used by /compare)
def compare_google_trends(keywords, timeframe='today 12-m', max_retries=3, initial_delay=5):
    """
    Fetches Google Trends data using fetch_trends_data and then plots it, saving an image.
    Returns the plot filename or None.
    """
    trends_data = fetch_trends_data(keywords, timeframe, max_retries, initial_delay)

    if trends_data is None or trends_data.empty:
        return None

    try:
        # Create the figure and axis
        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot each keyword with a label and different colors
        # Extended to 5 colors for up to 5 keywords
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'] 
        for i, keyword in enumerate(keywords):
            ax.plot(trends_data.index, trends_data[keyword], label=keyword, linewidth=2, color=colors[i % len(colors)])

        # Set title and labels
        ax.set_title('Google Trends Comparison', fontsize=16, weight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Interest Over Time', fontsize=12)

        # Format x-axis date ticks based on the timeframe
        if 'today 12-m' in timeframe or 'today 5-y' in timeframe:
            # For 12-month or longer periods, use monthly ticks
            ax.xaxis.set_major_locator(mdates.MonthLocator())  # Set locator to months
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))  # Format as 'Jan 2023'
        else:
            # For shorter timeframes, keep daily or weekly ticks
            if 'today 1-m' in timeframe:
                ax.xaxis.set_major_locator(mdates.WeekdayLocator())  # Weekly ticks for shorter periods
            else:
                ax.xaxis.set_major_locator(mdates.AutoLocator())  # Auto determine appropriate tick spacing
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))  # Show date format as Year-Month-Day

        # Rotate the x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')

        # Add a grid for better readability
        ax.grid(True, which='both', linestyle='--', linewidth=0.7)

        # Add a legend to identify the keywords
        ax.legend(title="Keywords", loc='upper right', fontsize=10)

        # Adjust layout for better spacing
        plt.tight_layout()

        # Save the plot to an image file
        plot_filename = "static/google_trends_comparison.png"
        plt.savefig(plot_filename)
        plt.close()

        return plot_filename
    except Exception as e:
        # This will catch errors from plotting if any, or if trends_data was problematic
        # The actual data fetching errors are raised by fetch_trends_data and caught by the route
        print(f"Error during plotting: {str(e)}")
        raise Exception(f"An error occurred during plot generation: {str(e)}")


# Route for the web interface (serves HTML form)
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle form submission and show the comparison
@app.route('/compare', methods=['POST'])
def compare():
    try:
        # Get the form data
        keyword1 = request.form.get('keyword1')
        keyword2 = request.form.get('keyword2')
        keyword3 = request.form.get('keyword3')
        keyword4 = request.form.get('keyword4')  # New
        keyword5 = request.form.get('keyword5')  # New
        timeframe = request.form.get('timeframe', 'today 12-m')

        if not keyword1 or not keyword2:
            return render_template('error.html', message="Please provide at least two keywords for comparison.")

        # Prepare the keywords list
        keywords = [keyword1, keyword2]
        if keyword3:
            keywords.append(keyword3)
        if keyword4:  # New
            keywords.append(keyword4)
        if keyword5:  # New
            keywords.append(keyword5)

        # Generate the comparison plot
        plot_filename = compare_google_trends(keywords, timeframe)
        if not plot_filename:
            return render_template('error.html', message="No data available for the given keywords.")

        # Redirect to the display page
        return redirect(url_for('display_image'))

    except Exception as e:
        return render_template('error.html', message=str(e))

# Route to display the generated image
@app.route('/image')
def display_image():
    return render_template('image.html')

# New API route for JSON output
@app.route('/api/compare', methods=['POST'])
def api_compare_trends():
    try:
        # Use silent=True to prevent Werkzeug from raising BadRequest for non-JSON,
        # allowing custom handling below.
        payload = request.get_json(silent=True) 
        if payload is None: # Handles both non-JSON and actual JSON 'null'
            return jsonify({"error": "Invalid JSON payload or non-JSON request"}), 400

        keywords = payload.get('keywords')
        timeframe = payload.get('timeframe', 'today 12-m')

        if not keywords or not isinstance(keywords, list) or len(keywords) < 2:
            return jsonify({"error": "Please provide at least two keywords as a list."}), 400
        if len(keywords) > 5:
            return jsonify({"error": "Cannot compare more than five keywords."}), 400
        
        # Ensure all keywords are strings
        if not all(isinstance(kw, str) for kw in keywords):
            return jsonify({"error": "All keywords must be strings."}), 400

        trends_df = fetch_trends_data(keywords, timeframe)

        if trends_df is None or trends_df.empty:
            return jsonify({"error": "No data available for the given keywords or timeframe."}), 404
        
        # Convert DataFrame to JSON, using 'table' orientation for schema + data
        json_data = trends_df.to_json(orient='table', date_format='iso')
        
        # jsonify will correctly set the Content-Type header to application/json
        return jsonify(json.loads(json_data)) # Parse json_data string to dict for jsonify

    except Exception as e:
        # Catch exceptions raised by fetch_trends_data or other issues
        # Check if the exception message indicates a rate limit error specifically
        if "Failed to fetch Google Trends data after" in str(e) and "rate limiting" in str(e):
            return jsonify({"error": str(e)}), 429  # Too Many Requests
        # Log other unexpected errors for debugging
        print(f"Unexpected error in /api/compare: {str(e)}") # Add logging
        return jsonify({"error": "An unexpected server error occurred."}), 500

# Run the Flask server
if __name__ == '__main__':
    # import json # Removed from here
    app.run(host='0.0.0.0', port=5000, debug=True)
