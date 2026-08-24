import json
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

BASE = "https://mapservices.weather.noaa.gov/tropical/rest/services/tropical/NHC_tropical_weather_summary/MapServer"

POINT_LAYER = 2
POLYGON_LAYER = 3

OUTPUT = "nhc_atlantic.kml"


def get_geojson(layer):
    params = {
        "where": "basin='Atlantic'",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson"
    }

    url = f"{BASE}/{layer}/query?" + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url) as response:
        return json.load(response)


def probability(props):
    value = props.get("prob7day", "0%")
    try:
        return int(str(value).replace("%", ""))
    except:
        return 0


def style_id(prob):
    if prob >= 70:
        return "high"
    if prob >= 40:
        return "medium"
    return "low"


def polygon_coordinates(coords):
    output = []

    # Polygon rings
    for ring in coords:
        output.append(
            " ".join(f"{lon},{lat},0" for lon, lat in ring)
        )

    return output


points = get_geojson(POINT_LAYER)
polygons = get_geojson(POLYGON_LAYER)

kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>

<name>NHC Atlantic Tropical Weather Outlook</name>

<Style id="low">
    <IconStyle>
        <color>ff00ffff</color>
        <scale>1.5</scale>
        <Icon>
            <href>https://maps.google.com/mapfiles/kml/shapes/cross-hairs.png</href>
        </Icon>
    </IconStyle>
    <LineStyle>
        <color>ff00ffff</color>
        <width>3</width>
    </LineStyle>
    <PolyStyle>
        <color>5500ffff</color>
    </PolyStyle>
</Style>

<Style id="medium">
    <IconStyle>
        <color>ff0099e6</color>
        <scale>1.5</scale>
        <Icon>
            <href>https://maps.google.com/mapfiles/kml/shapes/cross-hairs.png</href>
        </Icon>
    </IconStyle>
    <LineStyle>
        <color>ff0099e6</color>
        <width>3</width>
    </LineStyle>
    <PolyStyle>
        <color>550099e6</color>
    </PolyStyle>
</Style>

<Style id="high">
    <IconStyle>
        <color>ff0000e6</color>
        <scale>1.5</scale>
        <Icon>
            <href>https://maps.google.com/mapfiles/kml/shapes/cross-hairs.png</href>
        </Icon>
    </IconStyle>
    <LineStyle>
        <color>ff0000e6</color>
        <width>3</width>
    </LineStyle>
    <PolyStyle>
        <color>550000e6</color>
    </PolyStyle>
</Style>
"""

# Development areas
for feature in polygons.get("features", []):
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})

    prob = probability(props)
    style = style_id(prob)

    risk2 = escape(str(props.get("risk2day", "")))
    risk7 = escape(str(props.get("risk7day", "")))
    prob2 = escape(str(props.get("prob2day", "")))
    prob7 = escape(str(props.get("prob7day", "")))

    geometry_type = geom.get("type")
    coordinates = geom.get("coordinates", [])

    polygon_sets = coordinates if geometry_type == "MultiPolygon" else [coordinates]

    for polygon in polygon_sets:
        rings = polygon_coordinates(polygon)

        if not rings:
            continue

        outer = rings[0]

        kml += f"""
<Placemark>
    <name>7-Day Formation Chance: {prob7}</name>
    <description>
        2-Day Probability: {prob2}
        2-Day Risk: {risk2}
        7-Day Probability: {prob7}
        7-Day Risk: {risk7}
    </description>
    <styleUrl>#{style}</styleUrl>
    <Polygon>
        <outerBoundaryIs>
            <LinearRing>
                <coordinates>{outer}</coordinates>
            </LinearRing>
        </outerBoundaryIs>
"""

        for inner in rings[1:]:
            kml += f"""
        <innerBoundaryIs>
            <LinearRing>
                <coordinates>{inner}</coordinates>
            </LinearRing>
        </innerBoundaryIs>
"""

        kml += """
    </Polygon>
</Placemark>
"""


# Current disturbance locations
for feature in points.get("features", []):
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})

    if geom.get("type") != "Point":
        continue

    lon, lat = geom["coordinates"][:2]

    prob = probability(props)
    style = style_id(prob)

    prob2 = escape(str(props.get("prob2day", "")))
    prob7 = escape(str(props.get("prob7day", "")))
    risk2 = escape(str(props.get("risk2day", "")))
    risk7 = escape(str(props.get("risk7day", "")))

    kml += f"""
<Placemark>
    <name>Disturbance — {prob7}</name>
    <description>
        2-Day Probability: {prob2}
        2-Day Risk: {risk2}
        7-Day Probability: {prob7}
        7-Day Risk: {risk7}
    </description>
    <styleUrl>#{style}</styleUrl>
    <Point>
        <coordinates>{lon},{lat},0</coordinates>
    </Point>
</Placemark>
"""


kml += """
</Document>
</kml>
"""

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(kml)

print(f"Created {OUTPUT}")
