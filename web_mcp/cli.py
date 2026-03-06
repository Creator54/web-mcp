"""CLI tool to search the web and browse web pages"""

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*Unverified HTTPS.*")

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Union, Literal
import typer
import click
import json
import os
import re
import requests

# Try to use curl_cffi for better browser impersonation, fall back to requests
try:
    from curl_cffi import requests

    IMPERSONATE_AVAILABLE = True
except ImportError:
    import requests

    IMPERSONATE_AVAILABLE = False

from bs4 import BeautifulSoup
import urllib.parse
from readability import Document


app = typer.Typer(
    help="CLI tool for searching the web and browsing web pages.",
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True, no_args_is_help=True)
def callback(
    ctx: typer.Context,
    browse: Optional[str] = typer.Option(None, "-b", "--browse", help="Browse a URL"),
    query: Optional[str] = typer.Argument(None, help="Search query"),
):
    """Show help if no command is provided."""
    if ctx.invoked_subcommand is None:
        if browse:
            from web_mcp.cli import browse_web_page

            result = browse_web_page(browse, "text")
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"Title: {result['title']}")
                print(f"URL: {result['url']}")
                print("\nContent:")
                print(result["content"])
        elif query:
            from web_mcp.cli import search_duckduckgo

            results = search_duckduckgo(query, 5)
            for i, r in enumerate(results, 1):
                print(f"{i}. {r.get('title', 'No title')}")
                print(f"   {r.get('link', '')}")
                if r.get("snippet"):
                    print(f"   {r.get('snippet')}")
                print()


class SearchEngine(Enum):
    """Enumeration for supported search engines."""

    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"


class OutputFormat(Enum):
    """Enumeration for output formats."""

    TEXT = "text"
    JSON = "json"
    JSON_COMPACT = "json-compact"


@dataclass
class SearchResult:
    """Represents a single search result."""

    title: str
    link: str
    snippet: str
    result_type: str = "generic"


@dataclass
class BrowseResult:
    """Represents a browsing result."""

    title: str
    url: str
    content: str
    content_type: str = "text"
    error: Optional[str] = None


def search_duckduckgo(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo for the given query using curl_cffi
    This function uses DuckDuckGo's Instant Answer API which provides structured data
    """
    # First try the main API
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "pretty": "1",
        "no_html": "1",
        "skip_disambig": "1",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        if IMPERSONATE_AVAILABLE:
            response = requests.get(
                url, params=params, headers=headers, impersonate="chrome110"
            )
        else:
            response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}")

        data = response.json()

        results = []

        # Extract main abstract if available (summary of the query)
        if data.get("Abstract", ""):
            results.append(
                {
                    "title": data.get("Heading", query),
                    "link": data.get("AbstractURL", ""),
                    "snippet": data.get("Abstract", ""),
                    "type": "abstract",
                }
            )

        # Extract related topics
        if "RelatedTopics" in data:
            for topic in data["RelatedTopics"][:num_results]:
                if "FirstURL" in topic and "Text" in topic:
                    results.append(
                        {
                            "title": topic.get("Name", topic.get("Text", "No title")),
                            "link": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", ""),
                            "type": "topic",
                        }
                    )

        # Extract Results array
        if "Results" in data:
            for result in data["Results"][:num_results]:
                if "FirstURL" in result:
                    results.append(
                        {
                            "title": result.get("Text", ""),
                            "link": result.get("FirstURL", ""),
                            "snippet": result.get("Text", ""),
                            "type": "result",
                        }
                    )

        # If we don't have enough results, try to get from Results array which might have more
        if len(results) < num_results and "RelatedTopics" in data:
            for topic in data["RelatedTopics"]:
                if len(results) >= num_results:
                    break
                if "FirstURL" in topic and topic.get("FirstURL", "") not in [
                    r["link"] for r in results
                ]:
                    results.append(
                        {
                            "title": topic.get("Name", topic.get("Text", "No title")),
                            "link": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", ""),
                            "type": "topic",
                        }
                    )

        # If still no results, try using the lite method as fallback
        if not results:
            fallback_results = search_duckduckgo_lite(query, num_results)
            if fallback_results:
                return fallback_results

        return results[:num_results]

    except Exception as e:
        click.echo(f"Error performing search: {str(e)}", err=True)
        # If API fails, try the lite method as fallback
        try:
            return search_duckduckgo_lite(query, num_results)
        except Exception:
            return []


def search_duckduckgo_lite(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Alternative search approach using DuckDuckGo Lite which returns HTML
    This method scrapes the lite.duckduckgo.com page
    """
    url = "https://lite.duckduckgo.com/lite/"
    data = {
        "q": query,
        "kl": "us-en",  # Language/region
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        if IMPERSONATE_AVAILABLE:
            response = requests.post(
                url, data=data, headers=headers, impersonate="chrome110"
            )
        else:
            response = requests.post(url, data=data, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}")

        # Parse the HTML response
        soup = BeautifulSoup(response.text, "html.parser")

        results = []

        # Find result links in the table
        links = soup.find_all("a", class_="result-link")
        snippets = soup.find_all("td", class_="result-snippet")

        # Pair links with snippets
        for i, link in enumerate(links):
            if i >= num_results:
                break
            title = link.get_text().strip()
            href = link.get("href", "")

            # Get corresponding snippet if available
            snippet = ""
            if i < len(snippets):
                snippet = snippets[i].get_text().strip()

            if href:  # Only add if we have a valid link
                results.append(
                    {"title": title, "link": href, "snippet": snippet, "type": "lite"}
                )

        return results

    except Exception as e:
        click.echo(f"Error performing lite search: {str(e)}", err=True)
        return []


def browse_web_page(url: str, format: str = "text") -> Dict[str, Union[str, bool]]:
    """
    Browse a web page and extract its content
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        if IMPERSONATE_AVAILABLE:
            response = requests.get(
                url, headers=headers, impersonate="chrome110", timeout=10
            )
        else:
            response = requests.get(url, headers=headers, timeout=10, verify=False)

        if response.status_code != 200:
            return {
                "error": f"Failed to fetch page: HTTP {response.status_code}",
                "url": url,
            }

        # Use readability to extract the main content
        doc = Document(response.text)
        title = doc.title()
        content = doc.summary()

        if format == "html":
            # For HTML format, return the cleaned HTML content
            return {
                "title": title,
                "url": url,
                "content": content,
                "content_type": format,
            }
        else:  # text format
            # Clean up the content
            soup = BeautifulSoup(content, "html.parser")

            # Remove script and style elements
            for script in soup(
                [
                    "script",
                    "style",
                    "nav",
                    "header",
                    "footer",
                    "aside",
                    "meta",
                    "noscript",
                ]
            ):
                script.decompose()

            # Get text content
            text_content = soup.get_text(separator="\n", strip=True)

            # Clean up the text: remove extra whitespace and normalize newlines
            import re

            # Remove extra whitespace and normalize newlines
            lines = [line.strip() for line in text_content.splitlines() if line.strip()]
            text_content = "\n".join(lines)
            # Replace multiple spaces with single space
            text_content = re.sub(r"[ \t]{2,}", " ", text_content)
            # Remove lines that are just special characters (like citation markers)
            lines = [
                line
                for line in text_content.split("\n")
                if not re.match(
                    r"^[\[\(]?\d+[\]\)]?$|^[\[\(]?\s*edit\s*[\]\)]?$|^[^\w\s]*$",
                    line.strip(),
                )
            ]
            text_content = "\n".join(lines)
            # Remove leading/trailing whitespace
            text_content = text_content.strip()

            return {
                "title": title,
                "url": url,
                "content": text_content,
                "content_type": format,
            }

    except Exception as e:
        return {"error": f"Error browsing page: {str(e)}", "url": url}


def search_brave(
    query: str, num_results: int = 5, brave_api_key: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Search Brave Search for the given query using their API as primary method
    Falls back to web scraping if no API key is available
    """
    # Get API key from parameter or environment variable
    if not brave_api_key:
        brave_api_key = os.getenv("BRAVE_API_KEY")

    # Try API method first if API key is available
    if brave_api_key:
        url = "https://api.search.brave.com/res/v1/web/search"
        params = {"q": query, "count": num_results, "result_filter": "web"}

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": brave_api_key,
        }

        try:
            if IMPERSONATE_AVAILABLE:
                response = requests.get(
                    url, params=params, headers=headers, impersonate="chrome110"
                )
            else:
                response = requests.get(url, params=params, headers=headers)

            if response.status_code != 200:
                raise Exception(
                    f"Request failed with status code {response.status_code}"
                )

            data = response.json()

            results = []

            # Extract web search results
            if "web" in data and "results" in data["web"]:
                for item in data["web"]["results"][:num_results]:
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "link": item.get("url", ""),
                            "snippet": item.get("description", ""),
                            "type": "brave_api",
                        }
                    )

            return results

        except Exception as e:
            click.echo(f"API search failed: {str(e)}", err=True)
            click.echo("Falling back to web scraping method...", err=True)

    # If API key not available or API fails, use web scraping
    return search_brave_scrape(query, num_results)


def search_brave_scrape(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Search Brave Search using web scraping method (no API key required)
    Note: Brave uses AWS WAF with CAPTCHA, so this may not work reliably.
    For production use, get a free API key at https://brave.com/search/api/
    """
    click.echo(
        "Note: Brave Search uses CAPTCHA protection. For reliable results, use BRAVE_API_KEY.",
        err=True,
    )
    click.echo("Get a free API key at: https://brave.com/search/api/", err=True)

    url = "https://search.brave.com/search"
    params = {"q": query, "source": "web"}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        if IMPERSONATE_AVAILABLE:
            response = requests.get(
                url, params=params, impersonate="chrome120", timeout=15
            )
        else:
            response = requests.get(url, params=params, headers=headers, timeout=15)

        if response.status_code != 200:
            if response.status_code == 405:
                raise Exception(
                    f"Brave Search blocked the request with CAPTCHA (status {response.status_code}). An API key is required."
                )
            raise Exception(f"Request failed with status code {response.status_code}")

        # Parse the HTML response
        soup = BeautifulSoup(response.text, "html.parser")

        results = []

        # Look for result elements - brave search results often have specific class patterns
        # Results may be in <div> elements with certain classes or data attributes
        # Check for the main results container
        results_container = soup.find("div", id="results")
        if results_container:
            # Find all result items within the container
            result_items = results_container.find_all(
                "div",
                class_=lambda x: (
                    x
                    and any(
                        class_name in x.lower()
                        for class_name in ["snippet", "result", "web", "svelte"]
                    )
                ),
            )
        else:
            # Alternative: look for result items more broadly
            result_items = soup.find_all(
                "div",
                class_=lambda x: (
                    x
                    and any(
                        keyword in x.lower()
                        for keyword in ["result", "web", "snippet", "svelte"]
                    )
                ),
            )

        for item in result_items:
            if len(results) >= num_results:
                break

            # Try to find the link, title and snippet within the result item
            link_elem = item.find("a", href=True)
            if link_elem:
                href = link_elem.get("href", "")
                # Resolve relative URLs
                if href.startswith("/"):
                    if href.startswith("//"):
                        href = "https:" + href
                    else:
                        href = "https://search.brave.com" + href
                elif not href.startswith(("http://", "https://")):
                    continue  # Skip invalid links

                # Skip internal brave search links
                if "search.brave.com/search?" in href or "search.brave.com/?" in href:
                    continue

                title = link_elem.get_text().strip()
                if not title:
                    title = link_elem.find_next(text=True, recursive=False)
                    if title:
                        title = str(title).strip()

                # Find the snippet/description
                # Look for sibling elements that may contain the description
                snippet_elem = item.find(
                    ["p", "span", "div"],
                    class_=lambda x: (
                        x
                        and any(
                            keyword in x.lower()
                            for keyword in [
                                "description",
                                "snippet",
                                "t-secondary",
                                "t-tertiary",
                                "text",
                            ]
                        )
                    ),
                )

                if not snippet_elem:
                    # Look for next sibling elements that might be the snippet
                    next_elem = link_elem.find_next_sibling()
                    if next_elem:
                        snippet = next_elem.get_text().strip()
                    else:
                        # Try to find any remaining text content in the item
                        item_text = item.get_text().replace(title, "", 1).strip()
                        snippet = (
                            item_text[:200] + "..."
                            if len(item_text) > 200
                            else item_text
                        )
                else:
                    snippet = snippet_elem.get_text().strip()

                if (
                    title and href and "brave.com" not in href
                ):  # Exclude internal brave links
                    results.append(
                        {
                            "title": title,
                            "link": href,
                            "snippet": snippet[:200] + "..."
                            if len(snippet) > 200
                            else snippet,  # Limit snippet length
                            "type": "brave_scraped",
                        }
                    )

        return results

    except Exception as e:
        click.echo(f"Error performing Brave web scraping: {str(e)}", err=True)
        click.echo("Falling back to DuckDuckGo search...", err=True)
        # Fallback to DuckDuckGo when Brave fails
        return search_duckduckgo(query, num_results)


@app.command()
def search(
    query: List[str] = typer.Argument(..., help="The search query"),
    num_results: int = typer.Option(
        5, "--num-results", "-n", min=1, max=20, help="Number of results to return"
    ),
    format: str = typer.Option(
        "text", "--format", help="Output format: text, json, or json-compact"
    ),
    engine: str = typer.Option(
        "duckduckgo",
        "--engine",
        help="Search engine to use: duckduckgo (default) or brave",
    ),
    lite: bool = typer.Option(
        False,
        "--lite",
        help="Use DuckDuckGo Lite (HTML) instead of API (only applicable for DuckDuckGo)",
    ),
):
    """
    Search the web for a query

    Examples:
      web-search search python programming
      web-search search "machine learning" -n 10 --format json
      web-search search openai --engine brave
      web-search search openai --lite
    """
    search_query = " ".join(query)

    # Perform search based on selected engine and method
    if engine == "brave":
        results = search_brave(search_query, num_results)
    elif lite:
        results = search_duckduckgo_lite(search_query, num_results)
    else:
        results = search_duckduckgo(search_query, num_results)

    if format == "json":
        # Output as formatted JSON
        print(
            json.dumps(
                {
                    "query": search_query,
                    "results": results,
                    "count": len(results),
                    "engine": engine,
                },
                indent=2,
            )
        )
    elif format == "json-compact":
        # Output as compact JSON
        print(json.dumps(results))
    else:  # text format
        if results:
            print(f"\nSearch results for: {search_query} ({engine})\n")
            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")
                link = result.get("link", "")
                snippet = result.get("snippet", "")

                print(f"{i}. {title}")
                print(f"   {link}")
                if snippet:
                    print(f"   {snippet}")
                print()
        else:
            print("No results found or error occurred.")


@app.command()
def browse(
    url: str = typer.Argument(..., help="The URL to browse and extract content from"),
    format: str = typer.Option(
        "text", "--format", help="Output format: text (default) or html"
    ),
):
    """
    Browse a web page and extract its content

    Examples:
      web-search browse https://example.com
      web-search browse https://wikipedia.org --format html
    """
    # Validate and normalize URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    result = browse_web_page(url, format)

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        print("\nContent:")
        print(result["content"])


if __name__ == "__main__":
    app()
