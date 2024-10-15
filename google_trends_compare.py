import argparse
import warnings
from pytrends.request import TrendReq
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import time

# Suppress FutureWarnings related to fillna downcasting behavior
warnings.simplefilter(action='ignore', category=FutureWarning)

# Use 'Agg' backend for headless environments
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving plots as images

# Function to compare Google Trends of 2 or 3 keywords
def compare_google_trends(keywords, timeframe='today 12-m'):
    # Initialize pytrends
    pytrends = TrendReq(hl='en-US', tz=360)

    # Add a small delay to prevent rate limiting
    time.sleep(5)

    # Build the payload for the keywords
    pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo='', gprop='')

    # Retrieve interest over time
    trends_data = pytrends.interest_over_time()

    # Debugging output: Print the first few rows of data
    print("Trends data fetched:")
    print(trends_data.head())

    # Check if any data is available
    if trends_data.empty:
        print("No data found for the given keywords.")
        return

    # Drop the 'isPartial' column if it exists
    trends_data = trends_data.drop(labels=['isPartial'], axis='columns', errors='ignore')

    # Debugging: Print the columns and date range
    print(f"Columns in trends data: {trends_data.columns}")
    print(f"Data range: {trends_data.index.min()} to {trends_data.index.max()}")

    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot each keyword with a label and different colors
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Color list for each line
    for i, keyword in enumerate(keywords):
        ax.plot(trends_data.index, trends_data[keyword], label=keyword, linewidth=2, color=colors[i % len(colors)])

    # Set title and labels
    ax.set_title('Google Trends Comparison', fontsize=16, weight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Interest Over Time', fontsize=12)

    # Format x-axis for dates (daily ticks)
    ax.xaxis.set_major_locator(mdates.DayLocator())  # Set locator to days
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))  # Show date format as Year-Month-Day

    # Rotate the x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')

    # Add a grid for better readability
    ax.grid(True, which='both', linestyle='--', linewidth=0.7)

    # Add a legend to identify the keywords
    ax.legend(title="Keywords", loc='upper right', fontsize=10)

    # Adjust layout for better spacing
    plt.tight_layout()

    # Save the plot to an image file (since no GUI is available)
    plt.savefig("google_trends_comparison.png")
    print("Plot saved as 'google_trends_comparison.png'.")

# Main function to handle command-line arguments
def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Compare Google Trends for 2 or 3 keywords.')
    
    # Add two required positional arguments for the first two keywords
    parser.add_argument('keyword1', type=str, help='First keyword to compare')
    parser.add_argument('keyword2', type=str, help='Second keyword to compare')

    # Add optional third argument for the third keyword
    parser.add_argument('--keyword3', type=str, help='Third optional keyword', default=None)

    # Add optional argument for the date range (timeframe)
    parser.add_argument('--timeframe', type=str, help='Timeframe for Google Trends (e.g., "today 12-m", "today 5-y", "2004-present", "YYYY-MM-DD YYYY-MM-DD")', default='today 12-m')

    # Parse the arguments
    args = parser.parse_args()

    # Prepare the keywords list
    keywords = [args.keyword1, args.keyword2]

    # Add the third keyword if provided
    if args.keyword3:
        keywords.append(args.keyword3)

    # Compare the Google Trends for the provided keywords and timeframe
    compare_google_trends(keywords, timeframe=args.timeframe)

# Entry point of the script
if __name__ == "__main__":
    main()
