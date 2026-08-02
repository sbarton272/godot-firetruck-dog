# Overpass GeoJson

Ran this query on https://overpass-turbo.eu:

```
[out:json][timeout:60]
[bbox:51.7808,-2.2023,51.7898,-2.1877];

(
  // 1. ROADS & PATHS
  way["highway"];
  
  // 2. BUILDINGS & STRUCTURES
  way["building"];
  relation["building"];
  
  // 3. WATERWAYS & HYDROLOGY
  nwr["waterway"];
  nwr["natural"="water"];
  
  // 4. UTILITIES & POWER GRID
  nwr["power"];
  nwr["man_made"~"pipeline|substation|tower|water_works"];
  
  // 5. PERMANENT BARRIERS & ENGINEERING
  way["barrier"~"wall|retaining_wall|hedge|fence"];
  way["bridge"="yes"];
  way["tunnel"="yes"];

  // 6. HISTORIC & CULTURAL HERITAGE
  nwr["historic"];
  
  // 7. LAND USE & FIELDS (Farmland, Meadows, Orchards, Churchyard)
  way["landuse"~"farmland|meadow|grass|farmyard|forest|orchard|cemetery"];
  relation["landuse"~"farmland|meadow|grass|farmyard|forest|orchard|cemetery"];
  
  // 8. NATURAL TERRAIN & WOODLANDS
  nwr["natural"~"wood|scrub|heath|cliff|peak|rock"];
);

// Output geometries
out body;
>;
out skel qt;
```