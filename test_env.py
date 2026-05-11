from google import genai

client = genai.Client(api_key="AIzaSyCtr1e-cLto7uxORio6SJjY-VV4VF2vbaA")

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Say hello"
)

print(response.text)