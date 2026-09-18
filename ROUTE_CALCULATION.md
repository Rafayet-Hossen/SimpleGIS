# Route & Distance Calculation Guide: `handleMarkerSelect`

This document details the architecture, workflow, routing mathematics, and implementation details of the two-point distance calculation and routing feature implemented in `markers/templates/markers/map.html`.

---

## 1. Overview

The `handleMarkerSelect` function provides an interactive GIS measurement tool that allows users to:

1. Select a starting location pin (**Point A**).
2. Select a destination location pin (**Point B**).
3. Automatically calculate and visualize:
   - **Actual Driving Road Distance** (in kilometers) via road networks.
   - **Estimated Driving Travel Time** (in minutes).
   - **Turn-by-turn road route path** rendered directly on the Leaflet map.
   - **Straight-line (geodesic) fallback** if an offline/unroutable situation occurs.

```
+-------------------+       Click Marker A       +------------------------------+
|   Marker Layer    | ------------------------> | Record Point A & Show Badge  |
+-------------------+                           +------------------------------+
                                                               |
                                                        Click Marker B
                                                               |
                                                               v
                                                +------------------------------+
                                                | Record Point B & Show Status |
                                                +------------------------------+
                                                               |
                                            +------------------+------------------+
                                            |                                     |
                                            v                                     v
                                   [OSRM Driving API]                     [Leaflet Haversine]
                                            |                                     |
                                     (Network Success)                     (Fallback Mode)
                                            |                                     |
                                            v                                     v
                              Render GeoJSON Road Path                Render Dashed Polyline
                                            |                                     |
                                            +------------------+------------------+
                                                               |
                                                               v
                                                +------------------------------+
                                                |  Fit Map Bounds to Viewport  |
                                                |  Open Center Distance Popup  |
                                                +------------------------------+
```

---

## 2. State Management & Lifecycle

Three script-scoped variables govern the selection workflow:

| Variable          | Type                                  | Purpose                                                            |
| :---------------- | :------------------------------------ | :----------------------------------------------------------------- |
| `selectedMarkers` | `Array`                               | Holds up to 2 marker objects: `{ name, latlng, layer }`.           |
| `routeLayer`      | `L.GeoJSON` \| `L.Polyline` \| `null` | Active map layer showing the road route or straight line.          |
| `distancePopup`   | `L.Popup` \| `null`                   | Informational popup positioned at the midpoint between the points. |

### Step-by-Step Lifecycle

1. **Selection Reset (On First Click)**:
   When `selectedMarkers.length === 0`, any previous route (`routeLayer`), midpoint popup (`distancePopup`), and marker labels are removed from the map.

2. **Selecting Point A**:
   - The clicked marker is added to `selectedMarkers`.
   - A permanent tooltip badge is bound to the top of Marker A:  
     `<strong>Start (A):</strong> <Name>`.
   - Any default info popup bound to the marker is closed (`markerLayer.closePopup()`) to keep the visual presentation tidy.

3. **Deselection (Toggle Behavior)**:
   If the user clicks the same marker that is already selected as Point A, the function unbinds the tooltip and clears `selectedMarkers = []`.

4. **Selecting Point B**:
   - The second marker is pushed to `selectedMarkers`.
   - Its tooltip is updated to `<strong>End (B):</strong> Calculating distance...`.
   - Routing and distance calculations are initiated.

5. **Resetting for the Next Measurement**:
   In the `.finally()` block, `selectedMarkers` is reset to `[]`. This enables the user to select another pair immediately on their next click without needing a separate reset button.

---

## 3. How Routes & Distances Are Calculated

### A. Road Network Routing via OSRM (Primary Engine)

To calculate real-world drivable road routes, the function queries the **Open Source Routing Machine (OSRM)** public routing API.

#### 1. Coordinate Order Requirement

- **Leaflet** represents coordinates as `(Latitude, Longitude)` or `[lat, lng]`.
- **OSRM** and the GeoJSON standard expect coordinates in **`(Longitude, Latitude)`** order (Cartesian `[x, y]`).

The query URL is constructed accordingly:

```javascript
const url = `https://router.project-osrm.org/route/v1/driving/${p1.latlng.lng},${p1.latlng.lat};${p2.latlng.lng},${p2.latlng.lat}?overview=full&geometries=geojson`;
```

#### 2. Query Parameters

- `/route/v1/driving/`: Requests automobile/car driving profile routing.
- `overview=full`: Returns the full vector geometry of the entire route rather than a simplified summary.
- `geometries=geojson`: Returns the route polyline in native GeoJSON `LineString` format.

#### 3. API Response Processing

When OSRM responds, the payload includes:

- `route.distance`: Total route length in **meters**.
  $$\text{Distance (km)} = \frac{\text{route.distance}}{1000}$$
- `route.duration`: Estimated travel time in **seconds**.
  $$\text{Duration (mins)} = \left\lfloor \frac{\text{route.duration}}{60} + 0.5 \right\rfloor$$
- `route.geometry`: GeoJSON `LineString` with all the coordinates of the route along actual streets.

#### 4. Rendering the Road

The geometry is added to the Leaflet map as a vector GeoJSON layer:

```javascript
routeLayer = L.geoJSON(route.geometry, {
  style: {
    color: "#2563eb", // Tailwind blue-600
    weight: 5,
    opacity: 0.85,
  },
}).addTo(map);
```

The camera view automatically pans and zooms to fit the entire route using:

```javascript
map.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });
```

---

### B. Straight-Line Geodesic Distance (Fallback Engine)

If the device is offline, OSRM is rate-limited, or the selected points are disconnected (e.g., across bodies of water with no bridge or on separate islands), the function falls back to Leaflet's native distance calculation.

#### 1. Haversine / Great-Circle Distance

Leaflet provides built-in great-circle spherical distance via `latlng.distanceTo(otherLatLng)`:

```javascript
const straightDistanceMeters = p1.latlng.distanceTo(p2.latlng);
const straightDistanceKm = (straightDistanceMeters / 1000).toFixed(2);
```

This uses the Haversine formula on an Earth radius approximation ($R \approx 6,371,000 \text{ m}$):
$$d = 2R \arcsin \left( \sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)} \right)$$
where $\phi$ is latitude and $\lambda$ is longitude in radians.

#### 2. Drawing the Direct Route

A dashed blue polyline directly connects Point A and Point B:

```javascript
routeLayer = L.polyline([p1.latlng, p2.latlng], {
  color: "#2563eb",
  weight: 4,
  dashArray: "6, 8",
  opacity: 0.85,
}).addTo(map);
```

---

## 4. Midpoint Display Popup

Once the distance is determined, a popup is anchored at the geographic midpoint:

$$\text{lat}_{\text{mid}} = \frac{\text{lat}_1 + \text{lat}_2}{2}, \quad \text{lng}_{\text{mid}} = \frac{\text{lng}_1 + \text{lng}_2}{2}$$

The popup displays:

1. Point names: `Point A ➔ Point B`
2. Road driving distance in `km` (or direct distance if fallback was used)
3. Estimated driving duration in `mins`
4. Reference straight-line distance

```javascript
distancePopup = L.popup({ closeOnClick: false })
  .setLatLng([midLat, midLng])
  .setContent(
    `
    <div style="text-align: center; min-width: 170px;">
      <strong style="color: #1e293b;">${p1.name} ➔ ${p2.name}</strong><br>
      <div style="font-size: 1.2rem; color: #2563eb; font-weight: bold; margin: 4px 0;">
        🚗 ${roadDistanceKm} km
      </div>
      <span style="color: #64748b; font-size: 0.85rem;">
        Est. Driving Time: ~${durationMinutes} mins
      </span>
      <div style="color: #94a3b8; font-size: 0.75rem; margin-top: 4px;">
        Straight-line: ${straightDistanceKm} km
      </div>
    </div>
  `,
  )
  .openOn(map);
```

---

## 5. Event Propagation Prevention

In `markers/templates/markers/map.html`, clicking on the map coordinates input form listener is hooked to `map.on("click", ...)`.

To prevent clicking an existing marker from also moving the draft pin (`tempMarker`) and overwriting form coordinates, event propagation is stopped:

```javascript
layer.on("click", function (e) {
  L.DomEvent.stopPropagation(e);
  handleMarkerSelect(layer, name);
});
```

This isolates the marker selection interaction from the normal map click-to-pin interaction.

---

## 6. Summary of Key Files

- **Template**: [`markers/templates/markers/map.html`](file:///home/rafayet/Documents/simple-gis/markers/templates/markers/map.html)
  - Implements `handleMarkerSelect` and coordinates UI tooltips, Leaflet layers, and OSRM API calls.
- **Views**: [`markers/views.py`](file:///home/rafayet/Documents/simple-gis/markers/views.py)
  - Provides `map_view` (renders map page) and `marker_data` (outputs GeoJSON FeatureCollection for all saved pins).
- **Settings**: [`config/settings.py`](file:///home/rafayet/Documents/simple-gis/config/settings.py)
  - Configures `STATICFILES_DIRS = [BASE_DIR / "node_modules"]` to serve Leaflet assets locally.
