import urllib.request
import urllib.parse
import json

def search_web(query: str) -> str:
    """
    Searches the web using DuckDuckGo's free API and returns results.

    Args:
        query: The search query string

    Returns:
        Formatted search results as a string, or an error message
    """
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_redirect=1"
        req = urllib.request.Request(url, headers={"User-Agent": "jemi-agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        results = []
        if data.get("AbstractText"):
            results.append(f"Summary: {data['AbstractText']}")
            if data.get("AbstractURL"):
                results.append(f"Source: {data['AbstractURL']}")
        related = data.get("RelatedTopics", [])[:5]
        if related:
            results.append("\nRelated results:")
            for topic in related:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"• {topic['Text']}")
        if not results:
            return f"No results found for '{query}'. Try a different search term."
        return "\n".join(results)
    except urllib.error.URLError as e:
        return f"Network error searching for '{query}': {str(e)}"
    except json.JSONDecodeError:
        return f"Error parsing search results for '{query}'."
    except Exception as e:
        return f"Error searching: {str(e)}"
