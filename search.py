"""
File that contains a class that will be used to search the relevant database for the user's query.
"""

import re
from tkinter import messagebox
from typing import Dict, List, Tuple
from xml.etree import ElementTree as ET

import requests
import pandas as pd

from config import MAX_RESULTS
from const import EMBASE_KEY, PUBMED_KEY


class DBSearcher:
    def __init__(self, api_keys: Dict[str, str]) -> None:
        """
        Initialize the Search class with the API keys.

        Args:
            api_key (Dict[str, str]): Dict of API keys to use for the search.
        """
        self.api_key = api_keys

    def __is_proper_pubmed_search(self, query: str) -> bool:
        """
        Check if the given PubMed search query is properly formatted.

        Args:
            query (str): The PubMed search string.

        Returns:
            bool: True if the query is properly formatted, False otherwise.
        """
        # Check for balanced parentheses
        if query.count("(") != query.count(")"):
            return False

        # Check for balanced quotes
        if query.count('"') % 2 != 0:
            return False

        # Ensure that AND, OR, NOT are used in uppercase
        # We'll use a regular expression to find all operators and check their validity
        operator_pattern = r"\b(AND|OR|NOT)\b"
        operators = re.findall(operator_pattern, query, flags=re.IGNORECASE)

        for op in operators:
            if op != op.upper():
                return False

        # Check for correct field tag format (e.g., [tiab], [title], etc.)
        # Here we assume the field tags follow the pattern [<letters>] where letters are lowercase
        field_tag_pattern = r"\[\w+\]"
        field_tags = re.findall(field_tag_pattern, query)

        # Ensure that all field tags are valid from this list: tiab, title, abstract, mesh, mh
        valid_field_tags = {"tiab", "title", "abstract", "mesh", "mh"}
        if not all(tag[1:-1] in valid_field_tags for tag in field_tags):
            return False

        for tag in field_tags:
            if not re.match(r"\[\w+\]", tag):
                return False

        return True

    def __convert_pubmed_to_embase(self, pubmed_query: str) -> str:
        """
        Convert a PubMed search query into an Embase-compatible query.

        Args:
            pubmed_query (str): The search string in PubMed format.

        Returns:
            str: The search string converted to Embase format.
        """
        # Convert PubMed field tags to Embase tags
        field_tag_mapping = {
            "[tiab]": "/ti,ab",  # Title/Abstract in PubMed -> Title/Abstract in Embase
            "[title]": "/ti",  # Title in PubMed -> Title in Embase
            "[abstract]": "/ab",  # Abstract in PubMed -> Abstract in Embase
            "[mesh]": "/mj",  # MeSH in PubMed -> Major subject heading in Embase (broad assumption)
            "[mh]": "/mj",  # MeSH Heading -> Major subject heading (rough equivalent)
        }

        # Replace PubMed field tags with corresponding Embase tags
        for pubmed_tag, embase_tag in field_tag_mapping.items():
            pubmed_query = pubmed_query.replace(pubmed_tag, embase_tag)

        # Ensure Boolean operators are in uppercase
        pubmed_query = re.sub(
            r"\b(AND|OR|NOT)\b",
            lambda match: match.group(0).upper(),
            pubmed_query,
            flags=re.IGNORECASE,
        )

        # Add quotes around multi-word terms that are not already quoted
        # We use a regular expression to find terms outside of quotes
        def quote_phrases(match):
            phrase = match.group(0)
            if '"' not in phrase:  # If the phrase is not already quoted
                words = phrase.split()
                if len(words) > 1:  # If there are multiple words, it's a phrase
                    return f'"{phrase}"'
            return phrase

        # Apply quoting only to non-quoted multi-word terms
        pubmed_query = re.sub(
            r'(?<!")(\b\w+(?:\s+\w+)+\b)(?!")',  # Match multi-word terms not already quoted
            quote_phrases,
            pubmed_query,
        )

        return pubmed_query

    def __search_pubmed(self, query: str):
        """
        Search PubMed using the provided query and API key.

        Args:
            query (str): The search query for PubMed.

        Returns:
            dict: The search results from PubMed.
        """
        pubmed_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "api_key": self.api_key.get(PUBMED_KEY),
            "retmax": MAX_RESULTS,  # Number of results to return (optional)
        }

        response = requests.get(pubmed_base_url, params=params)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json().get("esearchresult", {}).get("idlist", [])

    def __search_embase(self, query: str) -> dict:
        """
        Search Embase using the provided query and API key.

        Args:
            query (str): The search query for Embase.

        Returns:
            dict: The search results from Embase.
        """
        embase_base_url = "https://api.elsevier.com/content/search/sciencedirect"
        params = {
            "query": query,
            "apiKey": self.api_key.get(EMBASE_KEY),
            "count": MAX_RESULTS,  # Number of results to return (optional)
        }

        headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": self.api_key.get(EMBASE_KEY),
            # "X-ELS-Insttoken": token,  # We need to get a token for this to work
        }

        response = requests.get(embase_base_url, params=params, headers=headers)

        # Check for errors in the response
        if response.status_code == 401:
            raise Exception("Unauthorized: Check your API key and permissions.")

        response.raise_for_status()  # Raise an error for bad responses
        return response.json().get("search-results", {}).get("entry", [])

    def __get_full_title(self, article: ET.Element) -> str:
        """
        Extract the full title text from an article element.

        Args:
            article (Element): The article element from the XML tree.

        Returns:
            str: The full title text of the article.
        """
        article_title_element = article.find(".//ArticleTitle")
        if article_title_element is not None:
            # Use itertext() to get all text including from sub-elements
            return "".join(article_title_element.itertext()).strip()
        else:
            return "No title available"

    def __get_full_abstract(self, article: ET.Element) -> str:
        """
        Extract the full abstract text from an article element.

        Args:
            article (Element): The article element from the XML tree.

        Returns:
            str: The full abstract text of the article.
        """
        abstract_element = article.find(".//Abstract")
        if abstract_element is not None:
            # Use itertext() to get all text from the Abstract and its child elements
            return "".join(abstract_element.itertext()).strip()
        else:
            return "No abstract available"

    def __fetch_pubmed_details(self, pubmed_ids: List[int]) -> List[Tuple[str, str]]:
        """
        Fetch details (title and abstract) from PubMed using the provided IDs.

        Args:
            pubmed_ids (list): List of PubMed IDs.
            api_key (str): Your PubMed API key.

        Returns:
            list: List of tuples containing (title, abstract) for each article.
        """
        if not pubmed_ids:
            return []

        pubmed_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        ids = ",".join(pubmed_ids)  # Join IDs into a single string
        params = {
            "db": "pubmed",
            "id": ids,
            "retmode": "xml",
            "api_key": self.api_key.get(PUBMED_KEY),
        }

        response = requests.get(pubmed_base_url, params=params)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        details = []

        for article in root.findall(".//PubmedArticle"):
            # See why the title is sometimes partially missing
            # print(ET.tostring(article, encoding="unicode", method="xml"))

            title = self.__get_full_title(article)
            abstract = self.__get_full_abstract(article)
            details.append((title, abstract))

        return details

    def __fetch_embase_details(self, doc: dict):
        """
        Fetch details (title and abstract) from a specific Embase document.

        Args:
            doc (dict): The Embase document.

        Returns:
            tuple: (title, abstract) of the document.
        """
        title = doc.get("dc:title", "No title available")
        abstract = doc.get("dc:description", "No abstract available")
        return title, abstract

    def search(self, query: str) -> pd.DataFrame:
        """
        Search both PubMed and Embase using the provided query
        and return the results in a Pandas DataFrame.

        Args:
            query (str): The search query.

        Returns:
            pd.DataFrame: A DataFrame containing the search results.
        """
        # Check that the query is in the proper format for PubMed
        if not self.__is_proper_pubmed_search(query):
            # Show an error messagebox
            messagebox.showerror(
                "DBSearcher: Error",
                "The search query is not properly formatted for PubMed.",
            )
            return pd.DataFrame()
        # Search PubMed
        try:
            pubmed_ids = self.__search_pubmed(query)
            pubmed_details = self.__fetch_pubmed_details(pubmed_ids)
        except Exception as e:
            # Show an error messagebox
            messagebox.showerror("DBSearcher: Error", f"Error searching PubMed: {e}")
            pubmed_ids = []
            pubmed_details = []

        # Convert the PubMed query to Embase format
        embase_query = self.__convert_pubmed_to_embase(query)

        # Search Embase
        try:
            embase_results = self.__search_embase(embase_query)
            embase_details = [
                self.__fetch_embase_details(doc) for doc in embase_results
            ]
        except Exception as e:
            # Show an error messagebox
            messagebox.showerror("DBSearcher: Error", f"Error searching Embase: {e}")
            embase_results = []
            embase_details = []

        # Create a DataFrame to hold the results
        results_data = {"Source": [], "Title": [], "Abstract": [], "ID": [], "Link": []}

        # Add PubMed results to the DataFrame
        for i, pmid in enumerate(pubmed_ids):
            results_data["Source"].append("PubMed")
            title, abstract = (
                pubmed_details[i]
                if i < len(pubmed_details)
                else ("No title available", "No abstract available")
            )
            results_data["Title"].append(title)
            results_data["Abstract"].append(abstract)
            results_data["ID"].append(pmid)
            results_data["Link"].append(
                f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            )  # Create PubMed link

        # Add Embase results to the DataFrame
        for i, doc in enumerate(embase_results):
            title, abstract = embase_details[i]
            results_data["Source"].append("Embase")
            results_data["Title"].append(title)
            results_data["Abstract"].append(abstract)
            results_data["ID"].append(doc.get("dc:identifier", "No ID available"))
            results_data["Link"].append(
                doc.get("link", [{"href": "No link available"}])[0]["href"]
            )  # Assuming there's a link

        # Create and return the DataFrame
        results_df = pd.DataFrame(results_data)
        print(results_df)
        return results_df
