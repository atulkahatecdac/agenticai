import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from flask import Flask, request, render_template_string

from chaining_tool_outputs import (
    geocode_city,
    get_current_weather,
    recommend_clothing,
    find_nearby_places,
)

# Web front end for chaining_tool_outputs.py's DETERMINISTIC chain only -
# geocode_city -> get_current_weather -> recommend_clothing, plus
# find_nearby_places branching off the same coordinates. No agent/LLM
# call here, so each request is just four fast HTTP calls.

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>What to Wear</title>
<style>
body { font-family: Arial; width: 700px; margin: 40px auto; }
input[type=text] { width: 300px; padding: 6px; }
input[type=submit] { padding: 6px 16px; }
.box { margin-top: 20px; padding: 15px; border: 1px solid gray; background: #f2f2f2; }
.error { color: #b00020; }
pre { white-space: pre-wrap; font-family: inherit; margin: 0; }
</style>
</head>
<body>
<h2>What to Wear</h2>
<form method="post">
<input type="text" name="city" placeholder="Enter a city, e.g. Tokyo" value="{{ city }}">
<input type="submit" value="Go">
</form>

{% if error %}
<p class="error">{{ error }}</p>
{% endif %}

{% if weather %}
<div class="box">
<h3>Weather in {{ city }}</h3>
<p>{{ weather }}</p>
<p><strong>{{ recommendation }}</strong></p>
</div>

<div class="box">
<h3>Nearby attractions &amp; restaurants</h3>
<pre>{{ places }}</pre>
</div>
{% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    city = ""
    weather = recommendation = places = error = ""

    if request.method == "POST":
        city = request.form["city"].strip()
        coords = geocode_city.invoke({"city": city})

        if "," not in coords:
            error = coords
        else:
            weather = get_current_weather.invoke({"lat_lon": coords})
            recommendation = recommend_clothing.invoke({"weather_summary": weather})
            places = find_nearby_places.invoke({"lat_lon": coords})

    return render_template_string(
        HTML,
        city=city,
        weather=weather,
        recommendation=recommendation,
        places=places,
        error=error,
    )

if __name__ == "__main__":
    app.run(debug=True)
