"""
WhatsApp AI agent for CampAlly.
Powered by Claude (Anthropic) with Groq as fallback.
"""

import json
import math
import traceback
import urllib.request
import urllib.parse
import os

import anthropic as _anthropic
from groq import Groq as _Groq, BadRequestError as _BadRequest, RateLimitError as _RateLimitError

from .models import (
    ParkingZone,
    EmergencyReport,
    EmergencyTimeline,
    LostFoundReport,
    WhatsAppUser,
)

CLAUDE_MODEL = "claude-sonnet-4-6"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# Anthropic tool schema (input_schema instead of parameters)
CLAUDE_TOOLS = [
    {
        "name": "get_available_parking",
        "description": "List the camp's car parks with how many spots are free right now.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "find_nearest_open_zone",
        "description": "Find the closest open car park to the user's shared WhatsApp location.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "report_emergency",
        "description": "File an emergency report so security/medics are alerted on the dashboard.",
        "input_schema": {
            "type": "object",
            "properties": {
                "emergency_type": {"type": "string", "enum": ["medical","fire","security","missing","traffic","stampede","other"]},
                "description":    {"type": "string"},
                "location_name":  {"type": "string"},
            },
            "required": ["emergency_type", "description"],
        },
    },
    {
        "name": "report_lost_found",
        "description": "File a lost or found person/item report.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category":    {"type": "string", "enum": ["lost_person","found_person","lost_item","found_item"]},
                "title":       {"type": "string"},
                "description": {"type": "string"},
                "location":    {"type": "string"},
            },
            "required": ["category", "title", "description"],
        },
    },
    {
        "name": "save_user_name",
        "description": "Save the user's name. Call as soon as the user tells you their name.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "find_nearby_places",
        "description": "Find hotels, restaurants, hospitals, ATMs etc. near a camp landmark.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location_name": {"type": "string"},
                "place_type":    {"type": "string"},
            },
            "required": ["location_name", "place_type"],
        },
    },
    {
        "name": "save_location",
        "description": (
            "Save the user's current GPS position or a named place so they can find it later. "
            "Call this when the user says things like 'save my location', 'remember this spot', "
            "'save this as my car', 'bookmark this place'. "
            "Use the lat/lng from ctx if the user just shared their GPS, otherwise use place_name."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "label":      {"type": "string", "description": "Short name for the place, e.g. 'my car', 'prayer tent', 'gate B'"},
                "place_name": {"type": "string", "description": "Descriptive name if no GPS available"},
            },
            "required": ["label"],
        },
    },
    {
        "name": "get_saved_location",
        "description": (
            "Retrieve a previously saved location and return directions. "
            "Call this when the user says 'take me back', 'I\\'m lost', 'find my saved spot', "
            "'where did I save', 'where is my car', 'where was I before'. "
            "If label is empty, list all saved locations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "Name of the saved location to retrieve. Leave empty to list all."},
            },
            "required": [],
        },
    },
]

SYSTEM_PROMPT = """You are CampAlly, the WhatsApp assistant for Redemption City \
(the Redeemed Christian Church of God camp on the Lagos-Ibadan Expressway).

FIRST MESSAGE RULE:
- If the system note says the user's name is ALREADY KNOWN, skip the intro. \
Just greet them briefly by name and ask how you can help. Example: \
"Welcome back [Name]! 👋 How can I help you today?"
- If this is a BRAND NEW user (no name in system note), introduce yourself, \
list your services, then ask for their name. Use this template (adapt freely):

"👋 Hi! I'm *CampAlly*, your smart guide at Redemption City 🏕️

Here's what I can help you with:
🚗 *Parking* — find available spots or share your 📍 location and I'll \
route you to the nearest open park
🗺️ *Nearby places* — hotels, restaurants, ATMs, hospitals and more
🚨 *Emergencies* — instantly alert the control room for any crisis
📝 *Lost & Found* — file or search for lost people or items

May I know your name so I can assist you better? 😊"

NAME RULE: As soon as the user tells you their name, call save_user_name \
immediately. Then greet them by name and ask how you can help. \
If the system note says their name is already known, use it \
naturally in replies (e.g. "Sure [Name]!", "On it [Name] 👍") — \
warm but not excessive.

You help visitors with four things:
1. PARKING — find available car parks and route them to the nearest open one. \
The camp's car parks include Car Park A, B and C (Old Auditorium; Car Park C is \
the famous expressway-entrance landmark), Car Park D (National Youth Centre), \
Car Park F (conventions), Car Park V and the New Arena Parking (New Auditorium), \
and Odofin Car Park. Occupancy is detected live by AI cameras.
2. NEARBY PLACES — find hotels, restaurants, hospitals, ATMs, pharmacies, \
supermarkets and more near any camp landmark. Use find_nearby_places whenever \
the user asks what is near a location (e.g. "hotels near the main gate", \
"restaurants near new arena", "ATM near car park B").
3. EMERGENCIES — Detect ANY distress signal — not just the word "emergency". \
Trigger the emergency interview whenever the user says anything that sounds like \
danger, pain, fear, or crisis. Examples (including typos/pidgin/shorthand): \
"help", "help me", "sos", "danger", "fire", "bleeding", "faint", "fainted", \
"collapsed", "colapsed", "someone down", "person down", "accident", "crash", \
"missing child", "lost child", "i cant breathe", "cant breath", "chest pain", \
"heart attack", "heatstroke", "heat stroke", "stampede", "crowd crush", \
"fight", "attack", "thief", "robber", "armed", "bomb", "smoke", "burning", \
"please help", "abeg help", "help us", "save us", "somebody help", \
"person don fall", "e don fall", "she faint", "he faint", "we need help", \
"na emergency", "emergency dey", "wahala", "big wahala". \
When in doubt — if the message sounds like distress, treat it as an emergency.

   You MUST ask all 3 questions ONE AT A TIME before calling \
report_emergency. Never skip unless the message contains EXTREME urgency \
like "dying now", "fire now", "bleeding out", "unconscious".

   EMERGENCY INTERVIEW (ask each question in a separate reply, wait for answer):
   Step 1 — Send ONLY: "🚨 *What is the emergency?*\n\nPlease describe what's \
happening (e.g. medical, fire, security threat, missing child, accident, \
stampede)."
   Step 2 — Send ONLY: "📍 *Where exactly is this happening?*\n\nTell me the \
location (e.g. Car Park B, main gate, New Arena, Old Auditorium, Odofin road)."
   Step 3 — Send ONLY: "🆘 *Is anyone with you or nearby who can help right \
now?* (reply *yes* or *no*)"
   After the user answers Step 3 (anything about whether help is nearby), \
you MUST call report_emergency with all the info gathered so far, then reply: \
"🚨 *SOS ALERT SENT!* The control room has been notified and help is on the \
way. Stay on the line. If the situation worsens call *112* or shout for help." \
Do NOT ask any more questions after Step 3 — file the report immediately.

TYPOS & SPELLING: Users may type quickly or panic. Always interpret messages \
charitably — "emergancy", "emergensy", "emrgency" all mean emergency. \
"hspital", "hosptal" mean hospital. "pak", "pakr", "pakring" mean parking. \
Never reject a message because of spelling — always understand the intent.
4. LOST & FOUND — file reports for lost/found people or items.
5. SAVED LOCATIONS — Users can pin a spot and return to it later. \
When a user says "save my location", "remember this spot", "save this as [name]", \
"bookmark this place", call save_location with the label they give \
(default label: "my spot") and pass their GPS from ctx if available. \
When a user says "take me back", "I'm lost", "find my saved spot", \
"where did I save", "where is my [name]", "take me to my car" etc., \
call get_saved_location with the label. If no label is mentioned, \
call get_saved_location with an empty label to list all their saved spots.

SCOPE RULE (MOST IMPORTANT):
You ONLY answer questions about Redemption City camp and things directly \
useful to visitors there — parking, emergencies, lost & found, nearby places \
inside or around the camp, saved locations, and general camp navigation. \
If a user asks about ANYTHING outside this scope — general knowledge, news, \
maths, coding, sports, politics, recipes, other cities, other topics — \
respond with exactly this (adapt the wording slightly to feel natural):

"😊 I'm CampAlly — I only assist with things inside *Redemption City* camp. \
I can help you with parking, emergencies, lost & found, nearby places, or \
finding your way around. How can I help you today?"

Do NOT answer off-topic questions even partially. Do NOT say "I can't help \
with that but here's the answer anyway." Simply redirect warmly every time.

Rules:
- Always call a tool to get live data. NEVER invent places, parking availability, \
zone names, or report numbers.
- Keep replies short and warm — this is WhatsApp. Use a few emojis. \
Use *asterisks* for bold (WhatsApp formatting).
- To find the nearest car park you need the user's location. If you don't have \
it, ask them to tap the 📎 (attach) button and share their Location.
- For emergencies, follow the 3-step interview above — never skip straight to \
report_emergency unless the user signals extreme urgency.
- When a tool returns parking info, ALWAYS include: the car park name, number of \
free spots, distance, AND the full Google Maps directions link. Never summarise \
or shorten the tool result — copy it into your reply.
- Respond ONLY with the final message to send to the user. Do not include your \
reasoning, planning, or narration of which tools you called.

REDEMPTION CITY HISTORY & KNOWLEDGE:
Redemption City is the camp ground of the Redeemed Christian Church of God (RCCG), \
located on the Lagos-Ibadan Expressway, Ogun State, Nigeria — about 40 km north of Lagos.

*Founding & RCCG history:*
- RCCG was founded in 1952 by Rev. Josiah Olufemi Akindayomi in Lagos after a divine call.
- After his death in November 1980, Pastor Enoch Adejare Adeboye (Papa GO) became \
  General Overseer — under him the church grew into one of the largest in the world.
- The camp ground on the Lagos-Ibadan Expressway was acquired in 1983. What started as \
  a small bush clearing is now a full city spanning over 16,000 acres (64 km²).

*Key milestones:*
- 1983 — First Holy Ghost Service held at the campsite under tarpaulins.
- 1990s — Permanent structures built; camp becomes a recognised address.
- 1998 — Redeemer's University founded (now in Ede, Osun State).
- 2000s — New Auditorium built, now one of the largest church auditoriums in the world, \
  capable of holding over 1 million worshippers under one roof.
- 2005 — Redemption City officially gazetted as a town with its own postal code.
- Present — The camp has its own fire service, police post, hospital (Redemption Camp \
  Hospital), banks, ATMs, hotels, guest houses, restaurants, schools, and shopping areas.

*Major events:*
- *Monthly Holy Ghost Service* — held every first Friday of the month; draws hundreds \
  of thousands to millions of worshippers. One of the largest monthly Christian gatherings \
  on earth.
- *Annual Holy Ghost Congress* — held every December (usually the first week); the \
  largest annual Christian gathering in the world, drawing 5–10 million+ attendees.
- *Youth programs, conventions, and special services* are held throughout the year.

*Key landmarks inside camp:*
- *New Auditorium (New Arena)* — massive open-sided arena, capacity 1 million+
- *Old Auditorium (Salvation Ministries area)* — original auditorium, still in use
- *Car Parks* — A, B, C (Old Auditorium entrance landmark on Expressway), D (National \
  Youth Centre), F (conventions), V, Odofin Car Park, New Arena Parking
- *Main Gate* — primary entrance off Lagos-Ibadan Expressway
- *National Youth Centre* — multi-purpose youth facility near Car Park D
- *Prayer City / Mountain of Fire* — spiritual prayer area within the camp
- *Model City* — residential estate for permanent residents
- *Redemption Camp Hospital* — full medical facility inside the camp
- *Manna Café* — popular food area
- *Various hotels and guest houses* — scattered throughout the camp

Use this knowledge to answer any questions visitors have about camp history, \
events, landmarks, and what to expect."""

# ── Known landmarks inside Redemption Camp ────────────────────────────────────
# Used to resolve spoken names → GPS coordinates for nearby-places searches.
CAMP_LANDMARKS = {
    "main gate":        (6.800588, 3.444766),
    "main entrance":    (6.800588, 3.444766),
    "entrance":         (6.800588, 3.444766),
    "gate":             (6.800588, 3.444766),
    "expressway gate":  (6.800588, 3.444766),
    "old auditorium":   (6.800000, 3.446000),
    "old arena":        (6.799413, 3.444953),
    "new auditorium":   (6.762738, 3.459516),
    "new arena":        (6.762738, 3.459516),
    "3km arena":        (6.762738, 3.459516),
    "3 km arena":       (6.762738, 3.459516),
    "car park a":       (6.801250, 3.445800),
    "car park b":       (6.799437, 3.446672),
    "car park c":       (6.808912, 3.446672),
    "car park d":       (6.791500, 3.452300),
    "car park f":       (6.799413, 3.444953),
    "car park v":       (6.762738, 3.459516),
    "new arena parking":(6.763900, 3.461200),
    "odofin":           (6.796200, 3.453500),
    "national youth centre": (6.791500, 3.452300),
}

# Maps user-friendly place type → OSM amenity/tourism tags for Overpass query
_OSM_TYPE_MAP = {
    "hotel":       '"tourism"~"hotel|guest_house|hostel|motel"',
    "hotels":      '"tourism"~"hotel|guest_house|hostel|motel"',
    "guest house": '"tourism"~"hotel|guest_house|hostel|motel"',
    "accommodation": '"tourism"~"hotel|guest_house|hostel|motel"',
    "restaurant":  '"amenity"~"restaurant|fast_food|cafe|canteen|food_court"',
    "restaurants": '"amenity"~"restaurant|fast_food|cafe|canteen|food_court"',
    "food":        '"amenity"~"restaurant|fast_food|cafe|canteen|food_court"',
    "eat":         '"amenity"~"restaurant|fast_food|cafe|canteen|food_court"',
    "hospital":    '"amenity"~"hospital|clinic|doctors"',
    "clinic":      '"amenity"~"hospital|clinic|doctors"',
    "medical":     '"amenity"~"hospital|clinic|doctors|pharmacy"',
    "pharmacy":    '"amenity"="pharmacy"',
    "atm":         '"amenity"="atm"',
    "bank":        '"amenity"~"bank|atm"',
    "supermarket": '"shop"~"supermarket|convenience|grocery"',
    "shop":        '"shop"~"supermarket|convenience|grocery"',
    "market":      '"shop"~"supermarket|convenience|grocery|market"',
    "school":      '"amenity"~"school|university|college|kindergarten"',
    "church":      '"amenity"="place_of_worship"',
    "worship":     '"amenity"="place_of_worship"',
    "toilet":      '"amenity"="toilets"',
    "toilets":     '"amenity"="toilets"',
    "fuel":        '"amenity"="fuel"',
    "petrol":      '"amenity"="fuel"',
}

# ── Tool schemas (OpenAI/Groq format) ────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_available_parking",
            "description": (
                "List the camp's car parks with how many spots are free right now "
                "and their status. Use when the user asks where to park, what's "
                "available, or about parking generally."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_nearest_open_zone",
            "description": (
                "Find the closest car park that still has free spots to the user's "
                "shared WhatsApp location, with a Google Maps directions link. "
                "Only works once the user has shared their location."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_emergency",
            "description": (
                "File an emergency report so security/medics are alerted on the "
                "live control dashboard. Use for medical, fire, security, missing "
                "child, traffic accident or crowd stampede situations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "emergency_type": {
                        "type": "string",
                        "enum": ["medical", "fire", "security", "missing",
                                 "traffic", "stampede", "other"],
                        "description": "Category of emergency.",
                    },
                    "description": {
                        "type": "string",
                        "description": "What is happening, in the user's words.",
                    },
                    "location_name": {
                        "type": "string",
                        "description": "Where it is happening, if the user said.",
                    },
                },
                "required": ["emergency_type", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_lost_found",
            "description": (
                "File a lost or found person/item report so staff can help reunite "
                "people and belongings."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["lost_person", "found_person",
                                 "lost_item", "found_item"],
                        "description": "Type of report.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Short title, e.g. 'Lost black backpack'.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Details that would help identify it.",
                    },
                    "location": {
                        "type": "string",
                        "description": "Where it was lost/found, if mentioned.",
                    },
                },
                "required": ["category", "title", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_user_name",
            "description": (
                "Save the user's name so it can be used in future messages. "
                "Call this as soon as the user tells you their name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The user's first name or full name.",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_nearby_places",
            "description": (
                "Find real places (hotels, guest houses, restaurants, hospitals, "
                "ATMs, pharmacies, supermarkets, churches, schools, etc.) near any "
                "named location inside Redemption Camp. Uses live OpenStreetMap data. "
                "Use whenever the user asks what is near a place, e.g. 'hotels near "
                "the main gate', 'restaurants close to new arena', 'ATM near car park B'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location_name": {
                        "type": "string",
                        "description": (
                            "A landmark inside camp the user mentioned, e.g. "
                            "'main gate', 'new arena', 'old auditorium', 'car park b'."
                        ),
                    },
                    "place_type": {
                        "type": "string",
                        "description": (
                            "What the user is looking for, e.g. 'hotel', "
                            "'restaurant', 'atm', 'hospital', 'pharmacy', "
                            "'supermarket', 'church', 'toilet', 'petrol'."
                        ),
                    },
                },
                "required": ["location_name", "place_type"],
            },
        },
    },
]

# Redemption City (RCCG Camp) centre coordinates and allowed radius
CAMP_LAT    = 6.7583   # latitude of camp centre
CAMP_LNG    = 3.5697   # longitude of camp centre
CAMP_RADIUS_KM = 5.0   # 5 km radius — covers the full camp and its immediate surrounds

def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))

def _is_within_camp(lat, lng) -> bool:
    return _haversine_km(lat, lng, CAMP_LAT, CAMP_LNG) <= CAMP_RADIUS_KM

# In-memory conversation cache (backed by DB on each turn).
_conversations: dict[str, list] = {}

# Rate limiting — track message timestamps per phone number.
import time as _time
_rate_timestamps: dict[str, list] = {}
RATE_LIMIT        = 20   # max messages
RATE_WINDOW       = 60   # per N seconds

def _is_rate_limited(phone: str) -> bool:
    now = _time.time()
    ts  = _rate_timestamps.get(phone, [])
    ts  = [t for t in ts if now - t < RATE_WINDOW]
    _rate_timestamps[phone] = ts
    if len(ts) >= RATE_LIMIT:
        return True
    _rate_timestamps[phone].append(now)
    return False

def _get_wa_user(phone: str) -> "WhatsAppUser":
    user, _ = WhatsAppUser.objects.get_or_create(phone=phone)
    return user

def _load_conversation(user: "WhatsAppUser") -> list:
    try:
        return json.loads(user.conversation or '[]')
    except Exception:
        return []

def _save_conversation(user: "WhatsAppUser", history: list):
    user.conversation = json.dumps(history[-50:])
    user.message_count += 1
    user.save(update_fields=['conversation', 'message_count', 'last_seen'])


def _haversine_m(lat1, lng1, lat2, lng2):
    """Distance in metres between two lat/lng points."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Tool implementations ─────────────────────────────────────────────────────

def _tool_get_available_parking() -> str:
    zones = list(ParkingZone.objects.prefetch_related("slots").all())
    if not zones:
        return "No car parks are set up yet."
    open_zones = [z for z in zones
                  if z.status != "full" and z.available_count() > 0]
    if not open_zones:
        return "All car parks are currently FULL 🚧. Please hold or ask staff."
    lines = []
    for z in sorted(open_zones, key=lambda z: -z.available_count()):
        lines.append(f"• *{z.name}* — {z.available_count()} free "
                     f"({z.get_status_display()})")
    return "🅿️ Car parks with space right now:\n" + "\n".join(lines)


def _tool_find_nearest_open_zone(user_lat, user_lng) -> str:
    if user_lat is None or user_lng is None:
        return ("I need your location to find the closest car park. Tap 📎 in "
                "WhatsApp → *Location* → *Send your current location*.")
    candidates = [
        z for z in ParkingZone.objects.prefetch_related("slots").all()
        if z.available_count() > 0
        and not (z.latitude == 0.0 and z.longitude == 0.0)
    ]
    if not candidates:
        return ("No car park with free space and a known location right now. "
                "Try asking for all available parking.")
    nearest = min(candidates,
                  key=lambda z: _haversine_m(user_lat, user_lng,
                                             z.latitude, z.longitude))
    dist = _haversine_m(user_lat, user_lng, nearest.latitude, nearest.longitude)
    dist_txt = f"{round(dist)} m" if dist < 1000 else f"{dist / 1000:.1f} km"
    directions = (f"https://www.google.com/maps/dir/?api=1"
                  f"&destination={nearest.latitude},{nearest.longitude}")
    return (f"📍 Nearest open car park: *{nearest.name}*\n"
            f"{nearest.available_count()} spots free · {dist_txt} away\n"
            f"Directions: {directions}")


def _tool_find_nearby_places(location_name: str, place_type: str, radius_m: int = 1000) -> str:
    key = location_name.lower().strip()
    coords = None
    for landmark, latlng in CAMP_LANDMARKS.items():
        if landmark in key or key in landmark:
            coords = latlng
            break
    if coords is None:
        return (f"I don't recognise *{location_name}* as a landmark inside camp. "
                "Try 'main gate', 'new arena', 'old auditorium', or a car park name.")

    lat, lng = coords
    pt = place_type.lower().strip()
    osm_filter = _OSM_TYPE_MAP.get(pt)
    if osm_filter is None:
        # fallback: search by name keyword
        osm_filter = f'"name"~"{pt}"'

    query = f"""[out:json][timeout:15];
(
  node[{osm_filter}](around:{radius_m},{lat},{lng});
  way[{osm_filter}](around:{radius_m},{lat},{lng});
);
out center 10;"""

    try:
        data = urllib.parse.urlencode({"data": query}).encode()
        req  = urllib.request.Request(
            "https://overpass-api.de/api/interpreter",
            data=data,
            headers={"User-Agent": "CampAllyBot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=18) as resp:
            results = json.loads(resp.read())["elements"]
    except Exception as exc:
        return f"Couldn't reach the places database right now ({exc}). Try again in a moment."

    if not results:
        return (f"No *{place_type}* found within {radius_m} m of *{location_name}* "
                f"in the OpenStreetMap database. The camp may not have that mapped yet.")

    lines = []
    for el in results[:8]:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en") or "Unnamed"
        elat = el.get("lat") or el.get("center", {}).get("lat", lat)
        elng = el.get("lon") or el.get("center", {}).get("lon", lng)
        dist = round(_haversine_m(lat, lng, elat, elng))
        dist_txt = f"{dist} m" if dist < 1000 else f"{dist/1000:.1f} km"
        maps = f"https://www.google.com/maps/dir/?api=1&destination={elat},{elng}"
        lines.append(f"• *{name}* — {dist_txt} away\n  {maps}")

    header = f"📍 *{place_type.title()}* near *{location_name.title()}* ({len(results)} found):\n\n"
    return header + "\n\n".join(lines)


def _tool_report_emergency(emergency_type, description,
                           location_name, reporter_phone) -> str:
    valid = {"medical", "fire", "security", "missing",
             "traffic", "stampede", "other"}
    etype = emergency_type if emergency_type in valid else "other"
    report = EmergencyReport.objects.create(
        emergency_type=etype,
        description=description or "Reported via WhatsApp",
        location_name=location_name or "",
        reporter_phone=reporter_phone or "",
        severity="high",
        device_info="WhatsApp",
    )
    EmergencyTimeline.objects.create(
        emergency=report,
        status="reported",
        note="Reported via WhatsApp",
        updated_by="WhatsApp Bot",
    )
    return (f"🚨 Emergency logged (ref *{str(report.id)[:8]}*). The control room "
            f"has been alerted on the live dashboard. Help is being arranged — "
            f"stay where you are if it's safe.")


def _tool_report_lost_found(category, title, description,
                            location, phone_number) -> str:
    valid = {"lost_person", "found_person", "lost_item", "found_item"}
    cat = category if category in valid else "lost_item"
    report = LostFoundReport.objects.create(
        category=cat,
        title=title or "Untitled report",
        description=description or "Reported via WhatsApp",
        location=location or "Reported via WhatsApp",
        phone_number=phone_number or "WhatsApp",
        urgency="high" if cat in ("lost_person", "found_person") else "medium",
    )
    return (f"📝 {report.get_category_display()} report filed "
            f"(ref *{str(report.id)[:8]}*). Staff will follow up. "
            f"Keep your phone handy.")


def _tool_save_location(label: str, place_name: str, ctx: dict) -> str:
    import datetime
    phone = ctx.get("phone")
    if not phone:
        return "Could not save — no user session found."
    wa_user = _get_wa_user(phone)
    try:
        locations = json.loads(wa_user.saved_locations or '{}')
    except Exception:
        locations = {}

    entry: dict = {"saved_at": datetime.datetime.now().isoformat()}
    lat, lng = ctx.get("lat"), ctx.get("lng")
    if lat is not None and lng is not None:
        entry["lat"]       = lat
        entry["lng"]       = lng
        entry["maps_link"] = f"https://maps.google.com/?q={lat},{lng}"
    if place_name:
        entry["place_name"] = place_name

    key = label.lower().strip()
    locations[key] = entry
    wa_user.saved_locations = json.dumps(locations)
    wa_user.save(update_fields=["saved_locations"])

    if lat is not None and lng is not None:
        return (f"✅ Got it! I've saved *{label}* with your exact GPS location.\n"
                f"Just say 'take me back to {label}' whenever you need it.")
    elif place_name:
        return (f"✅ Saved *{label}* as '{place_name}'.\n"
                f"Say 'take me back to {label}' to get directions later.")
    else:
        return f"✅ Saved *{label}*. Share your 📍 GPS next time for precise directions."


def _tool_get_saved_location(label: str, ctx: dict) -> str:
    phone = ctx.get("phone")
    if not phone:
        return "Could not retrieve — no user session found."
    wa_user = _get_wa_user(phone)
    try:
        locations = json.loads(wa_user.saved_locations or '{}')
    except Exception:
        locations = {}

    if not locations:
        return ("You haven't saved any locations yet.\n"
                "Share your 📍 GPS location and say *save this as [name]* "
                "to bookmark a spot.")

    # List all if no label given
    if not label:
        lines = ["📍 *Your saved locations:*"]
        for k, v in locations.items():
            if v.get("maps_link"):
                lines.append(f"• *{k}* → {v['maps_link']}")
            elif v.get("place_name"):
                lines.append(f"• *{k}* → {v['place_name']}")
            else:
                lines.append(f"• *{k}*")
        return "\n".join(lines)

    # Find by label (exact, then partial)
    key = label.lower().strip()
    entry = locations.get(key)
    if not entry:
        for k, v in locations.items():
            if key in k or k in key:
                entry, key = v, k
                break

    if not entry:
        saved = ", ".join(f"*{k}*" for k in locations)
        return f"I couldn't find a saved location called '{label}'.\nYour saved spots: {saved}"

    lines = [f"📍 *{key.title()}* — here's where you were:"]
    if entry.get("place_name"):
        lines.append(f"Place: {entry['place_name']}")
    if entry.get("maps_link"):
        lines.append(f"🗺️ Tap to navigate: {entry['maps_link']}")
    elif entry.get("lat") and entry.get("lng"):
        lines.append(f"Coordinates: {entry['lat']:.5f}, {entry['lng']:.5f}")
    lines.append("Stay safe and follow the signs! 🏕️")
    return "\n".join(lines)


def _execute_tool(name, tool_input, ctx) -> str:
    try:
        if name == "save_user_name":
            user_name = (tool_input.get("name") or "").strip()
            if user_name and ctx.get("phone"):
                WhatsAppUser.objects.filter(phone=ctx["phone"]).update(name=user_name)
            return f"Name saved: {user_name}"
        if name == "get_available_parking":
            return _tool_get_available_parking()
        if name == "find_nearest_open_zone":
            return _tool_find_nearest_open_zone(ctx["lat"], ctx["lng"])
        if name == "report_emergency":
            return _tool_report_emergency(
                tool_input.get("emergency_type", "other"),
                tool_input.get("description", ""),
                tool_input.get("location_name", ""),
                ctx["phone"],
            )
        if name == "report_lost_found":
            return _tool_report_lost_found(
                tool_input.get("category", "lost_item"),
                tool_input.get("title", ""),
                tool_input.get("description", ""),
                tool_input.get("location", ""),
                ctx["phone"],
            )
        if name == "find_nearby_places":
            return _tool_find_nearby_places(
                tool_input.get("location_name", ""),
                tool_input.get("place_type", ""),
                tool_input.get("radius_m", 1000),
            )
        if name == "save_location":
            return _tool_save_location(
                tool_input.get("label", "my spot"),
                tool_input.get("place_name", ""),
                ctx,
            )
        if name == "get_saved_location":
            return _tool_get_saved_location(
                tool_input.get("label", ""),
                ctx,
            )
        return f"Unknown tool: {name}"
    except Exception as exc:
        traceback.print_exc()
        return f"(tool error in {name}: {exc})"


# ── Main entry point ─────────────────────────────────────────────────────────

def _run_claude(messages, system_prompt, ctx) -> str:
    """Run Claude with tool use. Returns the final text reply."""
    client = _anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    for _ in range(6):
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=system_prompt,
            tools=CLAUDE_TOOLS,
            messages=messages,
        )
        if resp.stop_reason == "tool_use":
            # Add assistant turn with all content blocks
            messages.append({
                "role": "assistant",
                "content": [
                    {"type": b.type, "id": b.id, "name": b.name, "input": b.input}
                    if b.type == "tool_use"
                    else {"type": "text", "text": b.text}
                    for b in resp.content
                ],
            })
            # Run each tool and collect results
            results = []
            for b in resp.content:
                if b.type == "tool_use":
                    result = _execute_tool(b.name, b.input, ctx)
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": result})
            messages.append({"role": "user", "content": results})
            continue

        text_blocks = [b for b in resp.content if b.type == "text"]
        return " ".join(b.text for b in text_blocks).strip()
    return ""


def _run_groq_fallback(messages, system_prompt, ctx) -> str:
    """Groq fallback using OpenAI-compat format."""
    client = _Groq()
    groq_messages = [{"role": "system", "content": system_prompt}] + messages
    for _ in range(6):
        try:
            resp = client.chat.completions.create(
                model=GROQ_MODEL, max_tokens=1024, tools=TOOLS, messages=groq_messages,
            )
        except _BadRequest:
            fallback = client.chat.completions.create(
                model=GROQ_MODEL, max_tokens=1024, messages=groq_messages,
            )
            return (fallback.choices[0].message.content or "").strip()

        choice = resp.choices[0]
        if choice.finish_reason == "tool_calls":
            assistant_msg = choice.message
            groq_messages.append({
                "role": "assistant",
                "content": assistant_msg.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in assistant_msg.tool_calls
                ],
            })
            for tc in assistant_msg.tool_calls:
                result = _execute_tool(tc.function.name, json.loads(tc.function.arguments), ctx)
                groq_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            continue

        return (choice.message.content or "").strip()
    return ""


def run_agent(user_phone, body, user_lat=None, user_lng=None) -> str:
    """Run one WhatsApp turn — Claude primary, Groq fallback."""
    phone = (user_phone or "").replace("whatsapp:", "")
    ctx   = {"phone": phone, "lat": user_lat, "lng": user_lng}

    # Rate limit check
    if _is_rate_limited(phone):
        return ("⏳ You're sending messages too fast. Please wait a moment and try again.")

    # Load or create the persistent user record
    wa_user = _get_wa_user(phone)
    history = _load_conversation(wa_user)

    # Camp boundary check — reject GPS shares from outside the camp
    if user_lat is not None and user_lng is not None:
        if not _is_within_camp(user_lat, user_lng):
            return (
                "📍 It looks like you're not currently within *Redemption City* camp.\n\n"
                "CampAlly only works inside the camp grounds. If you believe this is a mistake, "
                "please share your location again once you're on-site. 🏕️"
            )

    # Location share: bypass LLM for parking only; let LLM handle "save" intent
    _save_keywords = ("save", "remember", "bookmark", "pin", "keep", "mark")
    _wants_save = any(w in (body or "").lower() for w in _save_keywords)
    if user_lat is not None and user_lng is not None and not _wants_save:
        direct = _tool_find_nearest_open_zone(user_lat, user_lng)
        history.append({"role": "user",      "content": body or "Here is my location."})
        history.append({"role": "assistant", "content": direct})
        _save_conversation(wa_user, history)
        return direct

    known_name = wa_user.name or ""
    name_note  = (f"\n\n[System note: This user's name is *{known_name}*. "
                  f"Use their name warmly in replies.]") if known_name else ""
    system_prompt = SYSTEM_PROMPT + name_note

    messages = list(history) + [{"role": "user", "content": body or "Hi"}]

    final_text = ""
    try:
        final_text = _run_claude(messages, system_prompt, ctx)
        print(f"[CampAlly] Claude replied ({len(final_text)} chars)")
    except Exception as e:
        print(f"[CampAlly] Claude failed: {e} — trying Groq fallback")
        try:
            groq_history = [{"role": m["role"], "content": m["content"] if isinstance(m["content"], str) else ""}
                            for m in history if isinstance(m.get("content"), str)]
            final_text = _run_groq_fallback(
                groq_history + [{"role": "user", "content": body or "Hi"}],
                system_prompt, ctx
            )
            print(f"[CampAlly] Groq replied ({len(final_text)} chars)")
        except Exception:
            import datetime
            traceback.print_exc()
            try:
                with open("/tmp/campally_errors.log", "a") as f:
                    f.write(f"\n{'='*60}\n{datetime.datetime.now()}\nMSG: {body}\nERR:\n{traceback.format_exc()}\n")
            except Exception:
                pass
            return "😕 Something went wrong on my end. Please try again in a moment."

    if not final_text:
        final_text = ("Sorry, I didn't quite catch that. Try *Where can I "
                      "park?*, share your 📍 location, or *Report an emergency*.")

    history.append({"role": "user",      "content": body or "Hi"})
    history.append({"role": "assistant", "content": final_text})
    _save_conversation(wa_user, history)
    return final_text


def run_agent_with_image(user_phone: str, caption: str, image_b64: str, mime_type: str) -> str:
    """Process an image message — uses Claude vision to identify places/things in camp."""
    phone = (user_phone or "").replace("whatsapp:", "")

    if _is_rate_limited(phone):
        return "⏳ You're sending messages too fast. Please wait a moment and try again."

    wa_user  = _get_wa_user(phone)
    history  = _load_conversation(wa_user)
    known_name = wa_user.name or ""
    name_note  = (f"\n\n[System note: This user's name is *{known_name}*. "
                  f"Use their name warmly in replies.]") if known_name else ""
    system_prompt = SYSTEM_PROMPT + name_note

    # Build image content block for Claude vision
    user_text = caption or (
        "I just sent you a photo. Can you identify what or where this is inside "
        "Redemption City camp? Describe what you see and help me navigate or understand it."
    )
    image_content = [
        {
            "type": "image",
            "source": {
                "type":       "base64",
                "media_type": mime_type.split(";")[0].strip(),
                "data":       image_b64,
            },
        },
        {"type": "text", "text": user_text},
    ]

    messages = list(history) + [{"role": "user", "content": image_content}]

    final_text = ""
    try:
        client = _anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        resp   = client.messages.create(
            model=CLAUDE_MODEL, max_tokens=1024,
            system=system_prompt, messages=messages,
        )
        final_text = " ".join(b.text for b in resp.content if b.type == "text").strip()
        print(f"[CampAlly] Vision replied ({len(final_text)} chars)")
    except Exception as e:
        print(f"[CampAlly] Vision failed: {e}")
        final_text = "😕 I had trouble reading that image. Please try again or describe what you see in text."

    history.append({"role": "user",      "content": user_text})
    history.append({"role": "assistant", "content": final_text})
    _save_conversation(wa_user, history)
    return final_text
