"""
Graphing utility class for the Relocation Impact Analysis Tool

The Graphing class in this module is designed to support creating visual representations of commute data, offering insightful visual analytics 
for relocation impact analysis. It harnesses the power of Matplotlib, Cartopy, and other scientific computing libraries to produce 
detailed maps, heatmaps, and histograms. These visualizations can illustrate geographical distributions, commute distances and times, 
and other critical metrics such as CO2 emissions or cost implications of potential office relocations. The class provides methods to 
plot employee and office locations on maps with various base layers, including OpenStreetMap and Google Maps, and to draw commuting 
radii, convex hulls, and more. It supports filtering employees based on commute distances and times, enhancing decision-making with 
visual data exploration tools. This module stands as a core component for analyzing the spatial aspects of commute data, aiding in 
the evaluation of relocation strategies through comprehensive, easy-to-understand graphical outputs.

Author: Victor Foulk
License: MIT License
Date: 2024-03-15
Version: 0.0.1 Pre-Alpha
"""

import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import Circle, Ellipse
from matplotlib.lines import Line2D

import numpy as np
from scipy.spatial import ConvexHull

from cartopy.io.img_tiles import OSM
from cartopy.io.img_tiles import GoogleTiles

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd

import math


class Graphing:
    def __init__(self):
        """
        Initializes the Graphing class instance.
        """
        pass  

    def configure_map_plot(self, latitudes, longitudes, imagery="OSM", padding=0.03):
        """
        Configures a map plot with specified latitudes and longitudes and an optional background imagery source.

        Args:
            latitudes (list): A list of latitude coordinates for plotting.
            longitudes (list): A list of longitude coordinates for plotting.
            imagery (str, optional): The background imagery source. Options include "OSM" (default), "Google", and "GoogleSatellite".
            padding (float, optional): Padding around the coordinate extents to ensure all points are visible on the map.

        Returns:
            tuple: A tuple containing the figure and axis objects of the map plot.
        """
        # configure the map plot
        if imagery == "OSM":
            # use OpenStreetMap as the background map
            imagery = OSM()
        elif imagery == "Google":
            # alternatively, use GoogleTiles() for a satellite map
            imagery = GoogleTiles()
        elif imagery == "GoogleSatellite":
            # alternatively, use GoogleTiles() for a satellite map
            imagery = GoogleTiles(style='satellite')
        else:
            imagery = OSM()

        # set figure size for readability
        fig, ax = plt.subplots(figsize=(15, 10), subplot_kw={'projection': imagery.crs})
        
        # set the extent of the map to include all the points plus a little extra
        lat_delta = abs((max(latitudes) - min(latitudes)) * padding)
        long_delta = abs((max(longitudes) - min(longitudes)) * padding)
        min_max = [min(longitudes)-long_delta, max(longitudes)+long_delta,min(latitudes)-lat_delta, max(latitudes)+lat_delta]
        ax.set_extent(min_max)

        # Add the imagery to the map at an automatically-chosen zoom level
        ax.add_image(imagery, self.calculate_zoom_level(ax), cmap='gray')
        return fig, ax

    def plot_addresses(self, ax, data, color='red', label=None, s=10, alpha=1.0, linestyle='', marker='o'):
        """
        Plots address points on the map.

        Args:
            ax: The matplotlib axes object on which to plot.
            data (DataFrame): The data containing 'latitude' and 'longitude' columns for the points to plot.
            color (str, optional): The color of the points. Defaults to 'red'.
            label (str, optional): Label for the points. Defaults to None.
            s (int, optional): Size of the points. Defaults to 10.
            alpha (float, optional): Transparency of the points. Defaults to 1.0.
            linestyle (str, optional): Style of the point lines. Defaults to '' (solid).
            marker (str, optional): Shape of the points. Defaults to 'o' (circle).
        """
        # plot the lat long points
        ax.scatter(data['longitude'], data['latitude'], color=color, marker=marker, alpha=alpha, s=s, linestyle=linestyle, transform=ccrs.PlateCarree(), label=label)

    def plot_offices(self, ax, data, color='black', label=None, s=100, alpha=1.0, linestyle='', marker='*'):
        """
        Plots office location points on the map.

        Args:
            ax: The matplotlib axes object on which to plot.
            data (DataFrame): The data containing 'latitude' and 'longitude' columns for the points to plot.
            color (str, optional): The color of the points. Defaults to 'black'.
            label (str, optional): Label for the points. Defaults to None.
            s (int, optional): Size of the points. Defaults to 100.
            alpha (float, optional): Transparency of the points. Defaults to 1.0.
            linestyle (str, optional): Style of the point lines. Defaults to '' (solid).
            marker (str, optional): Shape of the points. Defaults to '*' (star).
        """
        # plot the lat long points
        ax.scatter(data['longitude'], data['latitude'], color=color, marker=marker, alpha=alpha, s=s, linestyle=linestyle, transform=ccrs.PlateCarree(), label=label)
        
    def add_scalebar(self, ax, location=(0.05, 0.05), font_mod=1):
        """
        Adds a scale bar to the map plot.

        Args:
            ax: The matplotlib axes object to add the scale bar to.
            location (tuple, optional): A tuple (x, y) representing the location of the scale bar as a fraction of the axis dimensions. 
            Defaults to (0.05, 0.05).
        """

        # add a scale bar
        # first get the extent of the map
        x0, x1, y0, y1 = ax.get_extent(ccrs.PlateCarree())
        
        # calculate the width of the x axis in miles
        xd = self.haversine(y0, x0, y1, x0)
        yd = self.haversine(x0, x0, y1, x1)
        
        order = self.round_to_nearest_order_of_magnitude(xd)
        bar = order/4.0
        
        np=self.haversine_newpoint(y0, x0, bar, 90)
        # now we create a tuple of long/lats for the scalebar
        scalebar = ([x0, np[1]], [y0, y0])
        # now, adjust the coordinates of the scalebar for proper chart placement, up location[0]% and right location[1]%
        scalebar = ([x0 + (x1-x0)*location[0], np[1] + (x1-x0)*location[0]], [y0 + (y1-y0)*location[1], y0 + (y1-y0)*location[1]])
        # now we create end bars for the scale bar using scalebar as the source coordinates.
        # end bars are positioned one at each end of the scalebar, centered vertically on the scalebar, and total height being 2% of y axis
        scalebar_end = ([scalebar[0][0], scalebar[0][0]], [scalebar[1][0] - (y1-y0)*0.01, scalebar[1][0] + (y1-y0)*0.01])
        scalebar_end2 = ([scalebar[0][1], scalebar[0][1]], [scalebar[1][0] - (y1-y0)*0.01, scalebar[1][0] + (y1-y0)*0.01])
        # now we put a text label on the scale bar indicating the number of miles shown (bar).  Center the lable on the scalebar
        ax.text((scalebar[0][0]+scalebar[0][1])/2, scalebar[1][0] - (y1-y0)*0.01, str(bar) + ' miles', 
                horizontalalignment='center', verticalalignment='top', transform=ccrs.PlateCarree(), fontsize=10*font_mod)

        # draw a scale bar
        ax.plot(scalebar[0],scalebar[1], transform=ccrs.PlateCarree(), color='black', linewidth=2)
        ax.plot(scalebar_end[0],scalebar_end[1], transform=ccrs.PlateCarree(), color='black', linewidth=2)
        ax.plot(scalebar_end2[0],scalebar_end2[1], transform=ccrs.PlateCarree(), color='black', linewidth=2)

    def round_to_nearest_order_of_magnitude(self,number):
        """
        Rounds a number to the nearest order of magnitude.

        Args:
            number (float): The number to round.

        Returns:
            float: The rounded number.
        """

        # Calculate the order of magnitude of the number
        order_of_magnitude = 10 ** math.floor(math.log10(abs(number)))
        # Normalize the number to a value between 1 and 10 and round it
        rounded_normalized_number = round(number / order_of_magnitude)
        # Multiply back by the order of magnitude to get the rounded number
        return rounded_normalized_number * order_of_magnitude
        
    def calculate_zoom_level(self, ax, tile_service_resolution=256):
        """
        Calculate an appropriate zoom level for a Cartopy axis based on its extent.
        
        Args:
        - ax: The Cartopy GeoAxes object.
        - tile_service_resolution: The resolution of the tile service (256 for most web services).
        
        Returns:
        - An integer zoom level.
        """
        # Get the extent of the axis and calculate the width in degrees
        extent = ax.get_extent(ccrs.PlateCarree())
        width_deg = extent[1] - extent[0]
        
        # Estimate the width of the plot in pixels
        fig = plt.gcf()
        width_in_pixels = fig.get_dpi() * fig.get_size_inches()[0]
        
        # Calculate the zoom level
        # This formula is an approximation and might need adjustment for your specific needs
        zoom_level = math.log2((360 * width_in_pixels) / (width_deg * tile_service_resolution))
        
        return max(0, min(round(zoom_level), 19))  # Ensure zoom level is within a valid range
    
    def filter_radius(self,sources, targets, radius, inside=True):
        """
        Filters source points based on their linear distance from target points within a specified radius.

        Args:
            sources (DataFrame): A DataFrame containing source points with 'latitude' and 'longitude' columns.
            targets (DataFrame): A DataFrame containing target points with 'latitude' and 'longitude' columns.
            radius (float): The radius within which to filter source points, in miles.
            inside (bool, optional): If True, filters for source points inside the radius. If False, filters for source points 
            outside the radius. Defaults to True.

        Returns:
            DataFrame: A DataFrame of filtered source points that meet the radius criteria.
        """

        # check if the lat/long pair is within radius of any of the targets.
        # offices is a pandas dataframe with columns latitude and longitude, and each row represents a cetnered target location
        # return true if the lat/long pair is within radius of any of the offices, otherwise return false (vice versa for outside)
        def check_r(lat, lon, targets, radius, inside=True):
            for index, row in targets.iterrows():
                if inside:
                    if self.haversine(lat, lon, row['latitude'], row['longitude']) <= radius:
                        return True
                elif not inside:
                    if self.haversine(lat, lon, row['latitude'], row['longitude']) > radius:
                        return True
            return False
        return pd.DataFrame([{'latitude': lat, 'longitude': lon} for lat, lon in zip(sources['latitude'], sources['longitude']) 
                                if check_r(lat, lon, targets, radius, inside=inside)])


    def filter_drive_distance(self, sources, targets, radius, commute_data, inside=True):
        """
        Filters source points based on the driving distance to target points using commute data.

        Args:
            sources (DataFrame): A DataFrame containing source points with 'latitude' and 'longitude' columns.
            targets (DataFrame): A DataFrame containing target points with 'latitude' and 'longitude' columns.
            radius (float): The radius within which to filter source points, in miles.
            commute_data (DataFrame): A DataFrame containing commute data between source and target points.
            inside (bool, optional): If True, filters for source points within the driving distance radius. If False, 
            filters for source points outside the radius. Defaults to True.

        Returns:
            DataFrame: A DataFrame of filtered source points that meet the driving distance criteria.
        """

        # employee address maps to source, office address maps to destination
        # for each office, check if the lat/long pair is within radius of any of the offices based upon actual driving distance
        def check_d(lat, lon, targets, radius, commute_data, inside=True):
            for index, row in targets.iterrows():
                # get the rows from commute_data that have the office address as the destination and lat long pair as the source
                filtered_data = commute_data[
                                    (commute_data['origin_lat'] == lat) &
                                    (commute_data['origin_long'] == lon) &
                                    (commute_data['destination_lat'] ==row['latitude']) &
                                    (commute_data['destination_long'] == row['longitude'])
                                ]
                for index2, row2 in filtered_data.iterrows():
                    if inside and row2['miles'] <= radius:
                        return True
                    elif not inside and row2['miles'] > radius:
                        return True
            return False
        return pd.DataFrame([{'latitude': lat, 'longitude': lon} for lat, lon in zip(sources['latitude'], sources['longitude'])
                                if check_d(lat, lon, targets, radius, commute_data, inside=inside)])
    
    def filter_drive_time(self, sources, targets, minutes, commute_data, inside=True):
        """
        Filters source points based on the driving time to target points using commute data.

        Args:
            sources (DataFrame): A DataFrame containing source points with 'latitude' and 'longitude' columns.
            targets (DataFrame): A DataFrame containing target points with 'latitude' and 'longitude' columns.
            minutes (float): The maximum driving time in minutes within which to filter source points.
            commute_data (DataFrame): A DataFrame containing commute data between source and target points.
            inside (bool, optional): If True, filters for source points within the specified driving time. If False, filters for source points outside the driving time. Defaults to True.

        Returns:
            DataFrame: A DataFrame of filtered source points that meet the driving time criteria.
        """

        def check_t(lat, long, targets, minutes, commute_data, inside=True):
            for index, row in targets.iterrows():
                # get the rows from commute_data that have the office address as the destination and lat long pair as the source
                filtered_data = commute_data[
                                    (commute_data['origin_lat'] == lat) &
                                    (commute_data['origin_long'] == long) &
                                    (commute_data['destination_lat'] ==row['latitude']) &
                                    (commute_data['destination_long'] == row['longitude'])
                                ]
                for index2, row2 in filtered_data.iterrows():
                    if inside and row2['m_morning_duration_in_traffic'] <= minutes:
                        return True
                    elif not inside and row2['m_morning_duration_in_traffic'] > minutes:
                        return True
            return False
        return pd.DataFrame([{'latitude': lat, 'longitude': long} for lat, long in zip(sources['latitude'], sources['longitude'])
                                if check_t(lat, long, targets, minutes, commute_data, inside=inside)])
                            
    def get_common_points(self, set1, set2):
        """
        Finds common points between two sets of latitudes and longitudes.

        Args:
            set1 (DataFrame): A DataFrame containing 'latitude' and 'longitude' columns.
            set2 (DataFrame): A DataFrame containing 'latitude' and 'longitude' columns.

        Returns:
            DataFrame: A DataFrame of common points between the two sets.
        """
        # find the common points between the two sets
        return set1.merge(set2, on=['latitude', 'longitude'])

    def get_unique_points(self, set1, set2):
        """
        Finds unique points in the first set that are not present in the second set.

        Args:
            set1 (DataFrame): A DataFrame containing 'latitude' and 'longitude' columns.
            set2 (DataFrame): A DataFrame containing 'latitude' and 'longitude' columns.

        Returns:
            DataFrame: A DataFrame of unique points in the first set.
        """

        # find the unique points in the first set
        return set1[~set1.isin(set2)].dropna()
    
    def haversine(self,lat1, lon1, lat2, lon2):
        """
        Calculates the great-circle distance between two points on the Earth specified in decimal degrees using the Haversine formula.

        Args:
            lat1 (float): Latitude of the first point.
            lon1 (float): Longitude of the first point.
            lat2 (float): Latitude of the second point.
            lon2 (float): Longitude of the second point.

        Returns:
            float: The distance between the two points in miles.
        """

        #To calculate the distance between two latitude/longitude coordinates while taking the curvature of the Earth into account, 
        #you use the Haversine formula. This formula gives you the great-circle distance between two points on the surface of a sphere, 
        #given their longitudes and latitudes. This is particularly useful for calculating the approximate distance between two points 
        #on the Earth."

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
        Calculates a new point given a distance and bearing from a starting point using the Haversine formula.

        Args:
            lat1 (float): Latitude of the starting point.
            lon1 (float): Longitude of the starting point.
            distance (float): Distance from the starting point in miles.
            bearing (float): Bearing in degrees from the starting point to the new point.

        Returns:
            tuple: A tuple (lat2, lon2) representing the latitude and longitude of the new point.
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

    def plot_ellipses(self, ax, offices, commute_radius):
        """
        Draws ellipses around office locations to represent the commute radius from each office.

        Args:
            ax: The matplotlib axes object on which to draw.
            offices (DataFrame): A DataFrame containing office locations with 'latitude' and 'longitude' columns.
            commute_radius (float): The radius to draw around each office location, in miles.
        """

        # draw an ellipse around the office locations to represent the radius from each office (ellipse in thise OSM projection will be a circle)
        # note: this will be a jagged representation due to cartopy handling, better to use our own eline function
        xcdelta = None
        ycdelta = None
        for index, row in offices.iterrows():
            # if cdelta is None, calculate the circle radius using first set of lat long, and using haversine to calcuate a new point, then x0-x1
            if ycdelta is None:
                # calculate the circle radius using the first set of lat long
                ycdelta = abs(row['latitude']-self.haversine_newpoint(row['latitude'], row['longitude'], commute_radius, 0)[0])
                xcdelta = abs(row['longitude']-self.haversine_newpoint(row['latitude'], row['longitude'], commute_radius, 90)[1])

            # calculate the ellipse around the office location
            ellipse = Ellipse((row['longitude'], row['latitude']), 2*xcdelta, 2*ycdelta, color='blue', fill=False, label='Radius', transform=ccrs.PlateCarree(), zorder=10, )
            ax.add_patch(ellipse)
    
    def plot_elines(self, ax, targets, commute_radius, color='black', linestyle='--',linewidth=2):
        """
        Draws lines (elipses) around target points to represent a specified radius from each point on a map.

        Args:
            ax: The matplotlib axes object on which to draw.
            targets (DataFrame): A DataFrame containing target points with 'latitude' and 'longitude' columns.
            commute_radius (float): The radius around each target point to draw, in miles.
            color (str, optional): Color of the lines. Defaults to 'black'.
            linestyle (str, optional): Style of the line. Defaults to '--'.
            linewidth (int, optional): Width of the lines. Defaults to 2.

        """

        for index, row in targets.iterrows():
            # plot an eline
            elinex,eliney = self.create_eline(row['latitude'], row['longitude'], commute_radius)
            ax.plot(elinex, eliney, color=color, transform=ccrs.PlateCarree(), label='New Line', linewidth=linewidth, linestyle=linestyle, marker='')

    def create_eline(self, lat, long, r, step=10):
        """
        Creates a set of latitude and longitude points that form a circle (or ellipse) around a central point.

        Args:
            lat (float): Latitude of the central point.
            long (float): Longitude of the central point.
            r (float): Radius of the circle in miles.
            step (int, optional): Degrees between each point on the circle. Smaller values create a smoother circle. Defaults to 10.

        Returns:
            tuple: Two lists containing the longitude and latitude of points forming the circle.
        """

        # start with the lat/long, and calculate a point r miles away at 0 degrees, then, repeat every step degrees until 360, inclusive
        elinex = []
        eliney = []
        for i in range(0, 360+step, step):
            np = self.haversine_newpoint(lat, long, r, i)
            elinex.append(np[1])
            eliney.append(np[0])
        return [elinex, eliney]
    
    def plot_convex_hull(self, ax, data, color='green', linestyle='--', linewidth=2, alpha=1):
        """
        Draws a convex hull around a set of points on the map, effectively creating a boundary that encloses all the points.

        Args:
            ax: The matplotlib axes object on which to draw.
            data (DataFrame): A DataFrame containing points with 'latitude' and 'longitude' columns.
            color (str, optional): Color of the convex hull boundary. Defaults to 'green'.
            linestyle (str, optional): Style of the hull boundary line. Defaults to '--'.
            linewidth (int, optional): Width of the hull boundary line. Defaults to 2.
            linealpha (float, optional): Transparency of the hull boundary line. Defaults to 0.
            fillalpha (float, optional): Transparency of the hull fill. Defaults to 1.

        """

        # plot the convex hull of the employee addresses within the commute radius
        hull = ConvexHull(data[['longitude', 'latitude']])
        for simplex in hull.simplices:
            ax.plot(data['longitude'].iloc[simplex], data['latitude'].iloc[simplex], linestyle=linestyle, 
                     color=color, transform=ccrs.PlateCarree(), linewidth=linewidth, marker='', alpha=alpha) 
    
    
    def get_commute_values(self, emp, office, commute_data, values):
        """
        Extracts specified values from the commute data for employee addresses that match a given office location.

        Args:
            emp (DataFrame): A DataFrame containing employee locations with 'latitude' and 'longitude'.
            office (DataFrame): A single-row DataFrame containing the target office location with 'latitude' and 'longitude'.
            commute_data (DataFrame): A DataFrame containing commute data between employee and office locations.
            values (list of str or str): Column name(s) in `commute_data` to extract. Can be a single column name or a list of names.

        Returns:
            DataFrame: A DataFrame containing the extracted values for each employee location that matches the given office location. The DataFrame includes 'latitude' and 'longitude' of the employee locations and the specified `values`.
        """

         # Ensure the basic columns are always included
        base_columns = ['origin_lat', 'origin_long']
        # Combine base columns with user-specified columns, removing duplicates
        if isinstance(values, str):
            selected_columns = base_columns + [values]
        else:
            selected_columns = base_columns + [value for value in values if value not in base_columns]
        
        return commute_data[(commute_data['destination_lat'] == office.iloc[0]['latitude']) & 
                           (commute_data['destination_long'] == office.iloc[0]['longitude']) & 
                            (commute_data['origin_lat'].isin(emp['latitude']) & commute_data['origin_long'].isin(emp['longitude']))][selected_columns].rename(columns={'origin_lat': 'latitude', 'origin_long': 'longitude'})

    
    def plot_preamble(self, emp, offices, cutoff_radius=None, cutoff_distance=None, commute_data=None):
        """
        Filters employee locations based on a specified cutoff radius from office locations and prepares data for plotting.

        Args:
            emp (DataFrame): DataFrame containing employee locations with 'latitude' and 'longitude'.
            offices (DataFrame): DataFrame containing office locations with 'latitude' and 'longitude'.
            cutoff_radius (float, optional): Radius in miles to filter employee locations. Only employee locations within this radius from any office location are included.
            cutoff_distance (float, optional): Driving distance in miles to filter employee locations. Only employee locations within this distance from any office location are included.
            commute_data (DataFrame): A DataFrame containing commute data between employee and office locations, required if `cutoff_distance` is specified.
            
        Returns:
            tuple: A tuple containing the filtered employee DataFrame, and Series objects for latitudes and longitudes of all included 
            locations (employees and offices combined). The filtered DataFrame only includes employees within the `cutoff_radius` from 
            any office location if specified.
        """

        # we will use the haversine formula to calculate the distance between two lat/long pairs 
        if cutoff_radius is not None:
            # filter the employee lat/long pairs to only include those within cutoff_radius of any of the offices
            filtered_emp_points = self.filter_radius(emp, offices, cutoff_radius)
        elif cutoff_distance is not None:
            # filter the employee lat/long pairs to only include those within cutoff_distance of any of the offices
            filtered_emp_points = self.filter_drive_distance(emp, offices, cutoff_distance, commute_data)
        else:
            filtered_emp_points = emp
        
        # data is a pandas dataframe has coloumns latitude and longitude        
        # append the office lat/longs to the employee lat/longs to get bounding box
        latitudes = pd.concat([filtered_emp_points['latitude'], offices['latitude']])
        longitudes = pd.concat([filtered_emp_points['longitude'], offices['longitude']])
        return filtered_emp_points, latitudes, longitudes
    
    ############################################################################################################
    def get_map_view(self, emp, offices, commute_data=None, cutoff_radius=None, cutoff_distance=None, commute_radius=None, 
                      commute_color=False, title=None, convex_hull=False, size_e=10, 
                      size_o=200, color_o='black', color_e_in='green', color_e_out='red', legend_loc='upper right',
                      o_label='Potential Office \nLocations', e_label='Employee Addresses', manual_plot=False, font_mod=1):
        """
        Generates a map view showing employee and office locations, optionally with commute radius and coloring based on commute data.

        Args:
            emp (DataFrame): DataFrame containing employee locations with 'latitude' and 'longitude'.
            offices (DataFrame): DataFrame containing office locations with 'latitude' and 'longitude'.
            commute_data (DataFrame, optional): DataFrame containing commute data between employee and office locations. Required if commute_color is True.
            cutoff_radius (float, optional): Radius in miles to filter employee locations for visualization.
            cutoff_distance (float, optional): Driving distance in miles to filter employee locations for visualization.
            commute_radius (float, optional): Radius in miles from offices to visualize commute boundaries.
            commute_color (bool, optional): If True, colors employee locations based on commute data presence within commute_radius.
            title (str, optional): Title for the map.
            convex_hull (bool, optional): If True, draws a convex hull around employee locations within commute_radius.
            size_e (int, optional): Size of markers for employee locations. Defaults to 10.
            size_o (int, optional): Size of markers for office locations. Defaults to 200.
            color_o (str, optional): Color for office location markers. Defaults to 'black'.
            color_e_in (str, optional): Color for employee locations within commute_radius. Defaults to 'green'.
            color_e_out (str, optional): Color for employee locations outside commute_radius. Defaults to 'red'.
            legend_loc (str, optional): Location of the legend on the map. Defaults to 'upper right'.
            o_label (str, optional): Label for office locations in the legend. Defaults to 'Potential Office \nLocations'.
            e_label (str, optional): Label for employee locations in the legend. Defaults to 'Employee Addresses'.
            manual_plot (bool, optional): If True, returns the matplotlib plt and axes objects for manual plotting. Defaults to False.
            font_mod (int, optional): Font size modifier for scale bar. Defaults to 1.

        Returns:
            tuple: A tuple containing the matplotlib plt and axes objects.

        Notes:
            - Requires `commute_data` for commute_color functionality.
            - Adjust `cutoff_radius` and `commute_radius` to fine-tune the visualization.
        """

        # basic pre-filtering
        filtered_emp_points, latitudes, longitudes = self.plot_preamble(emp, offices, cutoff_radius=cutoff_radius, cutoff_distance=cutoff_distance, commute_data=commute_data)

        # configure the plot
        fig, ax = self.configure_map_plot(latitudes, longitudes)        

        if manual_plot:
            return plt, ax
        # plot the lat long points
        #plt.plot(longitudes, latitudes, color='red', marker='*', markersize=3, linestyle='', transform=ccrs.PlateCarree())#ccrs.OSGB())
        if not commute_color:
            self.plot_addresses(ax, filtered_emp_points, s=size_e, color='red', label=e_label)
            self.plot_offices(ax, offices, s=size_o, color=color_o, label=o_label)
            
        elif commute_color and commute_data is None:
            # plot the lat long points with color based on if the employee is within the linear radius of any of the offices
            # first create two new data frames for the employees within and outside the linear radius, and populate them with the appropriate lat/long pairs
            emp_within = self.filter_radius(filtered_emp_points, offices, commute_radius)
            emp_outside = self.filter_radius(filtered_emp_points, offices, commute_radius, inside=False)
            # plot the lat long points
            if not emp_within.empty:
                self.plot_addresses(ax, emp_within, color=color_e_in, label=e_label +' \nWithin ' + str(commute_radius) + ' Mile Radius', s=size_e)
            if not emp_outside.empty:
                self.plot_addresses(ax, emp_outside, color=color_e_out, label=e_label + ' \nOutside ' + str(commute_radius) + ' Mile Radius', s=size_e)
            self.plot_offices(ax, offices, s=size_o, color=color_o, label=o_label)
            
        elif commute_color and commute_data is not None:
            # use the commute data to use actual driving distance to color the data points
            emp_within = self.filter_drive_distance(filtered_emp_points, offices, commute_radius, commute_data)
            emp_outside = self.filter_drive_distance(filtered_emp_points, offices, commute_radius, commute_data, inside=False)
            # plot the lat long points
            if not emp_within.empty:
                self.plot_addresses(ax, emp_within, s=size_e ,color=color_e_in, label=e_label + ' \n' + str(u'\N{LESS-THAN OR EQUAL TO}') + ' ' + str(commute_radius) + ' Mile Drive')
            if not emp_outside.empty:
                self.plot_addresses(ax, emp_outside, s=size_e, color=color_e_out, label=e_label + ' \n' + str('>') + ' '+ str(commute_radius) + ' Mile Drive')
            self.plot_offices(ax, offices, s=size_o, color=color_o, label=o_label)          

        # add a scale bar
        self.add_scalebar(ax, location=(0.05, 0.05),font_mod=font_mod)
        
        handles, labels = plt.gca().get_legend_handles_labels()
        # draw a circle around the office locations to represent the radius from each office and add legend entry, if commute_radius is not None
        if commute_radius is not None:
            new_handle = Line2D([], [], color='black', label='Radius', linestyle='--', linewidth=2, marker='')
            new_label = 'Linear Radius \n(' + str(commute_radius) + ' miles)'
            handles.append(new_handle)
            labels.append(new_label)
            self.plot_elines(ax, offices, commute_radius)
        
        if convex_hull and commute_radius is not None:
            new_handle = Line2D([], [], color='green', label='Convex Hull', linestyle='--', linewidth=2, marker='')
            new_label = 'Bounding Area, \n' + str(commute_radius) + ' Mile Commute'
            handles.append(new_handle)
            labels.append(new_label)
            self.plot_convex_hull(ax, emp_within)
            
        # add a legend  to the plot on the middle left
        self.map_view_standard_legend(ax,handles=handles, labels=labels, fontsize=10*font_mod,legend_loc=legend_loc)
        # add a title
        if title is not None:
            plt.title(title, fontsize=16*font_mod)

        return plt, ax

    def map_view_standard_legend(self, ax, handles, labels, title=None, legend_title=None, legend_loc='upper left', 
                                 legend_edgecolor='black', legend_frameon=True, legend_facecolor='white', 
                                 legend_framealpha=0.7, fontsize=10):
        """
        Adds a standard legend to a map view plot.

        Args:
            ax: The matplotlib axes object on which to draw the legend.
            handles (list): A list of handles to the objects being represented in the legend.
            labels (list): A list of labels for the objects being represented in the legend.
            title (str, optional): Title for the legend. Defaults to None.
            legend_title (str, optional): Title for the legend. Defaults to None.
            legend_loc (str, optional): Location for the legend. Defaults to 'upper left'.
            legend_labels (list, optional): Labels for the legend entries. Defaults to None.
            legend_colors (list, optional): Colors for the legend entries. Defaults to None.
            legend_markers (list, optional): Markers for the legend entries. Defaults to None.
            legend_edgecolor (str, optional): Edge color for the legend. Defaults to 'black'.
            legend_frameon (bool, optional): Whether to draw a frame around the legend. Defaults to True.
            legend_facecolor (str, optional): Face color for the legend. Defaults to 'white'.
            legend_framealpha (float, optional): Opacity of the legend frame. Defaults to 0.7.
            fontsize (int, optional): Font size for the legend. Defaults to 10.

        """
        
        # Add legend to the plot
        ax.legend(handles=handles, labels=labels, title=legend_title, loc=legend_loc, fontsize=fontsize, edgecolor=legend_edgecolor, frameon=legend_frameon, 
                  facecolor=legend_facecolor, framealpha=legend_framealpha)
        
   

############################################################################################################
            
    def get_heatmap(self, emp, office, commute_data, value, title=None, value_label='', cutoff_radius=None, cutoff_distance=None,
                    commute_radius=None, convex_hull=False, plot_points=False, imagery="OSM", cmap='jet', 
                    size_e=10, size_o=200, color_o='black', color_e_in='green', color_e_out='red', o_label='Potential Office \nLocations', 
                    e_label='Employee Addresses', manual_plot=False, alpha=0.5, levels=10, font_mod=1, figsize=(15, 15)):

        """
        Generates a heatmap of a specific commute data metric for employee locations relative to a single office location.

        Args:
            emp (DataFrame): DataFrame containing employee locations with columns 'latitude' and 'longitude'.
            office (DataFrame): Single-row DataFrame representing the target office location with columns 'latitude' and 'longitude'.
            commute_data (DataFrame): DataFrame containing commute data metrics between employee locations and office locations.
            value (str): The name of the column in `commute_data` representing the metric to visualize on the heatmap.
            title (str, optional): Title for the heatmap. Defaults to None.
            value_label (str, optional): Label for the color bar indicating the metric. Defaults to ''.
            cutoff_radius (float, optional): Radius in miles to include employee locations from the office for the heatmap. Defaults to None.
            cutoff_distance (float, optional): Driving distance in miles to include employee locations from the office for the heatmap. Defaults to None.
            commute_radius (float, optional): Specifies the radius within which employees are considered for the heatmap. Defaults to None.
            convex_hull (bool, optional): If True, draw a convex hull around the employee locations included in the heatmap. Defaults to False.
            plot_points (bool, optional): If True, plot individual employee locations on the heatmap. Defaults to False.
            imagery (str, optional): Background map style. Supports "OSM" for OpenStreetMap and "Google" for Google Maps tiles. Defaults to "OSM".
            cmap (str, optional): Colormap for the heatmap. Defaults to 'jet'.
            size_e (int, optional): Size of markers for employee locations. Defaults to 10.
            size_o (int, optional): Size of markers for office locations. Defaults to 200.
            color_o (str, optional): Color for office location markers. Defaults to 'black'.
            color_e_in (str, optional): Color for employee locations within commute_radius. Defaults to 'green'.
            color_e_out (str, optional): Color for employee locations outside commute_radius. Defaults to 'red'.
            o_label (str, optional): Label for office locations in the legend. Defaults to 'Potential Office \nLocations'.
            e_label (str, optional): Label for employee locations in the legend. Defaults to 'Employee Addresses'.
            manual_plot (bool, optional): If True, returns the matplotlib plt and axes objects for manual plotting. Defaults to False.
            alpha (float, optional): Transparency of the heatmap. Defaults to 0.5.
            levels (int, optional): Number of levels for the color bar. Defaults to 10.
            font_mod (int, optional): Font size modifier for the plot. Defaults to 1.
            figsize (tuple, optional): Figure size. Defaults to (15, 15).

        Returns:
            tuple: A tuple containing the matplotlib figure and axes objects.
        """

        
        # basic pre-filtering
        filtered_emp_points, latitudes, longitudes = self.plot_preamble(emp, office, cutoff_radius)
    
        # extract rows from commute_data where office is the destination and data aligns with the employee addresses provided
        # only the first row of office will be read, as it doesn't make sense to plot this for more than one on a heatmap
        xyz = self.get_commute_values(filtered_emp_points, office, commute_data, value)
        # plot a) heatmap of a data value relative to employee addresses and a target office location
        
        # create an np array of the lat long pairs and the value
        fig, ax = self.configure_map_plot(latitudes, longitudes, imagery=imagery)

        if manual_plot:
            return plt, ax

        # Create the heatmap
        #plt.tricontourf(X, Y, Z, cmap='jet', levels=10, alpha=0.7, transform=ccrs.PlateCarree())
        plt.tricontourf(xyz['longitude'], xyz['latitude'], xyz[value], cmap=cmap, levels=levels, alpha=alpha, transform=ccrs.PlateCarree())
        cbar = plt.colorbar(label=value_label)  # Add a color bar to show the temperature scale
        cbar.ax.yaxis.label.set_size(13*font_mod)
        
        if commute_radius is not None and convex_hull:
            # get the filtered_emp_points within the commute radius
            emp_within = self.filter_drive_distance(filtered_emp_points, office, commute_radius, commute_data)
            self.plot_convex_hull(ax, emp_within, color='red')
        
        if plot_points:
            self.plot_addresses(ax, filtered_emp_points, color='red', s=size_e, alpha=alpha, label='Employee \nAddresses')
            self.plot_offices(ax, office, color='black', s=size_o, alpha=alpha, label='Potential Office \nLocations')


        # add a scale bar
        self.add_scalebar(ax, location=(0.05, 0.05),font_mod=font_mod)
        # add a title
        if title is not None:
            plt.title(title, fontsize=14*font_mod)
        
        return plt, ax

    ############################################################################################################

    def get_histogram(self, emp, office, commute_data, values, title=None, suptitle=None, value_label='', x_label='', y_label='', cutoff_radius=None, 
                    commute_radius=None, bins=10, rows=1, cols=1, figsize=(15, 15), column_titles=None, cumulative_line=False, cumulative_y_label="Cumulative %",
                    cumulative_color='black', cumulative_linestyle='--', cumulative_linewidth=1, cumulative_markers=False, cumulative_as_percentage=True,
                    font_mod=1, manual_plot=False, override_values=None, sharex=False, sharey=False):
        """
        Generates a histogram (or set of histograms) for specified commute data metrics for employee locations relative to a single office location.

        Args:
            emp (DataFrame): DataFrame containing employee locations with columns 'latitude' and 'longitude'.
            office (DataFrame): Single-row DataFrame representing the target office location.
            commute_data (DataFrame): DataFrame containing commute data metrics between employee locations and office locations.
            values (list of str): Names of the columns in `commute_data` representing the metrics to visualize in the histograms.
            title (str, optional): Main title for the histogram plot(s). Defaults to None.
            suptitle (str, optional): Supplementary title for the whole figure. Defaults to None.
            value_label (str, optional): Label for the metric values. Defaults to ''.
            x_label (str, optional): Label for the x-axis. Defaults to ''.
            y_label (str, optional): Label for the y-axis. Defaults to ''.
            cutoff_radius (float, optional): Radius in miles to include employee locations from the office for the histograms. Defaults to None.
            commute_radius (float, optional): Specifies the radius within which employees are considered for the histograms. Defaults to None.
            bins (int, optional): Number of bins for the histograms. Defaults to 10.
            rows (int, optional): Number of rows in the subplot grid. Defaults to 1.
            cols (int, optional): Number of columns in the subplot grid. Defaults to 1.
            figsize (tuple, optional): Figure size. Defaults to (15, 15).
            column_titles (list of str, optional): Titles for each subplot column. Defaults to None.
            cumulative_line (bool, optional): If True, add a cumulative percentage line to the histograms. Defaults to False.
            cumulative_y_label (str, optional): Label for the cumulative percentage y-axis. Defaults to "Cumulative %".
            cumulative_color (str, optional): Color for the cumulative line. Defaults to 'black'.
            cumulative_linestyle (str, optional): Line style for the cumulative line. Defaults to '--'.
            cumulative_linewidth (int, optional): Line width for the cumulative line. Defaults to 1.
            cumulative_markers (dict, optional): Dictionary specifying markers for specific cumulative percentages on the line. Format {%value(float or int): {style_arguments:values}}, not all values need to be present. Defaults to False.
            cumulative_as_percentage (bool, optional): If True, the cumulative line is displayed as a percentage. Defaults to True.
            font_mod (int, optional): Font size modifier for the plot. Defaults to 1.
            manual_plot (bool, optional): If True, returns the matplotlib plt and axes objects for manual plotting. Defaults to False.
            override_values (DataFrame, optional): DataFrame to override default values for the plot. Defaults to None.
            sharex (bool, optional): If True, share x-axis between subplots. Defaults to False.
            sharey (bool, optional): If True, share y-axis between subplots. Defaults to False.

        Returns:
            tuple: A tuple containing the matplotlib figure and axes objects.
        """

        """Cumulative Markers format: {%value(float or int): {style_arguments:values}} not all values need to be present"""
        # basic pre-filtering
        filtered_emp_points, latitudes, longitudes = self.plot_preamble(emp, office, cutoff_radius)
        if commute_radius is not None:
            # get the filtered_emp_points within the commute radius
            filtered_emp_points = self.filter_drive_distance(filtered_emp_points, office, commute_radius, commute_data)
        # if values is a string, it is one value to plot, if it is iterable, we get and plot multiple
        if isinstance(values, str):
            values = [values]

        # extract rows from commute_data where office is the destination and data aligns with the employee addresses provided
        # only the first row of office will be read, as it doesn't make sense to plot this for more than one on a heatmap
        if override_values is not None:
            xyz = override_values
        else:
            xyz = self.get_commute_values(filtered_emp_points, office, commute_data, values)

        fig, ax = plt.subplots(rows,cols,figsize=figsize, sharex=sharex, sharey=sharey)
        fig.tight_layout(pad=10,h_pad=1,w_pad=1)
        plt.suptitle(suptitle, fontsize=16*font_mod, y=.995)
        
        r=0
        c=0
        y_max = 0
        x_max = 0
        def axf(r,c,rows=rows, cols=cols):
            # if rows or cols is 1, ax is a 1D array, so we need to handle it differently
            # 1 row, 1 col, ax is a 1D array
            if rows == 1 and cols == 1:
                return ax
            # 1 row, multiple cols, ax is a 1D array
            elif rows == 1 and cols > 1:
                return ax[c]
            # multiple rows, 1 col, ax is a 1D array
            elif rows > 1 and cols == 1:
                return ax[r]
            # multiple rows, multiple cols, ax is a 2D array
            else:
                return ax[r,c]
            
        for i in range(0,len(values)):
            if rows > 1:
                r = i // cols
                c = i % cols
            else:
                r = 0
                c = i
            # set x label only for last row
            if r == rows-1:
                axf(r,c).set_xlabel(x_label, fontsize=14*font_mod)
            # set titles only for first row
            if r == 0 and column_titles is not None:
                axf(r,c).set_title(column_titles[i], fontsize=14*font_mod)
            # set y axis only for first col
            if c == 0 and r == 0:
                axf(r,c).set_ylabel(y_label, fontsize=14*font_mod)
            
            # if manually plotting, return the figure and axes
            if manual_plot:
                continue
        

            # give the bars a border for visibility
            axf(r,c).hist(xyz[values[i]], bins=bins, alpha=0.5, edgecolor='gray', linewidth=1, zorder=2, align='mid', rwidth=0.8)

            # set the xticks and yticks font size
            axf(r,c).tick_params(axis='both', labelsize=12*font_mod)
            

            # if cumulative line is requested, plot it
            if cumulative_line:
                twin = axf(r,c).twinx()
                twin.set_ylim(bottom=0)

                # add a cumulative percentage line to the other y axis
                count, edges = np.histogram(xyz[values[i]], bins)
                cumulative = np.cumsum(count)
                
                # get total cumulative for denominator to convert to percentage
                total = cumulative[-1]
                # convert to percentage
                if cumulative_as_percentage:
                    cumulative = cumulative / total * 100 
                
                # plot the cumulative line
                twin.plot(edges[1:], cumulative, color=cumulative_color, linestyle=cumulative_linestyle, 
                          linewidth=cumulative_linewidth, label=cumulative_y_label, zorder=0)

                # turn grid on relative to the twin y axis
                twin.grid(visible=True)
                # twin y ticks are percentage, set only for last column
                if c == cols-1 and r == 0:
                    twin.set_ylabel(cumulative_y_label,fontsize=14*font_mod)
                if cumulative_as_percentage:
                    # set ticks every 25%, only show on last col
                    twin.set_yticks(np.arange(0, 101, 25))
                # turn off twin y axis numbers for first col
                if c == 0:
                    twin.set_yticklabels([])
                
                # add markers to the cumulative line if requested
                if cumulative_markers is not False:
                    #cumulative_markers format: {%value: {'color': 'red', 'marker': 'o', 'label': '75%', linestyle="--"}} not all values need to be present
                    # we plot a vertical line at x where y=%value on the twin

                    # first get a polynomial fit to the cumulative percentage and find the x value where y is closest to %value
                    p = np.poly1d(np.polyfit(bins[1:], cumulative, 5))
                    
                    x = np.linspace(bins[0], bins[-1], 2000)
                    y = p(x)
                    
                    for key, value in cumulative_markers.items():
                        # get the x value where y is closest to key
                        xval = x[(np.abs(y-key)).argmin()]
                        # add the line with the style arguments
                        twin.axvline(x=xval, **value)
                        # insert a label at the top of the line
                        # get width of the plot
                        x_max = axf(r,c).get_xlim()[1]
                        x_min = axf(r,c).get_xlim()[0]
                        # calculate a delta for the label based on length                         
                        x_delta = ((x_max - x_min) / 100)*(1+0.25*len(str(int(xval))))
                        twin.text(xval-x_delta*2, 0.9*max(cumulative), int(xval), fontsize=13, ha='center', va='bottom', color=value['color'])

            # capture dimensionality for matching limits across cols/rows
            y_max = max(y_max, axf(r,c).get_ylim()[1])
            x_max = max(x_max, axf(r,c).get_xlim()[1])

        for i in range(0,len(values)):
            if manual_plot:
                continue
            if rows > 1:
                r = i // cols
                c = i % cols
            else:
                r = 0
                c = i
            axf(r,c).set_ylim(0, y_max)
            axf(r,c).set_xlim(0, x_max)
            #axf(r,c).set_xticks(np.arange(0, max(xyz[values[i]]), max(xyz[values[i]])/bins))
            

        #plt.xlabel(x_label)
        #plt.ylabel(y_label)
        
        return plt, ax
        
    ############################################################################################################

    def get_scatterplot(self, emp, office, commute_data, x_value, y_value, title=None, x_label='', y_label='', cutoff_radius=None, 
                    commute_radius=None, figsize=(15, 15), manual_plot=False, override_values=None, font_mod=1):
        """
        Generates a scatterplot for selected commute (or provided) data.
        """


        # basic pre-filtering
        filtered_emp_points, latitudes, longitudes = self.plot_preamble(emp, office, cutoff_radius)
        if commute_radius is not None:
            # get the filtered_emp_points within the commute radius
            filtered_emp_points = self.filter_drive_distance(filtered_emp_points, office, commute_radius, commute_data)

        # if values is a string, it is one value to plot, if it is iterable, we get and plot multiple
        
        if isinstance(x_value, str):
            x_value = [x_value]

        if isinstance(y_value, str):
            y_value = [y_value]

        
        if override_values is not None:
            xyz = override_values
        else:
            xyz = self.get_commute_values(filtered_emp_points, office, commute_data, x_value + y_value)
        
        fig, ax = plt.subplots(1,1,figsize=figsize)
        fig.tight_layout(pad=10,h_pad=1,w_pad=1)
        
        # set x label 
        ax.set_xlabel(x_label, fontsize=14*font_mod)
        # set title
        ax.set_title(title, fontsize=14*font_mod)
        # set y axis 
        ax.set_ylabel(y_label, fontsize=14*font_mod)
        
        # if manually plotting, return the figure and axes
        if manual_plot:
            return plt, ax

        # give the bars a border for visibility
        #axf(r,c).hist(xyz[values[i]], bins=bins, alpha=0.5, edgecolor='gray', linewidth=1, zorder=2, align='mid', rwidth=0.8)
        ax.scatter(x=xyz[x_value], y=xyz[y_value], alpha=0.5, edgecolor='gray', linewidth=1, zorder=2, s=10, c='blue')

        # set the xticks and yticks font size
        ax.tick_params(axis='both', labelsize=12*font_mod)
            
        
        return plt, ax
            
    def get_piechart(self, values, titles=None, suptitle=None, value_labels='', figsize=None, 
                     manual_plot=False, font_mod=1, rows=1, cols=1, startangle=90, colors=None):
        """
        Generates a pie chart or charts for selected commute data.

        Args:
            values (str or list): Names of the columns in `commute_data` representing the metrics to visualize in the pie chart(s).
            title (str, optional): Title for the pie chart(s). Defaults to None.
            suptitle (str, optional): Supplementary title for the whole figure. Defaults to None.
            value_labels (str or list, optional): Labels for the values in the pie chart(s). Defaults to ''.
            figsize (tuple, optional): Figure size. Defaults to None.
            manual_plot (bool, optional): If True, returns the matplotlib plt and axes objects for manual plotting. Defaults to False.
            font_mod (int, optional): Font size modifier for the plot. Defaults to 1.
            rows (int, optional): Number of rows in the subplot grid. Defaults to 1.
            cols (int, optional): Number of columns in the subplot grid. Defaults to 1.
            startangle (int, optional): Starting angle for the pie chart. Defaults to 90.
            colors (list, optional): List of colors for the pie chart. For multi-row/col, list of lists. Defaults to None.

        Returns:
            tuple: A tuple containing the matplotlib figure and axes objects.
        """
        # basic preamble
        if figsize is None:
            figsize = (5*rows, 5*cols)
            
        # if values is a string, it is one value to plot, if it is iterable, we get and plot multiple
        if isinstance(values, str):
            values = [values]
        
        if isinstance(value_labels, str):
            value_labels = [value_labels]

        if isinstance(titles, str):
            titles = [titles]

        fig, ax = plt.subplots(rows,cols,figsize=figsize)
        fig.tight_layout(pad=10,h_pad=1,w_pad=1)
        plt.suptitle(suptitle, fontsize=16*font_mod)
        
        r=0
        c=0
        def axf(r,c,rows=rows, cols=cols):
            # if rows or cols is 1, ax is a 1D array, so we need to handle it differently
            # 1 row, 1 col, ax is a 1D array
            if rows == 1 and cols == 1:
                return ax
            # 1 row, multiple cols, ax is a 1D array
            elif rows == 1 and cols > 1:
                return ax[c]
            # multiple rows, 1 col, ax is a 1D array
            elif rows > 1 and cols == 1:
                return ax[r]
            # multiple rows, multiple cols, ax is a 2D array
            else:
                return ax[r,c]

        for i in range(0,len(values)):
            if rows > 1:
                r = i // cols
                c = i % cols
            else:
                r = 0
                c = i
            # set title 
            axf(r,c).set_title(titles[i], fontsize=14*font_mod)
            # if manually plotting, return the figure and axes
            if manual_plot:
                continue
            # give the bars a border for visibility
            textprops={'fontsize': 14*font_mod}
            if colors is not None:
                axf(r,c).pie(values[i], labels=value_labels[i], autopct='%1.1f%%', shadow=True, startangle=startangle, colors=colors[i], textprops=textprops)
            else:
                axf(r,c).pie(values[i], labels=value_labels[i], autopct='%1.1f%%', shadow=True, startangle=startangle, textprops=textprops)
            axf(r,c).axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            axf(r,c).set_aspect('equal')


        return plt, ax
        

if __name__ == '__main__':

    # read lat long pairs in from employeegps file
    emp = pd.read_csv('../../projects/HQ_Analysis/gps_fuzz.csv', sep=';')
    offices = pd.read_csv('../../projects/HQ_Analysis/office_gps.csv', sep=';')
    commute_data = pd.read_csv('../../projects/HQ_Analysis/commute_data.csv', sep=';')
    graph = Graphing()
    #graph.plot()
    #graph.plot_map_view(emp,offices, cutoff_radius=80, commute_radius=50, commute_color=True)
    for index, row in offices.iterrows():
        office = offices.iloc[[index]]
        plt, ax = graph.get_map_view(emp, offices, commute_radius=50, commute_color=True, commute_data=commute_data, convex_hull=True)#,cutoff_radius=80)
        #plt, ax = graph.get_heatmap(emp, office, commute_data, 'emissions', title='m_morning_emissions', 
        #                            value_label='CO2 Emissions', cutoff_radius=40, commute_radius=50, convex_hull=True, plot_points=True, imagery="Google", cmap='gist_heat_r')
        #plt, ax = graph.get_heatmap(emp, office, commute_data, 'm_morning_emissions', title='m_morning_emissions', 
        #                            value_label='CO2 Emissions', cutoff_radius=40, commute_radius=50, convex_hull=True, plot_points=True, imagery="Google", cmap='gist_heat_r')
        #plt, ax = graph.get_heatmap(emp, office, commute_data, 'commute_cost', title='Per Commute Employee $ Impact', 
        #                            value_label='$/one way commute', cutoff_radius=40, commute_radius=50, convex_hull=True, plot_points=True, imagery="Google", cmap='autumn_r')
        #emp_within = graph.filter_drive_time(emp, office, 60, commute_data)
        #graph.plot_convex_hull(ax, emp_within, color='green')
        values = ['m_morning_duration_in_traffic','m_evening_duration_in_traffic',
                  't_morning_duration_in_traffic','t_evening_duration_in_traffic',
                  'w_morning_duration_in_traffic','w_evening_duration_in_traffic',
                  'h_morning_duration_in_traffic','h_evening_duration_in_traffic',
                  'f_morning_duration_in_traffic','f_evening_duration_in_traffic']
        cumulative_markers = {50: {'color': 'purple', 'marker': 'x', 'label': '50%', 'linestyle': '--', 'linewidth': 1},
                              75: {'color': 'blue', 'marker': 'x', 'label': '75%', 'linestyle': '--', 'linewidth': 1},}
        #plt.style.use('seaborn-v0_8-dark-palette')
        #print(plt.style.available)
        #plt = graph.get_histogram(emp, office, commute_data, values, cutoff_radius=40, bins=10, rows=5, cols=2, x_label='Minutes in Traffic', y_label='# of Employees')
        plt = graph.get_histogram(emp, office, commute_data, values, suptitle="Existing Commute Analysis", x_label='Minutes in Traffic', y_label='# Employees',  
                    commute_radius=50, bins=range(0,120,5), rows=5, cols=2, column_titles=['Morning Commute','Evening Commute'], cumulative_line=True,
                    cumulative_color='black', cumulative_linestyle='--', cumulative_linewidth=1, cumulative_markers=cumulative_markers)
        plt.legend(loc='center right')
        for each in plt.gcf().get_axes():
            # Add monday through Friday labels on first column only
            if each.get_subplotspec().colspan.start == 0:
                # first row is monday, second is tuesday, etc
                row = each.get_subplotspec().rowspan.start
                if row == 0:
                    each.text(0.02, 0.85, 'Monday', fontsize=10, transform=each.transAxes, ha='left', va='top')
                elif row == 1:
                    each.text(0.02, 0.85, 'Tuesday', fontsize=10, transform=each.transAxes, ha='left', va='top')
                elif row == 2:
                    each.text(0.02, 0.85, 'Wednesday', fontsize=10, transform=each.transAxes, ha='left', va='top')
                elif row == 3:
                    each.text(0.02, 0.85, 'Thursday', fontsize=10, transform=each.transAxes, ha='left', va='top')
                elif row == 4:
                    each.text(0.02, 0.85, 'Friday', fontsize=10, transform=each.transAxes, ha='left', va='top')
                    
        plt.show()
        break
    #graph.
    # plot_map_view(emp,offices, commute_radius=50)
    #main()