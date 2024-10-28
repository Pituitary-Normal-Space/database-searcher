# Database Searcher Simple UI To Ease Literature Review

This is a reusable UI that accesses and creates speadsheets of unique papers found from a searchterm in Pubmed and Embase.

### Why Was This Built?

This was built so that you can enter a single search query in PubMed syntax and search both Embase and Pubmed. This allows us to easily make searches, once we are certain that these are the searches we want to complete, and remove duplciates.

### What Does It Do Currently?

Currently this is a simple program that provides a UI to interface with the APIs for searching across these two medical databases: Embase and PubMed. It checks that your search string is properly formatted in PubMed syntax then converts it to Embase format to search there. Once the search is completed, the results of the search are added to a dataframe, duplicate entries are removed, and a CSV of results is produced.

The results saved to a csv file contain columns for:

- Source
- Author
- Title
- Abstract
- ID
- Link
- Query

### How To Set Up Locally

- Clone this repository locally

  ```
  git clone https://github.com/Pituitary-Neurochemistry-Heatmap/database-searcher
  ```

- Ensure you have pip and python 3 installed.
- Download our package manager poetry (if you have not downloaded it already)
  ```bash
  pip install poetry
  ```
- I have created the pyproject.toml files so you don't have to worry about any of that. Just do the below.
- Add configuration to have venv in project directory

  ```bash
  poetry config virtualenvs.in-project true
  ```

- Set up virtual environment using poetry

  ```bash
  poetry install --no-root
  ```

- Now you should have a created venv that you can switch into with the following command
  ```bash
  poetry shell
  ```
- Run the program with this command
  ```bash
  python main.py
  ```
- If you chose to change the source code--as you develop you can add packages with the following command
  ```bash
  poetry add <package-name>
  ```
