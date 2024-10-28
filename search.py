"""
File that contains a class that will be used to search the relevant database for the user's query.
"""

import re
from functools import reduce
from tkinter import messagebox
from typing import Dict, List, Tuple
from xml.etree import ElementTree as ET

import requests
import pandas as pd

from config import MAX_RESULTS
from const import EMBASE_KEY, PUBMED_KEY, EMBASE_INST_TOKEN_KEY


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
        
        # Define field tag mappings
        field_tag_mapping = {
            "[Title/Abstract]": ":ti,ab,kw",  # Title/Abstract in PubMed -> Title/Abstract in Embase
            "[Title]": ":ti,kw",  # Title in PubMed -> Title in Embase
            "[Abstract]": ":ab,kw",  # Abstract in PubMed -> Abstract in Embase
            "[Mesh]": "/mj",  # MeSH in PubMed -> Major subject heading in Embase
            "[mh]": "/mj",  # MeSH Heading -> Major subject heading
        }
        
        # Step 1: Apply quotes to unquoted phrases and lowercased terms
        def add_quotes(match):
            term = match.group(0).strip()
            # Ensure lowercase and single quoting
            return f"'{term.lower()}'" if not term.startswith("'") else term
        # This pattern finds terms without quotes or field tags
        embase_query = re.sub(r"(?<!['\"])\\b\\w[\\w\\s/-]+\\b(?!['\"])|\"([^\"]+)\"",
                            add_quotes, pubmed_query)

        # Step 2: Replace field tags in PubMed format with Embase format
        for pubmed_tag, embase_tag in field_tag_mapping.items():
            embase_query = re.sub(re.escape(pubmed_tag), embase_tag, embase_query)
        
        # Step 3: Ensure Boolean operators are in uppercase
        embase_query = re.sub(r"\b(and|or|not)\b", lambda x: x.group(0).upper(), embase_query, flags=re.IGNORECASE)
        
        # Step 4: Clean up any redundant spaces and quotes
        embase_query = re.sub(r"\s+", " ", embase_query)   # Replace multiple spaces with single space

        # Step 5: Add quotes to terms without quotes
        def remove_strings(string: str, l: List[str]) -> str:
            return reduce(lambda a, b: a.replace(b, ""), l, string)
        words_to_quote = remove_strings(embase_query, ["OR", "AND", "NOT", "(", ")"] + list(field_tag_mapping.values())).split("'")
        # Remove empty spaces in list
        words_to_quote = [word for word in words_to_quote if word.strip() != ""]
        # If word not surrounded by single quotes then split by space
        words_to_quote = [word.split() for word in words_to_quote if word[0] not in ["'", '"'] and word[-1] not in ["'", '"']]
        # Flatten the list
        words_to_quote = [word for sublist in words_to_quote for word in sublist]
        # Add single quotes to each word
        embase_query = re.sub(r"\b" + r"\b|\b".join(words_to_quote) + r"\b", lambda x: f"'{x.group(0)}'", embase_query)

        # Replace double quotes with single quotes
        embase_query = re.sub(r'"', "", embase_query)
        return embase_query


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
        embase_base_url = "https://api.elsevier.com/content/embase/article"
        params = {
            "query": query,
            "apiKey": self.api_key.get(EMBASE_KEY),
            "insttoken": self.api_key.get(EMBASE_INST_TOKEN_KEY),
            "count": MAX_RESULTS,  # Number of results to return (optional)
        }

        headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": self.api_key.get(EMBASE_KEY),
            "X-ELS-Insttoken": self.api_key.get(EMBASE_INST_TOKEN_KEY),
        }
        
        response = requests.get(embase_base_url, params=params, headers=headers)

        # Check for errors in the response
        if response.status_code == 401:
            raise Exception(
                "Unauthorized: Check your API key and permissions. You may need to get a token for Embase if working off grounds. You can email: integrationsupport@elsevier.com for this."
            )
        elif response.status_code == 403:
            raise Exception(
                "Forbidden: You do not have permission to access this resource. Check your API key and permissions. You can email: integrationsupport@elsevier.com for support."
            )
        
        response.raise_for_status()  # Raise an error for bad responses
        return response.json().get("results", {})

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

    def __fetch_pubmed_details(
        self, pubmed_ids: List[int]
    ) -> List[Tuple[str, str, str]]:
        """
        Fetch details (title, abstract, and first author's last name) from PubMed using the provided IDs.

        Args:
            pubmed_ids (list): List of PubMed IDs.
            api_key (str): Your PubMed API key.

        Returns:
            list: List of tuples containing (title, abstract, first_author_last_name) for each article.
        """
        if not pubmed_ids:
            return []

        pubmed_base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        ids = ",".join(map(str, pubmed_ids))  # Join IDs into a single string
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
            # Get full title and abstract
            title = self.__get_full_title(article)
            abstract = self.__get_full_abstract(article)

            # Get first author's last name
            first_author_lastname = "No author available"
            authors = article.findall(".//Author")
            if authors and authors[0].find(".//LastName") is not None:
                first_author_lastname = authors[0].find(".//LastName").text

            # Append title, abstract, and first author's last name
            details.append((title, abstract, first_author_lastname))

        return details

    def __fetch_embase_details(self, data: dict) -> Tuple[str, str, str]:
        """
        Fetch details (title, abstract, and first author's last name) from a specific Embase document.

        Args:
            data (dict): The Embase json.

        Returns:
            tuple: (title, abstract, first_author_last_name) of the document.
        """
        head = data.get("head", {})
        title = head.get("citationTitle", {}).get("titleText", {})[0].get("ttltext", "No title available")
        try:
            abstract = head.get("abstracts", {}).get("abstracts", {})[0].get("paras", "No abstract available")
            abstract = " ".join(abstract)
        except KeyError:
            abstract = "No abstract available"
        except IndexError:
            abstract = "No abstract available"
        try:
            first_author_lastname = head.get("authorList", {}).get("authors", {})[0].get("surname", "No author available")
        except IndexError:
            first_author_lastname = "No author available"
        except KeyError:
            first_author_lastname = "No author available"
        link = data.get("itemInfo", {}).get("itemIdList", {}).get("doi", "No link available")
        id = data.get("itemInfo", {}).get("itemIdList", {}).get("medl", "No ID available")

        if link == "No link available" and id != "No ID available":
            link = f"https://pubmed.ncbi.nlm.nih.gov/{id}/"

        return id, title, abstract, first_author_lastname, link

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
        results_data = {
            "Source": [],
            "Author": [],
            "Title": [],
            "Abstract": [],
            "ID": [],
            "Link": [],
            "Query": [],
        }

        # Add PubMed results to the DataFrame
        for i, pmid in enumerate(pubmed_ids):
            results_data["Source"].append("PubMed")

            # Extract title, abstract, and author from PubMed details
            title, abstract, author_lastname = (
                pubmed_details[i]
                if i < len(pubmed_details)
                else (
                    "No title available",
                    "No abstract available",
                    "No author available",
                )
            )

            results_data["Title"].append(title)
            results_data["Abstract"].append(abstract)
            results_data["Author"].append(author_lastname)
            results_data["ID"].append(pmid)
            results_data["Link"].append(
                f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            )  # Create PubMed link
            # Add the query to the DataFrame
            results_data["Query"].append(query)

        # Add Embase results to the DataFrame
        for i, doc in enumerate(embase_results):
            # Extract title, abstract, and author from Embase details
            id, title, abstract, author_lastname, link = embase_details[i]

            results_data["Source"].append("Embase")
            results_data["Title"].append(title)
            results_data["Abstract"].append(abstract)
            results_data["Author"].append(author_lastname)
            results_data["ID"].append(id)
            results_data["Link"].append(link) 
            results_data["Query"].append(embase_query)

        # Create and return the DataFrame
        results_df = pd.DataFrame(results_data)

        # Based on: lowercase title with only alphabetical characters and last name with lower case
        # If redundant rows are found, keep the first one
        # Drop duplicates by normalizing the "Title" and "Author" columns to lowercase and removing non-alphabetical characters
        # Create normalized columns for Title and Author
        results_df['Normalized_Title'] = results_df['Title'].str.lower().str.replace(r'[^a-z]', '', regex=True)
        results_df['Normalized_Author'] = results_df['Author'].str.lower().str.replace(r'[^a-z]', '', regex=True)

        # Drop duplicates based on these normalized columns, keeping the first occurrence
        results_df = results_df.drop_duplicates(subset=['Normalized_Title', 'Normalized_Author'], keep='first')

        # Drop the temporary normalized columns after deduplication
        results_df = results_df.drop(columns=['Normalized_Title', 'Normalized_Author'])

        return results_df
