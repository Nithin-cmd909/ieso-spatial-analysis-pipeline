import requests

# The official unversioned rolling XML file for all transmission outages occurring today
url = "https://reports-public.ieso.ca/public/TxOutagesTodayAll/PUB_TxOutagesTodayAll.xml"

print("Pinging IESO XML endpoint...")
response = requests.get(url, timeout=15)

if response.status_code == 200:
    raw_xml = response.text
    
    print("\n--- RAW XML PREVIEW (First 2000 Characters) ---")
    # Print the first 2000 characters so we can see the exact tags, namespaces, and structure
    print(raw_xml[:2000])
else:
    print(f"Failed to connect. HTTP Status: {response.status_code}")