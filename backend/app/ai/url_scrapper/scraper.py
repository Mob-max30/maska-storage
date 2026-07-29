import requests
import trafilatura


class WebScraper:
    """
    Scrapes and extracts readable content from a webpage.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/138.0 Safari/537.36"
            )
        }

    def scrape(self, url: str) -> dict:
        """
        Extracts article content and metadata from a URL.

        Args:
            url (str): Website URL

        Returns:
            dict: Scraped document containing title, author,
                  publish date, url and extracted text.
        """

        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=15
            )

            response.raise_for_status()

            downloaded = response.text

            text = trafilatura.extract(downloaded)

            metadata = trafilatura.extract_metadata(downloaded)

            if text is None:
                raise Exception("No readable content found.")

            return {
                "url": url,
                "title": metadata.title if metadata else None,
                "author": metadata.author if metadata else None,
                "date": metadata.date if metadata else None,
                "text": text
            }

        except requests.exceptions.RequestException as e:
            raise Exception(f"Network Error: {e}")

        except Exception as e:
            raise Exception(f"Scraping Error: {e}")