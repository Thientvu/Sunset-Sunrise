import pandas as pd
from bs4 import BeautifulSoup
import requests
import numpy as np
import re

TIME_AND_DATE_URL = 'https://www.timeanddate.com/sun/' 
YEAR = 2024  
CA_STATE_PARKS_URL = 'https://en.wikipedia.org/wiki/List_of_California_state_parks#List_of_parks'
WIKIPEDIA_URL = 'https://en.wikipedia.org'

"""
Retrieve data from timeanddate.com
"""
#Helper function
#Get html reponses from all the month pages from timeanddate.com
def get_time_date_html_responses(state_park, year):
    # Create a list to store responses for each month
    responses = []
    
    # Set up the parameters for the current month
    params = {'query': state_park}

    # Send a GET request to the website with the search query parameters
    response = requests.get(TIME_AND_DATE_URL, params=params)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Loop through each month (assuming months are represented by numbers 1 to 12)
        for month in range(1, 13):
            # Add ?month=&year= to the URL
            new_url = f'{response.url}?month={month}&year={year}'

            # Send another GET request with the updated URL
            new_response = requests.get(new_url)
            
            # Check if the second request was successful
            if new_response.status_code == 200:
                #Add response to the list
                responses.append(new_response)
            else:
                print(f'Error in the request for {year}-{month}: {response.status_code}')
    else:
        print('Error in the first request:', response.status_code)

    return responses

#Helper function
#Parse html reponses from above and store the data in a pandas df
def parse_and_store_monthly_time_date(state_park, content):
    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')

    # Find the table with the specified id
    table = soup.find('table', {'id': 'as-monthsun'})
    
    try:
        # Extract all the rows
        rows = table.find_all('tr')

        # Extract column headers
        headers1 = [th.text.strip() for th in rows[0].find_all('th')]
        headers = [th.text.strip() for th in rows[1].find_all('th')]

        # Rename Columns
        headers[0] = headers1[0] + ' ' + headers[0]
        headers[1] = headers[1] 
        headers[2] = headers[2]
        headers[3] = headers1[2] + ' (' + headers[3] + ')'
        headers[4] = headers1[2] + ' (' + headers[4] + ')'
        headers[5] = headers1[3] + ' (' + headers[5] + ')'
        headers[6] = headers1[3] + ' (' + headers[6] + ')'
        headers[7] = headers1[4] + ' (' + headers[7] + ')'
        headers[8] = headers1[4] + ' (' + headers[8] + ')'
        headers[9] = headers1[5] + ' (' + headers[9] + ')'
        headers[10] = headers1[5] + ' (' + headers[10] + ')'
        headers[11] = headers[11]
        headers[12] = headers1[6] + ' (' + headers[12] + ')'

        # Extract data rows
        data = []
        for row in rows[3:-1]:
            cols = row.find_all(['th', 'td'])
            cols = [col.text.strip() for col in cols]
            data.append(cols)

        # Convert data to a Pandas DataFrame
        df = pd.DataFrame(data, columns=headers).dropna()

        # Clean data
        df['Date'] = pd.to_datetime(headers[0] + ' ' + df[headers[0]], format='%Y %b %d')
        df[['Sunrise (Time)', 'Sunrise (Angle)']] = df['Sunrise'].str.extract(r'(\d+:\d+ [apm]+) ↑ \((\d+)°\)')
        df[['Sunset (Time)', 'Sunset (Angle)']] = df['Sunset'].str.extract(r'(\d+:\d+ [apm]+) ↑ \((\d+)°\)')
        df[['Solar Noon (Time)', 'Solar Noon (Angle)']] = df['Time'].str.extract(r'(\d+:\d+ [apm]+) \(([\d.]+)°\)')
        df = df.drop(columns=[headers[0], 'Sunrise', 'Sunset', 'Time'])

        # Reorder columns
        column_order = np.concatenate([['Date', 'Sunrise (Time)', 'Sunrise (Angle)', 'Sunset (Time)', 'Sunset (Angle)'], headers[3:11], ['Solar Noon (Time)', 'Solar Noon (Angle)', headers[-1]]])
        df = df[column_order]

        return df
    except Exception as e:
        return None

#Function to call
#Retrieve the dataframe of date and time of State park
def retrieve_SP_time_date(state_park):
    # Get all the responses
    responses = get_time_date_html_responses(state_park, YEAR)

    # Initialize an empty list to store DataFrames
    dfs = []

    # Iterate through each response and retrieve data
    for response in responses:
        df = parse_and_store_monthly_time_date(state_park, response.content)
        if df is not None:
            dfs.append(df)

    if not dfs:
        print(f"Can't find data for {state_park}")
        return None
    else:
        # Concatenate all DataFrames into a single DataFrame
        final_df = pd.concat(dfs, ignore_index=True)
        final_df.insert(0, 'State Park', state_park)
        print(f'Successfully retrieved data for {state_park}')

        return final_df

"""
Retrieve data from Wikipedia
"""
#Helper function
#Retrieve the State Parks table from wiki
def retrieve_SP():
    SP_table = pd.read_html(CA_STATE_PARKS_URL)[0]
    SP_table.columns = SP_table.columns.droplevel(0)
    SP_table.rename(columns={'Park name': 'State Park', 'County orcounties': 'County', 'acres': 'Size (acres)', 'ha': 'Size (ha)', 'Year established[1]': 'Year established'}, inplace=True)
    return SP_table

#Helper function
#Retrieve the links to each of the State Parks own pages
def retrieve_SP_links():
    # Send a GET request to the URL
    response = requests.get(CA_STATE_PARKS_URL)

    # List to store park links
    SP_links = []

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the table with the specified class
        table = soup.find('table', class_='wikitable')

        # Extract all the rows from the table
        rows = table.find_all('tr')[2:]

        # Iterate over rows and extract links
        for row in rows:
            link = row.find('a')
            park_link = link.get('href')
            SP_links.append(park_link)
    else:
        print(f"Error: Failed to retrieve the page. Status code: {response.status_code}")

    return SP_links

#Helper funciton
#Convert values from dms to decimal
def dms_to_decimal(dms_str):
    # Find all numbers in the string
    numbers = list(map(int, re.findall(r'\d+', dms_str)))

    # Extract degrees, minutes, and seconds
    if len(numbers) == 3:
        degrees, minutes, seconds = numbers[:3]
    elif len(numbers) == 2:
        degrees, minutes = numbers[:2]
        seconds = 0
    else:
        degrees = numbers[0]
        minutes = 0
        seconds = 0

    direction = dms_str[-1]
    
    decimal_degrees = float(degrees) + (float(minutes) / 60) + (float(seconds) / 3600)
    if direction == 'S' or direction == 'W':
        decimal_degrees *= -1
    return round(decimal_degrees, 4)

#Helper function
#Convert coordinates from dms to decimal
def convert_coordinates(lat_str, long_str):
    latitude = dms_to_decimal(lat_str)
    longitude = dms_to_decimal(long_str)
    return latitude, longitude

#Helper function
#Retrieve all states parks coordinates if aval on wikipedia
def retrieve_SP_coordinates(SP_links):
    dfs = []
    # Iterate over park links
    for link in SP_links:
        new_url = WIKIPEDIA_URL + link

        # Send a GET request to the URL
        response = requests.get(new_url)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the HTML content of the page
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find latitude and longitude spans
            latitude = soup.find('span', class_='latitude')
            longitude = soup.find('span', class_='longitude')

            if latitude and longitude:
                # Convert coordinates
                latitude, longitude = convert_coordinates(latitude.text, longitude.text)
            else:
                # If latitude or longitude is missing, set them to NaN
                latitude, longitude = 'NaN', 'NaN'
                
            data = {'Latitude': [latitude], 
                    'Longitude': [longitude]}
            print(f'Successfully retrieved data from {new_url}')

        else:
            print(f"Error: Failed to retrieve the page {new_url}. Status code: {response.status_code}")
            data = {'Latitude': ['NaN'], 
                    'Longitude': ['NaN']}
        df = pd.DataFrame(data)
        dfs.append(df)

    # Concatenate DataFrames into a final DataFrame
    final_df = pd.concat(dfs, ignore_index=True)

    return final_df

#Function to call
#Retrieve the comeplete State Parks table from wiki with coordinates
def retrieve_SP_table():
    SP_links = retrieve_SP_links()
    SP_table = retrieve_SP()
    SP_coordinates = retrieve_SP_coordinates(SP_links)

    #Add Coordinates to NP table
    keys = ['SP_table', 'SP_coordinates']
    final_SP_table = pd.concat([SP_table, SP_coordinates], axis=1, keys=keys)
    final_SP_table.columns = final_SP_table.columns.droplevel(0)

    return final_SP_table














