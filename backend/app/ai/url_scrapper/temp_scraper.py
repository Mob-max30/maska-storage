from scraper import WebScraper

scraper = WebScraper()

url = input("Enter URL: ")

result = scraper.scrape(url)

print("\nTITLE:")
print(result["title"])

print("\nAUTHOR:")
print(result["author"])

print("\nDATE:")
print(result["date"])

print("\nTEXT PREVIEW:")
print(result["text"])