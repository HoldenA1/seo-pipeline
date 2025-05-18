"""This file is the main static site generator"""

import os, re
from staging.schema import Article, Review, Location
from jinja2 import Template
import staging.database as db

# Constants
TEMPLATE_PATH = "/app/template.html"
WEBSITE_FOLDER = "/app/website"
ENV_TYPE = os.getenv("ENV_TYPE")
ENV_TYPES = {"prod", "dev"}

# Index variables
states = {}

# Load templates
f = open("/app/state_dir_template.html")
state_template = Template(f.read())
f.close()
f = open("/app/city_dir_template.html")
city_template = Template(f.read())
f.close()

def generate_city_directory(city: str, state: str):
    state_url = make_url_safe(state)
    folder = os.path.join(WEBSITE_FOLDER, "states", state_url)
    os.makedirs(folder, exist_ok=True)
    filename = make_url_safe(city)
    html = city_template.render(city=city, state=state)
    with open(f"{folder}/{filename}.html", "w") as f:
        f.write(html)

def make_url_safe(name: str) -> str:
    # Lowercase
    name = name.lower()
    # Replace spaces and underscores with dashes
    name = re.sub(r'[\s_]+', '-', name)
    # Remove any character that's not alphanumeric or dash
    name = re.sub(r'[^a-z0-9\-]', '', name)
    # Remove leading/trailing dashes
    name = name.strip('-')
    return name

def load_directory_data():
    """Loads the data needed to build directories into global states variable"""
    city_state_pairs = db.get_cities()
    for city, state in city_state_pairs:
        if state not in states:
            states[state] = []
        url = f"{make_url_safe(state)}/{make_url_safe(city)}.html"
        states[state].append((city, url))
    for cities in states.values():
        cities.sort()

def generate_state_directory():
    html = state_template.render(states=states)
    with open(f"{WEBSITE_FOLDER}/index.html", "w") as f:
        f.write(html)

load_directory_data()
for state, cities in states.items():
    for city in cities:
        generate_city_directory(city[0], state)
        print(f"generated {city}, {state} page")
generate_state_directory()