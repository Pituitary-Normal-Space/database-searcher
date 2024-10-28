import re
from typing import List
from functools import reduce

def convert_pubmed_to_embase(pubmed_query: str) -> str:
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

# Example input
pubmed_query = '(MMP OR metalloproteinases[Title/Abstract]) AND (invasive OR invasiveness) AND ("pituitary adenoma"[Title/Abstract] OR "pituitary adenomas"[Title/Abstract] OR "pituitary mass"[Title/Abstract] OR "pituitary tumor"[Title/Abstract])'

# Convert to Embase syntax
embase_query = convert_pubmed_to_embase(pubmed_query)

print(embase_query)
