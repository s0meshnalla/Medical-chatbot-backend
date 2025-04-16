import requests
import time
from datetime import datetime

def clinic_locator(user_location: str) -> list:
    """Find nearby clinics and hospitals using OpenStreetMap APIs"""
    try:
        time.sleep(1)  # Respect API rate limits
        print(f"Geocoding: {user_location}")
        
        # Step 1: Convert location to coordinates using Nominatim
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": user_location, 
            "format": "jsonv2", 
            "addressdetails": 1, 
            "limit": 1
        }
        headers = {"User-Agent": "MedicalSymptomChatbot/1.0"}
        
        response = requests.get(url, params=params, headers=headers)
        if response.status_code != 200:
            print(f"Nominatim error: Status {response.status_code} - {response.text}")
            return [{"error": f"Location service error: {response.status_code}"}]
            
        data = response.json()
        if not data:
            print("Geocoding failed: No results")
            return [{"error": "Location not found. Please try a different location."}]
            
        lat, lng = float(data[0]["lat"]), float(data[0]["lon"])
        print(f"Coordinates: lat={lat}, lon={lng}")
        
        # Step 2: Find medical facilities using Overpass API
        overpass_url = "https://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json];
        node["amenity"~"hospital|clinic|doctors|pharmacy"](around:5000,{lat},{lng});
        out body;
        """
        
        response = requests.post(overpass_url, data=overpass_query, headers=headers)
        if response.status_code != 200:
            print(f"Overpass error: Status {response.status_code}")
            return [{"error": "Medical facility search failed"}]
            
        data = response.json()
        clinics = []
        
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            clinic = {
                "name": tags.get("name", "Unnamed Facility"),
                "type": tags.get("amenity"),
                "lat": element.get("lat"),
                "lon": element.get("lon"),
                "address": ", ".join([
                    tags.get("addr:housenumber", ""),
                    tags.get("addr:street", ""),
                    tags.get("addr:city", "")
                ]).strip(", ")
            }
            clinics.append(clinic)
        
        # Sort by proximity
        clinics = sorted(clinics, key=lambda x: 
            (x["lat"] - lat)**2 + (x["lon"] - lng)**2)[:10]
        
        if not clinics:
            return [{"error": "No medical facilities found in this area"}]
            
        print(f"Found {len(clinics)} clinics/hospitals")
        return clinics
        
    except Exception as e:
        print(f"Locator error: {str(e)}")
        return [{"error": f"Failed to locate facilities: {str(e)}"}]
