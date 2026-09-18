from django.shortcuts import render,redirect
from .models import LocationMarker
from django.http import JsonResponse
# Create your views here.
def map_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")

        if name and latitude and longitude:
            LocationMarker.objects.create(
                name=name,
                description=description,
                latitude=float(latitude),
                longitude=float(longitude),
            )
            return redirect("map_view")

    return render(request, "markers/map.html")

def marker_data(request):

    markers = LocationMarker.objects.all()

    features = []
    for marker in markers:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [marker.longitude, marker.latitude]
            },
            "properties": {
                "name": marker.name,
                "description": marker.description,
            },
        })

    geojson = {"type": "FeatureCollection", "features": features}

    return JsonResponse(geojson)

