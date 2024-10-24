"""
This script checks the if user has API keys saved in the OS environment variables.
If not, we prompt the user to enter the keys and save them in the environment variables.
"""

import os
from tkinter import messagebox, simpledialog
from typing import Optional, Dict, Literal

# Load environment variables from the .env file
from dotenv import load_dotenv
from const import EMBASE_KEY, PUBMED_KEY, EMBASE_INST_TOKEN_KEY, VALID_DATABASES

load_dotenv()


def get_keys() -> Dict[Optional[str], Optional[str]]:
    """
    Check if the API keys are saved in the environment variables.
    If not, prompt the user to enter the keys and save them.

    Returns:
        Dict: A dictionary containing the API keys. If either key is missing it will be None.
    """
    api_keys = {
        EMBASE_KEY: os.getenv(EMBASE_KEY),
        EMBASE_INST_TOKEN_KEY: os.getenv(EMBASE_INST_TOKEN_KEY),
        PUBMED_KEY: os.getenv(PUBMED_KEY),
    }

    # Check if the keys are saved
    if not api_keys[EMBASE_KEY]:
        # Prompt the user to enter the key using a dialog box
        embase_key = simpledialog.askstring(
            "DBSearcher: Enter Embase API key",
            "You need to enter your Embase API key to continue:",
        )
        embase_key = embase_key.strip()
        try:
            # Save the key in the environment variables
            save_keys(embase_key, "embase")
            api_keys[EMBASE_KEY] = embase_key
        except ValueError as e:
            messagebox.showerror(
                "DBSearcher: Error",
                f"You need to enter a valid API key to continue. Please restart the program. {e}",
            )
            return api_keys
        
    if not api_keys[EMBASE_INST_TOKEN_KEY]:
        # Prompt the user to enter the key using a dialog box
        embase_inst_token = simpledialog.askstring(
            "DBSearcher: Enter Embase Institution Token",
            "You need to enter your Embase Institution Token to continue:",
        )
        embase_inst_token = embase_inst_token.strip()
        try:
            # Save the key in the environment variables
            save_keys(embase_inst_token, "embase_inst_token")
            api_keys[EMBASE_INST_TOKEN_KEY] = embase_inst_token
        except ValueError as e:
            messagebox.showerror(
                "DBSearcher: Error",
                f"You need to enter a valid API key to continue. Please restart the program. {e}",
            )
            return api_keys

    if not api_keys[PUBMED_KEY]:
        # Prompt the user to enter the key using a dialog box
        pubmed_key = simpledialog.askstring(
            "DBSearcher: Enter PubMed API key",
            "You need to enter your PubMed API key to continue:",
        )
        pubmed_key = pubmed_key.strip()
        try:
            # Save the key in the environment variables
            save_keys(pubmed_key, "pubmed")
            api_keys[PUBMED_KEY] = pubmed_key
        except ValueError as e:
            messagebox.showerror(
                "DBSearcher: Error",
                f"You need to enter a valid API key to continue. Please restart the program. {e}",
            )
            return api_keys

    return api_keys


def save_keys(key: str, database: Literal["embase", "pubmed", "embase_inst_token"]) -> None:
    """
    Save the API key in the environment variables for a database.

    Args:
        key (str): The API key to save.
        database (str): The database for which the key is saved.
    """
    # Check that the key is not empty
    if not key:
        raise ValueError("The key cannot be empty.")

    # Check that the database is valid
    if database not in VALID_DATABASES and database != "embase_inst_token":
        raise ValueError(f"The database must be one of {VALID_DATABASES} or inst_token.")

    # Save the key in the environment variables
    if database == "embase":
        os.environ[EMBASE_KEY] = key
    elif database == "pubmed":
        os.environ[PUBMED_KEY] = key
    elif database == "embase_inst_token":
        os.environ[EMBASE_INST_TOKEN_KEY] = key

    # Save the environment variables to the .env file
    with open(".env", "a") as f:
        f.write(f"{database.upper()}_KEY={key}\n")
