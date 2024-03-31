"""
GAPI - Google Maps API Utility Class

The GAPI class encapsulates interactions with the Google Maps API, offering simplified methods for geocoding addresses, 
calculating commute information, adding anonymity to location data, and generating static map images. This utility class 
is intended to streamline the process of integrating Google Maps services into the analysis workflow, focusing on geospatial 
data manipulation and visualization tasks.

This class handles API key management, rate limit considerations, and provides custom exception handling for API-related errors, 
enhancing the robustness of geospatial analyses conducted by the Analyzer.

Author: Victor Foulk
License: MIT License
Date: 2024-03-15
Version: 0.0.1 Pre-Alpha

"""

import googlemaps
from dotenv import load_dotenv
import os
import random
import math

class EmptyResult(Exception):
    # create a custom exception for when the geocode result is empty
    pass

class GAPI:
    def __init__(self, api_key=None):
        """
        Initializes the GAPI object with a provided Google Maps API key or loads it from the environment.

        Args:
            api_key (str, optional): The Google Maps API key. If not provided, the key is loaded from the 
            .env file using the GMAPS_API_KEY variable.

        This constructor sets up the Google Maps client for subsequent API calls and defines a mapping of Google API 
        exceptions to their recoverability status.
        """

        # load the API key from the .env file
        if api_key is not None:
            self.api_key = api_key
        else:
            load_dotenv()
            self.api_key = os.getenv("GMAPS_API_KEY")
        self.gmaps = googlemaps.Client(key=self.api_key)
        # Dictionary mapping exceptions to recoverability
        self.google_api_exceptions = {
            'ApiError': 'non-recoverable',  # General API errors
            'TransportError': 'recoverable',  # Issues with the network transport
            'HttpError': 'recoverable',  # Errors in HTTP response
            'Timeout': 'recoverable',  # Request timeout errors
            '_RetriableRequest': 'recoverable', # Retriable requests
            '_OverQueryLimit': 'recoverable', # Rate limit errors
            'EmptyResult': 'recoverable',  # Empty results
            # Add more specific exceptions as needed
}
        return None
    
    def validate_address(self, address):
        """
        Validates an address using the Google Maps API, ensuring it is a legitimate and recognized address.

        Args:
            address (str): The address to validate.

        Returns:
            dict: The validation result, which may include detailed address information or an error message if the validation fails.

        This method attempts to validate the given address and catches any exceptions, adding a note to the 
        exception with the address that triggered it before returning an error dictionary.
        """
        try:
            r=self.gmaps.addressvalidation(address)
            return(r)
        except Exception as e:
            e.add_note = "Address validation triggered an exception trying address "+ address + "."
            return {"Error":str(e)}

    def commute(self, origin, destination, departure_time):
        """
        Calculates commute details between an origin and a destination at a specified departure time.

        Args:
            origin (tuple): The latitude and longitude of the origin point.
            destination (tuple): The latitude and longitude of the destination point.
            departure_time (datetime): The time of departure used to estimate traffic conditions.

        Returns:
            dict: A dictionary containing commute distance, duration, and duration in traffic. If an error occurs, 
            returns a dictionary with an error message.

        Exceptions are caught and annotated with the relevant details before being returned as part of the error dictionary.
        """

        # get the duration of the morning commute, returning a dictionary of the distance, duration, and duration in traffic
        try:
            directions_result = self.gmaps.directions(origin, destination, mode="driving", 
                                                    departure_time=departure_time, avoid="tolls", 
                                                    traffic_model="pessimistic", units="imperial")
            # create a dictionary to hold the results
            commute = {}
            commute["distance"] = directions_result[0]["legs"][0]["distance"]["text"]
            commute["duration"] = directions_result[0]["legs"][0]["duration"]["text"]
            commute["duration_in_traffic"] = directions_result[0]["legs"][0]["duration_in_traffic"]["text"]
            return commute
        except Exception as e:
            e.add_note = "Commute triggered an exception trying origin " + origin + " and destination " + destination + " at departure time" + departure_time + "."
            return {"Error":str(e)}
    
    def geocode(self, address):
        """
        Retrieves the latitude and longitude coordinates for a given address.

        Args:
            address (str): The address to geocode.

        Returns:
            dict: A dictionary containing the 'lat' and 'lng' keys with corresponding latitude and longitude values.

        Raises:
            EmptyResult: If the geocode operation returns an empty result, indicating the address could not be found or recognized.

        Additional exceptions are caught, annotated, and re-raised to provide more context about the failure.
        """
        # get the GPS coordinates of an address
        geocode_result = self.gmaps.geocode(address)
        try:
            return geocode_result[0]["geometry"]["location"]
        except Exception as e:
            # if the geocode result is an empty list... we had a silent failure
            if len(geocode_result) == 0:
                raise EmptyResult("Geocode result is empty.")
            else:
                # raise the exception
                e.add_note = "Geocode triggered an exception trying address "+ address + "."
                raise e
    
    def fuzz_latlong(self, latlong, fuzz):
        """
        Applies a random displacement within a specified radius to a set of GPS coordinates to anonymize them.

        Args:
            latlong (dict): A dictionary containing the 'lat' and 'lng' keys for the original coordinates.
            fuzz (float): The radius in miles within which the random displacement should be applied.

        Returns:
            dict: A dictionary containing the 'lat' and 'lng' keys with the fuzzed coordinates.

        This method is particularly useful for anonymizing location data before publication, ensuring individual privacy is maintained.
        """
     # add a small amount of fuzz to the GPS coordinates to provide a degree of anonymity to the data (useful for publication)
        # first, convert the fuzz into a lat lont offset, it will vary by the distance from the equator
        np = self.haversine_newpoint(latlong["lat"], latlong["lng"], fuzz, 0)
        fuzz = abs(latlong["lat"] - np[0])
        random.seed() 
        latfuzz = random.uniform(-fuzz, fuzz)
        lngfuzz = random.uniform(-fuzz, fuzz) 
        latlong["lat"] += latfuzz
        latlong["lng"] += lngfuzz
        return latlong

    def haversine(self,lat1, lon1, lat2, lon2):
        """
        Calculates the great-circle distance between two points on the Earth's surface.

        Args:
            lat1 (float): The latitude of the first point.
            lon1 (float): The longitude of the first point.
            lat2 (float): The latitude of the second point.
            lon2 (float): The longitude of the second point.

        Returns:
            float: The distance between the two points in miles.
        """

        # Radius of the Earth in miles
        R = 3958.8
        # Radius of the Earth in kilometers (uncomment to use kilometers)
        #R = 6371.0

        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Difference in coordinates
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Haversine formula
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        # Total distance in (units selected above)
        distance = R * c

        return distance
    
    # calcuate a new point given a distance and bearing from a starting point using haversine
    def haversine_newpoint(self,lat1, lon1, distance, bearing):
        """
        Determines a new latitude and longitude based on starting coordinates, distance, and bearing using the Haversine formula.

        This method calculates a new geographic location given a starting point, a distance to travel, and a bearing (direction) 
        from the starting point. The calculation takes into account the curvature of the Earth.

        Args:
            lat1 (float): Latitude of the starting point in degrees.
            lon1 (float): Longitude of the starting point in degrees.
            distance (float): Distance to move from the starting point in miles.
            bearing (float): Direction to move in from the starting point in degrees.

        Returns:
            tuple: A tuple containing the latitude and longitude (lat2, lon2) of the new point.
        """
        # convert distance to radians
        distance = distance / 3958.8
        # convert bearing to radians
        bearing = math.radians(bearing)
        # convert latitude to radians
        lat1 = math.radians(lat1)
        # convert longitude to radians
        lon1 = math.radians(lon1)
        # calculate the new latitude
        lat2 = math.asin(math.sin(lat1) * math.cos(distance) + math.cos(lat1) * math.sin(distance) * math.cos(bearing))
        # calculate the new longitude
        lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(distance) * math.cos(lat1), math.cos(distance) - math.sin(lat1) * math.sin(lat2))
        # convert latitude back to degrees
        lat2 = math.degrees(lat2)
        # convert longitude back to degrees
        lon2 = math.degrees(lon2)
        return (lat2, lon2)

        

