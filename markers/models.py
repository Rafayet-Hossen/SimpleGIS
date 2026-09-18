from django.db import models

# Create your models here.
class LocationMarker(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    latitude = models.FloatField(help_text="Latitude in degrees (-90 to 90)")
    longitude = models.FloatField(help_text="Longitude in degrees (-180 to 180)")
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.name