import urllib.request
import urllib.error

url = "http://127.0.0.1:5000/flight/results?from_place=medicaps+university&to_place=iit+indore&date=2026-04-10&ranking_type=fastest"
try:
    with urllib.request.urlopen(url) as response:
        print("Success:", response.status)
        html = response.read().decode('utf-8')
        if "error.html" in html or "class=\"error-message" in html:
            print("Page returned 200, but has error content:")
            print(html[:500])
except urllib.error.HTTPError as e:
    print(f"HTTPError {e.code}: {e.reason}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print("Other error:", e)
