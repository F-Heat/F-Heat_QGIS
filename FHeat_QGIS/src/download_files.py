import urllib.request
import ast
from zipfile import ZipFile
from io import BytesIO
import geopandas as gpd
import pandas as pd
import os
import shutil
from owslib.wfs import WebFeatureService
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QEventLoop, QUrl
    
def file_list_from_URL(url):
    '''lists downloadable files from given URL

    This function downloads the content from the specified URL, decodes the content,
    evaluates it as a dictionary, and extracts a list of files from all dataset entries.

    Parameters
    ----------
    url : str
        The URL from which to download and extract the file list.

    Returns
    -------
    list
        A list of files found in all entries under 'datasets'.
    '''
    filestring = ''
    for line in urllib.request.urlopen(url):
        d = line.decode('latin1')
        d = d.strip()
        filestring += d
    data_dict = ast.literal_eval(filestring)

    files = []
    for dataset in data_dict.get('datasets', []):
        files.extend(dataset.get('files', []))
    
    return files

def file_list_from_URL_QGIS(url: str):
    """
    Lists downloadable files from given URL using QgsNetworkAccessManager.

    Parameters
    ----------
    url : str
        The URL from which to download and extract the file list.

    Returns
    -------
    list
        A list of files found in all entries under 'datasets'.
    """
    nam = QgsNetworkAccessManager.instance()
    request = QNetworkRequest(QUrl(url))

    # Start the request
    reply = nam.get(request)

    # Event loop to wait for the reply (blocking)
    loop = QEventLoop()
    reply.finished.connect(loop.quit)
    loop.exec_()

    if reply.error():
        raise Exception(f"Network error: {reply.errorString()}")

    # Get data and decode
    data_bytes = reply.readAll()
    reply.deleteLater()

    # Deine ursprüngliche latin1-Dekodierung
    filestring = bytes(data_bytes).decode("latin1").strip()

    # In dict umwandeln
    data_dict = ast.literal_eval(filestring)

    # Dateien extrahieren
    files = []
    for dataset in data_dict.get("datasets", []):
        files.extend(dataset.get("files", []))

    return files

def search_filename(files, city_id):
    '''Searches for a city in a list of files and returns the file name.

    This function iterates through a list of file dictionaries, searching for the specified
    city identifier in the file names. The city identifier can be either a city name or a
    Gemeindeschlüssel. If a matching file is found, its name is returned; otherwise, a default
    message indicating that no file was found is returned.

    Parameters
    ----------
    files : list of dict
        A list of dictionaries, each representing a file with at least a 'name' key.
    city_id : str or int
        The city identifier to search for in the file names. This can be a city name or a
        Gemeindeschlüssel.

    Returns
    -------
    str
        The name of the file that contains the city identifier, or 'Keine Datei gefunden'
        if no matching file is found.
    '''
    file_name = 'No data found'
    for item in files:
        print(item)
        if str(city_id) in item['name']:
            file_name = item['name']
            break
    return file_name

def read_file_from_zip(url, zipfile, file_pattern, file_type='.shp', encoding='utf-8', delimiter = ';'):
    '''
    Reads a file (GeoDataFrame for shapefiles or DataFrame for CSV) from a downloadable zip file.

    This function downloads a zip file from a specified URL, extracts its contents,
    searches for a file matching a given pattern and file type (e.g., '.shp', '.gpkg', or '.csv'),
    and reads the file as either a GeoDataFrame (for spatial files) or a DataFrame (for CSV).
    It handles the extraction of files and cleans up temporary files afterward.

    Parameters
    ----------
    url : str
        The URL of the site where the zip file can be downloaded.
    zipfile : str
        The name of the zip file to be downloaded.
    file_pattern : str
        The pattern to search for in the file names within the zip file.
    file_type : str, optional
        The type of file to be read (e.g., '.shp', '.csv', '.gpkg'), by default '.shp'.
    encoding : str, optional
        The encoding to use when reading the file, by default 'utf-8'.

    Returns
    -------
    GeoDataFrame or DataFrame
        A GeoDataFrame if a shapefile or GeoPackage is found, or a DataFrame if a CSV is found.

    Examples
    --------
    >>> url = "http://example.com/files/"
    >>> zipfile = "data.zip"
    >>> file_pattern = "desired_file"
    >>> data = read_file_from_zip(url, zipfile, file_pattern, file_type='.csv')
    >>> data.head()
       column1  column2  column3
    0        1        2        3
    1        4        5        6

    Notes
    -----
    - The function supports both spatial files (e.g., '.shp', '.gpkg') and CSV files.
    - Temporary files are extracted to '/tmp/extracted_zip' and cleaned up after reading.
    - The file type must be specified via the 'file_type' argument, which defaults to '.shp'.
    '''
    with urllib.request.urlopen(url + zipfile) as response:
        with ZipFile(BytesIO(response.read())) as my_zip_file:
            # Create a temporary directory
            temp_dir = '/tmp/extracted_zip'
            os.makedirs(temp_dir, exist_ok=True)

            # Extract the entire Zip archive to the temporary directory
            my_zip_file.extractall(temp_dir)
            
            # search matching file
            file_list = my_zip_file.namelist()

            matching_files = [file for file in file_list if 
                                file_pattern in file and file.endswith(file_type)]

            file = matching_files[0]

            # check file type
            if file_type in ['.shp','.gpkg']:
                # Read the shapefile directly from the extracted directory
                data = gpd.read_file(os.path.join(temp_dir, file), encoding=encoding)
            elif file_type == '.csv':
                # Read csv as pd.Dataframe
                data = pd.read_csv(os.path.join(temp_dir, file), encoding=encoding, delimiter = delimiter)

            # Clean up: Remove the temporary directory
            shutil.rmtree(temp_dir)
    return data

def read_file_from_zip_QGIS(url, zipfile, file_pattern, file_type='.shp', encoding='utf-8', delimiter=';'):
    """
    Reads a file (GeoDataFrame for shapefiles or DataFrame for CSV) from a downloadable zip file
    using QgsNetworkAccessManager (QGIS compatible).
    """

    # Download file 
    nam = QgsNetworkAccessManager.instance()
    request = QNetworkRequest(QUrl(url + zipfile))
    reply = nam.get(request)

    loop = QEventLoop()
    reply.finished.connect(loop.quit)
    loop.exec_()

    if reply.error():
        raise Exception(f"Network error: {reply.errorString()}")

    zip_bytes = reply.readAll()
    reply.deleteLater()

    # Extract zip to temp folder
    temp_dir = '/tmp/extracted_zip'
    os.makedirs(temp_dir, exist_ok=True)

    with ZipFile(BytesIO(bytes(zip_bytes))) as my_zip_file:
        my_zip_file.extractall(temp_dir)

        # search matching file
        file_list = my_zip_file.namelist()
        matching_files = [
            file for file in file_list
            if file_pattern in file and file.endswith(file_type)
        ]

        if not matching_files:
            shutil.rmtree(temp_dir)
            raise FileNotFoundError(f"No file matching {file_pattern}{file_type} found in archive.")

        file = matching_files[0]

        # Read file depending on type
        if file_type in ['.shp', '.gpkg']:
            data = gpd.read_file(os.path.join(temp_dir, file), encoding=encoding)
        elif file_type == '.csv':
            data = pd.read_csv(os.path.join(temp_dir, file), encoding=encoding, delimiter=delimiter)
        else:
            shutil.rmtree(temp_dir)
            raise ValueError(f"Unsupported file type: {file_type}")

    # Cleanup
    shutil.rmtree(temp_dir)
    return data

def filter_df(name, dataframe, parameter):
    '''
    Searches a DataFrame for a city name .

    This function filters a given DataFrame based on a specified parameter ('city' or 'gemeinde')
    and searches for an exact match of the provided name. If a match is found, a new DataFrame
    containing the matching rows is returned; otherwise, a message is printed and None is returned.

    Parameters
    ----------
    name : str
        The name (city or municipality name) to search for in the DataFrame.
    dataframe : pandas.DataFrame
        The DataFrame to search within.
    parameter : str
        Specifies whether to search by 'city' (for city name) or 'gemeinde' (for municipality name).

    Returns
    -------
    pandas.DataFrame or None
        A DataFrame containing rows matching the specified name and parameter, or None if no match is found.
    '''
    if parameter.lower() == 'city':
        col = 'name'
    else:
        col = 'gemeinde'
    try:
        df = dataframe.loc[dataframe[col] == name].reset_index(drop=True)
        return df
    except :
        print(f'{name} not found')
        return None

def get_shape_from_wfs(wfs_url, key, bbox, layer_name):
    '''
    Loads shapefiles within a bounding box from a WFS service and filters for 'key'.

    This function connects to a Web Feature Service (WFS), retrieves shapefiles within a specified
    bounding box, and filters the shapefiles based on the given key (Gemeinde or Gemarkung). If the
    number of features exceeds 100,000, a warning is printed.

    Parameters
    ----------
    wfs_url : str
        The URL of the WFS service.
    key : str
        The key for filtering (e.g., Gemeinde or Gemarkung).
    bbox : tuple
        The bounding box for filtering in the format (minx, miny, maxx, maxy).
    layer_name : str
        The name of the layer containing the desired shapes.

    Returns
    -------
    GeoDataFrame
        A GeoDataFrame containing the filtered shapes.
    int or None
        An exception flag. If the number of features exceeds 100,000, returns 1; otherwise, None.

    Examples
    --------
    >>> wfs_url = "http://example.com/wfs"
    >>> key = "123"
    >>> bbox = (10.0, 50.0, 10.5, 50.5)
    >>> layer_name = "example_layer"
    >>> shapes, exception = get_shape_from_wfs(wfs_url, key, bbox, layer_name)
    >>> shapes.head()
       nationalCadastralReference  geometry
    0                        1234  POINT (10.00000 50.00000)
    1                        1235  POINT (10.10000 50.10000)

    Notes
    -----
    The function assumes that the WFS service supports version 2.0.0 and returns data in 'text/xml' format.
    If the bounding box contains more than 100,000 features, a warning is printed, and the returned
    GeoDataFrame may be incomplete.
    '''
    # Connect to the WFS service
    wfs = WebFeatureService(wfs_url, version='2.0.0')

    # Retrieve the layer attributes as a GeoDataFrame
    response = wfs.getfeature(typename=layer_name, outputFormat='text/xml', bbox=bbox)

    # Reset the position of the BytesIO object for GeoPandas to read it
    response.seek(0)

    # Read the BytesIO object with GeoPandas
    gdf = gpd.read_file(response)

    # Warn if too many features are within the bounding box
    exception = None
    if len(gdf)>=100000:
        print('The selected area contains over 100,000 parcels! As the WFS service transmits only 100,000 features per request, some parcels may be missing.')
        exception = 1

    # Select features based on the key
    selected_rows = gdf[gdf['nationalCadastralReference'].str.startswith(key)].reset_index(drop=True)
    return selected_rows, exception


def clean_data(df):
    '''
    Cleans the DataFrame by replacing invalid characters.

    This method replaces specific invalid characters in the given DataFrame with valid alternatives. 
    The following replacements are made:
    - '\x96' and '' are replaced with '-'.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to clean.

    Returns
    -------
    pd.DataFrame
        The cleaned DataFrame with invalid characters replaced.
    '''
    df.replace({'\x96': '-', 'â': '-', '': '-'}, regex=True, inplace=True)
    return df

def add_point(df):
    '''
    Adds a point geometry to the DataFrame based on X and Y coordinates.

    This method creates a 'point' column in the DataFrame by generating Point geometries 
    from the 'X_MP_100m' and 'Y_MP_100m' coordinate columns.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the 'X_MP_100m' and 'Y_MP_100m' columns representing 
        the X and Y coordinates of the points.

    Returns
    -------
    pd.DataFrame
        The DataFrame with an additional 'point' column containing the Point geometries.
    '''
    df['point'] = df.apply(lambda row: Point(row['x_mp_100m'], row['y_mp_100m']), axis=1)
    return df

def create_square(point, size):
    '''
    Creates a square polygon around a given point with a specified size.

    This method generates a square-shaped polygon centered on the provided point. 
    The square's side length is determined by the size parameter, and the square is 
    oriented parallel to the axes.

    Parameters
    ----------
    point : shapely.geometry.Point
        The central point around which the square will be created. It should have 'x' and 'y' coordinates.
    size : float
        The total side length of the square.

    Returns
    -------
    shapely.geometry.Polygon
        A square-shaped polygon centered around the input point.
    '''
    x, y = point.x, point.y
    half_size = size / 2
    return Polygon([
        (x - half_size, y - half_size),
        (x + half_size, y - half_size),
        (x + half_size, y + half_size),
        (x - half_size, y + half_size)
    ])

def get_area_for_zensus(df):
    # Prüfe, ob die 'bbox'-Spalte existiert und konvertiere sie zu Polygonen
    if 'bbox' in df.columns:
        df['bbox'] = df['bbox'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
        df['geometry'] = df['bbox'].apply(lambda bbox: box(*bbox))

    # Erstelle ein GeoDataFrame mit der 'geometry'-Spalte
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:25832')

    # Transformation der Koordinaten in EPSG:3035
    gdf_3035 = gdf.to_crs(epsg=3035)

    # Berechne die geometrische Vereinigung aller Geometrien
    combined_geometry = unary_union(gdf_3035['geometry'])

    # Extrahiere die Bounding Box der vereinten Geometrie
    overall_bbox = combined_geometry.bounds  # Dies liefert die Bounding Box als Tupel (minx, miny, maxx, maxy)

    return overall_bbox, combined_geometry